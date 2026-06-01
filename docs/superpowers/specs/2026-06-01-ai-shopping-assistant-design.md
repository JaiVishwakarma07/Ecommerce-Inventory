# AI Shopping Assistant — Design Spec

**Date:** 2026-06-01  
**Status:** Approved (brainstorm)  
**Feature:** Customer AI assistant for natural-language product discovery on ECOM_OPPO

## Summary

Logged-in **customers** submit natural-language shopping queries (e.g. `"laptop under 10000"`) and receive:

```json
{
  "answer": "Found 2 in-stock laptops under ₹10,000…",
  "products": [ /* up to 5 Product objects from SQLite */ ]
}
```

**Hard requirement:** every item in `products[]` MUST be loaded from the real database. The LLM never supplies product IDs; the server owns the product list entirely.

**Delivery:** backend API + minimal UI — an “Ask AI” query box on the existing `/products` page (not a full chat widget). Single-turn only in v1.

## Goals

- Interpret natural-language product intent via Groq (OpenAI-compatible API).
- Query SQLite with structured filters (text, price bounds, category, stock rules).
- Return at most **5 in-stock** products by default.
- Provide a short human-readable `answer` summarizing results.
- Show assistant UI only to authenticated customers on `/products`.

## Non-Goals (v1)

- Multi-turn chat or conversation history.
- Visitor (unauthenticated) access to the assistant.
- Admin assistant or order-status answers (“where is my order?”).
- Vector / semantic / embedding search.
- Recommendations when zero DB matches exist (beyond a helpful empty-state message).
- Versioned `/api/v1/assistant/*` path alias.

## Decisions (brainstorm)

| Topic | Choice |
|-------|--------|
| Access | Logged-in **customers** only (`401` / `403` otherwise) |
| UI | Minimal query box on `/products` (reuse product cards) |
| LLM provider | Groq via OpenAI-compatible client |
| Model | `llama-3.3-70b-versatile` (env-configurable) |
| Stock filter | In-stock only (`quantity > 0`) unless query explicitly asks for out-of-stock |
| Max products | **5** per response |
| Grounding strategy | **Approach 1** — LLM extracts filters only; server queries DB and builds `products[]` |

## Approach

### Selected: Structured filter extraction + DB query + server-owned response

```
Customer query
  → LLM returns structured filters (JSON only, no product IDs)
  → ProductRepository.search_for_assistant(filters)
  → up to 5 ProductResponse rows from SQLite
  → AnswerBuilder builds answer text from real rows (template v1)
  → HTTP 200 { answer, products }
```

**Rejected alternatives:**

1. **Tool-calling loop** — LLM calls `search_products` then writes answer. Higher risk of answer text mentioning products outside the tool result; requires extra validation to strip model-supplied IDs.
2. **Rule-based parser only** — cheap for “under X” patterns but brittle; still needs LLM for varied phrasing.

### Anti-hallucination guarantees

1. LLM JSON schema includes **filter fields only** (`search`, `max_price`, `min_price`, `category`, `include_out_of_stock`) — no `product_id`, no `products` array.
2. Route handler sets `products` **exclusively** from repository results mapped to `ProductResponse`.
3. Integration tests seed known products and assert every returned `id` exists in the database; fake IDs never appear even if mocked LLM output includes them.
4. v1 `answer` is **template-generated on the server** from DB rows (no second LLM call that could invent SKUs or prices). Optional LLM summarization can be a v2 enhancement with the same DB-only product constraint.

## API Contract

### Endpoint

| Method | Path | Auth | Success |
|--------|------|------|---------|
| `POST` | `/assistant/query` | Customer Bearer | `200` `{ answer, products }` |

Not on the public allowlist — token required.

### Request

```json
{
  "query": "laptop under 10000"
}
```

- `query`: required string, trimmed, min length 1, max length 500.

### Response

```json
{
  "answer": "Found 2 in-stock products matching \"laptop under 10000\".",
  "products": [
    {
      "id": 1,
      "name": "Budget Laptop",
      "description": "...",
      "sku": "LAP-001",
      "price": 8999.0,
      "quantity": 3,
      "category": "electronics",
      "image_url": "",
      "created_at": "2026-05-27T12:00:00Z",
      "updated_at": "2026-05-27T12:00:00Z"
    }
  ]
}
```

- `products`: array of **same `Product` shape** as `GET /products` (`ProductResponse`), max length **5**.
- Zero matches: HTTP `200`, `products: []`, `answer` explains no in-stock matches (still no fabricated products).

### Status codes

