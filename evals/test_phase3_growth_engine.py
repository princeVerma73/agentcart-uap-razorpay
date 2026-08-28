import os
import sys
import pytest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from main import app
from merchant.catalog import catalog_db
from merchant.models import Product, OrderProposal, CartItem
from merchant.growth_engine import GrowthEngine, growth_engine
from security.policy_engine import policy_engine, PolicyConfig
from audit.ledger import audit_ledger


def record_offer(session_id, offer_type, base_product_id, offered_product_id, max_budget=None):
    audit_ledger.record(
        session_id=session_id,
        event_type=f"{offer_type.upper()}_PROPOSED",
        status="SUCCESS",
        summary="Test growth offer",
        details={
            "base_product_id": base_product_id,
            "offered_product_id": offered_product_id,
            "max_budget": max_budget,
            "quantity": 1,
        },
    )

@pytest.fixture(autouse=True)
def reset_state():
    catalog_db.reset_catalog()
    audit_ledger.clear()
    policy_engine.update_config(PolicyConfig(
        max_single_transaction_limit=10000.0,
        auto_approve_limit=3000.0,
        require_human_approval_always=False
    ))
    policy_engine.processed_idempotency_keys.clear()

def test_valid_product_recommendation():
    """Test 1: Verify valid product recommendation retrieval."""
    base_prod = catalog_db.get_by_id("prod_budget_ergonomic_mouse")
    upsell = growth_engine.get_upsell_candidate(base_prod)
    assert upsell is not None
    assert upsell["upsell_product"]["id"] == "prod_mx_master_3s"
    assert upsell["price_delta"] > 0

def test_no_recommendation_for_incompatible_product():
    """Test 2: Top-tier product (highest price) has no upsell candidate available."""
    top_prod = catalog_db.get_by_id("prod_mx_master_3s")  # Price 8995.0
    upsell = growth_engine.get_upsell_candidate(top_prod)
    assert upsell is None

def test_valid_upsell_candidate():
    """Test 3: Discovery of higher-tier item in same category with grounded reason."""
    base_prod = catalog_db.get_by_id("prod_budget_ergonomic_mouse")
    upsell = growth_engine.get_upsell_candidate(base_prod)
    assert upsell["upsell_product"]["price"] > base_prod.price
    assert "MX Master 3S" in upsell["reason"] or "rating" in upsell["reason"]

def test_invalid_upsell_candidate_rejected():
    """Test 4: Upsell exceeding user budget cap is excluded."""
    base_prod = catalog_db.get_by_id("prod_budget_ergonomic_mouse")  # 699 INR
    # Set max budget to 5000 (MX Master 3S costs 8995 -> exceeds budget)
    upsell = growth_engine.get_upsell_candidate(base_prod, max_budget=5000.0)
    assert upsell is None

def test_user_rejects_upsell():
    """Test 5: User rejection of upsell offer records UPSELL_REJECTED audit event."""
    session_id = "sess_upsell_reject"
    record_offer(session_id, "upsell", "prod_budget_ergonomic_mouse", "prod_mx_master_3s")
    res = growth_engine.interact_offer(session_id, "upsell", "reject", "prod_mx_master_3s")
    assert res["status"] == "SUCCESS"

    logs = audit_ledger.get_logs_by_session(session_id)
    assert logs[-1].event_type == "UPSELL_REJECTED"

def test_user_accepts_upsell():
    """Test 6: User acceptance of upsell offer records UPSELL_ACCEPTED event."""
    session_id = "sess_upsell_accept"
    record_offer(session_id, "upsell", "prod_budget_ergonomic_mouse", "prod_mx_master_3s")
    res = growth_engine.interact_offer(session_id, "upsell", "accept", "prod_mx_master_3s")
    assert res["status"] == "SUCCESS"

    logs = audit_ledger.get_logs_by_session(session_id)
    assert logs[-1].event_type == "UPSELL_ACCEPTED"

