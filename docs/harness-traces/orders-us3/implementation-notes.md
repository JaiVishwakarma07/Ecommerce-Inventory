# Implementation Notes (TDD)

Task: `orders-us3`

**Harness:** US3 — admin order list (`GET /orders` with `?status=` and `?limit=`) (`specs/003-orders-checkout` tasks T030–T036)

**Prerequisites:** US1 `POST /orders`, US2 customer reads — `docs/harness-traces/post-orders/`, `docs/harness-traces/orders-us2/`

**Plan:** `docs/harness-traces/orders-us3/plan.md`  
**Brainstorm:** `docs/harness-traces/orders-us3/brainstorm.md`

## Key decisions made during test-driven development

1. **Tests first (RED → GREEN)**
   - Wrote 6 contract, 7 integration, and 1 route-policy test before `GET /orders` handler.
   - Initial RED: HTTP **405** (`GET /orders` not registered); auth/filter tests also **405** until route added.
   - Contract tests passed in RED (OpenAPI already defined admin `GET /orders`).
   - Slice verification: **14 passed** on `-k get_orders_admin` (exit 0).

2. **No repository changes**
   - Reused `OrderRepository.list_all` — `status` exact match, `order_by(created_at.desc())`, `limit` via `min(limit, 100)`.
   - Read path does not commit.

3. **Service layer**
   - `OrderService.list_admin(status, limit)` — maps all matching orders to `OrderResponse[]`.

4. **Auth**
   - `require_admin` on `GET /orders` — non-admin **403** `"Admin access required"`; no token **401**.

5. **Query validation**
   - `status: OrderStatus | None = Query(default=None)` — invalid enum → **422** (FastAPI).
   - `limit: int | None = Query(default=None, ge=1)` — **no** `le=100` on Query so `?limit=200` reaches repo and caps at 100 (spec scenario 4).

6. **Router route order**
   - `POST /orders` → `GET /orders/me` → `GET /orders/{order_id}` → **`GET /orders`** (admin list; same path as POST, different method).

7. **Structlog**
   - `order_admin_list_success`, `order_admin_list_error` (distinct from US2 `order_list_*` on `/orders/me`).
   - Fields: `request_id`, `path`, `method`, `status_code`, `latency_ms`, `outcome`, `user_id`, `result_count`, `status_filter`, `limit`.

8. **Integration test helpers (test-only)**
   - `set_order_status()` — ORM update for multi-status filter (approach A; no US4 dependency).
   - `set_order_created_at()` — stable newest-first assertion.
   - `seed_orders_for_user()` — bulk insert 101 orders for limit-cap test (avoids 101 HTTP checkouts).

## Files touched

| File | Role |
|------|------|
| `app/services/order_service.py` | `list_admin` |
| `app/routers/orders.py` | `GET /orders` + `require_admin` + structlog |
| `tests/contract/test_orders_contract.py` | 6 US3 contract tests |
| `tests/integration/test_orders.py` | 7 US3 integration tests + helpers |
| `tests/contract/test_route_access_policy.py` | `test_get_orders_admin_requires_authentication` |

**Unchanged (per plan):** `app/repositories/order_repository.py`, `app/models/order.py`, `app/schemas/order.py`, `app/dependencies/auth.py`

## Spec coverage (US3)

| Requirement | Covered |
|-------------|---------|
| FR-010 admin list/filter/limit | Yes |
| FR-014 auth on orders | Yes |
| US3 scenarios 1–6 | Yes |

## Out of scope (documented, not implemented in this harness)

- `PATCH /orders/{id}/status` + cancel restock (US4)
- Pagination metadata (`total`, `page`)
- `/api/v1/orders` route alias
- Rate limiting on admin list

## Postman smoke

- `GET /orders` with admin Bearer token → **200** array
- `GET /orders?status=pending&limit=50` → filtered/capped list
- Customer token → **403**; no token → **401**
