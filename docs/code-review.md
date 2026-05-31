# Code Review — `backend/app/` vs Specs & Rules

**Date:** 2026-06-01  
**Last updated:** 2026-06-01 (post-remediation)  
**Scope:** All modules under `backend/app/`  
**References:** `specs/user-authentication/`, `specs/002-product-catalog/`, `specs/003-orders-checkout/`, `.cursor/rules/common/project.mdc`, `.cursor/rules/common-security.mdc`

---

## Executive Summary

Initial review found a **checkout stock race** (overselling / negative inventory), missing **`POST /auth/login-form`** on the canonical path, and hardcoded CORS. **Critical and selected important items are fixed** with minimal diffs. Remaining items are documented deferrals or accepted deviations.

**Current assessment:** **Ready to merge** for v1 dev scope, with known deferrals below for production hardening.

---

## Remediation Log

| ID | Issue | Status | Change |
|----|-------|--------|--------|
| C1 | Checkout race / overselling | **Fixed** | `ProductRepository.decrement_quantity_if_available()` — conditional `UPDATE` with `quantity >= :qty`; checkout rolls back on failure (`product_repository.py`, `order_service.py`) |
| C2 | Negative stock allowed | **Fixed** | Same atomic decrement; no decrement when insufficient stock |
| I1 | Missing `POST /auth/login-form` | **Fixed** | `versioned_auth_router` mounted under `/auth` in `main.py` |
| I2 | Auth `{error}` vs `{detail}` | **Accepted** | Project uses `{detail}` consistently on products/orders; auth contract deviation documented — no envelope refactor |
| I3 | Route versioning vs `project.mdc` | **Accepted** | Feature specs intentionally use bare `/products`, `/orders`; auth has both `/auth/*` and `/api/v1/auth/*` |
| I4 | Rate limit all endpoints | **Deferred** | In-memory limiter on register/login only; distributed/wider scope is production work |
| I5 | Auth p50/p95/p99 metrics | **Deferred** | Counters only; external metrics via Locust/docs |
| I6 | Mixed transaction ownership | **Deferred** | Refactor out of scope for minimal fix |
| I7 | CORS hardcoded | **Fixed** | `ECOM_OPPO_CORS_ORIGINS` in `config.py` (defaults include 5173 + 5174); `main.py` reads `settings.cors_origin_list` |
| I8 | Default seed password | **Deferred** | Dev script; overridable via `ECOM_OPPO_ADMIN_PASSWORD` |
| Minor | `response_model`, structlog in scripts, lifespan | **Deferred** | Non-blocking |

**Verification:** `pytest tests/integration/test_orders.py tests/integration/test_auth_login.py` — 42 passed.

---

## Strengths (unchanged)

- Clean **routers → services → repositories** layout; async SQLAlchemy throughout.
- Auth: bcrypt, JWT, DB-backed roles, no passwords in responses, register/login rate limits.
- Products: public GET, admin CRUD, SKU conflict → 409, plain array responses.
- Orders: snapshots, `items` key, cancel restock idempotency, customer/admin role gates.
- Structured logging via `structlog` on request paths.

---

## Resolved Issues (detail)

### C1/C2 — Atomic stock decrement

**Before:** Read-check-write in `adjust_quantity` allowed concurrent checkouts to oversell.

**After:**

```python
# product_repository.py
update(Product)
    .where(Product.id == product_id, Product.quantity >= quantity)
    .values(quantity=Product.quantity - quantity)
```

Checkout calls `decrement_quantity_if_available` per line; any failure raises `InsufficientStockError` and rolls back the whole transaction (no partial order).

---

### I1 — `POST /auth/login-form`

**Before:** Only `/api/v1/auth/login-form`.

**After:** Also available at `/auth/login-form` via router mount in `main.py`.

---

### I7 — CORS

**Before:** Hardcoded `5173` only.

**After:** `ECOM_OPPO_CORS_ORIGINS` comma-separated list; defaults include `5173` and `5174`.

---

## Open / Deferred Items

### I4 — Rate limiting scope

Only auth register/login limited. Checkout and admin writes unprotected. Recommend Redis-backed limiter before production.

### I5 — Auth latency percentiles

Spec mentions p50/p95/p99; app tracks counters only. Use Locust baselines in `docs/performance.md` for load metrics.

### I6 — Repository commit boundaries

Product/user repos commit internally; checkout commits in service. Works but inconsistent for future multi-entity transactions.

### I8 — Seed script default password

`seed_admin.py` ships a dev default; must override in shared environments.

### Minor

- `DELETE /products/{id}` and `GET /` lack explicit `response_model`
- Register password complexity stricter than auth contract minimum
- Seed/cleanup scripts use `print()` not structlog

---

## Spec & Rule Alignment Matrix (updated)

| Requirement | Status | Notes |
|-------------|--------|-------|
| FR-006 atomic checkout | **Pass** | Conditional decrement + rollback |
| Auth `/auth/login-form` | **Pass** | Mounted under `/auth` |
| Auth error envelope | **Accepted** | `{detail}` matches products/orders |
| Password never in response | **Pass** | |
| DB-backed role checks | **Pass** | |
| Product / order contracts | **Pass** | |
| Rate limit all endpoints | **Deferred** | Auth only |
| Version all routes `/api/v1/` | **Accepted** | Feature specs override for catalog/orders |
| CORS configurable | **Pass** | Env-driven with dev defaults |

---

## Assessment

**Ready to merge?** **Yes** (v1 dev / demo scope)

**Reasoning:** Blocking checkout integrity and auth route gaps are fixed with minimal, tested changes. Remaining items are production-hardening (distributed rate limits, metrics pipeline, repository transaction refactor) or intentional contract deviations documented above.

---

## Review Method

- Initial review: all `backend/app/` modules vs specs and `.cursor/rules/`
- Remediation: minimal targeted fixes + integration test verification
- Load-test note: run `python -m app.scripts.cleanup_locust_data` after Locust suites on shared dev DBs
