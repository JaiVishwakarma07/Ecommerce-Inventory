# POST /orders Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver customer `POST /orders` with SPA-aligned `201` + `Order` JSON, mandatory line snapshots, and atomic stock decrement.

**Architecture:** `orders` router → `OrderService.checkout()` (owns transaction) → `OrderRepository` + `ProductRepository` flush-only stock helpers. Full `OrderRepository` implemented upfront; only checkout wired in service/router this slice.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Pydantic v2, pytest + httpx AsyncClient, structlog

**Scope source:** `docs/harness-traces/post-orders/brainstorm.md`, `specs/003-orders-checkout/spec.md` (US1), tasks T001–T021

---

> This document defines **signatures and test names only** — no implementation bodies.

## File Map

| File | Role |
|------|------|
| `app/models/order.py` | `Order`, `OrderLineItem` ORM |
| `app/schemas/order.py` | Request/response Pydantic models |
| `app/repositories/order_repository.py` | `OrderRepository` (full) |
| `app/repositories/product_repository.py` | Add `get_by_ids`, `adjust_quantity` |
| `app/services/order_service.py` | `OrderService`, helpers, domain errors |
| `app/dependencies/auth.py` | `require_customer` |
| `app/routers/orders.py` | `POST /orders` + DI |
| `app/main.py` | Register `orders` router |
| `app/database.py` | Import order models for `create_all` |
| `tests/unit/test_order_service.py` | Pure helpers |
| `tests/integration/test_orders.py` | HTTP checkout flows |
| `tests/contract/test_orders_contract.py` | OpenAPI alignment |

---

## ORM Models (reference)

```python
# app/models/order.py
class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int]
    user_id: Mapped[int]  # FK users.id
    status: Mapped[str]
    total_amount: Mapped[Decimal]  # Numeric(12, 2)
    shipping_address: Mapped[str]
    stock_restored: Mapped[bool]  # internal; not in API
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    line_items: Mapped[list["OrderLineItem"]]


class OrderLineItem(Base):
    __tablename__ = "order_line_items"
    id: Mapped[int]
    order_id: Mapped[int]  # FK orders.id CASCADE
    product_id: Mapped[int]  # no FK to products
    product_name: Mapped[str]
    quantity: Mapped[int]
    unit_price: Mapped[Decimal]  # Numeric(10, 2)
    order: Mapped[Order]
```

---

## Domain Exceptions

```python
# app/services/order_service.py

class InsufficientStockError(Exception):
  def __init__(self, product_id: int) -> None: ...

class ProductNotFoundForOrderError(Exception):
  def __init__(self, product_id: int) -> None: ...

class OrderNotFoundError(Exception):
  ...

class ForbiddenOrderAccessError(Exception):
  ...
```

*`OrderNotFoundError` / `ForbiddenOrderAccessError` implemented for repo completeness; not raised in US1 router.*

---

## Repository Layer Signatures

### `ProductRepository` (extend existing class)

```python
# app/repositories/product_repository.py

class ProductRepository:
    async def get_by_ids(
        self,
        db: AsyncSession,
        product_ids: list[int],
    ) -> dict[int, Product]:
        """
        Return {product_id: Product} for all found ids.
        Missing ids omitted (service validates completeness).
        Does not commit.
        """
        ...

    async def adjust_quantity(
        self,
        db: AsyncSession,
        product_id: int,
        delta: int,
    ) -> Product | None:
        """
        product.quantity += delta; await db.flush().
        Return None if product missing.
        Does not commit.
        """
        ...
```

### `OrderRepository` (new)

```python
# app/repositories/order_repository.py
from decimal import Decimal
from typing import TypedDict
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.order import Order


class OrderLineSnapshot(TypedDict):
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal


class OrderRepository:
    async def create_with_line_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        shipping_address: str,
        total_amount: Decimal,
        lines: list[OrderLineSnapshot],
    ) -> Order:
        """
        Insert Order (status=pending, stock_restored=False) + line items.
        await db.flush(); refresh order with line_items loaded.
        Does not commit.
        """
        ...

    async def get_by_id(
        self,
        db: AsyncSession,
        order_id: int,
    ) -> Order | None:
        """Eager-load line_items (selectinload)."""
        ...

    async def list_for_user(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> list[Order]:
        """
        Orders for user_id, created_at DESC, with line_items.
        (Implemented now; used in US2.)
        """
        ...

    async def list_all(
        self,
        db: AsyncSession,
        *,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[Order]:
        """
        All orders, created_at DESC, with line_items.
        If status set, filter exact match.
        If limit set, apply min(limit, 100).
        (Implemented now; used in US3.)
        """
        ...

    async def update_status(
        self,
        db: AsyncSession,
        order: Order,
        *,
        status: str,
        stock_restored: bool | None = None,
    ) -> Order:
        """
        Set order.status, bump updated_at.
        If stock_restored is not None, set order.stock_restored.
        flush + refresh line_items.
        Does not commit.
        (Implemented now; used in US4.)
        """
        ...
```

---

## Service Layer Signatures

