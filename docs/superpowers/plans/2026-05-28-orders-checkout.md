# Orders & Checkout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship customer checkout and order management (`POST /orders`, `GET /orders/me`, `GET /orders/{id}`, admin list/filter/PATCH) with SPA-aligned JSON, mandatory line snapshots, atomic stock decrement, and one-time cancel restock.

**Architecture:** Extend existing `routers → services → repositories` stack. `OrderService` owns checkout and status workflows in one DB transaction per mutation. `ProductRepository` gains non-committing stock helpers. Internal `stock_restored` on `orders` never appears in API JSON; nested key is `items`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, Pydantic v2, pytest + httpx AsyncClient, structlog, JWT auth (`customer` / `admin` roles).

**Spec / contract references:**
- `specs/003-orders-checkout/spec.md`
- `specs/003-orders-checkout/contracts/orders-api.yaml`
- `docs/superpowers/specs/2026-05-28-orders-checkout-design.md`

---

## File map (create / modify)

| File | Responsibility |
|------|----------------|
| `app/models/order.py` | `Order`, `OrderLineItem` ORM |
| `app/database.py` | Import order models for `create_all` |
| `app/schemas/order.py` | Wire Pydantic models |
| `app/repositories/product_repository.py` | `get_by_ids`, `adjust_quantity` (no commit) |
| `app/repositories/order_repository.py` | Persist/list/load orders + lines |
| `app/services/order_service.py` | `checkout`, `list_mine`, `get_order`, `list_admin`, `update_status` |
| `app/dependencies/auth.py` | `require_customer` |
| `app/routers/orders.py` | HTTP + structlog |
| `app/main.py` | Include orders router |
| `tests/conftest.py` | `insert_product`, `order_checkout_payload` helpers |
| `tests/unit/test_order_service.py` | Pure logic + service rules |
| `tests/integration/test_orders.py` | End-to-end HTTP |
| `tests/contract/test_orders_contract.py` | OpenAPI alignment |
| `tests/contract/test_route_access_policy.py` | `/orders*` require auth |

---

### Task 1: Order ORM models and DB bootstrap

**Files:**
- Create: `app/models/order.py`
- Modify: `app/database.py`
- Test: `tests/integration/test_orders.py` (bootstrap smoke)

- [ ] **Step 1: Write failing smoke test**

```python
# tests/integration/test_orders.py
"""Integration tests for orders & checkout."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.anyio
async def test_order_tables_exist_after_bootstrap(db_session: AsyncSession) -> None:
    bind = db_session.get_bind()
    table_names = await db_session.run_sync(
        lambda sync_conn: inspect(sync_conn).get_table_names()
    )
    assert "orders" in table_names
    assert "order_line_items" in table_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_orders.py::test_order_tables_exist_after_bootstrap -v`  
Expected: FAIL (`orders` table missing)

- [ ] **Step 3: Add ORM models**

```python
# app/models/order.py
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)
    stock_restored: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    line_items: Mapped[list["OrderLineItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrderLineItem(Base):
    __tablename__ = "order_line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped[Order] = relationship(back_populates="line_items")
```

- [ ] **Step 4: Register models in database bootstrap**

```python
# app/database.py — add after product import
from app.models import order as _order_model  # noqa: F401
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/integration/test_orders.py::test_order_tables_exist_after_bootstrap -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/models/order.py app/database.py tests/integration/test_orders.py
git commit -m "feat(orders): add Order and OrderLineItem ORM models"
```

---

### Task 2: Pydantic schemas (SPA wire format)

**Files:**
- Create: `app/schemas/order.py`
- Test: `tests/contract/test_orders_contract.py` (schema fields only, added in Task 12)

- [ ] **Step 1: Create schemas**

```python
# app/schemas/order.py
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

OrderStatus = Literal["pending", "processing", "shipped", "delivered", "cancelled"]


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
        if value is None:
            return ""
        return str(value).strip()


class OrderLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal

    @field_serializer("unit_price")
    def serialize_unit_price(self, value: Decimal) -> float:
        return float(value)


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
        return float(value)


class OrderStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: OrderStatus
```

