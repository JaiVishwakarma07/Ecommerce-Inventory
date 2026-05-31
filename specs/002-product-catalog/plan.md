# Implementation Plan: Product Catalog & Admin Inventory

**Branch**: `002-product-catalog` | **Date**: 2026-05-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-product-catalog/spec.md`  
**Design reference**: `docs/superpowers/specs/2026-05-27-product-catalog-design.md`

## Summary

Deliver public product browsing (`GET /products`, `GET /products/{id}`) and admin inventory CRUD (`POST`, `PUT`, `DELETE`) on bare `/products` paths with plain `Product[]` JSON. Implement layered `routers → services → repositories → models`, async SQLAlchemy, JWT admin gating (`role === "admin"`), Alembic migration for `products`, and TDD coverage (pytest + httpx AsyncClient).

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (async), asyncpg, Alembic, python-jose, passlib+bcrypt, pydantic-settings, structlog  
**Storage**: PostgreSQL (production via `ECOM_OPPO_DATABASE_URL=postgresql+asyncpg://...`); SQLite in-memory/file for tests and default dev (existing `app/config.py`)  
**Testing**: pytest, pytest-asyncio, httpx `AsyncClient` with ASGI transport  
**Target Platform**: Linux/macOS API server (uvicorn)  
**Project Type**: Single FastAPI backend (`app/`)  
**Performance Goals**: Browse list for ≤500 products in one request without timeout under normal dev hardware  
**Constraints**: Async-only I/O; no pagination envelope; browse must not apply default `LIMIT`; errors as `{ "detail": ... }`  
**Scale/Scope**: v1 catalog ≤500 SKUs; 5 HTTP endpoints; 1 new table

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **API-First Contracts**: `specs/002-product-catalog/contracts/products-api.yaml` defines paths, schemas, auth, errors.
- [x] **Test-First Delivery**: Plan defines unit/integration/contract tests; implement RED→GREEN per endpoint.
- [x] **Security by Default**: GET list/detail public (allowlisted); POST/PUT/DELETE require Bearer + admin role from DB.
- [x] **Async Throughout**: All DB access via `AsyncSession`; no sync SQL in request path.
- [x] **Observability by Default**: structlog events per endpoint (`product_list`, `product_create`, etc.) with latency and outcome.

**Post-design re-check**: All gates pass. No constitution violations requiring complexity tracking.

## Project Structure

### Documentation (this feature)

```text
specs/002-product-catalog/
├── spec.md
├── plan.md              # This file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── products-api.yaml
└── tasks.md             # Created by /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
app/
├── main.py                          # include products router; allowlist docs
├── config.py
├── database.py
├── core/security.py
├── models/
│   ├── user.py
│   └── product.py                   # NEW
├── schemas/
│   ├── auth.py
│   └── product.py                   # NEW
├── repositories/
│   ├── user_repository.py
│   └── product_repository.py        # NEW
├── services/
│   ├── auth_service.py
│   └── product_service.py           # NEW
├── routers/
│   ├── auth.py
│   └── products.py                  # NEW
└── dependencies/
    ├── rate_limit.py
    └── auth.py                        # NEW: get_current_user, require_admin

alembic/
├── env.py
└── versions/
    └── xxxx_create_products_table.py  # NEW

tests/
├── integration/
│   └── test_products.py               # NEW
├── contract/
│   └── test_products_contract.py      # NEW
└── unit/
    └── test_product_service.py        # NEW (optional)
```

**Structure Decision**: Extend existing flat `app/` layout (not `app/api/routes/`) to match implemented auth code. New work is isolated under product-* modules plus shared `dependencies/auth.py`.

## Phase 0: Research

Completed — see [research.md](./research.md). All technical context items resolved (PostgreSQL+Alembic vs SQLite dev, search pattern, limit semantics, admin deps, SKU errors).

## Phase 1: Design & Contracts

Completed artifacts:

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| API contract | [contracts/products-api.yaml](./contracts/products-api.yaml) |
| Quickstart | [quickstart.md](./quickstart.md) |

### Implementation sequence (for `/speckit-tasks`)

1. **Alembic + model** — `Product` ORM, migration, register model in `Base`.
2. **Auth dependencies** — `get_current_user`, `require_admin` (DB role lookup).
3. **Repository** — list/get/create/update/delete + search + conditional limit.
4. **Service** — domain errors (`ProductNotFound`, `DuplicateSku`), `image_url` normalization.
5. **Schemas** — `ProductWrite`, `ProductResponse` with `response_model` on routes.
6. **Router** — wire endpoints; structlog metrics.
7. **main.py** — `include_router(products_router)` prefix `""` (paths `/products`).
8. **Tests** — contract + integration per quickstart; allowlist test update.
9. **Docs** — sync `docs/design/api-contract-draft.md` note: v1 uses `search` not `category` filter.

### TDD expectations

| Test file | Covers |
|-----------|--------|
| `tests/contract/test_products_contract.py` | OpenAPI paths, Product schema fields, public vs secured |
| `tests/integration/test_products.py` | Browse no-limit (>100 rows), search, admin CRUD, 401/403/409 |
| `tests/contract/test_route_access_policy.py` | Extend allowlist for GET products |

Coverage target: ≥80% on new modules; 100% on admin write paths.

### Observability

Log fields (mirror auth): `request_id`, `path`, `method`, `status_code`, `latency_ms`, `outcome`, `product_id` (when applicable). Counters: `product_list_success`, `product_create_conflict`, etc.

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Phase 2 Boundary

This plan stops before `tasks.md` generation. Run `/speckit-tasks` to produce dependency-ordered implementation tasks.
