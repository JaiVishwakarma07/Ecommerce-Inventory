# Verification Output

Task: `products-us2-us3`

## Verification command

```bash
pytest tests/integration/test_products.py \
  tests/contract/test_products_contract.py \
  tests/contract/test_route_access_policy.py \
  tests/unit/test_product_service.py \
  tests/integration/test_auth_register.py \
  tests/integration/test_auth_login.py \
  -q
```

## Test run output (latest)

```text
........................................................................ [ 98%]
.                                                                        [100%]
=============================== warnings summary ===============================
tests/integration/test_products.py::test_list_products_without_auth_returns_200_and_array
  .../passlib/utils/__init__.py:854: DeprecationWarning: 'crypt' is deprecated and slated for removal in Python 3.13

tests/integration/test_products.py::test_list_products_without_auth_returns_200_and_array
  .../app/database.py:70: DeprecationWarning:
          on_event is deprecated, use lifespan event handlers instead.

tests/integration/test_products.py::test_list_products_without_auth_returns_200_and_array
  .../fastapi/applications.py:4598: DeprecationWarning:
          on_event is deprecated, use lifespan event handlers instead.

tests/integration/test_products.py::test_list_products_without_auth_returns_200_and_array
  .../app/database.py:81: DeprecationWarning:
          on_event is deprecated, use lifespan event handlers instead.

tests/integration/test_products.py::test_get_product_by_id_non_integer_path_returns_422
tests/integration/test_products.py::test_create_product_invalid_payload_returns_422
tests/integration/test_auth_register.py::test_register_invalid_payload_returns_400
  .../starlette/_exception_handler.py:59: DeprecationWarning:
          'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
73 passed, 9 warnings in 8.13s
```

## Test inventory

| Suite | File | Count |
|-------|------|-------|
| Integration (products) | `tests/integration/test_products.py` | 34 |
| Contract (products) | `tests/contract/test_products_contract.py` | 16 |
| Route policy | `tests/contract/test_route_access_policy.py` | 2 |
| Unit (ProductService) | `tests/unit/test_product_service.py` | 5 |
| Auth regression | `tests/integration/test_auth_register.py` + `test_auth_login.py` | 16 |
| **Total (command above)** | | **73** |

### US2-focused filter

```bash
pytest tests/integration/test_products.py tests/contract/test_products_contract.py \
  -k "detail or get_by_id or get_product_by_id" -q
```

```text
9 passed (US2 integration + contract subset; full suite 73)
```

### US3-focused filter

```bash
pytest tests/integration/test_products.py -k "admin or create or update or delete or limit_100 or after_delete" -q
```

```text
17 passed (US3 integration subset)
```

## Integration regression (auth + US1 list)

```bash
pytest tests/integration/test_auth_register.py tests/integration/test_auth_login.py \
  tests/integration/test_products.py -k "list or search" -q
```

```text
13 passed (US1 list/search), 16 passed (auth) — run separately in full suite
```

Full suite: **73 passed, 0 failed** (auth + products together).

## Manual smoke (Postman / curl)

```bash
(cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000)
(cd backend && python -m app.scripts.seed_admin)
(cd backend && python -m app.scripts.seed_products)
```

| Request | Auth | Expected |
|---------|------|----------|
| `GET /products/1` | None | `200` product or `404` if missing |
| `POST /products` | Admin Bearer | `201` + product body |
| `PUT /products/1` | Admin Bearer | `200` |
| `DELETE /products/1` | Admin Bearer | `204`, empty body |
| `GET /products?limit=100` | Optional | `200`, max 100 items |
| `POST /products` (customer token) | Customer | `403` |
| `POST /products` (no token) | None | `401` |

### Admin login

```bash
curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@inventory.com","password":"AdminPass123!"}'
```

Use `access_token` as `Authorization: Bearer <token>` on write endpoints.

## Seed scripts

```bash
(cd backend && python -m app.scripts.seed_admin)
(cd backend && python -m app.scripts.seed_products)
```

## Coverage

- **Coverage %:** Not run in this verification pass
- **Optional command:** `pytest tests/integration/test_products.py tests/contract/test_products_contract.py tests/unit/test_product_service.py --cov=app --cov-report=term-missing` (requires `pytest-cov`)

## Requirements spot-check

| Requirement | Verified by |
|-------------|-------------|
| FR-005 public `GET /products/{id}` | `test_get_product_by_id_*`, contract detail tests |
| FR-006 admin writes | `test_*_requires_bearer_auth`, admin CRUD tests |
| FR-007 full body POST/PUT | `test_product_write_schema_required_fields` |
| FR-008 201 + id/timestamps | `test_create_product_as_admin_returns_201_with_id_and_timestamps` |
| FR-009 duplicate SKU 409 | `test_create_product_duplicate_sku_returns_409` |
| FR-010 hard delete 204 | `test_delete_product_as_admin_returns_204_empty_body` |
| FR-011/012 auth errors | 401/403/404/409 tests |
| FR-013 zero qty in detail | `test_get_product_by_id_includes_zero_quantity_product` |
| FR-015 `image_url` never null | create/list/detail tests |
| Admin `limit=100` | `test_list_products_with_limit_100_caps_results_when_over_100_rows` |
| US1 browse unchanged | `test_list_products_without_limit_returns_all_when_over_100_rows` |

## Status

**US2 + US3 harness slice:** verified (**73/73** tests in full command, **0 failures**).

**Production follow-ups (not blocking harness):** Alembic migration; `docs/design/api-contract-draft.md` (T040); optional coverage report (T039); manual quickstart walkthrough (T041).
