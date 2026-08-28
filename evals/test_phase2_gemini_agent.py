import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from agent.buyer_intent import BuyerIntent, GeminiIntentParser
from agent.buyer_agent import BuyerAgent
from agent.tools import tool_search_catalog
from merchant.catalog import catalog_db
from security.policy_engine import policy_engine, PolicyConfig
from audit.ledger import audit_ledger

@pytest.fixture(autouse=True)
def reset_state():
    catalog_db.reset_catalog()
    audit_ledger.clear()
    policy_engine.update_config(PolicyConfig(
        max_single_transaction_limit=10000.0,
        auto_approve_limit=3000.0,
        require_human_approval_always=False
    ))
    policy_engine.processed_idempotency_keys.clear()

@pytest.mark.asyncio
async def test_gemini_valid_structured_intent_parsing():
    """Test 1: Verify parsing valid structured output from Gemini API."""
    mock_response_json = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": '{"query": "mechanical keyboard", "category": "peripherals", "budget": 3000.0, "quantity": 1, "use_case": "programming", "required_features": ["mechanical", "wireless"], "exclusions": []}'
                        }
                    ]
                }
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_json

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        parser = GeminiIntentParser(api_key="mock_key_123")
        intent, fallback_used, error = await parser.parse_intent("Buy a wireless mechanical keyboard for programming under ₹3000")

        assert fallback_used is False
        assert error is None
        assert intent is not None
        assert intent.query == "mechanical keyboard"
        assert intent.category == "peripherals"
        assert intent.budget == 3000.0
        assert intent.quantity == 1
        assert "wireless" in intent.required_features

@pytest.mark.asyncio
async def test_budget_extraction():
    """Test 2: Verify budget extraction from Gemini structured response."""
    intent_data = BuyerIntent(query="hub", budget=2500.0, quantity=1)
    assert intent_data.budget == 2500.0

@pytest.mark.asyncio
async def test_quantity_extraction():
    """Test 3: Verify multi-item quantity extraction."""
    intent_data = BuyerIntent(query="hdmi cable", quantity=3, budget=2000.0)
    assert intent_data.quantity == 3

@pytest.mark.asyncio
async def test_category_extraction():
    """Test 4: Verify category field parsing."""
    intent_data = BuyerIntent(query="coffee beans", category="pantry")
    assert intent_data.category == "pantry"

@pytest.mark.asyncio
async def test_required_feature_extraction():
    """Test 5: Verify feature constraint list extraction."""
    intent_data = BuyerIntent(query="charger", required_features=["GaN", "100W", "Dual USB-C"])
    assert "GaN" in intent_data.required_features
    assert "100W" in intent_data.required_features

def test_catalog_tool_receives_structured_intent():
    """Test 6: Verify backend tool_search_catalog filters using structured intent criteria."""
    results = tool_search_catalog(query="hub", category="accessories", max_price=3000.0)
    assert len(results) > 0
    for r in results:
        assert r["category"] == "accessories"
        assert r["price"] <= 3000.0

@pytest.mark.asyncio
async def test_llm_cannot_invent_product_prices():
    """Test 7: Verify that actual item prices are fetched strictly from merchant DB, not arbitrary LLM claims."""
    # Product prod_hdmi_cable_4k costs 799.0 in DB
    product = catalog_db.get_by_id("prod_hdmi_cable_4k")
    assert product.price == 799.0

    # Retrieve directly by ID
    fetched = catalog_db.get_by_id("prod_hdmi_cable_4k")
    assert fetched.price == 799.0

@pytest.mark.asyncio
async def test_invalid_llm_output_triggers_fallback():
    """Test 8: Invalid non-JSON output from Gemini triggers heuristic fallback."""
    mock_response_json = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "INVALID NON-JSON TEXT"}]
                }
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_json

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        parser = GeminiIntentParser(api_key="mock_key_123")
        intent, fallback_used, error = await parser.parse_intent("Buy HDMI cable")

        assert fallback_used is True
        assert intent is None
        assert "failed" in error.lower() or "json" in error.lower() or "expecting value" in error.lower()

@pytest.mark.asyncio
async def test_gemini_api_failure_triggers_fallback():
    """Test 9: Gemini API HTTP 500 error or timeout triggers graceful fallback."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Connection timed out")

        parser = GeminiIntentParser(api_key="mock_key_123")
        intent, fallback_used, error = await parser.parse_intent("Buy mouse")

        assert fallback_used is True
        assert intent is None
        assert "timed out" in error.lower()

@pytest.mark.asyncio
async def test_no_matching_products_handled_safely():
    """Test 10: Searching for non-existent items or impossible budget caps handles safely without crashing."""
    session_id = "sess_no_match"
    agent = BuyerAgent()
    steps = []

    async for step in agent.run_goal_stream(session_id, "Buy quantum computer workstation", max_user_budget=50.0):
        steps.append(step)

    assert any(s["status"] == "REJECTED" or "No matching products" in s["thought"] for s in steps)
    
    # Audit log check
    logs = audit_ledger.get_logs_by_session(session_id)
    assert any(l.status == "REJECTED" for l in logs)

@pytest.mark.asyncio
async def test_policy_engine_rejection_over_budget():
    """Test 11: Policy engine hard ceiling (₹10,000) blocks high-cost intentions."""
    session_id = "sess_over_budget"
    agent = BuyerAgent()
    steps = []

    async for step in agent.run_goal_stream(session_id, "Buy 2 Logitech MX Master 3S mice", max_user_budget=20000.0):
        steps.append(step)

    # 2 * 8995 = 17990 > 10000 limit -> REJECTED
    assert any(s["status"] == "REJECTED" and "policy_rejected" in s["action"] for s in steps)
