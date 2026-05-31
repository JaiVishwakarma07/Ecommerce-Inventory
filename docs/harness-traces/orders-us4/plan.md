# US4 — Admin Order Status PATCH Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver admin `PATCH /orders/{order_id}/status` with free transitions, one-time cancel restock (`stock_restored` gate), idempotent re-cancel, and skip restock for deleted catalog products.

**Architecture:** `require_admin` → `OrderService.update_status` → `get_by_id`, optional restock via `adjust_quantity(+qty)`, `update_status` on repo, single `commit`. Deleted products skipped with structlog warning (PATCH still **200**).

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Pydantic v2, pytest + httpx AsyncClient, structlog

**Scope source:** `docs/harness-traces/orders-us4/brainstorm.md`, `specs/003-orders-checkout/spec.md` (US4), tasks T037–T043

**Prerequisite:** US1–US3 complete — `docs/harness-traces/post-orders/`, `orders-us2/`, `orders-us3/`

---

> This document defines **signatures and test names only** — no implementation bodies.

## File Map

| File | Role |
|------|------|
| `app/services/order_service.py` | `update_status` + restock logic + transaction |
| `app/routers/orders.py` | `PATCH /orders/{order_id}/status` + structlog |
| `tests/contract/test_orders_contract.py` | US4 OpenAPI tests |
| `tests/integration/test_orders.py` | US4 HTTP flows + `_patch_order_status` helper |
| `tests/contract/test_route_access_policy.py` | `test_patch_order_status_requires_authentication` |

**Unchanged:** `app/repositories/order_repository.py`, `app/repositories/product_repository.py`, `app/schemas/order.py` (`OrderStatusUpdate` exists), `app/models/order.py`

---

## Route registration order

Final order in `app/routers/orders.py`:

1. `POST /orders`
2. `GET /orders/me`
3. `GET /orders/{order_id}`
4. `GET /orders`
5. **`PATCH /orders/{order_id}/status`** ← **new**

---

## Restock algorithm (service)

```python
should_restock = (
    status == "cancelled"
    and order.status != "cancelled"
    and not order.stock_restored
)

if should_restock:
    for line in order.line_items:
        product = await self._products.get_by_id(db, line.product_id)
        if product is None:
            logger.warning("order_restock_product_missing", ...)
            continue
        await self._products.adjust_quantity(db, line.product_id, line.quantity)
    await self._orders.update_status(
        db, order, status=status, stock_restored=True
    )
else:
    await self._orders.update_status(db, order, status=status)

await db.commit()
# reload order with line_items → return _to_response(reloaded)
```

On exception: `await db.rollback()` then re-raise.

---

## Service layer signature

```python
# app/services/order_service.py

async def update_status(
    self,
    db: AsyncSession,
    *,
    order_id: int,
    status: str,
) -> OrderResponse:
    """
    order = await self._orders.get_by_id(db, order_id)
    if order is None: raise OrderNotFoundError()
    old_status = order.status
    # restock branch per algorithm above
    # commit; reload; return _to_response(reloaded)
    Does not expose stock_restored in response.
    """
```

---

## Router signature

```python
# app/routers/orders.py

from app.dependencies.auth import require_admin
from app.schemas.order import OrderStatusUpdate

@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
async def patch_order_status(
    request: Request,
    order_id: int,
    payload: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: OrderService = Depends(get_order_service),
    admin_user: RegisterUserResponse = Depends(require_admin),
) -> OrderResponse:
    """
    order = await service.update_status(db, order_id=order_id, status=payload.status)
    Map OrderNotFoundError → 404
    Log order_status_update_success | order_status_update_not_found | order_status_update_error
    Include: restocked (bool), old_status, new_status, order_id, user_id, latency_ms
    """
```

---

## Integration test helpers

```python
# tests/integration/test_orders.py

async def _patch_order_status(
    client: AsyncClient,
    headers: dict[str, str],
    order_id: int,
    status: str,
) -> httpx.Response:
    return await client.patch(
        f"/orders/{order_id}/status",
        json={"status": status},
        headers=headers,
    )
```

