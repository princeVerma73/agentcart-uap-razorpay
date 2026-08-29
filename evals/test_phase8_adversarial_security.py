import hashlib
import hmac
import json
import os
import sys
import time
import pytest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from main import app
from config import settings
from audit.ledger import audit_ledger
from merchant.catalog import catalog_db
from merchant.models import OrderProposal, CartItem
from payments.razorpay_client import razorpay_service, verify_webhook_signature
from security.policy_engine import policy_engine, PolicyConfig

@pytest.fixture(autouse=True)
def reset_system_state():
    catalog_db.reset_catalog()
    audit_ledger.clear()
    policy_engine.update_config(PolicyConfig(
        max_single_transaction_limit=10000.0,
        auto_approve_limit=3000.0,
        require_human_approval_always=False,
        idempotency_window_seconds=300
    ))
    policy_engine.processed_idempotency_keys.clear()
    razorpay_service._orders.clear()
    razorpay_service._verified_orders.clear()
    razorpay_service._payment_to_order.clear()
    razorpay_service._orders_by_idempotency.clear()
    original_mock = razorpay_service.mock_mode
    razorpay_service.mock_mode = True
    yield
    razorpay_service.mock_mode = original_mock


# 1. Missing HITL Token
def test_adversarial_missing_hitl_token():
    client = TestClient(app)
    session_id = "sess_adv_missing_token"
    proposal = {
        "merchant_id": "merchant_rzp_tech_01",
        "items": [{"product_id": "prod_mech_keyboard_k2", "quantity": 1, "unit_price": 6499.0, "name": "Mechanical Keyboard"}],
        "total_amount": 6499.0,
        "user_goal": "Buy mechanical keyboard"
    }
    response = client.post("/api/agent/approve-hitl", json={
        "session_id": session_id,
        "proposal": proposal,
        "verified_total": 6499.0,
        "hitl_token": ""
    })
    assert response.status_code == 403
    assert "missing" in response.json()["detail"].lower()
    logs = audit_ledger.get_logs_by_session(session_id)
    assert any(log.event_type == "HITL_REJECTED" for log in logs)


# 2. Invalid HITL Token
def test_adversarial_invalid_hitl_token():
    client = TestClient(app)
    session_id = "sess_adv_invalid_token"
    proposal = {
        "merchant_id": "merchant_rzp_tech_01",
        "items": [{"product_id": "prod_mech_keyboard_k2", "quantity": 1, "unit_price": 6499.0, "name": "Mechanical Keyboard"}],
        "total_amount": 6499.0,
        "user_goal": "Buy mechanical keyboard"
    }
    response = client.post("/api/agent/approve-hitl", json={
        "session_id": session_id,
        "proposal": proposal,
        "verified_total": 6499.0,
        "hitl_token": "forged_invalid_hmac_token_999"
    })
    assert response.status_code == 403
    assert "invalid" in response.json()["detail"].lower()


# 3. Expired HITL Token
def test_adversarial_expired_hitl_token():
    client = TestClient(app)
    session_id = "sess_adv_expired_token"
    proposal = {
        "merchant_id": "merchant_rzp_tech_01",
        "items": [{"product_id": "prod_mech_keyboard_k2", "quantity": 1, "unit_price": 6499.0, "name": "Mechanical Keyboard"}],
        "total_amount": 6499.0,
        "user_goal": "Buy mechanical keyboard"
    }
    proposal_obj = OrderProposal(**proposal)
    verification = policy_engine.verify_order_proposal(session_id, proposal_obj)
    
    # Generate token that expired in the past
    past_timestamp = int(time.time() - 600)
    expired_token = policy_engine.generate_hitl_token(
        session_id=session_id,
        verified_total=verification.verified_total,
        idempotency_key=verification.idempotency_key,
        proposal=proposal_obj,
        expires_at=past_timestamp
    )
    response = client.post("/api/agent/approve-hitl", json={
        "session_id": session_id,
        "proposal": proposal,
        "verified_total": 6499.0,
        "hitl_token": expired_token
    })
    assert response.status_code == 403
    assert "expired" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()


