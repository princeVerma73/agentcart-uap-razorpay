import json
import hashlib
import uuid
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Literal
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import settings
from merchant.catalog import catalog_db
from merchant.models import CatalogQuery, Product, OrderProposal
from security.policy_engine import policy_engine, PolicyConfig
from payments.razorpay_client import razorpay_service, verify_webhook_signature
from audit.ledger import audit_ledger
from agent.buyer_agent import buyer_agent
from merchant.analytics import merchant_analytics

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Agentic Commerce Protocol & Execution Engine for Razorpay"
)

# CORS middleware configured from environment origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class RunAgentRequest(BaseModel):
    goal: str
    session_id: Optional[str] = None
    max_budget: Optional[float] = None

class ApproveHitlRequest(BaseModel):
    session_id: str
    proposal: Dict[str, Any]
    verified_total: float
    hitl_token: str

class RejectHitlRequest(BaseModel):
    session_id: str
    reason: Optional[str] = "User rejected approval proposal"


class PriceSurgeRequest(BaseModel):
    product_id: str
    new_price: float

class StockDepleteRequest(BaseModel):
    product_id: str

class RazorpayConfigRequest(BaseModel):
    key_id: str
    key_secret: str
    mock_mode: bool = False


class PaymentVerificationRequest(BaseModel):
    session_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class CheckoutFailureRequest(BaseModel):
    session_id: str
    razorpay_order_id: str
    reason: Literal["cancelled", "failed"]

def require_demo_mode():
    if not settings.AGENTCART_DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Demo simulation and destructive endpoints are disabled in production mode (AGENTCART_DEMO_MODE=false)."
        )

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "mock_mode": razorpay_service.mock_mode,
        "demo_mode": settings.AGENTCART_DEMO_MODE,
        "items_in_catalog": len(catalog_db.list_all())
    }

# ----------------- Merchant Catalog Endpoints ----------------- #

@app.get("/api/catalog")
def get_catalog():
    return {
        "products": [p.model_dump() for p in catalog_db.list_all()]
    }

@app.post("/api/catalog/search")
def search_catalog(query: CatalogQuery):
    results = catalog_db.search(query)
    return {"results": [p.model_dump() for p in results]}

@app.post("/api/catalog/simulate-price-surge")
def simulate_price_surge(req: PriceSurgeRequest):
    require_demo_mode()
    catalog_db.simulate_price_surge(req.product_id, req.new_price)
    return {"status": "success", "message": f"Updated price of {req.product_id} to ₹{req.new_price}"}

@app.post("/api/catalog/simulate-stockout")
def simulate_stockout(req: StockDepleteRequest):
    require_demo_mode()
    catalog_db.simulate_stock_depletion(req.product_id)
    return {"status": "success", "message": f"Depleted stock for {req.product_id}"}

@app.post("/api/catalog/reset")
def reset_catalog():
    require_demo_mode()
    catalog_db.reset_catalog()
    return {"status": "success", "message": "Catalog reset to default state"}

# ----------------- Policy & Financial Guardrails Endpoints ----------------- #

@app.get("/api/policy")
def get_policy():
    cfg = policy_engine.config.model_dump()
    cfg["spent_today"] = policy_engine.get_daily_spent()
    return cfg

@app.post("/api/policy")
def update_policy(config: PolicyConfig):
    try:
        policy_engine.update_config(config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    res = policy_engine.config.model_dump()
    res["spent_today"] = policy_engine.get_daily_spent()
    return {"status": "success", "config": res}

# ----------------- Agent Streaming & Execution Endpoints ----------------- #

@app.post("/api/agent/run")
async def run_agent_stream(req: RunAgentRequest):
    session_id = req.session_id or f"sess_{uuid.uuid4().hex[:10]}"

    async def event_generator():
        try:
            async for step in buyer_agent.run_goal_stream(session_id, req.goal, req.max_budget):
                yield f"data: {json.dumps(step)}\n\n"
        except Exception as e:
            err_payload = {
                "step_number": 99,
                "title": "Execution Error",
                "thought": f"An error occurred: {str(e)}",
                "action": "error",
                "status": "ERROR",
                "data": {"error": str(e)}
            }
            yield f"data: {json.dumps(err_payload)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-ID": session_id
        }
    )