Reuse: `_checkout_order`, `insert_product`, `admin_auth_headers`, `customer_auth_headers`.

**Deleted-product test:** After checkout with two products, `DELETE /products/{deleted_id}` with `admin_auth_headers` before PATCH `cancelled`.

---

## Exact test case names and assertions

### Contract tests (`tests/contract/test_orders_contract.py`)

- `test_patch_order_status_path_exists_in_contract`
  - asserts `paths["/orders/{order_id}/status"]["patch"]` exists
- `test_patch_order_status_requires_bearer_security`
  - bearerAuth on PATCH operation
- `test_patch_order_status_request_schema_is_order_status_update`
  - body `$ref` → `#/components/schemas/OrderStatusUpdate`
- `test_patch_order_status_response_schema_is_order`
  - `200` → `#/components/schemas/Order`
- `test_patch_order_status_403_uses_forbidden_response`
- `test_patch_order_status_404_uses_not_found_response`

### Integration tests (`tests/integration/test_orders.py`)

- `test_patch_order_status_returns_200_with_updated_order`
  - checkout → PATCH `processing` → **200**; `status == "processing"`; `"updated_at"` present
- `test_patch_cancel_restock_once`
  - product `quantity=10` → checkout `quantity=2` → stock **8** → PATCH `cancelled` → stock **10**
- `test_patch_cancel_idempotent_no_double_restock`
  - after cancel restock → PATCH `cancelled` again → stock still **10** (not 12)
- `test_patch_cancel_skips_restock_when_product_deleted`
  - two products in one order → admin DELETE one product → PATCH `cancelled` → **200**; surviving product qty restored; deleted product line skipped
- `test_patch_order_status_as_customer_returns_403`
- `test_patch_order_status_not_found`
  - `PATCH /orders/999999/status` → **404**, `"detail"` present
- `test_patch_order_status_without_token_returns_401`

### Route access policy

- `test_patch_order_status_requires_authentication`
  - no token → **401**

---

## Spec coverage map (US4)

| Requirement | Test(s) |
|-------------|---------|
| FR-011 PATCH admin | `test_patch_order_status_*` |
| FR-012 free transitions | `test_patch_order_status_returns_200_with_updated_order` |
| FR-013 restock once | `test_patch_cancel_restock_once`, `test_patch_cancel_idempotent_*` |
| FR-014 auth | 401/403 + contract bearer |
| US4 scenario 4 deleted product | `test_patch_cancel_skips_restock_when_product_deleted` |
| Edge: same status | covered by idempotent cancel test |

---

## Task alignment (`tasks.md`)

| Task | Plan section |
|------|----------------|
| T037 | Contract tests |
| T038 | Integration tests + helper |
| T039 | Run RED |
| T040 | `update_status` service |
| T041 | Router PATCH |
| T042 | structlog |
| T043 | Run GREEN |

---

## Verification commands

**US4-only:**

```bash
backend/.venv/bin/pytest tests/contract/test_orders_contract.py \
  tests/integration/test_orders.py \
  tests/contract/test_route_access_policy.py \
  -k "patch_order or patch_cancel" -v
```

**Full orders regression (US1–US4):**

```bash
backend/.venv/bin/pytest tests/contract/test_orders_contract.py \
  tests/integration/test_orders.py \
  tests/unit/test_order_service.py \
  -k "checkout or merge or total or post_orders or orders_me or order_by_id or forbidden or get_orders_admin or patch_order or patch_cancel" -v
```

---

## Self-review

- **Placeholder scan:** None.
- **Consistency:** Matches `brainstorm.md`, `spec.md` US4, `orders-api.yaml`, `research.md` R4/R5.
- **Scope:** PATCH + restock only; unit tests remain T045.
- **Ambiguity:** Restock only on first transition **to** `cancelled`, not when already cancelled.

---

## Execution handoff

Plan saved to `docs/harness-traces/orders-us4/plan.md`.

**Next:** TDD — write failing tests (T037–T039), then implement T040–T042, verify T043.
