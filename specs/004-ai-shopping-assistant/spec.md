# Feature Specification: AI Shopping Assistant

**Feature Branch**: `004-ai-shopping-assistant`

**Created**: 2026-06-01

**Status**: Draft

**Input**: Customer AI assistant — logged-in shoppers submit natural-language product queries and receive a helpful answer plus up to five real catalog products from inventory. Target consumers: React SPA (minimal query UI on `/products`) and API clients sharing the same JSON contract.

**Design reference**: `docs/superpowers/specs/2026-06-01-ai-shopping-assistant-design.md` (approved brainstorm)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Customer asks a natural-language shopping question (Priority: P1)

As a logged-in customer, I can type a natural-language question (e.g. `"laptop under 10000"`) so that I get a short answer and a list of matching in-stock products I can browse or add to cart.

**Why this priority**: This is the core value of the assistant — faster discovery than manual keyword search when shoppers describe intent in plain language.

**Independent Test**: Authenticate as customer, `POST /assistant/query` with a valid query; verify `200`, non-empty `answer`, and each product in `products[]` exists in the catalog with matching filters.

**Acceptance Scenarios**:

1. **Given** a customer is authenticated and matching in-stock products exist, **When** they submit `"laptop under 10000"`, **Then** the system returns HTTP `200` with `answer` (string) and `products` (array of at most 5 catalog products).
2. **Given** a successful assistant response, **When** the client inspects `products[]`, **Then** every item uses the same product shape as `GET /products` and every `id` corresponds to a persisted catalog row.
3. **Given** a customer submits a query, **When** no in-stock products match, **Then** the system returns HTTP `200` with `products: []` and an `answer` that explains no matches were found (without inventing products).
4. **Given** a visitor without a token, **When** they call the assistant endpoint, **Then** the system returns HTTP `401`.
5. **Given** an admin is authenticated, **When** they call the assistant endpoint, **Then** the system returns HTTP `403`.
6. **Given** a customer submits an empty or whitespace-only query, **When** the request is processed, **Then** the system returns HTTP `422`.

---

### User Story 2 - Customer uses assistant from the products page (Priority: P1)

As a logged-in customer on the storefront products page, I see an “Ask AI” input so that I can run assistant queries without leaving the catalog.

**Why this priority**: Minimal UI delivery was chosen for v1; the assistant must be discoverable where shoppers already browse.

**Independent Test**: Log in as customer, open `/products`, submit an AI query, verify answer text and product cards render; verify visitors and admins do not see the assistant input.

**Acceptance Scenarios**:

1. **Given** a customer is signed in, **When** they visit `/products`, **Then** an assistant query input and submit control are visible.
2. **Given** a visitor is not signed in, **When** they visit `/products`, **Then** the assistant query input is not shown.
3. **Given** a customer submits a query from the page, **When** the API returns success, **Then** the page displays the `answer` and product results using the same card presentation as the catalog.
4. **Given** the assistant service is unavailable, **When** the customer submits a query, **Then** the UI shows a friendly unavailable message without breaking the rest of the catalog.

---

### User Story 3 - Trustworthy product results (Priority: P1)

As a customer, I need every recommended product to be real inventory so that I never follow links to products that do not exist.

**Why this priority**: Hallucinated product IDs destroy trust and break cart/checkout flows.

**Independent Test**: Run assistant queries against a seeded catalog; assert all returned IDs ⊆ database; run tests with mocked LLM output that includes fake IDs and assert response `products[]` still contains only DB rows.

**Acceptance Scenarios**:

1. **Given** any successful assistant response, **When** `products` is non-empty, **Then** each `id` MUST exist in the catalog database at response time.
2. **Given** the language model fails or returns unusable structured data, **When** the endpoint cannot safely complete, **Then** the system returns HTTP `503` and MUST NOT return fabricated products.

---

### Edge Cases

- Query longer than 500 characters → HTTP `422`.
- Price intent without currency symbol → interpret against numeric catalog `price` values.
- Query explicitly asks for out-of-stock items → include products with `quantity == 0`; otherwise default to in-stock only (`quantity > 0`).
- More than five matches → return at most five products; `answer` may note additional matches exist.
- Rate limit exceeded → HTTP `429` with `{ "detail": "..." }` (or project-standard rate-limit response).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose `POST /assistant/query` requiring bearer authentication; only users with the **customer** role may use it; admins receive HTTP `403`.
- **FR-002**: System MUST accept request body `{ "query": "<string>" }` where `query` is trimmed, length 1–500.
- **FR-003**: System MUST return HTTP `200` on success with `{ "answer": string, "products": Product[] }` where each `Product` matches the catalog response shape.
- **FR-004**: System MUST populate `products[]` exclusively from database query results; the system MUST NOT return product IDs invented by the language model.
- **FR-005**: System MUST return at most **5** products per response.
- **FR-006**: System MUST default to in-stock products only (`quantity > 0`) unless the query explicitly requests out-of-stock items.
- **FR-007**: System MUST support natural-language intent including text search and optional price bounds (e.g. “under 10000”, “above 5000”) mapped to catalog filters.
- **FR-008**: System MUST return HTTP `200` with empty `products` when no matches exist, with an explanatory `answer`.
- **FR-009**: System MUST return HTTP `503` when the assistant language service is unavailable or misconfigured (fail closed — no fake catalog fallback).
- **FR-010**: System MUST return errors as `{ "detail": "..." }` (validation failures may use an array under `detail` for HTTP `422`).
- **FR-011**: System MUST NOT add `/assistant/query` to the public allowlist.
- **FR-012**: System MUST apply per-customer rate limiting on the assistant endpoint (documented limit in plan/quickstart).
- **FR-013**: Frontend MUST show the assistant query UI on `/products` only for authenticated customers.

### Key Entities

- **Assistant query**: A single natural-language request from a customer. Attributes: query text (input only; not persisted in v1).
- **Assistant response**: Ephemeral API payload combining a human-readable `answer` and zero to five **Product** references from the existing catalog entity (see `specs/002-product-catalog/`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A logged-in customer can submit a natural-language query and receive a valid response within 15 seconds at least 95% of the time when the language service is healthy.
- **SC-002**: 100% of product IDs in assistant responses exist in the catalog database (verified by automated integration tests).
- **SC-003**: 100% of unauthorized access attempts (visitor, admin) are rejected with HTTP `401` or `403` as appropriate.
- **SC-004**: Zero-match queries return helpful answers without fabricated products 100% of the time.
- **SC-005**: Customers can use the assistant from `/products` without client-side transformation of product JSON shape.

## Assumptions

- User authentication (bearer tokens, customer role) and product catalog are already implemented.
- Language service credentials are provided via environment variables at runtime (not in source control).
- v1 uses single-turn queries only (no conversation history).
- Currency display formatting is handled by the frontend; API returns numeric `price` on products.
- The existing keyword search box on `/products` remains; the assistant is an additional discovery path.

## Out of Scope (v1)

- Multi-turn chat or session history.
- Visitor (unauthenticated) assistant access.
- Admin assistant or order-status answers.
- Vector / semantic / embedding search.
- Versioned `/api/v1/assistant/*` path alias.
- Persisting assistant queries or analytics dashboard.
- LLM-generated `answer` text that references products not in `products[]` (v1 uses server-built answers from DB rows).
