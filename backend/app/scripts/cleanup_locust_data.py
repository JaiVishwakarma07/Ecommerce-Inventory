"""Remove Locust load-test users, products, and orders from the dev database.

Preserves seed admin, seed catalog SKUs (WGT-001, GAD-002, OUT-003), and all other
non-Locust users/products/orders.

Usage (from backend/):
    python -m app.scripts.cleanup_locust_data
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import create_db_engine, create_session_factory
from app.models.order import Order, OrderLineItem
from app.models.product import Product
from app.models.user import User

SEED_SKUS = frozenset({"WGT-001", "GAD-002", "OUT-003"})
SEED_PRODUCT_DEFAULTS: dict[str, dict[str, object]] = {
    "WGT-001": {
        "name": "Widget",
        "description": "A useful widget",
        "price": Decimal("19.99"),
        "quantity": 10,
        "category": "general",
        "image_url": "",
    },
    "GAD-002": {
        "name": "Gadget Pro",
        "description": "Premium gadget",
        "price": Decimal("49.50"),
        "quantity": 5,
        "category": "electronics",
        "image_url": "https://example.com/gadget.jpg",
    },
    "OUT-003": {
        "name": "Out of Stock Item",
        "description": "Unavailable for now",
        "price": Decimal("9.99"),
        "quantity": 0,
        "category": "general",
        "image_url": "",
    },
}


def _is_locust_user(email: str) -> bool:
    normalized = email.strip().lower()
    return normalized == "locust-customer@example.com" or normalized.startswith("locust-")


def _is_locust_product(product: Product) -> bool:
    sku = product.sku.upper()
    if sku.startswith("LOC-"):
        return True
    name = product.name.strip()
    return name.startswith("Locust ")


async def cleanup(session: AsyncSession) -> dict[str, int]:
    locust_users_result = await session.execute(select(User))
    locust_user_ids = [
        user.id for user in locust_users_result.scalars() if _is_locust_user(user.email)
    ]

    deleted_line_items = 0
    deleted_orders = 0
    if locust_user_ids:
        order_ids_result = await session.execute(
            select(Order.id).where(Order.user_id.in_(locust_user_ids))
        )
        order_ids = [row[0] for row in order_ids_result.all()]
        if order_ids:
            line_items_result = await session.execute(
                delete(OrderLineItem).where(OrderLineItem.order_id.in_(order_ids))
            )
            deleted_line_items = line_items_result.rowcount or 0
            orders_result = await session.execute(
                delete(Order).where(Order.id.in_(order_ids))
            )
            deleted_orders = orders_result.rowcount or 0

    deleted_users = 0
    if locust_user_ids:
        users_result = await session.execute(
            delete(User).where(User.id.in_(locust_user_ids))
        )
        deleted_users = users_result.rowcount or 0

    products_result = await session.execute(select(Product))
    locust_product_ids = [
        product.id
        for product in products_result.scalars()
        if _is_locust_product(product)
    ]

    deleted_products = 0
    if locust_product_ids:
        delete_result = await session.execute(
            delete(Product).where(Product.id.in_(locust_product_ids))
        )
        deleted_products = delete_result.rowcount or 0

    restored_seed = 0
    inserted_seed = 0
    for sku, defaults in SEED_PRODUCT_DEFAULTS.items():
        existing = await session.execute(select(Product).where(Product.sku == sku))
        product = existing.scalar_one_or_none()
        if product is None:
            session.add(Product(sku=sku, **defaults))
            inserted_seed += 1
            continue
        await session.execute(
            update(Product)
            .where(Product.id == product.id)
            .values(**defaults)
        )
        restored_seed += 1

    await session.commit()
    return {
        "deleted_orders": deleted_orders,
        "deleted_line_items": deleted_line_items,
        "deleted_users": deleted_users,
        "deleted_products": deleted_products,
        "restored_seed_products": restored_seed,
        "inserted_seed_products": inserted_seed,
    }


async def main() -> None:
    engine = create_db_engine(settings.resolved_database_url)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        stats = await cleanup(session)
    await engine.dispose()
    print("Locust cleanup complete:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
