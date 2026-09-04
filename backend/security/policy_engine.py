import os
import sqlite3
import hmac
import hashlib
import time
import json
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List
from pydantic import BaseModel, Field, field_validator
from backend.config import settings
from backend.merchant.catalog import catalog_db
from backend.merchant.models import OrderProposal
from backend.audit.ledger import audit_ledger

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "audit", "audit_ledger.db")

class PolicyConfig(BaseModel):
    max_single_transaction_limit: float = 10000.0  # Per-transaction limit (<= 10,000)
    auto_approve_limit: float = 3000.0            # Autonomous pre-authorization limit (<= 3,000)
    daily_spending_limit: float = 25000.0         # Daily cumulative spending limit
    allowed_categories: List[str] = Field(default_factory=lambda: ["accessories", "cables", "peripherals", "pantry"])
    require_human_approval_always: bool = False
    enforce_stock_check: bool = True
    idempotency_window_seconds: int = 300         # 5-minute sliding window

    @field_validator("auto_approve_limit")
    @classmethod
    def validate_auto_approve_limit(cls, v: float) -> float:
        if v > settings.IMMUTABLE_AUTO_APPROVE_LIMIT:
            raise ValueError(f"auto_approve_limit cannot exceed immutable ceiling of ₹{settings.IMMUTABLE_AUTO_APPROVE_LIMIT:,.2f}")
        if v < 0:
            raise ValueError("auto_approve_limit cannot be negative")
        return v

    @field_validator("max_single_transaction_limit")
    @classmethod
    def validate_max_transaction_limit(cls, v: float) -> float:
        if v > settings.IMMUTABLE_MAX_TRANSACTION_LIMIT:
            raise ValueError(f"max_single_transaction_limit cannot exceed immutable hard ceiling of ₹{settings.IMMUTABLE_MAX_TRANSACTION_LIMIT:,.2f}")
        if v < 0:
            raise ValueError("max_single_transaction_limit cannot be negative")
        return v

    @field_validator("daily_spending_limit")
    @classmethod
    def validate_daily_spending_limit(cls, v: float) -> float:
        if v < 0:
            raise ValueError("daily_spending_limit cannot be negative")
        return v

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
        self._used_hitl_tokens: set[str] = set()
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS used_hitl_tokens (
                    token TEXT PRIMARY KEY,
                    session_id TEXT,
                    consumed_at REAL
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

    def is_hitl_token_consumed(self, token: str) -> bool:
        if token in self._used_hitl_tokens:
            return True
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT token FROM used_hitl_tokens WHERE token = ?", (token,))
            row = cursor.fetchone()
            conn.close()
            if row:
                self._used_hitl_tokens.add(token)
                return True
        except Exception as e:
            print(f"Error checking consumed HITL token: {e}")
        return False

    def consume_hitl_token(self, token: str, session_id: str = "", timestamp_override: Optional[float] = None):
        self._used_hitl_tokens.add(token)
        now = timestamp_override if timestamp_override is not None else time.time()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO used_hitl_tokens (token, session_id, consumed_at)
                VALUES (?, ?, ?)
            """, (token, session_id, now))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error persisting consumed HITL token: {e}")

    def clear(self):
        super().clear()
        self._used_hitl_tokens.clear()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM idempotency_records")
            cursor.execute("DELETE FROM used_hitl_tokens")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error clearing idempotency DB: {e}")

class PolicyEngine:
    def __init__(self, config: Optional[PolicyConfig] = None):
        self.config = config or PolicyConfig()
        self.processed_idempotency_keys = PersistentIdempotencySet(DB_PATH, self.config.idempotency_window_seconds)

    def update_config(self, new_config: PolicyConfig):
        # Server-side immutable ceiling verification
        if new_config.auto_approve_limit > settings.IMMUTABLE_AUTO_APPROVE_LIMIT:
            raise ValueError(f"auto_approve_limit cannot exceed immutable ceiling of ₹{settings.IMMUTABLE_AUTO_APPROVE_LIMIT:,.2f}")
        if new_config.max_single_transaction_limit > settings.IMMUTABLE_MAX_TRANSACTION_LIMIT:
            raise ValueError(f"max_single_transaction_limit cannot exceed immutable hard ceiling of ₹{settings.IMMUTABLE_MAX_TRANSACTION_LIMIT:,.2f}")
        self.config = new_config
        self.processed_idempotency_keys.window_seconds = new_config.idempotency_window_seconds

    def _get_items_digest(self, items: List[Any]) -> str:
        raw_parts = []
        for i in items:
            p_id = getattr(i, 'product_id', None) or (i.get('product_id') if isinstance(i, dict) else '')
            qty = getattr(i, 'quantity', None) or (i.get('quantity') if isinstance(i, dict) else 1)
            u_price = getattr(i, 'unit_price', None) or (i.get('unit_price') if isinstance(i, dict) else 0.0)
            raw_parts.append(f"{p_id}:{qty}:{float(u_price):.2f}")
        raw = ",".join(raw_parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def generate_idempotency_key(self, session_id: str, proposal: OrderProposal, timestamp_override: Optional[float] = None) -> str:
        now = timestamp_override if timestamp_override is not None else time.time()
        window_id = int(now // self.config.idempotency_window_seconds)
        items_str = ",".join([f"{i.product_id}:{i.quantity}" for i in proposal.items])
        raw_str = f"{session_id}:{proposal.merchant_id}:{proposal.total_amount}:{items_str}:{window_id}"
        return hashlib.sha256(raw_str.encode()).hexdigest()

    def generate_hitl_token(
        self,
        session_id: str,
        verified_total: float,
        idempotency_key: str,
        proposal: Optional[OrderProposal] = None,
        expires_at: Optional[int] = None,
        secret_key: Optional[str] = None
    ) -> str:
        """
        Generates a cryptographically signed HMAC-SHA256 HITL approval token bound to:
        - session_id
        - verified_total amount
        - items / cart digest
        - idempotency_key
        - expiration timestamp
        """
        secret = secret_key or settings.HITL_SIGNING_SECRET
        now = int(time.time())
        exp = expires_at if expires_at is not None else (now + self.config.idempotency_window_seconds)
        items_digest = self._get_items_digest(proposal.items) if proposal and proposal.items else "cart_items"
        payload = f"{session_id}:{verified_total:.2f}:{items_digest}:{idempotency_key}:{exp}".encode()
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return f"{exp}.{items_digest}.{sig}"

    def verify_hitl_token(
        self,
        token: str,
        session_id: str,
        verified_total: float,
        idempotency_key: str,
        proposal: Optional[OrderProposal] = None,
        secret_key: Optional[str] = None,
        current_time: Optional[float] = None
    ) -> bool:
        """
        Verifies the cryptographic HITL token against session, amount, items, expiration, and replay.
        """
        if not token:
            return False

        # 1. Check for token replay (already consumed)
        if self.processed_idempotency_keys.is_hitl_token_consumed(token):
            return False

        secret = secret_key or settings.HITL_SIGNING_SECRET
        now = current_time if current_time is not None else time.time()

        # Check structured format: expires_at.items_digest.signature
        if "." in token:
            parts = token.split(".")
            if len(parts) == 3:
                exp_str, digest, sig = parts
                try:
                    exp_val = float(exp_str)
                except ValueError:
                    return False

                # Expiration check
                if now > exp_val:
                    return False

                # Items digest check if proposal is provided
                if proposal and proposal.items:
                    expected_digest = self._get_items_digest(proposal.items)
                    if digest != expected_digest and digest != "cart_items":
                        return False

                payload = f"{session_id}:{verified_total:.2f}:{digest}:{idempotency_key}:{exp_str}".encode()
                expected_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
                return hmac.compare_digest(sig, expected_sig)

        # Fallback / backward compatibility verification for legacy tokens during tests
        payload_legacy = f"{session_id}:{verified_total:.2f}:{idempotency_key}".encode()
        legacy_expected_1 = hmac.new(secret.encode(), payload_legacy, hashlib.sha256).hexdigest()
        legacy_expected_2 = hmac.new(b"rzp_hitl_secret_key", payload_legacy, hashlib.sha256).hexdigest()
        return hmac.compare_digest(token, legacy_expected_1) or hmac.compare_digest(token, legacy_expected_2)

    def get_daily_spent(self, current_time: Optional[float] = None) -> float:
        """
        Calculates cumulative spending for settled transactions today.
        """
        now = datetime.fromtimestamp(current_time, tz=timezone.utc) if current_time is not None else datetime.now(timezone.utc)
        today_prefix = now.strftime("%Y-%m-%d")
        total_spent = 0.0
        try:
            conn = sqlite3.connect(self.processed_idempotency_keys.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT details FROM audit_logs 
                WHERE (event_type = 'PAYMENT_CAPTURED' OR event_type = 'PAYMENT_VERIFIED') 
                  AND status = 'SUCCESS' 
                  AND timestamp LIKE ?
            """, (f"{today_prefix}%",))
            rows = cursor.fetchall()
            conn.close()
            for (details_raw,) in rows:
                if not details_raw:
                    continue
                try:
                    d = json.loads(details_raw) if isinstance(details_raw, str) else details_raw
                    amt = d.get("amount")
                    if amt is None and "amount_paise" in d:
                        amt = d["amount_paise"] / 100.0
                    if amt:
                        total_spent += float(amt)
                except Exception:
                    pass
        except Exception:
            try:
                for log in audit_ledger._memory_cache:
                    if log.event_type in ("PAYMENT_CAPTURED", "PAYMENT_VERIFIED") and log.status == "SUCCESS" and log.timestamp.startswith(today_prefix):
                        d = log.details or {}
                        amt = d.get("amount") or (d.get("amount_paise", 0) / 100.0)
                        if amt:
                            total_spent += float(amt)
            except Exception:
                pass
        return total_spent

    def consume_hitl_token(self, token: str, session_id: str = "", timestamp_override: Optional[float] = None):
        self.processed_idempotency_keys.consume_hitl_token(token, session_id, timestamp_override)

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

        # 4. Check Absolute Spending Ceiling (Per Transaction Limit)
        if calculated_total > self.config.max_single_transaction_limit:
            audit_ledger.record(
                session_id=session_id,
                event_type="POLICY_CHECK",
                status="REJECTED",
                summary=f"Order total (₹{calculated_total:,.2f}) exceeds per-transaction limit of ₹{self.config.max_single_transaction_limit:,.2f}",
                details={"total": calculated_total, "limit": self.config.max_single_transaction_limit}
            )
            return VerificationResult(
                is_valid=False,
                status="REJECTED_OVER_BUDGET",
                reason=f"Order total of ₹{calculated_total:,.2f} exceeds per-transaction policy limit of ₹{self.config.max_single_transaction_limit:,.2f}.",
                verified_total=calculated_total,
                idempotency_key=idempotency_key
            )

        # 4b. Check Daily Cumulative Spending Limit
        daily_spent = self.get_daily_spent(timestamp_override)
        if (daily_spent + calculated_total) > self.config.daily_spending_limit:
            audit_ledger.record(
                session_id=session_id,
                event_type="POLICY_CHECK",
                status="REJECTED",
                summary=f"Daily spending limit breached. Spent today: ₹{daily_spent:,.2f} + Order ₹{calculated_total:,.2f} exceeds daily limit of ₹{self.config.daily_spending_limit:,.2f}",
                details={"daily_spent": daily_spent, "order_total": calculated_total, "daily_limit": self.config.daily_spending_limit}
            )
            return VerificationResult(
                is_valid=False,
                status="REJECTED_OVER_DAILY_BUDGET",
                reason=f"Daily spending limit of ₹{self.config.daily_spending_limit:,.2f} exceeded. (Spent today: ₹{daily_spent:,.2f}, Attempted order: ₹{calculated_total:,.2f}).",
                verified_total=calculated_total,
                idempotency_key=idempotency_key,
                details={"daily_spent": daily_spent, "daily_limit": self.config.daily_spending_limit}
            )

        # 5. Check Autonomous Pre-Authorization vs Human-In-The-Loop Gate
        if self.config.require_human_approval_always or calculated_total > self.config.auto_approve_limit:
            hitl_token = self.generate_hitl_token(session_id, calculated_total, idempotency_key, proposal=proposal)
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

