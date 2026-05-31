# Implementation Plan: Orders & Checkout

**Branch**: `003-orders-checkout` | **Date**: 2026-05-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-orders-checkout/spec.md`  
**Design reference**: `docs/superpowers/specs/2026-05-28-orders-checkout-design.md`

## Summary

Deliver customer checkout (`POST /orders`) with mandatory line-item snapshots and atomic stock decrement, customer order history (`GET /orders/me`, `GET /orders/{id}`), and admin operations (`GET /orders` with optional `status`/`limit`, `PATCH /orders/{id}/status` with one-time cancel restock). Implement layered `routers → services → repositories`, async SQLAlchemy, JWT auth (`customer` checkout, `admin` list/PATCH), Alembic migration for `orders` + `order_line_items`, OpenAPI contract, and TDD (pytest + httpx AsyncClient).

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (async), asyncpg, Alembic, python-jose, passlib+bcrypt, pydantic-settings, structlog  
**Storage**: PostgreSQL (production via `ECOM_OPPO_DATABASE_URL`); SQLite in-memory/file for tests and default dev  
**Testing**: pytest, pytest-asyncio, httpx `AsyncClient` with ASGI transport  
**Target Platform**: Linux/macOS API server (uvicorn)  
**Project Type**: Single FastAPI backend (`app/`)  
**Performance Goals**: Checkout completes in one request under normal dev load; admin list with `limit=100` returns within interactive UI expectations  
**Constraints**: Async-only I/O; plain `Order[]` / single `Order` JSON (no envelope); nested key `items`; errors `{ "detail": ... }`; all `/orders*` authenticated  
**Scale/Scope**: v1 order volume modest; 6 HTTP endpoints; 2 new tables; depends on existing `users` + `products`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **API-First Contracts**: `specs/003-orders-checkout/contracts/orders-api.yaml` defines paths, schemas, auth, errors.
- [x] **Test-First Delivery**: Plan defines unit/integration/contract tests; implement RED→GREEN per user story.
- [x] **Security by Default**: All order routes require Bearer; no public `/orders*`; checkout customer-only; admin routes use `require_admin`; owner-or-admin on detail GET.
- [x] **Async Throughout**: All DB access via `AsyncSession`; transactional checkout in async service.
- [x] **Observability by Default**: structlog per endpoint (`order_checkout`, `order_status_update`, `order_list`, `order_get`) with latency and outcome.

**Post-design re-check**: All gates pass. No constitution violations requiring complexity tracking.

## Project Structure

### Documentation (this feature)

```text
specs/003-orders-checkout/
├── spec.md
├── plan.md              # This file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── orders-api.yaml
└── tasks.md             # Created by /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
app/
├── main.py                          # include orders router
├── database.py                      # import order models for create_all
├── models/
│   ├── user.py
│   ├── product.py
│   └── order.py                       # NEW: Order, OrderLineItem
├── schemas/
│   ├── auth.py
│   ├── product.py
│   └── order.py                       # NEW
├── repositories/
│   ├── user_repository.py
│   ├── product_repository.py          # EXTEND: get_by_ids, adjust_quantity (no commit)
│   └── order_repository.py            # NEW
├── services/
│   ├── auth_service.py
│   ├── product_service.py
│   └── order_service.py               # NEW: checkout, update_status, list/get
├── routers/
│   ├── auth.py
│   ├── products.py
│   └── orders.py                        # NEW
└── dependencies/
    ├── rate_limit.py
    └── auth.py                          # EXTEND: require_customer

alembic/versions/
└── xxxx_create_orders_tables.py         # NEW

tests/
├── integration/
│   └── test_orders.py                   # NEW
├── contract/
│   ├── test_orders_contract.py          # NEW
│   └── test_route_access_policy.py      # EXTEND: orders 401 without token
└── unit/
    └── test_order_service.py            # NEW
```

**Structure Decision**: Extend existing flat `app/` layout to match auth and products. `OrderService` orchestrates checkout and restock; `ProductRepository` gains non-committing stock helpers for use inside service transaction.

## Phase 0: Research

Completed — see [research.md](./research.md). Resolved: atomic checkout transaction, restock idempotency, auth roles, HTTP status codes, `items` wire key, admin `limit`, no public order routes.

## Phase 1: Design & Contracts

Completed artifacts:

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| API contract | [contracts/orders-api.yaml](./contracts/orders-api.yaml) |
| Quickstart | [quickstart.md](./quickstart.md) |

### Implementation sequence (for `/speckit-tasks`)

1. **Alembic + models** — `Order`, `OrderLineItem` ORM; migration; import in `database.py`.
2. **ProductRepository extensions** — `get_by_ids`, `adjust_quantity` (flush only, no commit).
3. **OrderRepository** — create order+lines, list (me/admin/filter/limit), get by id, update status + `stock_restored`.
4. **Schemas** — `OrderCreate`, `Order`, `OrderLineItem`, `OrderStatusUpdate`; field alias `items`.
5. **OrderService** — `checkout()` (merge lines, validate, snapshot, total, stock), `update_status()` (restock rules), access checks.
6. **Auth deps** — `require_customer` for POST `/orders`.
7. **Router** — six endpoints with `response_model`; map domain errors to 401/403/404/409/422.
8. **main.py** — `include_router(orders_router)`.
9. **Tests** — contract + integration + unit per quickstart; extend route access policy.
10. **Docs** — optional sync note in `docs/architecture.md` ERD (orders tables live).

### TDD expectations

| Test file | Covers |
|-----------|--------|
| `tests/contract/test_orders_contract.py` | OpenAPI paths, Order schema, `items` key, auth security |
| `tests/integration/test_orders.py` | Checkout 201 + snapshots + stock; 409/404; me/detail; admin list/filter/limit; PATCH cancel restock once; 401/403 |
| `tests/unit/test_order_service.py` | Line merge, total_amount, restock idempotency |
| `tests/contract/test_route_access_policy.py` | All `/orders*` return 401 without token |

Coverage target: ≥80% on new modules; 100% on checkout and auth-gated paths.

### Observability

Log fields: `request_id`, `path`, `method`, `status_code`, `latency_ms`, `outcome`, `user_id`, `order_id` (when known). Events: `order_checkout`, `order_status_update` (include `restocked: bool`), `order_list`, `order_get`. No tokens in logs.

### Domain errors (service → router)

| Service exception | HTTP |
|-------------------|------|
| `InsufficientStockError` | 409 |
| `ProductNotFoundForOrderError` | 404 |
| `OrderNotFoundError` | 404 |
| `ForbiddenOrderAccessError` | 403 |

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Phase 2 Boundary

This plan stops before `tasks.md` generation. Run `/speckit-tasks` to produce dependency-ordered implementation tasks.
