# Implementation Plan: AI Shopping Assistant

**Branch**: `004-ai-shopping-assistant` | **Date**: 2026-06-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-ai-shopping-assistant/spec.md`  
**Design reference**: `docs/superpowers/specs/2026-06-01-ai-shopping-assistant-design.md`

## Summary

Deliver `POST /assistant/query` for **customer-only** natural-language product discovery. Pipeline: Groq (OpenAI-compatible) extracts structured search filters → async repository query on existing `products` table (max 5, in-stock default) → server template builds `answer` → `{ answer, products }` where `products[]` is **100% DB-sourced**. Add minimal “Ask AI” UI on `frontend/src/pages/Products.jsx`. TDD with mocked LLM in integration tests.

## Technical Context

**Language/Version**: Python 3.12+ (backend), React 18 / Vite 5 (frontend)  
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (async), pydantic-settings, structlog, **openai** (AsyncOpenAI for Groq), existing JWT auth stack  
**Storage**: SQLite (dev/test) via existing `products` table — **no new migrations**  
**Testing**: pytest, pytest-asyncio, httpx AsyncClient; Vitest for frontend component smoke (optional in tasks)  
**Target Platform**: Local dev — uvicorn :8000, Vite :5173  
**Project Type**: Web application (`backend/` + `frontend/` + root `tests/`)  
**Performance Goals**: p95 assistant latency ≤ 15s including LLM round-trip under dev catalog size  
**Constraints**: Async-only I/O; products never from LLM IDs; errors `{ "detail": ... }`; endpoint auth-required (not public allowlist)  
**Scale/Scope**: v1 single endpoint; ≤5 products/response; single-turn queries; catalog ≤500 SKUs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **API-First Contracts**: `specs/004-ai-shopping-assistant/contracts/assistant-api.yaml` defines path, request/response, auth, errors.
- [x] **Test-First Delivery**: Plan defines unit (filters, answer builder, repository), integration (auth, grounding, mock LLM), contract tests; RED→GREEN per layer.
- [x] **Security by Default**: `POST /assistant/query` requires Bearer + customer role; not on public allowlist; secrets in env only.
- [x] **Async Throughout**: `AsyncOpenAI` + `AsyncSession`; LLM calls via `await`; no sync HTTP in request path.
- [x] **Observability by Default**: structlog events (`assistant_query_success`, `assistant_query_no_results`, `assistant_query_llm_error`, `assistant_query_forbidden`) with `request_id`, `user_id`, `latency_ms`, `result_count`.

**Post-design re-check**: All gates pass. LLM sync fallback not used. No constitution violations requiring complexity tracking.

## Project Structure

### Documentation (this feature)

```text
specs/004-ai-shopping-assistant/
├── spec.md
├── plan.md              # This file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── assistant-api.yaml
└── tasks.md             # Created by /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── config.py                        # ADD llm_* settings
│   ├── main.py                          # include assistant router
│   ├── dependencies/
│   │   ├── auth.py                      # reuse require_customer
│   │   └── rate_limit.py                # ADD assistant_rate_limiter
│   ├── schemas/
│   │   └── assistant.py                 # NEW AssistantQueryRequest/Response, AssistantSearchFilters
│   ├── clients/
│   │   └── llm_client.py                # NEW AsyncOpenAI wrapper
│   ├── repositories/
│   │   └── product_repository.py        # ADD search_for_assistant
│   ├── services/
│   │   └── assistant_service.py         # NEW orchestration + answer template
│   └── routers/
│       └── assistant.py                 # NEW POST /assistant/query
├── requirements.txt                     # ADD openai

frontend/
└── src/
    └── pages/
        └── Products.jsx                 # ADD Ask AI block (customer only)

tests/
├── contract/
│   └── test_assistant_contract.py       # NEW
├── integration/
│   └── test_assistant.py                # NEW (mock LLM)
└── unit/
    ├── test_assistant_service.py        # NEW
    └── test_assistant_filters.py        # NEW (optional split)
```

**Structure Decision**: Extend existing `backend/app/` layered layout and root `tests/` mirror used by auth, products, and orders. New modules isolated under `assistant_*` and `clients/llm_client.py`.

## Phase 0: Research

Completed — see [research.md](./research.md). Resolved: Groq via AsyncOpenAI, filter-only LLM output, repository extension, mock LLM in CI, no new DB tables, 429 rate limit.

## Phase 1: Design & Contracts

Completed artifacts:

| Artifact | Path |
|----------|------|
| Data model | [data-model.md](./data-model.md) |
| API contract | [contracts/assistant-api.yaml](./contracts/assistant-api.yaml) |
| Quickstart | [quickstart.md](./quickstart.md) |

### Implementation sequence (for `/speckit-tasks`)

1. **Config + LLM client** — Settings fields; `AssistantLlmClient.extract_filters(query) -> AssistantSearchFilters`; 503 on misconfig/timeout/parse error.
2. **Schemas** — `AssistantQueryRequest`, `AssistantQueryResponse`, internal `AssistantSearchFilters`.
3. **Repository** — `search_for_assistant` with price/stock/text filters, `LIMIT 5`.
4. **Service** — `AssistantService.query(db, query_text)` orchestrates LLM → repo → template answer; never accept product IDs from LLM.
5. **Rate limit** — `enforce_assistant_rate_limit` dependency (10/min).
6. **Router** — `POST /assistant/query` with `Depends(require_customer)`; structlog metrics.
7. **main.py** — `include_router(assistant_router)`.
8. **Tests** — contract → integration (mock LLM) → unit; grounding test asserts IDs ⊆ DB.
9. **Frontend** — Products.jsx Ask AI UI for customers.
10. **Docs** — Update `docs/architecture.md` assistant section (optional task).

### LLM prompt sketch (implementation detail)

System prompt instructs model to output JSON only:

```json
{
  "search": "laptop",
  "max_price": 10000,
  "min_price": null,
  "category": null,
  "include_out_of_stock": false
}
```

No `products` or `ids` keys allowed. Service validates with Pydantic before repository call.

### Testing strategy

| Layer | Focus |
|-------|--------|
| Unit | Filter validation; answer template 0/1/N; repository SQL filters with in-memory SQLite |
| Integration | Customer 200; visitor 401; admin 403; mock LLM → grounded IDs; empty results; 503 on LLM error |
| Contract | Request/response shapes per YAML |

### Observability

Log fields per request: `request_id`, `path`, `method`, `user_id`, `status_code`, `outcome`, `latency_ms`, `result_count`, `llm_latency_ms` (optional split).

### Dependencies

| Feature | Usage |
|---------|--------|
| `user-authentication` | Bearer JWT, `require_customer` |
| `002-product-catalog` | `Product`, `ProductResponse`, `ProductRepository` |

## Complexity Tracking

> No violations — table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
