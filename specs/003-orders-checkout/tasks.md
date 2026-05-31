---
description: "Task list for orders & checkout implementation"
---

# Tasks: Orders & Checkout

**Input**: Design documents from `specs/003-orders-checkout/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/orders-api.yaml`, `quickstart.md`

**Tests**: REQUIRED — TDD per constitution and plan. Write tests first, confirm RED, then implement GREEN.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no dependency on incomplete tasks)
- **[Story]**: `[US1]`–`[US4]` for user-story phases only

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify artifacts and test harness for orders feature.

- [ ] T001 Confirm API contract baseline in `specs/003-orders-checkout/contracts/orders-api.yaml` matches spec FR-001–FR-017 and SPA JSON (`items`, snapshots)
- [ ] T002 [P] Add order test fixtures (`insert_product`, `order_checkout_payload`, customer/admin JWT) in `tests/conftest.py` and `tests/integration/test_orders.py`
- [ ] T003 [P] Create empty `tests/integration/test_orders.py`, `tests/unit/test_order_service.py`, `tests/contract/test_orders_contract.py` module stubs

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared models, persistence helpers, auth, repositories, service shell, router registration.

**⚠️ CRITICAL**: No user story work until this phase completes.

- [ ] T004 Create `Order` and `OrderLineItem` ORM models per `data-model.md` in `app/models/order.py` (include internal `stock_restored`, not exposed in API)
- [ ] T005 Register order models in `app/database.py` bootstrap import for `create_all`
- [ ] T006 [P] Add Alembic migration `alembic/versions/*_create_orders_tables.py` for `orders` and `order_line_items` (or document SQLite `create_all` path if Alembic not wired)
- [ ] T007 [P] Create Pydantic schemas `OrderCreate`, `OrderResponse`, `OrderLineItemResponse`, `OrderStatusUpdate` in `app/schemas/order.py` (nested key `items`, `OrderStatus` literal enum)
- [ ] T008 [P] Implement `require_customer` in `app/dependencies/auth.py` (reject `role != customer` with 403)
- [ ] T009 [P] Extend `ProductRepository` with `get_by_ids` and `adjust_quantity` (flush only, no commit) in `app/repositories/product_repository.py`
- [ ] T010 Implement `OrderRepository` async methods in `app/repositories/order_repository.py` (`create_with_line_items`, `get_by_id`, `list_for_user`, `list_all`, `update_status`)
- [ ] T011 Implement `OrderService` helpers `merge_line_items`, `compute_total_amount` and domain exceptions in `app/services/order_service.py`
- [ ] T012 Create empty `APIRouter` in `app/routers/orders.py` and register in `app/main.py` (no handlers yet)

**Checkpoint**: Foundation ready — user story phases can begin.

---

## Phase 3: User Story 1 - Customer checks out (Priority: P1) 🎯 MVP

**Goal**: `POST /orders` returns `201` + full `Order` with snapshotted `product_name`/`unit_price`, decrements stock atomically; `409` on oversell, `404` on missing product, `403` for admin, `401` without token.

**Independent Test**: Customer JWT + valid cart payload → `201` with `id`, `status=pending`, nested `items`, reduced `products.quantity`; oversell → `409` without partial order.

### Tests for User Story 1 (REQUIRED) ⚠️

- [ ] T013 [P] [US1] Add contract tests for `POST /orders` (bearerAuth required, `Order` response schema, `items` key) in `tests/contract/test_orders_contract.py`
- [ ] T014 [P] [US1] Add failing integration tests: checkout 201 + snapshots + stock decrement, 409 oversell, 404 product, admin 403, no token 401 in `tests/integration/test_orders.py`
- [ ] T015 [P] [US1] Add unit tests for `merge_line_items` and `compute_total_amount` in `tests/unit/test_order_service.py`
- [ ] T016 [US1] Run US1 tests and confirm FAIL: `pytest tests/contract/test_orders_contract.py tests/integration/test_orders.py tests/unit/test_order_service.py -k "checkout or merge or total" -v`

### Implementation for User Story 1

- [ ] T017 [US1] Implement `OrderService.checkout` (merge lines, validate stock, snapshot, `total_amount`, transactional commit) in `app/services/order_service.py`
- [ ] T018 [US1] Implement `POST /orders` with `Depends(require_customer)` and `response_model=OrderResponse` in `app/routers/orders.py`
- [ ] T019 [US1] Map `InsufficientStockError` → 409, `ProductNotFoundForOrderError` → 404 in `app/routers/orders.py`
- [ ] T020 [US1] Add structlog `order_checkout_*` events in `app/routers/orders.py`
- [ ] T021 [US1] Re-run US1 tests and confirm PASS: `pytest tests/contract/test_orders_contract.py tests/integration/test_orders.py tests/unit/test_order_service.py -k "checkout or merge or total" -v`