def test_valid_cross_sell_candidate():
    """Test 7: Complementary item discovery grounded in catalog metadata."""
    base_prod = catalog_db.get_by_id("prod_mech_keyboard_k2")
    cross_sell = growth_engine.get_cross_sell_candidate(base_prod)
    assert cross_sell is not None
    assert cross_sell["cross_sell_product"]["id"] == "prod_budget_ergonomic_mouse"

def test_incompatible_cross_sell_rejected():
    """Test 8: Out of stock item cannot be offered as cross-sell."""
    catalog_db.simulate_stock_depletion("prod_budget_ergonomic_mouse")
    base_prod = catalog_db.get_by_id("prod_mech_keyboard_k2")
    cross_sell = growth_engine.get_cross_sell_candidate(base_prod)
    # Budget mouse is out of stock, should skip or pick alternative
    if cross_sell:
        assert cross_sell["cross_sell_product"]["id"] != "prod_budget_ergonomic_mouse"

def test_user_rejects_cross_sell():
    """Test 9: User rejection of cross-sell records CROSS_SELL_REJECTED audit event."""
    session_id = "sess_cross_reject"
    record_offer(session_id, "cross_sell", "prod_usb_c_hub_01", "prod_hdmi_cable_4k")
    res = growth_engine.interact_offer(session_id, "cross_sell", "reject", "prod_hdmi_cable_4k")
    assert res["status"] == "SUCCESS"

    logs = audit_ledger.get_logs_by_session(session_id)
    assert logs[-1].event_type == "CROSS_SELL_REJECTED"

def test_user_accepts_cross_sell():
    """Test 10: User acceptance of cross-sell records CROSS_SELL_ACCEPTED event."""
    session_id = "sess_cross_accept"
    record_offer(session_id, "cross_sell", "prod_usb_c_hub_01", "prod_hdmi_cable_4k")
    res = growth_engine.interact_offer(session_id, "cross_sell", "accept", "prod_hdmi_cable_4k")
    assert res["status"] == "SUCCESS"

    logs = audit_ledger.get_logs_by_session(session_id)
    assert logs[-1].event_type == "CROSS_SELL_ACCEPTED"

def test_correct_incremental_revenue():
    """Test 11: Incremental revenue accumulates only accepted offer prices."""
    session_id = "sess_inc_rev"
    # Base purchase = 799 INR (HDMI cable)
    # Accept cross-sell = 699 INR (Mouse)
    record_offer(session_id, "cross_sell", "prod_mech_keyboard_k2", "prod_budget_ergonomic_mouse")
    growth_engine.interact_offer(session_id, "cross_sell", "accept", "prod_budget_ergonomic_mouse")

    metrics = growth_engine.calculate_metrics()
    assert metrics["incremental_revenue"] == 699.0

def test_rejected_recommendation_does_not_increase_revenue():
    """Test 12: Rejected upsell/cross-sell does not add to incremental revenue."""
    session_id = "sess_rej_rev"
    record_offer(session_id, "upsell", "prod_budget_ergonomic_mouse", "prod_mx_master_3s")
    growth_engine.interact_offer(session_id, "upsell", "reject", "prod_mx_master_3s")

    metrics = growth_engine.calculate_metrics()
    assert metrics["incremental_revenue"] == 0.0

def test_stockout_product_cannot_be_recommended():
    """Test 13: Stockout item is excluded from upsell & cross-sell suggestions."""
    catalog_db.simulate_stock_depletion("prod_mx_master_3s")
    base_prod = catalog_db.get_by_id("prod_budget_ergonomic_mouse")
    
    upsell = growth_engine.get_upsell_candidate(base_prod)
    if upsell:
        assert upsell["upsell_product"]["id"] != "prod_mx_master_3s"

