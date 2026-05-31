# Implementation Notes (TDD)

Task: `post-orders`

**Harness:** US1 — customer `POST /orders` checkout slice only (`specs/003-orders-checkout` tasks T001–T021 scope)

**Prerequisites:** Auth (`customer` / `admin` roles), product catalog (`GET` / admin CRUD)

**Plan:** `docs/harness-traces/post-orders/plan.md`  
**Brainstorm:** `docs/harness-traces/post-orders/brainstorm.md`

## Key decisions made during test-driven development

1. **Tests first (RED → GREEN)**
   - Wrote unit, contract, integration, and route-policy tests before application code.
   - Initial RED: `ModuleNotFoundError` (schemas/service), HTTP `404` (route missing), missing `orders` / `order_line_items` tables.
   - Slice verification: **19 passed** on plan filter (exit 0).

2. **Single transaction owner**
   - `OrderService.checkout()` owns `commit` / `rollback`.
   - `OrderRepository.create_with_line_items` and `ProductRepository.adjust_quantity` / `get_by_ids` **flush only** (no per-op commit), per `specs/003-orders-checkout/research.md` R1.

3. **Full `OrderRepository` upfront**
   - `create_with_line_items`, `get_by_id`, `list_for_user`, `list_all`, `update_status` implemented now.
   - Only `checkout` wired in service/router for this slice; US2–US4 routes deferred.

4. **SPA wire format**
   - Response uses nested **`items`** (not `line_items`); ORM relationship remains `line_items`.
   - `OrderService._to_response()` maps ORM → `OrderResponse` with `OrderLineItemResponse` per line.
   - `total_amount` and `unit_price` serialized as JSON numbers (`float`).

5. **Checkout flow**
   - `merge_line_items()` sums duplicate `product_id` before validation (FR-017).
   - Load products via `get_by_ids` → validate existence (404) and stock (409).
   - Snapshot `product_name` and `unit_price` at checkout time.
   - Insert order (`status=pending`, `stock_restored=false`) + line items → decrement stock → `commit`.

6. **Auth**
   - `require_customer` in `app/dependencies/auth.py` — `role == "customer"` else **403** `"Customer access required"`.
   - Admin checkout forbidden; unauthenticated → **401** via `get_current_user`.

7. **Error mapping (router)**
   - `ProductNotFoundForOrderError` → **404** (`detail` includes product id).
   - `InsufficientStockError` → **409** (`detail` includes `product_id`).
   - Pydantic validation → **422** (empty `items`, whitespace-only `shipping_address`, `quantity: 0`).

8. **Internal field**
   - `orders.stock_restored` on ORM only — never exposed in `OrderResponse`.

9. **Test helpers**
   - `order_checkout_payload()` in `tests/conftest.py`.
   - `insert_product()`, `count_orders()` in `tests/integration/test_orders.py`.

10. **`ProductRepository.get_by_id` + `populate_existing=True`**
    - Ensures integration tests see stock decrements after HTTP checkout uses a different session than the test fixture’s `db_session`.

11. **Code review follow-up (accepted as-is)**
    - No changes applied after review; no critical issues for US1 slice scope.
    - Concurrency: per `research.md` R2, SQLite tests rely on transaction isolation; `SELECT … FOR UPDATE` deferred until PostgreSQL / explicit concurrency task.
    - Rate limiting: not added on `POST /orders` (consistent with `/products` — auth endpoints only).
    - `adjust_quantity` return value / negative-stock guard: not added (pre-check + rollback sufficient for slice).

## Files touched

| File | Role |
|------|------|
| `app/models/order.py` | `Order`, `OrderLineItem` ORM |
| `app/schemas/order.py` | `OrderCreate`, `OrderResponse`, `OrderStatusUpdate` |
| `app/repositories/order_repository.py` | Full repo + `OrderLineSnapshot` |
| `app/repositories/product_repository.py` | `get_by_ids`, `adjust_quantity`, `populate_existing` on `get_by_id` |
| `app/services/order_service.py` | Helpers + `checkout`, domain errors |
| `app/dependencies/auth.py` | `require_customer` |
| `app/routers/orders.py` | `POST /orders` + structlog |
| `app/main.py` | Register orders router |
| `app/database.py` | Import order models for `create_all` |
| `tests/unit/test_order_service.py` | 4 unit tests |
| `tests/integration/test_orders.py` | 10 integration tests |
| `tests/contract/test_orders_contract.py` | 7 contract tests |
| `tests/conftest.py` | `order_checkout_payload` |
| `tests/contract/test_route_access_policy.py` | `test_post_orders_requires_authentication` |

## Spec coverage (US1)

| Requirement | Covered |
|-------------|---------|
| FR-001 customer checkout / admin 403 | Yes |
| FR-002 request shape | Yes |
| FR-003 201 + full Order | Yes |
| FR-004 snapshots | Yes |
| FR-005 server-side `total_amount` | Yes |
| FR-006 stock decrement / 409 | Yes |
| FR-007 missing product 404 | Yes |
| FR-014 auth on orders | Yes |
| FR-016 nested `items` | Yes |
| FR-017 merge duplicates | Yes |

## Out of scope (documented, not implemented in this harness)

- `GET /orders/me`, `GET /orders/{id}` (US2)
- `GET /orders` admin list/filter/limit (US3)
- `PATCH /orders/{id}/status` + cancel restock (US4)
- Alembic migration (still `Base.metadata.create_all` for dev/test)
- `/api/v1/orders` route alias
- Checkout rate limiting
- Row-level locking / concurrent last-unit test (research R2 — Postgres follow-up)
- Harness artifacts for parent feature polish (`T044`–`T049`)