# 4. HITL Token from Another Session
def test_adversarial_cross_session_hitl_token():
    client = TestClient(app)
    session_a = "sess_adv_session_a"
    session_b = "sess_adv_session_b"
    proposal = {
        "merchant_id": "merchant_rzp_tech_01",
        "items": [{"product_id": "prod_mech_keyboard_k2", "quantity": 1, "unit_price": 6499.0, "name": "Mechanical Keyboard"}],
        "total_amount": 6499.0,
        "user_goal": "Buy mechanical keyboard"
    }
    proposal_obj = OrderProposal(**proposal)
    verification_a = policy_engine.verify_order_proposal(session_a, proposal_obj)
    token_a = verification_a.hitl_token

    # Attempt to use token_a for session_b
    response = client.post("/api/agent/approve-hitl", json={
        "session_id": session_b,
        "proposal": proposal,
        "verified_total": 6499.0,
        "hitl_token": token_a
    })
    assert response.status_code == 403


# 5. HITL Token with Modified Amount
def test_adversarial_tampered_amount_hitl_token():
    client = TestClient(app)
    session_id = "sess_adv_tampered_amount"
    proposal = {
        "merchant_id": "merchant_rzp_tech_01",
        "items": [{"product_id": "prod_mech_keyboard_k2", "quantity": 1, "unit_price": 6499.0, "name": "Mechanical Keyboard"}],
        "total_amount": 6499.0,
        "user_goal": "Buy mechanical keyboard"
    }
    proposal_obj = OrderProposal(**proposal)
    verification = policy_engine.verify_order_proposal(session_id, proposal_obj)
    token = verification.hitl_token

    # Attempt to submit with lower claimed amount
    response = client.post("/api/agent/approve-hitl", json={
        "session_id": session_id,
        "proposal": proposal,
        "verified_total": 2499.0,
        "hitl_token": token
    })
    assert response.status_code == 400
    assert "mismatch" in response.json()["detail"].lower()


# 6. HITL Token Replay
def test_adversarial_hitl_token_replay():
    client = TestClient(app)
    session_id = "sess_adv_replay_token"
    proposal = {
        "merchant_id": "merchant_rzp_tech_01",
        "items": [{"product_id": "prod_mech_keyboard_k2", "quantity": 1, "unit_price": 6499.0, "name": "Mechanical Keyboard"}],
        "total_amount": 6499.0,
        "user_goal": "Buy mechanical keyboard"
    }
    proposal_obj = OrderProposal(**proposal)
    verification = policy_engine.verify_order_proposal(session_id, proposal_obj)
    token = verification.hitl_token

    # First approval -> SUCCESS
    res1 = client.post("/api/agent/approve-hitl", json={
        "session_id": session_id,
        "proposal": proposal,
        "verified_total": 6499.0,
        "hitl_token": token
    })
    assert res1.status_code == 200

    # Second approval attempt with same token -> REJECTED (Replay Protection)
    res2 = client.post("/api/agent/approve-hitl", json={
        "session_id": session_id,
        "proposal": proposal,
        "verified_total": 6499.0,
        "hitl_token": token
    })
    assert res2.status_code in {400, 403}


# 7. Client Attempts to Lower Product Price
def test_adversarial_client_price_tampering():
    session_id = "sess_adv_price_tamper"
    # Catalog price for 4K HDMI cable is 799.0; client claims 99.0
    tampered_proposal = OrderProposal(
        merchant_id="merchant_rzp_tech_01",
        items=[CartItem(product_id="prod_hdmi_cable_4k", quantity=1, unit_price=99.0, name="HDMI Cable (Hacked)")],
        total_amount=99.0,
        user_goal="Buy cheap cable"
    )
    result = policy_engine.verify_order_proposal(session_id, tampered_proposal)
    assert result.is_valid is True
    # Verified total must be overridden with authoritative DB price
    assert result.verified_total == 799.0
    logs = audit_ledger.get_logs_by_session(session_id)
    assert any("price discrepancy" in log.summary.lower() or "price" in log.summary.lower() for log in logs)


# 8. Client Attempts Malicious Quantity (0 or Negative or Insufficient Stock)
def test_adversarial_malicious_quantity():
    session_id = "sess_adv_qty"
    # Requested 9999 units when stock is 25
    proposal = OrderProposal(
        merchant_id="merchant_rzp_tech_01",
        items=[CartItem(product_id="prod_hdmi_cable_4k", quantity=9999, unit_price=799.0, name="HDMI Cable")],
        total_amount=799.0 * 9999,
        user_goal="Buy all inventory"
    )
    result = policy_engine.verify_order_proposal(session_id, proposal)
    assert result.is_valid is False
    assert result.status in {"REJECTED_STOCK_ERROR", "REJECTED_OVER_BUDGET"}