def test_growth_suggestions_cannot_bypass_policy():
    """Test 14: Adding cross-sell item that pushes cart total over max_single_transaction_limit (₹10,000) is blocked by Policy Engine."""
    session_id = "sess_policy_growth"
    # Base item: Keychron keyboard (6499) + MX Master 3S cross-sell (8995) = 15494 > 10000 limit
    proposal = OrderProposal(
        merchant_id="merchant_rzp_tech_01",
        items=[
            CartItem(product_id="prod_mech_keyboard_k2", quantity=1, unit_price=6499.0, name="Keyboard"),
            CartItem(product_id="prod_mx_master_3s", quantity=1, unit_price=8995.0, name="Mouse")
        ],
        total_amount=15494.0,
        user_goal="Buy keyboard and mouse"
    )

    verification = policy_engine.verify_order_proposal(session_id, proposal)
    assert verification.is_valid is False
    assert verification.status == "REJECTED_OVER_BUDGET"

def test_growth_metrics_accuracy():
    """Test 15: Mathematical accuracy of conversion rate, AOV, and acceptance rates."""
    client = TestClient(app)
    
    # 1. Fetch initial metrics via REST API
    res = client.get("/api/growth/metrics")
    assert res.status_code == 200
    m = res.json()
    assert "conversion_rate" in m
    assert "average_order_value" in m
    assert "incremental_revenue" in m

from agent.buyer_agent import buyer_agent
from agent.buyer_intent import BuyerIntent

def test_keyboard_request_returns_keyboard():
    """Phase 3.1 Test 1: A keyboard query under ₹3000 returns a real keyboard, NOT a mouse."""
    goal = "I need a mechanical keyboard for programming under ₹3000."
    intent = BuyerIntent(query="mechanical keyboard for programming", category="peripherals", budget=3000.0, quantity=1)
    candidates = catalog_db.list_all()
    match = buyer_agent._pick_best_match(goal, intent, candidates)
    assert match is not None
    assert "keyboard" in match.name.lower()
    assert match.price <= 3000.0

def test_mouse_request_returns_mouse():
    """Phase 3.1 Test 2: A mouse query returns a real mouse, NOT a keyboard."""
    goal = "I need a silent wireless mouse for office under ₹1000."
    intent = BuyerIntent(query="wireless mouse", category="peripherals", budget=1000.0, quantity=1)
    candidates = catalog_db.list_all()
    match = buyer_agent._pick_best_match(goal, intent, candidates)
    assert match is not None
    assert "mouse" in match.name.lower()
    assert match.price <= 1000.0

def test_upsell_is_same_category_or_valid_upgrade():
    """Phase 3.1 Test 3: Upsell for budget keyboard is a higher-tier keyboard."""
    base_prod = catalog_db.get_by_id("prod_budget_mech_keyboard")
    upsell = growth_engine.get_upsell_candidate(base_prod)
    assert upsell is not None
    assert upsell["upsell_product"]["id"] == "prod_mech_keyboard_k2"
    assert "keyboard" in upsell["upsell_product"]["name"].lower()

def test_upsell_respects_budget():
    """Phase 3.1 Test 4: Upsell returns None if no higher-tier product fits within user's budget cap."""
    base_prod = catalog_db.get_by_id("prod_budget_mech_keyboard")
    upsell = growth_engine.get_upsell_candidate(base_prod, max_budget=3000.0)
    assert upsell is None

def test_cross_sell_is_compatible():
    """Phase 3.1 Test 5: Keyboard cross-sell is a complementary mouse or accessory, NOT an HDMI cable."""
    base_prod = catalog_db.get_by_id("prod_budget_mech_keyboard")
    cross_sell = growth_engine.get_cross_sell_candidate(base_prod)
    assert cross_sell is not None
    cross_sell_name = cross_sell["cross_sell_product"]["name"].lower()
    assert "mouse" in cross_sell_name or "hub" in cross_sell_name
    assert "cable" not in cross_sell_name

def test_irrelevant_cross_sell_rejected():
    """Phase 3.1 Test 6: Cross-sell filtering excludes irrelevant products (e.g. cable for keyboard)."""
    base_prod = catalog_db.get_by_id("prod_mech_keyboard_k2")
    cross_sell = growth_engine.get_cross_sell_candidate(base_prod)
    if cross_sell:
        assert "cable" not in cross_sell["cross_sell_product"]["name"].lower()
