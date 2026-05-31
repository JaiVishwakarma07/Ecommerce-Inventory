# GET /products Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver public `GET /products` returning plain `Product[]` with optional `?search=`, backed by async persistence and a minimal dev seed.

**Architecture:** Thin vertical slice — `app/routers/products.py` → `ProductService` → `ProductRepository` → `Product` ORM. No auth on this route. Browse requests omit `limit` (no SQL cap).

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic v2, pytest + httpx AsyncClient, structlog

**Scope source:** `docs/harness-traces/get-products/brainstorm.md`, `specs/002-product-catalog/spec.md` (US1)

---

> This document defines **signatures and test names only** — no implementation bodies.

## File Map

| File | Role |
|------|------|
| `app/models/product.py` | `Product` ORM |
| `app/schemas/product.py` | `ProductResponse` (+ helpers) |
| `app/repositories/product_repository.py` | `ProductRepository` |
| `app/services/product_service.py` | `ProductService` |
| `app/routers/products.py` | `GET /products` handler + DI |
| `app/scripts/seed_products.py` | Idempotent dev seed |
| `app/main.py` | Register `products_router` |
| `app/database.py` | Import `Product` for `create_all` |
| `tests/integration/test_products.py` | HTTP integration tests |
| `tests/contract/test_products_contract.py` | Contract / OpenAPI alignment |

---

## ORM Model (reference)

```python
# app/models/product.py
class Product(Base):
    __tablename__ = "products"
    id: Mapped[int]
    name: Mapped[str]
    description: Mapped[str]
    sku: Mapped[str]
    price: Mapped[Decimal]  # Numeric(10, 2)
    quantity: Mapped[int]
    category: Mapped[str]
    image_url: Mapped[str]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

---

## Repository Layer Signatures

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import Product


class ProductRepository:
    async def list_products(
        self,
        db: AsyncSession,
        *,
        search: str | None = None,
    ) -> list[Product]:
        """
        Return all products matching optional search.
        - Trim search; empty/whitespace → no filter.
        - Case-insensitive partial match on name, sku, category (OR).
        - No LIMIT (browse slice).
        """
        ...
```

---

## Service Layer Signatures

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import Product
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductResponse


class ProductService:
    def __init__(self, repository: ProductRepository) -> None: ...

    async def list_products(
        self,
        db: AsyncSession,
        *,
        search: str | None = None,
    ) -> list[ProductResponse]:
        ...

    @staticmethod
    def _to_response(product: Product) -> ProductResponse:
        """Map ORM → API; coerce image_url None → \"\"."""
        ...
```

---

## Router & Dependency Signatures

```python
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_session_with_request
from app.repositories.product_repository import ProductRepository
from app.services.product_service import ProductService
from app.schemas.product import ProductResponse


router = APIRouter(tags=["products"])


def get_product_repository() -> ProductRepository: ...


def get_product_service(
    repository: ProductRepository = Depends(get_product_repository),
) -> ProductService: ...


@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    request: Request,
    search: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session_with_request),
    service: ProductService = Depends(get_product_service),
) -> list[ProductResponse]:
    ...
```

**`app/main.py`**

```python
from app.routers.products import router as products_router

app.include_router(products_router)
```

---

## Pydantic Schemas Needed

```python
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str = Field(min_length=1, max_length=255)
    description: str
    sku: str = Field(min_length=1, max_length=255)
    price: Decimal  # serializes as JSON number
    quantity: int = Field(ge=0)
    category: str = Field(min_length=1, max_length=100)
    image_url: str = ""
    created_at: datetime
    updated_at: datetime

    @field_validator("image_url", mode="before")
    @classmethod
    def coerce_image_url(cls, value: object) -> str:
        ...
```

**Out of scope for this slice (defer to US3):**

```python
class ProductWrite(BaseModel):
    ...
```

---

## Seed Script Signature

```python
# app/scripts/seed_products.py
async def seed_products(db: AsyncSession) -> int:
    """Insert default catalog rows if SKU missing. Returns count inserted."""

async def main() -> None:
    """CLI entry: open session, run seed_products, commit."""
    ...
```

---

## Test Fixtures (signatures only)

```python
# tests/conftest.py (additions)
@pytest.fixture
async def async_client():
    ...

@pytest.fixture
async def db_session():
    ...

