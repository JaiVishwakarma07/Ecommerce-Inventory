# Research: Orders & Checkout

**Feature**: `003-orders-checkout`  
**Date**: 2026-05-28

## R1 — Atomic checkout transaction

**Decision**: `OrderService.checkout()` runs inside one `async with db.begin():` (or explicit commit/rollback) spanning: merge line items → load products → validate stock → insert order + line items → decrement `products.quantity`. No partial commits mid-flow.

**Rationale**: FR-006 requires stock decrement and order creation to succeed or fail together. Current `ProductRepository` methods call `commit()` per operation; checkout adds repository helpers that **flush only** (`adjust_quantity`, `get_by_ids`) while the service owns the transaction boundary.

**Alternatives considered**:
- Separate commits per product update (reject): oversell race and partial orders.
- Saga/outbox (reject): out of scope for v1 monolith.

## R2 — Concurrency / locking

**Decision**: Load products by id list in checkout; validate `quantity >= requested` before writes. On PostgreSQL, use `SELECT ... FOR UPDATE` when dialect supports it; on SQLite tests, rely on transaction isolation + single-writer test DB (document limitation).

**Rationale**: v1 catalog size is small; primary goal is atomicity within one request. Full optimistic locking (`version` column) deferred to Phase 2.

**Alternatives considered**:
- Optimistic locking column on `products` (reject for v1): extra migration and retry logic.
- No locking (reject): concurrent last-unit orders can oversell.

## R3 — Line item merge in POST body

**Decision**: Service merges duplicate `product_id` keys by summing `quantity` before stock validation.

**Rationale**: FR-017; defensive against duplicate cart rows.

## R4 — Cancel restock idempotency

**Decision**: `orders.stock_restored` boolean (internal, not in API). Set `true` after first successful restock on transition to `cancelled`. Skip restock if already `cancelled` or `stock_restored`.

**Rationale**: FR-013; prevents double restock on repeated PATCH or `cancelled` → `cancelled`.

**Alternatives considered**:
- Status history table (reject): overkill for v1.
- Restock only from `pending` (reject): user chose restock from any prior status once.

## R5 — Deleted product on restock

**Decision**: If `product_id` no longer exists, skip that line and emit structlog warning; PATCH still returns `200`.

**Rationale**: Catalog allows hard delete; admin cancel must not fail operations.

## R6 — Auth dependencies

**Decision**: Reuse `get_current_user` and `require_admin`. Add `require_customer` for `POST /orders` (`role == "customer"` else `403`).

**Rationale**: FR-001; admin checkout forbidden. Matches existing `dependencies/auth.py` pattern.

## R7 — Public route policy

**Decision**: No `/orders*` routes on public allowlist. Extend contract test `test_route_access_policy.py` to assert all order paths return `401` without token.

**Rationale**: FR-014; constitution default-protected.

## R8 — Wire JSON key `items`

**Decision**: Pydantic models and OpenAPI use `items` for nested line arrays; DB table remains `order_line_items`.

**Rationale**: SPA contract (`MyOrders.jsx`, `OrderDetail.jsx`); FR-016.

## R9 — Stock error HTTP code

**Decision**: Insufficient stock → **409** with string `detail` naming `product_id`. Missing product → **404**.

**Rationale**: Approved design; distinct from validation `422`.

## R10 — Admin list `limit`

**Decision**: Optional `limit` query on `GET /orders`; when present apply `min(limit, 100)`; when omitted return all matching orders (newest first).

**Rationale**: Aligns with admin product list pattern; FR-010.

## R11 — Status enum validation

**Decision**: Pydantic `Literal` for five status strings on PATCH body and optional `status` query filter.

**Rationale**: Invalid filter → 422; free transitions otherwise (no graph validation).

## R12 — Alembic vs create_all

**Decision**: Add Alembic revision `orders` + `order_line_items`; register models in `app/database.py` bootstrap import (mirror products).

**Rationale**: Constitution + existing product migration path; SQLite tests use `create_all` until `alembic upgrade` in dev.
