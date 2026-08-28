from typing import Any, Dict

from audit.ledger import audit_ledger


def merchant_analytics() -> Dict[str, Any]:
    """Aggregate auditable runtime facts; no counters are accepted from clients."""
    logs = audit_ledger.get_all_logs(limit=1_000_000)
    settled_orders = set()
    gmv = 0.0
    incremental_revenue = 0.0
    pre_authorized = hitl_approved = recovered = 0

    for log in logs:
        details = log.details or {}
        if log.event_type == "PAYMENT_CAPTURED" and log.status == "SUCCESS":
            order_id = details.get("order_id") or details.get("razorpay_order_id")
            if order_id and order_id not in settled_orders:
                settled_orders.add(order_id)
                gmv += float(details.get("amount", details.get("amount_paise", 0) / 100.0))
        elif log.event_type in {"UPSELL_ACCEPTED", "CROSS_SELL_ACCEPTED"}:
            incremental_revenue += float(details.get("incremental_revenue", 0.0))
        elif log.event_type == "POLICY_CHECK" and log.status == "SUCCESS":
            pre_authorized += 1
        elif log.event_type == "HITL_APPROVED" and log.status == "SUCCESS":
            hitl_approved += 1
        elif log.event_type == "ERROR_RECOVERED":
            recovered += 1

    gate_total = pre_authorized + hitl_approved
    return {
        "gmv": round(gmv, 2),
        "incremental_revenue": round(incremental_revenue, 2),
        "purchases": len(settled_orders),
        "average_order_value": round(gmv / len(settled_orders), 2) if settled_orders else 0.0,
        "pre_authorized_transactions": pre_authorized,
        "hitl_approved_transactions": hitl_approved,
        "hitl_gate_ratio": round((hitl_approved / gate_total) * 100, 2) if gate_total else 0.0,
        "failure_recoveries": recovered,
    }
