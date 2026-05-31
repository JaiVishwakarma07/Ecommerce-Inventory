## Why

Users can currently register and persist accounts, but they cannot authenticate with those stored credentials or fetch their own authenticated profile. Adding login and current-user endpoints completes the first usable auth loop by verifying database-backed users, issuing JWTs, and resolving the authenticated user from a bearer token.

## What Changes

- Add `POST /auth/login` under the canonical `/auth/*` route set.
- Add `POST /api/v1/auth/login-form` for form-encoded username/password login compatibility.
- Add `GET /api/v1/auth/me` to return the current authenticated user from the bearer token.
- Verify credentials against the SQLite-backed `users` table using normalized email lookup and bcrypt password verification.
- Return a signed JWT access token and user view on successful login.
- Return `401 Unauthorized` for unknown email or wrong password without revealing which field failed.
- Return `401 Unauthorized` for missing, invalid, or expired bearer tokens on `/api/v1/auth/me`.
- Preserve the existing `/auth/register` contract and database persistence foundation.

## Capabilities

### New Capabilities
- `auth-login`: Database-backed user login using stored credentials, JWT access token issuance, form login compatibility, and current-user lookup.

### Modified Capabilities
- None.

## Impact

- Affected code: `app/schemas/auth.py`, `app/services/auth_service.py`, `app/routers/auth.py`, auth dependencies/security helpers, and auth integration/contract/unit tests.
- Affected APIs: adds `POST /auth/login`, `POST /api/v1/auth/login-form`, and `GET /api/v1/auth/me`.
- Dependencies: no new runtime dependencies expected; uses existing SQLite, repository, bcrypt, and JWT utilities.
- Systems: relies on existing `users` table, DB session dependency, and password hashing from registration.
