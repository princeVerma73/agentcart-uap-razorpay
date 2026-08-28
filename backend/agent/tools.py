from typing import List, Dict, Any, Optional
from merchant.catalog import catalog_db
from merchant.models import CatalogQuery, Product, OrderProposal, CartItem
from security.policy_engine import policy_engine

def tool_search_catalog(query: str = "", category: str = "", max_price: Optional[float] = None) -> List[Dict[str, Any]]:
    """Query merchant inventory by keyword, category, or maximum price."""
    q = CatalogQuery(
        query=query,
        category=category if category and category != "all" else None,
        max_price=max_price,
        in_stock_only=False  # We want to see stock numbers so agent can reason about availability
    )
    products = catalog_db.search(q)
    return [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "price": p.price,
            "stock": p.stock,
            "rating": p.rating,
            "specs": p.specs,
            "merchant": p.merchant_name
        }
        for p in products
    ]

def tool_get_product_details(product_id: str) -> Optional[Dict[str, Any]]:
    """Fetch complete specifications and live stock status for a specific product."""
    p = catalog_db.get_by_id(product_id)
    if not p:
        return None
    return p.model_dump()

def tool_check_policy_limits() -> Dict[str, Any]:
    """Retrieve current financial safety limits and autonomous pre-authorization thresholds."""
    return {
        "max_single_transaction_limit": policy_engine.config.max_single_transaction_limit,
        "auto_approve_limit": policy_engine.config.auto_approve_limit,
        "allowed_categories": policy_engine.config.allowed_categories,
        "require_human_approval_always": policy_engine.config.require_human_approval_always
    }
