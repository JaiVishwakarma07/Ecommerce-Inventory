# US3 — Admin Order List Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver admin `GET /orders` with optional `?status=` exact filter and `?limit=` capped at 100, `403` for non-admin, `422` for invalid query params.

**Architecture:** Add `GET /orders` handler with `require_admin` → `OrderService.list_admin` → existing `OrderRepository.list_all`. No repository changes. Invalid `status` via FastAPI `OrderStatus` query type; limit cap in repository via `min(limit, 100)`.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Pydantic v2, pytest + httpx AsyncClient, structlog

**Scope source:** `docs/harness-traces/orders-us3/brainstorm.md`, `specs/003-orders-checkout/spec.md` (US3), tasks T030–T036

**Prerequisite:** US1 + US2 complete — `docs/harness-traces/post-orders/`, `docs/harness-traces/orders-us2/`

---

> This document defines **signatures and test names only** — no implementation bodies.

## File Map

| File | Role |
|------|------|
| `app/services/order_service.py` | Add `list_admin` |
| `app/routers/orders.py` | `GET /orders` + `require_admin` + structlog |
| `tests/contract/test_orders_contract.py` | US3 OpenAPI tests |
| `tests/integration/test_orders.py` | US3 HTTP flows + `set_order_status` helper |
| `tests/contract/test_route_access_policy.py` | `test_get_orders_admin_requires_authentication` |

**Unchanged:** `app/repositories/order_repository.py`, `app/models/order.py`, `app/schemas/order.py`, `app/dependencies/auth.py`

---

## Route registration order

In `app/routers/orders.py`, final order:

1. `POST /orders` (existing)
2. `GET /orders/me` (existing)
3. `GET /orders/{order_id}` (existing)
4. **`GET /orders`** ← **new** (admin list; same path as POST, different HTTP method)
5. (US4 later) `PATCH /orders/{order_id}/status`

---

## Service layer signature

```python
# app/services/order_service.py

async def list_admin(
    self,
    db: AsyncSession,
    *,
    status: str | None = None,
    limit: int | None = None,
) -> list[OrderResponse]:
    """
    orders = await self._orders.list_all(db, status=status, limit=limit)
    return [self._to_response(o) for o in orders]
  Does not commit.
    """
```

---

## Router signature

```python
# app/routers/orders.py

from fastapi import Query
from app.dependencies.auth import require_admin
from app.schemas.order import OrderStatus

@router.get("/orders", response_model=list[OrderResponse])
async def list_orders_admin(
    request: Request,
    status: OrderStatus | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db_session_with_request),
    service: OrderService = Depends(get_order_service),
    _admin: RegisterUserResponse = Depends(require_admin),
) -> list[OrderResponse]:
    """
    orders = await service.list_admin(db, status=status, limit=limit)
    Log order_admin_list_success | order_admin_list_error
    Fields: request_id, path, method, status_code, latency_ms, outcome,
            user_id, result_count, status_filter=status, limit=limit
    """
```

**Note:** Do **not** set `le=100` on `limit` Query — spec requires `?limit=200` to be processed and capped in repository.

---

## Integration test helper

```python
# tests/integration/test_orders.py

async def set_order_status(
    db_session: AsyncSession,
    order_id: int,
    status: str,
) -> None:
    """Load Order by id, set status, flush. Test-only setup."""
```

Reuse `_checkout_order()` from US2 tests where needed.

---

## Exact test case names and assertions

### Contract tests (`tests/contract/test_orders_contract.py`)

- `test_get_orders_admin_path_exists_in_contract`
  - asserts `paths["/orders"]["get"]` exists
- `test_get_orders_admin_requires_bearer_security`
  - asserts operation declares/inherits `bearerAuth`
- `test_get_orders_admin_has_status_query_param`
  - asserts `status` parameter references `OrderStatus`