# 9. Client Attempts to Exceed ₹10,000 Hard Spending Cap
def test_adversarial_spending_ceiling_breach():
    session_id = "sess_adv_cap_breach"
    proposal = OrderProposal(
        merchant_id="merchant_rzp_tech_01",
        items=[CartItem(product_id="prod_mx_master_3s", quantity=2, unit_price=8995.0, name="MX Master 3S")],
        total_amount=17990.0,
        user_goal="Buy 2 mice"
    )
    result = policy_engine.verify_order_proposal(session_id, proposal)
    assert result.is_valid is False
    assert result.status == "REJECTED_OVER_BUDGET"
    assert result.verified_total > 10000.0


# 10. Client Attempts to Modify Policy Threshold Beyond Server Limits
def test_adversarial_policy_threshold_override():
    client = TestClient(app)
    # Attempt to set auto_approve_limit to ₹8,000 (exceeding ₹3,000 ceiling)
    res1 = client.post("/api/policy", json={
        "auto_approve_limit": 8000.0,
        "max_single_transaction_limit": 10000.0,
        "allowed_categories": ["accessories"],
        "require_human_approval_always": False,
        "enforce_stock_check": True,
        "idempotency_window_seconds": 300
    })
    assert res1.status_code in {400, 422}
    assert "cannot exceed immutable" in res1.text.lower()

    # Attempt to set max_single_transaction_limit to ₹50,000 (exceeding ₹10,000 hard cap)
    res2 = client.post("/api/policy", json={
        "auto_approve_limit": 2000.0,
        "max_single_transaction_limit": 50000.0,
        "allowed_categories": ["accessories"],
        "require_human_approval_always": False,
        "enforce_stock_check": True,
        "idempotency_window_seconds": 300
    })
    assert res2.status_code in {400, 422}
    assert "cannot exceed immutable" in res2.text.lower()


# 11. LLM Attempts to Influence Financial Price
def test_adversarial_llm_price_hallucination():
    session_id = "sess_adv_llm_price"
    # LLM hallucinates that Keychron K2 is ₹1,000 instead of ₹6,499
    proposal = OrderProposal(
        merchant_id="merchant_rzp_tech_01",
        items=[CartItem(product_id="prod_mech_keyboard_k2", quantity=1, unit_price=1000.0, name="Keychron K2")],
        total_amount=1000.0,
        user_goal="Buy Keychron for 1000"
    )
    result = policy_engine.verify_order_proposal(session_id, proposal)
    assert result.is_valid is True
    # Server policy engine re-anchors price to ₹6,499, triggering HITL
    assert result.verified_total == 6499.0
    assert result.status == "HITL_REQUIRED"


# 12. LLM Attempts to Approve Transaction Directly
def test_adversarial_llm_cannot_bypass_policy_gate():
    # Only server-side policy engine verification status can authorize order creation
    session_id = "sess_adv_llm_bypass"
    unauthorized_proposal = OrderProposal(
        merchant_id="merchant_rzp_tech_01",
        items=[CartItem(product_id="prod_mech_keyboard_k2", quantity=1, unit_price=6499.0, name="Keychron K2")],
        total_amount=6499.0,
        user_goal="Buy keyboard"
    )
    # Verification returns HITL_REQUIRED; no autonomous order creation allowed without HITL sign-off
    result = policy_engine.verify_order_proposal(session_id, unauthorized_proposal)
    assert result.status == "HITL_REQUIRED"
    assert result.requires_human_signature is True


# 13. Out-of-Stock Item Immediately Before Checkout
def test_adversarial_stockout_before_checkout():
    session_id = "sess_adv_stockout_checkout"
    catalog_db.simulate_stock_depletion("prod_mech_keyboard_k2")
    proposal = OrderProposal(
        merchant_id="merchant_rzp_tech_01",
        items=[CartItem(product_id="prod_mech_keyboard_k2", quantity=1, unit_price=6499.0, name="Keychron K2")],
        total_amount=6499.0,
        user_goal="Buy depleted item"
    )
    result = policy_engine.verify_order_proposal(session_id, proposal)
    assert result.is_valid is False
    assert result.status == "REJECTED_STOCK_ERROR"