```python
# app/services/order_service.py
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.order import Order
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order import OrderCreate, OrderLineItemCreate, OrderResponse


def merge_line_items(
    items: list[OrderLineItemCreate],
) -> list[OrderLineItemCreate]:
    """Sum quantities for duplicate product_id; preserve one row per id."""
    ...


def compute_total_amount(
    lines: list[tuple[int, Decimal]],
) -> Decimal:
    """Sum of quantity * unit_price for each (quantity, unit_price) pair."""
    ...


class OrderService:
    def __init__(
        self,
        order_repository: OrderRepository,
        product_repository: ProductRepository,
    ) -> None: ...

    async def checkout(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        payload: OrderCreate,
    ) -> OrderResponse:
        """
        merge → load products → validate stock → snapshot → create order
        → decrement stock → commit (rollback on failure).
        Raises ProductNotFoundForOrderError, InsufficientStockError.
        """
        ...

    @staticmethod
    def _to_response(order: Order) -> OrderResponse:
        """Map ORM Order + line_items → OrderResponse (nested items)."""
        ...
```

**Deferred service methods (US2–US4; not called by `POST /orders`):**

```python
    async def list_mine(
        self,
        db: AsyncSession,
        *,
        user_id: int,
    ) -> list[OrderResponse]:
        ...

    async def get_order(
        self,
        db: AsyncSession,
        *,
        order_id: int,
        user_id: int,
        is_admin: bool,
    ) -> OrderResponse:
        ...

    async def list_admin(
        self,
        db: AsyncSession,
        *,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[OrderResponse]:
        ...

    async def update_status(
        self,
        db: AsyncSession,
        *,
        order_id: int,
        status: str,
    ) -> OrderResponse:
        ...
```

---

## Dependency Signatures

```python
# app/dependencies/auth.py
from app.schemas.auth import RegisterUserResponse

async def require_customer(
    current_user: RegisterUserResponse = Depends(get_current_user),
) -> RegisterUserResponse:
    """role == 'customer' else HTTP 403."""
    ...
```

---

## Router & DI Signatures

```python
# app/routers/orders.py
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_session_with_request
from app.dependencies.auth import require_customer
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.auth import RegisterUserResponse
from app.schemas.order import OrderCreate, OrderResponse
from app.services.order_service import OrderService


router = APIRouter(tags=["orders"])


def get_order_repository() -> OrderRepository: ...


def get_product_repository() -> ProductRepository: ...


def get_order_service(
    order_repository: OrderRepository = Depends(get_order_repository),
    product_repository: ProductRepository = Depends(get_product_repository),
) -> OrderService: ...


@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
    request: Request,
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: OrderService = Depends(get_order_service),
    current_user: RegisterUserResponse = Depends(require_customer),
) -> OrderResponse:
    """
    Map ProductNotFoundForOrderError → 404.
    Map InsufficientStockError → 409.
  Emit structlog order_checkout_*.
    """
    ...
```

**`app/main.py`**

```python
from app.routers.orders import router as orders_router

app.include_router(orders_router)
```

---

## Pydantic Schemas Needed

```python
# app/schemas/order.py
from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

OrderStatus = Literal[
    "pending",
    "processing",
    "shipped",
    "delivered",
    "cancelled",
]


class OrderLineItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(ge=1)
    quantity: int = Field(ge=1)


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shipping_address: str = Field(min_length=1)
    items: list[OrderLineItemCreate] = Field(min_length=1)

    @field_validator("shipping_address", mode="before")
    @classmethod
    def strip_shipping_address(cls, value: object) -> str:
        ...


class OrderLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal

    @field_serializer("unit_price")
    def serialize_unit_price(self, value: Decimal) -> float:
        ...


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: OrderStatus
    total_amount: Decimal
    shipping_address: str
    created_at: datetime
    updated_at: datetime
    items: list[OrderLineItemResponse]

    @field_serializer("total_amount")
    def serialize_total_amount(self, value: Decimal) -> float:
        ...
```

**Defined now, not used by `POST /orders` (US4):**

```python
class OrderStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: OrderStatus
```

---

## Test Fixtures (signatures only)

```python
# tests/conftest.py (addition)
def order_checkout_payload(
    product_id: int,
    *,
    quantity: int = 1,
    shipping_address: str = "42 MG Road, Bengaluru, India",
) -> dict[str, object]:
    ...


# tests/integration/test_orders.py
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

async def _async_client() -> AsyncIterator[AsyncClient]:
    ...

async def count_orders(db: AsyncSession) -> int:
    ...
```

---

## Exact Test Case Names And Assertions

### Unit Tests (`tests/unit/test_order_service.py`)

- `test_merge_line_items_sums_duplicate_product_ids`
  - asserts two lines with same `product_id` become one line with summed `quantity`
  - asserts distinct `product_id` values remain separate rows
- `test_merge_line_items_preserves_single_product_unchanged`
  - asserts one-item input returns one item with same `product_id` and `quantity`
- `test_compute_total_amount_sums_line_totals`
  - asserts `[(2, Decimal("799.00")), (1, Decimal("2499.00"))]` → `Decimal("4097.00")`
