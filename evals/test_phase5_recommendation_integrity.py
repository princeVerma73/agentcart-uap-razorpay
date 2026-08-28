import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from audit.ledger import audit_ledger
from merchant.catalog import catalog_db
from merchant.growth_engine import growth_engine
from security.policy_engine import PolicyConfig, policy_engine


@pytest.fixture(autouse=True)
def reset_state():
    catalog_db.reset_catalog()
    audit_ledger.clear()
    policy_engine.update_config(PolicyConfig())
    policy_engine.processed_idempotency_keys.clear()


def record_offer(session_id, offer_type, base_product_id, offered_product_id, max_budget=None):
    audit_ledger.record(
        session_id=session_id,
        event_type=f"{offer_type.upper()}_PROPOSED",
        status="SUCCESS",
        summary="Test offer",
        details={
            "base_product_id": base_product_id,
            "offered_product_id": offered_product_id,
            "max_budget": max_budget,
            "quantity": 1,
        },
    )


def test_cross_sell_uses_reciprocal_catalog_compatibility_only():
    coffee = catalog_db.get_by_id("prod_coffee_beans_1kg")
    keyboard = catalog_db.get_by_id("prod_mech_keyboard_k2")

    assert growth_engine.get_cross_sell_candidate(coffee) is None
    suggestion = growth_engine.get_cross_sell_candidate(keyboard)
    assert suggestion is not None
    assert suggestion["cross_sell_product"]["id"] in keyboard.compatible_product_ids
    assert keyboard.id in suggestion["cross_sell_product"]["compatible_product_ids"]


def test_cross_sell_respects_combined_buyer_budget():
    keyboard = catalog_db.get_by_id("prod_budget_mech_keyboard")
    assert growth_engine.get_cross_sell_candidate(keyboard, max_budget=3000.0) is None


def test_unoffered_item_cannot_be_accepted_for_growth_revenue():
    response = growth_engine.interact_offer(
        "sess_unoffered", "cross_sell", "accept", "prod_hdmi_cable_4k"
    )

    assert response["status"] == "ERROR"
    assert growth_engine.calculate_metrics()["incremental_revenue"] == 0.0


def test_incompatible_cross_sell_is_rejected_even_if_an_offer_event_is_tampered():
    session_id = "sess_incompatible_offer"
    record_offer(session_id, "cross_sell", "prod_coffee_beans_1kg", "prod_budget_ergonomic_mouse")

    response = growth_engine.interact_offer(
        session_id, "cross_sell", "accept", "prod_budget_ergonomic_mouse", "prod_coffee_beans_1kg"
    )

    assert response["status"] == "ERROR"
    assert growth_engine.calculate_metrics()["incremental_revenue"] == 0.0


def test_accepted_upsell_records_only_price_delta_as_incremental_revenue():
    session_id = "sess_upsell_delta"
    record_offer(session_id, "upsell", "prod_budget_ergonomic_mouse", "prod_mx_master_3s")

    response = growth_engine.interact_offer(
        session_id, "upsell", "accept", "prod_mx_master_3s", "prod_budget_ergonomic_mouse"
    )

    assert response["status"] == "SUCCESS"
    assert growth_engine.calculate_metrics()["incremental_revenue"] == 8296.0


def test_stock_change_before_acceptance_rejects_offer_without_revenue():
    session_id = "sess_stock_changed"
    record_offer(session_id, "cross_sell", "prod_mech_keyboard_k2", "prod_budget_ergonomic_mouse")
    catalog_db.simulate_stock_depletion("prod_budget_ergonomic_mouse")

    response = growth_engine.interact_offer(
        session_id, "cross_sell", "accept", "prod_budget_ergonomic_mouse", "prod_mech_keyboard_k2"
    )

    assert response["status"] == "ERROR"
    assert growth_engine.calculate_metrics()["incremental_revenue"] == 0.0
