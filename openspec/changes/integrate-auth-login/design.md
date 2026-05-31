## Context

Registration now persists users in SQLite and stores bcrypt password hashes through the existing auth repository and service layers. The missing pieces are database-backed login and current-user lookup: a user needs to authenticate with stored credentials, receive a bearer JWT, and use that token to fetch their own public profile.

## Goals / Non-Goals

**Goals:**
- Add canonical `POST /auth/login` endpoint.
- Add `POST /api/v1/auth/login-form` for form-encoded login clients that submit `username` and `password`.
- Add `GET /api/v1/auth/me` for bearer-token authenticated current-user lookup.
- Use existing SQLite-backed `UserRepository.get_by_email(...)` for normalized email lookup.
- Verify submitted password using the existing password verification helper.
- Return the same token/user response contract as registration on success.
- Return `401 Unauthorized` for unknown email and wrong password without credential-enumeration hints.
- Return `401 Unauthorized` for missing, invalid, expired, or user-not-found bearer token on `/api/v1/auth/me`.
- Add focused tests for success, unknown email, wrong password, case-insensitive email lookup, form login, current-user lookup, invalid token behavior, and response shape.

**Non-Goals:**
- Add refresh tokens, sessions, logout, or token revocation.
- Add canonical `/auth/me`; this phase adds only the requested versioned `GET /api/v1/auth/me`.
- Change `/auth/register` behavior or route canonicalization.
- Add new database tables; this uses the existing `users` table only.

## Decisions

1. **Reuse register response shape for login**
   - **Why:** Keeps auth token responses consistent for clients and avoids duplicate response schemas.
   - **Alternative considered:** A separate `LoginResponse`; rejected unless the shape diverges later.

2. **Add a dedicated `LoginRequest` schema**
   - **Why:** Login requires only `email` and `password`, unlike register which also requires `full_name`.
   - **Alternative considered:** Reusing `RegisterRequest`; rejected because it would incorrectly require `full_name`.

3. **Use one generic invalid-credentials error**
   - **Why:** Unknown email and wrong password must both return `401` with the same public message to avoid account enumeration.
   - **Alternative considered:** Return `404` for unknown user or distinct wrong-password errors; rejected for security.

4. **Keep authentication business logic in `AuthService`**
   - **Why:** Router should handle HTTP concerns only; service should own credential verification and token creation.
   - **Alternative considered:** Verify password directly in router; rejected because it mixes HTTP and domain logic.

5. **Treat `login-form` as a versioned compatibility endpoint**
   - **Why:** Some clients and Swagger/OAuth-style flows use form-encoded `username`/`password`; keeping it under `/api/v1/auth/login-form` avoids changing canonical JSON login behavior.
   - **Alternative considered:** Accept both JSON and form payloads on `/auth/login`; rejected because it makes request parsing ambiguous.

6. **Decode bearer token for `/api/v1/auth/me` and reload user from DB**
   - **Why:** Token proves the subject, but DB lookup ensures the returned user still exists and reflects current persisted data.
   - **Alternative considered:** Return only JWT claims; rejected because it would not return the canonical public user view.

## Risks / Trade-offs

- **[Credential enumeration risk]** -> Mitigation: return identical `401` response for unknown email and wrong password.
- **[Timing differences between unknown user and wrong password]** -> Mitigation: acceptable for this phase; consider dummy hash verification later if threat model requires it.
- **[Duplicate token response construction]** -> Mitigation: extract a small private service helper if register/login response creation duplicates too much.
- **[Rate limiting scope]** -> Mitigation: reuse or add auth login rate limiting in implementation to prevent brute force attempts.
- **[Bearer token parsing errors]** -> Mitigation: map all token decode, expiry, missing subject, and missing user cases to the same `401` response.

## Migration Plan

1. Add `LoginRequest` schema.
2. Add `InvalidCredentialsError` domain error.
3. Add `AuthService.login_user(db, payload)` using repository lookup and password verification.
4. Add bearer token decoding/current-user service behavior for `GET /api/v1/auth/me`.
5. Add `POST /auth/login`, `POST /api/v1/auth/login-form`, and `GET /api/v1/auth/me` routes with response models and `401` mapping.
6. Add contract/integration/unit tests for JSON login, form login, and current-user behavior.
7. Verify existing register tests still pass.

## Open Questions

- Should login rate limiting reuse the current register limiter or get a separate limiter/key?
- Should failed login attempts emit a dedicated structured log/metric counter?
