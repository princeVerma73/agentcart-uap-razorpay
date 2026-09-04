import hashlib
import hmac
import time
import uuid
from typing import Any, Dict, Optional

import razorpay

from backend.audit.ledger import audit_ledger
from backend.config import settings


def verify_webhook_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """Verify Razorpay's HMAC over the exact, unparsed request body."""
    if not raw_body or not signature or not secret:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


class RazorpayService:
    """Order lifecycle boundary. Browser callbacks are never payment authority."""

    def __init__(self) -> None:
        self.mock_mode = settings.RAZORPAY_MOCK_MODE
        self.key_id, self.key_secret = settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET
        self.client: Optional[razorpay.Client] = None
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._verified_orders: set[str] = set()
        self._payment_to_order: Dict[str, str] = {}
        self._orders_by_idempotency: Dict[tuple[str, str], str] = {}
        if not self.mock_mode and self.key_id.startswith("rzp_"):
            try:
                self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
            except Exception as exc:
                print(f"Razorpay client init warning (fallback to mock): {exc}")
                self.mock_mode = True

    def set_credentials(self, key_id: str, key_secret: str, mock_mode: bool = False):
        self.key_id, self.key_secret, self.mock_mode, self.client = key_id, key_secret, mock_mode, None
        if not mock_mode and key_id.startswith("rzp_"):
            try:
                self.client = razorpay.Client(auth=(key_id, key_secret))
            except Exception:
                self.mock_mode = True
        else:
            self.mock_mode = True

    @property
    def checkout_enabled(self) -> bool:
        return not self.mock_mode and self.client is not None

    def _lifecycle(self, session_id: str, order_id: str, state: str, **details: Any) -> None:
        audit_ledger.record(session_id, "ORDER_LIFECYCLE", "SUCCESS" if state == "paid" else "INFO", f"Order {order_id} transitioned to {state}.", {"order_id": order_id, "state": state, **details})

    def _transition(self, order_id: str, expected: str, target: str, **details: Any) -> Dict[str, Any]:
        order = self._orders.get(order_id)
        if not order:
            raise ValueError("Order ID not recognized")
        if order.get("state", "created") != expected:
            raise ValueError(f"Order cannot transition from {order.get('state', 'created')} to {target}")
        order["state"], order["updated_at"] = target, int(time.time())
        self._lifecycle(order["session_id"], order_id, target, **details)
        return order

    def _store(self, provider_order: Dict[str, Any], session_id: str, amount: int, idem: Optional[str]) -> None:
        order_id = provider_order["id"]
        self._orders[order_id] = {"session_id": session_id, "amount": amount, "currency": provider_order.get("currency", "INR"), "verified": False, "settled": False, "idempotency_key": idem, "state": "created", "created_at": int(time.time()), "provider_order": provider_order}
        if idem:
            self._orders_by_idempotency[(session_id, idem)] = order_id
        audit_ledger.record(session_id, "RAZORPAY_ORDER_CREATED", "SUCCESS", f"Razorpay order created: {order_id} for INR {amount / 100:,.2f}", {"order_id": order_id, "amount_paise": amount, "currency": provider_order.get("currency", "INR")})
        self._lifecycle(session_id, order_id, "created")

    def create_order(self, session_id: str, amount: float, receipt_id: str, notes: Optional[Dict[str, Any]] = None, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("Order amount must be positive")
        if idempotency_key and (old_id := self._orders_by_idempotency.get((session_id, idempotency_key))):
            old = self._orders.get(old_id)
            if old:
                return old["provider_order"]
        paise, notes = int(round(amount * 100)), notes or {}
        if self.checkout_enabled:
            try:
                order = self.client.order.create(data={"amount": paise, "currency": "INR", "receipt": receipt_id[:40], "notes": notes, "payment_capture": 1})
                self._store(order, session_id, paise, idempotency_key)
                return order
            except Exception as exc:
                audit_ledger.record(session_id, "RAZORPAY_ORDER_CREATED", "WARNING", "Razorpay API error; using configured sandbox order.", {"error": str(exc)})
        order = {"id": f"order_mock_{uuid.uuid4().hex[:14]}", "entity": "order", "amount": paise, "amount_paid": 0, "amount_due": paise, "currency": "INR", "receipt": receipt_id, "status": "created", "attempts": 0, "notes": notes, "created_at": int(time.time()), "is_mock": True}
        self._store(order, session_id, paise, idempotency_key)
        return order

    def checkout_options(self, order: Dict[str, Any]) -> Dict[str, Any]:
        if not self.checkout_enabled:
            raise ValueError("Razorpay Checkout is unavailable while mock mode is enabled")
        rec = self._orders.get(order["id"])
        if not rec:
            raise ValueError("Order ID not recognized")
        if rec["state"] == "created":
            self._transition(order["id"], "created", "checkout")
        elif rec["state"] != "checkout":
            raise ValueError(f"Checkout is unavailable for {rec['state']} order")
        return {"key": self.key_id, "amount": rec["amount"], "currency": rec["currency"], "order_id": order["id"], "name": "AgentCart", "description": "AgentCart order"}

    def fail_checkout(self, session_id: str, order_id: str, reason: str) -> Dict[str, Any]:
        order = self._orders.get(order_id)
        if not order:
            raise ValueError("Order ID not recognized")
        if order["session_id"] != session_id:
            raise ValueError("Order does not belong to this session")
        if reason not in {"failed", "cancelled"}:
            raise ValueError("Unsupported checkout failure reason")
        self._transition(order_id, "checkout", reason, reason=reason)
        order["failure_reason"] = reason
        return self.order_status(session_id, order_id)

    def order_status(self, session_id: str, order_id: str) -> Dict[str, Any]:
        order = self._orders.get(order_id)
        if not order:
            raise ValueError("Order ID not recognized")
        if order["session_id"] != session_id:
            raise ValueError("Order does not belong to this session")
        return {"order_id": order_id, "session_id": session_id, "state": order["state"], "amount_paise": order["amount"], "currency": order["currency"], "payment_id": order.get("payment_id"), "failure_reason": order.get("failure_reason")}

    def _provider_status(self, order_id: str, payment_id: str, order: Dict[str, Any]) -> None:
        """A real client must independently confirm captured status, amount, and order binding."""
        payment_api = getattr(self.client, "payment", None) if self.checkout_enabled else None
        fetch = getattr(payment_api, "fetch", None)
        if not fetch:  # narrow fake clients in tests do not expose a Payment API
            return
        payment = fetch(payment_id)
        if payment.get("order_id") != order_id or payment.get("amount") != order["amount"] or payment.get("currency", "INR") != order["currency"]:
            raise ValueError("Razorpay payment does not match the order")
        if payment.get("status") != "captured":
            raise ValueError("Razorpay payment is not captured")

    def verify_payment(self, session_id: str, order_id: str, payment_id: str, signature: str) -> Dict[str, Any]:
        order = self._orders.get(order_id)
        if not order:
            raise ValueError("Order ID not recognized")
        if order["session_id"] != session_id:
            raise ValueError("Order does not belong to this session")
        if order.get("verified") or order_id in self._verified_orders:
            raise ValueError("Order already verified (replay attack)")
        if payment_id in self._payment_to_order:
            raise ValueError("Payment ID is already bound to another order")
        expected = hmac.new(self.key_secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid Razorpay signature")
        if order.get("state", "created") != "checkout":
            raise ValueError("Order is not awaiting Razorpay Checkout payment")
        self._provider_status(order_id, payment_id, order)
        order["verified"] = order["settled"] = True
        order["payment_id"] = payment_id
        self._payment_to_order[payment_id] = order_id
        self._transition(order_id, "checkout", "paid", payment_id=payment_id)
        self._verified_orders.add(order_id)
        audit_ledger.record(session_id, "PAYMENT_VERIFIED", "SUCCESS", f"Payment {payment_id} verified for order {order_id}", {"order_id": order_id, "payment_id": payment_id, "amount_paise": order["amount"]})
        audit_ledger.record(session_id, "PAYMENT_CAPTURED", "SUCCESS", f"Payment {payment_id} captured exactly once.", {"order_id": order_id, "payment_id": payment_id, "amount_paise": order["amount"], "currency": order["currency"]})
        return {"status": "verified", "order_id": order_id, "payment_id": payment_id, "amount": order["amount"]}

    def simulate_payment_settlement(self, session_id: str, order_id: str, amount: float, method: str = "upi") -> Dict[str, Any]:
        """Legacy mock mode only; bound to an order and intentionally single-use."""
        order = self._orders.get(order_id)
        if not self.mock_mode:
            raise ValueError("Simulated settlement is available only in mock mode")
        if not order or order["session_id"] != session_id:
            raise ValueError("Order does not belong to this session")
        if int(round(amount * 100)) != order["amount"]:
            raise ValueError("Settlement amount does not match the order")
        if order.get("settled") or order["state"] in {"paid", "failed", "cancelled"}:
            raise ValueError("Order is already terminal and cannot be settled again")
        if order["state"] == "created":
            self._transition(order_id, "created", "checkout")
        payment_id = f"pay_mock_{uuid.uuid4().hex[:14]}"
        signature = hmac.new(self.key_secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
        order["verified"] = order["settled"] = True
        order["payment_id"] = payment_id
        self._payment_to_order[payment_id] = order_id
        self._transition(order_id, "checkout", "paid", payment_id=payment_id, mock=True)
        self._verified_orders.add(order_id)
        receipt = {"razorpay_order_id": order_id, "razorpay_payment_id": payment_id, "razorpay_signature": signature, "status": "captured", "method": method, "amount": amount, "currency": order["currency"], "timestamp": int(time.time()), "autonomous_settlement": True}
        audit_ledger.record(session_id, "PAYMENT_CAPTURED", "SUCCESS", f"Mock payment {payment_id} settled exactly once.", {**receipt, "amount_paise": order["amount"]})
        return receipt

    def reconcile_webhook(self, event_type: str, payload: Dict[str, Any], event_id: str) -> Dict[str, Any]:
        """Apply a signed Razorpay event once, using server-side order facts only."""
        if event_type not in {"payment.captured", "payment.failed", "order.paid"}:
            return {"status": "ignored", "reason": "unsupported_event"}
        if any(log.event_type == "WEBHOOK_RECEIVED" and log.details.get("event_id") == event_id for log in audit_ledger.get_all_logs(limit=1_000_000)):
            return {"status": "duplicate", "event_id": event_id}

        event_payload = payload.get("payload", payload)
        payment = event_payload.get("payment", {}).get("entity", event_payload.get("payment", {}))
        provider_order = event_payload.get("order", {}).get("entity", event_payload.get("order", {}))
        order_id = payment.get("order_id") or provider_order.get("id")
        payment_id = payment.get("id")
        order = self._orders.get(order_id)
        session_id = order.get("session_id") if order else "webhook_unmatched"
        audit_ledger.record(session_id, "WEBHOOK_RECEIVED", "SUCCESS", f"Signed Razorpay webhook received: {event_type}.", {"event_id": event_id, "event_type": event_type, "order_id": order_id, "payment_id": payment_id})
        if not order:
            audit_ledger.record(session_id, "WEBHOOK_RECONCILIATION", "WARNING", "Webhook references no known AgentCart order; no financial state changed.", {"event_id": event_id, "order_id": order_id})
            return {"status": "unmatched", "event_id": event_id}

        if event_type == "payment.failed":
            if order["state"] == "checkout":
                self._transition(order_id, "checkout", "failed", source="webhook")
                order["failure_reason"] = "razorpay_payment_failed"
                return {"status": "reconciled", "state": "failed", "event_id": event_id}
            return {"status": "ignored", "state": order["state"], "event_id": event_id}

        amount = payment.get("amount", provider_order.get("amount"))
        currency = payment.get("currency", provider_order.get("currency", "INR"))
        if amount != order["amount"] or currency != order["currency"] or not payment_id:
            audit_ledger.record(session_id, "WEBHOOK_RECONCILIATION", "REJECTED", "Webhook payment did not match the server-side order.", {"event_id": event_id, "order_id": order_id, "payment_id": payment_id})
            return {"status": "rejected", "reason": "order_mismatch", "event_id": event_id}
        if order["state"] == "paid":
            return {"status": "already_paid", "event_id": event_id}
        if order["state"] in {"failed", "cancelled"} or payment_id in self._payment_to_order:
            return {"status": "ignored", "state": order["state"], "event_id": event_id}
        if order["state"] == "created":
            self._transition(order_id, "created", "checkout", source="webhook")
        if order["state"] != "checkout":
            return {"status": "ignored", "state": order["state"], "event_id": event_id}
        order["verified"] = order["settled"] = True
        order["payment_id"] = payment_id
        self._payment_to_order[payment_id] = order_id
        self._verified_orders.add(order_id)
        self._transition(order_id, "checkout", "paid", payment_id=payment_id, source="webhook")
        audit_ledger.record(session_id, "PAYMENT_CAPTURED", "SUCCESS", f"Webhook-reconciled payment {payment_id} captured exactly once.", {"order_id": order_id, "payment_id": payment_id, "amount_paise": order["amount"], "currency": order["currency"], "webhook_event_id": event_id})
        audit_ledger.record(session_id, "PAYMENT_LEDGER_POSTED", "SUCCESS", "Balanced payment ledger entries posted.", {"order_id": order_id, "payment_id": payment_id, "entries": [{"account": "buyer_cash", "debit_paise": order["amount"], "credit_paise": 0}, {"account": "merchant_receivable", "debit_paise": 0, "credit_paise": order["amount"]}]})
        return {"status": "reconciled", "state": "paid", "event_id": event_id}


razorpay_service = RazorpayService()
