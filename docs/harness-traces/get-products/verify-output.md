# Verification Output

Task: `get-products`

## Verification command

```bash
pytest tests/integration/test_products.py tests/contract/test_products_contract.py tests/contract/test_route_access_policy.py -q
```

## Test run output (latest)

```text
..................                                                       [100%]
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

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
18 passed, 5 warnings in 0.73s
```

## Test inventory

| Suite | File | Count |
|-------|------|-------|
| Integration | `tests/integration/test_products.py` | 12 |
| Contract | `tests/contract/test_products_contract.py` | 5 |
| Route policy | `tests/contract/test_route_access_policy.py` | 1 |
| **Total** | | **18** |

## Integration regression (related)

```bash
pytest tests/integration/ -q
```

```text
39 passed, 9 warnings in 4.10s
```

Auth + product integration tests pass together (exit code 0).

## Manual smoke (Postman / curl)

```bash
(cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000)
(cd backend && (cd backend && python -m app.scripts.seed_products))
```

| Request | Expected |
|---------|----------|
| `GET http://127.0.0.1:8000/products` | `200`, JSON array |
| `GET http://127.0.0.1:8000/products?search=widget` | `200`, filtered array |
| OpenAPI | `http://127.0.0.1:8000/docs` → **products** tag |

No `Authorization` header required for `GET /products`.

## Seed script check

```bash
(cd backend && python -m app.scripts.seed_products)
```

```text
Seeded N product(s). GET http://127.0.0.1:8000/products
```

(`N` is 3 on empty DB, `0` when SKUs already exist — idempotent.)

## Coverage

- **Coverage %:** Not available in current environment (N/A)
- **Reason:** `pytest-cov` / `coverage.py` not installed (`pytest: error: unrecognized arguments: --cov=app`)
- **Attempted command:**
  - `pytest ... --cov=app --cov-report=term-missing` (failed: unrecognized `--cov` args)

## Requirements spot-check (US1)

| Requirement | Verified by |
|-------------|-------------|
| `GET /products` public, plain array | `test_list_products_without_auth_returns_200_and_array` |
| Optional `?search=` | `test_list_products_search_matches_*` |
| No browse cap | `test_list_products_without_limit_returns_all_when_over_100_rows` |
| `quantity === 0` listed | `test_list_products_includes_zero_quantity_item` |
| `image_url` never null | `test_list_products_image_url_never_null` |
| Contract public + shape | `test_get_products_has_no_security_requirement`, schema tests |

## Status

**US1 harness slice:** verified (18/18 product tests, 0 failures).

**Production follow-ups (not blocking harness):** Alembic migration for `products` table; global route allowlist middleware when auth policy lands.
