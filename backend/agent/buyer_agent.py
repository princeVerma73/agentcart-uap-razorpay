import asyncio
import json
import re
import uuid
from typing import Dict, Any, List, Optional, AsyncGenerator
from merchant.catalog import catalog_db
from merchant.models import OrderProposal, CartItem, Product
from security.policy_engine import policy_engine
from payments.razorpay_client import razorpay_service
from audit.ledger import audit_ledger
from .tools import tool_search_catalog, tool_get_product_details, tool_check_policy_limits
from .buyer_intent import BuyerIntent, gemini_intent_parser, GeminiIntentParser

class AgentExecutionStep(dict):
    def __init__(self, step_number: int, title: str, thought: str, action: str, status: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(
            step_number=step_number,
            title=title,
            thought=thought,
            action=action,
            status=status,
            data=data or {}
        )

class BuyerAgent:
    def __init__(self, intent_parser: Optional[GeminiIntentParser] = None):
        self.intent_parser = intent_parser or gemini_intent_parser

    async def run_goal_stream(self, session_id: str, goal: str, max_user_budget: Optional[float] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Autonomous Agentic Commerce Execution Loop with Gemini Intent & Structured Tool Calling.
        Follows NPCI UAP / AP2 protocol lifecycle.
        """
        step_idx = 1
        
        # Step 1: Goal Intake & Intent Decomposition via Gemini (or Fallback)
        audit_ledger.record(
            session_id=session_id,
            event_type="AGENT_INTAKE",
            status="SUCCESS",
            summary=f"New purchase intent received: '{goal}'",
            details={"goal": goal, "max_user_budget": max_user_budget}
        )
        
        intent, fallback_used, error_reason = await self.intent_parser.parse_intent(goal, max_user_budget)
        
        if fallback_used or not intent:
            # Fallback heuristic parser
            keywords = self._extract_search_keywords(goal)
            qty = self._extract_quantity(goal)
            intent = BuyerIntent(
                query=keywords[0] if keywords else goal,
                category=self._extract_category(goal),
                budget=max_user_budget,
                quantity=qty,
                required_features=keywords
            )
            
            audit_ledger.record(
                session_id=session_id,
                event_type="LLM_FALLBACK",
                status="WARNING",
                summary=f"Gemini intent parsing failed ({error_reason or 'Unavailable'}). Used heuristic fallback.",
                details={"reason": error_reason, "goal": goal}
            )

            yield AgentExecutionStep(
                step_number=step_idx,
                title="Goal Intent Parsing (Heuristic Fallback)",
                thought=f"Gemini LLM unavailable ({error_reason or 'Fallback mode'}). Derived search keywords: {keywords}, Qty: {qty}.",
                action="parse_intent_fallback",
                status="COMPLETED",
                data={"intent": intent.model_dump(), "fallback_used": True, "reason": error_reason}
            )
        else:
            audit_ledger.record(
                session_id=session_id,
                event_type="INTENT_PARSED",
                status="SUCCESS",
                summary=f"Structured intent parsed via Gemini: query='{intent.query}', category='{intent.category}'",
                details=intent.model_dump()
            )

            yield AgentExecutionStep(
                step_number=step_idx,
                title="Goal Intent Parsing (Gemini LLM)",
                thought=f"Parsed structured intent: Query='{intent.query}', Category='{intent.category or 'all'}', Budget=₹{intent.budget or 'Uncapped'}, Qty={intent.quantity}.",
                action="parse_intent_gemini",
                status="COMPLETED",
                data={"intent": intent.model_dump(), "fallback_used": False}
            )

        # The caller's cap is authoritative when both the parsed intent and UI provide one.
        if max_user_budget is not None:
            intent.budget = min(intent.budget, max_user_budget) if intent.budget is not None else max_user_budget

        await asyncio.sleep(0.3)
        step_idx += 1

        # Step 2: Query Merchant Catalog via MCP Catalog Tool
        yield AgentExecutionStep(
            step_number=step_idx,
            title="Merchant Catalog Search (Catalog Tool)",
            thought=f"Executing tool_search_catalog(query='{intent.query}', category='{intent.category or ''}', max_price={intent.budget}).",
            action="tool_search_catalog",
            status="IN_PROGRESS"
        )

        # Execute backend catalog search tool
        raw_candidates = tool_search_catalog(
            query=intent.query,
            category=intent.category or "",
            max_price=(intent.budget / intent.quantity) if intent.budget is not None else None
        )

        # Convert back to Product objects for validation
        candidate_products: List[Product] = []
        for raw in raw_candidates:
            p = catalog_db.get_by_id(raw["id"])
            if p:
                candidate_products.append(p)

        # Fallback search by keywords if query returned nothing
        if not candidate_products:
            for kw in intent.required_features or [intent.query]:
                fallback_results = catalog_db.search(type("Q", (), {
                    "query": kw,
                    "category": intent.category,
                    "max_price": intent.budget,
                    "in_stock_only": False,
                    "limit": 5
                }))
                candidate_products.extend(fallback_results)

        # Deduplicate candidates
        seen_ids = set()
        unique_candidates = []
        for p in candidate_products:
            if p.id not in seen_ids:
                seen_ids.add(p.id)
                unique_candidates.append(p)

        await asyncio.sleep(0.4)

        if not unique_candidates:
            audit_ledger.record(
                session_id=session_id,
                event_type="POLICY_CHECK",
                status="REJECTED",
                summary="No matching products found within requested budget/criteria.",
                details={"goal": goal, "intent": intent.model_dump()}
            )
            yield AgentExecutionStep(
                step_number=step_idx,
                title="No Matching Products Found",
                thought="No matching products were found within your budget.",
                action="abort",
                status="REJECTED",
                data={"error": "No matching products were found within your budget."}
            )
            return

        audit_ledger.record(
            session_id=session_id,
            event_type="TOOL_CALL",
            status="SUCCESS",
            summary=f"Catalog tool returned {len(unique_candidates)} candidate products.",
            details={"candidates": [p.id for p in unique_candidates], "tool_used": "search_catalog"}
        )

        yield AgentExecutionStep(
            step_number=step_idx,
            title="Catalog Discovery Complete",
            thought=f"Discovered {len(unique_candidates)} items matching criteria.",
            action="tool_search_catalog_done",
            status="COMPLETED",
            data={"candidates": [p.model_dump() for p in unique_candidates], "tool_used": "search_catalog"}
        )
        step_idx += 1

        # Step 3: Product Ranking & Grounded Recommendation Explanation
        yield AgentExecutionStep(
            step_number=step_idx,
            title="Specification & Budget Verification",
            thought="Filtering candidates against budget limits, stock availability, and verified specifications.",
            action="verify_inventory",
            status="IN_PROGRESS"
        )
        await asyncio.sleep(0.3)

        primary_match = self._pick_best_match(goal, intent, unique_candidates)
        if not primary_match:
            yield AgentExecutionStep(
                step_number=step_idx,
                title="No Matching Products Found",
                thought="No matching products were found within your requested criteria and budget constraint.",
                action="abort",
                status="REJECTED",
                data={"error": "No matching products were found within your budget/criteria."}
            )
            return

        target_qty = intent.quantity
        selected_items: List[CartItem] = []


        if primary_match.stock <= 0:

            # Stockout recovery
            audit_ledger.record(
                session_id=session_id,
                event_type="ERROR_RECOVERED",
                status="WARNING",
                summary=f"Primary choice '{primary_match.name}' is out of stock. Searching alternative.",
                details={"out_of_stock_item": primary_match.id}
            )

            yield AgentExecutionStep(
                step_number=step_idx,
                title="Stockout Detected -> Autonomous Fallback",
                thought=f"Item '{primary_match.name}' has 0 stock! Querying category '{primary_match.category}' for an in-stock alternative.",
                action="auto_recovery_search",
                status="RECOVERING"
            )
            await asyncio.sleep(0.4)

            alt_products = [p for p in catalog_db.list_all() if p.category == primary_match.category and p.stock > 0 and p.id != primary_match.id]
            if alt_products:
                alternative = alt_products[0]
                primary_match = alternative
                selected_items.append(CartItem(
                    product_id=alternative.id,
                    quantity=target_qty,
                    unit_price=alternative.price,
                    name=alternative.name
                ))
            else:
                yield AgentExecutionStep(
                    step_number=step_idx,
                    title="Out of Stock - No Alternative",
                    thought=f"All items in category '{primary_match.category}' are out of stock.",
                    action="abort",
                    status="REJECTED"
                )
                return
        else:
            selected_items.append(CartItem(
                product_id=primary_match.id,
                quantity=target_qty,
                unit_price=primary_match.price,
                name=primary_match.name
            ))

        # Discover Contextual Growth Opportunities (Upsell & Cross-Sell)
        from merchant.growth_engine import growth_engine
        upsell_cand = growth_engine.get_upsell_candidate(primary_match, intent.budget, target_qty)
        if upsell_cand:
            upsell_cand.update({
                "base_product_id": primary_match.id,
                "offered_product_id": upsell_cand["upsell_product"]["id"],
                "max_budget": intent.budget,
                "quantity": target_qty,
            })
            audit_ledger.record(
                session_id=session_id,
                event_type="UPSELL_PROPOSED",
                status="SUCCESS",
                summary=f"Upsell candidate proposed: '{upsell_cand['upsell_product']['name']}' (+₹{upsell_cand['price_delta']:,.2f})",
                details=upsell_cand
            )

        cross_sell_cand = growth_engine.get_cross_sell_candidate(primary_match, intent.budget, target_qty)
        if cross_sell_cand:
            cross_sell_cand.update({
                "offered_product_id": cross_sell_cand["cross_sell_product"]["id"],
                "max_budget": intent.budget,
                "quantity": target_qty,
            })
            audit_ledger.record(
                session_id=session_id,
                event_type="CROSS_SELL_PROPOSED",
                status="SUCCESS",
                summary=f"Cross-sell candidate proposed: '{cross_sell_cand['cross_sell_product']['name']}' (+₹{cross_sell_cand['additional_price']:,.2f})",
                details=cross_sell_cand
            )

        # Generate concise grounded explanation
        explanation = f"Recommended '{primary_match.name}' because it matches your requested {primary_match.category} specifications and budget of ₹{primary_match.price:,.2f}."
        
        audit_ledger.record(
            session_id=session_id,
            event_type="RECOMMENDATION",
            status="SUCCESS",
            summary=f"Recommended product '{primary_match.name}' for ₹{primary_match.price:,.2f}",
            details={"product_id": primary_match.id, "price": primary_match.price, "explanation": explanation}
        )

        yield AgentExecutionStep(
            step_number=step_idx,
            title="Product Recommendation Formulated",
            thought=explanation,
            action="recommend_product",
            status="COMPLETED",
            data={
                "recommendation": primary_match.model_dump(),
                "explanation": explanation,
                "upsell_candidate": upsell_cand,
                "cross_sell_candidate": cross_sell_cand
            }
        )

        step_idx += 1

        # Step 4: Construct Order Proposal
        total_price = sum(item.unit_price * item.quantity for item in selected_items)
        proposal = OrderProposal(
            merchant_id="merchant_rzp_tech_01",
            items=selected_items,
            total_amount=total_price,
            user_goal=goal
        )

        yield AgentExecutionStep(
            step_number=step_idx,
            title="Order Proposal Formulated",
            thought=f"Formulated proposal for {len(selected_items)} item(s). Total calculated from DB: ₹{total_price:,.2f}.",
            action="policy_engine_submit",
            status="COMPLETED",
            data={"proposal": proposal.model_dump()}
        )
        await asyncio.sleep(0.3)
        step_idx += 1

        # Step 5: Deterministic Policy Engine Verification
        verification = policy_engine.verify_order_proposal(session_id, proposal)

        if not verification.is_valid:
            yield AgentExecutionStep(
                step_number=step_idx,
                title="Policy Check: Transaction REJECTED",
                thought=f"Policy violation: {verification.reason}. Halting execution to protect funds.",
                action="policy_rejected",
                status="REJECTED",
                data={"verification": verification.model_dump()}
            )
            return

        yield AgentExecutionStep(
            step_number=step_idx,
            title="Deterministic Security & Policy Verification",
            thought=f"Proposal verified against DB limits and replay protection. Verified amount: ₹{verification.verified_total:,.2f}.",
            action="verify_guardrails",
            status="COMPLETED",
            data={"verification": verification.model_dump()}
        )
        await asyncio.sleep(0.3)
        step_idx += 1

        # Step 6: Branching: HITL vs Autonomous Auto-Approve
        if verification.status == "HITL_REQUIRED":
            yield AgentExecutionStep(
                step_number=step_idx,
                title="Human-in-the-Loop (HITL) Approval Required",
                thought=f"Order amount (₹{verification.verified_total:,.2f}) exceeds autonomous limit of ₹{policy_engine.config.auto_approve_limit:,.2f}. Pausing until human sign-off.",
                action="await_user_signature",
                status="PENDING_APPROVAL",
                data={
                    "verification": verification.model_dump(),
                    "proposal": proposal.model_dump(),
                    "session_id": session_id,
                    "hitl_token": verification.hitl_token
                }
            )
            return

        # Step 7: Autonomous Payment Execution via Razorpay Test Service
        yield AgentExecutionStep(
            step_number=step_idx,
            title="Autonomous Pre-Authorization Approved",
            thought=f"Order (₹{verification.verified_total:,.2f}) is within autonomous pre-auth limit. Calling Razorpay Orders API.",
            action="razorpay_order_create",
            status="COMPLETED"
        )
        await asyncio.sleep(0.4)

        rzp_order = razorpay_service.create_order(
            session_id=session_id,
            amount=verification.verified_total,
            receipt_id=f"rcpt_{session_id[:8]}",
            notes={"goal": goal, "agent": "AgentCart-Gemini-v2"},
            idempotency_key=verification.idempotency_key,
        )

        if razorpay_service.checkout_enabled:
            step_idx += 1
            yield AgentExecutionStep(
                step_number=step_idx,
                title="Razorpay Test Checkout Ready",
                thought="The order is policy-approved. Complete Razorpay Test Checkout to authorize payment.",
                action="razorpay_checkout",
                status="PENDING_PAYMENT",
                data={
                    "order": rzp_order,
                    "checkout": razorpay_service.checkout_options(rzp_order),
                    "items": [item.model_dump() for item in selected_items],
                    "verified_total": verification.verified_total,
                },
            )
            return

        settlement = razorpay_service.simulate_payment_settlement(
            session_id=session_id,
            order_id=rzp_order["id"],
            amount=verification.verified_total
        )
        policy_engine.mark_key_processed(verification.idempotency_key, session_id=session_id)

        step_idx += 1

        # Final Step: Transaction Settled & Sealed
        yield AgentExecutionStep(
            step_number=step_idx,
            title="Transaction Completed & Settled",
            thought="Order fulfilled successfully. Cryptographic receipt generated and recorded in audit ledger.",
            action="order_fulfilled",
            status="SUCCESS",
            data={
                "order": rzp_order,
                "settlement": settlement,
                "items": [item.model_dump() for item in selected_items],
                "verified_total": verification.verified_total,
                "audit_sealed": True
            }
        )

    def _extract_search_keywords(self, text: str) -> List[str]:
        text_lower = text.lower()
        keywords = []
        if "hub" in text_lower or "adapter" in text_lower or "anker" in text_lower:
            keywords.append("hub")
        if "cable" in text_lower or "hdmi" in text_lower:
            keywords.append("hdmi")
        if "mouse" in text_lower or "logitech" in text_lower or "master" in text_lower:
            keywords.append("mouse")
        if "keyboard" in text_lower or "keychron" in text_lower:
            keywords.append("keyboard")
        if "coffee" in text_lower or "beans" in text_lower or "tokai" in text_lower:
            keywords.append("coffee")
        if "charger" in text_lower or "gan" in text_lower or "power" in text_lower:
            keywords.append("charger")
            
        return keywords if keywords else ["hub", "cable", "mouse", "keyboard", "coffee", "charger"]

    def _extract_quantity(self, text: str) -> int:
        match = re.search(r'\b(\d+)\s*(units|pcs|pieces|items|cables|mice|chargers|keyboards|packs)?\b', text.lower())
        if match:
            try:
                qty = int(match.group(1))
                if 1 <= qty <= 50:
                    return qty
            except Exception:
                pass
        return 1

    def _extract_category(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        if "cable" in text_lower or "hdmi" in text_lower:
            return "cables"
        if "keyboard" in text_lower or "mouse" in text_lower:
            return "peripherals"
        if "hub" in text_lower or "charger" in text_lower:
            return "accessories"
        if "coffee" in text_lower or "beans" in text_lower:
            return "pantry"
        return None

    def _extract_item_type(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        if "keyboard" in text_lower:
            return "keyboard"
        if "mouse" in text_lower:
            return "mouse"
        if "cable" in text_lower or "hdmi" in text_lower:
            return "cable"
        if "hub" in text_lower or "adapter" in text_lower:
            return "hub"
        if "charger" in text_lower or "gan" in text_lower:
            return "charger"
        if "coffee" in text_lower or "beans" in text_lower:
            return "coffee"
        return None

    def _score_product_relevance(self, goal: str, intent: BuyerIntent, product: Product) -> float:
        target_item_type = self._extract_item_type(goal) or self._extract_item_type(intent.query)
        prod_text = f"{product.name} {product.description} {product.category} {json.dumps(product.specs)}".lower()
        
        # Hard penalty for item type mismatch (e.g. keyboard requested but product is mouse)
        if target_item_type:
            prod_item_type = self._extract_item_type(product.name) or self._extract_item_type(product.description)
            if prod_item_type and prod_item_type != target_item_type:
                return -10000.0  # Completely exclude mismatched item types

        score = 0.0

        # 1. Item type direct match (+1000)
        if target_item_type and target_item_type in prod_text:
            score += 1000.0

        # 2. Category match (+200)
        if intent.category and product.category.lower() == intent.category.lower():
            score += 200.0

        # 3. Required feature matches (+50 each)
        if intent.required_features:
            for feat in intent.required_features:
                if feat.lower() in prod_text:
                    score += 50.0

        # 4. Use case match (+30)
        if intent.use_case and intent.use_case.lower() in prod_text:
            score += 30.0

        # 5. User budget constraint. The deterministic policy engine remains the
        # authority for the hard transaction ceiling after an order is constructed.
        quantity = intent.quantity
        total = product.price * quantity
        if intent.budget is not None:
            if total <= intent.budget:
                score += 50.0
            else:
                score -= 5000.0  # Do not select over-budget products as primary choice
        # 6. Stock check
        # Stock penalty removed to allow out-of-stock products to be considered for primary match.
        # if product.stock <= 0:
        #     score -= 5000.0

        return score

    def _pick_best_match(self, goal: str, intent: BuyerIntent, candidates: List[Product]) -> Optional[Product]:
        scored_candidates = []
        for p in candidates:
            score = self._score_product_relevance(goal, intent, p)
            if score > 0:  # Only consider valid positive matches
                scored_candidates.append((score, p))

        if scored_candidates:
            scored_candidates.sort(key=lambda x: -x[0])
            return scored_candidates[0][1]

        all_prods = catalog_db.list_all()
        scored_all = []
        for p in all_prods:
            score = self._score_product_relevance(goal, intent, p)
            if score > 0:
                scored_all.append((score, p))

        if scored_all:
            scored_all.sort(key=lambda x: (-x[0], x[1].price))
            return scored_all[0][1]

        return None

buyer_agent = BuyerAgent()
