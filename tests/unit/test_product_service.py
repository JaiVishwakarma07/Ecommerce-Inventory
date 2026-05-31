"""Unit tests for ProductService domain error mapping."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.product_repository import DuplicateSkuError, ProductRepository
from app.schemas.product import ProductWrite
from app.services.product_service import DuplicateSku, ProductNotFound, ProductService


def _product_write(**overrides: object) -> ProductWrite:
    data = {
        "name": "Unit Test Product",
        "description": "Desc",
        "sku": "UNIT-001",
        "price": Decimal("9.99"),
        "quantity": 1,
        "category": "general",
        "image_url": "",
    }
    data.update(overrides)
    return ProductWrite(**data)


def _orm_product_stub(**overrides: object) -> MagicMock:
    from datetime import datetime, timezone

    product = MagicMock()
    product.id = overrides.get("id", 1)
    product.name = overrides.get("name", "Unit Test Product")
    product.description = overrides.get("description", "Desc")
    product.sku = overrides.get("sku", "UNIT-001")
    product.price = overrides.get("price", Decimal("9.99"))
    product.quantity = overrides.get("quantity", 1)
    product.category = overrides.get("category", "general")
    product.image_url = overrides.get("image_url", "")
    now = datetime.now(timezone.utc)
    product.created_at = overrides.get("created_at", now)
    product.updated_at = overrides.get("updated_at", now)
    return product


@pytest.mark.anyio
async def test_get_product_raises_not_found_when_repository_returns_none():
    repository = AsyncMock(spec=ProductRepository)
    repository.get_by_id.return_value = None
    service = ProductService(repository)

    with pytest.raises(ProductNotFound, match="Product not found"):
        await service.get_product(AsyncMock(), 999)

    repository.get_by_id.assert_awaited_once()


@pytest.mark.anyio
async def test_create_product_raises_duplicate_sku_from_repository():
    repository = AsyncMock(spec=ProductRepository)
    repository.create.side_effect = DuplicateSkuError("SKU already exists")
    service = ProductService(repository)

    with pytest.raises(DuplicateSku, match="SKU already exists"):
        await service.create_product(AsyncMock(), _product_write())

    repository.create.assert_awaited_once()


@pytest.mark.anyio
async def test_update_product_raises_not_found_when_repository_returns_none():
    repository = AsyncMock(spec=ProductRepository)
    repository.update.return_value = None
    service = ProductService(repository)

    with pytest.raises(ProductNotFound, match="Product not found"):
        await service.update_product(AsyncMock(), 1, _product_write())

    repository.update.assert_awaited_once()


@pytest.mark.anyio
async def test_delete_product_raises_not_found_when_repository_returns_false():
    repository = AsyncMock(spec=ProductRepository)
    repository.delete.return_value = False
    service = ProductService(repository)

    with pytest.raises(ProductNotFound, match="Product not found"):
        await service.delete_product(AsyncMock(), 1)

    repository.delete.assert_awaited_once()


@pytest.mark.anyio
async def test_create_product_passes_empty_image_url_to_repository():
    repository = AsyncMock(spec=ProductRepository)
    repository.create.return_value = _orm_product_stub()
    service = ProductService(repository)

    await service.create_product(AsyncMock(), _product_write(image_url=""))

    assert repository.create.await_args.kwargs["image_url"] == ""
