# Brainstorm: US4 — Admin updates order status

## Task

Wire admin status updates and cancel restock (Phase 6 / tasks T037–T043):

- **Endpoint:** `PATCH /orders/{order_id}/status` with `{ "status": "<enum>" }`
- **Reference:** `specs/003-orders-checkout/spec.md` (US4), `plan.md`, `tasks.md`
- **Prerequisite:** US1–US3 — `docs/harness-traces/post-orders/`, `orders-us2/`, `orders-us3/`
- **Parent design:** `docs/superpowers/specs/2026-05-28-orders-checkout-design.md`

## Decisions

| Topic | Decision |
|-------|----------|
| Harness path | `docs/harness-traces/orders-us4/` |
| Approach | **1** — `OrderService.update_status` + transaction owner; existing repos |
| Auth | `require_admin` on PATCH |
| Restock gate | `new_status == "cancelled"` AND `order.status != "cancelled"` AND `NOT order.stock_restored` |
| Free transitions | Any allowed status → any allowed status; no transition matrix |
| Same-status PATCH | **200**; no restock (e.g. `pending` → `pending`, `cancelled` → `cancelled`) |
| Deleted product on restock | `get_by_id` → skip line; structlog warning; PATCH **200** (approach **A**: admin `DELETE /products/{id}` in test) |
| Transaction | Service `commit` / `rollback`; repos flush only |
| `stock_restored` | Set `true` after first successful restock; never in API JSON |
| Unit tests | Deferred to Phase 7 **T045** (integration + contract in US4 slice) |
| Deferred | Reverse inventory on `cancelled` → non-cancel; `/api/v1` alias |

## Restock rules

```text
should_restock =
  new_status == "cancelled"
  AND order.status != "cancelled"
  AND NOT order.stock_restored
```

For each line when `should_restock`:
- `product = await get_by_id(product_id)`
- If product: `adjust_quantity(db, product_id, +line.quantity)`
- Else: log `order_restock_product_missing`, continue

Then `update_status(..., stock_restored=True)` if restocked, else status only.

## Architecture

```text
PATCH /orders/{order_id}/status
  → require_admin
  → OrderService.update_status(order_id, status)
  → OrderRepository.get_by_id
  → [restock loop if should_restock]
  → OrderRepository.update_status
  → commit
  → OrderResponse
```

## API contract

### `PATCH /orders/{order_id}/status`

- **Auth:** Bearer; admin only → **403** `"Admin access required"`
- **Body:** `OrderStatusUpdate` — `{ "status": "<enum>" }`
- **200:** Full `Order` with updated `status`, `updated_at`, nested `items`
- **404:** Order missing
- **422:** Invalid `status` in body

## Service signature

```python
async def update_status(
    self,
    db: AsyncSession,
    *,
    order_id: int,
    status: str,
) -> OrderResponse:
    """Load order; optional restock; update status; commit; return OrderResponse."""
```

## Router signature

```python
@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
async def patch_order_status(
    request: Request,
    order_id: int,
    payload: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: OrderService = Depends(get_order_service),
    _admin: RegisterUserResponse = Depends(require_admin),
) -> OrderResponse: ...
```

Structlog: `order_status_update_success` (include `restocked: bool`, `old_status`, `new_status`); `order_status_update_not_found`; `order_status_update_error`; warning `order_restock_product_missing`.

## Testing

| Test | Asserts |
|------|---------|
| `test_patch_order_status_returns_200_with_updated_order` | PATCH `processing` → **200**, new status |
| `test_patch_cancel_restock_once` | checkout reduces stock; cancel restores |
| `test_patch_cancel_idempotent_no_double_restock` | second `cancelled` PATCH → stock unchanged |
| `test_patch_cancel_skips_restock_when_product_deleted` | 2-line order; DELETE one product; cancel → **200**, surviving product restocked |
| `test_patch_order_status_as_customer_returns_403` | |
| `test_patch_order_status_not_found` | **404** |
| `test_patch_order_status_without_token_returns_401` | |

Contract: PATCH path, bearer, request/response schemas, error responses.

**Filter:** `-k "patch_status or cancel or restock"`

## Spec coverage (US4)

| Requirement | Covered |
|-------------|---------|
| FR-011 PATCH admin | Yes |
| FR-012 free transitions | Yes |
| FR-013 restock once | Yes |
| FR-014 auth | Yes |
| US4 scenarios 1–6 | Yes |

## Out of scope

- Unit restock idempotency (**T045**)
- Inventory change on non-cancel transitions (except first cancel restock)
- Customer-initiated cancel
- Rate limiting

## Next step

Implementation plan: `docs/harness-traces/orders-us4/plan.md` (TDD, signatures + test names only).
