# Brainstorm: POST /orders (US1 checkout slice)

## Task

Implement customer checkout as a focused vertical slice:

- **Endpoint:** `POST /orders` (bare path only — no `/api/v1` prefix)
- **Reference:** `specs/003-orders-checkout/spec.md` (User Story 1), `plan.md`, `tasks.md` (T001–T021)
- **Parent design:** `docs/superpowers/specs/2026-05-28-orders-checkout-design.md`

## Final Decisions

| Topic | Decision |
|-------|----------|
| Scope | US1 vertical: Phase 1–2 foundation + `POST /orders` only |
| Approach | 1 — `OrderService.checkout()` owns single DB transaction |
| OrderRepository | **Full upfront** (all methods); only `create_with_line_items` used in this slice |
| Auth | Bearer required; `require_customer` (`admin` → 403) |
| Response | `201` + full `Order` JSON; SPA redirect uses `data.id` |
| Snapshots | Mandatory `product_name`, `unit_price` on each `items[]` line |
| Stock | Decrement `products.quantity` atomically with order create; oversell → `409` |
| Missing product | `404` |
| Wire key | Nested **`items`** (not `line_items`) |
| `stock_restored` | DB only — never in API JSON |
| Duplicate `product_id` in POST | Merge quantities before validation |
| Deferred | `GET /orders*`, `PATCH` status (US2–US4); service methods for list/update not wired yet |

## Architecture (Approved)

```text
Client
  → POST /orders + Bearer (customer)
  → app/routers/orders.py
      Depends(require_customer)
  → app/services/order_service.py
      checkout() — merge lines, validate, snapshot, commit
  → app/repositories/order_repository.py
      create_with_line_items (flush only)
  → app/repositories/product_repository.py
      get_by_ids, adjust_quantity (flush only, no commit)
  → orders + order_line_items + products tables
```

## POST contract

### Request (`OrderCreate`)

```json
{
  "shipping_address": "42 MG Road, Bengaluru, Karnataka 560001, India",
  "items": [
    { "product_id": 1, "quantity": 2 },
    { "product_id": 3, "quantity": 1 }
  ]
}
```

| Field | Rule |
|-------|------|
| `shipping_address` | Required; strip whitespace; min length 1 after strip |
| `items` | Min 1 entry; each `quantity` ≥ 1 |

### Response (`OrderResponse`, HTTP 201)

```json
{
  "id": 10,
  "user_id": 2,
  "status": "pending",
  "total_amount": 8297.0,
  "shipping_address": "...",
  "created_at": "2026-05-27T10:15:00Z",
  "updated_at": "2026-05-27T10:15:00Z",
  "items": [
    {
      "id": 101,
      "product_id": 1,
      "product_name": "Wireless Mouse",
      "quantity": 2,
      "unit_price": 799.0
    }
  ]
}
```

`total_amount` = server-computed Σ(`quantity × unit_price`); client does not send it.

## HTTP mapping

| Condition | HTTP | `detail` example |
|-----------|------|------------------|
| Success | `201` | — |
| Validation | `422` | Pydantic array |
| Missing product | `404` | `Product 99 not found` |
| Insufficient stock | `409` | `Insufficient stock for product_id 1` |
| Admin checkout | `403` | `Customer access required` |
| No token | `401` | `Not authenticated` |

## Checkout flow (`OrderService.checkout`)

```
1. merged = merge_line_items(payload.items)
2. products = product_repo.get_by_ids(db, ids)
3. FOR each line:
     missing product → ProductNotFoundForOrderError
     insufficient stock → InsufficientStockError
     snapshot product_name, unit_price
4. total_amount = compute_total_amount(...)
5. TRY:
     order_repo.create_with_line_items(...)   # flush only
     FOR each line: product_repo.adjust_quantity(db, id, -qty)
     await db.commit()
   EXCEPT:
     await db.rollback(); raise
6. return OrderResponse (items via selectinload)
```

**Invariants:** `status=pending`, `stock_restored=false`; no `commit()` inside flush-only repo helpers.

## OrderRepository (full, upfront)

| Method | This slice | Later story |
|--------|------------|---------------|
| `create_with_line_items` | Yes | — |
| `get_by_id` | Optional refresh | US2 |
| `list_for_user` | Implement only | US2 `GET /orders/me` |
| `list_all` | Implement only | US3 admin list |
| `update_status` | Implement only | US4 PATCH + restock |

## Testing (TDD)

### Unit — `tests/unit/test_order_service.py`

- `merge_line_items` sums duplicate `product_id`
- `compute_total_amount` decimal math

### Integration — `tests/integration/test_orders.py`

| Case | Expect |
|------|--------|
| Happy checkout | `201`, snapshots, stock decremented |
| Oversell | `409`, no order, stock unchanged |
| Missing product | `404` |
| Admin POST | `403` |
| No token | `401` |
| Bad body | `422` |

### Contract — `tests/contract/test_orders_contract.py`

- `POST /orders` in `specs/003-orders-checkout/contracts/orders-api.yaml`
- `bearerAuth` required
- Response `items` includes `product_name`, `unit_price`

### Verification (GREEN)

```bash
pytest tests/contract/test_orders_contract.py \
  tests/integration/test_orders.py \
  tests/unit/test_order_service.py \
  -k "checkout or merge or total or post_orders" -v
```

## File checklist

| Action | Path |
|--------|------|
| Create | `app/models/order.py` |
| Modify | `app/database.py` |
| Create | `app/schemas/order.py` |
| Modify | `app/dependencies/auth.py` (`require_customer`) |
| Modify | `app/repositories/product_repository.py` |
| Create | `app/repositories/order_repository.py` |
| Create | `app/services/order_service.py` |
| Create | `app/routers/orders.py` |
| Modify | `app/main.py` |
| Create | `tests/integration/test_orders.py` |
| Create | `tests/unit/test_order_service.py` |
| Create | `tests/contract/test_orders_contract.py` |

## Harness artifact layout

For this and future slices, store brainstorm output here:

```text
docs/harness-traces/<task-name>/
├── brainstorm.md      # this file — decisions + contract + flow
├── plan.md            # implementation steps (optional; or use superpowers plan)
├── implementation-notes.md
└── verify-output.md
```

**Task folder:** `post-orders`

## References

- `specs/003-orders-checkout/spec.md`
- `specs/003-orders-checkout/plan.md`
- `specs/003-orders-checkout/tasks.md` (T001–T021)
- `docs/superpowers/plans/2026-05-28-orders-checkout.md`
