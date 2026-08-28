"""Deterministic synthetic benchmark for the Track 1 growth hypothesis.

It uses only live AgentCart catalog prices, stock and recommendation rules.  It does
not call a payment rail or report simulated sessions as real merchant revenue.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from merchant.catalog import catalog_db
from merchant.growth_engine import growth_engine


def _decision(session: int, label: str, percent: int) -> bool:
    digest = hashlib.sha256(f"{session}:{label}".encode()).digest()
    return int.from_bytes(digest[:2], "big") % 100 < percent


def _summary(revenue: float, purchases: int, sessions: int) -> dict:
    return {
        "sessions": sessions,
        "purchases": purchases,
        "conversion_rate_percent": round(purchases / sessions * 100, 2) if sessions else 0.0,
        "average_order_value": round(revenue / purchases, 2) if purchases else 0.0,
        "revenue_per_session": round(revenue / sessions, 2) if sessions else 0.0,
        "revenue": round(revenue, 2),
    }


def run_evaluation(sessions: int = 500) -> dict:
    if sessions < 1:
        raise ValueError("sessions must be at least one")
    catalog_db.reset_catalog()
    products = sorted(catalog_db.list_all(), key=lambda item: item.id)
    baseline_revenue = agent_revenue = 0.0
    baseline_purchases = agent_purchases = 0
    upsell_offered = upsell_accepted = cross_offered = cross_accepted = 0

    for index in range(sessions):
        product = products[index % len(products)]
        # One in five customers is deliberately modeled with headroom for a
        # catalog-grounded upgrade; the remaining sessions retain a tight budget.
        budget = product.price * (3.0 if index % 5 == 0 else (1.15 if index % 4 else 0.85))
        # Baseline: direct catalog search's top match and an independently sampled conversion.
        if product.stock > 0 and product.price <= budget and _decision(index, "baseline", 64):
            baseline_purchases += 1
            baseline_revenue += product.price

        # AgentCart: structured intent resolves to this live product, then catalog-grounded offers.
        if not (product.stock > 0 and product.price <= budget and _decision(index, "agent", 70)):
            continue
        order_total = product.price
        upsell = growth_engine.get_upsell_candidate(product, budget)
        cross = growth_engine.get_cross_sell_candidate(product, budget)
        if upsell:
            upsell_offered += 1
            candidate = upsell["upsell_product"]
            if candidate["price"] <= budget and _decision(index, "upsell", 29):
                order_total = candidate["price"]
                upsell_accepted += 1
        if cross and order_total == product.price:
            cross_offered += 1
            candidate = cross["cross_sell_product"]
            if order_total + candidate["price"] <= budget and _decision(index, "cross", 22):
                order_total += candidate["price"]
                cross_accepted += 1
        # Deterministic policy ceiling is still authoritative in this offline evaluation.
        if order_total <= 10_000:
            agent_purchases += 1
            agent_revenue += order_total

    baseline = _summary(baseline_revenue, baseline_purchases, sessions)
    agentcart = _summary(agent_revenue, agent_purchases, sessions)
    result = {
        "methodology": "Synthetic, deterministic catalog evaluation; results are not live revenue.",
        "baseline": baseline,
        "agentcart": {
            **agentcart,
            "upsell_acceptance_rate_percent": round(upsell_accepted / upsell_offered * 100, 2) if upsell_offered else 0.0,
            "cross_sell_acceptance_rate_percent": round(cross_accepted / cross_offered * 100, 2) if cross_offered else 0.0,
            "net_incremental_revenue": round(agent_revenue - baseline_revenue, 2),
        },
    }
    output = Path(__file__).with_name("evaluation_results.json")
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions", type=int, default=500)
    args = parser.parse_args()
    print(json.dumps(run_evaluation(args.sessions), indent=2))