@app.post("/api/agent/approve-hitl")
def approve_hitl(req: ApproveHitlRequest):
    """Called when a human user signs off on a high-value transaction exceeding the autonomous threshold."""
    session_id = req.session_id
    
    # 1. Validate order proposal structure and policy eligibility
    try:
        proposal_obj = OrderProposal(**req.proposal)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid order proposal format: {str(e)}")

    # Verify against policy engine
    verification = policy_engine.verify_order_proposal(session_id, proposal_obj)
    
    if not verification.is_valid or verification.status != "HITL_REQUIRED":
        raise HTTPException(
            status_code=400,
            detail=f"Transaction validation failed or is not pending HITL sign-off. Status: {verification.status}. Reason: {verification.reason}"
        )

    # 2. Verify total amount consistency
    if abs(verification.verified_total - req.verified_total) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Claimed amount mismatch: server verified total is ₹{verification.verified_total:,.2f}, provided ₹{req.verified_total:,.2f}"
        )

    # 3. Verify HITL HMAC Token (mandatory, cryptographically bound, unexpired, un-replayed)
    if not req.hitl_token:
        audit_ledger.record(
            session_id=session_id,
            event_type="HITL_REJECTED",
            status="REJECTED",
            summary="HITL approval rejected: Missing cryptographic sign-off token.",
            details={"session_id": session_id, "reason": "missing_token"}
        )
        raise HTTPException(status_code=403, detail="Missing HITL cryptographic sign-off token.")

    is_valid_token = policy_engine.verify_hitl_token(
        token=req.hitl_token,
        session_id=session_id,
        verified_total=verification.verified_total,
        idempotency_key=verification.idempotency_key,
        proposal=proposal_obj
    )
    if not is_valid_token:
        audit_ledger.record(
            session_id=session_id,
            event_type="HITL_REJECTED",
            status="REJECTED",
            summary="HITL approval rejected: Invalid, expired, session-mismatched, or replayed sign-off token.",
            details={"session_id": session_id, "amount": verification.verified_total, "hitl_token": req.hitl_token}
        )
        raise HTTPException(status_code=403, detail="Invalid, expired, or replayed HITL cryptographic sign-off token.")

    # Consume token immediately (single-use replay protection)
    policy_engine.consume_hitl_token(req.hitl_token, session_id=session_id)

    amount = verification.verified_total
    
    audit_ledger.record(
        session_id=session_id,
        event_type="HITL_APPROVED",
        status="SUCCESS",
        summary=f"Human user cryptographically signed off on transaction for ₹{amount:,.2f}",
        details={"session_id": session_id, "amount": amount, "hitl_token": req.hitl_token}
    )
    
    # Create Razorpay Order
    rzp_order = razorpay_service.create_order(
        session_id=session_id,
        amount=amount,
        receipt_id=f"rcpt_hitl_{session_id[:8]}",
        notes={"approved_by": "human_signer", "agent": "AgentCart-UAP-v1"},
        idempotency_key=verification.idempotency_key,
    )

    if razorpay_service.checkout_enabled:
        return {
            "status": "PENDING_PAYMENT",
            "message": "Razorpay Test Checkout is ready.",
            "order": rzp_order,
            "checkout": razorpay_service.checkout_options(rzp_order),
        }

    # Preserve the sandbox behavior used by the Phase 1-3 test suite.
    settlement = razorpay_service.simulate_payment_settlement(
        session_id=session_id,
        order_id=rzp_order["id"],
        amount=amount,
    )
    policy_engine.mark_key_processed(verification.idempotency_key, session_id=session_id)
    return {
        "status": "SUCCESS",
        "message": f"Transaction approved by user and executed on Razorpay.",
        "order": rzp_order,
        "settlement": settlement
    }


@app.post("/api/agent/reject-hitl")
def reject_hitl(req: RejectHitlRequest):
    """Called when a human user rejects a proposal at the HITL sign-off gate."""
    audit_ledger.record(
        session_id=req.session_id,
        event_type="HITL_REJECTED",
        status="REJECTED",
        summary=f"Human user rejected transaction sign-off: {req.reason}",
        details={"session_id": req.session_id, "reason": req.reason}
    )
    return {"status": "REJECTED", "message": "Transaction rejected by user"}


