# Quickstart: Product Catalog

**Feature**: `002-product-catalog`

## Prerequisites

- Python 3.12+ with backend venv active (`cd backend && source .venv/bin/activate`)
- Auth endpoints working (`POST /auth/login`, admin user seeded)
- Run backend CLI commands from the `backend/` directory
- Database URL configured:
  - **Dev (SQLite)**: default `ECOM_OPPO_SQLITE_DEV_DB_PATH=./data/ecom_oppo.db`
  - **PostgreSQL**: `ECOM_OPPO_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/ecom_oppo`

## 1. Apply schema

```bash
# After Alembic is wired for this feature
alembic upgrade head
```

For SQLite-only local bootstrap, restarting the app may run `create_all` including `products` until Alembic is the sole path.

## 2. Seed admin (if needed)

Admin is not created via register. Idempotent dev seed:

```bash
cd backend
# Optional: override default dev password (default: AdminPass123!)
export ECOM_OPPO_ADMIN_PASSWORD="your-admin-password"

python -m app.scripts.seed_admin
```

Then login:

```bash
curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@inventory.com","password":"AdminPass123!"}'
```

Save `access_token` from the response.

## 3. Public browse (no token)

```bash
# Full catalog
curl -s http://127.0.0.1:8000/products

# Search
curl -s "http://127.0.0.1:8000/products?search=widget"

# Detail
curl -s http://127.0.0.1:8000/products/1
```

## 4. Admin CRUD

```bash
export TOKEN="<access_token>"

# Create
curl -s -X POST http://127.0.0.1:8000/products \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Widget",
    "description": "A useful widget",
    "sku": "WGT-001",
    "price": 19.99,
    "quantity": 10,
    "category": "general",
    "image_url": ""
  }'

# Admin list (max 100)
curl -s "http://127.0.0.1:8000/products?limit=100" \
  -H "Authorization: Bearer $TOKEN"

# Update (full body)
curl -s -X PUT http://127.0.0.1:8000/products/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Widget Pro",
    "description": "Updated",
    "sku": "WGT-001",
    "price": 24.99,
    "quantity": 5,
    "category": "general",
    "image_url": ""
  }'

# Delete
curl -s -o /dev/null -w "%{http_code}\n" -X DELETE http://127.0.0.1:8000/products/1 \
  -H "Authorization: Bearer $TOKEN"
# Expect 204
```

## 5. Run tests

```bash
pytest tests/integration/test_products.py tests/contract/test_products_contract.py -v
pytest --cov=app --cov-report=term-missing
```

## Expected error samples

| Case | Status | Body shape |
|------|--------|------------|
| No token on POST | 401 | `{ "detail": "..." }` |
| Customer token on POST | 403 | `{ "detail": "..." }` |
| Duplicate SKU | 409 | `{ "detail": "..." }` |
| Unknown id | 404 | `{ "detail": "..." }` |
| Invalid payload | 422 | `{ "detail": [ ... ] }` |

## Frontend alignment

- Base URL: `VITE_API_URL` (default `http://127.0.0.1:8000`)
- Paths: `/products` only (no `/api/v1` prefix)
- List response: plain JSON array, not `{ data: [...] }`
