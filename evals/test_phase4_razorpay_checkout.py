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
from payments.razorpay_client import razorpay_service
from security.policy_engine import PolicyConfig, policy_engine


class FakeRazorpayOrderAPI:
    def create(self, data):
        return {
            "id": "order_test_checkout_123",
            "amount": data["amount"],
            "currency": data["currency"],
            "receipt": data["receipt"],
            "status": "created",
        }


class FakeRazorpayClient:
    order = FakeRazorpayOrderAPI()


@pytest.fixture(autouse=True)
def test_mode_checkout_state():
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


def test_hitl_creates_public_checkout_and_verifies_signature():
    client = TestClient(app)
    session_id = "sess_phase4_checkout"
    proposal = {
        "merchant_id": "merchant_rzp_tech_01",
        "items": [{"product_id": "prod_mech_keyboard_k2", "quantity": 1, "unit_price": 6499.0, "name": "Mechanical Keyboard"}],
        "total_amount": 6499.0,
        "user_goal": "Buy mechanical keyboard",
    }

    order_response = client.post("/api/agent/approve-hitl", json={
        "session_id": session_id,
        "proposal": proposal,
        "verified_total": 6499.0,
    })

    assert order_response.status_code == 200
    payload = order_response.json()
    assert payload["status"] == "PENDING_PAYMENT"
    assert payload["checkout"]["key"] == "rzp_test_public_key"
    assert payload["checkout"]["order_id"] == "order_test_checkout_123"
    assert "test_mode_secret" not in order_response.text

    payment_id = "pay_test_checkout_456"
    signature = hmac.new(
        b"test_mode_secret",
        f"{payload['order']['id']}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    verification_response = client.post("/api/payments/verify", json={
        "session_id": session_id,
        "razorpay_order_id": payload["order"]["id"],
        "razorpay_payment_id": payment_id,
        "razorpay_signature": signature,
    })

    assert verification_response.status_code == 200
    assert verification_response.json()["status"] == "SUCCESS"
    assert razorpay_service._orders[payload["order"]["id"]]["verified"] is True
    assert policy_engine.processed_idempotency_keys


def test_checkout_rejects_invalid_signature():
    client = TestClient(app)
    razorpay_service._orders["order_test_invalid"] = {
        "session_id": "sess_invalid_signature",
        "amount": 100,
        "currency": "INR",
        "verified": False,
    }

    response = client.post("/api/payments/verify", json={
        "session_id": "sess_invalid_signature",
        "razorpay_order_id": "order_test_invalid",
        "razorpay_payment_id": "pay_invalid",
        "razorpay_signature": "not-a-valid-signature",
    })

    assert response.status_code == 400
    assert "invalid razorpay signature" in response.json()["detail"].lower()