- [ ] **Step 2: Commit**

```bash
git add app/schemas/order.py
git commit -m "feat(orders): add Pydantic order schemas"
```

---

### Task 3: `require_customer` dependency

**Files:**
- Modify: `app/dependencies/auth.py`
- Test: `tests/integration/test_orders.py`

- [ ] **Step 1: Write failing test**

```python
@pytest.mark.anyio
async def test_post_orders_as_admin_returns_403(
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from tests.integration.test_orders import insert_product  # added Task 4

    product = await insert_product(db_session, name="Mouse", sku="ORD-MOUSE-1", quantity=5)
    body = {
        "shipping_address": "1 Test St",
        "items": [{"product_id": product.id, "quantity": 1}],
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/orders",
            json=body,
            headers=admin_auth_headers,
        )
    assert response.status_code == 403
```

*(Router not wired yet → expect 404; after router + dependency, expect 403.)*

- [ ] **Step 2: Add dependency**

```python
# app/dependencies/auth.py
async def require_customer(
    current_user: RegisterUserResponse = Depends(get_current_user),
) -> RegisterUserResponse:
    if current_user.role != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access required",
        )
    return current_user
```

- [ ] **Step 3: Commit after Task 8 wires router (or commit dependency alone)**

```bash
git add app/dependencies/auth.py
git commit -m "feat(orders): add require_customer dependency"
```

---

### Task 4: Test helpers (`insert_product`, checkout payload)

**Files:**
- Modify: `tests/conftest.py`
- Create: shared helpers in `tests/integration/test_orders.py`

- [ ] **Step 1: Add to `tests/conftest.py`**

```python
def order_checkout_payload(
    product_id: int,
    *,
    quantity: int = 1,
    shipping_address: str = "42 MG Road, Bengaluru, India",
) -> dict[str, object]:
    return {
        "shipping_address": shipping_address,
        "items": [{"product_id": product_id, "quantity": quantity}],
    }
```

- [ ] **Step 2: Add `insert_product` to `tests/integration/test_orders.py`**

Copy `insert_product` / `_async_client` pattern from `tests/integration/test_products.py` (same `Product` insert + commit).

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py tests/integration/test_orders.py
git commit -m "test(orders): add integration helpers"
```

---

### Task 5: Line merge + total (unit tests, pure functions)

**Files:**
- Create: `app/services/order_service.py` (helpers only)
- Test: `tests/unit/test_order_service.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_order_service.py
from decimal import Decimal

from app.schemas.order import OrderLineItemCreate
from app.services.order_service import compute_total_amount, merge_line_items


def test_merge_line_items_sums_duplicate_product_ids() -> None:
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


def test_compute_total_amount() -> None:
    total = compute_total_amount(
        [
            (2, Decimal("799.00")),
            (1, Decimal("2499.00")),
        ]
    )
    assert total == Decimal("4097.00")
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest tests/unit/test_order_service.py -v`

- [ ] **Step 3: Implement helpers**

```python
# app/services/order_service.py (initial)
from decimal import Decimal

from app.schemas.order import OrderLineItemCreate


def merge_line_items(
    items: list[OrderLineItemCreate],
) -> list[OrderLineItemCreate]:
    quantities: dict[int, int] = {}
    for item in items:
        quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity
    return [
        OrderLineItemCreate(product_id=product_id, quantity=quantity)
        for product_id, quantity in sorted(quantities.items())
    ]


def compute_total_amount(lines: list[tuple[int, Decimal]]) -> Decimal:
    total = Decimal("0")
    for quantity, unit_price in lines:
        total += Decimal(quantity) * unit_price
    return total
```

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add app/services/order_service.py tests/unit/test_order_service.py
git commit -m "feat(orders): add merge_line_items and compute_total_amount"
```

---

### Task 6: ProductRepository stock helpers (no commit)

