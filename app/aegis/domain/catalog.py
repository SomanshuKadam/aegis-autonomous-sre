from __future__ import annotations

from aegis.domain.models import Product


CATALOG = {
    "sku-001": Product(product_id="product-001", sku="sku-001", name="Aegis Notebook", search_text="aegis notebook reliability", price_minor=1299),
    "sku-002": Product(product_id="product-002", sku="sku-002", name="Signal Mug", search_text="signal mug observability", price_minor=899),
}


def browse(query: str | None = None) -> list[Product]:
    needle = (query or "").strip().lower()
    return [product for product in CATALOG.values() if not needle or needle in product.search_text.lower() or needle in product.name.lower()]


def product(sku: str) -> Product | None:
    return CATALOG.get(sku)
