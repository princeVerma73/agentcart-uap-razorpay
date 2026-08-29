import hashlib
import hmac
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from audit.ledger import audit_ledger
from main import app
from merchant.catalog import catalog_db
from merchant.growth_engine import growth_engine
from payments.razorpay_client import razorpay_service
from security.policy_engine import PolicyConfig, policy_engine


class FakeRazorpayOrderAPI:
    def create(self, data):
        return {
            "id": "order_test_lifecycle_123",
            "amount": data["amount"],
            "currency": data["currency"],
            "receipt": data["receipt"],
            "status": "created",
        }


class FakeRazorpayClient:
    order = FakeRazorpayOrderAPI()


@pytest.fixture(autouse=True)
def lifecycle_state():
    catalog_db.reset_catalog()
    audit_ledger.clear()
    policy_engine.update_config(PolicyConfig())
    policy_engine.processed_idempotency_keys.clear()
    razorpay_service._orders.clear()
    razorpay_service._verified_orders.clear()
    razorpay_service._payment_to_order.clear()
    razorpay_service._orders_by_idempotency.clear()
    original = (razorpay_service.mock_mode, razorpay_service.client, razorpay_service.key_id, razorpay_service.key_secret)
    razorpay_service.mock_mode = False
    razorpay_service.client = FakeRazorpayClient()
    razorpay_service.key_id = "rzp_test_public_key"
    razorpay_service.key_secret = "test_mode_secret"
    yield
    razorpay_service.mock_mode, razorpay_service.client, razorpay_service.key_id, razorpay_service.key_secret = original


from merchant.models import OrderProposal

def checkout_order(client, session_id="sess_lifecycle"):
    proposal_dict = {
        "merchant_id": "merchant_rzp_tech_01",
        "items": [{"product_id": "prod_mech_keyboard_k2", "quantity": 1, "unit_price": 6499.0, "name": "Mechanical Keyboard"}],
        "total_amount": 6499.0,
        "user_goal": "Buy mechanical keyboard",
    }
    proposal_obj = OrderProposal(**proposal_dict)
    verification = policy_engine.verify_order_proposal(session_id, proposal_obj)
    token = verification.hitl_token

    response = client.post("/api/agent/approve-hitl", json={
        "session_id": session_id,
        "proposal": proposal_dict,
        "verified_total": 6499.0,
        "hitl_token": token,
    })
    assert response.status_code == 200
    return response.json()


def payment_payload(session_id, order_id, payment_id="pay_test_lifecycle_456"):
    signature = hmac.new(
        b"test_mode_secret", f"{order_id}|{payment_id}".encode(), hashlib.sha256
    ).hexdigest()
    return {
        "session_id": session_id,
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": signature,
    }


def test_checkout_order_tracks_created_then_checkout_state():
    client = TestClient(app)
    session_id = "sess_created_checkout"
    payload = checkout_order(client, session_id)
    order_id = payload["order"]["id"]

    status_response = client.get(f"/api/orders/{order_id}", params={"session_id": session_id})

    assert payload["status"] == "PENDING_PAYMENT"
    assert status_response.status_code == 200
    assert status_response.json()["state"] == "checkout"
    states = [log.details.get("state") for log in audit_ledger.get_logs_by_session(session_id) if log.event_type == "ORDER_LIFECYCLE"]
    assert states == ["created", "checkout"]


def test_verified_payment_transitions_once_to_paid_and_captures_once():
    client = TestClient(app)
    session_id = "sess_paid_once"
    payload = checkout_order(client, session_id)
    verification = payment_payload(session_id, payload["order"]["id"])

    first = client.post("/api/payments/verify", json=verification)
    second = client.post("/api/payments/verify", json=verification)
    status = client.get(f"/api/orders/{payload['order']['id']}", params={"session_id": session_id})
    captured = [log for log in audit_ledger.get_logs_by_session(session_id) if log.event_type == "PAYMENT_CAPTURED"]

    assert first.status_code == 200
    assert second.status_code == 400
    assert status.json()["state"] == "paid"
    assert status.json()["payment_id"] == "pay_test_lifecycle_456"
    assert len(captured) == 1


