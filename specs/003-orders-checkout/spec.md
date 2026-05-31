# Feature Specification: Orders & Checkout

**Feature Branch**: `003-orders-checkout`

**Created**: 2026-05-28

**Status**: Draft

**Input**: Orders & checkout — customers place orders from a client-side cart; users view order history; admins list orders and update fulfillment status. Target consumers: React SPA and API clients sharing the same JSON contract.

**Design reference**: `docs/superpowers/specs/2026-05-28-orders-checkout-design.md` (approved brainstorm)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Customer checks out (Priority: P1)

As a logged-in customer, I can submit my cart as an order with a shipping address and line items (product id + quantity) so that I receive a confirmed order with a stable total and product details captured at purchase time.

**Why this priority**: Checkout is the core revenue path; without it, the storefront cannot complete a sale.

**Independent Test**: Authenticate as a customer, `POST /orders` with valid items and address; verify `201`, order `id`, `status` of `pending`, nested `items` with `product_name` and `unit_price` matching catalog at checkout time, and reduced product stock.

**Acceptance Scenarios**:

1. **Given** a customer is authenticated and products have sufficient stock, **When** they submit a valid order with `shipping_address` and at least one line item, **Then** the system returns HTTP `201` with a complete `Order` object including `id` usable for redirect.
2. **Given** a customer checks out, **When** the order is created, **Then** each line item includes snapshotted `product_name` and `unit_price` from the catalog at checkout (not live catalog values on later reads).
3. **Given** a customer checks out successfully, **When** the order is persisted, **Then** catalog stock for each product is reduced by the ordered quantity in the same operation.
4. **Given** a customer requests more quantity than available for any product, **When** they submit the order, **Then** the system returns HTTP `409` with a `detail` message identifying insufficient stock.
5. **Given** a line item references a non-existent product, **When** they submit the order, **Then** the system returns HTTP `404` with a `detail` message.
6. **Given** an admin is authenticated, **When** they attempt `POST /orders`, **Then** the system returns HTTP `403`.
7. **Given** no valid bearer token, **When** `POST /orders` is attempted, **Then** the system returns HTTP `401`.

---

### User Story 2 - Customer views order history (Priority: P1)

As a logged-in user, I can list all orders I have placed and open any one of them to see status, shipping address, total, and line items with historical snapshots.

**Why this priority**: Order visibility is required for trust and support after checkout.

**Independent Test**: Place an order, then call `GET /orders/me` and `GET /orders/{id}` as the same user; verify list and detail match the created order shape.

**Acceptance Scenarios**:

1. **Given** a user has placed orders, **When** they call `GET /orders/me` with a valid token, **Then** the system returns HTTP `200` with a JSON array of their orders (newest first), each including nested `items`.
2. **Given** a user owns an order, **When** they call `GET /orders/{order_id}`, **Then** the system returns HTTP `200` with the full `Order` object.
3. **Given** a user does not own the order, **When** they call `GET /orders/{order_id}`, **Then** the system returns HTTP `403`.
4. **Given** no order exists for the id, **When** an authorized caller requests it, **Then** the system returns HTTP `404`.
5. **Given** no valid bearer token, **When** order read endpoints are called, **Then** the system returns HTTP `401`.

---

### User Story 3 - Admin lists and filters orders (Priority: P2)

As an admin, I can view all customer orders and optionally filter by fulfillment status or cap the list size for operational review.

**Why this priority**: Operations need visibility into the order queue before status updates.

**Independent Test**: Authenticate as admin, create sample orders, call `GET /orders` and `GET /orders?status=pending` with optional `limit`.

**Acceptance Scenarios**:

1. **Given** an admin is authenticated, **When** they call `GET /orders`, **Then** the system returns HTTP `200` with a JSON array of all orders (newest first), each with nested `items`.
2. **Given** an admin calls `GET /orders?status=pending`, **When** orders exist in multiple statuses, **Then** only orders with `status` exactly `pending` are returned.
3. **Given** an admin passes `limit=100`, **When** more than 100 orders match, **Then** at most 100 orders are returned.
4. **Given** an admin passes `limit` greater than 100, **When** the request is processed, **Then** results are capped at 100.
5. **Given** an invalid `status` query value, **When** an admin lists orders, **Then** the system returns HTTP `422`.
6. **Given** a non-admin user, **When** they call `GET /orders`, **Then** the system returns HTTP `403`.

---

### User Story 4 - Admin updates order status (Priority: P2)

As an admin, I can change an order’s fulfillment status to any supported value so the customer-facing UI and operations stay in sync. Cancelling an order returns stock to inventory once.

**Why this priority**: Fulfillment workflow depends on status updates; cancel must restore sellable inventory.

**Independent Test**: Admin `PATCH /orders/{id}/status` with each status; verify `200` and updated order; cancel once and confirm stock restored; cancel again idempotently without double restock.

**Acceptance Scenarios**:

1. **Given** an admin and a valid order, **When** they `PATCH` with `{ "status": "<any allowed value>" }`, **Then** the system returns HTTP `200` with the updated `Order` including new `status` and `updated_at`.
2. **Given** an admin sets status to `cancelled` from any prior status, **When** the update succeeds, **Then** product stock is increased by each line item’s quantity (once per order).
3. **Given** an order is already `cancelled`, **When** an admin sets status to `cancelled` again, **Then** stock is not restored a second time.
4. **Given** a product referenced by a cancelled order was deleted from the catalog, **When** restock runs, **Then** the status update still succeeds (`200`) and remaining products are restocked.
5. **Given** a non-admin user, **When** they attempt status update, **Then** the system returns HTTP `403`.
6. **Given** free status transitions, **When** an admin moves e.g. `delivered` → `processing`, **Then** the system allows it (no transition matrix in v1).

