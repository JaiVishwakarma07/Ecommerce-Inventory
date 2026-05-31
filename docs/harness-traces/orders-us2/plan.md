# US2 — Customer Order Reads Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver `GET /orders/me` and `GET /orders/{order_id}` with SPA-aligned `Order` / `Order[]` JSON, owner-or-admin access on detail, and structlog observability.

**Architecture:** Extend `orders` router with two GET handlers → `OrderService.list_mine` / `get_order` → existing `OrderRepository.list_for_user` / `get_by_id`. No repository changes. Auth via `get_current_user` (any role for `/me`; admin bypass on detail).

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Pydantic v2, pytest + httpx AsyncClient, structlog

**Scope source:** `docs/harness-traces/orders-us2/brainstorm.md`, `specs/003-orders-checkout/spec.md` (US2), tasks T022–T029

**Prerequisite:** US1 `POST /orders` complete — `docs/harness-traces/post-orders/`

---

> This document defines **signatures and test names only** — no implementation bodies.

## File Map

| File | Role |
|------|------|
| `app/services/order_service.py` | Add `list_mine`, `get_order`; exception messages |
| `app/routers/orders.py` | `GET /orders/me`, `GET /orders/{order_id}`; error mapping; structlog |
| `tests/contract/test_orders_contract.py` | US2 OpenAPI tests |
| `tests/integration/test_orders.py` | US2 HTTP flows |
| `tests/contract/test_route_access_policy.py` | Optional: extend 401 checks for new GET paths |

**Unchanged:** `app/models/order.py`, `app/schemas/order.py`, `app/repositories/order_repository.py`, `app/dependencies/auth.py` (no new deps)

---

## Route registration order

In `app/routers/orders.py`, declare routes in this order:

1. `POST /orders` (existing)
2. `GET /orders/me` ← **new; before `{order_id}`**
3. `GET /orders/{order_id}` ← **new**
4. (US3 later) `GET /orders`
5. (US4 later) `PATCH /orders/{order_id}/status`

---

## Domain exceptions (extend)

```python
# app/services/order_service.py

class OrderNotFoundError(Exception):
    def __init__(self, message: str = "Order not found") -> None: ...

class ForbiddenOrderAccessError(Exception):
    def __init__(self, message: str = "Not allowed to access this order") -> None: ...
```

---

## Service layer signatures

```python
# app/services/order_service.py

async def list_mine(
    self,
    db: AsyncSession,
    *,
    user_id: int,
) -> list[OrderResponse]:
    """Load user orders; map to OrderResponse list. Does not commit."""

async def get_order(
    self,
    db: AsyncSession,
    *,
    order_id: int,
    user_id: int,
    is_admin: bool,
) -> OrderResponse:
    """
    order = await self._orders.get_by_id(db, order_id)
    if order is None: raise OrderNotFoundError()
    if order.user_id != user_id and not is_admin:
        raise ForbiddenOrderAccessError()
    return self._to_response(order)
    """
```

---

## Router & DI signatures

```python
# app/routers/orders.py

@router.get("/orders/me", response_model=list[OrderResponse])
async def list_my_orders(
    request: Request,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: OrderService = Depends(get_order_service),
    current_user: RegisterUserResponse = Depends(get_current_user),
) -> list[OrderResponse]:
    """
    Map exceptions only if raised (none expected on list_mine).
    Log order_list_success / order_list_error.
    """

@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order_by_id(
    request: Request,
    order_id: int,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: OrderService = Depends(get_order_service),
    current_user: RegisterUserResponse = Depends(get_current_user),
) -> OrderResponse:
    """
    is_admin = current_user.role == "admin"
    service.get_order(db, order_id=order_id, user_id=current_user.id, is_admin=is_admin)
    Map OrderNotFoundError → 404, ForbiddenOrderAccessError → 403
    Log order_get_success | order_get_not_found | order_get_forbidden | order_get_error
    """
```

**Imports to add in router:** `get_current_user` from `app.dependencies.auth` (replace or supplement `require_customer` usage on GET only).

---

## Exact test case names and assertions

### Contract tests (`tests/contract/test_orders_contract.py`)

- `test_get_orders_me_path_exists_in_contract`
  - asserts `paths["/orders/me"]["get"]` exists
