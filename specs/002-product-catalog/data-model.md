# Data Model: Product Catalog

**Feature**: `002-product-catalog`  
**Date**: 2026-05-27

## Entity: Product

Represents a sellable inventory item in the storefront and admin UI.

### Table: `products`

| Column | Type | Nullable | Default | Constraints |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | auto | PRIMARY KEY |
| `name` | VARCHAR(255) | NO | — | non-empty |
| `description` | TEXT | NO | — | empty string allowed |
| `sku` | VARCHAR(255) | NO | — | UNIQUE, indexed |
| `price` | NUMERIC(10,2) | NO | — | ≥ 0 |
| `quantity` | INTEGER | NO | — | ≥ 0 |
| `category` | VARCHAR(100) | NO | — | non-empty |
| `image_url` | VARCHAR(2048) | NO | `''` | never NULL |
| `created_at` | TIMESTAMPTZ | NO | now() | set on insert |
| `updated_at` | TIMESTAMPTZ | NO | now() | set on insert/update |

### Indexes

- `uq_products_sku` — UNIQUE (`sku`)
- Optional: index on `lower(name)`, `lower(category)` if search latency requires (defer until measured)

### Relationships (v1)

- None enforced at DB level.
- Future `order_line_items` may reference `product_id` optionally; v1 delete does not FK-block.

### Validation rules (application layer)

| Field | Rule |
|-------|------|
| `name` | 1–255 chars |
| `description` | required; may be `""` |
| `sku` | 1–255 chars; unique |
| `price` | ≥ 0; max 2 decimal places |
| `quantity` | integer ≥ 0 |
| `category` | 1–100 chars |
| `image_url` | string; default `""`; never expose `null` |

### State transitions

- **Create**: insert row; set `created_at`, `updated_at`.
- **Update (PUT)**: replace all mutable fields; bump `updated_at`.
- **Delete**: hard delete row (no `deleted_at`).

### API projection

Response includes all columns as JSON:

- `id`, `name`, `description`, `sku`, `price` (number), `quantity`, `category`, `image_url`, `created_at`, `updated_at` (ISO-8601 strings).

Request body (POST/PUT) omits `id` and timestamps; server assigns on create.
