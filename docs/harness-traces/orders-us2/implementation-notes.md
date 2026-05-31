# Implementation Notes (TDD)

Task: `orders-us2`

**Harness:** US2 — customer order reads (`GET /orders/me`, `GET /orders/{order_id}`) (`specs/003-orders-checkout` tasks T022–T029)

**Prerequisites:** US1 `POST /orders` complete — `docs/harness-traces/post-orders/`

**Plan:** `docs/harness-traces/orders-us2/plan.md`  
**Brainstorm:** `docs/harness-traces/orders-us2/brainstorm.md`

## Key decisions made during test-driven development

1. **Tests first (RED → GREEN)**
   - Wrote 8 contract, 7 integration, and 2 route-policy tests before GET handlers.
   - Initial RED: HTTP `404` (routes missing); auth tests also `404` until routes registered.
   - Contract test for 403: YAML uses inline `ErrorDetail` ref, not `#/components/responses/Forbidden` — test named `test_get_orders_by_id_403_uses_error_detail_schema`.
   - Slice verification: **18 passed** on plan filter (exit 0).

2. **No repository changes**
   - Reused `OrderRepository.list_for_user` (newest-first via `order_by(created_at.desc())`) and `get_by_id`.
   - Read paths do not commit; checkout transaction owner unchanged.

3. **Service layer**
   - `OrderService.list_mine()` — maps all user orders to `OrderResponse[]`.
   - `OrderService.get_order()` — `OrderNotFoundError` if missing; `ForbiddenOrderAccessError` if `user_id` mismatch and not admin.
   - Exception defaults: `"Order not found"`, `"Not allowed to access this order"`.

4. **Auth on GET (not `require_customer`)**
   - `get_current_user` on both GET routes — any authenticated role may call `/orders/me`.
   - Detail: `is_admin = current_user.role == "admin"` bypasses ownership check.
   - `POST /orders` still uses `require_customer` (unchanged from US1).

5. **Router route order**
   - `POST /orders` → `GET /orders/me` → `GET /orders/{order_id}` (static `/me` before path param).

6. **Error mapping (router)**
   - `OrderNotFoundError` → **404** (`detail=str(exc)`).
   - `ForbiddenOrderAccessError` → **403** (`detail=str(exc)`).

7. **Structlog**
   - List: `order_list_success`, `order_list_error`.
   - Detail: `order_get_success`, `order_get_not_found`, `order_get_forbidden`, `order_get_error`.
   - Fields: `request_id`, `path`, `method`, `status_code`, `latency_ms`, `outcome`, `user_id`, `order_id` (detail), `result_count` (list).

8. **Integration test helpers**
   - `_checkout_order()` in `tests/integration/test_orders.py` — seeds order via `POST /orders` for read tests.
   - `ORDER_KEYS` frozenset for full Order shape assertion on detail.

## Files touched

| File | Role |
|------|------|
| `app/services/order_service.py` | `list_mine`, `get_order`; exception messages |
| `app/routers/orders.py` | `GET /orders/me`, `GET /orders/{order_id}` + structlog |
| `tests/contract/test_orders_contract.py` | 8 US2 contract tests |
| `tests/integration/test_orders.py` | 7 US2 integration tests + `_checkout_order` |
| `tests/contract/test_route_access_policy.py` | 2 GET auth policy tests |

**Unchanged (per plan):** `app/models/order.py`, `app/schemas/order.py`, `app/repositories/order_repository.py`, `app/dependencies/auth.py`

## Spec coverage (US2)

| Requirement | Covered |
|-------------|---------|
| FR-008 `GET /orders/me` | Yes |
| FR-009 detail owner/admin | Yes |
| FR-009 404 missing | Yes |
| FR-014 auth on orders | Yes |
| FR-004 snapshots on read | Yes (`product_name`, `unit_price` on detail) |
| FR-016 nested `items` | Yes (contract + `ORDER_KEYS`) |

## Out of scope (documented, not implemented in this harness)

- `GET /orders` admin list/filter/limit (US3)
- `PATCH /orders/{id}/status` + cancel restock (US4)
- Admin `GET /orders/me` test (brainstorm strategy A — omitted by design)
- `/api/v1/orders` route alias
- Rate limiting on GET order endpoints
