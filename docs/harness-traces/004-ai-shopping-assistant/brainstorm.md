# Brainstorm: AI Shopping Assistant (full feature)

## Task

Implement customer natural-language product discovery — backend API, anti-hallucination guarantees, storefront UI, and polish:

- **Endpoint:** `POST /assistant/query` (bare path only — no `/api/v1` prefix)
- **UI:** Minimal “Ask AI” query box on `/products` (not full chat)
- **Reference:** `specs/004-ai-shopping-assistant/spec.md`, `plan.md`, `tasks.md` (T001–T037)
- **Parent design:** `docs/superpowers/specs/2026-06-01-ai-shopping-assistant-design.md` (approved)
- **Detailed TDD plan:** `docs/superpowers/plans/2026-06-01-ai-shopping-assistant.md`

## Brainstorm Session (2026-06-01)

### Context reviewed

| Artifact | Status |
|----------|--------|
| Design spec | Approved — filter-only LLM, DB-grounded products |
| Feature spec | 3 × P1 user stories (API, UI, trust) |
| Speckit plan | `specs/004-ai-shopping-assistant/plan.md` |
| Task checklist | 37 tasks — `/speckit-tasks` |
| Codebase | No assistant modules under `backend/app/` yet |

### Scope question

**How much in first delivery?**

| Option | Choice |
|--------|--------|
| A — Backend MVP only (Phases 1–3) | — |
| **B — Full feature (all 37 tasks)** | **Selected** |
| C — Backend + frontend, skip polish | — |

**Full delivery includes:** Setup → Foundational → US1 API → US3 grounding tests → US2 frontend → Polish (route access policy, full pytest, architecture docs, quickstart validation).

### Execution question

**How to execute tasks?**

| Option | Choice |
|--------|--------|
| **A — Subagent-driven (one subagent per task, two-stage review)** | **Selected** |
| B — Inline in session | — |
| C — Batch by phase with pauses | — |

**Note:** Do not commit unless user explicitly requests (project rule).

## Final Decisions

| Topic | Decision |
|-------|----------|
| Access | Logged-in **customers** only (`401` visitor, `403` admin) |
| UI | Minimal query box on `/products`; reuse product cards |
| LLM provider | Groq via OpenAI-compatible `AsyncOpenAI` |
| Env vars | `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` (default `llama-3.3-70b-versatile`) |
| Grounding | **Approach 1** — LLM extracts **filter JSON only**; server owns `products[]` from DB |
| Stock filter | In-stock only (`quantity > 0`) unless query explicitly asks for out-of-stock |
| Max products | **5** per response |
| Answer text | Server template from DB row count (v1 — no second LLM call) |
| Rate limit | 10 requests/minute per customer on `/assistant/query` |
| DB changes | **None** — extend existing `products` table queries only |
| CI | Integration tests **mock LLM** — no live Groq in pytest |
| Errors | `{ "detail": "..." }`; LLM failure → `503` fail-closed (no fake products) |

## Architecture (Approved)

```text
Customer (Bearer JWT, role=customer)
  → POST /assistant/query { "query": "laptop under 10000" }
  → backend/app/routers/assistant.py
      Depends(require_customer)
      Depends(enforce_assistant_rate_limit)
  → backend/app/services/assistant_service.py
      query() — orchestration
  → backend/app/clients/llm_client.py
      extract_filters() → AssistantSearchFilters (JSON only, no product IDs)
  → backend/app/repositories/product_repository.py
      search_for_assistant(filters) → up to 5 Product rows
  → template build_answer(count) → AssistantQueryResponse
  → HTTP 200 { answer, products[] }  (products = ProductResponse shape)
```

**Frontend (US2):**

```text
/products (customer only)
  → frontend/src/pages/Products.jsx — Ask AI input + submit
  → POST /assistant/query with bearer token
  → display answer + product cards (same shape as catalog)
```

## POST contract

### Request (`AssistantQueryRequest`)

```json
{ "query": "laptop under 10000" }
```

| Field | Rule |
|-------|------|
| `query` | Required; strip whitespace; length 1–500 |

### Response (`AssistantQueryResponse`, HTTP 200)

```json
{
  "answer": "Found 2 products matching your request.",
  "products": [ /* 0–5 Product objects, same shape as GET /products */ ]
}
```

