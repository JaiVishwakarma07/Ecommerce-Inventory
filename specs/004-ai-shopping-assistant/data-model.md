# Data Model: AI Shopping Assistant

**Feature**: `004-ai-shopping-assistant`  
**Date**: 2026-06-01

## Overview

v1 introduces **no new database tables**. The assistant reads from the existing **`products`** table (see `specs/002-product-catalog/data-model.md`) and returns ephemeral API DTOs.

## API DTOs (Pydantic)

### AssistantQueryRequest

Inbound customer query.

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `query` | string | yes | strip whitespace; min length 1; max length 500 |

### AssistantQueryResponse

Outbound assistant result.

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `answer` | string | yes | non-empty on success; server-generated from DB results in v1 |
| `products` | `ProductResponse[]` | yes | max 5 items; reuse catalog schema |

`ProductResponse` is imported from `app.schemas.product` — identical to `GET /products` items.

## Internal: AssistantSearchFilters

Parsed from LLM JSON; **not** exposed in public API.

| Field | Type | Default | Rules |
|-------|------|---------|-------|
| `search` | string \| null | null | optional keywords for text match |
| `max_price` | Decimal \| null | null | inclusive upper bound |
| `min_price` | Decimal \| null | null | inclusive lower bound |
| `category` | string \| null | null | case-insensitive exact or partial match on `products.category` |
| `include_out_of_stock` | bool | false | when false, require `quantity > 0` |

Validation:
- If both `min_price` and `max_price` set, `min_price <= max_price` or treat as invalid filter → fallback to text-only search or `503` on parse failure (implementation detail in service).
- Empty filter object still allowed → broad in-stock query with limit 5 (discouraged but safe).

## Repository query semantics

Method: `ProductRepository.search_for_assistant(...)`

| Filter | SQL behavior |
|--------|----------------|
| `search` | Case-insensitive `%term%` OR across `name`, `sku`, `category`, `description` |
| `max_price` | `price <= max_price` |
| `min_price` | `price >= min_price` |
| `category` | `lower(category) LIKE %category%` when provided |
| `in_stock_only` | `quantity > 0` when true |
| `limit` | `LIMIT 5` always |

**Sort**: `price ASC`, then `name ASC` (v1 default for “affordable” bias).

## Entity relationships

```text
Customer (users.role = customer)
  → POST /assistant/query (ephemeral)
      → reads Product (0..5 rows)
      → returns AssistantQueryResponse
```

No foreign keys or persistence for assistant queries in v1.

## State transitions

None — each request is stateless. No conversation store.

## Answer generation (v1)

Template examples (server-side):

- 0 results: `"No in-stock products match your search. Try different keywords or a higher budget."`
- 1 result: `"Found 1 product matching your request."`
- N results: `"Found {n} products matching your request."`

Template MUST NOT include product names/prices not present in `products[]` beyond aggregate count (optional v1.1 enhancement: list first product name only if in array).
