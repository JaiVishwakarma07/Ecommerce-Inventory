"""Unit tests for ProductRepository.search_for_assistant."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.product_repository import ProductRepository
from app.schemas.assistant import AssistantSearchFilters


@pytest.mark.anyio
async def test_search_for_assistant_filters_by_max_price_and_stock(
    db_session: AsyncSession,
) -> None:
    from app.models.product import Product

    db_session.add_all(
        [
            Product(
                name="Budget Laptop",
                description="cheap laptop",
                sku="LAP-001",
                price=Decimal("8999.00"),
                quantity=2,
                category="electronics",
                image_url="",
            ),
            Product(
                name="Premium Laptop",
                description="expensive",
                sku="LAP-002",
                price=Decimal("45000.00"),
                quantity=1,
                category="electronics",
                image_url="",
            ),
            Product(
                name="Sold Out Laptop",
                description="none left",
                sku="LAP-003",
                price=Decimal("5000.00"),
                quantity=0,
                category="electronics",
                image_url="",
            ),
        ]
    )
    await db_session.commit()

    repo = ProductRepository()
    filters = AssistantSearchFilters(
        search="laptop",
        max_price=Decimal("10000"),
        include_out_of_stock=False,
    )
    results = await repo.search_for_assistant(db_session, filters=filters, limit=5)

    assert len(results) == 1
    assert results[0].sku == "LAP-001"


@pytest.mark.anyio
async def test_search_for_assistant_respects_limit_five(db_session: AsyncSession) -> None:
    from app.models.product import Product

    for i in range(7):
        db_session.add(
            Product(
                name=f"Widget {i}",
                description="",
                sku=f"W-{i}",
                price=Decimal("10.00"),
                quantity=10,
                category="general",
                image_url="",
            )
        )
    await db_session.commit()

    repo = ProductRepository()
    results = await repo.search_for_assistant(
        db_session,
        filters=AssistantSearchFilters(search="widget"),
        limit=5,
    )
    assert len(results) == 5
