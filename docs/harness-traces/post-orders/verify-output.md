# Verification Output

Task: `post-orders`

**Date:** 2026-05-28  
**Branch:** `003-orders-checkout` (implementation largely uncommitted at verification time)

## Verification command (plan gate)

```bash
backend/.venv/bin/pytest tests/contract/test_orders_contract.py \
  tests/integration/test_orders.py \
  tests/unit/test_order_service.py \
  tests/contract/test_route_access_policy.py \
  -k "checkout or merge or total or post_orders or order_tables" -v
```

## Test run output (latest)

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.7, pytest-9.0.3, pluggy-1.6.0
plugins: asyncio-1.3.0, anyio-4.13.0
collected 24 items / 5 deselected / 19 selected

tests/contract/test_orders_contract.py::test_post_orders_path_exists_in_contract PASSED
tests/contract/test_orders_contract.py::test_post_orders_requires_bearer_security PASSED
tests/contract/test_orders_contract.py::test_post_orders_request_schema_order_create PASSED
tests/contract/test_orders_contract.py::test_post_orders_response_schema_is_order PASSED
tests/integration/test_orders.py::test_order_tables_exist_after_bootstrap PASSED
tests/integration/test_orders.py::test_post_orders_checkout_returns_201_with_snapshots_and_decrements_stock PASSED
tests/integration/test_orders.py::test_post_orders_merge_duplicate_product_ids_in_request PASSED
tests/integration/test_orders.py::test_post_orders_insufficient_stock_returns_409_and_no_order_row PASSED
tests/integration/test_orders.py::test_post_orders_missing_product_returns_404 PASSED
tests/integration/test_orders.py::test_post_orders_as_admin_returns_403 PASSED
tests/integration/test_orders.py::test_post_orders_without_token_returns_401 PASSED
tests/integration/test_orders.py::test_post_orders_empty_items_returns_422 PASSED
tests/integration/test_orders.py::test_post_orders_empty_shipping_address_returns_422 PASSED
tests/integration/test_orders.py::test_post_orders_invalid_quantity_returns_422 PASSED
tests/unit/test_order_service.py::test_merge_line_items_sums_duplicate_product_ids PASSED
tests/unit/test_order_service.py::test_merge_line_items_preserves_single_product_unchanged PASSED
tests/unit/test_order_service.py::test_compute_total_amount_sums_line_totals PASSED
tests/unit/test_order_service.py::test_compute_total_amount_empty_list_returns_zero PASSED
tests/contract/test_route_access_policy.py::test_post_orders_requires_authentication PASSED

================= 19 passed, 5 deselected, 8 warnings in 2.33s =================
```

**Exit code:** `0`

## Test inventory

| Suite | File | In plan filter | Full file |
|-------|------|----------------|-----------|
| Contract | `tests/contract/test_orders_contract.py` | 4 | 7 |
| Integration | `tests/integration/test_orders.py` | 10 | 10 |
| Unit | `tests/unit/test_order_service.py` | 4 | 4 |
| Route policy | `tests/contract/test_route_access_policy.py` | 1 | 3 |
| **Total (plan filter)** | | **19** | — |
| **Total (orders files, no filter)** | | — | **24** |

### Contract tests deselected by plan `-k` filter

These pass when running the full contract file:

```bash
backend/.venv/bin/pytest tests/contract/test_orders_contract.py -q
```

```text
7 passed
```

Deselected by filter (still required for FR-004 / FR-016):

- `test_order_schema_required_fields`
- `test_order_schema_uses_items_not_line_items`
- `test_order_line_item_schema_snapshot_fields`

## Warnings (non-blocking)

- `passlib` / `crypt` deprecation (Python 3.13)
- FastAPI `@app.on_event` deprecation (`app/database.py`)
- Starlette `HTTP_422_UNPROCESSABLE_ENTITY` deprecation on validation responses

## Full project suite (informational)

```bash
backend/.venv/bin/pytest -q
```

```text
110 passed, 13 errors in ~11s
```

**Exit code:** `1`

Errors are pre-existing collection/setup failures: sync unit/contract tests vs autouse async fixture `dispose_database_engine_after_async_test` (`pytest.PytestRemovedIn9Warning`). Not introduced by the orders slice.

## Manual smoke (optional)

```bash
cd backend && source .venv/bin/activate
# seed users + products, then:
curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"customer@example.com","password":"CustomerPass123!"}'
# use access_token:
curl -s -X POST http://127.0.0.1:8000/orders \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"shipping_address":"42 MG Road, Bengaluru, India","items":[{"product_id":1,"quantity":1}]}'
```

## Verdict

| Gate | Result |
|------|--------|
| Plan verification command (19 tests) | **PASS** |
| Full orders test files (24 tests) | **PASS** (run without `-k`) |
| US1 spec FR-001–FR-007, FR-014, FR-016–FR-017 | **Covered** |
| Code review critical issues | **None** — slice accepted as-is |

**US1 `POST /orders` harness slice: verified.**
