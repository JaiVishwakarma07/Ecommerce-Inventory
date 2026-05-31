# Brainstorm: GET /products (US1 browse slice)

## Task

Implement public product catalog list as a focused vertical slice:

- **Endpoint:** `GET /products` (bare path only — no `/api` or `/api/v1` prefix)
- **Reference:** `specs/002-product-catalog/spec.md` (User Story 1), `plan.md`, `tasks.md` (T012–T018)

## Final Decisions

| Topic | Decision |
|-------|----------|
| URL | `/products` only (matches spec FR-014 and React `VITE_API_URL`) |
| Scope | US1 end-to-end: foundation + list endpoint + minimal dev seed |
| Approach | Thin vertical slice (router → service → repository → model) |
| Auth | Public — no Bearer token required |
| Response | Plain `Product[]` JSON array (no pagination envelope) |
| `?search=` | In scope — case-insensitive partial match on `name`, `sku`, `category` |
| `?limit=` | Out of scope for this slice (browse never sends it; no silent cap) |
| Seed | Minimal dev seed (3–5 products, one with `quantity: 0`); idempotent by SKU |

## Architecture (Approved)

```text
Client
  → GET /products[?search=]
  → app/routers/products.py
  → app/services/product_service.py
  → app/repositories/product_repository.py
  → app/models/product.py
  → AsyncSession (SQLite dev/test | PostgreSQL prod)
```

**New files**

| File | Responsibility |
|------|----------------|
| `app/models/product.py` | `products` ORM table |
| `app/schemas/product.py` | `ProductWrite`, `ProductResponse` |
| `app/repositories/product_repository.py` | `list_products(search)` async queries |
| `app/services/product_service.py` | List workflow, `image_url` → `""` |
| `app/routers/products.py` | `GET /products`, structlog |
| `app/scripts/seed_products.py` | Idempotent dev seed by SKU |
| `alembic/versions/*_create_products_table.py` | Migration (if Alembic wired) |

**Modified files**

| File | Change |
|------|--------|
| `app/main.py` | `include_router(products_router)` — no path prefix |
| `app/database.py` | Import `Product` for `create_all` bootstrap |

## API Contract (This Slice)

### `GET /products`

- **Auth:** none (public allowlist)
- **Success:** `200` — JSON array of `Product`
- **Query:** `search` optional string

### `Product` response shape

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

- `image_url`: always string; use `""` when absent — never `null`
- `quantity: 0`: included in list (UI shows “Out of stock”)
- `price`: JSON number

### Errors

- `422` — invalid query/body → `{ "detail": [...] }` (Pydantic)

## Data Model

Per `specs/002-product-catalog/data-model.md`:

| Column | Notes |
|--------|--------|
| `id` | PK |
| `name` | VARCHAR(255), required |
| `description` | TEXT, `""` allowed |
| `sku` | UNIQUE |
| `price` | NUMERIC(10,2) ≥ 0 |
| `quantity` | INTEGER ≥ 0 |
| `category` | VARCHAR(100) |
| `image_url` | NOT NULL, default `''` |
| `created_at`, `updated_at` | TIMESTAMPTZ |

## Repository: `list_products(search)`

1. Start with `SELECT` from `products`
2. If `search` is non-empty after trim:
   - `WHERE lower(name) LIKE '%term%' OR lower(sku) LIKE ... OR lower(category) LIKE ...`
3. **Do not** apply `LIMIT` (browse has no cap)
4. Return ORM rows mapped to `ProductResponse`

## Dev Seed (Minimal)

- Entry point: `app/scripts/seed_products.py` (or documented `python -m` invocation)
- Insert 3–5 products if SKU not already present
- Include at least one row with `quantity: 0`
- Example SKUs: `WGT-001`, `GAD-002`, `OUT-003` (zero stock)

## Observability

Mirror auth router pattern (structlog):

- Event: `product_list_success` / `product_list_error`
- Fields: `request_id`, `path`, `method`, `status_code`, `latency_ms`, `outcome`, `result_count`

## Testing (TDD)

Write tests before implementation (`tasks.md` T012–T018).

| Test | Assert |
|------|--------|
| `GET /products` no auth | `200`, body is `list` |
| Zero-quantity product | Present in array |
| `?search=widget` | Only matching rows |
| \>100 seeded rows, no `limit` | All rows returned |
| Contract | `GET /products` has `security: []` in OpenAPI alignment |

**Commands**

```bash
pytest tests/contract/test_products_contract.py tests/integration/test_products.py -k "list or search" -v
```

## Out of Scope (This Slice)

- `GET /products/{id}` (US2)
- `POST` / `PUT` / `DELETE` (US3)
- `?limit=` query param (admin list — later)
- `/api/v1/products` aliases
- `app/dependencies/auth.py` (`require_admin`)
- Order snapshots / FK delete guards

## Public Allowlist

Add to route access policy tests (when present):

- `("GET", "/products")`

## Related Artifacts

| Document | Path |
|----------|------|
| Feature spec | `specs/002-product-catalog/spec.md` |
| Implementation plan | `specs/002-product-catalog/plan.md` |
| Tasks (US1) | `specs/002-product-catalog/tasks.md` T012–T018 |
| Full catalog design | `docs/superpowers/specs/2026-05-27-product-catalog-design.md` |
| Architecture | `docs/architecture.md` |

## Approaches Considered

| # | Approach | Verdict |
|---|----------|---------|
| 1 | Thin vertical slice | **Selected** |
| 2 | SQL in router only | Rejected — blocks US2/US3 |
| 3 | Static JSON stub | Rejected — throwaway |

## Status

**Approved** — ready for implementation plan or direct execution per `specs/002-product-catalog/tasks.md` Phase 2–3.
