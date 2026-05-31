# Brainstorm: Product detail (US2) + Admin inventory writes (US3)

## Task

Implement product catalog read-by-id and admin inventory CRUD as two sequential vertical slices:

- **US2:** `GET /products/{product_id}` (public)
- **US3:** `POST /products`, `PUT /products/{product_id}`, `DELETE /products/{product_id}` (admin Bearer)
- **Also:** admin list cap via `GET /products?limit=100` (when `limit` is provided)
- **Reference:** `specs/002-product-catalog/spec.md` (User Stories 2–3), `plan.md`, `tasks.md` (T019–T032)

**Prerequisite:** `GET /products` (US1) is implemented — see `docs/harness-traces/get-products/brainstorm.md`.

## Final Decisions

| Topic | Decision |
|-------|----------|
| Scope | Full US3 — `POST`, `PUT`, `DELETE` + admin `?limit=100` |
| Order | **US2 first**, then **US3** (two checkpoints in one harness plan) |
| Approach | **Thin vertical slice per batch** (router → service → repository) |
| Auth | `app/dependencies/auth.py`: JWT + **DB role** lookup; `require_admin` on writes |
| Admin dev seed | `app/scripts/seed_admin.py` — idempotent `admin@inventory.com` |
| Admin tests | `tests/conftest.py` helpers insert admin/customer + JWT headers |
| URL | Bare `/products` only (no `/api/v1` prefix) |
| Delete | Hard delete → `204`; subsequent `GET` returns `404` (requires US2) |
| Duplicate SKU | DB unique constraint → `409` `{ "detail": "SKU already exists" }` |

## Approaches Considered

| # | Approach | Verdict |
|---|----------|---------|
| 1 | Thin vertical slice per batch (US2 → foundation → US3) | **Selected** |
| 2 | Foundation-first, then wire all routes together | Rejected — long RED window, weaker checkpoints |
| 3 | Router-heavy (auth + SQL in router) | Rejected — duplicates `/auth/me`, breaks layering |

---

## Architecture (Approved)

### Batch 1 — US2 (public detail)

```text
Client
  → GET /products/{product_id}
  → app/routers/products.py
  → app/services/product_service.py  (get_product)
  → app/repositories/product_repository.py  (get_by_id)
  → app/models/product.py
```

### Batch 2 — Shared foundation (before US3 routes)

```text
app/dependencies/auth.py
  extract_bearer_token → get_current_user (AuthService + DB) → require_admin

app/schemas/product.py
  ProductWrite (request body for POST/PUT)

app/repositories/product_repository.py
  get_by_id | create | update | delete | list_products(..., limit)

app/services/product_service.py
  ProductNotFound | DuplicateSku | image_url → ""
```

### Batch 3 — US3 (admin writes)

```text
Client + Authorization: Bearer <token>
  → POST | PUT | DELETE /products[/{product_id}]
  → Depends(require_admin)
  → ProductService → ProductRepository
```

**Auth rule:** Never trust JWT `role` claim alone — `require_admin` loads the user from the database and checks `role == "admin"` (research R4).

---

## API Contract

### Endpoints

| Method | Path | Auth | Success | Error statuses |
|--------|------|------|---------|----------------|
| `GET` | `/products/{product_id}` | Public | `200` `Product` | `404` |
| `POST` | `/products` | Admin Bearer | `201` `Product` | `401`, `403`, `409`, `422` |
| `PUT` | `/products/{product_id}` | Admin Bearer | `200` `Product` | `401`, `403`, `404`, `409`, `422` |
| `DELETE` | `/products/{product_id}` | Admin Bearer | `204` no body | `401`, `403`, `404` |
| `GET` | `/products?limit=N` | Public | `200` `Product[]` | `422` — max `min(N, 100)` when `limit` present |

### Stable `detail` strings (v1)

| Status | `detail` |
|--------|----------|
| `401` | `"Not authenticated"` |
| `403` | `"Admin access required"` |
| `404` | `"Product not found"` |
| `409` | `"SKU already exists"` |
| `422` | Pydantic validation array (FastAPI default) |

### Request body (`ProductWrite`)

Required on POST and PUT (full replacement):

```json
{
  "name": "Widget",
  "description": "A useful widget",
  "sku": "WGT-001",
  "price": 19.99,
  "quantity": 10,
  "category": "general",
  "image_url": ""
}
```

### Response (`Product`)

Same shape as US1 list items — adds `id`, `created_at`, `updated_at` (ISO-8601). `image_url` never `null`; `price` as JSON number.

---

## Files

### New

| File | Responsibility |
|------|----------------|
| `app/dependencies/auth.py` | `extract_bearer_token`, `get_current_user`, `require_admin` |
| `app/scripts/seed_admin.py` | Idempotent admin user `admin@inventory.com` |

### Modified

| File | Change |
|------|--------|
| `app/schemas/product.py` | Add `ProductWrite` |
| `app/repositories/product_repository.py` | `get_by_id`, `create`, `update`, `delete`; `list_products` + optional `limit` |
| `app/services/product_service.py` | CRUD methods; `ProductNotFound`, `DuplicateSku` |
| `app/routers/products.py` | US2 GET + US3 POST/PUT/DELETE; error mapping; structlog |
| `tests/conftest.py` | Admin/customer fixtures + `auth_headers` |
| `tests/integration/test_products.py` | US2 + US3 integration tests |
| `tests/contract/test_products_contract.py` | Detail path + write ops `bearerAuth` |
| `specs/002-product-catalog/quickstart.md` | Document `seed_admin.py` + `ECOM_OPPO_ADMIN_PASSWORD` |

