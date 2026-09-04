from typing import Any, Dict

from backend.audit.ledger import audit_ledger


def merchant_analytics() -> Dict[str, Any]:
    """Aggregate auditable runtime facts; no counters are accepted from clients."""
    logs = audit_ledger.get_all_logs(limit=1_000_000)
    settled_orders = set()
    gmv = 0.0
    upsell_incremental = 0.0
    cross_sell_incremental = 0.0
    upsell_opps = upsell_accepted = upsell_rejected = 0
    cross_opps = cross_accepted = cross_rejected = 0
    pre_authorized = hitl_approved = recovered = 0

    for log in logs:
        details = log.details or {}
        if log.event_type == "PAYMENT_CAPTURED" and log.status == "SUCCESS":
            order_id = details.get("order_id") or details.get("razorpay_order_id")
            if order_id and order_id not in settled_orders:
                settled_orders.add(order_id)
                gmv += float(details.get("amount", details.get("amount_paise", 0) / 100.0))
        elif log.event_type == "UPSELL_ACCEPTED":
            upsell_accepted += 1
            upsell_incremental += float(details.get("incremental_revenue", 0.0))
        elif log.event_type == "UPSELL_REJECTED":
            upsell_rejected += 1
        elif log.event_type == "CROSS_SELL_ACCEPTED":
            cross_accepted += 1
            cross_sell_incremental += float(details.get("incremental_revenue", 0.0))
        elif log.event_type == "CROSS_SELL_REJECTED":
            cross_rejected += 1
        elif log.event_type == "POLICY_CHECK" and log.status == "SUCCESS":
            pre_authorized += 1
        elif log.event_type == "HITL_APPROVED" and log.status == "SUCCESS":
            hitl_approved += 1
        elif log.event_type == "ERROR_RECOVERED":
            recovered += 1

    upsell_opps = upsell_accepted + upsell_rejected
    cross_opps = cross_accepted + cross_rejected
    total_incremental = upsell_incremental + cross_sell_incremental
    base_product_rev = max(0.0, gmv - total_incremental)
    gate_total = pre_authorized + hitl_approved

    return {
        "gmv": round(gmv, 2),
        "base_product_revenue": round(base_product_rev, 2),
        "incremental_revenue": round(total_incremental, 2),
        "upsell_incremental_revenue": round(upsell_incremental, 2),
        "cross_sell_incremental_revenue": round(cross_sell_incremental, 2),
        "purchases": len(settled_orders),
        "average_order_value": round(gmv / len(settled_orders), 2) if settled_orders else 0.0,
        "upsell_opportunities": upsell_opps,
        "accepted_upsells": upsell_accepted,
        "rejected_upsells": upsell_rejected,
        "upsell_acceptance_rate": round((upsell_accepted / upsell_opps) * 100, 2) if upsell_opps else 0.0,
        "cross_sell_opportunities": cross_opps,
        "accepted_cross_sells": cross_accepted,
        "rejected_cross_sells": cross_rejected,
        "cross_sell_acceptance_rate": round((cross_accepted / cross_opps) * 100, 2) if cross_opps else 0.0,
        "pre_authorized_transactions": pre_authorized,
        "hitl_approved_transactions": hitl_approved,
        "hitl_gate_ratio": round((hitl_approved / gate_total) * 100, 2) if gate_total else 0.0,
        "failure_recoveries": recovered,
    }