@app.post("/api/payments/verify")
def verify_razorpay_payment(req: PaymentVerificationRequest):
    """Verify the Checkout success payload server-side before completing an order."""
    try:
        verification = razorpay_service.verify_payment(
            session_id=req.session_id,
            order_id=req.razorpay_order_id,
            payment_id=req.razorpay_payment_id,
            signature=req.razorpay_signature,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    order_record = razorpay_service._orders[req.razorpay_order_id]
    idempotency_key = order_record.get("idempotency_key")
    if idempotency_key:
        policy_engine.mark_key_processed(idempotency_key, session_id=req.session_id)

    return {"status": "SUCCESS", "payment": verification}


@app.post("/api/payments/checkout-failed")
def checkout_failed(req: CheckoutFailureRequest):
    """Record a Checkout cancellation/failure without accepting any payment status from the browser."""
    try:
        order = razorpay_service.fail_checkout(req.session_id, req.razorpay_order_id, req.reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "SUCCESS", "order": order}


@app.post("/api/payments/webhook")
async def razorpay_webhook(request: Request):
    """Razorpay's signed, asynchronous source of truth for payment reconciliation."""
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not verify_webhook_signature(raw_body, signature, settings.RAZORPAY_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid Razorpay webhook signature")
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Webhook body must be valid JSON")
    event_type = payload.get("event", "")
    # Razorpay event IDs are preferred; a content digest is deterministic for retries.
    event_id = request.headers.get("X-Razorpay-Event-Id") or hashlib.sha256(raw_body).hexdigest()
    return razorpay_service.reconcile_webhook(event_type, payload, event_id)


@app.get("/api/orders/{order_id}")
def get_order_lifecycle(order_id: str, session_id: str):
    try:
        return razorpay_service.order_status(session_id, order_id)
    except ValueError as exc:
        raise HTTPException(status_code=404 if str(exc) == "Order ID not recognized" else 403, detail=str(exc))


@app.get("/api/orders")
def get_all_orders():
    """Retrieve summarized order and transaction history derived from the authoritative audit ledger and orders registry."""
    orders_map: Dict[str, Dict[str, Any]] = {}
    
    # First, populate from razorpay_service orders
    for order_id, rec in razorpay_service._orders.items():
        sess_id = rec.get("session_id", "")
        paise = rec.get("amount", 0)
        state = rec.get("state", "created")
        status_label = "Settled" if state == "paid" else ("Rejected" if state in ("failed", "cancelled") else ("Pending Approval" if state == "checkout" else "Created"))
        orders_map[sess_id] = {
            "order_id": order_id,
            "session_id": sess_id,
            "goal": (rec.get("provider_order") or {}).get("notes", {}).get("goal") or "Autonomous Purchase",
            "amount": paise / 100.0,
            "status": status_label,
            "timestamp": datetime.fromtimestamp(rec.get("created_at", time.time()), tz=timezone.utc).isoformat(),
            "payment_id": rec.get("payment_id"),
        }

    # Second, enrich/add from audit ledger entries (to capture rejected or non-order sessions as well)
    all_logs = audit_ledger.get_all_logs(limit=500)
    sessions: Dict[str, List[Any]] = {}
    for log in all_logs:
        sessions.setdefault(log.session_id, []).append(log)

    for sess_id, logs in sessions.items():
        if not sess_id or sess_id == "webhook_unmatched" or sess_id == "system":
            continue
        
        goal = "Autonomous Purchase"
        for l in logs:
            if l.event_type == "AGENT_INTAKE" and l.details.get("goal"):
                goal = l.details["goal"]
                break

        is_paid = any(l.event_type in ("PAYMENT_CAPTURED", "PAYMENT_VERIFIED") and l.status == "SUCCESS" for l in logs)
        is_hitl_rejected = any(l.event_type == "HITL_REJECTED" for l in logs)
        is_policy_rejected = any(l.event_type == "POLICY_CHECK" and l.status == "REJECTED" for l in logs)
        is_hitl_pending = any(l.event_type == "HITL_REQUIRED" and l.status == "PENDING_APPROVAL" for l in logs) and not is_paid and not is_hitl_rejected

        status = "Settled" if is_paid else ("Rejected" if (is_hitl_rejected or is_policy_rejected) else ("Pending Approval" if is_hitl_pending else "Completed"))
        
        amount = 0.0
        payment_id = None
        order_id = None
        ts = logs[0].timestamp if logs else datetime.now(timezone.utc).isoformat()

        for l in logs:
            d = l.details or {}
            if "verified_total" in d and isinstance(d["verified_total"], (int, float)):
                amount = float(d["verified_total"])
            elif "total" in d and isinstance(d["total"], (int, float)):
                amount = float(d["total"])
            elif "amount" in d and isinstance(d["amount"], (int, float)):
                amount = float(d["amount"])
            
            if "order_id" in d and d["order_id"]:
                order_id = d["order_id"]
            if "payment_id" in d and d["payment_id"]:
                payment_id = d["payment_id"]
            if "razorpay_payment_id" in d and d["razorpay_payment_id"]:
                payment_id = d["razorpay_payment_id"]

        if sess_id not in orders_map:
            orders_map[sess_id] = {
                "order_id": order_id or f"ord_{sess_id[:10]}",
                "session_id": sess_id,
                "goal": goal,
                "amount": amount,
                "status": status,
                "timestamp": ts,
                "payment_id": payment_id
            }
        else:
            orders_map[sess_id]["goal"] = goal
            if is_hitl_rejected or is_policy_rejected:
                orders_map[sess_id]["status"] = "Rejected"
            if amount > 0 and orders_map[sess_id]["amount"] == 0:
                orders_map[sess_id]["amount"] = amount

    return {"orders": sorted(list(orders_map.values()), key=lambda x: x.get("timestamp", ""), reverse=True)}


# ----------------- Audit Ledger Endpoints ----------------- #

@app.get("/api/audit-logs")
def get_audit_logs(session_id: Optional[str] = None):
    if session_id:
        logs = audit_ledger.get_logs_by_session(session_id)
    else:
        logs = audit_ledger.get_all_logs(limit=100)
    return {"logs": [log.model_dump() for log in logs]}

@app.post("/api/audit-logs/clear")
def clear_audit_logs():
    require_demo_mode()
    audit_ledger.clear()
    return {"status": "success", "message": "Audit ledger cleared"}

# ----------------- Merchant Growth Engine Endpoints ----------------- #

from merchant.growth_engine import growth_engine

class GrowthInteractRequest(BaseModel):
    session_id: str
    offer_type: str  # 'upsell' or 'cross_sell'
    action: str      # 'accept' or 'reject'
    product_id: str
    base_product_id: Optional[str] = None
    quantity: int = 1

class GrowthRecommendationRequest(BaseModel):
    product_id: str
    max_budget: Optional[float] = None

@app.get("/api/growth/metrics")
def get_growth_metrics():
    return growth_engine.calculate_metrics()

@app.get("/api/merchant/analytics")
def get_merchant_analytics():
    return merchant_analytics()

@app.post("/api/growth/interact")
def interact_growth_offer(req: GrowthInteractRequest):
    return growth_engine.interact_offer(
        session_id=req.session_id,
        offer_type=req.offer_type,
        action=req.action,
        item_id=req.product_id,
        base_product_id=req.base_product_id,
        quantity=req.quantity,
    )

@app.post("/api/growth/recommendations")
def get_growth_recommendations(req: GrowthRecommendationRequest):
    base_product = catalog_db.get_by_id(req.product_id)
    if not base_product:
        raise HTTPException(status_code=404, detail="Product not found")

    upsell = growth_engine.get_upsell_candidate(base_product, req.max_budget)
    cross_sell = growth_engine.get_cross_sell_candidate(base_product, req.max_budget)

    return {
        "base_product": base_product.model_dump(),
        "upsell_candidate": upsell,
        "cross_sell_candidate": cross_sell
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
