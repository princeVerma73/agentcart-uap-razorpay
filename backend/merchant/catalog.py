from typing import List, Optional, Dict, Any
from .models import Product, CatalogQuery

# Initial Realistic Tech/Office Hardware & Supplies Catalog
DEFAULT_PRODUCTS = [
    Product(
        id="prod_usb_c_hub_01",
        name="Anker 7-in-1 USB-C Hub (4K HDMI, 100W PD, SD Reader)",
        category="accessories",
        description="High-speed USB-C multi-port adapter with 4K@60Hz HDMI, 100W Power Delivery pass-through, dual USB 3.0 ports.",
        price=2499.0,
        stock=25,
        specs={"ports": 7, "power_delivery_watts": 100, "hdmi_res": "4K@60Hz", "warranty_months": 18},
        rating=4.8,
        merchant_name="Anker India Official",
        compatible_product_ids=["prod_hdmi_cable_4k", "prod_macbook_charger_100w"]
    ),
    Product(
        id="prod_hdmi_cable_4k",
        name="Ultra High Speed 4K@60Hz HDMI 2.1 Braided Cable (2M)",
        category="cables",
        description="Heavy duty braided 4K/8K HDR HDMI cable for monitors and dev workstations.",
        price=799.0,
        stock=40,
        specs={"length_meters": 2, "bandwidth_gbps": 48, "connector": "Gold Plated HDMI 2.1"},
        rating=4.7,
        merchant_name="CableTech Pro",
        compatible_product_ids=["prod_usb_c_hub_01"]
    ),
    Product(
        id="prod_mx_master_3s",
        name="Logitech MX Master 3S Wireless Performance Mouse",
        category="peripherals",
        description="Quiet click ergonomic wireless mouse with 8K DPI sensor and MagSpeed scrolling.",
        price=8995.0,
        stock=12,
        specs={"dpi": 8000, "connectivity": "Bluetooth / Logi Bolt", "battery_life_days": 70},
        rating=4.9,
        merchant_name="Logitech Authorized Store",
        compatible_product_ids=["prod_mech_keyboard_k2", "prod_budget_mech_keyboard"]
    ),
    Product(
        id="prod_mech_keyboard_k2",
        name="Keychron K2 V2 Wireless Mechanical Keyboard (Gateron Brown)",
        category="peripherals",
        description="75% layout compact Bluetooth mechanical keyboard with Mac & Windows layout support.",
        price=6499.0,
        stock=15,
        specs={"switches": "Gateron Brown", "layout": "75%", "backlight": "RGB", "battery_mah": 4000},
        rating=4.8,
        merchant_name="Keychron India",
        compatible_product_ids=["prod_budget_ergonomic_mouse", "prod_mx_master_3s"]
    ),
    Product(
        id="prod_budget_mech_keyboard",
        name="Redragon K552 Mechanical Keyboard (Tactile Blue Switches)",
        category="peripherals",
        description="Tenkeyless TKL compact mechanical gaming and programming keyboard with anti-ghosting keys.",
        price=2499.0,
        stock=25,
        specs={"switches": "Tactile Blue", "layout": "TKL (87 Keys)", "backlight": "Rainbow LED", "use_case": "programming"},
        rating=4.5,
        merchant_name="Redragon India",
        compatible_product_ids=["prod_budget_ergonomic_mouse", "prod_mx_master_3s"]
    ),

    Product(
        id="prod_coffee_beans_1kg",
        name="Blue Tokai Attikan Estate Dark Roast Coffee Beans (1kg)",
        category="pantry",
        description="Freshly roasted specialty arabica whole beans for espresso & French press.",
        price=1450.0,
        stock=30,
        specs={"roast": "Dark", "origin": "Biligirirangan Hills", "grind": "Whole Beans", "weight_kg": 1.0},
        rating=4.9,
        merchant_name="Blue Tokai Direct"
    ),
    Product(
        id="prod_macbook_charger_100w",
        name="GaN 100W Fast Charger with Dual USB-C & USB-A",
        category="accessories",
        description="Compact GaN III fast charger suitable for MacBook Pro, iPad, and Android phones.",
        price=2999.0,
        stock=20,
        specs={"technology": "GaN III", "total_output_watts": 100, "ports": 3},
        rating=4.6,
        merchant_name="PowerVolt Store",
        compatible_product_ids=["prod_usb_c_hub_01"]
    ),
    Product(
        id="prod_budget_ergonomic_mouse",
        name="Portronics Toad One Ergonomic Wireless Mouse",
        category="peripherals",
        description="Budget-friendly vertical optical mouse with adjustable DPI and silent clicks.",
        price=699.0,
        stock=50,
        specs={"dpi": 1600, "connectivity": "2.4GHz Wireless", "ergonomic": True},
        rating=4.2,
        merchant_name="Portronics India",
        compatible_product_ids=["prod_mech_keyboard_k2", "prod_budget_mech_keyboard"]
    )
]

class MerchantCatalogDB:
    def __init__(self):
        self.products: Dict[str, Product] = {p.id: p.model_copy() for p in DEFAULT_PRODUCTS}

    def reset_catalog(self):
        """Reset all products to their default prices and stock."""
        self.products = {p.id: p.model_copy() for p in DEFAULT_PRODUCTS}

    def list_all(self) -> List[Product]:
        return list(self.products.values())

    def get_by_id(self, product_id: str) -> Optional[Product]:
        return self.products.get(product_id)

    def search(self, query: CatalogQuery) -> List[Product]:
        results = []
        q = (query.query or "").lower().strip()
        
        for p in self.products.values():
            # In stock filter
            if query.in_stock_only and p.stock <= 0:
                continue
                
            # Category filter
            if query.category and query.category.lower() != "all":
                if p.category.lower() != query.category.lower():
                    continue
                    
            # Price filter
            if query.max_price is not None and p.price > query.max_price:
                continue
                
            # Keyword search in name, description, category, and specs
            if q:
                specs_str = " ".join([f"{k}:{v}" for k, v in p.specs.items()]).lower()
                text_to_search = f"{p.name} {p.description} {p.category} {p.merchant_name} {specs_str}".lower()
                
                stop_words = {"for", "office", "setup", "under", "with", "and", "the", "a", "an", "in", "on", "to", "buy", "need", "want", "purchase", "restock", "inr"}
                tokens = [t for t in q.split() if t not in stop_words and len(t) >= 2]
                if tokens and not any(t in text_to_search for t in tokens):
                    continue

                    
            results.append(p)
            if len(results) >= query.limit:
                break
                
        return results

    # Simulation Hooks for Demonstrating Resilience & Guardrails
    def simulate_price_surge(self, product_id: str, new_price: float):
        if product_id in self.products:
            self.products[product_id].price = new_price

    def simulate_stock_depletion(self, product_id: str):
        if product_id in self.products:
            self.products[product_id].stock = 0

catalog_db = MerchantCatalogDB()