**Checkpoint**: Customer checkout works end-to-end (MVP).

---

## Phase 4: User Story 2 - Customer views order history (Priority: P1)

**Goal**: `GET /orders/me` returns caller's orders newest-first; `GET /orders/{id}` returns order for owner or admin; `403` for non-owner; `404` missing; `401` without token.

**Independent Test**: Place order as customer A; `GET /orders/me` and `GET /orders/{id}` as A succeed; customer B gets `403` on A's order id.

### Tests for User Story 2 (REQUIRED) ⚠️

- [x] T022 [P] [US2] Add contract tests for `GET /orders/me` and `GET /orders/{order_id}` in `tests/contract/test_orders_contract.py`
- [x] T023 [P] [US2] Add failing integration tests: list mine, get own detail, forbidden other user, not found, 401 in `tests/integration/test_orders.py`
- [x] T024 [US2] Run US2 tests and confirm FAIL: `pytest tests/integration/test_orders.py -k "orders_me or order_by_id or forbidden" -v`

### Implementation for User Story 2

- [x] T025 [US2] Implement `OrderService.list_mine` and `OrderService.get_order` (owner-or-admin) in `app/services/order_service.py`
- [x] T026 [US2] Implement `GET /orders/me` and `GET /orders/{order_id}` in `app/routers/orders.py` with `response_model` declared
- [x] T027 [US2] Map `OrderNotFoundError` → 404, `ForbiddenOrderAccessError` → 403 in `app/routers/orders.py`
- [x] T028 [US2] Add structlog `order_list_*` and `order_get_*` events in `app/routers/orders.py`
- [x] T029 [US2] Re-run US2 tests and confirm PASS: `pytest tests/integration/test_orders.py -k "orders_me or order_by_id or forbidden" -v`

**Checkpoint**: US1 + US2 deliver checkout and customer order visibility.

---

## Phase 5: User Story 3 - Admin lists and filters orders (Priority: P2)

**Goal**: Admin `GET /orders` returns all orders; `?status=` exact filter; optional `limit` capped at 100; `403` for non-admin; `422` invalid status.

**Independent Test**: Seed orders in multiple statuses; admin list + `?status=pending` + `?limit=100` return expected subsets; customer `GET /orders` → `403`.

### Tests for User Story 3 (REQUIRED) ⚠️

- [x] T030 [P] [US3] Add contract tests for admin `GET /orders` query params (`status`, `limit`) in `tests/contract/test_orders_contract.py`
- [x] T031 [P] [US3] Add failing integration tests: admin list all, status filter, limit cap, customer 403, invalid status 422 in `tests/integration/test_orders.py`
- [x] T032 [US3] Run US3 tests and confirm FAIL: `pytest tests/integration/test_orders.py -k "get_orders_admin" -v`

### Implementation for User Story 3

- [x] T033 [US3] Implement `OrderService.list_admin` with status filter and `limit` cap in `app/services/order_service.py`
- [x] T034 [US3] Implement admin `GET /orders` with `Depends(require_admin)` in `app/routers/orders.py`
- [x] T035 [US3] Validate `status` query enum (422 on invalid) in `app/routers/orders.py`
- [x] T036 [US3] Re-run US3 tests and confirm PASS: `pytest tests/integration/test_orders.py -k "get_orders_admin" -v`

**Checkpoint**: Admin can browse and filter order queue.

---

## Phase 6: User Story 4 - Admin updates order status (Priority: P2)

**Goal**: Admin `PATCH /orders/{id}/status` returns `200` + updated `Order`; free transitions; cancel restocks inventory once (`stock_restored` gate); idempotent re-cancel; skip restock for deleted products.

**Independent Test**: Checkout reduces stock; PATCH to `cancelled` restores stock once; second cancel PATCH does not double-restock; non-admin → `403`.

### Tests for User Story 4 (REQUIRED) ⚠️

- [x] T037 [P] [US4] Add contract tests for `PATCH /orders/{order_id}/status` in `tests/contract/test_orders_contract.py`
- [x] T038 [P] [US4] Add failing integration tests: status update 200, cancel restock once, idempotent cancel, deleted product skip, customer 403 in `tests/integration/test_orders.py`
- [x] T039 [US4] Run US4 tests and confirm FAIL: `pytest tests/integration/test_orders.py -k "patch_order or patch_cancel" -v`

### Implementation for User Story 4

- [x] T040 [US4] Implement `OrderService.update_status` with cancel restock rules in `app/services/order_service.py`
- [x] T041 [US4] Implement `PATCH /orders/{order_id}/status` with `Depends(require_admin)` in `app/routers/orders.py`
- [x] T042 [US4] Add structlog `order_status_update_*` events (include `restocked` bool) in `app/routers/orders.py`
- [x] T043 [US4] Re-run US4 tests and confirm PASS: `pytest tests/integration/test_orders.py -k "patch_order or patch_cancel" -v`