- `test_compute_total_amount_empty_list_returns_zero`
  - asserts `compute_total_amount([]) == Decimal("0")`

### Contract Tests (`tests/contract/test_orders_contract.py`)

- `test_post_orders_path_exists_in_contract`
  - asserts OpenAPI `paths` include `/orders` with `post` operation
- `test_post_orders_requires_bearer_security`
  - asserts `POST /orders` operation `security` includes `bearerAuth`
- `test_post_orders_request_schema_order_create`
  - asserts request body schema requires `shipping_address` and `items`
- `test_post_orders_response_schema_is_order`
  - asserts `201` response `$ref` is `#/components/schemas/Order`
- `test_order_schema_required_fields`
  - asserts `Order` component includes `id`, `user_id`, `status`, `total_amount`, `shipping_address`, `created_at`, `updated_at`, `items`
- `test_order_schema_uses_items_not_line_items`
  - asserts `Order` has property `items` (array); no `line_items` property
- `test_order_line_item_schema_snapshot_fields`
  - asserts line item schema includes `product_name`, `unit_price`, `product_id`, `quantity`, `id`

### Integration Tests (`tests/integration/test_orders.py`)

- `test_order_tables_exist_after_bootstrap`
  - asserts `orders` and `order_line_items` tables exist after DB bootstrap
- `test_post_orders_checkout_returns_201_with_snapshots_and_decrements_stock`
  - asserts customer `POST /orders` returns `201`
  - asserts body keys: `id`, `user_id`, `status`, `total_amount`, `shipping_address`, `created_at`, `updated_at`, `items`
  - asserts `status == "pending"`
  - asserts `items[0].product_name` matches catalog product name at checkout time
  - asserts `items[0].unit_price` equals catalog price as JSON number
  - asserts `total_amount == quantity * unit_price` (for single-line case)
  - asserts `products.quantity` decreased by ordered quantity in DB
- `test_post_orders_merge_duplicate_product_ids_in_request`
  - asserts payload with two entries same `product_id` creates one line with summed quantity and correct `total_amount`
- `test_post_orders_insufficient_stock_returns_409_and_no_order_row`
  - asserts `quantity` exceeding stock returns `409`
  - asserts response `detail` mentions `product_id`
  - asserts order count unchanged; product quantity unchanged
- `test_post_orders_missing_product_returns_404`
  - asserts non-existent `product_id` returns `404`
  - asserts `detail` references product
- `test_post_orders_as_admin_returns_403`
  - asserts admin Bearer on `POST /orders` returns `403`
- `test_post_orders_without_token_returns_401`
  - asserts no `Authorization` header returns `401`
- `test_post_orders_empty_items_returns_422`
  - asserts `items: []` returns `422`
- `test_post_orders_empty_shipping_address_returns_422`
  - asserts `shipping_address: ""` or whitespace-only returns `422`
- `test_post_orders_invalid_quantity_returns_422`
  - asserts `quantity: 0` returns `422`

### Route Access Policy (`tests/contract/test_route_access_policy.py`)

- `test_post_orders_requires_authentication`
  - asserts `POST /orders` without token returns `401` (not public allowlist)

---

## Spec Coverage Map (US1)

| Requirement | Test(s) |
|-------------|---------|
| FR-001 customer checkout / admin 403 | `test_post_orders_checkout_*`, `test_post_orders_as_admin_returns_403` |
| FR-002 request shape | `test_post_orders_request_schema_order_create`, validation 422 tests |
| FR-003 201 + full Order | `test_post_orders_checkout_returns_201_with_snapshots_and_decrements_stock` |
| FR-004 snapshots | same + `test_order_line_item_schema_snapshot_fields` |
| FR-005 total_amount server-side | `test_post_orders_checkout_*`, `test_compute_total_amount_*` |
| FR-006 stock decrement / 409 | `test_post_orders_checkout_*`, `test_post_orders_insufficient_stock_*` |
| FR-007 missing product 404 | `test_post_orders_missing_product_returns_404` |
| FR-014 all routes auth | `test_post_orders_without_token_returns_401`, `test_post_orders_requires_authentication` |
| FR-016 nested `items` | `test_order_schema_uses_items_not_line_items` |
| FR-017 merge duplicates | `test_merge_line_items_*`, `test_post_orders_merge_duplicate_product_ids_in_request` |

---

## Self-Review

- **Spec coverage:** US1 FR-001–FR-007, FR-014, FR-016–FR-017 mapped above.
- **Placeholder scan:** None.
- **Type consistency:** `OrderLineSnapshot` (repo) fed from service after validation; `OrderResponse.items` is `list[OrderLineItemResponse]`; router `response_model=OrderResponse`.

---

## Verification Command

```bash
pytest tests/contract/test_orders_contract.py \
  tests/integration/test_orders.py \
  tests/unit/test_order_service.py \
  tests/contract/test_route_access_policy.py \
  -k "checkout or merge or total or post_orders or order_tables" -v
```

---

## Execution Handoff

Plan complete and saved to `docs/harness-traces/post-orders/plan.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration

2. **Inline Execution** — execute in this session with checkpoints (`executing-plans`)

Which approach?
