# Quickstart: Orders & Checkout

**Feature**: `003-orders-checkout`

## Prerequisites

- Python 3.12+ with backend venv active (`cd backend && source .venv/bin/activate`)
- Auth and product catalog implemented
- Run backend CLI commands from the `backend/` directory
- Customer user (register via `POST /auth/register`) and admin (`python -m app.scripts.seed_admin`)
- Products seeded (`python -m app.scripts.seed_products` or manual admin create)

## 1. Apply schema

```bash
alembic upgrade head
```

Restart app if using SQLite `create_all` bootstrap until Alembic is applied.

## 2. Obtain tokens

**Customer** (register or use existing):

```bash
curl -s -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"buyer@example.com","password":"BuyerPass123!","full_name":"Buyer"}'
```

**Admin**:

```bash
curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@inventory.com","password":"AdminPass123!"}'
```

```bash
export CUSTOMER_TOKEN="<customer access_token>"
export ADMIN_TOKEN="<admin access_token>"
```

## 3. Checkout (customer)

```bash
curl -s -X POST http://127.0.0.1:8000/orders \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "shipping_address": "42 MG Road, Bengaluru, Karnataka 560001, India",
    "items": [
      { "product_id": 1, "quantity": 2 },
      { "product_id": 2, "quantity": 1 }
    ]
  }'
```

Expect `201` with `id`, `status: "pending"`, `items[].product_name`, `items[].unit_price`, and `total_amount`.

## 4. My orders (customer)

```bash
curl -s http://127.0.0.1:8000/orders/me \
  -H "Authorization: Bearer $CUSTOMER_TOKEN"

curl -s http://127.0.0.1:8000/orders/1 \
  -H "Authorization: Bearer $CUSTOMER_TOKEN"
```

## 5. Admin list and status update

```bash
# All orders
curl -s http://127.0.0.1:8000/orders \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Pending only, max 100
curl -s "http://127.0.0.1:8000/orders?status=pending&limit=100" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Mark processing
curl -s -X PATCH http://127.0.0.1:8000/orders/1/status \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"processing"}'

# Cancel (restocks inventory once)
curl -s -X PATCH http://127.0.0.1:8000/orders/1/status \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"cancelled"}'
```

## 6. Error spot checks

```bash
# No token → 401
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/orders/me

# Admin checkout → 403
curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8000/orders \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"shipping_address":"x","items":[{"product_id":1,"quantity":1}]}'

# Oversell → 409
curl -s -X POST http://127.0.0.1:8000/orders \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"shipping_address":"x","items":[{"product_id":1,"quantity":99999}]}'
```

## 7. Run tests

```bash
pytest tests/integration/test_orders.py \
  tests/contract/test_orders_contract.py \
  tests/unit/test_order_service.py \
  tests/contract/test_route_access_policy.py -q
```

Coverage target: ≥80% on new order modules.
