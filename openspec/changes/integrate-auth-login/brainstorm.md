# Brainstorm Output: Auth Login, Login Form, and Current User

## Scope Confirmation

- Implement database-backed login using the existing SQLite `users` table.
- Extend existing files where they already exist; do not create new modules unless required by tests or framework needs.
- Add canonical JSON login at `POST /auth/login`.
- Add form login at `POST /api/v1/auth/login-form`.
- Add current-user lookup at `GET /auth/me`.
- Do not add `GET /api/v1/auth/me` in this phase.
- Do not add refresh tokens, sessions, logout, token revocation, or password reset.
- Keep simple FastAPI-compatible error bodies using `{ "detail": "..." }`.

## Locked Decisions

### Login Form Fields

`POST /api/v1/auth/login-form` will use standard OAuth2-style form fields:

- `username=<email>`
- `password=<password>`

The service will treat `username` as the user's email.

### Current User Response Shape

`GET /auth/me` returns the public user object directly:

```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "User Name",
  "role": "customer",
  "created_at": "..."
}
```

It does not return `access_token`, `token_type`, or a nested `user` wrapper because `/auth/me` does not issue a token.

### Error Shape

Do not introduce the structured error envelope yet. The frontend reads:

```python
err.response?.data?.detail
```

Use simple detail responses:

- Login unknown email or wrong password: `{ "detail": "Invalid credentials" }`
- `/auth/me` missing, invalid, expired token, or missing user: `{ "detail": "Not authenticated" }`

## Selected Approach

**Chosen:** Approach 1 (Extend Existing Auth Router/Service)

Rationale:
- Lowest implementation risk.
- Keeps all auth behavior in existing files where practical.
- Avoids new abstractions before additional protected ecommerce endpoints exist.
- Reuses current SQLite session dependency, repository, password hashing, and JWT utilities.

## Design Section 1: Architecture and Components

### `app/schemas/auth.py`

- Add `LoginRequest` with:
  - `email`
  - `password`
- Reuse `RegisterResponse` for login token response.
- Reuse `RegisterUserResponse` as the public `/auth/me` response model.

### `app/repositories/user_repository.py`

- Keep `get_by_email(db, email)` for login.
- Add `get_by_id(db, user_id)` for `/auth/me`.

### `app/core/security.py`

- Keep `create_access_token(subject)`.
- Add token decode/subject extraction helper for bearer-token flows.

### `app/services/auth_service.py`

- Add `InvalidCredentialsError`.
- Add `UnauthenticatedError`.
- Add `login_user(db, payload)` for JSON login.
- Add current-user lookup behavior for `/auth/me`.
- Reuse existing password verification and token creation helpers.

### `app/routers/auth.py`

- Add `POST /auth/login`.
- Add `POST /api/v1/auth/login-form`.
- Add `GET /auth/me`.
- Preserve existing `POST /auth/register`.
- Use simple `HTTPException` detail responses for auth failures.

## Design Section 2: Data Flow, Errors, and Tests

### JSON Login Flow

1. Client posts `{ email, password }` to `POST /auth/login`.
2. Router resolves `AsyncSession` and `AuthService`.
3. Service normalizes email and loads user with `UserRepository.get_by_email`.
4. Service verifies submitted password against stored bcrypt hash.
5. On success, service returns signed JWT token response using the same shape as register.

### Form Login Flow

1. Client posts form data to `POST /api/v1/auth/login-form`.
2. Router reads `username` as email and `password` as password.
3. Router maps form data into the same login flow.
4. Response shape matches JSON login.

### Current User Flow

1. Client calls `GET /auth/me` with `Authorization: Bearer <token>`.
2. Router/service extracts and decodes token subject.
3. Repository loads user by id.
4. Endpoint returns public user object directly.

### Error Handling

- Unknown email and wrong password both return `401` with `Invalid credentials`.
- Missing token, malformed token, expired token, missing subject, or deleted user all return `401` with `Not authenticated`.
- Responses must never include `password` or `password_hash`.

### Test Strategy

Add tests for:

- `LoginRequest` accepts `email` and `password`.
- JSON login succeeds after registration.
- JSON login is case-insensitive for email.
- Unknown email returns `401`.
- Wrong password returns `401`.
- Login responses exclude `password` and `password_hash`.
- Form login succeeds with `username=<email>` and `password=<password>`.
- Form login invalid credentials return `401`.
- `GET /auth/me` succeeds with valid bearer token.
- `GET /auth/me` returns public user object directly.
- `GET /auth/me` returns `401` for missing token.
- `GET /auth/me` returns `401` for invalid token.
- Existing register, database, and security tests continue passing.

## Out of Scope

- `GET /api/v1/auth/me`
- `/auth/logout`
- refresh tokens
- password reset
- role-based authorization middleware
- session tables or new auth-related database tables

## Success Criteria

- `POST /auth/login` works with SQLite-backed users.
- `POST /api/v1/auth/login-form` works with OAuth2-style `username` field.
- `GET /auth/me` returns public user profile from bearer token.
- Invalid auth failures use compatible `{ "detail": "..." }` responses.
- No sensitive password fields appear in responses.
- Existing registration behavior remains unchanged.
