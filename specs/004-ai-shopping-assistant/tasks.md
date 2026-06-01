---
description: "Task list for AI shopping assistant implementation"
---

# Tasks: AI Shopping Assistant

**Input**: Design documents from `specs/004-ai-shopping-assistant/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/assistant-api.yaml`, `quickstart.md`

**Tests**: REQUIRED — TDD per constitution and plan. Write tests first, confirm RED, then implement GREEN.

**Organization**: Tasks grouped by user story for independent implementation and testing.

**Reference plan**: Detailed TDD steps in `docs/superpowers/plans/2026-06-01-ai-shopping-assistant.md`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no dependency on incomplete tasks)
- **[Story]**: `[US1]`–`[US3]` for user-story phases only

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify artifacts, dependencies, and test harness for assistant feature.

- [x] T001 Confirm API contract baseline in `specs/004-ai-shopping-assistant/contracts/assistant-api.yaml` matches spec FR-001–FR-013 (`POST /assistant/query`, bearerAuth, `{ answer, products }`, error shapes)
- [x] T002 Add `openai` dependency to `backend/requirements.txt`
- [x] T003 [P] Create empty test module stubs: `tests/contract/test_assistant_contract.py`, `tests/integration/test_assistant.py`, `tests/unit/test_assistant_service.py`, `tests/unit/test_assistant_config.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared config, schemas, LLM client, repository search, rate limiting, and service shell.

**⚠️ CRITICAL**: No user story work until this phase completes.

- [x] T004 Add LLM settings (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `llm_timeout_seconds`, `llm_configured`) to `backend/app/config.py`
- [x] T005 [P] Create Pydantic schemas `AssistantQueryRequest`, `AssistantQueryResponse`, internal `AssistantSearchFilters` in `backend/app/schemas/assistant.py` per `data-model.md`
- [x] T006 [P] Implement `AssistantLlmClient.extract_filters` (AsyncOpenAI / Groq, JSON-only filter output) in `backend/app/clients/llm_client.py`
- [x] T007 [P] Add `ProductRepository.search_for_assistant` (text/price/category/stock filters, `LIMIT 5`, sort price ASC) in `backend/app/repositories/product_repository.py`
- [x] T008 [P] Add `assistant_rate_limiter` and `enforce_assistant_rate_limit` (10/min per customer) in `backend/app/dependencies/rate_limit.py`
- [x] T009 Create `AssistantService` shell with template `build_answer(count)` in `backend/app/services/assistant_service.py`
- [x] T010 [P] Add unit tests for LLM config and answer template in `tests/unit/test_assistant_config.py` and `tests/unit/test_assistant_service.py`; run and confirm PASS for foundational helpers

**Checkpoint**: Foundation ready — user story phases can begin.

---

## Phase 3: User Story 1 - Customer asks a natural-language shopping question (Priority: P1) 🎯 MVP

**Goal**: `POST /assistant/query` returns `200` with `{ answer, products }` for customers; `401` visitor, `403` admin, `422` invalid query, `429` rate limit; empty `products` when no matches.

**Independent Test**: Authenticate as customer, `POST /assistant/query` with `"laptop under 10000"` → `200`, non-empty `answer`, each `products[]` item matches catalog `ProductResponse` shape and exists in DB.

### Tests for User Story 1 (REQUIRED) ⚠️

> **NOTE: Write these tests FIRST and ensure they FAIL before implementation**

- [x] T011 [P] [US1] Add contract tests for `POST /assistant/query` (bearerAuth, request/response schemas, max 5 products) in `tests/contract/test_assistant_contract.py`
- [x] T012 [P] [US1] Add failing integration tests: customer 200 + grounded products, empty results 200, visitor 401, admin 403, whitespace 422, query >500 chars 422 in `tests/integration/test_assistant.py` (mock LLM via router dependency override)
- [x] T013 [P] [US1] Add unit tests for `search_for_assistant` filter combinations in `tests/unit/test_assistant_service.py` or `tests/unit/test_assistant_repository.py`
- [x] T014 [US1] Run US1 tests and confirm FAIL: `pytest tests/contract/test_assistant_contract.py tests/integration/test_assistant.py tests/unit/test_assistant_service.py -k "assistant" -v`

### Implementation for User Story 1

- [x] T015 [US1] Implement `AssistantService.query` (LLM filters → repository → template answer; never accept product IDs from LLM) in `backend/app/services/assistant_service.py`
- [x] T016 [US1] Implement `POST /assistant/query` with `Depends(require_customer)`, `Depends(enforce_assistant_rate_limit)`, and `response_model=AssistantQueryResponse` in `backend/app/routers/assistant.py`
- [x] T017 [US1] Register assistant router in `backend/app/main.py`; ensure `/assistant/query` is NOT on public allowlist
- [x] T018 [US1] Add structlog events `assistant_query_success`, `assistant_query_no_results`, `assistant_query_forbidden`, `assistant_query_llm_error` in `backend/app/routers/assistant.py`
- [x] T019 [US1] Map LLM misconfig/timeout/parse errors → `503` with `{ "detail": "..." }` in `backend/app/routers/assistant.py`
- [x] T020 [US1] Re-run US1 tests and confirm PASS: `pytest tests/contract/test_assistant_contract.py tests/integration/test_assistant.py tests/unit/test_assistant_service.py -k "assistant" -v`

**Checkpoint**: Customer can query assistant via API (MVP backend).

---

## Phase 4: User Story 3 - Trustworthy product results (Priority: P1)

**Goal**: 100% of returned product IDs exist in catalog; LLM failure returns `503` with no fabricated products; mock LLM fake IDs never appear in response.

**Independent Test**: Seed catalog; run assistant with mocked LLM returning fake product IDs → `products[]` contains only DB rows; LLM error → `503` and empty/no fake catalog.

### Tests for User Story 3 (REQUIRED) ⚠️

- [x] T021 [P] [US3] Add integration test: every returned `products[].id` exists in database at response time in `tests/integration/test_assistant.py`
- [x] T022 [P] [US3] Add integration test: mock LLM JSON includes `product_ids` or fake IDs → response `products[]` still DB-sourced only in `tests/integration/test_assistant.py`
- [x] T023 [P] [US3] Add integration test: LLM timeout/parse failure → `503`, no products returned in `tests/integration/test_assistant.py`
- [x] T024 [US3] Run US3 tests and confirm FAIL (if gaps), then PASS after verification: `pytest tests/integration/test_assistant.py -k "grounding or hallucin or llm_error or fake" -v`

### Implementation for User Story 3

- [x] T025 [US3] Audit `AssistantService.query` and `AssistantLlmClient` to reject/ignore any LLM product ID fields; filters-only contract in `backend/app/services/assistant_service.py` and `backend/app/clients/llm_client.py`
- [x] T026 [US3] Ensure fail-closed `503` path never synthesizes catalog rows in `backend/app/services/assistant_service.py`
- [x] T027 [US3] Re-run US3 grounding suite and confirm PASS: `pytest tests/integration/test_assistant.py -k "grounding or hallucin or llm_error or fake" -v`

**Checkpoint**: Anti-hallucination guarantees verified by automated tests (SC-002).

---

## Phase 5: User Story 2 - Customer uses assistant from the products page (Priority: P1)

**Goal**: Logged-in customers see “Ask AI” on `/products`, submit queries, view `answer` and product cards; visitors and admins do not see the input; API errors show friendly message without breaking catalog.

**Independent Test**: Login as customer → `/products` shows Ask AI → submit query → answer + cards render; logout → hidden; admin login → hidden.

### Tests for User Story 2 (REQUIRED) ⚠️

- [x] T028 [P] [US2] Add Vitest smoke test or document manual checklist for Ask AI visibility and submit flow in `frontend/src/pages/Products.jsx` (optional automated test if Vitest configured)

### Implementation for User Story 2

- [x] T029 [P] [US2] Expose `isCustomer` from `frontend/src/context/AuthContext.jsx`
- [x] T030 [US2] Add Ask AI query input, submit handler (`POST /assistant/query` with bearer token), answer display, and product cards reusing catalog card markup in `frontend/src/pages/Products.jsx`
- [x] T031 [US2] Hide Ask AI block for visitors and admins; show loading and friendly `503`/network error message without breaking catalog list in `frontend/src/pages/Products.jsx`
- [x] T032 [US2] Manual verification: customer flow, visitor hidden, admin hidden, error state per spec acceptance scenarios

**Checkpoint**: End-to-end customer discovery from storefront (SC-005).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Auth policy, full verification, docs, and quickstart validation.

- [x] T033 [P] Extend route access policy: `/assistant/query` requires auth (401 without token) in `tests/contract/test_route_access_policy.py`
- [x] T034 [P] Reset `assistant_rate_limiter` in `tests/conftest.py` autouse fixture alongside existing rate limiters
- [x] T035 Run full assistant suite: `pytest tests/contract/test_assistant_contract.py tests/integration/test_assistant.py tests/unit/test_assistant_service.py tests/unit/test_assistant_config.py tests/contract/test_route_access_policy.py -k "assistant" -q`
- [x] T036 [P] Update assistant section in `docs/architecture.md` (pipeline diagram, env vars, endpoint)
- [x] T037 Validate quickstart flows in `specs/004-ai-shopping-assistant/quickstart.md` against running API with `LLM_*` env set

---

## Dependencies & Execution Order

### Phase Dependencies

| Phase | Depends on | Blocks |
|-------|------------|--------|
| 1 Setup | — | Phase 2 |
| 2 Foundational | Phase 1 | All user stories |
| 3 US1 | Phase 2 | US2 (frontend needs API), US3 (tests need endpoint) |
| 4 US3 | Phase 3 US1 | — |
| 5 US2 | Phase 3 US1 | — |
| 6 Polish | Desired stories complete | — |

### User Story Dependencies

| Story | Depends on | Notes |
|-------|------------|-------|
| US1 (P1) | Foundational | MVP — backend API only |
| US3 (P1) | US1 | Grounding tests validate US1 service; no separate endpoint |
| US2 (P1) | US1 | Frontend consumes live `POST /assistant/query` |

### Within Each User Story

1. Contract tests ∥ integration tests ∥ unit tests → confirm RED
2. Service layer → router → main wiring → structlog
3. Re-run story tests → GREEN
4. Checkpoint before next story

### Parallel Opportunities

- **Phase 1**: T003 ∥ T002 (after T001)
- **Phase 2**: T005 ∥ T006 ∥ T007 ∥ T008 (after T004); T010 ∥ T009
- **US1 tests**: T011 ∥ T012 ∥ T013
- **US3 tests**: T021 ∥ T022 ∥ T023
- **US2**: T029 ∥ T028
- **Polish**: T033 ∥ T034 ∥ T036
- **After US1**: US2 and US3 can proceed in parallel (frontend vs grounding hardening)

### Parallel Example: User Story 1

```bash
# Tests in parallel (RED):
pytest tests/contract/test_assistant_contract.py -v
pytest tests/integration/test_assistant.py -k "assistant and not grounding" -v
pytest tests/unit/test_assistant_service.py -v

