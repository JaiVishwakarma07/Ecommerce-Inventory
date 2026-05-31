# Orders & Checkout — Design Spec

**Date:** 2026-05-28  
**Status:** Approved (brainstorm)  
**Feature:** Orders & checkout for ECOM_OPPO FastAPI REST API  
**Depends on:** User authentication, product catalog (`specs/002-product-catalog/`)

## Summary

Implement customer checkout and order management aligned with the existing React SPA: client-side cart, `POST /orders` with line items by `product_id`, server-side **mandatory snapshots** (`product_name`, `unit_price`), atomic **stock decrement** on checkout, and **one-time restock** when an admin sets status to `cancelled`. Admin can list/filter orders and freely change status via `PATCH`. Wire format uses nested **`items`** (not `line_items`).

**Approach:** Single `OrderService` with router → service → repository layering (Approach 1), one DB transaction per checkout and per status update that touches inventory.

## Goals

- `POST /orders` → `201` + full `Order` (SPA redirect uses `data.id`).
- `GET /orders/me` → customer's orders with nested `items` and snapshots.
- `GET /orders/{order_id}` → owner or admin.
- Admin: `GET /orders`, `GET /orders?status=...`, optional `limit` (cap 100), `PATCH /orders/{id}/status`.
- Snapshot `product_name` and `unit_price` from catalog at checkout; never read live product price/name for historical display.
- Decrement `products.quantity` on successful checkout; `409` when insufficient stock.
- Restock on first transition to `cancelled` (idempotent); internal `stock_restored` flag never exposed in API.

## Non-Goals (v1)

- `GET /dashboard/insights`
- Payment gateways, shipping carriers, tax, coupons
- Server-side cart persistence
- Guest checkout
- FK from `order_line_items.product_id` → `products` (hard product delete allowed)
- `409` on product delete when referenced by orders
- Admin `POST /orders` (customers only)
- Enforced status state machine (free admin transitions)
- Versioned `/api/v1/orders` routes

## Frontend Contract (source of truth)

### `POST /orders` request

```json
{
  "shipping_address": "42 MG Road, Bengaluru, Karnataka 560001, India",
  "items": [
    { "product_id": 1, "quantity": 2 },
    { "product_id": 3, "quantity": 1 }
  ]
}
```

### `Order` response (POST 201, GET me/detail, PATCH 200)

```json
{
  "id": 10,
  "user_id": 2,
  "status": "pending",
  "total_amount": 8297.0,
  "shipping_address": "42 MG Road, Bengaluru, Karnataka 560001, India",
  "created_at": "2026-05-27T10:15:00Z",
  "updated_at": "2026-05-27T10:15:00Z",
  "items": [
    {
      "id": 101,
      "product_id": 1,
      "product_name": "Wireless Mouse",
      "quantity": 2,
      "unit_price": 799.0
    },
    {
      "id": 102,
      "product_id": 3,
      "product_name": "USB-C Hub",
      "quantity": 1,
      "unit_price": 2499.0
    }
  ]
}
```

### Status values (UI)

`pending`, `processing`, `shipped`, `delivered`, `cancelled`

### Errors

`{ "detail": "..." }` (422 may use validation array under `detail`).

## Data Model

### Table: `orders`

| Column | Type | Notes |
|--------|------|--------|
| `id` | INTEGER PK | |
| `user_id` | INTEGER FK → `users.id` | From authenticated user |
| `status` | VARCHAR | Default `pending`; one of five UI values |
| `total_amount` | NUMERIC(12,2) | `Σ(quantity × unit_price)` at checkout; server-only |
| `shipping_address` | TEXT | Required; min length 1 |
| `stock_restored` | BOOLEAN | Default `false`; **internal only**, not in API JSON |
| `created_at` | TIMESTAMPTZ | Set on insert |
| `updated_at` | TIMESTAMPTZ | Set on insert and every update |

### Table: `order_line_items`

