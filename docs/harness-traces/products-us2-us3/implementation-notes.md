# Implementation Notes (TDD)

Task: `products-us2-us3`

**Harness:** US2 (`GET /products/{product_id}`) + US3 (admin `POST` / `PUT` / `DELETE`, `GET /products?limit=100`)

**Prerequisite:** US1 `GET /products` — see `docs/harness-traces/get-products/implementation-notes.md`

## Key decisions made during test-driven development

1. **Tests first, two RED→GREEN batches**
   - Batch A (US2): 5 integration + 4 contract tests before `get_by_id` / detail route.
   - Batch B (US3): 17 integration + 7 contract tests + `conftest` auth helpers before write routes.
   - Initial RED: `404`/`405` (routes missing), `401`/`403` on writes without implementation.

2. **US2 before US3 (sequential checkpoints)**
   - Public detail shipped first so `test_get_product_after_delete_returns_404` can run after DELETE lands.
   - Foundation (`ProductWrite`, auth deps, full repo/service CRUD) implemented alongside US3 wiring.

3. **Admin auth via shared dependencies**
   - `app/dependencies/auth.py`: `extract_bearer_token`, `get_current_user`, `require_admin`.
   - Role from **DB lookup** after JWT decode (`role == "admin"`), not JWT claims alone (research R4).
   - `/auth/me` refactored to import `extract_bearer_token` from dependencies (review follow-up).

4. **Stable error `detail` strings**
   - `401` → `"Not authenticated"`
   - `403` → `"Admin access required"`
   - `404` → `"Product not found"`
   - `409` → `"SKU already exists"`

5. **`ProductWrite` + `ProductResponse`**
   - Full body required on POST/PUT; `image_url` coerced to `""`; `price` max 2 decimal places.
   - `ProductResponse` price serialized as JSON number (`field_serializer` → `float`).

6. **Repository CRUD + SKU uniqueness**
   - `create` / `update` catch `IntegrityError` → `DuplicateSkuError` → service `DuplicateSku` → router `409`.
   - `delete` hard-deletes row; `update` bumps `updated_at` explicitly.
   - `list_products` applies `LIMIT min(limit, 100)` only when `limit` query param is present (browse unchanged).

7. **Browse regression guard**
   - `test_list_products_without_limit_returns_all_when_over_100_rows` still passes when `limit` omitted.
   - Admin cap verified: `test_list_products_with_limit_100_caps_results_when_over_100_rows`.

8. **Global validation handler fix**
   - `app/main.py`: `RequestValidationError` → **422** with `jsonable_encoder(exc.errors())` (fixes `Decimal` in error ctx on product validation).
   - Auth register invalid-payload test updated to expect `422`.

9. **Admin bootstrap**
   - `app/scripts/seed_admin.py`: idempotent `admin@inventory.com`, password from `ECOM_OPPO_ADMIN_PASSWORD` (default `AdminPass123!`).
   - `tests/conftest.py`: `create_admin_user`, `create_customer_user`, `admin_auth_headers`, `customer_auth_headers`, `product_write_payload`.

10. **Structlog per endpoint family**
    - US2: `product_get_success`, `product_get_not_found`, `product_get_error`
    - US3: `product_create_*`, `product_update_*`, `product_delete_*` (success / not_found / conflict / error)

11. **Post-review harness hardening**
    - `test_get_product_by_id_is_public_allowlisted` — asserts `status not in (401, 403)` (not `404 < 401`, which is false in Python).
    - `tests/unit/test_product_service.py` — `ProductNotFound` / `DuplicateSku` mapping with mocked repository.

12. **Deferred (documented)**
    - Alembic migration (`T002`, `T005`) — still `create_all` for dev/test.
    - Repository ORM in-place field assignment on update (standard SQLAlchemy pattern; immutability refactor optional).
    - `docs/design/api-contract-draft.md` update (`T040`).

## Files touched

| File | Role |
|------|------|
| `app/dependencies/auth.py` | Bearer + `require_admin` |
| `app/schemas/product.py` | `ProductWrite`, `ProductResponse` |
| `app/repositories/product_repository.py` | `get_by_id`, `create`, `update`, `delete`, `list_products(limit)` |
| `app/services/product_service.py` | CRUD + `ProductNotFound`, `DuplicateSku` |
| `app/routers/products.py` | GET detail, POST, PUT, DELETE, list `limit` |
| `app/scripts/seed_admin.py` | Idempotent admin user |
| `app/main.py` | Validation 422 + `jsonable_encoder` |
| `app/routers/auth.py` | Shared `extract_bearer_token` |
| `tests/conftest.py` | Admin/customer fixtures |
| `tests/integration/test_products.py` | US2 + US3 integration tests (+ US1) |
| `tests/contract/test_products_contract.py` | US2 + US3 contract tests (+ US1) |
| `tests/contract/test_route_access_policy.py` | Public allowlist for list + detail |
| `tests/unit/test_product_service.py` | Service error mapping unit tests |
| `specs/002-product-catalog/quickstart.md` | `seed_admin` + login docs |

## Out of scope (documented, not implemented in this harness)

- `/api/v1/products` aliases
- Alembic revision (production migration trail)
- Global default-deny route middleware
- Order FK / delete blocking
- `PATCH` / soft delete