def test_cancelled_checkout_cannot_be_verified_or_settled():
    client = TestClient(app)
    session_id = "sess_cancelled"
    payload = checkout_order(client, session_id)
    order_id = payload["order"]["id"]

    cancellation = client.post("/api/payments/checkout-failed", json={
        "session_id": session_id,
        "razorpay_order_id": order_id,
        "reason": "cancelled",
    })
    verification = client.post("/api/payments/verify", json=payment_payload(session_id, order_id))
    status = client.get(f"/api/orders/{order_id}", params={"session_id": session_id})

    assert cancellation.status_code == 200
    assert cancellation.json()["order"]["state"] == "cancelled"
    assert verification.status_code == 400
    assert status.json()["failure_reason"] == "cancelled"
    assert not [log for log in audit_ledger.get_logs_by_session(session_id) if log.event_type == "PAYMENT_CAPTURED"]


def test_lifecycle_status_and_failure_are_session_bound():
    client = TestClient(app)
    payload = checkout_order(client, "sess_owner")
    order_id = payload["order"]["id"]

    status = client.get(f"/api/orders/{order_id}", params={"session_id": "sess_other"})
    failure = client.post("/api/payments/checkout-failed", json={
        "session_id": "sess_other",
        "razorpay_order_id": order_id,
        "reason": "failed",
    })

    assert status.status_code == 403
    assert failure.status_code == 400
    assert razorpay_service._orders[order_id]["state"] == "checkout"


def test_failed_checkout_is_terminal_and_is_audited():
    client = TestClient(app)
    session_id = "sess_failed"
    payload = checkout_order(client, session_id)
    order_id = payload["order"]["id"]

    failed = client.post("/api/payments/checkout-failed", json={
        "session_id": session_id, "razorpay_order_id": order_id, "reason": "failed",
    })

    assert failed.status_code == 200
    assert failed.json()["order"]["state"] == "failed"
    states = [log.details.get("state") for log in audit_ledger.get_logs_by_session(session_id) if log.event_type == "ORDER_LIFECYCLE"]
    assert states == ["created", "checkout", "failed"]
    assert client.post("/api/payments/verify", json=payment_payload(session_id, order_id)).status_code == 400


def test_provider_status_is_checked_when_the_real_client_exposes_payment_api():
    class PaymentAPI:
        def fetch(self, payment_id):
            return {"id": payment_id, "order_id": "wrong_order", "amount": 649900, "currency": "INR", "status": "captured"}

    client = TestClient(app)
    payload = checkout_order(client, "sess_provider_check")
    razorpay_service.client.payment = PaymentAPI()

    response = client.post("/api/payments/verify", json=payment_payload("sess_provider_check", payload["order"]["id"]))

    assert response.status_code == 400
    assert razorpay_service._orders[payload["order"]["id"]]["state"] == "checkout"


def test_mock_settlement_is_single_use_and_revenue_is_not_duplicated():
    razorpay_service.mock_mode = True
    razorpay_service.client = None
    session_id = "sess_single_settlement"
    order = razorpay_service.create_order(session_id, 799.0, "rcpt_single", idempotency_key="idem_single")

    first = razorpay_service.simulate_payment_settlement(session_id, order["id"], 799.0)
    with pytest.raises(ValueError, match="cannot be settled again"):
        razorpay_service.simulate_payment_settlement(session_id, order["id"], 799.0)

    captured = [log for log in audit_ledger.get_logs_by_session(session_id) if log.event_type == "PAYMENT_CAPTURED"]
    assert len(captured) == 1
    assert first["razorpay_order_id"] == order["id"]
    assert growth_engine.calculate_metrics()["total_revenue"] == 799.0
