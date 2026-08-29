"""Deterministic synthetic benchmark for the Track 1 growth hypothesis.

It uses only live AgentCart catalog prices, stock, and recommendation rules. It compares
identical synthetic shopping sessions under identical buyer propensity, budget, and catalog state.
It does not call live payment rails or report simulated sessions as live merchant revenue.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from merchant.catalog import catalog_db
from merchant.growth_engine import growth_engine


def _decision(session: int, label: str, percent: int) -> bool:
    digest = hashlib.sha256(f"{session}:{label}".encode()).digest()
    return int.from_bytes(digest[:2], "big") % 100 < percent


def _summary(revenue: float, purchases: int, sessions: int, order_values: list[float]) -> dict:
    cr = round(purchases / sessions * 100, 2) if sessions else 0.0
    aov = round(revenue / purchases, 2) if purchases else 0.0
    rps = round(revenue / sessions, 2) if sessions else 0.0
    
    # 95% Confidence Interval for Conversion Rate (Normal approximation)
    p = purchases / sessions if sessions else 0.0
    cr_std_err = math.sqrt(p * (1 - p) / sessions) if sessions else 0.0
    cr_ci_95 = round(1.96 * cr_std_err * 100, 2)

    # 95% Confidence Interval for AOV
    if purchases > 1:
        variance = sum((v - (revenue / purchases)) ** 2 for v in order_values) / (purchases - 1)
        aov_std_err = math.sqrt(variance / purchases)
        aov_ci_95 = round(1.96 * aov_std_err, 2)
    else:
        aov_ci_95 = 0.0

    return {
        "sessions": sessions,
        "purchases": purchases,
        "conversion_rate_percent": cr,
        "conversion_rate_ci_95": cr_ci_95,
        "average_order_value": aov,
        "average_order_value_ci_95": aov_ci_95,
        "revenue_per_session": rps,
        "revenue": round(revenue, 2),
    }


def run_evaluation(sessions: int = 500) -> dict:
    if sessions < 1:
        raise ValueError("sessions must be at least one")
    catalog_db.reset_catalog()
    products = sorted(catalog_db.list_all(), key=lambda item: item.id)
    baseline_revenue = agent_revenue = 0.0
    baseline_purchases = agent_purchases = 0
    baseline_order_values: list[float] = []
    agent_order_values: list[float] = []
    upsell_offered = upsell_accepted = cross_offered = cross_accepted = 0

    # Growth attribution totals
    base_product_revenue = 0.0
    upsell_incremental_revenue = 0.0
    cross_sell_incremental_revenue = 0.0

    for index in range(sessions):
        product = products[index % len(products)]
        # Headroom model: One in five buyers has upgrade headroom; others retain standard budgets
        budget = product.price * (3.0 if index % 5 == 0 else (1.20 if index % 4 else 0.85))

        # Shared underlying purchase propensity (fair, unskewed baseline vs AgentCart)
        has_purchase_propensity = _decision(index, "shared_buyer_propensity", 65)

        # Baseline: direct keyword lookup for the target item
        if product.stock > 0 and product.price <= budget and has_purchase_propensity:
            baseline_purchases += 1
            baseline_revenue += product.price
            baseline_order_values.append(product.price)

        # AgentCart: Intent discovery + Contextual Recommendations + Deterministic Policy Gate
        if not (product.stock > 0 and product.price <= budget and has_purchase_propensity):
            continue

        base_val = product.price
        order_total = product.price
        upsell = growth_engine.get_upsell_candidate(product, budget)
        cross = growth_engine.get_cross_sell_candidate(product, budget)

        # Step 1: Evaluate Upsell candidate
        upsell_accepted_in_session = False
        if upsell:
            upsell_offered += 1
            candidate = upsell["upsell_product"]
            # Grounded acceptance probability for premium upgrade
            if candidate["price"] <= budget and _decision(index, "upsell_acceptance", 25):
                delta = candidate["price"] - product.price
                order_total = candidate["price"]
                upsell_accepted += 1
                upsell_accepted_in_session = True
                upsell_incremental_revenue += delta

        # Step 2: Evaluate Cross-Sell candidate (if no upsell accepted)
        if cross and not upsell_accepted_in_session:
            cross_offered += 1
            candidate = cross["cross_sell_product"]
            if order_total + candidate["price"] <= budget and _decision(index, "cross_sell_acceptance", 22):
                add_price = candidate["price"]
                order_total += add_price
                cross_accepted += 1
                cross_sell_incremental_revenue += add_price

        # Deterministic Policy Ceiling (Hard Spending Cap <= INR 10,000)
        if order_total <= 10_000:
            agent_purchases += 1
            agent_revenue += order_total
            agent_order_values.append(order_total)
            base_product_revenue += base_val

    baseline = _summary(baseline_revenue, baseline_purchases, sessions, baseline_order_values)
    agentcart = _summary(agent_revenue, agent_purchases, sessions, agent_order_values)
    
    aov_lift = round(agentcart["average_order_value"] - baseline["average_order_value"], 2)
    aov_lift_percent = round((aov_lift / baseline["average_order_value"] * 100), 2) if baseline["average_order_value"] else 0.0
    rps_lift = round(agentcart["revenue_per_session"] - baseline["revenue_per_session"], 2)
    rps_lift_percent = round((rps_lift / baseline["revenue_per_session"] * 100), 2) if baseline["revenue_per_session"] else 0.0

    result = {
        "methodology": "Synthetic, deterministic catalog evaluation with shared buyer propensities; results are not live revenue.",
        "statistical_design": {
            "shared_propensity_enforced": True,
            "confidence_level": "95%",
            "deterministic_seed_generator": "SHA-256 session hashing"
        },
        "baseline": baseline,
        "agentcart": {
            **agentcart,
            "upsell_acceptance_rate_percent": round(upsell_accepted / upsell_offered * 100, 2) if upsell_offered else 0.0,
            "cross_sell_acceptance_rate_percent": round(cross_accepted / cross_offered * 100, 2) if cross_offered else 0.0,
            "net_incremental_revenue": round(agent_revenue - baseline_revenue, 2),
            "aov_lift": aov_lift,
            "aov_lift_percent": aov_lift_percent,
            "rps_lift": rps_lift,
            "rps_lift_percent": rps_lift_percent,
            "attribution": {
                "base_product_revenue": round(base_product_revenue, 2),
                "upsell_incremental_revenue": round(upsell_incremental_revenue, 2),
                "cross_sell_incremental_revenue": round(cross_sell_incremental_revenue, 2),
            }
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