# After T015–T019 (GREEN):
pytest tests/contract/test_assistant_contract.py tests/integration/test_assistant.py tests/unit/test_assistant_service.py -k "assistant" -v
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1–2 (Setup + Foundational)
2. Complete Phase 3 (US1) → validate with `quickstart.md` curl examples
3. **STOP and DEMO** — API returns grounded `{ answer, products }` for customers

### Incremental Delivery

1. Foundation → API (US1) → Grounding verification (US3) → Storefront UI (US2) → Polish
2. After US1, backend MVP is shippable for API clients
3. After US2, full customer-facing discovery path is complete

### Suggested MVP Scope

**User Story 1 only** (Phase 3) after Foundational — minimum shippable backend increment.

---

## Notes

- Paths use `backend/app/` layout; tests import via `backend` on `PYTHONPATH` (`tests/conftest.py`)
- LLM env vars: `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` — never commit secrets
- Integration tests MUST mock LLM (`get_llm_client` override) — no live Groq in CI
- `products[]` reuses `ProductResponse` from `backend/app/schemas/product.py` — no shape transformation in frontend
- Default in-stock filter (`quantity > 0`); include out-of-stock only when query intent requests it
- Rate limit: 10 requests/minute per customer on `/assistant/query`
- Detailed step-by-step code samples: `docs/superpowers/plans/2026-06-01-ai-shopping-assistant.md`
- Commit after each task or logical checkpoint