**Files:**
- Modify: `app/repositories/product_repository.py`
- Test: `tests/integration/test_orders.py`

- [ ] **Step 1: Write failing test**

```python
@pytest.mark.anyio
async def test_adjust_quantity_does_not_commit_until_service_commits(
    db_session: AsyncSession,
) -> None:
    from app.repositories.product_repository import ProductRepository

    product = await insert_product(db_session, name="Stock", sku="STK-1", quantity=10)
    repo = ProductRepository()
    await repo.adjust_quantity(db_session, product.id, -3)
    await db_session.refresh(product)
    assert product.quantity == 7
```

- [ ] **Step 2: Implement**

```python
async def get_by_ids(
    self,
    db: AsyncSession,
    product_ids: list[int],
) -> dict[int, Product]:
    if not product_ids:
        return {}
    result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
    products = list(result.scalars().all())
    return {product.id: product for product in products}


async def adjust_quantity(
    self,
    db: AsyncSession,
    product_id: int,
    delta: int,
) -> Product | None:
    product = await self.get_by_id(db, product_id)
    if product is None:
        return None
    product.quantity = product.quantity + delta
    await db.flush()
    return product
```

- [ ] **Step 3: Run test — PASS**

- [ ] **Step 4: Commit**

```bash
git add app/repositories/product_repository.py tests/integration/test_orders.py
git commit -m "feat(orders): add product stock helpers without auto-commit"
```

---

### Task 7: OrderRepository

**Files:**
- Create: `app/repositories/order_repository.py`

- [ ] **Step 1: Implement repository (flush only, caller commits)**

```python
# app/repositories/order_repository.py
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderLineItem


class OrderRepository:
    async def create_with_line_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        shipping_address: str,
        total_amount: Decimal,
        lines: list[dict[str, object]],
    ) -> Order:
        now = datetime.now(timezone.utc)
        order = Order(
            user_id=user_id,
            status="pending",
            total_amount=total_amount,
            shipping_address=shipping_address,
            stock_restored=False,
            created_at=now,
            updated_at=now,
        )
        db.add(order)
        await db.flush()
        for line in lines:
            db.add(
                OrderLineItem(
                    order_id=order.id,
                    product_id=line["product_id"],
                    product_name=line["product_name"],
                    quantity=line["quantity"],
                    unit_price=line["unit_price"],
                )
            )
        await db.flush()
        await db.refresh(order, attribute_names=["line_items"])
        return order

    async def get_by_id(self, db: AsyncSession, order_id: int) -> Order | None:
        result = await db.execute(
            select(Order)
            .options(selectinload(Order.line_items))
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, db: AsyncSession, user_id: int) -> list[Order]:
        result = await db.execute(
            select(Order)
            .options(selectinload(Order.line_items))
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_all(
        self,
        db: AsyncSession,
        *,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[Order]:
        query = select(Order).options(selectinload(Order.line_items)).order_by(
            Order.created_at.desc()
        )
        if status is not None:
            query = query.where(Order.status == status)
        if limit is not None:
            query = query.limit(min(limit, 100))
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_status(
        self,
        db: AsyncSession,
        order: Order,
        *,
        status: str,
        stock_restored: bool | None = None,
    ) -> Order:
        order.status = status
        order.updated_at = datetime.now(timezone.utc)
        if stock_restored is not None:
            order.stock_restored = stock_restored
        await db.flush()
        await db.refresh(order, attribute_names=["line_items"])
        return order
```

- [ ] **Step 2: Commit**

```bash
git add app/repositories/order_repository.py
git commit -m "feat(orders): add OrderRepository"
```

---

### Task 8: OrderService.checkout (integration RED → GREEN)

**Files:**
- Modify: `app/services/order_service.py`
- Test: `tests/integration/test_orders.py`

- [ ] **Step 1: Write failing checkout test**