| Column | Type | Notes |
|--------|------|--------|
| `id` | INTEGER PK | Exposed as `items[].id` |
| `order_id` | INTEGER FK → `orders.id` | ON DELETE CASCADE |
| `product_id` | INTEGER | Reference only; no FK to `products` in v1 |
| `product_name` | VARCHAR(255) | Snapshot at checkout |
| `quantity` | INTEGER | ≥ 1 |
| `unit_price` | NUMERIC(10,2) | Snapshot at checkout |

### Relationships

- `users` 1 — * `orders`
- `orders` 1 — * `order_line_items`
- No FK from line items to `products` (deleted products do not block orders or cancel PATCH)

### Request normalization

- Duplicate `product_id` in one `POST` body → **merge quantities** into a single line before validation.
- `items` must contain at least one entry; each `quantity` ≥ 1.

## API Endpoints & Authorization

All `/orders*` routes require `Authorization: Bearer`. None are on the public allowlist.

| Method | Path | Auth | Response |
|--------|------|------|----------|
| `POST` | `/orders` | Authenticated **customer** (non-admin) | `201` + `Order` |
| `GET` | `/orders/me` | Authenticated user | `Order[]`, newest first |
| `GET` | `/orders/{order_id}` | Order owner or admin | `Order` |
| `GET` | `/orders` | Admin | `Order[]`, newest first |
| `GET` | `/orders?status={status}` | Admin | Filtered `Order[]` |
| `GET` | `/orders?status={status}&limit={n}` | Admin | Filtered; `limit` capped at **100** |
| `PATCH` | `/orders/{order_id}/status` | Admin | `200` + `Order` |

### Role rules

- **`POST /orders`:** `get_current_user`; if `role == "admin"` → `403`. Missing/invalid token → `401`.
- **`GET /orders/me`:** any authenticated user; scope to `user_id == current_user.id`.
- **`GET /orders/{id}`:** if `order.user_id != current_user.id` and not admin → `403`; missing order → `404`.
- **Admin list/detail/PATCH:** `require_admin`.

### Request / response schemas

**`OrderCreate`**

| Field | Rule |
|-------|------|
| `shipping_address` | Required string, min length **1** |
| `items` | Array, min 1; `{ product_id: int, quantity: int ≥ 1 }` |

**`OrderStatusUpdate` (PATCH)**

```json
{ "status": "processing" }
```

`status` must be one of the five enum values. **Free transitions:** any status → any status. Same status as current → `200` (no-op for business logic except idempotent cancel restock rules).

### HTTP status mapping

| Situation | Code |
|-----------|------|
| Checkout success | `201` |
| Missing/invalid token | `401` |
| Admin `POST /orders` | `403` |
| Non-owner `GET /orders/{id}` | `403` |
| Order or product not found | `404` |
| Insufficient stock | `409` |
| Invalid body / invalid status query | `422` |
| Non-admin on admin routes | `403` |

Example stock conflict: `{ "detail": "Insufficient stock for product_id 1" }`

### Admin list: `limit`

- Optional query `limit`; when provided, cap at **100** (values > 100 treated as 100).
- When `limit` omitted, return **all** orders matching filter (no silent default cap).
- `?status=` must match an allowed status exactly; invalid value → `422`.

## Checkout Transaction Flow

Single database transaction per `POST /orders`:

1. Merge duplicate `product_id` lines (sum quantities).
2. Load all referenced products (use row-level lock on PostgreSQL where available).
3. For each line: if product missing → abort `404`; if `product.quantity < line.quantity` → abort `409`.
4. Snapshot `product_name` ← `product.name`, `unit_price` ← `product.price`.
5. Compute `total_amount` = sum of `quantity × unit_price`.
6. Insert `orders` row: `status=pending`, `user_id`, `shipping_address`, `stock_restored=false`.
7. Insert `order_line_items` rows.
8. Decrement each `products.quantity` by line quantity.
9. Commit; return `Order` with nested `items`.

**Invariants:** Stock is not decremented unless the order and line items are persisted in the same transaction.