- `test_get_orders_admin_has_limit_query_param`
  - asserts `limit` integer parameter with `minimum: 1` (and `maximum: 100` in OpenAPI schema)
- `test_get_orders_admin_response_schema_is_order_array`
  - asserts `200` response is array of `#/components/schemas/Order`
- `test_get_orders_admin_403_uses_forbidden_response`
  - asserts `403` `$ref` is `#/components/responses/Forbidden` or inline `ErrorDetail`

### Integration tests (`tests/integration/test_orders.py`)

- `test_get_orders_admin_returns_all_orders_newest_first`
  - two checkouts (same or different customers) → admin `GET /orders` → `200`, `len >= 2`
  - assert `created_at[0] >= created_at[1]` (newest first)
- `test_get_orders_admin_filters_by_status`
  - two orders; `set_order_status` one to `shipped` → `?status=shipped` → `200`, all returned have `status == "shipped"`, count 1
- `test_get_orders_admin_respects_limit`
  - three orders → `?limit=2` → `200`, `len == 2`
- `test_get_orders_admin_limit_over_100_capped`
  - seed >100 orders (loop checkout acceptable) → `?limit=200` → `200`, `len == 100`
- `test_get_orders_admin_as_customer_returns_403`
  - customer token → `GET /orders` → `403`, `"detail"` present
- `test_get_orders_admin_invalid_status_returns_422`
  - `?status=invalid` → `422`
- `test_get_orders_admin_without_token_returns_401`

### Route access policy (`tests/contract/test_route_access_policy.py`)

- `test_get_orders_admin_requires_authentication`
  - no header → `GET /orders` → `401`

---

## Spec coverage map (US3)

| Requirement | Test(s) |
|-------------|---------|
| FR-010 `GET /orders` admin list/filter/limit | `test_get_orders_admin_*` |
| FR-014 auth | `*_without_token_returns_401`, `*_as_customer_returns_403`, contract bearer |
| US3 scenario 1 (list all) | `test_get_orders_admin_returns_all_orders_newest_first` |
| US3 scenario 2 (status filter) | `test_get_orders_admin_filters_by_status` |
| US3 scenario 3–4 (limit / cap) | `test_get_orders_admin_respects_limit`, `test_get_orders_admin_limit_over_100_capped` |
| US3 scenario 5 (invalid status) | `test_get_orders_admin_invalid_status_returns_422` |
| US3 scenario 6 (non-admin) | `test_get_orders_admin_as_customer_returns_403` |

---

## Task alignment (`tasks.md`)

| Task | Plan section |
|------|----------------|
| T030 | Contract tests |
| T031 | Integration tests + helper |
| T032 | Run RED |
| T033 | `list_admin` service |
| T034 | Router `GET /orders` |
| T035 | Query validation (`OrderStatus`, `ge=1` on limit) |
| T036 | Run GREEN |

---

## Verification commands

**US3-only:**

```bash
backend/.venv/bin/pytest tests/contract/test_orders_contract.py \
  tests/integration/test_orders.py \
  tests/contract/test_route_access_policy.py \
  -k "get_orders_admin" -v
```

**Regression (US1 + US2 + US3):**

```bash
backend/.venv/bin/pytest tests/contract/test_orders_contract.py \
  tests/integration/test_orders.py \
  tests/unit/test_order_service.py \
  -k "checkout or merge or total or post_orders or orders_me or order_by_id or forbidden or get_orders_admin" -v
```

---

## Self-review

- **Placeholder scan:** None.
- **Consistency:** Matches `brainstorm.md`, `spec.md` US3, `orders-api.yaml`.
- **Scope:** Admin list only; no US4 PATCH.
- **Ambiguity resolved:** `limit>100` capped in repo, not rejected at Query layer.

---

## Execution handoff

Plan saved to `docs/harness-traces/orders-us3/plan.md`.

**Next:** TDD — write failing tests (T030–T032), then implement T033–T035, verify T036.
