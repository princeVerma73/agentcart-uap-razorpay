import os
import sqlite3
import hmac
import hashlib
import time
from typing import Dict, Any, Tuple, Optional, List
from pydantic import BaseModel, Field
from merchant.catalog import catalog_db
from merchant.models import OrderProposal
from audit.ledger import audit_ledger

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "audit", "audit_ledger.db")

class PolicyConfig(BaseModel):
    max_single_transaction_limit: float = 10000.0  # Absolute max allowed
    auto_approve_limit: float = 3000.0            # UAP / Autonomous pre-authorization limit
    allowed_categories: List[str] = Field(default_factory=lambda: ["accessories", "cables", "peripherals", "pantry"])
    require_human_approval_always: bool = False
    enforce_stock_check: bool = True
    idempotency_window_seconds: int = 300         # 5-minute sliding window

class VerificationResult(BaseModel):
    is_valid: bool
    status: str  # 'AUTO_APPROVED', 'HITL_REQUIRED', 'REJECTED_OVER_BUDGET', 'REJECTED_STOCK_ERROR', 'REJECTED_PRICE_MISMATCH', 'REJECTED_DUPLICATE'
    reason: str
    verified_total: float
    idempotency_key: str
    requires_human_signature: bool = False
    hitl_token: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

class PersistentIdempotencySet(set):
    def __init__(self, db_path: str = DB_PATH, window_seconds: int = 300):
        super().__init__()
        self.db_path = db_path
        self.window_seconds = window_seconds
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS idempotency_records (
                    key TEXT PRIMARY KEY,
                    created_at REAL,
                    session_id TEXT
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error initializing idempotency DB: {e}")

    def add_key(self, key: str, session_id: str = "", timestamp_override: Optional[float] = None):
        self.add(key)
        now = timestamp_override if timestamp_override is not None else time.time()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO idempotency_records (key, created_at, session_id)
                VALUES (?, ?, ?)
            """, (key, now, session_id))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error persisting idempotency key: {e}")

    def is_processed(self, key: str, timestamp_override: Optional[float] = None) -> bool:
        if key in self:
            return True
        now = timestamp_override if timestamp_override is not None else time.time()
        cutoff = now - self.window_seconds
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT key FROM idempotency_records WHERE key = ? AND created_at >= ?", (key, cutoff))
            row = cursor.fetchone()
            conn.close()
            if row:
                self.add(key)
                return True
        except Exception as e:
            print(f"Error checking idempotency key: {e}")
        return False

    def clear(self):
        super().clear()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM idempotency_records")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error clearing idempotency DB: {e}")

class PolicyEngine:
    def __init__(self, config: Optional[PolicyConfig] = None):
        self.config = config or PolicyConfig()
        self.processed_idempotency_keys = PersistentIdempotencySet(DB_PATH, self.config.idempotency_window_seconds)

    def update_config(self, new_config: PolicyConfig):
        self.config = new_config
        self.processed_idempotency_keys.window_seconds = new_config.idempotency_window_seconds

    def generate_idempotency_key(self, session_id: str, proposal: OrderProposal, timestamp_override: Optional[float] = None) -> str:
        now = timestamp_override if timestamp_override is not None else time.time()
        window_id = int(now // self.config.idempotency_window_seconds)
        items_str = ",".join([f"{i.product_id}:{i.quantity}" for i in proposal.items])
        raw_str = f"{session_id}:{proposal.merchant_id}:{proposal.total_amount}:{items_str}:{window_id}"
        return hashlib.sha256(raw_str.encode()).hexdigest()

    def generate_hitl_token(self, session_id: str, verified_total: float, idempotency_key: str, secret_key: str = "rzp_hitl_secret_key") -> str:
        payload = f"{session_id}:{verified_total:.2f}:{idempotency_key}".encode()
        return hmac.new(secret_key.encode(), payload, hashlib.sha256).hexdigest()

    def verify_hitl_token(self, token: str, session_id: str, verified_total: float, idempotency_key: str, secret_key: str = "rzp_hitl_secret_key") -> bool:
        expected = self.generate_hitl_token(session_id, verified_total, idempotency_key, secret_key)
        return hmac.compare_digest(token, expected)

    def verify_order_proposal(self, session_id: str, proposal: OrderProposal, timestamp_override: Optional[float] = None) -> VerificationResult:
        idempotency_key = self.generate_idempotency_key(session_id, proposal, timestamp_override)
        
        # 1. Check for replay attack / duplicate transaction in current window
        if self.processed_idempotency_keys.is_processed(idempotency_key, timestamp_override):
            audit_ledger.record(
                session_id=session_id,
                event_type="POLICY_CHECK",
                status="REJECTED",
                summary="Duplicate transaction blocked by Idempotency Guard",
                details={"idempotency_key": idempotency_key}
            )
            return VerificationResult(
                is_valid=False,
                status="REJECTED_DUPLICATE",
                reason="Duplicate order payload detected within time window (Idempotency violation).",
                verified_total=0.0,
                idempotency_key=idempotency_key
            )

        # 2. Verify all items against Live Merchant Database
        calculated_total = 0.0
        item_verifications = []
        
        for item in proposal.items:
            product = catalog_db.get_by_id(item.product_id)
            if not product:
                audit_ledger.record(
                    session_id=session_id,
                    event_type="POLICY_CHECK",
                    status="REJECTED",
                    summary=f"Product {item.product_id} not found in merchant catalog",
                    details={"product_id": item.product_id}
                )
                return VerificationResult(
                    is_valid=False,
                    status="REJECTED_INVALID_PRODUCT",
                    reason=f"Product '{item.product_id}' does not exist in the merchant inventory.",
                    verified_total=0.0,
                    idempotency_key=idempotency_key
                )
            
            # Verify stock
            if self.config.enforce_stock_check and product.stock < item.quantity:
                audit_ledger.record(
                    session_id=session_id,
                    event_type="POLICY_CHECK",
                    status="REJECTED",
                    summary=f"Insufficient stock for {product.name} (Requested: {item.quantity}, Available: {product.stock})",
                    details={"product_id": product.id, "requested": item.quantity, "available": product.stock}
                )
                return VerificationResult(
                    is_valid=False,
                    status="REJECTED_STOCK_ERROR",
                    reason=f"Insufficient inventory for '{product.name}'. In stock: {product.stock}, Requested: {item.quantity}.",
                    verified_total=0.0,
                    idempotency_key=idempotency_key,
                    details={"available_stock": product.stock, "product_id": product.id}
                )

            # Recalculate true unit price from merchant DB (Anti-Hallucination Guard)
            true_item_total = product.price * item.quantity
            calculated_total += true_item_total
            item_verifications.append({
                "product_id": product.id,
                "name": product.name,
                "claimed_unit_price": item.unit_price,
                "verified_db_price": product.price,
                "quantity": item.quantity,
                "subtotal": true_item_total
            })

        # 3. Verify price integrity (Reject if LLM hallucinated arbitrary lower price)
        if abs(calculated_total - proposal.total_amount) > 0.01:
            audit_ledger.record(
                session_id=session_id,
                event_type="POLICY_CHECK",
                status="WARNING",
                summary="Price discrepancy detected between agent proposal and merchant DB",
                details={"claimed_total": proposal.total_amount, "verified_total": calculated_total}
            )
            # We enforce the verified DB price strictly
            proposal.total_amount = calculated_total

        # 4. Check Absolute Spending Ceiling
        if calculated_total > self.config.max_single_transaction_limit:
            audit_ledger.record(
                session_id=session_id,
                event_type="POLICY_CHECK",
                status="REJECTED",
                summary=f"Order total (₹{calculated_total:,.2f}) exceeds hard spending ceiling of ₹{self.config.max_single_transaction_limit:,.2f}",
                details={"total": calculated_total, "limit": self.config.max_single_transaction_limit}
            )
            return VerificationResult(
                is_valid=False,
                status="REJECTED_OVER_BUDGET",
                reason=f"Order total of ₹{calculated_total:,.2f} exceeds policy maximum limit of ₹{self.config.max_single_transaction_limit:,.2f}.",
                verified_total=calculated_total,
                idempotency_key=idempotency_key
            )

        # 5. Check Autonomous Pre-Authorization vs Human-In-The-Loop Gate
        if self.config.require_human_approval_always or calculated_total > self.config.auto_approve_limit:
            hitl_token = self.generate_hitl_token(session_id, calculated_total, idempotency_key)
            audit_ledger.record(
                session_id=session_id,
                event_type="HITL_REQUIRED",
                status="PENDING_APPROVAL",
                summary=f"Order amount ₹{calculated_total:,.2f} exceeds auto-approve limit (₹{self.config.auto_approve_limit:,.2f}). Human sign-off required.",
                details={"total": calculated_total, "threshold": self.config.auto_approve_limit, "items": item_verifications, "hitl_token": hitl_token}
            )
            return VerificationResult(
                is_valid=True,
                status="HITL_REQUIRED",
                reason=f"Order amount (₹{calculated_total:,.2f}) requires explicit human sign-off as it exceeds the ₹{self.config.auto_approve_limit:,.2f} autonomous limit.",
                verified_total=calculated_total,
                idempotency_key=idempotency_key,
                requires_human_signature=True,
                hitl_token=hitl_token,
                details={"items": item_verifications}
            )

        # 6. Passed all checks -> Auto-Approved
        audit_ledger.record(
            session_id=session_id,
            event_type="POLICY_CHECK",
            status="SUCCESS",
            summary=f"Order ₹{calculated_total:,.2f} pre-authorized autonomously under UAP limits.",
            details={"total": calculated_total, "items": item_verifications, "idempotency_key": idempotency_key}
        )
        return VerificationResult(
            is_valid=True,
            status="AUTO_APPROVED",
            reason=f"Order fully validated and within autonomous pre-authorization ceiling (₹{calculated_total:,.2f} <= ₹{self.config.auto_approve_limit:,.2f}).",
            verified_total=calculated_total,
            idempotency_key=idempotency_key,
            requires_human_signature=False,
            details={"items": item_verifications}
        )

    def mark_key_processed(self, idempotency_key: str, session_id: str = "", timestamp_override: Optional[float] = None):
        self.processed_idempotency_keys.add_key(idempotency_key, session_id, timestamp_override)

policy_engine = PolicyEngine()

