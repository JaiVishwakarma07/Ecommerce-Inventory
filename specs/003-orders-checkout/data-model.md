# Data Model: Orders & Checkout

**Feature**: `003-orders-checkout`  
**Date**: 2026-05-28

## Entity: Order

Represents a customer purchase with fulfillment status and shipping destination.

### Table: `orders`

| Column | Type | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | auto | PRIMARY KEY |
| `user_id` | INTEGER | NO | — | FK → `users.id` |
| `status` | VARCHAR(50) | NO | `pending` | one of five UI values |
| `total_amount` | NUMERIC(12,2) | NO | — | ≥ 0; server-computed |
| `shipping_address` | TEXT | NO | — | min 1 char (after trim) |
| `stock_restored` | BOOLEAN | NO | `false` | **internal**; not in API JSON |
| `created_at` | TIMESTAMPTZ | NO | now() | set on insert |
| `updated_at` | TIMESTAMPTZ | NO | now() | set on insert/update |

### Indexes

- `ix_orders_user_id` on (`user_id`) — list `GET /orders/me`
- `ix_orders_status` on (`status`) — admin filter
- `ix_orders_created_at` on (`created_at` DESC) — list ordering (optional composite with status)

## Entity: Order line item

A single product line on an order with checkout-time snapshots.

### Table: `order_line_items`

| Column | Type | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | auto | PRIMARY KEY |
| `order_id` | INTEGER | NO | — | FK → `orders.id` ON DELETE CASCADE |
| `product_id` | INTEGER | NO | — | **no FK** to `products` in v1 |
| `product_name` | VARCHAR(255) | NO | — | snapshot at checkout |
| `quantity` | INTEGER | NO | — | ≥ 1 |
| `unit_price` | NUMERIC(10,2) | NO | — | snapshot at checkout |

### Indexes

- `ix_order_line_items_order_id` on (`order_id`)

## Relationships

```text
users 1 ── * orders 1 ── * order_line_items
products (logical reference via product_id only; no FK)
```

## Validation rules (application layer)

| Field | Rule |
|-------|------|
| `shipping_address` | required; strip whitespace; min 1 char after strip |
| `items` | min 1 entry |
| `items[].product_id` | positive integer; must exist at checkout |
| `items[].quantity` | integer ≥ 1 |
| `status` (PATCH) | `pending`, `processing`, `shipped`, `delivered`, `cancelled` |
| `total_amount` | not accepted from client; `sum(qty * unit_price)` at checkout |

## State transitions

### Order `status` (API-visible)

- **Create (checkout)**: always `pending`.
- **Admin PATCH**: any allowed status → any allowed status (free transitions v1).
- **Cancel restock**: first transition **to** `cancelled` triggers inventory restore once (`stock_restored` gate).

### Inventory side effects

| Event | `products.quantity` |
|-------|---------------------|
| Successful checkout | decrease by line quantities |
| First PATCH to `cancelled` | increase by line quantities (per line, if product exists) |
| Repeat `cancelled` PATCH | no change |
| Non-cancel PATCH | no change |

## API projection

**Order** JSON (response):

- `id`, `user_id`, `status`, `total_amount` (number), `shipping_address`, `created_at`, `updated_at` (ISO-8601)
- `items`: array of `{ id, product_id, product_name, quantity, unit_price }`

**OrderCreate** JSON (request):

- `shipping_address`, `items: [{ product_id, quantity }]`

**OrderStatusUpdate** JSON (PATCH):

- `{ "status": "<enum>" }`

**Not exposed**: `stock_restored`
