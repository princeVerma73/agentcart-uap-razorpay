import pytest
import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from merchant.catalog import catalog_db
from merchant.models import OrderProposal, CartItem
from security.policy_engine import policy_engine, PolicyConfig
from payments.razorpay_client import razorpay_service
from audit.ledger import audit_ledger
from agent.buyer_agent import buyer_agent

@pytest.fixture(autouse=True)
def reset_state():
    """Reset catalog, policy, and audit ledger before each test."""
    catalog_db.reset_catalog()
    policy_engine.update_config(PolicyConfig(
        max_single_transaction_limit=10000.0,
        auto_approve_limit=3000.0,
        require_human_approval_always=False
    ))
    audit_ledger.clear()
    policy_engine.processed_idempotency_keys.clear()

def test_autonomous_pre_auth_within_limits():
    """Test 1: Normal purchase within autonomous limit succeeds without human interruption."""
    session_id = "test_sess_01"
    proposal = OrderProposal(
        merchant_id="merchant_rzp_tech_01",
        items=[CartItem(product_id="prod_hdmi_cable_4k", quantity=2, unit_price=799.0, name="HDMI Cable")],
        total_amount=1598.0,
        user_goal="Buy 2 HDMI cables"
    )
    
    result = policy_engine.verify_order_proposal(session_id, proposal)
    assert result.is_valid is True
    assert result.status == "AUTO_APPROVED"
    assert result.requires_human_signature is False
    assert result.verified_total == 1598.0
    
    # Create order
    order = razorpay_service.create_order(session_id, result.verified_total, "rcpt_test_01")
    assert order["id"].startswith("order_")
    assert order["amount"] == 159800  # 1598 INR in paise

def test_human_in_the_loop_trigger_above_auto_limit():
    """Test 2: Purchase exceeding auto-limit (₹3,000) correctly triggers HITL approval gate."""
    session_id = "test_sess_02"
    proposal = OrderProposal(
        merchant_id="merchant_rzp_tech_01",
        items=[CartItem(product_id="prod_mech_keyboard_k2", quantity=1, unit_price=6499.0, name="Mechanical Keyboard")],
        total_amount=6499.0,
        user_goal="Buy Keychron Keyboard"
    )
    
    result = policy_engine.verify_order_proposal(session_id, proposal)
    assert result.is_valid is True
    assert result.status == "HITL_REQUIRED"
    assert result.requires_human_signature is True
    assert result.verified_total == 6499.0

def test_hard_spending_ceiling_rejection():
    """Test 3: Order exceeding absolute max limit (₹10,000) is strictly rejected."""
    session_id = "test_sess_03"
    proposal = OrderProposal(
        merchant_id="merchant_rzp_tech_01",
        items=[CartItem(product_id="prod_mx_master_3s", quantity=2, unit_price=8995.0, name="MX Master 3S")],
        total_amount=17990.0,
        user_goal="Buy 2 Logitech MX Master 3S mice"
    )
    
    result = policy_engine.verify_order_proposal(session_id, proposal)
    assert result.is_valid is False
    assert result.status == "REJECTED_OVER_BUDGET"

def test_anti_hallucination_price_enforcement():
    """Test 4: If LLM attempts to pass a lower price, the policy engine recalculates from true DB price."""
    session_id = "test_sess_04"
    proposal = OrderProposal(
        merchant_id="merchant_rzp_tech_01",
        items=[CartItem(product_id="prod_hdmi_cable_4k", quantity=1, unit_price=100.0, name="HDMI Cable (Fake Price)")],
        total_amount=100.0,  # True DB price is 799.0
        user_goal="Buy cheap HDMI cable"
    )
    
    result = policy_engine.verify_order_proposal(session_id, proposal)
    assert result.is_valid is True
    assert result.verified_total == 799.0  # Correctly overwritten with true DB price

def test_idempotency_replay_protection():
    """Test 5: Replaying an identical transaction is blocked."""
    session_id = "test_sess_05"
    proposal = OrderProposal(
        merchant_id="merchant_rzp_tech_01",
        items=[CartItem(product_id="prod_hdmi_cable_4k", quantity=1, unit_price=799.0, name="HDMI Cable")],
        total_amount=799.0,
        user_goal="Buy 1 HDMI cable"
    )
    
    result1 = policy_engine.verify_order_proposal(session_id, proposal)
    assert result1.is_valid is True
    policy_engine.mark_key_processed(result1.idempotency_key)
    
    # Try replaying
    result2 = policy_engine.verify_order_proposal(session_id, proposal)
    assert result2.is_valid is False
    assert result2.status == "REJECTED_DUPLICATE"

@pytest.mark.asyncio
async def test_agent_graceful_stockout_recovery():
    """Test 6: Live agent detects out-of-stock primary choice and autonomously substitutes in-stock alternative."""
    # Deplete stock of Keychron keyboard
    catalog_db.simulate_stock_depletion("prod_mech_keyboard_k2")
    
    session_id = "test_agent_sess_06"
    steps = []
    
    async for step in buyer_agent.run_goal_stream(session_id, "Buy a mechanical keyboard for office"):
        steps.append(step)
        
    # Verify that agent encountered stockout and recovered
    step_titles = [s["title"] for s in steps]
    assert any("Stockout Detected" in t or "Gracefully" in t for t in step_titles)
    
    # Verify audit logs captured the recovery
    logs = audit_ledger.get_logs_by_session(session_id)
    event_types = [l.event_type for l in logs]
    assert "ERROR_RECOVERED" in event_types

def test_cryptographic_audit_ledger_hashing():
    """Test 7: Audit log records tamper-evident cryptographic hashes for every step."""
    session_id = "test_audit_sess_07"
    entry = audit_ledger.record(
        session_id=session_id,
        event_type="POLICY_CHECK",
        status="SUCCESS",
        summary="Test audit entry",
        details={"foo": "bar"}
    )
    assert len(entry.cryptographic_hash) == 64  # Valid SHA-256 hex string
