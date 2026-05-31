# Verification Output

Task: `orders-us4`

**Date:** 2026-05-28  
**Branch:** `003-orders-checkout`

## Verification command (plan gate — US4)

Use `-k "patch_order or patch_cancel"` (test names use `patch_order_*` / `patch_cancel_*`, not `patch_status`):

```bash
backend/.venv/bin/pytest tests/contract/test_orders_contract.py \
  tests/integration/test_orders.py \
  tests/contract/test_route_access_policy.py \
  -k "patch_order or patch_cancel" -v
```

## Test run output (latest)

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.7, pytest-9.0.3, pluggy-1.6.0
collected 65 items / 51 deselected / 14 selected

tests/contract/test_orders_contract.py::test_patch_order_status_path_exists_in_contract PASSED
tests/contract/test_orders_contract.py::test_patch_order_status_requires_bearer_security PASSED
tests/contract/test_orders_contract.py::test_patch_order_status_request_schema_is_order_status_update PASSED
tests/contract/test_orders_contract.py::test_patch_order_status_response_schema_is_order PASSED
tests/contract/test_orders_contract.py::test_patch_order_status_403_uses_forbidden_response PASSED
tests/contract/test_orders_contract.py::test_patch_order_status_404_uses_not_found_response PASSED
tests/integration/test_orders.py::test_patch_order_status_returns_200_with_updated_order PASSED
tests/integration/test_orders.py::test_patch_cancel_restock_once PASSED
tests/integration/test_orders.py::test_patch_cancel_idempotent_no_double_restock PASSED
tests/integration/test_orders.py::test_patch_cancel_skips_restock_when_product_deleted PASSED
tests/integration/test_orders.py::test_patch_order_status_as_customer_returns_403 PASSED
tests/integration/test_orders.py::test_patch_order_status_not_found PASSED
tests/integration/test_orders.py::test_patch_order_status_without_token_returns_401 PASSED
tests/contract/test_route_access_policy.py::test_patch_order_status_requires_authentication PASSED

================ 14 passed, 51 deselected, 5 warnings in 2.86s =================
```

**Exit code:** `0`

## Regression (US1 + US2 + US3 + US4)

```bash
backend/.venv/bin/pytest tests/contract/test_orders_contract.py \
  tests/integration/test_orders.py \
  tests/unit/test_order_service.py \
  tests/contract/test_route_access_policy.py \
  -k "checkout or merge or total or post_orders or orders_me or order_by_id or forbidden or get_orders_admin or patch_order or patch_cancel" -v
```

```text
================= 58 passed, 11 deselected, 9 warnings in 9.47s =================
```

**Exit code:** `0`
