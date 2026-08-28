import hashlib
import hmac
import json
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.dirname(__file__))

from audit.ledger import audit_ledger
from config import settings
from main import app
from merchant.analytics import merchant_analytics
from merchant.catalog import catalog_db
from payments.razorpay_client import razorpay_service, verify_webhook_signature
from security.policy_engine import PolicyConfig, policy_engine


@pytest.fixture(autouse=True)
def phase7_state():
    audit_ledger.clear()
    catalog_db.reset_catalog()
    policy_engine.update_config(PolicyConfig())
    policy_engine.processed_idempotency_keys.clear()
    razorpay_service._orders.clear()
    razorpay_service._verified_orders.clear()
    razorpay_service._payment_to_order.clear()
    razorpay_service._orders_by_idempotency.clear()
    original_secret = settings.RAZORPAY_WEBHOOK_SECRET
    settings.RAZORPAY_WEBHOOK_SECRET = "phase7_webhook_secret"
    yield
    settings.RAZORPAY_WEBHOOK_SECRET = original_secret


def webhook_body(order_id="order_webhook_1", payment_id="pay_webhook_1", event="payment.captured"):
    return json.dumps({
        "event": event,
        "payload": {"payment": {"entity": {"id": payment_id, "order_id": order_id, "amount": 79900, "currency": "INR"}}},
    }, separators=(",", ":")).encode()


def signed_headers(body, event_id="evt_phase7_1"):
    return {
        "X-Razorpay-Signature": hmac.new(b"phase7_webhook_secret", body, hashlib.sha256).hexdigest(),
        "X-Razorpay-Event-Id": event_id,
        "Content-Type": "application/json",
    }


def test_evaluation_runner_metrics_consistency():
    from run_growth_evaluation import run_evaluation

    result = run_evaluation(500)
    values = [*result["baseline"].values(), *result["agentcart"].values()]
    assert result["baseline"]["sessions"] == 500
    assert all(not isinstance(value, float) or value == value for value in values)
    assert result["agentcart"]["net_incremental_revenue"] == pytest.approx(
        result["agentcart"]["revenue"] - result["baseline"]["revenue"]
    )


def test_webhook_signature_verification_success_and_tamper():
    body = webhook_body()
    signature = signed_headers(body)["X-Razorpay-Signature"]
    assert verify_webhook_signature(body, signature, "phase7_webhook_secret")
    assert not verify_webhook_signature(body + b" ", signature, "phase7_webhook_secret")

    response = TestClient(app).post("/api/payments/webhook", content=body + b" ", headers=signed_headers(body))
    assert response.status_code == 401


def test_webhook_idempotent_duplicate_handling():
    razorpay_service._orders["order_webhook_1"] = {
        "session_id": "sess_webhook", "amount": 79900, "currency": "INR", "verified": False,
        "settled": False, "state": "checkout",
    }
    body = webhook_body()
    client = TestClient(app)
    first = client.post("/api/payments/webhook", content=body, headers=signed_headers(body))
    second = client.post("/api/payments/webhook", content=body, headers=signed_headers(body))

    captured = [entry for entry in audit_ledger.get_logs_by_session("sess_webhook") if entry.event_type == "PAYMENT_CAPTURED"]
    ledger_entries = [entry for entry in audit_ledger.get_logs_by_session("sess_webhook") if entry.event_type == "PAYMENT_LEDGER_POSTED"]
    assert first.status_code == 200 and first.json()["status"] == "reconciled"
    assert second.status_code == 200 and second.json()["status"] == "duplicate"
    assert len(captured) == len(ledger_entries) == 1


def test_merchant_analytics_aggregation():
    audit_ledger.record("sess_growth", "PAYMENT_CAPTURED", "SUCCESS", "captured", {"order_id": "order_growth", "amount_paise": 150000})
    audit_ledger.record("sess_growth", "UPSELL_ACCEPTED", "SUCCESS", "upsell", {"incremental_revenue": 200.0})
    audit_ledger.record("sess_growth", "CROSS_SELL_ACCEPTED", "SUCCESS", "cross", {"incremental_revenue": 300.0})
    audit_ledger.record("sess_growth", "POLICY_CHECK", "SUCCESS", "approved", {})
    audit_ledger.record("sess_growth", "HITL_APPROVED", "SUCCESS", "approved", {})
    audit_ledger.record("sess_growth", "ERROR_RECOVERED", "SUCCESS", "recovered", {})

    analytics = merchant_analytics()
    response = TestClient(app).get("/api/merchant/analytics")
    assert analytics["gmv"] == 1500.0
    assert analytics["incremental_revenue"] == 500.0
    assert analytics["hitl_gate_ratio"] == 50.0
    assert analytics["failure_recoveries"] == 1
    assert response.status_code == 200 and response.json()["incremental_revenue"] == 500.0
