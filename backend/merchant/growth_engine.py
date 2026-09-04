import json
import os
import sqlite3
from typing import Any, Dict, Optional

from backend.audit.ledger import audit_ledger
from backend.security.policy_engine import policy_engine

from backend.merchant.catalog import catalog_db
from backend.merchant.models import CartItem, OrderProposal, Product

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "audit", "audit_ledger.db")


class GrowthEngine:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _item_type(self, product: Product) -> Optional[str]:
        text = f"{product.name} {product.description}".lower()
        for item_type, terms in {
            "keyboard": ("keyboard",), "mouse": ("mouse",), "cable": ("cable", "hdmi"),
            "hub": ("hub", "adapter"), "charger": ("charger", "gan"), "coffee": ("coffee", "beans"),
        }.items():
            if any(term in text for term in terms):
                return item_type
        return None

    def _upgrade_summary(self, base: Product, candidate: Product) -> Optional[str]:
        """Return catalog-proven specification differences, never marketing claims."""
        differences = []
        for key, value in candidate.specs.items():
            base_value = base.specs.get(key)
            if base_value is None:
                differences.append(f"{key}={value}")
            elif isinstance(value, (int, float)) and isinstance(base_value, (int, float)) and value > base_value:
                differences.append(f"{key}={value} versus {base_value}")
            elif value != base_value:
                differences.append(f"{key}={value} versus {base_value}")
        return "; ".join(differences[:2]) or None

    def get_upsell_candidate(self, base_product: Product, max_budget: Optional[float] = None, quantity: int = 1) -> Optional[Dict[str, Any]]:
        """Find an in-stock, same-kind catalog upgrade that fits user and policy limits."""
        if quantity < 1 or base_product.stock < quantity:
            return None
        base_type = self._item_type(base_product)
        for candidate in sorted(catalog_db.list_all(), key=lambda product: (product.price, product.id)):
            if candidate.id == base_product.id or candidate.stock < quantity or candidate.price <= base_product.price:
                continue
            if candidate.category != base_product.category or self._item_type(candidate) != base_type:
                continue
            total = candidate.price * quantity
            if (max_budget is not None and total > max_budget) or total > policy_engine.config.max_single_transaction_limit:
                continue
            summary = self._upgrade_summary(base_product, candidate)
            if summary:
                return {
                    "original_product_id": base_product.id,
                    "original_product_name": base_product.name,
                    "original_price": base_product.price,
                    "upsell_product": candidate.model_dump(),
                    "price_delta": candidate.price - base_product.price,
                    "reason": f"Catalog-listed upgrade to {candidate.name} over {base_product.name}: {summary}.",
                }
        return None

    def get_cross_sell_candidate(self, base_product: Product, max_budget: Optional[float] = None, quantity: int = 1) -> Optional[Dict[str, Any]]:
        """Find only reciprocal, merchant-maintained compatibility relationships."""
        if quantity < 1 or base_product.stock < quantity:
            return None
        for candidate in sorted(catalog_db.list_all(), key=lambda product: (product.price, product.id)):
            if candidate.id not in base_product.compatible_product_ids:
                continue
            if base_product.id not in candidate.compatible_product_ids or candidate.stock < quantity:
                continue
            combined_total = (base_product.price + candidate.price) * quantity
            if (max_budget is not None and combined_total > max_budget) or combined_total > policy_engine.config.max_single_transaction_limit:
                continue
            return {
                "base_product_id": base_product.id,
                "cross_sell_product": candidate.model_dump(),
                "additional_price": candidate.price,
                "reason": f"Merchant catalog marks {candidate.name} as compatible with {base_product.name}.",
            }
        return None

    def interact_offer(self, session_id: str, offer_type: str, action: str, item_id: str, base_product_id: Optional[str] = None, quantity: int = 1) -> Dict[str, Any]:
        """Record an interaction only for a previously proposed, catalog-valid offer."""
        action = action.lower()
        if offer_type not in {"upsell", "cross_sell"} or action not in {"accept", "accepted", "reject", "rejected"}:
            return {"status": "ERROR", "message": "Invalid growth offer action."}
        if quantity < 1:
            return {"status": "ERROR", "message": "Offer quantity must be at least one."}
        product = catalog_db.get_by_id(item_id)
        if not product:
            return {"status": "ERROR", "message": f"Product '{item_id}' not found in catalog."}

        proposal_event = f"{offer_type.upper()}_PROPOSED"
        offer = next((
            log for log in reversed(audit_ledger.get_logs_by_session(session_id))
            if log.event_type == proposal_event and log.details.get("offered_product_id") == item_id
            and (base_product_id is None or log.details.get("base_product_id") == base_product_id)
        ), None)
        if not offer:
            return {"status": "ERROR", "message": "This catalog item was not offered for this session."}

        details = offer.details
        base_product = catalog_db.get_by_id(details["base_product_id"])
        if not base_product:
            return {"status": "ERROR", "message": "The original product is no longer in the catalog."}
        offered_quantity = details.get("quantity", 1)
        if quantity != offered_quantity:
            return {"status": "ERROR", "message": "Offer quantity does not match the proposed offer."}
        if offer_type == "cross_sell" and (
            product.id not in base_product.compatible_product_ids
            or base_product.id not in product.compatible_product_ids
        ):
            return {"status": "ERROR", "message": "This cross-sell is not catalog-compatible with the original product."}
        if offer_type == "upsell" and (
            product.category != base_product.category
            or self._item_type(product) != self._item_type(base_product)
            or product.price <= base_product.price
            or not self._upgrade_summary(base_product, product)
        ):
            return {"status": "ERROR", "message": "This upsell is not a catalog-grounded upgrade."}
        decision_events = {f"{offer_type.upper()}_ACCEPTED", f"{offer_type.upper()}_REJECTED"}
        if any(
            log.event_type in decision_events
            and log.details.get("product_id") == product.id
            and log.details.get("base_product_id") == base_product.id
            for log in audit_ledger.get_logs_by_session(session_id)
        ):
            return {"status": "ERROR", "message": "This offer has already been decided."}

        accepted = action in {"accept", "accepted"}
        incremental_revenue = 0.0
        if accepted:
            if product.stock < quantity or base_product.stock < quantity:
                return {"status": "ERROR", "message": "An item in this offer is out of stock."}
            if offer_type == "upsell":
                items = [CartItem(product_id=product.id, quantity=quantity, unit_price=product.price, name=product.name)]
                incremental_revenue = (product.price - base_product.price) * quantity
            else:
                items = [
                    CartItem(product_id=base_product.id, quantity=quantity, unit_price=base_product.price, name=base_product.name),
                    CartItem(product_id=product.id, quantity=quantity, unit_price=product.price, name=product.name),
                ]
                incremental_revenue = product.price * quantity
            total = sum(item.unit_price * item.quantity for item in items)
            recorded_budget = details.get("max_budget")
            if recorded_budget is not None and total > recorded_budget:
                return {"status": "ERROR", "message": "This offer exceeds the buyer's recorded budget."}
            policy_result = policy_engine.verify_order_proposal(
                session_id,
                OrderProposal(merchant_id="merchant_rzp_tech_01", items=items, total_amount=total, user_goal=f"Accepted {offer_type} offer"),
            )
            if not policy_result.is_valid:
                return {"status": "ERROR", "message": f"Policy rejected offer: {policy_result.reason}"}

        suffix = "ACCEPTED" if accepted else "REJECTED"
        entry = audit_ledger.record(
            session_id=session_id,
            event_type=f"{offer_type.upper()}_{suffix}",
            status="SUCCESS" if accepted else "INFO",
            summary=f"User {suffix} {offer_type.replace('_', '-')} offer for '{product.name}' (INR {product.price:,.2f})",
            details={"session_id": session_id, "offer_type": offer_type, "action": action, "product_id": product.id,
                     "base_product_id": base_product.id, "price": product.price, "quantity": quantity,
                     "incremental_revenue": incremental_revenue},
        )
        resp = {
            "status": "SUCCESS",
            "message": entry.summary,
            "product": product.model_dump(),
            "audit_entry": entry.model_dump(),
            "action": "accepted" if accepted else "declined"
        }
        if accepted:
            resp.update({
                "items": [item.model_dump() for item in items],
                "total_amount": total,
                "verification": policy_result.model_dump(),
                "proposal": OrderProposal(merchant_id="merchant_rzp_tech_01", items=items, total_amount=total, user_goal=f"Accepted {offer_type} offer").model_dump(),
                "hitl_token": policy_result.hitl_token if policy_result.status == "HITL_REQUIRED" else None
            })
        return resp

    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate growth metrics from ledger events rather than in-memory counters."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT session_id) FROM audit_logs")
        total_sessions = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM audit_logs WHERE event_type = 'RECOMMENDATION'")
        recommendation_opportunities = cursor.fetchone()[0] or 0
        cursor.execute("SELECT details FROM audit_logs WHERE event_type = 'PAYMENT_CAPTURED' AND status = 'SUCCESS'")
        total_revenue = 0.0
        settled_orders = set()
        for (raw_details,) in cursor.fetchall():
            try:
                details = json.loads(raw_details)
                order_id = details.get("order_id", details.get("razorpay_order_id"))
                # The order is the financial unit: an accidental duplicate audit event
                # must never become another purchase or another unit of revenue.
                if not order_id or order_id in settled_orders:
                    continue
                settled_orders.add(order_id)
                total_revenue += float(details.get("amount", details.get("amount_paise", 0) / 100.0))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        purchases = len(settled_orders)

        counts = {}
        for name in ("UPSELL_PROPOSED", "UPSELL_ACCEPTED", "UPSELL_REJECTED", "CROSS_SELL_PROPOSED", "CROSS_SELL_ACCEPTED", "CROSS_SELL_REJECTED"):
            cursor.execute("SELECT COUNT(*) FROM audit_logs WHERE event_type = ?", (name,))
            counts[name] = cursor.fetchone()[0] or 0
        cursor.execute("SELECT details FROM audit_logs WHERE event_type IN ('UPSELL_ACCEPTED', 'CROSS_SELL_ACCEPTED')")
        incremental_revenue = 0.0
        for (raw_details,) in cursor.fetchall():
            try:
                incremental_revenue += float(json.loads(raw_details).get("incremental_revenue", 0.0))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        conn.close()

        upsell_opportunities = counts["UPSELL_PROPOSED"]
        cross_sell_opportunities = counts["CROSS_SELL_PROPOSED"]
        return {
            "total_sessions": total_sessions, "recommendation_opportunities": recommendation_opportunities, "purchases": purchases,
            "conversion_rate": round((purchases / total_sessions * 100.0) if total_sessions else 0.0, 2),
            "total_revenue": round(total_revenue, 2), "average_order_value": round((total_revenue / purchases) if purchases else 0.0, 2),
            "upsell_opportunities": upsell_opportunities, "upsell_accepted": counts["UPSELL_ACCEPTED"], "upsell_rejected": counts["UPSELL_REJECTED"],
            "upsell_acceptance_rate": round((counts["UPSELL_ACCEPTED"] / upsell_opportunities * 100.0) if upsell_opportunities else 0.0, 2),
            "cross_sell_opportunities": cross_sell_opportunities, "cross_sell_accepted": counts["CROSS_SELL_ACCEPTED"], "cross_sell_rejected": counts["CROSS_SELL_REJECTED"],
            "cross_sell_acceptance_rate": round((counts["CROSS_SELL_ACCEPTED"] / cross_sell_opportunities * 100.0) if cross_sell_opportunities else 0.0, 2),
            "incremental_revenue": round(incremental_revenue, 2),
            "revenue_per_session": round((total_revenue / total_sessions) if total_sessions else 0.0, 2),
        }


growth_engine = GrowthEngine()
