from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Product(BaseModel):
    id: str
    name: str
    category: str
    description: str
    price: float = Field(..., description="Price in INR")
    stock: int = Field(..., description="Available inventory units")
    specs: Dict[str, Any] = Field(default_factory=dict)
    rating: float = 4.5
    merchant_id: str = "merchant_rzp_tech_01"
    merchant_name: str = "CloudGear Technologies"
    merchant_trust_score: float = 0.98
    compatible_product_ids: List[str] = Field(default_factory=list)

class CatalogQuery(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    max_price: Optional[float] = None
    in_stock_only: bool = True
    limit: int = 10

class CartItem(BaseModel):
    product_id: str
    quantity: int = 1
    unit_price: float
    name: str

class OrderProposal(BaseModel):
    merchant_id: str
    items: List[CartItem]
    total_amount: float
    user_goal: str
    delivery_speed: str = "standard"
    currency: str = "INR"