| Code | When |
|------|------|
| `200` | Success (including zero matches) |
| `401` | Missing, invalid, or expired bearer token |
| `403` | Valid token but role is not `customer` (includes admin) |
| `422` | Invalid request body (empty/too-long `query`) |
| `503` | LLM unavailable (missing config, timeout, upstream error) |

Errors use project-standard shape: `{ "detail": "..." }`.

## Filter model (LLM → repository)

Extended repository method, e.g. `search_for_assistant(db, *, search, max_price, min_price, category, in_stock_only, limit=5)`:

| Filter | Parsed from | Default |
|--------|-------------|---------|
| `search` | Product type / keywords (“laptop”, “widget”) | optional; case-insensitive partial match on `name`, `sku`, `category`, `description` |
| `max_price` | “under 10000”, “below 500” | none |
| `min_price` | “above 5000”, “at least 100” | none |
| `category` | explicit category if stated | none |
| `in_stock_only` | implicit unless query mentions out-of-stock | `true` |

**Sort:** text relevance first, then `price` ascending (unless query clearly asks for “cheapest” / “most expensive” — v1 may use price ascending as default).

**Limit:** hard cap **5** rows at SQL/repository level.

## LLM configuration

Environment variables only (never committed):

```
LLM_API_KEY=<secret>
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile
```

- OpenAI-compatible chat/completions client with **JSON / structured output** for filter extraction.
- Request timeout ~15 seconds; on failure return `503` with generic `detail`.
- If `LLM_API_KEY` or `LLM_BASE_URL` missing at runtime, endpoint returns `503` (fail closed, no silent fallback to fake products).

## Authorization

- Dependency: `require_customer` (new or reuse pattern from orders checkout).
- **Customer:** allowed.
- **Admin:** `403` (assistant is shopper-facing in v1).
- **Visitor:** `401`.

## Frontend (minimal v1)

**Page:** `frontend/src/pages/Products.jsx`

- Render “Ask AI” input + submit button **only when** user is authenticated with role `customer`.
- On submit: `POST /assistant/query` with bearer token via existing axios client.
- Show loading state; on success render `answer` text and product cards below the search bar (reuse existing catalog card markup/styles).
- On `401`: redirect or prompt login (match existing auth UX).
- On `503`: show friendly “Assistant temporarily unavailable” message.
- Does not replace the existing text `search` box — both can coexist (keyword search vs AI query).

## Rate limiting & observability

- Rate limit: **10 requests per minute per customer** (reuse in-memory limiter pattern from auth login).
- Structured logs: `assistant_query_success`, `assistant_query_no_results`, `assistant_query_llm_error`, `assistant_query_forbidden` with `request_id`, `user_id`, `latency_ms`, `result_count` — no raw API keys or full LLM prompts in logs (query text may be logged at info level; avoid logging secrets).

## Testing strategy

### Unit

- Filter schema validation (Pydantic model for LLM output).
- Repository: price bounds, in-stock filter, limit 5, description search.
- AnswerBuilder: copy for 0 / 1 / N results.

### Integration

- Customer + valid token → `200` with grounded products.
- Visitor → `401`; admin → `403`.
- Mock LLM returns filters → assert products match DB only.
- Zero-match query → `200`, `products: []`.
- LLM failure / timeout → `503`.
- Assert no returned product `id` outside seeded set.

### Contract

- Response shape `{ answer: string, products: Product[] }`.
- Each product object matches catalog contract fields.

## Error & edge cases

- Query with only whitespace → `422`.
- Query longer than 500 chars → `422`.
- Price filter with no currency in query → assume store numeric currency (same as catalog `price` field).
- All matches out of stock → `200`, empty products, answer suggests broadening search or checking back later.
- LLM returns invalid JSON → `503` (log parse error server-side).

## Dependencies on existing features

- **Auth:** JWT bearer, customer role ( `specs/user-authentication/` ).
- **Product catalog:** `Product` model, `ProductResponse`, repository patterns ( `specs/002-product-catalog/` ).
- **Frontend auth context:** token + role available on `Products` page.

## Open questions (deferred)

- v2: second LLM call for richer natural-language `answer` (still DB-grounded).
- v2: multi-turn context on `/assistant` dedicated page.
- v2: semantic search if catalog grows large.

## Next steps (not started)

1. Write feature spec (`specs/004-ai-shopping-assistant/spec.md`) — what/why only.
2. Write implementation plan (`/writing-plans`) — stack, file paths, TDD tasks.
3. OpenSpec change proposal if following change-management workflow.

**Implementation explicitly paused** until spec review and plan approval.