**Checkpoint**: Full order lifecycle (checkout → read → admin list → status + restock) operational.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Auth policy, docs, coverage, and verification.

- [ ] T044 [P] Extend route access policy: all `/orders*` return 401 without token in `tests/contract/test_route_access_policy.py`
- [ ] T045 [P] Add unit tests for restock idempotency and `_to_response` mapping in `tests/unit/test_order_service.py`
- [ ] T046 Run full orders suite: `pytest tests/integration/test_orders.py tests/contract/test_orders_contract.py tests/unit/test_order_service.py tests/contract/test_route_access_policy.py -q`
- [ ] T047 Run orders coverage gate: `pytest tests/integration/test_orders.py tests/unit/test_order_service.py --cov=app/services/order_service --cov=app/repositories/order_repository --cov=app/routers/orders --cov-report=term-missing` (target ≥80%)
- [ ] T048 [P] Update `docs/architecture.md` ERD section for live `orders` / `order_line_items` tables
- [ ] T049 Validate quickstart curl flows in `specs/003-orders-checkout/quickstart.md` against running API

---

## Dependencies & Execution Order

### Phase Dependencies

| Phase | Depends on | Blocks |
|-------|------------|--------|
| 1 Setup | — | Phase 2 |
| 2 Foundational | Phase 1 | All user stories |
| 3 US1 | Phase 2 | — |
| 4 US2 | Phase 2 + US1 checkout data | — |
| 5 US3 | Phase 2 + US1 orders exist | — |
| 6 US4 | Phase 2 + US1 orders exist | — |
| 7 Polish | Desired stories complete | — |

### User Story Dependencies

| Story | Depends on | Notes |
|-------|------------|-------|
| US1 (P1) | Foundational | MVP — checkout only |
| US2 (P1) | Foundational + US1 for realistic data | Can stub orders in tests if needed |
| US3 (P2) | Foundational + at least one order | Uses US1 checkout in integration tests |
| US4 (P2) | Foundational + US1 | Restock requires line items from checkout |

### Within Each User Story

1. Contract tests (where applicable) ∥ integration tests ∥ unit tests → confirm RED  
2. Service layer → router handlers → structlog  
3. Re-run story tests → GREEN  
4. Checkpoint before next story

### Parallel Opportunities

- **Phase 1**: T002 ∥ T003  
- **Phase 2**: T006 ∥ T007 ∥ T008 ∥ T009 (after T004–T005)  
- **US1 tests**: T013 ∥ T014 ∥ T015  
- **US2 tests**: T022 ∥ T023  
- **US3 tests**: T030 ∥ T031  
- **US4 tests**: T037 ∥ T038  
- **Polish**: T044 ∥ T045 ∥ T048  
- **After Phase 2**: US3 and US4 can proceed in parallel once US1 has seeded orders (US2 should complete before relying on cross-customer reads)

### Parallel Example: User Story 1

```bash
# Tests in parallel (RED):
pytest tests/contract/test_orders_contract.py -k post_orders -v
pytest tests/integration/test_orders.py -k checkout -v
pytest tests/unit/test_order_service.py -v

# After T017–T020 (GREEN):
pytest tests/contract/test_orders_contract.py tests/integration/test_orders.py tests/unit/test_order_service.py -k "checkout or merge or total" -v
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1–2 (Setup + Foundational)  
2. Complete Phase 3 (US1) → validate checkout with `quickstart.md` §3  
3. **STOP and DEMO** — SPA can place orders and redirect on `data.id`

### Incremental Delivery

1. Foundation → Checkout (US1) → Customer reads (US2) → Admin list (US3) → Admin status/restock (US4) → Polish  
2. After US2, customer-facing order pages are unblocked  
3. After US3–US4, admin order management is complete

### Suggested MVP Scope

**User Story 1 only** (Phase 3) after Foundational — minimum shippable increment for storefront checkout.

---

## Notes

- Paths use existing `app/` layout (`app/routers/orders.py`, not versioned `/api/v1/orders`)  
- List responses are raw `Order[]` — no pagination envelope  
- Checkout role is `customer`; admin receives `403` on `POST /orders`  
- `stock_restored` is persistence-only — never serialize in `OrderResponse`  
- Duplicate `product_id` in POST body merged before validation (FR-017)  
- Product catalog (`002-product-catalog`) must be present for checkout integration tests  
- Reference implementation plan: `docs/superpowers/plans/2026-05-28-orders-checkout.md`  
- Commit after each task or logical checkpoint
