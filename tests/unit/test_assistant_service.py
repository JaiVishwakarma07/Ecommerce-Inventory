"""Unit tests for AssistantService orchestration."""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.llm_client import LlmUnavailableError
from app.repositories.product_repository import ProductRepository
from app.schemas.assistant import AssistantSearchFilters
from app.services.assistant_service import AssistantService


class LlmClientProtocol(Protocol):
    async def extract_filters(self, query: str) -> AssistantSearchFilters: ...


class FakeLlmClient:
    def __init__(
        self,
        filters: AssistantSearchFilters | None = None,
        error: Exception | None = None,
    ) -> None:
        self._filters = filters or AssistantSearchFilters(
            search="laptop",
            max_price=Decimal("10000"),
        )
        self._error = error

    async def extract_filters(self, query: str) -> AssistantSearchFilters:
        if self._error:
            raise self._error
        return self._filters


@pytest.mark.anyio
async def test_assistant_service_returns_db_products_only(
    db_session: AsyncSession,
) -> None:
    from app.models.product import Product

    db_session.add(
        Product(
            name="Budget Laptop",
            description="",
            sku="LAP-001",
            price=Decimal("8999.00"),
            quantity=3,
            category="electronics",
            image_url="",
        )
    )
    await db_session.commit()

    service = AssistantService(FakeLlmClient(), ProductRepository())
    result = await service.query(db_session, "laptop under 10000")

    assert len(result.products) == 1
    assert result.products[0].sku == "LAP-001"
    assert "Found 1 product" in result.answer


@pytest.mark.anyio
async def test_assistant_service_propagates_llm_unavailable(
    db_session: AsyncSession,
) -> None:
    service = AssistantService(
        FakeLlmClient(error=LlmUnavailableError("down")),
        ProductRepository(),
    )
    with pytest.raises(LlmUnavailableError):
        await service.query(db_session, "laptop")


@pytest.mark.anyio
async def test_assistant_service_ignores_fake_product_ids_in_llm_payload(
    db_session: AsyncSession,
) -> None:
    from app.models.product import Product

    db_session.add(
        Product(
            name="Real Laptop",
            description="",
            sku="LAP-REAL",
            price=Decimal("5000.00"),
            quantity=2,
            category="electronics",
            image_url="",
        )
    )
    await db_session.commit()

    filters_with_fake_ids = AssistantSearchFilters.model_validate(
        {
            "search": "laptop",
            "product_ids": [99999],
            "products": [{"id": 88888}],
        }
    )
    service = AssistantService(FakeLlmClient(filters=filters_with_fake_ids), ProductRepository())
    result = await service.query(db_session, "laptop")

    assert len(result.products) == 1
    assert result.products[0].sku == "LAP-REAL"
    assert all(product.id != 99999 for product in result.products)
