# Research: Product Catalog & Admin Inventory

**Feature**: `002-product-catalog`  
**Date**: 2026-05-27

## R1 — Database target vs current repo state

**Decision**: Implement `products` with Alembic migration targeting PostgreSQL (`postgresql+asyncpg://`); keep SQLite (`sqlite+aiosqlite`) for local dev and in-memory tests via existing `Settings.resolved_database_url`.

**Rationale**: User stack specifies PostgreSQL + Alembic. Auth already ships with async SQLAlchemy and SQLite bootstrap (`Base.metadata.create_all` in `app/database.py`). Product feature adds the first Alembic revision so production schema is versioned; tests continue to use `:memory:` SQLite without requiring Docker for CI.

**Alternatives considered**:
- PostgreSQL-only (reject): breaks current fast local/CI test loop.
- SQLite-only without Alembic (reject): conflicts with stated stack and constitution long-term migration path.

## R2 — Search query pattern (PostgreSQL + SQLite)

**Decision**: Repository applies trimmed `search` with SQL `OR` across `lower(name)`, `lower(sku)`, `lower(category)` using `LIKE '%term%'` (portable across SQLite and PostgreSQL).

**Rationale**: Spec requires case-insensitive partial match on three fields. `ILIKE` is PostgreSQL-specific; `lower(column).like(pattern)` works in both dialects used by the project.

**Alternatives considered**:
- PostgreSQL full-text search (reject): overkill for v1 catalog size.
- In-memory filter (reject): violates scale assumption for browse-without-limit.

## R3 — List `limit` semantics

**Decision**: Apply SQL `LIMIT` only when query param `limit` is present; cap at `min(limit, 100)`. Omit param → no `LIMIT` clause.

**Rationale**: Frontend browse never sends `limit`; admin sends `limit=100`. Silent default cap would violate FR-003/SC-001.

**Alternatives considered**:
- Default `limit=50` (reject): breaks browse parity.
- High default (e.g. 1000) when omitted (reject): still a hidden cap; spec says no cap.

## R4 — Admin authorization dependency

**Decision**: Add `app/dependencies/auth.py` with `get_current_user` (JWT + DB role lookup, mirroring auth router) and `require_admin` (`role == "admin"` → else 403).

**Rationale**: Auth exists but role-gated dependencies are not yet extracted. Product writes are the first admin-only surface; reusable dependency serves orders/dashboard later.

**Alternatives considered**:
- Inline checks in router (reject): duplicates logic across future admin routes.
- Trust role from JWT claims (reject): auth plan requires DB-backed role per request.

## R5 — SKU uniqueness and errors

**Decision**: DB unique constraint on `sku`; catch `IntegrityError` in repository → service raises `DuplicateSkuError` → router returns **409** with `{ "detail": "SKU already exists" }` (or similar stable message).

**Rationale**: FR-009; race-safe vs application-only check.

## R6 — `image_url` null handling

**Decision**: Pydantic schema defaults `image_url` to `""`; validator coerces `None` → `""`; ORM column `NOT NULL` default `''`.

**Rationale**: FR-015; frontend uses truthy check on string.

## R7 — Public route policy

**Decision**: Document public allowlist in contract tests: `GET /products`, `GET /products/{product_id}`. Writes use `Depends(require_admin)` only (no global middleware required for v1 if dependencies enforce auth).

**Rationale**: Matches auth spec allowlist entries; constitution default-deny satisfied for POST/PUT/DELETE.

## R8 — Price storage

**Decision**: `NUMERIC(10, 2)` in PostgreSQL migration; SQLAlchemy `Numeric(10, 2)`; Pydantic `Decimal` or constrained `float` serialized as JSON number.

**Rationale**: Avoid float drift in persistence; API returns JSON number for `formatINR`.

## R9 — Alembic bootstrap

**Decision**: Initialize `alembic/` (async env) if missing; first revision `create_products_table` after `users` exists.

**Rationale**: User-mandated Alembic; products is first new table after auth.

**Alternatives considered**:
- `create_all` only (reject): no production migration trail.

## R10 — Contract location and draft alignment

**Decision**: OpenAPI contract at `specs/002-product-catalog/contracts/products-api.yaml`. Omit `?category=` filter (not in feature spec v1). Use `product_id` path param name in OpenAPI; route implementation `/products/{id}`.

**Rationale**: Spec FR-014 and brainstorm supersede draft’s `?category=` for this feature.
