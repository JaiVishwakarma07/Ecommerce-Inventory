# Brainstorm: US3 — Admin lists and filters orders

## Task

Wire admin order queue visibility (Phase 5 / tasks T030–T036):

- **Endpoint:** `GET /orders` with optional `?status=` and `?limit=`
- **Reference:** `specs/003-orders-checkout/spec.md` (US3), `plan.md`, `tasks.md`
- **Prerequisite:** US1 `POST /orders`, US2 customer reads — `docs/harness-traces/post-orders/`, `docs/harness-traces/orders-us2/`
- **Parent design:** `docs/superpowers/specs/2026-05-28-orders-checkout-design.md`

## Decisions

| Topic | Decision |
|-------|----------|
| Harness path | `docs/harness-traces/orders-us3/` |
| Approach | **1** — Wire existing `OrderRepository.list_all` + thin `OrderService.list_admin` |
| Auth | `require_admin` on `GET /orders` (`403` non-admin; `401` no token) |
| Repo | **No changes** — `list_all` already filters by `status` and `min(limit, 100)` |
| `limit` query | `Query(ge=1)` only — **no** `le=100` on FastAPI param so `?limit=200` reaches repo and caps at 100 (spec scenario 4) |
| `limit` omitted | No SQL `LIMIT` — return all matching orders |
| Invalid `status` | **422** via FastAPI — `status: OrderStatus \| None = Query(default=None)` |
| Response | `Order[]`, newest first; nested `items`; no envelope |
| Route order | Add `GET /orders` **after** `GET /orders/{order_id}` (same path as `POST /orders`, different method) |
| Structlog | `order_admin_list_success` / `order_admin_list_error` (distinct from US2 `order_list_*` on `/orders/me`) |
| Multi-status tests | **A** — test helper sets `order.status` on `db_session` (no HTTP; no US4 dependency) |
| Deferred | `PATCH /orders/{id}/status` (US4) |

## Architecture

```text
GET /orders?status=&limit=
  → require_admin
  → OrderService.list_admin(status, limit)
  → OrderRepository.list_all
  → list[OrderResponse]
```

## API contract

### `GET /orders` (admin)

- **Auth:** Bearer required; `role == "admin"` else **403** `"Admin access required"`
- **200:** `Order[]`, newest `created_at` first
- **Query `status`:** optional; exact match on `pending` \| `processing` \| `shipped` \| `delivered` \| `cancelled`
- **Query `limit`:** optional integer ≥ 1; values > 100 capped at 100 in repository
- **422:** invalid `status` enum; `limit` < 1

### Stable `detail` strings

| Situation | Status | `detail` |
|-----------|--------|----------|
| No token | `401` | `"Not authenticated"` |
| Non-admin | `403` | `"Admin access required"` |

## Service signature

```python
async def list_admin(
    self,
    db: AsyncSession,
    *,
    status: str | None = None,
    limit: int | None = None,
) -> list[OrderResponse]:
    """Load all orders (optional filter/limit); map to OrderResponse list. Does not commit."""
```

## Router signature

```python
@router.get("/orders", response_model=list[OrderResponse])
async def list_orders_admin(
    request: Request,
    status: OrderStatus | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db_session_with_request),
    service: OrderService = Depends(get_order_service),
    _admin: RegisterUserResponse = Depends(require_admin),
) -> list[OrderResponse]: ...
```

Import `require_admin`, `OrderStatus` from schemas. Log `order_admin_list_*` with `result_count`, `status_filter`, `limit`.

## Testing

### Test helper (integration only)

```python
async def set_order_status(
    db_session: AsyncSession,
    order_id: int,
    status: str,
) -> None:
    """ORM update + flush; no HTTP."""
```

### Integration tests

| Test | Asserts |
|------|---------|
| `test_get_orders_admin_returns_all_orders_newest_first` | 2+ checkouts → admin `GET /orders` → 200, count, descending `created_at` |
| `test_get_orders_admin_filters_by_status` | Helper sets one order `shipped` → `?status=shipped` returns only that order |
| `test_get_orders_admin_respects_limit` | 3 orders → `?limit=2` → len 2 |
| `test_get_orders_admin_limit_over_100_capped` | 101+ orders (loop checkout or bulk insert) → `?limit=200` → len ≤ 100 |
| `test_get_orders_admin_as_customer_returns_403` | Customer token |
| `test_get_orders_admin_invalid_status_returns_422` | `?status=not-a-status` |
| `test_get_orders_admin_without_token_returns_401` | |

### Contract tests

| Test | Asserts |
|------|---------|
| `test_get_orders_admin_path_exists_in_contract` | `paths["/orders"]["get"]` |
| `test_get_orders_admin_requires_bearer_security` | bearerAuth |
| `test_get_orders_admin_has_status_and_limit_query_params` | parameters in OpenAPI |
| `test_get_orders_admin_response_schema_is_order_array` | 200 → array of Order |
| `test_get_orders_admin_403_uses_forbidden_response` | 403 ref or ErrorDetail |

### Route access policy

| Test | Asserts |
|------|---------|
| `test_get_orders_admin_requires_authentication` | no token → 401 |

**Pytest filter:** `-k "admin_list or admin_orders"`

## Spec coverage (US3)

| Requirement | Covered |
|-------------|---------|
| FR-010 admin list/filter/limit | Yes |
| FR-014 auth | Yes |
| US3 scenarios 1–6 | Yes |

## Out of scope

- `PATCH /orders/{id}/status` (US4)
- Pagination metadata (`total`, `page`)
- Customer `GET /orders` (always 403)
- Repository / model changes
- `/api/v1/orders` alias

## Next step

Implementation plan: `docs/harness-traces/orders-us3/plan.md` (TDD, signatures + test names only).
