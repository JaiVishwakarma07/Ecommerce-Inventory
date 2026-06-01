# Implementation Notes (TDD)

Task: `004-ai-shopping-assistant`

**Harness:** Full feature — `POST /assistant/query`, grounding tests, Ask AI on `/products` (`specs/004-ai-shopping-assistant` tasks T001–T037)

**Prerequisites:** Auth (`require_customer`), product catalog (`ProductRepository`, `ProductResponse`)

**Plan:** `specs/004-ai-shopping-assistant/plan.md`  
**Brainstorm (pre-implementation decisions):** `docs/harness-traces/004-ai-shopping-assistant/brainstorm.md`

## Key decisions made during test-driven development

1. **Strict RED → GREEN order**
   - Wrote `tests/unit/test_assistant_config.py` first; confirmed RED (`Settings` has no `llm_api_key`) before touching `config.py`.
   - Each layer followed the same pattern: unit tests → minimal implementation → GREEN before the next layer.
   - Initial integration RED: HTTP **404** (route missing) and **503** when LLM stubbing approach was wrong (see #7).

2. **`Settings` changes for unprefixed LLM env**
   - Added `populate_by_name=True` to `SettingsConfigDict` so `LLM_*` vars work alongside `ECOM_OPPO_*`.
   - Used `Field(validation_alias="LLM_API_KEY")` etc. — not plain field names — so pydantic-settings reads the correct env keys.
   - `llm_configured` implemented as a property (key + base URL both non-empty), not a stored field.

3. **Product mapping reuse**
   - `AssistantService` delegates row → `ProductResponse` via existing `ProductService._to_response` instead of duplicating mapper logic in the assistant module.

4. **Rate limit keyed by customer id (not IP)**
   - Plan sketch used IP-based `_get_client_ip` pattern; implemented **10 req / 60s per `current_user.id`** inside the handler after `require_customer`.
   - Matches spec FR-012 “per-customer” intent; `enforce_assistant_rate_limit(user_id: int)` takes id explicitly.

5. **Blank query validation in schema, not router**
   - `AssistantQueryRequest` strip validator raises on whitespace-only input → **422** from FastAPI/Pydantic automatically.
   - No custom router validation branch.

6. **LLM fail-closed in router only**
   - `LlmUnavailableError` caught in `assistant_query`; service propagates unchanged.
   - Response always **503** + `"Assistant temporarily unavailable"` — never partial `{ answer, products }` on LLM failure.

7. **Integration tests: `dependency_overrides`, not `monkeypatch`**
   - First attempt patched `assistant_router.get_llm_client`; tests still got **503** because `Depends(get_llm_client)` holds the original callable reference at import time.
   - **Fix:** `app.dependency_overrides[get_llm_client] = lambda: StubLlmClient()` in fixtures; teardown pops override.
   - Documented in harness for future assistant/LLM test work.

8. **Grounding tests as separate integration cases**
   - Added explicit tests for: IDs ⊆ DB, fake LLM `product_ids` ignored, empty catalog **200** with `products: []`.
   - US3 verification separate from US1 happy-path tests (not folded into one mega test).

9. **Structlog outcome derived from result count**
   - Single handler logs `assistant_query_success` vs `assistant_query_no_results` based on `len(result.products)`.
   - `assistant_query_llm_error` only on `LlmUnavailableError` path with `outcome="llm_error"`.

10. **Frontend: shared `ProductCard` component**
    - Extracted catalog card markup into `ProductCard` inside `Products.jsx` so AI results and browse grid share identical presentation (spec SC-005).
    - Ask AI block gated on `isCustomer` only — not `isAuthenticated` (admins are authenticated but must not see assistant).

11. **No `/api/v1/assistant` alias**
    - Router mounted at bare `/assistant/query` only, consistent with `/products` and `/orders` brainstorm paths.
    - Frontend calls `api.post("/assistant/query", …)` against existing `VITE_API_URL`.

12. **pytest runner note (Windows dev)**
    - Suite requires `--asyncio-mode=auto` when sync unit tests coexist with async autouse `dispose_database_engine_after_async_test` fixture.
    - Recorded in `verify-output.md`; not a code change.

13. **Slice verification**
    - **27** assistant tests + **45** auth/products regression = **72 passed**, exit 0.
    - See `docs/harness-traces/004-ai-shopping-assistant/verify-output.md`.

## Files touched

| File | Role |
|------|------|
| `backend/app/config.py` | LLM settings + `llm_configured` |
| `backend/app/schemas/assistant.py` | Request/response, filters, answer template |
| `backend/app/clients/llm_client.py` | Groq filter extraction |
| `backend/app/repositories/product_repository.py` | `search_for_assistant` |
| `backend/app/services/assistant_service.py` | Orchestration |
| `backend/app/dependencies/rate_limit.py` | `assistant_rate_limiter` |
| `backend/app/routers/assistant.py` | `POST /assistant/query` |
| `backend/app/main.py` | Register router |
| `backend/requirements.txt` | `openai` |
| `tests/unit/test_assistant_*.py` | Unit tests (5 modules) |
| `tests/integration/test_assistant.py` | Integration + grounding |
| `tests/contract/test_assistant_contract.py` | Contract shapes |
| `tests/contract/test_route_access_policy.py` | Auth policy append |
| `tests/conftest.py` | Reset assistant rate limiter |
| `frontend/src/context/AuthContext.jsx` | `isCustomer` |
| `frontend/src/pages/Products.jsx` | Ask AI UI |
| `frontend/src/styles.css` | Assistant bar styles |
| `docs/architecture.md` | Assistant flow section |

## Pre-implementation decisions (not repeated here)

Access model, grounding Approach 1, Groq env vars, max 5 products, in-stock default, server template answers, and out-of-scope items are recorded in **`brainstorm.md`** and **`docs/superpowers/specs/2026-06-01-ai-shopping-assistant-design.md`**.
