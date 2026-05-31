# Implementation Notes (TDD)

Task: `get-products`

## Key decisions made during test-driven development

1. **Tests first, endpoint behavior only**
   - Wrote integration and contract tests for `GET /products` before any product modules existed.
   - Initial RED: `404` (route missing) and `ModuleNotFoundError` for `app.models.product` in seed helpers.

2. **Thin vertical slice over monolithic router**
   - Implemented `Product` ORM → `ProductRepository` → `ProductService` → `products` router to match auth layering and future US2/US3 work.

3. **Bare `/products` path only**
   - Mounted router in `app/main.py` with no prefix (no `/api/v1/products`) per approved brainstorm and frontend `VITE_API_URL` usage.

4. **Plain `Product[]` response**
   - `response_model=list[ProductResponse]` returns a JSON array with no pagination envelope.

5. **Browse list has no SQL `LIMIT`**
   - `list_products` applies `LIMIT` only when a `limit` query param is passed (deferred for admin slice).
   - Browse calls omit `limit`; repository returns all matching rows (verified with 101+ row test).

6. **Search via parameterized SQLAlchemy**
   - Optional `?search=` trims whitespace; empty/whitespace-only → no filter.
   - Case-insensitive partial match on `name`, `sku`, `category` using `func.lower(...) LIKE '%term%'`.

7. **`image_url` never null in API**
   - ORM column `NOT NULL` with default `""`.
   - Pydantic `ProductResponse` coerces `None` → `""` before serialization.

8. **Price as JSON number**
   - Stored as `Numeric(10, 2)`; serialized with Pydantic `field_serializer` to `float` for frontend `formatINR`.

9. **Schema bootstrap via `create_all`**
   - Registered `Product` model import in `app/database.py` so in-memory/file SQLite tests and dev use `Base.metadata.create_all`.
   - Alembic migration deferred to full `002-product-catalog` track (see code review triage).

10. **Dependency-injected service/repository**
    - `get_product_repository` / `get_product_service` providers on the router (request-safe, matches auth pattern).

11. **Structlog on list endpoint**
    - `product_list_success` on happy path; `product_list_error` uses `logger.exception` after review hardening (path A).

12. **Dev seed for manual testing**
    - `app/scripts/seed_products.py` inserts WGT-001, GAD-002, OUT-003 idempotently by SKU.
    - Includes `quantity: 0` row for out-of-stock UI check.

13. **Test helpers colocated in integration file**
    - `insert_product` / `insert_products_bulk` live in `tests/integration/test_products.py` (plan allowed conftest later).
    - Tests share app DB session via `get_db_session()` and in-memory SQLite `StaticPool`.

14. **Contract tests against YAML artifact**
    - `tests/contract/test_products_contract.py` validates `specs/002-product-catalog/contracts/products-api.yaml` (public `security: []`, array response, required fields).

15. **Post-review harness hardening (path A)**
    - Error path: `logger.info` → `logger.exception` in `app/routers/products.py`.
    - `seed_products(session: AsyncSession)` type hint added.

## Files touched

| File | Role |
|------|------|
| `app/models/product.py` | `products` table ORM |
| `app/schemas/product.py` | `ProductResponse` |
| `app/repositories/product_repository.py` | `list_products(search)` |
| `app/services/product_service.py` | ORM → response mapping |
| `app/routers/products.py` | `GET /products` |
| `app/scripts/seed_products.py` | Idempotent dev seed |
| `app/main.py` | Include products router |
| `app/database.py` | Import Product for `create_all` |
| `tests/integration/test_products.py` | 12 integration tests |
| `tests/contract/test_products_contract.py` | 5 contract tests |
| `tests/contract/test_route_access_policy.py` | Public allowlist check |

## Out of scope (documented, not implemented)

- `GET /products/{id}` (US2)
- Admin `POST` / `PUT` / `DELETE` (US3)
- `?limit=` on browse (admin list only, later)
- `/api/v1/products` aliases
- Alembic revision (follow-up on `002-product-catalog`)
- Global default-deny route middleware allowlist (auth policy follow-up)