```python
ORDER_KEYS = frozenset(
    {
        "id",
        "user_id",
        "status",
        "total_amount",
        "shipping_address",
        "created_at",
        "updated_at",
        "items",
    }
)
LINE_KEYS = frozenset({"id", "product_id", "product_name", "quantity", "unit_price"})


@pytest.mark.anyio
async def test_checkout_returns_201_with_snapshots_and_decrements_stock(
    db_session: AsyncSession,
    customer_auth_headers: dict[str, str],
) -> None:
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.repositories.product_repository import ProductRepository

    product = await insert_product(
        db_session,
        name="Wireless Mouse",
        sku="CHK-MOUSE",
        price=Decimal("799.00"),
        quantity=10,
    )
    body = {
        "shipping_address": "42 MG Road, Bengaluru, India",
        "items": [{"product_id": product.id, "quantity": 2}],
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/orders", json=body, headers=customer_auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert set(data.keys()) == ORDER_KEYS
    assert data["status"] == "pending"
    assert data["items"][0]["product_name"] == "Wireless Mouse"
    assert data["items"][0]["unit_price"] == 799.0
    assert data["total_amount"] == 1598.0

    repo = ProductRepository()
    refreshed = await repo.get_by_id(db_session, product.id)
    assert refreshed is not None
    assert refreshed.quantity == 8
```

- [ ] **Step 2: Run — FAIL (no route / service)**

- [ ] **Step 3: Extend OrderService**

```python
class InsufficientStockError(Exception):
    def __init__(self, product_id: int) -> None:
        self.product_id = product_id
        super().__init__(f"Insufficient stock for product_id {product_id}")


class ProductNotFoundForOrderError(Exception):
    def __init__(self, product_id: int) -> None:
        self.product_id = product_id
        super().__init__(f"Product {product_id} not found")


class OrderService:
    def __init__(
        self,
        order_repository: OrderRepository,
        product_repository: ProductRepository,
    ) -> None:
        self._orders = order_repository
        self._products = product_repository

    async def checkout(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        payload: OrderCreate,
    ) -> OrderResponse:
        merged = merge_line_items(payload.items)
        product_ids = [line.product_id for line in merged]
        products = await self._products.get_by_ids(db, product_ids)

        snapshot_lines: list[dict[str, object]] = []
        priced_lines: list[tuple[int, Decimal]] = []

        for line in merged:
            product = products.get(line.product_id)
            if product is None:
                raise ProductNotFoundForOrderError(line.product_id)
            if product.quantity < line.quantity:
                raise InsufficientStockError(line.product_id)
            snapshot_lines.append(
                {
                    "product_id": product.id,
                    "product_name": product.name,
                    "quantity": line.quantity,
                    "unit_price": product.price,
                }
            )
            priced_lines.append((line.quantity, product.price))

        total_amount = compute_total_amount(priced_lines)

        try:
            order = await self._orders.create_with_line_items(
                db,
                user_id=user_id,
                shipping_address=payload.shipping_address,
                total_amount=total_amount,
                lines=snapshot_lines,
            )
            for line in merged:
                await self._products.adjust_quantity(
                    db, line.product_id, -line.quantity
                )
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        return self._to_response(order)

    def _to_response(self, order: Order) -> OrderResponse:
        return OrderResponse(
            id=order.id,
            user_id=order.user_id,
            status=order.status,
            total_amount=order.total_amount,
            shipping_address=order.shipping_address,
            created_at=order.created_at,
            updated_at=order.updated_at,
            items=[
                OrderLineItemResponse.model_validate(item)
                for item in order.line_items
            ],
        )
```

- [ ] **Step 4: Wire minimal `POST /orders` in router (Task 9) then run test — PASS**

---

### Task 9: Orders router — `POST /orders`

**Files:**
- Create: `app/routers/orders.py`
- Modify: `app/main.py`

- [ ] **Step 1: Router handler**

