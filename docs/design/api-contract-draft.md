GET  /                         → { status, service }

POST /auth/register            → { access_token, token_type, user }
POST /auth/login               → { access_token, token_type, user }
POST /auth/login-form          → { access_token, token_type, user }   # swagger/oauth helper, not used by UI
GET  /auth/me                  → { id, email, full_name, role, created_at }

GET  /products                 → Product[]
GET  /products?search=...      → Product[]
GET  /products?category=...    → Product[]
GET  /products/{product_id}    → Product
POST /products                 → Product                              # admin only
PUT  /products/{product_id}    → Product                              # admin only
DELETE /products/{product_id}  → 204 No Content                       # admin only

POST /orders                   → Order                                # customer only
GET  /orders/me                → Order[]                              # logged-in user
GET  /orders/{order_id}        → Order                                # owner or admin
GET  /orders                   → Order[]                              # admin only
GET  /orders?status=pending    → Order[]                              # admin only
PATCH /orders/{order_id}/status → Order                               # admin only; body { status }

GET  /dashboard/insights       → {
                                  summary,
                                  orders_by_status,
                                  orders_over_time,
                                  top_products,
                                  inventory_by_category,
                                  low_stock
                                }                                     # admin only