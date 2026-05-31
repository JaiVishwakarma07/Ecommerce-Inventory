# Product Catalog & Admin CRUD — Design Spec

**Date:** 2026-05-27  
**Status:** Approved (brainstorm)  
**Feature:** Product catalog & admin CRUD for ECOM_OPPO FastAPI REST API

## Summary

Implement a thin vertical slice for products: SQLite-backed persistence, router → service → repository layering (matching auth), bare `/products` paths, plain `Product[]` JSON (no pagination envelope), public read endpoints, and admin-only writes authorized via `Authorization: Bearer <JWT>` with `role === "admin"`.

Frontend parity is the primary success criterion. Orders snapshot `name`/`price` at checkout on the backend; product delete is a hard remove with no frontend handling for order-reference conflicts.

## Goals

- Serve browse catalog: `GET /products?search=...` (optional search, no limit, all matches).
- Serve admin catalog: `GET /products?limit=100` (plain array, cap at 100).
- Serve product detail: `GET /products/{id}` (public).
- Admin CRUD: `POST`, `PUT` (full body), `DELETE` (204 hard delete).
- Align response/request JSON with the existing frontend admin form and catalog UI.

## Non-Goals (v1)

- `/api/v1/products` route aliases.
- Pagination metadata (`total`, `page`, `skip`).
- `PATCH`, soft delete, `is_active`.
- `staff` role or API keys.
- `?category=` or `?skip=` query params.
- `409` on delete when product is referenced by orders.
- Order line-item snapshot implementation (orders change; noted for coordination only).

## Approach

**Approach 1 — Thin vertical slice (selected).** Single `products` table with `ProductRepository`, `ProductService`, and `products` router. Search and optional `limit` implemented in SQLAlchemy repository queries. One shared Pydantic schema for request/response (plus `id` and timestamps on responses).

Rejected alternatives:

- In-memory filter after full table load (does not scale; unnecessary).
- Separate read/write DTOs (frontend uses one shape everywhere).

## API Contract

### Base URL

Paths are relative to `VITE_API_URL` (default `http://127.0.0.1:8000`). **No version prefix.**

### Product JSON

**Response** (`Product`) — all endpoints returning a product:

```json
{
  "id": 1,
  "name": "Widget",
  "description": "A useful widget",
  "sku": "WGT-001",
  "price": 19.99,
  "quantity": 0,
  "category": "general",
  "image_url": "",
  "created_at": "2026-05-27T12:00:00Z",
  "updated_at": "2026-05-27T12:00:00Z"
}
```

- `price`: JSON number (two decimal places in practice); `formatINR` on frontend.
- `quantity`: integer ≥ 0; `0` means out of stock — **still listed** on public catalog.
- `image_url`: string, never `null`; use `""` when no image.
- `created_at` / `updated_at`: ISO-8601 strings (timezone-aware storage; `Z` suffix acceptable).

**Request body** (`POST`, `PUT`) — admin always sends full object:

```json
{
  "name": "Widget",
  "description": "A useful widget",
  "sku": "WGT-001",
  "price": 19.99,
  "quantity": 0,
  "category": "general",
  "image_url": ""
}
```

All fields required on create and update. Response adds `id`, `created_at`, `updated_at`.

### Endpoints

| Method | Path | Auth | Success | Notes |
|--------|------|------|---------|-------|
| `GET` | `/products` | Public | `200` `Product[]` | See query params below |
| `GET` | `/products/{id}` | Public | `200` `Product` | `404` if not found |
| `POST` | `/products` | Admin Bearer | `201` `Product` | `409` duplicate SKU |
| `PUT` | `/products/{id}` | Admin Bearer | `200` `Product` | Full replacement; `404`, `409` |
| `DELETE` | `/products/{id}` | Admin Bearer | `204` no body | Hard delete; `404` |

#### `GET /products` query parameters

| Param | Used by | Behavior |
|-------|---------|----------|
| `search` | Browse (optional) | Case-insensitive partial match on `name`, `sku`, or `category` (OR). Omit = all products. |
| `limit` | Admin (`100`) | When present: `LIMIT min(limit, 100)`. When **absent**: **no SQL limit** — return all matching rows (browse must not silently truncate). |

Not used by frontend in v1: `skip`, `category` (as separate filter).

### Authentication & authorization

- Header: `Authorization: Bearer <access_token>` (JWT from `POST /auth/login`).
- **Public:** `GET /products`, `GET /products/{id}` (allowlisted; no token required).
- **Admin writes:** `POST`, `PUT`, `DELETE` require valid token and `user.role == "admin"`.
- **401** — missing or invalid token (frontend clears storage on 401).
- **403** — valid token but `role !== "admin"`.
- First admin user: created outside the app (seed script or env), not via register UI. Register continues to assign `customer` only.

### Error responses

FastAPI default shape (frontend expects `detail`):

```json
{ "detail": "..." }
```

or validation:

```json
{ "detail": [ { "loc": [...], "msg": "...", "type": "..." } ] }
```

| Status | When |
|--------|------|
| `400` | Malformed request (project validation handler) |
| `401` | Unauthenticated on protected write |
| `403` | Authenticated non-admin on write |
| `404` | Product id not found |
| `409` | Duplicate `sku` on create/update |
| `422` | Pydantic validation failure |

### HTTP status summary

| Operation | Success code |
|-----------|----------------|
| List / get | `200` |
| Create | `201` |
| Update | `200` |
| Delete | `204` |

## Data Model

### Table: `products`

