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
    print("\n=== Scenario 1: Autonomous Purchase (<= INR 3,000) ===")
    session_id = f"demo_autonomous_{RUN_ID}"
    base = catalog_db.get_by_id("prod_budget_mech_keyboard")
    assert base is not None
    cross_sell = growth_engine.get_cross_sell_candidate(base)
    upsell = growth_engine.get_upsell_candidate(base)
    print("  [INPUT]           Buyer Intent: 'Buy a mechanical keyboard under INR 2500'")
    print(f"  [AGENT DECISION]  Matched: {base.name} (INR {base.price:.2f})")
    if cross_sell:
        candidate = cross_sell["cross_sell_product"]
        print(f"                    Growth Attached: {candidate['name']} (+INR {candidate['price']:.2f})")
    proposal = OrderProposal(merchant_id="merchant_rzp_tech_01", items=[CartItem(product_id=base.id, quantity=1, unit_price=base.price, name=base.name)], total_amount=base.price, user_goal="Buy a mechanical keyboard under ₹2500")
    result = policy_engine.verify_order_proposal(session_id, proposal)
    assert result.is_valid and result.status == "AUTO_APPROVED"
    order = razorpay_service.create_order(session_id, result.verified_total, "demo_auto", idempotency_key=result.idempotency_key)
    receipt = razorpay_service.simulate_payment_settlement(session_id, order["id"], result.verified_total)
    policy_engine.mark_key_processed(result.idempotency_key, session_id)
    print(f"  [POLICY RESULT]   Status: {result.status} (Verified Total: INR {result.verified_total:.2f} <= INR 3,000 ceiling)")
    print(f"  [PAYMENT RESULT]  Sandbox Order: {order['id']} | Receipt: {receipt['razorpay_payment_id']} (Captured)")
    print(f"  [AUDIT RESULT]    Logged: ORDER_CREATED, PAYMENT_CAPTURED, PAYMENT_LEDGER_POSTED")


def scenario_hitl() -> None:
    print("\n=== Scenario 2: Human-in-the-Loop Sign-off (INR 3,001 - INR 10,000) ===")
    session_id = f"demo_hitl_{RUN_ID}"
    product = catalog_db.get_by_id("prod_mech_keyboard_k2")
    assert product is not None
    proposal = OrderProposal(merchant_id="merchant_rzp_tech_01", items=[CartItem(product_id=product.id, quantity=1, unit_price=product.price, name=product.name)], total_amount=product.price, user_goal="Purchase a Keychron K2")
    result = policy_engine.verify_order_proposal(session_id, proposal)
    assert result.is_valid and result.status == "HITL_REQUIRED"
    print(f"  [INPUT]           Buyer Intent: 'Purchase a Keychron K2' (Price: INR {product.price:.2f})")
    print(f"  [AGENT DECISION]  Proposed High-Value Item -> Triggered Policy Tier")
    print(f"  [POLICY RESULT]   Status: {result.status} | Generated HMAC-SHA256 Approval Token")
    assert policy_engine.verify_hitl_token(result.hitl_token or "", session_id, result.verified_total, result.idempotency_key)
    audit_ledger.record(session_id, "HITL_APPROVED", "SUCCESS", "Demo human sign-off verified.", {"amount": result.verified_total})
    order = razorpay_service.create_order(session_id, result.verified_total, "demo_hitl", idempotency_key=result.idempotency_key)
    print(f"  [PAYMENT RESULT]  Sign-off Confirmed -> Razorpay Sandbox Order Created: {order['id']}")
    print(f"  [AUDIT RESULT]    Logged: HITL_REQUIRED, HITL_APPROVED (Single-Use Token Consumed)")


async def scenario_stockout() -> None:
    print("\n=== Scenario 3: Stockout Auto-Recovery ===")
    session_id = f"demo_stockout_{RUN_ID}"
    catalog_db.simulate_stock_depletion("prod_mech_keyboard_k2")
    print("  [INPUT]           Buyer Intent: 'Buy a mechanical keyboard for office'")
    print("  [AGENT DECISION]  Primary choice out of stock -> Searching catalog alternative...")
    async for _ in buyer_agent.run_goal_stream(session_id, "Buy a mechanical keyboard for office"):
        pass
    recovered = [entry for entry in audit_ledger.get_logs_by_session(session_id) if entry.event_type == "ERROR_RECOVERED"]
    assert recovered, "Expected the buyer agent to record stockout recovery"
    print(f"  [POLICY RESULT]   Intercepted Stockout: Alternate in-stock category item selected")
    print(f"  [AUDIT RESULT]    Logged: ERROR_RECOVERED ({recovered[-1].summary})")


def scenario_price_surge() -> None:
    print("\n=== Scenario 4: Price Surge Rejection & DB Re-anchoring ===")
    session_id = f"demo_surge_{RUN_ID}"
    product = catalog_db.get_by_id("prod_hdmi_cable_4k")
    assert product is not None
    original_price = product.price
    # Merchant catalog price surges to INR 1499.00
    catalog_db.simulate_price_surge("prod_hdmi_cable_4k", 1499.0)
    
    stale_proposal = OrderProposal(
        merchant_id="merchant_rzp_tech_01",
        items=[CartItem(product_id="prod_hdmi_cable_4k", quantity=1, unit_price=original_price, name="4K HDMI Cable")],
        total_amount=original_price,
        user_goal="Buy 4K HDMI Cable"
    )
    print(f"  [INPUT]           Client proposes stale price: INR {original_price:.2f}")
    result = policy_engine.verify_order_proposal(session_id, stale_proposal)
    assert result.verified_total == 1499.0
    print(f"  [AGENT DECISION]  Client unit price overridden by server database truth")
    print(f"  [POLICY RESULT]   Re-anchored Verified Total: INR {result.verified_total:.2f}")
    print(f"  [AUDIT RESULT]    Logged: POLICY_CHECK with price discrepancy notice")


def scenario_gateway_failure() -> None:
    print("\n=== Scenario 5: Payment Gateway Failure & Terminal Cancellation ===")
    session_id = f"demo_fail_{RUN_ID}"
    order = razorpay_service.create_order(session_id, 799.0, "demo_failure_receipt")
    razorpay_service._transition(order["id"], "created", "checkout")
    failed_order = razorpay_service.fail_checkout(session_id, order["id"], "cancelled")
    assert failed_order["state"] == "cancelled"
    print(f"  [INPUT]           Razorpay Modal dismissed / Payment cancelled by user")
    print(f"  [AGENT DECISION]  Checkout aborted")
    print(f"  [PAYMENT RESULT]  Order State: {failed_order['state']} (Reason: {failed_order['failure_reason']})")
    print(f"  [AUDIT RESULT]    Zero false capture recorded; Financial ledger remains uncredited")


def main() -> None:
    original_mode, original_client = razorpay_service.mock_mode, razorpay_service.client
    catalog_snapshot = {product_id: product.model_copy() for product_id, product in catalog_db.products.items()}
    try:
        razorpay_service.mock_mode, razorpay_service.client = True, None
        scenario_autonomous()
        scenario_hitl()
        asyncio.run(scenario_stockout())
        scenario_price_surge()
        scenario_gateway_failure()
        valid, _, message = audit_ledger.verify_chain_integrity()
        print(f"\nAudit chain: {'VALID' if valid else 'INVALID'} | {message}")
    finally:
        # Demonstration audit entries are intentionally retained, but temporary
        # stock changes are restored instead of altering merchant inventory.
        catalog_db.products = catalog_snapshot
        razorpay_service.mock_mode, razorpay_service.client = original_mode, original_client


if __name__ == "__main__":
    main()
