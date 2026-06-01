# Research: AI Shopping Assistant

**Feature**: `004-ai-shopping-assistant`  
**Date**: 2026-06-01

## R1 — LLM client and provider

**Decision**: Use `openai` Python SDK `AsyncOpenAI` with `base_url=LLM_BASE_URL` pointing at Groq (`https://api.groq.com/openai/v1`), model from `LLM_MODEL` (default `llama-3.3-70b-versatile`).

**Rationale**: Groq exposes an OpenAI-compatible chat completions API. The async client satisfies constitution async I/O. Structured JSON filter extraction via `response_format={"type": "json_object"}` (or equivalent) keeps LLM output parseable.

**Alternatives considered**:
- Raw `httpx` POST (reject): more boilerplate; OpenAI SDK handles timeouts and typing.
- Local Ollama (reject): user chose Groq hosted API.
- Synchronous `openai` client (reject): blocks event loop.

## R2 — Anti-hallucination product grounding

**Decision**: Two-phase server pipeline — (1) LLM returns **filter JSON only** (`AssistantSearchFilters` schema); (2) repository query returns rows; (3) route sets `products[]` from repository only; (4) `answer` built by template from DB rows (v1, no second LLM call).

**Rationale**: Hard requirement that product IDs never come from model free text. Template answers eliminate risk of answer text inventing SKUs/prices while keeping v1 simple.

**Alternatives considered**:
- Tool-calling with model-written product list (reject): requires stripping model output; higher hallucination risk.
- Second LLM call for answer (defer v2): richer text but needs strict grounding prompts.

## R3 — Repository search extension

**Decision**: Add `ProductRepository.search_for_assistant(db, *, search, max_price, min_price, category, in_stock_only, limit=5)` with SQLAlchemy filters on existing `products` table. Include `description` in text OR match (catalog list search uses name/sku/category only — assistant search is intentionally broader).

**Rationale**: Natural queries reference product types in descriptions. Hard `LIMIT 5` at SQL level enforces FR-005.

**Alternatives considered**:
- Reuse `list_products(search=...)` only (reject): no price bounds; narrower field set.
- Full-table load + Python filter (reject): does not scale; violates existing catalog patterns.

## R4 — Auth and rate limiting

**Decision**: Reuse `require_customer` from `app.dependencies.auth`. Add `assistant_rate_limiter` mirroring login limiter — **10 requests/minute** keyed by user id or client IP fallback.

**Rationale**: FR-001/FR-012; LLM calls are cost-sensitive. Admin forbidden keeps assistant shopper-facing.

**Alternatives considered**:
- Public assistant (reject): brainstorm decision B — customers only.
- Shared login rate limiter (reject): different abuse profile.

## R5 — LLM failure modes

**Decision**: Missing `LLM_API_KEY` or `LLM_BASE_URL` → `503` at request time. Timeout 15s → `503`. Invalid JSON from model → log error, `503`. Never return synthetic products on failure.

**Rationale**: FR-009 fail-closed; trust requirement.

## R6 — Configuration

**Decision**: Extend `app.config.Settings` with optional `llm_api_key`, `llm_base_url`, `llm_model`, `llm_timeout_seconds` (default 15), loaded from env `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`.

**Rationale**: Secrets via environment; matches project pydantic-settings pattern.

## R7 — Frontend integration

**Decision**: Extend `frontend/src/pages/Products.jsx` — conditional “Ask AI” block when auth context has customer role; POST via existing axios instance with bearer header.

**Rationale**: Minimal UI scope (brainstorm C); reuses product card markup.

## R8 — Testing LLM in CI

**Decision**: Integration tests **mock** `AssistantLlmClient.extract_filters` (protocol or dependency override); contract/unit tests cover filter schema and repository. Optional manual smoke test with real Groq key documented in quickstart.

**Rationale**: CI must not depend on external API keys; grounding tests remain deterministic.

## R9 — HTTP status for rate limit

**Decision**: Return **429 Too Many Requests** with `{ "detail": "Rate limit exceeded" }` when assistant limiter trips (align with auth rate limit pattern if present, else document as new behavior).

**Rationale**: FR-012 edge case; standard semantics.

## R10 — No new database tables

**Decision**: No migrations for v1. Assistant queries are ephemeral; all data reads from existing `products` table.

**Rationale**: YAGNI; design explicitly non-persistent.
