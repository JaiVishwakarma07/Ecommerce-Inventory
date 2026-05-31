# Performance Baselines (pre-optimization)

Date: 2026-06-01

**Run config:** `locust -f tests/locustfile.py --headless -u 10 -r 2 --run-time 30s --host http://localhost:8000`

**Scope:** All canonical `/auth`, `/products`, and `/orders` endpoints — one endpoint per run, in sequence. No `/api/v1/auth/*` routes.

**Run all:** `powershell -File tests/run_perf_baselines.ps1`

Set a single target: `$env:LOCUST_TARGET = "auth-login"` (see `tests/locustfile.py` for values).

---

## Auth

### POST /auth/register

P50: 3ms | P95: 220ms | P99: 2500ms | RPS: 7.11

**Notes:** 208 requests; 203 HTTP 429 (5 req/min IP rate limit).

### POST /auth/login

P50: 3ms | P95: 530ms | P99: 2300ms | RPS: 7.03

**Notes:** 205 requests; 200 HTTP 429. Run after 65s cooldown following register burst.

### GET /auth/me

P50: 7ms | P95: 18ms | P99: 2100ms | RPS: 6.87

**Notes:** 201 requests; 0 failures. Run first in auth sequence before login rate-limit window fills.

---

## Products

### GET /products

P50: 9ms | P95: 39ms | P99: 2100ms | RPS: 6.96

**Notes:** 203 requests; 0 failures. Public list.

### GET /products/{product_id}

P50: 7ms | P95: 20ms | P99: 2100ms | RPS: 6.74

**Notes:** 196 requests; 0 failures.

### POST /products

P50: 22ms | P95: 87ms | P99: 2100ms | RPS: 6.80

**Notes:** 199 requests; 0 failures. Admin auth; unique SKU per request.

### PUT /products/{product_id}

P50: 23ms | P95: 110ms | P99: 2100ms | RPS: 6.46

**Notes:** 189 requests; 0 failures. Dedicated product created in setup.

### DELETE /products/{product_id}

P50: 17ms | P95: 77ms | P99: 280ms | RPS: 6.46

**Notes:** 189 requests; 0 failures. Create-then-delete per request (setup excluded from stats).

---

## Orders

### POST /orders

P50: 9ms | P95: 51ms | P99: 2100ms | RPS: 6.77

**Notes:** 198 requests; 192 HTTP 409 (insufficient stock after repeated checkout). Customer auth.

### GET /orders/me

P50: 12ms | P95: 53ms | P99: 2100ms | RPS: 7.00

**Notes:** 205 requests; 0 failures. Customer auth.

### GET /orders/{order_id}

P50: 11ms | P95: 81ms | P99: 2100ms | RPS: 6.21

**Notes:** 181 requests; 0 failures. Uses existing order from customer history or setup checkout.

### GET /orders

P50: 11ms | P95: 53ms | P99: 2100ms | RPS: 6.87

**Notes:** 201 requests; 0 failures. Admin list.

### PATCH /orders/{order_id}/status

P50: 28ms | P95: 150ms | P99: 2200ms | RPS: 6.45

**Notes:** 188 requests; 0 failures. Admin auth; patches setup order to `processing`.

---

## Summary

| Endpoint | P50 | P95 | P99 | RPS | Failures |
|----------|-----|-----|-----|-----|----------|
| POST /auth/register | 3ms | 220ms | 2500ms | 7.11 | 203 (429) |
| POST /auth/login | 3ms | 530ms | 2300ms | 7.03 | 200 (429) |
| GET /auth/me | 7ms | 18ms | 2100ms | 6.87 | 0 |
| GET /products | 9ms | 39ms | 2100ms | 6.96 | 0 |
| GET /products/{product_id} | 7ms | 20ms | 2100ms | 6.74 | 0 |
| POST /products | 22ms | 87ms | 2100ms | 6.80 | 0 |
| PUT /products/{product_id} | 23ms | 110ms | 2100ms | 6.46 | 0 |
| DELETE /products/{product_id} | 17ms | 77ms | 280ms | 6.46 | 0 |
| POST /orders | 9ms | 51ms | 2100ms | 6.77 | 192 (409) |
| GET /orders/me | 12ms | 53ms | 2100ms | 7.00 | 0 |
| GET /orders/{order_id} | 11ms | 81ms | 2100ms | 6.21 | 0 |
| GET /orders | 11ms | 53ms | 2100ms | 6.87 | 0 |
| PATCH /orders/{order_id}/status | 28ms | 150ms | 2200ms | 6.45 | 0 |

---

## Optimization Scheme (no app code changes)

**Constraint:** No changes to `backend/` or `frontend/` application code.

### What skewed these baselines

| Factor | Effect |
|--------|--------|
| Auth rate limit (5 req/min per IP) | Register/login P95/P99 inflated by HTTP 429 |
| Stock depletion on checkout | POST /orders returns HTTP 409 after stock exhausted |
| SQLite + single uvicorn worker | P99 tails on concurrent reads/writes |
| Sequential suite | Auth-me run first; 65s cooldown after auth-login |

### Test infrastructure

| File | Purpose |
|------|---------|
| `tests/locustfile.py` | Single-endpoint profiles via `LOCUST_TARGET` |
| `tests/run_perf_baselines.ps1` | Runs all 13 endpoints in sequence |

### Out of scope (would require app code)

- Rate-limit tuning, bcrypt/JWT optimization, DB indexes, connection pooling
- `/api/v1/auth/*` routes (not part of this API surface)