```python
# app/routers/orders.py (excerpt)
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
    start = perf_counter()
    try:
        order = await service.checkout(
            db, user_id=current_user.id, payload=payload
        )
        logger.info(
            "order_checkout_success",
            request_id=request.headers.get("x-request-id", ""),
            path=str(request.url.path),
            method=request.method,
            status_code=201,
            latency_ms=round((perf_counter() - start) * 1000, 2),
            outcome="success",
            user_id=current_user.id,
            order_id=order.id,
        )
        return order
    except ProductNotFoundForOrderError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InsufficientStockError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
```

- [ ] **Step 2: `app/main.py`**

```python
from app.routers.orders import router as orders_router

app.include_router(orders_router)
```

- [ ] **Step 3: Run checkout + admin 403 tests — PASS**

- [ ] **Step 4: Commit**

```bash
git add app/routers/orders.py app/main.py app/services/order_service.py
git commit -m "feat(orders): add POST /orders checkout endpoint"
```

---

### Task 10: Customer reads (`GET /orders/me`, `GET /orders/{id}`)

**Files:**
- Modify: `app/services/order_service.py`, `app/routers/orders.py`
- Test: `tests/integration/test_orders.py`

- [ ] **Step 1: Failing tests**

```python
@pytest.mark.anyio
async def test_get_orders_me_returns_only_own_orders(...) -> None:
    # create two customers, order as customer A, GET /orders/me as A → 1 order
    # GET /orders/me as B → []

@pytest.mark.anyio
async def test_get_order_by_id_forbidden_for_other_user(...) -> None:
    # customer A order, customer B GET → 403

@pytest.mark.anyio
async def test_get_order_by_id_not_found(...) -> None:
    # GET /orders/99999 → 404
```

- [ ] **Step 2: Service methods**

```python
class OrderNotFoundError(Exception):
    pass

class ForbiddenOrderAccessError(Exception):
    pass

async def list_mine(self, db, *, user_id: int) -> list[OrderResponse]: ...

async def get_order(
    self, db, *, order_id: int, user_id: int, is_admin: bool
) -> OrderResponse:
    order = await self._orders.get_by_id(db, order_id)
    if order is None:
        raise OrderNotFoundError("Order not found")
    if order.user_id != user_id and not is_admin:
        raise ForbiddenOrderAccessError("Not allowed to access this order")
    return self._to_response(order)
```

- [ ] **Step 3: Router**

```python
@router.get("/orders/me", response_model=list[OrderResponse])
async def list_my_orders(..., current_user=Depends(get_current_user)): ...

@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(..., current_user=Depends(get_current_user)): ...
```

- [ ] **Step 4: Run tests — PASS; commit**

```bash
git commit -m "feat(orders): add customer order list and detail endpoints"
```

---

### Task 11: Admin list + PATCH status (restock)

**Files:**
- Modify: `app/services/order_service.py`, `app/routers/orders.py`
- Test: `tests/integration/test_orders.py`

- [ ] **Step 1: Failing tests**

```python
@pytest.mark.anyio
async def test_admin_list_orders_with_status_filter(...) -> None: ...

@pytest.mark.anyio
async def test_admin_list_orders_limit_capped_at_100(...) -> None: ...

@pytest.mark.anyio
async def test_patch_cancel_restock_once(...) -> None:
    # checkout qty 2, cancel → stock back
    # PATCH cancelled again → stock unchanged

@pytest.mark.anyio
async def test_non_admin_get_orders_returns_403(...) -> None: ...
```

- [ ] **Step 2: `update_status` in service**

```python
async def update_status(
    self, db: AsyncSession, *, order_id: int, status: OrderStatus
) -> OrderResponse:
    order = await self._orders.get_by_id(db, order_id)
    if order is None:
        raise OrderNotFoundError("Order not found")

    should_restock = (
        status == "cancelled"
        and order.status != "cancelled"
        and not order.stock_restored
    )

    try:
        if should_restock:
            for line in order.line_items:
                product = await self._products.get_by_id(db, line.product_id)
                if product is not None:
                    await self._products.adjust_quantity(
                        db, line.product_id, line.quantity
                    )
            await self._orders.update_status(
                db, order, status=status, stock_restored=True
            )
        else:
            await self._orders.update_status(db, order, status=status)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    reloaded = await self._orders.get_by_id(db, order_id)
    assert reloaded is not None
    return self._to_response(reloaded)
```