## Cancel Restock Flow

On `PATCH` when `new_status == "cancelled"`:

- If order already `cancelled` → no restock (idempotent).
- If `stock_restored == true` → no restock (safety).
- Else: for each line item, if product still exists, add `line.quantity` back to `products.quantity`; if product deleted, **skip line** and log `structlog` warning; set `stock_restored = true`.
- Always update `status` and `updated_at`.

Non-cancel PATCH: update `status` and `updated_at` only; no inventory change.

## Architecture

```
app/routers/orders.py
  → OrderService
      → OrderRepository
      → ProductRepository (read + decrement / restock)
  → dependencies: get_current_user, require_admin
```

### New modules

| Path | Responsibility |
|------|----------------|
| `app/models/order.py` | `Order`, `OrderLineItem` ORM |
| `app/schemas/order.py` | Pydantic `OrderCreate`, `Order`, `OrderLineItem`, `OrderStatusUpdate` |
| `app/repositories/order_repository.py` | CRUD, list filters, transactional helpers |
| `app/services/order_service.py` | `checkout()`, `update_status()`, list/get with access rules |
| `app/routers/orders.py` | HTTP mapping, structlog |
| `alembic/versions/*_orders_tables.py` | Schema migration |

Wire `orders` router in `app/main.py`.

## Observability

Structured logs (structlog), per route:

- `order_checkout` — `user_id`, `order_id`, `outcome`, `latency_ms`
- `order_status_update` — `order_id`, `old_status`, `new_status`, `restocked` (bool)
- `order_list` / `order_get` — `user_id`, `order_id`, `outcome`

No tokens or passwords in logs.

## Testing Strategy

| Layer | Coverage |
|-------|----------|
| **Unit** | Line merge; `total_amount`; restock idempotency; exception mapping |
| **Integration** | Happy checkout 201 + snapshots + stock down; 409 oversell; 404 product; admin POST 403; owner/admin GET; admin list/status/limit; cancel restock once; deleted product skip on restock |
| **Contract** | `specs/003-orders-checkout/contracts/orders-api.yaml`; allowlist unchanged |

Use existing async client + JWT fixtures from `tests/conftest.py`.

## Artifact Locations (implementation phase)

| Artifact | Path |
|----------|------|
| Design (this doc) | `docs/superpowers/specs/2026-05-28-orders-checkout-design.md` |
| Feature spec | `specs/003-orders-checkout/spec.md` |
| Plan | `specs/003-orders-checkout/plan.md` |
| Data model | `specs/003-orders-checkout/data-model.md` |
| API contract | `specs/003-orders-checkout/contracts/orders-api.yaml` |
| Tasks | `specs/003-orders-checkout/tasks.md` |

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Contract source | React SPA examples | Frontend parity; no adapter layer |
| Approach | Single `OrderService` + one transaction | Matches auth/products; meets atomic stock rules |
| Snapshots | Mandatory on line items | Historical orders survive catalog price/name changes |
| Stock on checkout | Decrement atomically | Option A; prevent oversell |
| Stock on cancel | Restock once, idempotent | Option A; `stock_restored` internal |
| Admin status | Free transitions | Admin UI flexibility |
| Duplicate `product_id` in POST | Merge quantities | Safer cart payloads |
| `shipping_address` | Required, min length 1 | Match UI validation |
| Admin list `limit` | Optional, cap 100 | Align with admin product list pattern |
| Product delete | No FK; skip restock if gone | Catalog v1 hard delete; PATCH still succeeds |
| API nested key | `items` | SPA `MyOrders.jsx` / `OrderDetail.jsx` |
| Stock conflict HTTP | `409` | Distinct from `404` missing product |
| `stock_restored` | DB only | Not in `Order` JSON |

## Coordination with Product Catalog

- Catalog exposes live `price` / `quantity` for cart UI; checkout copies `name` and `price` into order lines.
- Product hard delete does not block orders or cancel PATCH.
- Phase 2 (optional): `409` on product delete when referenced by orders.