- `test_get_orders_me_requires_bearer_security`
  - asserts operation inherits or declares `bearerAuth`
- `test_get_orders_me_response_schema_is_order_array`
  - asserts `200` response is `array` of `#/components/schemas/Order`
- `test_get_orders_by_id_path_exists_in_contract`
  - asserts `paths["/orders/{order_id}"]["get"]` exists
- `test_get_orders_by_id_requires_bearer_security`
- `test_get_orders_by_id_response_schema_is_order`
  - asserts `200` `$ref` is `#/components/schemas/Order`
- `test_get_orders_by_id_403_uses_forbidden_response`
  - asserts `403` `$ref` is `#/components/responses/Forbidden`
- `test_get_orders_by_id_404_uses_not_found_response`

### Integration tests (`tests/integration/test_orders.py`)

Shared constant (reuse from US1 or define once):

```python
ORDER_KEYS = frozenset({
    "id", "user_id", "status", "total_amount",
    "shipping_address", "created_at", "updated_at", "items",
})
```

- `test_get_orders_me_returns_only_own_orders`
  - customer A checks out via `POST /orders`
  - A `GET /orders/me` → `200`, `len == 1`, `user_id == A.id`
  - B `GET /orders/me` → `200`, `len == 0`
- `test_get_order_by_id_returns_own_order`
  - A checkout → `GET /orders/{id}` as A → `200`
  - asserts `set(body.keys()) == ORDER_KEYS`
  - asserts `items[0].product_name` and `unit_price` match checkout response
- `test_get_order_by_id_forbidden_for_other_customer`
  - A checkout → B `GET /orders/{id}` → `403`
- `test_get_order_by_id_allowed_for_admin`
  - A checkout → admin `GET /orders/{id}` → `200`, same `id`
- `test_get_order_by_id_not_found`
  - customer `GET /orders/999999` → `404`, `"detail"` present
- `test_get_orders_me_without_token_returns_401`
- `test_get_order_by_id_without_token_returns_401`

### Route access policy (optional polish, can be Phase 7)

- `test_get_orders_me_requires_authentication`
- `test_get_order_by_id_requires_authentication`

---

## Spec coverage map (US2)

| Requirement | Test(s) |
|-------------|---------|
| FR-008 `GET /orders/me` | `test_get_orders_me_*` |
| FR-009 detail owner/admin | `test_get_order_by_id_returns_own_order`, `test_get_order_by_id_allowed_for_admin`, `test_get_order_by_id_forbidden_*` |
| FR-009 404 | `test_get_order_by_id_not_found` |
| FR-014 auth | `*_without_token_returns_401`, contract bearer tests |
| FR-004 snapshots on read | `test_get_order_by_id_returns_own_order` |
| FR-016 `items` key | contract Order schema tests (existing) |

---

## Task alignment (`tasks.md`)

| Task | Plan section |
|------|----------------|
| T022 | Contract tests |
| T023 | Integration tests |
| T024 | Run RED |
| T025 | Service methods |
| T026 | Router GETs |
| T027 | Error mapping |
| T028 | Structlog |
| T029 | Run GREEN |

---

## Verification command

```bash
backend/.venv/bin/pytest tests/contract/test_orders_contract.py \
  tests/integration/test_orders.py \
  tests/contract/test_route_access_policy.py \
  -k "orders_me or order_by_id or forbidden or get_orders" -v
```

**US2-only filter (tasks.md):**

```bash
backend/.venv/bin/pytest tests/integration/test_orders.py \
  -k "orders_me or order_by_id or forbidden" -v
```

**Regression (US1 + US2):**

```bash
backend/.venv/bin/pytest tests/contract/test_orders_contract.py \
  tests/integration/test_orders.py \
  tests/unit/test_order_service.py \
  -k "checkout or merge or total or post_orders or orders_me or order_by_id or forbidden" -v
```

---

## Self-review

- **Placeholder scan:** None.
- **Consistency:** Matches `brainstorm.md`, `spec.md` US2, `orders-api.yaml`.
- **Scope:** Read-only; no US3/US4 routes.
- **Ambiguity:** Admin uses `role == "admin"` string match (same as `require_admin`).

---

## Execution handoff

Plan saved to `docs/harness-traces/orders-us2/plan.md`.

**Next:** TDD — write failing tests (T022–T024), then implement T025–T028, verify T029.
