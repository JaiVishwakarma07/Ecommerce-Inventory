# Implementation Notes (TDD)

Task: `orders-us4`

**Harness:** US4 — admin status update (`PATCH /orders/{order_id}/status`) with cancel restock (`specs/003-orders-checkout` tasks T037–T043)

**Prerequisites:** US1 checkout, US2 customer reads, US3 admin list — `docs/harness-traces/post-orders/`, `orders-us2/`, `orders-us3/`

**Plan:** `docs/harness-traces/orders-us4/plan.md`  
**Brainstorm:** `docs/harness-traces/orders-us4/brainstorm.md`

## Key decisions made during test-driven development

1. **Tests first (RED → GREEN)**
   - Wrote 6 contract, 7 integration, and 1 route-policy test before handler.
   - Initial RED: HTTP **404** (route missing); contract tests passed in RED (OpenAPI already defined PATCH).
   - Slice verification: **14 passed** on `-k "patch_order or patch_cancel"` (exit 0).

2. **Restock rules (service)**
   - Restock when: `new_status == "cancelled"` AND `order.status != "cancelled"` AND `NOT order.stock_restored`.
   - Loop line items → `ProductRepository.adjust_quantity(+qty)`; skip missing products with `order_restock_product_missing` warning.
   - Single transaction: restock + `update_status(..., stock_restored=True)` then `commit`; rollback on any failure.
   - Idempotent second cancel: no restock (`stock_restored` already true).

3. **Deleted product test (approach A)**
   - Admin `DELETE /products/{id}` after checkout; cancel PATCH still **200**, stock unchanged for deleted SKU.

4. **Auth**
   - `require_admin` on PATCH — customer **403** `"Admin access required"`; no token **401**.

5. **Router**
   - `PATCH /orders/{order_id}/status` with `OrderStatusUpdate` body, `response_model=OrderResponse`.
   - `OrderNotFoundError` → **404**; `OrderResponse` never exposes `stock_restored`.

6. **Structlog**
   - `order_status_update_success`, `order_status_update_not_found`, `order_status_update_error`.
   - Success includes `restocked`, `old_status`, `new_status`, `order_id`, `user_id`.

7. **Service return tuple**
   - `update_status` returns `(OrderResponse, bool restocked, str old_status)` for router logging only.

## Files touched

| File | Role |
|------|------|
| `app/services/order_service.py` | `update_status` + restock loop |
| `app/routers/orders.py` | `PATCH /orders/{order_id}/status` + structlog |
| `tests/contract/test_orders_contract.py` | 6 US4 contract tests |
| `tests/integration/test_orders.py` | 7 US4 integration tests + `_patch_order_status`, `_get_product_quantity` |
| `tests/contract/test_route_access_policy.py` | `test_patch_order_status_requires_authentication` |

**Unchanged (per plan):** `app/repositories/order_repository.py` (reused `update_status`), `app/schemas/order.py`, `app/dependencies/auth.py`

## Spec coverage (US4)

| Requirement | Covered |
|-------------|---------|
| FR-011 admin status update | Yes |
| FR-012 cancel restock once | Yes |
| FR-013 skip restock for deleted products | Yes |
| FR-014 auth on orders | Yes |
| US4 scenarios 1–5 | Yes |

## Out of scope (this harness)

- Unit tests for restock idempotency (Phase 7 **T045**)
- `stock_restored` in API responses
- `/api/v1/orders` route alias

## Postman smoke

- Admin login → `PATCH /orders/{id}/status` with `{"status":"cancelled"}` → **200**, product qty restored once
- Second cancel PATCH → **200**, qty unchanged
- Customer token → **403**; unknown order → **404**
