# Implementation Notes (TDD)

Task: `post-auth-register`

## Key decisions made during test-driven development

1. **Start from integration behavior, not internals**
   - Wrote endpoint-first tests for `POST /auth/register` and implemented the minimum code to satisfy them.

2. **Use in-memory ASGI testing instead of network calls**
   - Switched to `httpx.ASGITransport(app=app)` so tests run entirely in process and avoid sandbox network restrictions.

3. **Preserve canonical route while supporting versioned alias**
   - Kept `/auth/register` as canonical behavior from the approved brainstorm.
   - Also mounted `/api/v1/auth` for compatibility with project routing conventions.

4. **Force role on self-registration**
   - Registration flow ignores any incoming role and always persists/returns `role="customer"`.

5. **Security implementation corrected after review**
   - Replaced SHA-256 password logic with bcrypt-based hashing/verification.
   - Replaced custom token string with signed JWT containing `sub`, `iat`, and `exp` claims.

6. **Introduce dependency-driven endpoint wiring**
   - Removed router-level singleton service/repository usage.
   - Added dependency providers so the register flow is request-safe and test-isolated.

7. **Add baseline abuse protection**
   - Added in-memory rate limiting for register attempts.
   - Rate-limit key now prefers `x-forwarded-for` first IP with client-host fallback.

8. **Harden request validation and contracts**
   - Added explicit size limits for `full_name` and `password`.
   - Added password complexity validation (lowercase, uppercase, number, symbol).

9. **Expand tests to match design artifacts**
   - Added contract tests for request/response shape and sensitive-field exclusion.
   - Added unit tests for password hashing and JWT claim structure.
   - Added integration regression for case-insensitive duplicate email detection.

10. **Reset mutable state per test**
    - Added `tests/conftest.py` fixture to reset repository and rate limiter each test run for deterministic outcomes.