# 14. Price Changes Immediately Before Checkout
def test_adversarial_price_surge_before_checkout():
    session_id = "sess_adv_price_surge"
    # Surge price from ₹799 to ₹1,499
    catalog_db.simulate_price_surge("prod_hdmi_cable_4k", 1499.0)
    proposal = OrderProposal(
        merchant_id="merchant_rzp_tech_01",
        items=[CartItem(product_id="prod_hdmi_cable_4k", quantity=1, unit_price=799.0, name="HDMI Cable")],
        total_amount=799.0,
        user_goal="Buy cable"
    )
    result = policy_engine.verify_order_proposal(session_id, proposal)
    assert result.is_valid is True
    assert result.verified_total == 1499.0


# 15. Payment Amount Mismatch
def test_adversarial_payment_amount_mismatch():
    session_id = "sess_adv_amt_mismatch"
    order = razorpay_service.create_order(session_id, 2499.0, "rcpt_mismatch")
    # Simulate payment settlement with incorrect amount
    with pytest.raises(ValueError, match="amount does not match"):
        razorpay_service.simulate_payment_settlement(session_id, order["id"], 100.0)


# 16. Payment / Order ID Mismatch
def test_adversarial_payment_order_id_mismatch():
    client = TestClient(app)
    response = client.get("/api/orders/order_non_existent_id", params={"session_id": "sess_adv_order_mismatch"})
    assert response.status_code in {400, 404}


# 17. Invalid Webhook Signature
def test_adversarial_invalid_webhook_signature():
    client = TestClient(app)
    settings.RAZORPAY_WEBHOOK_SECRET = "secret_webhook_test"
    payload = json.dumps({"event": "payment.captured", "payload": {}}).encode()
    response = client.post(
        "/api/payments/webhook",
        content=payload,
        headers={"X-Razorpay-Signature": "invalid_forged_signature_12345", "Content-Type": "application/json"}
    )
    assert response.status_code == 401
    assert "invalid razorpay webhook signature" in response.json()["detail"].lower()


# 18. Duplicate Webhook / Event
def test_adversarial_duplicate_webhook_event():
    client = TestClient(app)
    settings.RAZORPAY_WEBHOOK_SECRET = "secret_webhook_test"
    order_id = "order_adv_webhook_dup"
    razorpay_service._orders[order_id] = {
        "session_id": "sess_adv_webhook",
        "amount": 79900,
        "currency": "INR",
        "verified": False,
        "settled": False,
        "state": "checkout"
    }
    payload_dict = {
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay_adv_dup_1", "order_id": order_id, "amount": 79900, "currency": "INR"}}}
    }
    raw_payload = json.dumps(payload_dict, separators=(",", ":")).encode()
    signature = hmac.new(b"secret_webhook_test", raw_payload, hashlib.sha256).hexdigest()
    headers = {
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": "evt_unique_12345",
        "Content-Type": "application/json"
    }

    # First webhook -> Reconciled (200)
    res1 = client.post("/api/payments/webhook", content=raw_payload, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["status"] == "reconciled"

    # Duplicate webhook with same event ID -> Duplicate ignored (200, status=duplicate)
    res2 = client.post("/api/payments/webhook", content=raw_payload, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["status"] == "duplicate"


# 19. Duplicate Order Submission (Idempotency Replay)
def test_adversarial_duplicate_order_submission():
    session_id = "sess_adv_dup_submission"
    proposal = OrderProposal(
        merchant_id="merchant_rzp_tech_01",
        items=[CartItem(product_id="prod_hdmi_cable_4k", quantity=1, unit_price=799.0, name="HDMI Cable")],
        total_amount=799.0,
        user_goal="Buy cable"
    )
    res1 = policy_engine.verify_order_proposal(session_id, proposal)
    assert res1.is_valid is True
    policy_engine.mark_key_processed(res1.idempotency_key, session_id=session_id)

    # Immediate identical submission
    res2 = policy_engine.verify_order_proposal(session_id, proposal)
    assert res2.is_valid is False
    assert res2.status == "REJECTED_DUPLICATE"


# 20. Cross-Session Order Replay / Checkout Hijack
def test_adversarial_cross_session_order_hijack():
    session_owner = "sess_adv_owner"
    session_attacker = "sess_adv_attacker"
    order = razorpay_service.create_order(session_owner, 799.0, "rcpt_owner")
    
    # Attacker attempts to check status of victim's order
    with pytest.raises(ValueError, match="does not belong to this session"):
        razorpay_service.order_status(session_attacker, order["id"])

    # Attacker attempts to fail victim's order
    with pytest.raises(ValueError, match="does not belong to this session"):
        razorpay_service.fail_checkout(session_attacker, order["id"], "cancelled")
