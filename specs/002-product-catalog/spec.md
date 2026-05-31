# Feature Specification: Product Catalog & Admin Inventory

**Feature Branch**: `002-product-catalog`

**Created**: 2026-05-27

**Status**: Draft

**Input**: Product catalog & admin inventory — public browsing and admin inventory management over a single `/products` API for the React SPA and API consumers sharing the same JSON contract.

**Design reference**: `docs/superpowers/specs/2026-05-27-product-catalog-design.md` (approved brainstorm)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse catalog without signing in (Priority: P1)

As a visitor, I can discover products on the storefront without creating an account or signing in. I can view the full catalog or narrow results using a single search term that matches product name, SKU, or category.

**Why this priority**: The catalog is the primary entry point for the ecommerce experience; without public read access, the storefront cannot function.

**Independent Test**: Call the product list without credentials; verify a plain array of products is returned, including items with zero quantity, and optional search filters the list.

**Acceptance Scenarios**:

1. **Given** products exist in the catalog, **When** a visitor requests the product list without credentials, **Then** the system returns HTTP 200 with a JSON array of all products (no pagination wrapper).
2. **Given** products exist with varying names, SKUs, and categories, **When** a visitor searches with a term matching any of those fields, **Then** only matching products are returned (case-insensitive partial match).
3. **Given** a product has quantity zero, **When** a visitor views the catalog, **Then** that product still appears in the list so the UI can show “Out of stock.”
4. **Given** a visitor requests the product list without a limit parameter, **When** more than 100 products exist, **Then** all matching products are returned (no silent cap).

---

### User Story 2 - View product details (Priority: P1)

As a visitor, I can open a single product’s detail page to see full product information before adding to cart.

**Why this priority**: Detail view is required for purchase decisions and cart integration.

**Independent Test**: Request a single product by identifier without credentials; verify full product fields or 404 when missing.

**Acceptance Scenarios**:

1. **Given** a product exists, **When** a visitor requests that product by id, **Then** the system returns HTTP 200 with the complete product record including quantity and price.
2. **Given** no product exists for the requested id, **When** a visitor requests that product, **Then** the system returns HTTP 404 with an error body containing a `detail` field.

---

### User Story 3 - Admin manages inventory (Priority: P2)

As an admin, I can create, update, and delete products after signing in with an account that has the admin role. I send the full product form on every save. Deletes are permanent.

**Why this priority**: Inventory management enables the business to maintain the catalog; it depends on authentication already in place.

**Independent Test**: Authenticate as admin, perform create/update/delete, verify non-admin and unauthenticated callers are rejected appropriately.

**Acceptance Scenarios**:

1. **Given** an admin is authenticated with a valid bearer token, **When** they submit a new product with all required fields, **Then** the system returns HTTP 201 with the created product including id and timestamps.
2. **Given** an admin is authenticated, **When** they replace an existing product with a full PUT body, **Then** the system returns HTTP 200 with the updated product.
3. **Given** an admin is authenticated, **When** they delete a product, **Then** the system returns HTTP 204 with no body and subsequent reads return 404.
4. **Given** a user is authenticated as a customer (non-admin), **When** they attempt create, update, or delete, **Then** the system returns HTTP 403.
5. **Given** no valid token is provided, **When** a write is attempted, **Then** the system returns HTTP 401.
6. **Given** an admin requests the product list with `limit=100`, **When** more than 100 products exist, **Then** at most 100 products are returned.

---

### User Story 4 - Customer uses catalog data in cart (Priority: P2)

As a signed-in customer, I can see accurate stock and pricing on the catalog and use that product data when building a cart and placing orders.

**Why this priority**: Connects catalog visibility to the purchase flow; quantity and price must be trustworthy at browse time.

**Independent Test**: Browse as visitor or customer; confirm quantity and price fields are present and numeric; cart flow can rely on product id, name, and price (order snapshotting handled separately).

**Acceptance Scenarios**:

1. **Given** a product is listed in the catalog, **When** a customer views it, **Then** `quantity` and `price` are present as numbers suitable for display and cart logic.
2. **Given** a product’s price or name changes after an order was placed, **When** viewing historical order data, **Then** order records retain the name and price captured at checkout (out of scope for this feature to implement snapshots; catalog must not assume orders block delete).

