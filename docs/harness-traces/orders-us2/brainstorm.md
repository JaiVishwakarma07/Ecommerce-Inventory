# Brainstorm: US2 — Customer order reads

## Task

Wire customer order visibility (Phase 4 / tasks T022–T029):

- **Endpoints:** `GET /orders/me`, `GET /orders/{order_id}`
- **Reference:** `specs/003-orders-checkout/spec.md` (US2), `plan.md`, `tasks.md`
- **Prerequisite:** US1 `POST /orders` — `docs/harness-traces/post-orders/`
- **Parent design:** `docs/superpowers/specs/2026-05-28-orders-checkout-design.md`

## Decisions

| Topic | Decision |
|-------|----------|
| Harness path | `docs/harness-traces/orders-us2/` |
| Approach | **1** — Wire existing `OrderRepository` + thin `OrderService` methods |
| Auth | `get_current_user` on both routes (not `require_customer`) |
| `GET /orders/me` | Scope to `current_user.id`; any role (customer-focused tests) |
| `GET /orders/{order_id}` | Owner **or** admin → `200`; other customer → `403`; missing → `404` |
| Response | Same `Order` / `Order[]` shape as checkout; nested `items`; no `stock_restored` |
| Repo | **No changes** — use `list_for_user`, `get_by_id` (already implemented) |
| Route order | Register `GET /orders/me` **before** `GET /orders/{order_id}` (and before future `GET /orders`) |
| Test focus | **A** — Customer A/B + admin detail on customer order; no admin `/me` test |
| Deferred | `GET /orders`, `PATCH …/status` (US3–US4) |

## Architecture

```text
GET /orders/me
  → get_current_user
  → OrderService.list_mine(user_id)
  → OrderRepository.list_for_user
  → list[OrderResponse]

GET /orders/{order_id}
  → get_current_user
  → OrderService.get_order(order_id, user_id, is_admin)
  → OrderRepository.get_by_id
  → OrderResponse | OrderNotFoundError | ForbiddenOrderAccessError
```

## API contract

### `GET /orders/me`

- **Auth:** Bearer required (`401` if missing/invalid)
- **200:** `Order[]`, newest `created_at` first (repo `order_by(Order.created_at.desc())`)
- Each element: full `Order` with nested `items` (snapshots)

### `GET /orders/{order_id}`

- **Auth:** Bearer required
- **200:** `Order` when `order.user_id == current_user.id` **or** `current_user.role == "admin"`
- **403:** Authenticated non-owner, non-admin
- **404:** Order id does not exist
- **422:** Non-integer `order_id` (FastAPI path validation)

### Stable `detail` strings (router)

| Situation | Status | `detail` (example) |
|-----------|--------|----------------------|
| Missing order | `404` | `"Order not found"` |
| Wrong customer | `403` | `"Not allowed to access this order"` |
| No token | `401` | `"Not authenticated"` |

## Service signatures

```python
async def list_mine(
    self,
    db: AsyncSession,
    *,
    user_id: int,
) -> list[OrderResponse]: ...

async def get_order(
    self,
    db: AsyncSession,
    *,
    order_id: int,
    user_id: int,
    is_admin: bool,
) -> OrderResponse: ...
```

Domain exceptions (extend messages on existing classes):

```python
class OrderNotFoundError(Exception): ...  # detail: "Order not found"
class ForbiddenOrderAccessError(Exception): ...  # detail: "Not allowed to access this order"
```

## Router signatures

```python
@router.get("/orders/me", response_model=list[OrderResponse])
async def list_my_orders(
    request: Request,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: OrderService = Depends(get_order_service),
    current_user: RegisterUserResponse = Depends(get_current_user),
) -> list[OrderResponse]: ...

@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order_by_id(
    request: Request,
    order_id: int,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: OrderService = Depends(get_order_service),
    current_user: RegisterUserResponse = Depends(get_current_user),
) -> OrderResponse: ...
```

Structlog events: `order_list_*`, `order_get_*` (success, not_found, forbidden, error) with `latency_ms`, `user_id`, `order_id`, `outcome`.

## Testing (choice A)

| Test | Asserts |
|------|---------|
| `test_get_orders_me_returns_only_own_orders` | A checkout → A list has 1; B list `[]` |
| `test_get_order_by_id_returns_own_order` | A `200`, full keys, snapshots |
| `test_get_order_by_id_forbidden_for_other_customer` | B → `403` |
| `test_get_order_by_id_allowed_for_admin` | Admin → `200` on A's order |
| `test_get_order_by_id_not_found` | `999999` → `404` |
| `test_get_orders_me_without_token_returns_401` | |
| `test_get_order_by_id_without_token_returns_401` | |

Contract: OpenAPI paths, bearer security, `200` response schemas for both GETs.

## Spec coverage (US2)

| Requirement | Covered |
|-------------|---------|
| FR-008 `GET /orders/me` | Yes |
| FR-009 owner/admin detail, 403/404 | Yes |
| FR-014 auth on routes | Yes |
| FR-004 snapshots on read | Yes (stored at checkout) |
| FR-016 nested `items` | Yes |

## Out of scope

- Admin `GET /orders` (US3)
- `PATCH /orders/{id}/status` (US4)
- New migrations or model changes
- Rate limiting (deferred; same as US1)
- `/api/v1/orders` aliases

## Next step

Implementation plan: `docs/harness-traces/orders-us2/plan.md` (TDD, signatures + test names only).
