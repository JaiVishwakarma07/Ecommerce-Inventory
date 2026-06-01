"""Unit tests for assistant schemas and answer builder."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.schemas.assistant import AssistantSearchFilters, build_assistant_answer
from app.schemas.product import ProductResponse


def _product(product_id: int, name: str) -> ProductResponse:
    now = datetime.now(timezone.utc)
    return ProductResponse(
        id=product_id,
        name=name,
        description="",
        sku=f"SKU-{product_id}",
        price=Decimal("99.99"),
        quantity=5,
        category="general",
        image_url="",
        created_at=now,
        updated_at=now,
    )


def test_build_assistant_answer_zero_results() -> None:
    answer = build_assistant_answer([], query="laptop under 10000")
    assert "No in-stock products" in answer


def test_build_assistant_answer_one_result() -> None:
    answer = build_assistant_answer([_product(1, "Budget Laptop")], query="laptop")
    assert "Found 1 product" in answer


def test_build_assistant_answer_multiple_results() -> None:
    products = [_product(1, "A"), _product(2, "B")]
    answer = build_assistant_answer(products, query="gadget")
    assert "Found 2 products" in answer


def test_assistant_search_filters_defaults() -> None:
    filters = AssistantSearchFilters.model_validate({})
    assert filters.search is None
    assert filters.include_out_of_stock is False


def test_assistant_search_filters_ignores_product_ids_from_llm() -> None:
    filters = AssistantSearchFilters.model_validate(
        {
            "search": "laptop",
            "product_ids": [999, 1000],
            "products": [{"id": 1}],
        }
    )
    assert filters.search == "laptop"
    assert not hasattr(filters, "product_ids") or getattr(filters, "product_ids", None) is None
