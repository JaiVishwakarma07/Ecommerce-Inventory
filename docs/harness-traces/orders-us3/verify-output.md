# Verification Output

Task: `orders-us3`

**Date:** 2026-05-28  
**Branch:** `003-orders-checkout`

## Verification command (plan gate — US3)

Use `-k get_orders_admin` (test names use `get_orders_admin`, not `admin_list`):

```bash
backend/.venv/bin/pytest tests/contract/test_orders_contract.py \
  tests/integration/test_orders.py \
  tests/contract/test_route_access_policy.py \
  -k "get_orders_admin" -v
```

## Test run output (latest)

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.7, pytest-9.0.3, pluggy-1.6.0
plugins: asyncio-1.3.0, anyio-4.13.0
collected 51 items / 37 deselected / 14 selected

tests/contract/test_orders_contract.py::test_get_orders_admin_path_exists_in_contract PASSED
tests/contract/test_orders_contract.py::test_get_orders_admin_requires_bearer_security PASSED
tests/contract/test_orders_contract.py::test_get_orders_admin_has_status_query_param PASSED
tests/contract/test_orders_contract.py::test_get_orders_admin_has_limit_query_param PASSED
tests/contract/test_orders_contract.py::test_get_orders_admin_response_schema_is_order_array PASSED
tests/contract/test_orders_contract.py::test_get_orders_admin_403_uses_forbidden_response PASSED
tests/integration/test_orders.py::test_get_orders_admin_returns_all_orders_newest_first PASSED
tests/integration/test_orders.py::test_get_orders_admin_filters_by_status PASSED
tests/integration/test_orders.py::test_get_orders_admin_respects_limit PASSED
tests/integration/test_orders.py::test_get_orders_admin_limit_over_100_capped PASSED
tests/integration/test_orders.py::test_get_orders_admin_as_customer_returns_403 PASSED
tests/integration/test_orders.py::test_get_orders_admin_invalid_status_returns_422 PASSED
tests/integration/test_orders.py::test_get_orders_admin_without_token_returns_401 PASSED
tests/contract/test_route_access_policy.py::test_get_orders_admin_requires_authentication PASSED

================ 14 passed, 37 deselected, 6 warnings in 2.99s =================
```

**Exit code:** `0`

## Regression (US1 + US2 + US3)

```bash
backend/.venv/bin/pytest tests/contract/test_orders_contract.py \
  tests/integration/test_orders.py \
  tests/unit/test_order_service.py \
  -k "checkout or merge or total or post_orders or orders_me or order_by_id or forbidden or get_orders_admin" -v
```

```text
================= 40 passed, 9 deselected, 9 warnings in 6.84s =================
```

**Exit code:** `0`

## Integration-only (US3 behavior)

```bash
backend/.venv/bin/pytest tests/integration/test_orders.py -k "get_orders_admin" -v
```

**Result:** 7 passed — exit code `0`

## Test inventory

| Suite | File | US3 tests |
|-------|------|-----------|
| Contract | `tests/contract/test_orders_contract.py` | 6 |
| Integration | `tests/integration/test_orders.py` | 7 |
| Route policy | `tests/contract/test_route_access_policy.py` | 1 |
| **Total** | | **14** |

## Warnings (non-blocking)

- `passlib` / `crypt` deprecation (Python 3.13)
- FastAPI `@app.on_event` startup/shutdown deprecation
- Starlette `HTTP_422_UNPROCESSABLE_ENTITY` deprecation (validation tests)

## Manual smoke (Postman / curl)

```bash
(cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000)
```

```bash
# Admin login
curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@inventory.com","password":"AdminPass123!"}'

export ADMIN_TOKEN="<access_token>"

curl -s http://127.0.0.1:8000/orders \
  -H "Authorization: Bearer $ADMIN_TOKEN"

curl -s "http://127.0.0.1:8000/orders?status=pending&limit=50" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

| Request | Expected |
|---------|----------|
| Admin `GET /orders` | **200** `Order[]` |
| `?status=invalid` | **422** |
| Customer token | **403** |
| No token | **401** |

## Checkpoint

US1 + US2 + US3: checkout, customer reads, and admin list/filter verified. US4 (`PATCH` status) not run.
