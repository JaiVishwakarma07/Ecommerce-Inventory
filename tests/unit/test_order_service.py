"""Unit tests for OrderService helpers (POST /orders slice)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.schemas.order import OrderLineItemCreate
from app.services.order_service import compute_total_amount, merge_line_items


@pytest.mark.anyio
async def test_merge_line_items_sums_duplicate_product_ids() -> None:
    merged = merge_line_items(
        [
            OrderLineItemCreate(product_id=1, quantity=2),
            OrderLineItemCreate(product_id=1, quantity=3),
            OrderLineItemCreate(product_id=2, quantity=1),
        ]
    )

    assert len(merged) == 2
    by_id = {line.product_id: line.quantity for line in merged}
    assert by_id[1] == 5
    assert by_id[2] == 1


@pytest.mark.anyio
async def test_merge_line_items_preserves_single_product_unchanged() -> None:
    merged = merge_line_items([OrderLineItemCreate(product_id=7, quantity=4)])

    assert len(merged) == 1
    assert merged[0].product_id == 7
    assert merged[0].quantity == 4


@pytest.mark.anyio
async def test_compute_total_amount_sums_line_totals() -> None:
    total = compute_total_amount(
        [
            (2, Decimal("799.00")),
            (1, Decimal("2499.00")),
        ]
    )

    assert total == Decimal("4097.00")


@pytest.mark.anyio
async def test_compute_total_amount_empty_list_returns_zero() -> None:
    assert compute_total_amount([]) == Decimal("0")
