"""Terminal walkthrough for AgentCart's guarded commerce paths.

This script deliberately forces Razorpay mock mode: its capture receipt is a local
sandbox demonstration, never a claim of a live payment. It uses only existing
catalog products and prints the audit-chain verification result at the end.
"""
import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from agent.buyer_agent import buyer_agent
from audit.ledger import audit_ledger
from merchant.catalog import catalog_db
from merchant.growth_engine import growth_engine
from merchant.models import CartItem, OrderProposal
from payments.razorpay_client import razorpay_service
from security.policy_engine import policy_engine

RUN_ID = uuid.uuid4().hex[:8]


def scenario_autonomous() -> None:
    print("\n=== 1. Autonomous path: live intent, recommendation, policy, sandbox order ===")
    session_id = f"demo_autonomous_{RUN_ID}"
    base = catalog_db.get_by_id("prod_budget_mech_keyboard")
    assert base is not None
    cross_sell = growth_engine.get_cross_sell_candidate(base)
    upsell = growth_engine.get_upsell_candidate(base)
    print("Intent: Buy a mechanical keyboard under INR 2500")
    print(f"Ranked live catalog match: {base.name} — INR {base.price:.2f}")
    if cross_sell:
        candidate = cross_sell["cross_sell_product"]
        print(f"Compatible live recommendation: {candidate['name']} — +INR {candidate['price']:.2f}")
    if upsell:
        print(f"Catalog upgrade considered: {upsell['upsell_product']['name']} — INR {upsell['upsell_product']['price']:.2f}")
    # Do not invent the requested wrist rest: none exists in the merchant catalog.
    # The base order stays inside the fixed INR 3,000 autonomous tier.
    proposal = OrderProposal(merchant_id="merchant_rzp_tech_01", items=[CartItem(product_id=base.id, quantity=1, unit_price=base.price, name=base.name)], total_amount=base.price, user_goal="Buy a mechanical keyboard under ₹2500")
    result = policy_engine.verify_order_proposal(session_id, proposal)
    assert result.is_valid and result.status == "AUTO_APPROVED"
    order = razorpay_service.create_order(session_id, result.verified_total, "demo_auto", idempotency_key=result.idempotency_key)
    receipt = razorpay_service.simulate_payment_settlement(session_id, order["id"], result.verified_total)
    policy_engine.mark_key_processed(result.idempotency_key, session_id)
    print(f"Policy: {result.status}; sandbox order: {order['id']}; sandbox receipt: {receipt['razorpay_payment_id']}")


def scenario_hitl() -> None:
    print("\n=== 2. HITL path: high-value purchase requires explicit approval ===")
    session_id = f"demo_hitl_{RUN_ID}"
    product = catalog_db.get_by_id("prod_mech_keyboard_k2")
    assert product is not None
    proposal = OrderProposal(merchant_id="merchant_rzp_tech_01", items=[CartItem(product_id=product.id, quantity=1, unit_price=product.price, name=product.name)], total_amount=product.price, user_goal="Purchase a Keychron K2")
    result = policy_engine.verify_order_proposal(session_id, proposal)
    assert result.is_valid and result.status == "HITL_REQUIRED"
    print(f"Policy: {result.status}; verified total: INR {result.verified_total:.2f}")
    assert policy_engine.verify_hitl_token(result.hitl_token or "", session_id, result.verified_total, result.idempotency_key)
    audit_ledger.record(session_id, "HITL_APPROVED", "SUCCESS", "Demo human sign-off verified.", {"amount": result.verified_total})
    order = razorpay_service.create_order(session_id, result.verified_total, "demo_hitl", idempotency_key=result.idempotency_key)
    print(f"Human sign-off accepted; Razorpay sandbox order created: {order['id']}")


async def scenario_stockout() -> None:
    print("\n=== 3. Stockout recovery: category alternative instead of unsafe checkout ===")
    session_id = f"demo_stockout_{RUN_ID}"
    catalog_db.simulate_stock_depletion("prod_mech_keyboard_k2")
    async for _ in buyer_agent.run_goal_stream(session_id, "Buy a mechanical keyboard for office"):
        pass
    recovered = [entry for entry in audit_ledger.get_logs_by_session(session_id) if entry.event_type == "ERROR_RECOVERED"]
    assert recovered, "Expected the buyer agent to record stockout recovery"
    print(f"Stockout detected; recovery event: {recovered[-1].summary}")


def main() -> None:
    original_mode, original_client = razorpay_service.mock_mode, razorpay_service.client
    catalog_snapshot = {product_id: product.model_copy() for product_id, product in catalog_db.products.items()}
    try:
        razorpay_service.mock_mode, razorpay_service.client = True, None
        scenario_autonomous()
        scenario_hitl()
        asyncio.run(scenario_stockout())
        valid, _, message = audit_ledger.verify_chain_integrity()
        print(f"\nAudit chain: {'VALID' if valid else 'INVALID'} — {message}")
    finally:
        # Demonstration audit entries are intentionally retained, but temporary
        # stock changes are restored instead of altering merchant inventory.
        catalog_db.products = catalog_snapshot
        razorpay_service.mock_mode, razorpay_service.client = original_mode, original_client


if __name__ == "__main__":
    main()