| Column | SQL type | Constraints |
|--------|----------|-------------|
| `id` | INTEGER | PK, autoincrement |
| `name` | VARCHAR(255) | NOT NULL |
| `description` | TEXT | NOT NULL (empty string allowed) |
| `sku` | VARCHAR(255) | NOT NULL, UNIQUE, indexed |
| `price` | NUMERIC(10,2) | NOT NULL, ≥ 0 |
| `quantity` | INTEGER | NOT NULL, ≥ 0 |
| `category` | VARCHAR(100) | NOT NULL |
| `image_url` | VARCHAR(2048) | NOT NULL, default `''` |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

No soft-delete columns. Hard `DELETE` removes the row.

### Validation (Pydantic)

| Field | Rules |
|-------|--------|
| `name` | Non-empty, max 255 |
| `description` | Required; `""` allowed |
| `sku` | Non-empty; unique in DB |
| `price` | Number ≥ 0; at most 2 decimal places |
| `quantity` | Integer ≥ 0 |
| `category` | Non-empty, max 100 |
| `image_url` | String; default/coerce to `""`; never `null` in API |

Optional: lenient URL check when `image_url` is non-empty (warn/fail only if clearly invalid — prefer permissive for v1).

## Architecture

### Layering

```text
app/
├── models/product.py
├── schemas/product.py
├── repositories/product_repository.py
├── services/product_service.py
├── routers/products.py
└── dependencies/auth.py    # get_current_user, require_admin
```

**Request flow:**

```text
Client → products router → ProductService → ProductRepository → AsyncSession → SQLite
                ↓
         require_admin (writes only)
                ↓
         AuthService / JWT decode (existing pattern)
```

### Repository responsibilities

- `list_products(search, limit)` — build query; apply `OR` ILIKE/LIKE for search; apply `LIMIT` only when `limit` is not `None`.
- `get_by_id(id)` — single row or none.
- `create(product)` — insert; catch integrity error on duplicate SKU.
- `update(id, product)` — full replace; set `updated_at`.
- `delete(id)` — hard delete; return whether row existed.

### Service responsibilities

- Map repository exceptions to domain errors (`ProductNotFound`, `DuplicateSku`).
- Normalize `image_url` to `""` before persist.
- No business logic beyond validation and auth delegation.

### Router responsibilities

- Declare `response_model` on every endpoint.
- Wire `Depends(get_db_session_with_request)`, `Depends(require_admin)` on writes.
- Query params: `search: str | None = None`, `limit: int | None = None`.
- Structured logging (structlog): `product_list`, `product_create`, etc., with `request_id`, `latency_ms`, `outcome`, `product_id`.

### Database bootstrap

Extend existing `Base.metadata.create_all` / bootstrap path used for `users` to include `Product` model (same SQLite async pattern as auth persistence change).

### Public route allowlist

Add to route access policy (middleware or documented allowlist tests):

- `("GET", "/products")`
- `GET` paths matching `/products/{id}` (numeric id)

All write routes remain protected via `require_admin`.

## Search implementation

When `search` is provided (trimmed, non-empty):

```sql
WHERE lower(name) LIKE '%term%'
   OR lower(sku) LIKE '%term%'
   OR lower(category) LIKE '%term%'
```

SQLite: use `LIKE` with lowered columns or `COLLATE NOCASE` as appropriate for async SQLAlchemy.

When `search` is omitted: no search filter.

When `limit` is omitted: no `LIMIT` clause.

When `limit` is provided: `LIMIT min(limit, 100)`.

## Admin bootstrap

- Document seed command or env vars (e.g. `ADMIN_EMAIL`, `ADMIN_PASSWORD`) in feature quickstart.
- Seed creates one user with `role="admin"` and hashed password.
- Not exposed in register endpoint.

## Testing strategy (TDD)

Write tests before implementation. Minimum coverage target: 80% on product module; 100% on auth-gated write paths.

| Suite | Cases |
|-------|--------|
| Integration | Public `GET /products` without token returns 200 array |
| Integration | Browse list without `limit` returns all seeded products (>100 rows test) |
| Integration | Admin list with `limit=100` returns at most 100 |
| Integration | `search` matches name, sku, category |
| Integration | Admin CRUD happy path |
| Integration | Customer JWT on POST → 403 |
| Integration | No token on POST → 401 |
| Integration | Duplicate SKU → 409 |
| Integration | `GET /products/{id}` 404 |
| Integration | `DELETE` → 204; subsequent GET 404 |
| Integration | `image_url` omitted in POST body coerced to `""`; response never null |
| Contract | OpenAPI YAML under `specs/product-catalog/contracts/products-api.yaml` |
| Contract | Public allowlist includes product GET routes |

## Orders coordination (reference only)

- Frontend already calls `POST /orders`.
- Order line items should store `product_name` and `price` at checkout time (orders feature).
- Product `DELETE` does not return `409` for order references in this slice; snapshots preserve historical display.

## Artifact locations (implementation phase)

| Artifact | Path |
|----------|------|
| Feature spec | `specs/product-catalog/spec.md` |
| Plan | `specs/product-catalog/plan.md` |
| API contract | `specs/product-catalog/contracts/products-api.yaml` |
| Tasks | `specs/product-catalog/tasks.md` |

## Decision log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Route prefix | `/products` only | Frontend uses bare paths on `VITE_API_URL` |
| List shape | Plain `Product[]` | No pagination UI |
| Browse limit | None | Avoid silent truncation |
| Admin list | `limit=100` | Matches admin UI |
| Update verb | PUT full body | Admin form sends all fields |
| Delete | Hard 204 | Frontend treats delete as permanent |
| `image_url` | `""` not null | Frontend checks truthy string |
| Admin auth | JWT `role=admin` | Matches existing interceptor |
| Search | Single `search` param | Frontend browse behavior |