### LLM internal filter schema (not in public API)

```json
{
  "search": "laptop",
  "max_price": 10000,
  "min_price": null,
  "category": null,
  "include_out_of_stock": false
}
```

No `products`, `ids`, or `product_id` keys from LLM.

## HTTP mapping

| Condition | HTTP | Notes |
|-----------|------|-------|
| Success | `200` | `{ answer, products }` |
| No token | `401` | Not on public allowlist |
| Admin / non-customer | `403` | `require_customer` |
| Empty/whitespace query, query >500 chars | `422` | Pydantic validation |
| Rate limit exceeded | `429` | 10/min per customer |
| LLM misconfig / timeout / parse error | `503` | Fail closed — no fabricated products |

## Anti-hallucination guarantees (US3)

1. LLM schema = filter fields only.
2. Route sets `products[]` exclusively from `ProductRepository.search_for_assistant`.
3. Integration tests: every returned `id` ∈ database; mock LLM fake IDs never appear in response.
4. LLM error → `503`, not partial/fake catalog.

## User stories (all P1, full scope)

| Story | Deliverable | Tasks (approx) |
|-------|-------------|----------------|
| **US1** | `POST /assistant/query` — auth, validation, grounded results | T011–T020 |
| **US3** | Grounding + fail-closed tests | T021–T027 |
| **US2** | Ask AI on `/products` for customers | T028–T032 |

## Testing (TDD)

| Layer | Focus |
|-------|--------|
| Unit | LLM config; answer template; repository filters; service with fake LLM |
| Integration | Customer 200; visitor 401; admin 403; empty results; 503 on LLM error; grounding |
| Contract | Request/response per `contracts/assistant-api.yaml`; route access policy |

### Verification (full suite, Phase 6)

```bash
pytest tests/contract/test_assistant_contract.py \
  tests/integration/test_assistant.py \
  tests/unit/test_assistant_service.py \
  tests/unit/test_assistant_config.py \
  tests/contract/test_route_access_policy.py \
  -k "assistant" -q
```

## File checklist

| Action | Path |
|--------|------|
| Modify | `backend/requirements.txt` (add `openai`) |
| Modify | `backend/app/config.py` |
| Create | `backend/app/schemas/assistant.py` |
| Create | `backend/app/clients/llm_client.py` |
| Modify | `backend/app/repositories/product_repository.py` |
| Create | `backend/app/services/assistant_service.py` |
| Modify | `backend/app/dependencies/rate_limit.py` |
| Create | `backend/app/routers/assistant.py` |
| Modify | `backend/app/main.py` |
| Modify | `tests/conftest.py` (reset assistant rate limiter) |
| Create | `tests/contract/test_assistant_contract.py` |
| Create | `tests/integration/test_assistant.py` |
| Create | `tests/unit/test_assistant_service.py` |
| Create | `tests/unit/test_assistant_config.py` |
| Modify | `tests/contract/test_route_access_policy.py` |
| Modify | `frontend/src/context/AuthContext.jsx` (`isCustomer`) |
| Modify | `frontend/src/pages/Products.jsx` (Ask AI UI) |
| Modify | `docs/architecture.md` (optional polish) |

## Harness artifact layout

```text
docs/harness-traces/004-ai-shopping-assistant/
├── brainstorm.md           # this file — decisions + contract + flow
├── plan.md                 # optional harness-local plan (or use superpowers plan)
├── implementation-notes.md
└── verify-output.md
```

**Task folder:** `004-ai-shopping-assistant`

## References

- `specs/004-ai-shopping-assistant/spec.md`
- `specs/004-ai-shopping-assistant/plan.md`
- `specs/004-ai-shopping-assistant/tasks.md`
- `specs/004-ai-shopping-assistant/contracts/assistant-api.yaml`
- `specs/004-ai-shopping-assistant/data-model.md`
- `specs/004-ai-shopping-assistant/quickstart.md`
- `docs/superpowers/specs/2026-06-01-ai-shopping-assistant-design.md`
- `docs/superpowers/plans/2026-06-01-ai-shopping-assistant.md`

## Approval

**Approved** — Full feature (B), subagent-driven execution (A). Ready for Phase 1 implementation (T001–T003).
