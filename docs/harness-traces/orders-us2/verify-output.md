# Verification Output

Task: `orders-us2`

**Date:** 2026-05-28  
**Branch:** `003-orders-checkout`

## Verification command (plan gate — US2)

```bash
backend/.venv/bin/pytest tests/contract/test_orders_contract.py \
  tests/integration/test_orders.py \
  tests/contract/test_route_access_policy.py \
  -k "orders_me or order_by_id or forbidden or get_orders" -v
```

## Test run output (latest)

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.7, pytest-9.0.3, pluggy-1.6.0
plugins: asyncio-1.3.0, anyio-4.13.0
collected 37 items / 19 deselected / 18 selected

tests/contract/test_orders_contract.py::test_get_orders_me_path_exists_in_contract PASSED
tests/contract/test_orders_contract.py::test_get_orders_me_requires_bearer_security PASSED
tests/contract/test_orders_contract.py::test_get_orders_me_response_schema_is_order_array PASSED
tests/contract/test_orders_contract.py::test_get_orders_by_id_path_exists_in_contract PASSED
tests/contract/test_orders_contract.py::test_get_orders_by_id_requires_bearer_security PASSED
tests/contract/test_orders_contract.py::test_get_orders_by_id_response_schema_is_order PASSED
tests/contract/test_orders_contract.py::test_get_orders_by_id_403_uses_error_detail_schema PASSED
tests/contract/test_orders_contract.py::test_get_orders_by_id_404_uses_not_found_response PASSED
tests/integration/test_orders.py::test_post_orders_merge_duplicate_product_ids_in_request PASSED
tests/integration/test_orders.py::test_get_orders_me_returns_only_own_orders PASSED
tests/integration/test_orders.py::test_get_order_by_id_returns_own_order PASSED
tests/integration/test_orders.py::test_get_order_by_id_forbidden_for_other_customer PASSED
tests/integration/test_orders.py::test_get_order_by_id_allowed_for_admin PASSED
tests/integration/test_orders.py::test_get_order_by_id_not_found PASSED
tests/integration/test_orders.py::test_get_orders_me_without_token_returns_401 PASSED
tests/integration/test_orders.py::test_get_order_by_id_without_token_returns_401 PASSED
tests/contract/test_route_access_policy.py::test_get_orders_me_requires_authentication PASSED
tests/contract/test_route_access_policy.py::test_get_order_by_id_requires_authentication PASSED

================ 18 passed, 19 deselected, 5 warnings in 2.75s =================
```

**Exit code:** `0`

## Regression (US1 + US2)

```bash
backend/.venv/bin/pytest tests/contract/test_orders_contract.py \
  tests/integration/test_orders.py \
  tests/unit/test_order_service.py \
  -k "checkout or merge or total or post_orders or orders_me or order_by_id or forbidden or get_orders" -v
```

```text
================= 32 passed, 4 deselected, 8 warnings in 4.46s =================
```

**Exit code:** `0`

## Integration-only filter (`tasks.md` T029)

```bash
backend/.venv/bin/pytest tests/integration/test_orders.py \
  -k "orders_me or order_by_id or forbidden" -v
```

**Result:** 8 passed, 9 deselected — exit code `0`

## Test inventory

| Suite | File | In US2 filter | US2-specific |
|-------|------|---------------|--------------|
| Contract | `tests/contract/test_orders_contract.py` | 8 (+1 deselected US1) | 8 GET tests |
| Integration | `tests/integration/test_orders.py` | 8 (+1 deselected US1) | 7 GET tests |
| Route policy | `tests/contract/test_route_access_policy.py` | 2 | 2 GET auth tests |
| **Total (US2 plan filter)** | | **18** | |

Note: `-k` filter also selects `test_post_orders_merge_duplicate_product_ids_in_request` (matches `order_by_id` substring). Harmless; still passes.

## Warnings (non-blocking)

- `passlib` / `crypt` deprecation (Python 3.13)
- FastAPI `@app.on_event` startup/shutdown deprecation
- Starlette `HTTP_422_UNPROCESSABLE_ENTITY` deprecation (US1 validation tests)

## Checkpoint

US1 + US2: checkout and customer order visibility verified. US3/US4 not run.