---

### Edge Cases

- Duplicate `product_id` in one checkout payload → quantities merged before stock validation.
- Empty `items` array or missing `shipping_address` → HTTP `422`.
- `shipping_address` with only whitespace after trim → treat as invalid if trimmed empty; otherwise min length 1 character required.
- Checkout with zero stock product → `409`, no order created, no stock change.
- Concurrent checkouts for last unit → only one succeeds; other receives `409`.
- Product price or name changes after order placed → historical order lines unchanged on read.
- Admin `GET /orders/{id}` for any order → allowed (same shape as customer detail).
- Same `status` in PATCH as current → `200`, no duplicate restock on cancel.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose `POST /orders` requiring bearer authentication; only users with the **customer** role may checkout; admins receive HTTP `403`.
- **FR-002**: System MUST accept checkout body with `shipping_address` (required, minimum 1 character) and `items` (array, minimum 1 entry) where each item has `product_id` (integer) and `quantity` (integer ≥ 1).
- **FR-003**: System MUST return HTTP `201` on successful checkout with a complete `Order` JSON object including `id`, `user_id`, `status` defaulting to `pending`, `total_amount`, `shipping_address`, `created_at`, `updated_at`, and nested `items`.
- **FR-004**: System MUST snapshot `product_name` and `unit_price` on each line item from the catalog at checkout time and return them on all order reads.
- **FR-005**: System MUST compute `total_amount` as the sum of `quantity × unit_price` for all line items at checkout; clients MUST NOT supply `total_amount`.
- **FR-006**: System MUST decrement catalog stock by ordered quantities atomically with order creation; insufficient stock MUST yield HTTP `409` with a `detail` string and MUST NOT create a partial order.
- **FR-007**: System MUST return HTTP `404` when any referenced `product_id` does not exist at checkout.
- **FR-008**: System MUST expose `GET /orders/me` returning a JSON array of the authenticated user’s orders, newest first, each with nested `items`.
- **FR-009**: System MUST expose `GET /orders/{order_id}` returning one `Order` for the order owner or an admin; other users receive HTTP `403`; missing order receives HTTP `404`.
- **FR-010**: System MUST expose `GET /orders` for admins only, returning all orders newest first, with optional `status` filter (exact match on `pending`, `processing`, `shipped`, `delivered`, `cancelled`) and optional `limit` capped at 100.
- **FR-011**: System MUST expose `PATCH /orders/{order_id}/status` for admins only with body `{ "status": "<value>" }` where `status` is one of the five allowed values; response HTTP `200` with updated `Order`.
- **FR-012**: System MUST allow free status transitions (any allowed status to any allowed status) in v1.
- **FR-013**: System MUST restock catalog quantities once when an order first transitions to `cancelled`, and MUST NOT restock again if already cancelled or already restocked.
- **FR-014**: System MUST require bearer authentication on all `/orders` routes; none are publicly accessible without a token.
- **FR-015**: System MUST return errors as `{ "detail": "..." }` (validation failures may use an array under `detail` for HTTP `422`).
- **FR-016**: System MUST use nested key `items` on `Order` responses (not `line_items`).
- **FR-017**: System MUST merge duplicate `product_id` entries in a single checkout request by summing quantities before validation.

### Key Entities

- **Order**: A purchase placed by a user. Attributes: unique id, owning user, fulfillment status, computed total amount, shipping address, created/updated timestamps. Related to many line items. Internal restock tracking is not exposed in API responses.
- **Order line item (items[])**: A single product line on an order. Attributes: unique id, referenced product id, snapshotted product name, quantity purchased, snapshotted unit price at checkout. Preserves history if catalog product is later changed or removed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A logged-in customer can complete checkout from cart submission to receiving an order id in one successful request at least 95% of the time when stock is available.
- **SC-002**: 100% of successful checkouts return snapshotted `product_name` and `unit_price` that match the catalog values at the moment of purchase.
- **SC-003**: 100% of checkout attempts exceeding available stock are rejected without creating an order or reducing stock.
- **SC-004**: Customers can retrieve their full order history and any single order detail with the same JSON shape the React SPA expects, without client-side transformation.
- **SC-005**: Admins can list, filter by status, and update any order status in one request, with cancel restock applied exactly once per order.
- **SC-006**: Unauthorized access (missing token, wrong role, wrong owner) is rejected 100% of the time with HTTP `401` or `403` as appropriate.

## Assumptions

- User authentication (JWT bearer, roles) and product catalog are already implemented.
- Checkout role is **`customer`** (registered users default to this role); “logged-in user” for checkout means authenticated customer, not admin.
- Cart state lives in the React SPA; the API only receives the final checkout payload.
- Currency display is handled by the frontend; amounts are numeric in JSON.
- No payment capture, refunds, tax, or shipping carrier integration in v1.
- No guest checkout; all order routes require authentication.
- No versioned `/api/v1/orders` path alias in v1.
- List responses are plain `Order[]` arrays without pagination metadata envelopes.
- Product hard delete remains allowed; cancelled-order restock skips deleted products without failing the status update.
- Design and API examples in `docs/superpowers/specs/2026-05-28-orders-checkout-design.md` define wire JSON shapes for planning and contract tests.

## Out of Scope (v1)

- Server-side cart API
- Payments, refunds, and payment webhooks
- Customer-initiated cancel in the UI/API
- Versioned `/api/v1/orders` routes
- Response envelope wrappers and pagination metadata (`total`, `page`, etc.)
- Admin placing orders via `POST /orders`
- Enforced order status state machine (Phase 2)
- Dashboard / analytics endpoints
- Blocking product delete when referenced by historical orders
