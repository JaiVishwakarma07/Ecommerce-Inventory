## 1. Login schema and contract tests

- [x] 1.1 Add failing contract tests for `LoginRequest` accepting `email` and `password` only.
- [x] 1.2 Add failing contract tests that successful login response contains `access_token`, `token_type`, and `user`.
- [x] 1.3 Add failing contract tests that login response excludes `password` and `password_hash`.
- [x] 1.4 Add failing contract tests for form login accepting `username` and `password`.
- [x] 1.5 Add failing contract tests for current-user response excluding password fields.
- [x] 1.6 Implement `LoginRequest` and current-user response schema reuse in `app/schemas/auth.py`.

## 2. Auth service login behavior

- [x] 2.1 Add failing unit/integration test for `AuthService.login_user` returning token response for valid credentials.
- [x] 2.2 Add failing test for unknown email raising generic invalid credentials error.
- [x] 2.3 Add failing test for wrong password raising the same generic invalid credentials error.
- [x] 2.4 Add failing test for current-user lookup returning public user view for valid token subject.
- [x] 2.5 Add failing test for invalid token subject or missing user raising unauthenticated error.
- [x] 2.6 Implement `InvalidCredentialsError`, `UnauthenticatedError`, `AuthService.login_user(db, payload)`, and current-user lookup behavior.
- [x] 2.7 Extract shared token/user response construction if needed to avoid register/login duplication.

## 3. Login router endpoint

- [x] 3.1 Add failing integration test for `POST /auth/login` success after registering a user.
- [x] 3.2 Add failing integration test for case-insensitive login email lookup.
- [x] 3.3 Add failing integration test for unknown email returning `401`.
- [x] 3.4 Add failing integration test for wrong password returning `401`.
- [x] 3.5 Add failing integration test for `POST /api/v1/auth/login-form` success with form-encoded `username` and `password`.
- [x] 3.6 Add failing integration test for `POST /api/v1/auth/login-form` invalid credentials returning `401`.
- [x] 3.7 Implement `POST /auth/login` and `POST /api/v1/auth/login-form` in `app/routers/auth.py` with response models and generic `401` mapping.

## 4. Current-user endpoint

- [x] 4.1 Add failing integration test for `GET /api/v1/auth/me` returning current user with a valid bearer token.
- [x] 4.2 Add failing integration test for `GET /api/v1/auth/me` returning `401` without `Authorization` header.
- [x] 4.3 Add failing integration test for `GET /api/v1/auth/me` returning `401` with invalid bearer token.
- [x] 4.4 Add failing integration test for `GET /api/v1/auth/me` excluding `password` and `password_hash`.
- [x] 4.5 Implement bearer-token dependency and `GET /api/v1/auth/me` route.

## 5. Observability and abuse protection

- [x] 5.1 Add structured success/failure login logs with no raw password or password hash fields.
- [x] 5.2 Add login attempt metric counters for success and invalid credentials.
- [x] 5.3 Add or reuse rate limiting for `POST /auth/login` and `POST /api/v1/auth/login-form` to reduce brute-force risk.
- [x] 5.4 Add structured current-user logs for success and unauthorized outcomes.

## 6. Verification

- [x] 6.1 Run login/current-user contract, integration, and auth service tests.
- [x] 6.2 Run existing register, database, and security tests to verify no regressions.
- [x] 6.3 Smoke-test live `POST /auth/login`, `POST /api/v1/auth/login-form`, and `GET /api/v1/auth/me` with a persisted user using the local SQLite-backed app.
