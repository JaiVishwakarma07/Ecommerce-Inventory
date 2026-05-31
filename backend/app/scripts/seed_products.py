"""Idempotent dev seed for manual catalog testing (Postman, curl)."""

from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import bootstrap_database, create_db_engine, create_session_factory
from app.config import settings
from app.models.product import Product

DEFAULT_PRODUCTS: tuple[dict[str, object], ...] = (
    {
        "name": "Widget",
        "description": "A useful widget",
        "sku": "WGT-001",
        "price": Decimal("19.99"),
        "quantity": 10,
        "category": "general",
        "image_url": "",
    },
    {
        "name": "Gadget Pro",
        "description": "Premium gadget",
        "sku": "GAD-002",
        "price": Decimal("49.50"),
        "quantity": 5,
        "category": "electronics",
        "image_url": "https://example.com/gadget.jpg",
    },
    {
        "name": "Out of Stock Item",
        "description": "Unavailable for now",
        "sku": "OUT-003",
        "price": Decimal("9.99"),
        "quantity": 0,
        "category": "general",
        "image_url": "",
    },
)


async def seed_products(session: AsyncSession) -> int:
    inserted = 0
    for item in DEFAULT_PRODUCTS:
        sku = str(item["sku"])
        existing = await session.execute(select(Product).where(Product.sku == sku))
        if existing.scalar_one_or_none() is not None:
            continue
        session.add(Product(**item))
        inserted += 1
    if inserted:
        await session.commit()
    return inserted


async def main() -> None:
    engine = create_db_engine(settings.resolved_database_url)
    await bootstrap_database(engine)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        count = await seed_products(session)
    await engine.dispose()
    print(f"Seeded {count} product(s). GET http://127.0.0.1:8000/products")


if __name__ == "__main__":
    asyncio.run(main())
