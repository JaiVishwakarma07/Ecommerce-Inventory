# Quickstart: AI Shopping Assistant

**Feature**: `004-ai-shopping-assistant`

## Prerequisites

- Backend running (`cd backend && uvicorn app.main:app --reload --port 8000`)
- Product catalog seeded with sample SKUs
- Auth working (`POST /auth/register`, `POST /auth/login`)
- LLM env vars set in `backend/.env` (never commit secrets):

```env
LLM_API_KEY=your-groq-api-key
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile
```

- Install new runtime dependency after implementation:

```bash
cd backend
pip install openai
```

## 1. Register and login as customer

```bash
curl -s -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "shopper@example.com",
    "full_name": "Shopper",
    "password": "StrongPass123!"
  }'
```

Save `access_token` from the response.

## 2. Assistant query (customer)

```bash
export TOKEN="<customer_access_token>"

curl -s -X POST http://127.0.0.1:8000/assistant/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "laptop under 10000"}'
```

Expected `200`:

```json
{
  "answer": "Found 2 products matching your request.",
  "products": [ /* up to 5 Product objects */ ]
}
```

Verify every `products[].id` exists:

```bash
curl -s http://127.0.0.1:8000/products/<id>
```

## 3. Authorization checks

```bash
# No token → 401
curl -s -X POST http://127.0.0.1:8000/assistant/query \
  -H "Content-Type: application/json" \
  -d '{"query": "widget"}'

# Admin token → 403
curl -s -X POST http://127.0.0.1:8000/assistant/query \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "widget"}'
```

## 4. Validation and failure cases

```bash
# Empty query → 422
curl -s -X POST http://127.0.0.1:8000/assistant/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "   "}'

# Missing LLM_API_KEY → 503
# (unset env and restart server)
```

## 5. Frontend smoke test

1. Start frontend (`cd frontend && npm run dev`).
2. Register/login as customer.
3. Open `http://localhost:5173/products`.
4. Use **Ask AI** input with `laptop under 10000`.
5. Confirm answer text and product cards render.

## 6. Run tests

```bash
cd backend
pytest ../tests/integration/test_assistant.py ../tests/unit/test_assistant_service.py ../tests/contract/test_assistant_contract.py -v
```

Integration tests mock the LLM client — no live Groq key required in CI.

## Rate limit

Default: **10 requests/minute** per customer on `POST /assistant/query`. Exceeding returns **429** with `{ "detail": "Rate limit exceeded" }`.