---

### Edge Cases

- Duplicate SKU on create or update → HTTP 409 with `detail` explaining the conflict.
- Empty or missing `image_url` on input → stored and returned as empty string `""`, never `null`.
- Invalid payload (negative price, negative quantity, empty name, empty SKU, empty category) → HTTP 422 with validation `detail`.
- Search term with only whitespace → treated as no search filter (return all products, subject to limit rules).
- Admin `limit` greater than 100 → capped at 100.
- Product deleted while on admin list → next list load no longer includes it; detail returns 404.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose `GET /products` as a public endpoint returning a JSON array of products (not a pagination envelope).
- **FR-002**: System MUST support optional `search` on `GET /products` matching name, SKU, or category with case-insensitive partial match.
- **FR-003**: System MUST return all matching products on browse requests when `limit` is omitted (no default cap that hides products).
- **FR-004**: System MUST support optional `limit` on `GET /products`, capping results at 100 when provided (admin use case).
- **FR-005**: System MUST expose `GET /products/{id}` as a public endpoint returning one product or 404.
- **FR-006**: System MUST expose `POST /products`, `PUT /products/{id}`, and `DELETE /products/{id}` requiring `Authorization: Bearer` token and admin role.
- **FR-007**: System MUST accept a full product body on create and update with fields: `name`, `description`, `sku`, `price`, `quantity`, `category`, `image_url`.
- **FR-008**: System MUST return product responses including `id`, all writable fields, `created_at`, and `updated_at` as ISO-8601 strings.
- **FR-009**: System MUST enforce unique SKU across products; duplicate attempts return HTTP 409.
- **FR-010**: System MUST perform hard delete on `DELETE /products/{id}` and return HTTP 204 on success.
- **FR-011**: System MUST return errors in the shape `{ "detail": "..." }` (or validation array under `detail` for 422).
- **FR-012**: System MUST return HTTP 401 for missing or invalid tokens on protected writes; HTTP 403 for valid non-admin tokens.
- **FR-013**: System MUST include products with `quantity` of 0 in public list and detail responses.
- **FR-014**: System MUST use `/products` paths only (no versioned `/api/v1/products` alias in this feature).
- **FR-015**: System MUST default `image_url` to `""` and never return `null` for `image_url`.

### Key Entities

- **Product**: Sellable inventory item exposed to the storefront and admin UI. Attributes: human-readable name, description, unique SKU, unit price, stock quantity, merchandising category, optional image URL (empty string when absent), creation and last-update timestamps. Identified by numeric id.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A visitor can load the full product catalog (no login) in one request when the catalog has up to 500 products, with all items visible on the browse page.
- **SC-002**: At least 95% of valid admin create/update/delete operations complete successfully on the first attempt when authenticated as admin.
- **SC-003**: Search returns only relevant products — when searching for a known SKU, the matching product appears and unrelated products do not.
- **SC-004**: Unauthorized write attempts (no token, customer token) are rejected 100% of the time with 401 or 403 as appropriate.
- **SC-005**: The React SPA can integrate without adapter layers: list responses are a plain array, product shape matches the admin form, and out-of-stock items remain listable.

## Assumptions

- User authentication (login, JWT bearer tokens, roles) is already available; admin users are provisioned outside self-service registration (seed or environment).
- The React SPA is the primary consumer; API paths are bare `/products` on the configured API base URL.
- Catalog size for v1 is small enough that unpaginated browse lists are acceptable.
- Order line-item price/name snapshots at checkout are implemented in a separate orders feature; deleting a product does not require conflict responses for existing orders in v1.
- Currency display formatting (e.g. INR) is handled by the frontend; the API returns numeric price.
- Product categories are free-text labels (max 100 characters), not a separate category master table in v1.

## Out of Scope (v1)

- Pagination metadata (`total`, `page`, `skip`).
- Partial updates (`PATCH`), soft delete, or `is_active` flag.
- Versioned `/api/v1/products` routes.
- Separate `?category=` or `?skip=` query filters.
- `staff` role or API-key authentication.
- Blocking delete when a product is referenced by existing orders (Phase 2).
- Order snapshot implementation (noted for coordination only).