async def insert_product(
    db: AsyncSession,
    *,
    name: str,
    sku: str,
    price: Decimal = Decimal("9.99"),
    quantity: int = 10,
    category: str = "general",
    description: str = "",
    image_url: str = "",
) -> Product:
    ...

async def insert_products_bulk(
    db: AsyncSession,
    count: int,
    *,
    prefix: str = "SKU",
) -> list[Product]:
    """Insert `count` products for no-limit test (e.g. 101 rows)."""
    ...
```

---

## Exact Test Case Names And Assertions

### Contract Tests (`tests/contract/test_products_contract.py`)

- `test_get_products_path_exists_in_contract`
  - asserts OpenAPI paths include `/products` with `get` operation
- `test_get_products_has_no_security_requirement`
  - asserts `GET /products` operation `security` is empty or absent (public)
- `test_get_products_response_is_array_of_product`
  - asserts 200 response schema is `array` with `$ref` to `Product` component
- `test_product_schema_required_fields`
  - asserts component lists `id`, `name`, `description`, `sku`, `price`, `quantity`, `category`, `image_url`, `created_at`, `updated_at`
- `test_product_schema_image_url_default_is_empty_string`
  - asserts `image_url` type is `string` (not nullable)

### Integration Tests (`tests/integration/test_products.py`)

- `test_list_products_without_auth_returns_200_and_array`
  - asserts `GET /products` without `Authorization` returns `200`
  - asserts `isinstance(body, list)`
- `test_list_products_empty_catalog_returns_empty_array`
  - asserts `GET /products` returns `200` and `[]` when no rows exist
- `test_list_products_returns_product_shape`
  - asserts each item has keys: `id`, `name`, `description`, `sku`, `price`, `quantity`, `category`, `image_url`, `created_at`, `updated_at`
  - asserts `password` / internal fields absent
- `test_list_products_image_url_never_null`
  - asserts every item has `"image_url"` key and value is `str` (not `null`)
- `test_list_products_includes_zero_quantity_item`
  - asserts seeded product with `quantity: 0` appears in response array
- `test_list_products_search_matches_name`
  - asserts `?search=widget` returns only products whose `name` matches (case-insensitive partial)
- `test_list_products_search_matches_sku`
  - asserts `?search=wgt-001` returns product with matching `sku`
- `test_list_products_search_matches_category`
  - asserts `?search=electronics` returns products in matching `category`
- `test_list_products_search_whitespace_only_returns_all`
  - asserts `?search=%20%20` returns same count as unfiltered list
- `test_list_products_without_limit_returns_all_when_over_100_rows`
  - asserts after seeding 101+ products, `GET /products` (no `limit`) returns `len(body) >= 101`
- `test_list_products_price_is_numeric_json`
  - asserts `price` in response is JSON number (not string)
- `test_list_products_quantity_is_integer_json`
  - asserts `quantity` in response is JSON integer

### Route Access Policy (`tests/contract/test_route_access_policy.py`)

Create file if missing.

- `test_get_products_is_public_allowlisted`
  - asserts `("GET", "/products")` is treated as public (status `< 401` without token)

---

## Spec Coverage Map

| Requirement | Test(s) |
|-------------|---------|
| FR-001 plain `Product[]` | `test_list_products_without_auth_returns_200_and_array`, `test_get_products_response_is_array_of_product` |
| FR-002 optional `search` | `test_list_products_search_matches_*` (name, sku, category) |
| FR-003 no default cap | `test_list_products_without_limit_returns_all_when_over_100_rows` |
| FR-013 zero stock visible | `test_list_products_includes_zero_quantity_item` |
| FR-015 `image_url` never null | `test_list_products_image_url_never_null`, `test_product_schema_image_url_default_is_empty_string` |
| Public, no auth | `test_get_products_has_no_security_requirement`, `test_get_products_is_public_allowlisted` |

---

## Self-Review

- **Spec coverage:** US1 acceptance scenarios mapped to integration tests above.
- **Placeholder scan:** None.
- **Type consistency:** `list_products` returns `list[Product]` (repo) and `list[ProductResponse]` (service); router `response_model=list[ProductResponse]`.

---

## Verification Command

```bash
pytest tests/contract/test_products_contract.py tests/integration/test_products.py tests/contract/test_route_access_policy.py -v
```