### Optional (same PR only if trivial)

| File | Change |
|------|--------|
| `app/routers/auth.py` | Reuse `extract_bearer_token` from `dependencies/auth.py` on `/auth/me` |

---

## Repository

| Method | Behavior |
|--------|----------|
| `get_by_id(db, id)` | `SELECT` by PK; return row or `None` |
| `create(db, data)` | `INSERT`; catch `IntegrityError` on duplicate `sku` → raise `DuplicateSku` |
| `update(db, id, data)` | Full replace; bump `updated_at`; `404` path via service if missing |
| `delete(db, id)` | Hard `DELETE`; return whether row existed |
| `list_products(db, search, limit)` | Existing search logic; apply `LIMIT min(limit, 100)` **only** when `limit` is not `None` |

---

## Service

| Method | Behavior |
|--------|----------|
| `get_product(db, id)` | `get_by_id` → `ProductResponse` or raise `ProductNotFound` |
| `create_product(db, payload)` | Normalize `image_url` → `""`; persist; map `DuplicateSku` |
| `update_product(db, id, payload)` | Not found → `ProductNotFound`; duplicate SKU → `DuplicateSku` |
| `delete_product(db, id)` | Not found → `ProductNotFound`; else delete |

Domain exceptions (router maps to HTTP):

- `ProductNotFound` → `404`
- `DuplicateSku` → `409`

---

## Admin Bootstrap

### `app/scripts/seed_admin.py`

- **Email:** `admin@inventory.com` (fixed for docs and manual testing)
- **Password:** `ECOM_OPPO_ADMIN_PASSWORD` env var (document a dev-only default in quickstart)
- **Role:** `admin`
- **Idempotent:** skip if email already exists
- **Invocation:** `python -m app.scripts.seed_admin` (mirror `seed_products.py`)

### Test helpers (`tests/conftest.py`)

- `create_admin_user(db)` / `create_customer_user(db)` via `UserRepository` + `hash_password`
- `admin_auth_headers` / `customer_auth_headers` — Bearer tokens for integration tests
- Do **not** use `/auth/register` for admin (register forces `customer` role)

---

## Observability

Mirror `product_list_*` pattern (structlog):

| Event | When |
|-------|------|
| `product_get_success` / `product_get_not_found` / `product_get_error` | US2 |
| `product_create_success` / `product_create_conflict` / … | US3 POST |
| `product_update_*` | US3 PUT |
| `product_delete_*` | US3 DELETE |

Fields: `request_id`, `path`, `method`, `status_code`, `latency_ms`, `outcome`, `product_id` (when known).

---

## Testing (TDD)

Per `tasks.md` T019–T032. **US2 must be GREEN before US3 delete verification.**

### Batch 1 — US2

| Test | Assert |
|------|--------|
| `GET /products/{id}` no auth | `200`, full product shape |
| Unknown id | `404`, `"detail"` present |
| Contract | Path exists; `security: []` on GET |

```bash
pytest tests/integration/test_products.py -k "detail or get_by_id" -v
pytest tests/contract/test_products_contract.py -k "product_id or detail" -v
```

### Batch 2 — US3

| Test | Assert |
|------|--------|
| Admin POST | `201`, body includes `id`, timestamps |
| Customer POST | `403` |
| No token POST | `401` |
| Duplicate SKU | `409` |
| Admin PUT | `200` |
| Admin DELETE | `204` |
| GET after DELETE | `404` |
| Admin `?limit=100` with >100 rows | `len(body) <= 100` |
| Contract | POST/PUT/DELETE require `bearerAuth` |

```bash
pytest tests/integration/test_products.py -k "admin or create or update or delete" -v
pytest tests/contract/test_products_contract.py -v
```

Coverage target: ≥80% on new product modules; 100% on admin write paths.

---

## Out of Scope (This Harness)

- Alembic migration (table exists via `create_all`; migration can follow in polish T002/T005)
- `PATCH`, soft delete, `is_active`
- `/api/v1/products` aliases
- Global auth middleware (deps-only gating per research R7)
- Order FK / delete blocking
- `GET /products` changes beyond adding `limit` param

## Public Allowlist (Polish / T037)

When extending route access policy tests:

- `("GET", "/products")`
- `("GET", "/products/{product_id}")` or pattern for numeric id

Writes are **not** allowlisted — protected by `require_admin` only.

---

## Related Artifacts

| Document | Path |
|----------|------|
| Feature spec | `specs/002-product-catalog/spec.md` |
| Implementation plan | `specs/002-product-catalog/plan.md` |
| Tasks US2–US3 | `specs/002-product-catalog/tasks.md` T019–T032 |
| OpenAPI contract | `specs/002-product-catalog/contracts/products-api.yaml` |
| Full catalog design | `docs/superpowers/specs/2026-05-27-product-catalog-design.md` |
| US1 harness | `docs/harness-traces/get-products/brainstorm.md` |
| Quickstart | `specs/002-product-catalog/quickstart.md` |

---

## Status

**Approved** — Approach 1 (thin vertical slice). Ready for implementation plan at `docs/harness-traces/products-us2-us3/plan.md`.