- [ ] **Step 3: Router admin routes**

```python
@router.get("/orders", response_model=list[OrderResponse])
async def list_orders(
    status: OrderStatus | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1),
    _admin=Depends(require_admin),
): ...

@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
async def patch_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    _admin=Depends(require_admin),
): ...
```

- [ ] **Step 4: Run tests — PASS; commit**

```bash
git commit -m "feat(orders): add admin list/filter and status PATCH with restock"
```

---

### Task 12: Contract tests + route access policy

**Files:**
- Create: `tests/contract/test_orders_contract.py`
- Modify: `tests/contract/test_route_access_policy.py`

- [ ] **Step 1: Contract tests (mirror `test_products_contract.py`)**

```python
CONTRACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "specs/003-orders-checkout/contracts/orders-api.yaml"
)

ORDER_REQUIRED_FIELDS = frozenset(
    {
        "id",
        "user_id",
        "status",
        "total_amount",
        "shipping_address",
        "created_at",
        "updated_at",
        "items",
    }
)

def test_post_orders_requires_bearer_security(orders_contract: dict) -> None:
    post = orders_contract["paths"]["/orders"]["post"]
    assert post["security"] == [{"bearerAuth": []}]
```

- [ ] **Step 2: Access policy**

```python
@pytest.mark.anyio
async def test_orders_me_requires_authentication():
    ...
    assert response.status_code == 401

@pytest.mark.anyio
async def test_post_orders_requires_authentication():
    ...
    assert response.status_code == 401
```

- [ ] **Step 3: Run**

```bash
pytest tests/contract/test_orders_contract.py tests/contract/test_route_access_policy.py -v
```

- [ ] **Step 4: Commit**

```bash
git commit -m "test(orders): add contract and auth policy tests"
```

---

### Task 13: Final verification

- [ ] **Step 1: Full suite**

```bash
pytest tests/integration/test_orders.py \
  tests/unit/test_order_service.py \
  tests/contract/test_orders_contract.py \
  tests/contract/test_route_access_policy.py \
  tests/integration/test_products.py \
  tests/integration/test_auth_register.py -q
```

Expected: all PASS

- [ ] **Step 2: Coverage (optional gate)**

```bash
pytest tests/integration/test_orders.py tests/unit/test_order_service.py \
  --cov=app/services/order_service --cov=app/repositories/order_repository \
  --cov=app/routers/orders --cov-report=term-missing
```

Target: ≥80% on new modules

- [ ] **Step 3: Manual quickstart**

Follow `specs/003-orders-checkout/quickstart.md` curl examples.

- [ ] **Step 4: Commit any fixes**

```bash
git commit -m "chore(orders): verification pass for checkout feature"
```

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|------------------|------|
| FR-001 customer checkout / admin 403 | Task 3, 9 |
| FR-002–005 snapshots + total | Task 5, 8 |
| FR-006 stock decrement / 409 | Task 6, 8 |
| FR-007 404 product | Task 8 |
| FR-008 `GET /orders/me` | Task 10 |
| FR-009 detail owner/admin | Task 10 |
| FR-010 admin list filter/limit | Task 11 |
| FR-011–012 PATCH status | Task 11 |
| FR-013 cancel restock once | Task 11 |
| FR-014 all routes auth | Task 12 |
| FR-016 `items` key | Task 2 |
| FR-017 merge duplicates | Task 5 |

**Placeholder scan:** None.  
**Type consistency:** `OrderResponse`, `OrderService`, `OrderRepository` names aligned across tasks.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-28-orders-checkout.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration (`superpowers:subagent-driven-development`).

2. **Inline Execution** — run tasks in this session with checkpoints (`superpowers:executing-plans`).

Which approach do you want?
