---
description: "Task list for product catalog & admin inventory implementation"
---

# Tasks: Product Catalog & Admin Inventory

**Input**: Design documents from `specs/002-product-catalog/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/products-api.yaml`, `quickstart.md`

**Tests**: REQUIRED — TDD per constitution and plan. Write tests first, confirm RED, then implement GREEN.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no dependency on incomplete tasks)
- **[Story]**: `[US1]`–`[US4]` for user-story phases only

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify artifacts and test harness for product feature.

- [x] T001 Confirm API contract baseline in `specs/002-product-catalog/contracts/products-api.yaml` matches spec FR-001–FR-015
- [ ] T002 [P] Initialize Alembic async scaffold in `alembic.ini`, `alembic/env.py` (if not present) wired to `app.config.settings.resolved_database_url`
- [x] T003 [P] Add product test fixtures (seed products, admin/customer JWT helpers) in `tests/conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared model, persistence, auth dependencies, and service/repository layers.

**⚠️ CRITICAL**: No user story work until this phase completes.

- [x] T004 Create `Product` ORM model per `data-model.md` in `app/models/product.py`
- [ ] T005 Add Alembic migration `alembic/versions/*_create_products_table.py` (unique `sku`, `image_url` NOT NULL default `''`)
- [x] T006 Register `Product` metadata in `app/database.py` bootstrap (`create_all` / import model)
- [x] T007 [P] Create Pydantic schemas `ProductWrite`, `ProductResponse` in `app/schemas/product.py` (`image_url` default `""`, never null)
- [x] T008 [P] Implement `get_current_user` and `require_admin` in `app/dependencies/auth.py` (JWT + DB role lookup)
- [x] T009 [P] Implement `ProductRepository` async methods in `app/repositories/product_repository.py` (`list_products`, `get_by_id`, `create`, `update`, `delete`)
- [x] T010 Implement `ProductService` with `ProductNotFound`, `DuplicateSku` in `app/services/product_service.py`
- [x] T011 Create empty `APIRouter` and register in `app/main.py` from `app/routers/products.py` (no handlers yet)

**Checkpoint**: Foundation ready — user story phases can begin.

---

## Phase 3: User Story 1 - Browse catalog without signing in (Priority: P1) 🎯 MVP

**Goal**: Public `GET /products` returns plain `Product[]` with optional `search`, no default `limit`, includes `quantity=0` items.

**Independent Test**: `GET /products` and `GET /products?search=term` without `Authorization` return 200 and JSON array; catalog with >100 rows returns all when `limit` omitted.

### Tests for User Story 1 (REQUIRED) ⚠️

- [x] T012 [P] [US1] Add contract tests for public `GET /products` (array shape, security: []) in `tests/contract/test_products_contract.py`
- [x] T013 [P] [US1] Add failing integration tests: list all, search name/sku/category, no-limit (>100 seeds), zero-quantity visible in `tests/integration/test_products.py`
- [x] T014 [US1] Run US1 tests and confirm FAIL: `pytest tests/contract/test_products_contract.py tests/integration/test_products.py -k "list or search" -v`

### Implementation for User Story 1

- [x] T015 [US1] Implement `list_products` search/limit logic in `app/repositories/product_repository.py` (no SQL `LIMIT` when `limit` is None; cap `min(limit,100)` when set)
- [x] T016 [US1] Implement list handler in `app/services/product_service.py` and `GET /products` in `app/routers/products.py` with `response_model=list[ProductResponse]`
- [x] T017 [US1] Add structlog `product_list_*` events in `app/routers/products.py`
- [x] T018 [US1] Re-run US1 tests and confirm PASS: `pytest tests/contract/test_products_contract.py tests/integration/test_products.py -k "list or search" -v`

**Checkpoint**: Browse catalog works without authentication.

---

## Phase 4: User Story 2 - View product details (Priority: P1)

**Goal**: Public `GET /products/{id}` returns one product or 404 with `{ "detail": ... }`.

**Independent Test**: `GET /products/1` without token returns 200 + full product; unknown id returns 404.

### Tests for User Story 2 (REQUIRED) ⚠️

- [x] T019 [P] [US2] Add contract tests for `GET /products/{product_id}` in `tests/contract/test_products_contract.py`
- [x] T020 [P] [US2] Add failing integration tests: get by id success and 404 in `tests/integration/test_products.py`
- [x] T021 [US2] Run US2 tests and confirm FAIL: `pytest tests/integration/test_products.py -k "detail or get_by_id" -v`

### Implementation for User Story 2

- [x] T022 [US2] Implement `get_by_id` path in `app/services/product_service.py` and `GET /products/{product_id}` in `app/routers/products.py`
- [x] T023 [US2] Add structlog `product_get_*` events in `app/routers/products.py`
- [x] T024 [US2] Re-run US2 tests and confirm PASS: `pytest tests/integration/test_products.py -k "detail or get_by_id" -v`

**Checkpoint**: US1 + US2 together deliver public catalog read MVP.

---

## Phase 5: User Story 3 - Admin manages inventory (Priority: P2)

**Goal**: Admin-only `POST`, `PUT`, `DELETE` on `/products` with full body, hard delete 204, duplicate SKU 409, customer/no-token 403/401; admin list `?limit=100`.

**Independent Test**: Admin JWT can CRUD; customer gets 403; missing token gets 401; duplicate SKU gets 409.

### Tests for User Story 3 (REQUIRED) ⚠️

- [x] T025 [P] [US3] Add contract tests for secured write endpoints (`bearerAuth` required) in `tests/contract/test_products_contract.py`
- [x] T026 [P] [US3] Add failing integration tests: create 201, put 200, delete 204, 401/403/409, admin `limit=100` in `tests/integration/test_products.py`
- [x] T027 [US3] Run US3 tests and confirm FAIL: `pytest tests/integration/test_products.py -k "admin or create or update or delete" -v`

### Implementation for User Story 3

- [x] T028 [US3] Wire `Depends(require_admin)` on `POST`, `PUT`, `DELETE` in `app/routers/products.py`
- [x] T029 [US3] Implement `POST /products` (201), `PUT /products/{product_id}` (200), `DELETE /products/{product_id}` (204) in `app/routers/products.py`
- [x] T030 [US3] Map `DuplicateSku` → 409 and `ProductNotFound` → 404 with `{ "detail": ... }` in `app/routers/products.py`
- [x] T031 [US3] Add structlog `product_create_*`, `product_update_*`, `product_delete_*` events in `app/routers/products.py`
- [x] T032 [US3] Re-run US3 tests and confirm PASS: `pytest tests/integration/test_products.py -k "admin or create or update or delete" -v`

**Checkpoint**: Full admin inventory CRUD operational.

---

## Phase 6: User Story 4 - Customer uses catalog data in cart (Priority: P2)

**Goal**: List and detail responses expose numeric `price` and integer `quantity` suitable for cart UI (no adapter).

**Independent Test**: Public list/detail JSON types validate as numbers for `price` and `quantity`.

### Tests for User Story 4 (REQUIRED) ⚠️

- [x] T033 [P] [US4] Add integration assertions for numeric `price`/`quantity` and non-null `image_url` string in `tests/integration/test_products.py`
- [x] T034 [US4] Run US4 tests and confirm PASS (may pass once US1/US2 green): `pytest tests/integration/test_products.py -k "cart_fields or numeric" -v`

### Implementation for User Story 4

- [x] T035 [US4] Ensure `ProductResponse` serialization returns JSON number for `price` and int for `quantity` in `app/schemas/product.py`
- [x] T036 [US4] Verify `image_url` coercion to `""` on read/write in `app/services/product_service.py`

**Checkpoint**: Catalog JSON matches frontend cart expectations.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Security policy, docs, coverage, and verification.

- [x] T037 [P] Extend public route allowlist tests for `GET /products` and `GET /products/{id}` in `tests/contract/test_route_access_policy.py` (create file if missing)
- [x] T038 [P] Add unit tests for `ProductService` error mapping in `tests/unit/test_product_service.py`
- [ ] T039 Run full product suite with coverage: `pytest tests/integration/test_products.py tests/contract/test_products_contract.py tests/unit/test_product_service.py --cov=app --cov-report=term-missing`
- [ ] T040 [P] Update `docs/design/api-contract-draft.md` note: v1 browse uses `?search=` only (not `?category=`)
- [ ] T041 Validate quickstart curl flows in `specs/002-product-catalog/quickstart.md` against running API

---

## Dependencies & Execution Order

### Phase Dependencies

| Phase | Depends on | Blocks |
|-------|------------|--------|
| 1 Setup | — | Phase 2 |
| 2 Foundational | Phase 1 | All user stories |
| 3 US1 | Phase 2 | — |
| 4 US2 | Phase 2 (US1 repo/router partial OK) | — |
| 5 US3 | Phase 2 | — |
| 6 US4 | US1 + US2 responses | — |
| 7 Polish | Desired stories complete | — |

### User Story Dependencies

| Story | Depends on | Notes |
|-------|------------|-------|
| US1 (P1) | Foundational | MVP — public list |
| US2 (P1) | Foundational | Can parallel with US1 after T009–T011 |
| US3 (P2) | Foundational + T008 auth deps | Writes independent of US1/US2 |
| US4 (P2) | US1 + US2 | Validation-only; no new endpoints |

### Parallel Opportunities

- **Phase 1**: T002 ∥ T003
- **Phase 2**: T007 ∥ T008 ∥ T009 (after T004–T006)
- **US1 tests**: T012 ∥ T013
- **US2 tests**: T019 ∥ T020
- **US3 tests**: T025 ∥ T026
- **Polish**: T037 ∥ T038 ∥ T040

### Parallel Example: User Story 1

```bash
# Tests in parallel (RED):
pytest tests/contract/test_products_contract.py -k products_list -v
pytest tests/integration/test_products.py -k "list or search" -v

# After T015–T017 (GREEN):
pytest tests/contract/test_products_contract.py tests/integration/test_products.py -k "list or search" -v
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1–2 (Setup + Foundational)
2. Complete Phase 3 (US1) → validate browse
3. Complete Phase 4 (US2) → validate detail
4. **STOP and DEMO** storefront read paths

### Incremental Delivery

1. Foundation → Public read (US1 + US2) → Admin CRUD (US3) → Cart field validation (US4) → Polish

### Suggested MVP Scope

**User Story 1 only** (Phase 3) after Foundational — unblocks browse page; add US2 before cart/detail page.

---

## Notes

- Paths use existing `app/` layout (`routers/`, not `app/api/routes/`)
- No `/api/v1/products` routes
- List response is raw `Product[]` — no `{ data, total }` envelope
- Register creates `customer` only; admin via seed/env per `quickstart.md`
- Commit after each task or logical checkpoint
