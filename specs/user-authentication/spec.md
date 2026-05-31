# Feature Specification: User Authentication

**Feature Branch**: `user-authentication`

**Created**: 2026-05-26

**Status**: Draft

**Input**: User authentication — visitors can register and sign in; signed-in users can view their profile; downstream features (catalog admin, checkout) can rely on bearer tokens and role checks. Target consumers: React SPA and API clients sharing the same JSON contract.

**Contract reference**: `specs/user-authentication/contracts/auth-api.yaml`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Register as a customer (Priority: P1)

As a new visitor, I can create an account with my email, full name, and password so that I can sign in and use customer-only features such as checkout.

**Why this priority**: Registration is the entry point for any signed-in experience; without it, customers cannot place orders or view order history.

**Independent Test**: `POST /auth/register` with valid fields; verify `200`, bearer token, and user profile with `role` of `customer`; duplicate email returns `409`.

**Acceptance Scenarios**:

1. **Given** no account exists for the email, **When** a visitor registers with `email`, `full_name`, and `password`, **Then** the system returns HTTP `200` with `access_token`, `token_type`, and a `user` object.
2. **Given** a successful registration, **When** the response is returned, **Then** the user’s `role` is `customer` regardless of any role value sent by the client.
3. **Given** an account already exists for the email (case-insensitive), **When** another registration is attempted, **Then** the system returns HTTP `409` with a conflict message.
4. **Given** a successful registration, **When** the response is returned, **Then** `password` and `password_hash` are never included in the response.
5. **Given** invalid input (missing fields, invalid email, password too short), **When** registration is attempted, **Then** the system returns HTTP `422` with validation `detail`.

---

### User Story 2 - Sign in with email and password (Priority: P1)

As a registered user, I can sign in with my email and password so that I receive a bearer token to call protected APIs.

**Why this priority**: Login unlocks all authenticated flows; it must work reliably before catalog admin or checkout can enforce access.

**Independent Test**: Register a user, then `POST /auth/login` with matching credentials; verify `200` and token response; wrong password and unknown email both return generic `401`.

**Acceptance Scenarios**:

1. **Given** a registered user, **When** they submit the correct email and password, **Then** the system returns HTTP `200` with `access_token`, `token_type`, and the public `user` view.
2. **Given** a user registered as `demo@example.com`, **When** they log in with `Demo@Example.com`, **Then** the system authenticates the same account and returns HTTP `200`.
3. **Given** an unknown email or wrong password, **When** login is attempted, **Then** the system returns HTTP `401` with the same generic invalid-credentials message (must not reveal whether the email exists).
4. **Given** a successful login, **When** the response is returned, **Then** `password` and `password_hash` are never included.

---

### User Story 3 - Sign in via form-encoded credentials (Priority: P2)

As a developer or API consumer using interactive API tooling, I can authenticate with form-encoded `username` and `password` fields so that OAuth2-compatible login flows work in Swagger and similar tools.

**Why this priority**: Improves developer experience and tooling compatibility; core JSON login remains the primary SPA path.

**Independent Test**: Register a user, then `POST /auth/login-form` with form fields `username` (email) and `password`; verify same success and error behavior as JSON login.

**Acceptance Scenarios**:

1. **Given** a registered user, **When** they submit form-encoded `username` (email) and matching `password`, **Then** the system returns HTTP `200` with the same auth response shape as JSON login.
2. **Given** invalid credentials via form login, **When** the request is processed, **Then** the system returns HTTP `401` with the same generic invalid-credentials message as JSON login.

---

### User Story 4 - View current profile when signed in (Priority: P1)

As a signed-in user, I can fetch my own profile so that the SPA can display my name, email, and role after login.

**Why this priority**: The client needs a stable “who am I?” endpoint to restore session state and drive role-aware UI.

**Independent Test**: Register or log in, call `GET /auth/me` with `Authorization: Bearer <token>`; verify public profile fields; missing or invalid token returns `401`.

**Acceptance Scenarios**:

1. **Given** a valid bearer token for a persisted user, **When** the user calls `GET /auth/me`, **Then** the system returns HTTP `200` with `id`, `email`, `full_name`, `role`, and `created_at`.
2. **Given** no `Authorization` header, **When** `GET /auth/me` is called, **Then** the system returns HTTP `401`.
3. **Given** an invalid, expired, or malformed bearer token, **When** `GET /auth/me` is called, **Then** the system returns HTTP `401`.
4. **Given** a token whose user no longer exists, **When** `GET /auth/me` is called, **Then** the system returns HTTP `401`.
5. **Given** a successful profile response, **When** the body is returned, **Then** `password` and `password_hash` are never included.

---

### User Story 5 - Access protected APIs with role enforcement (Priority: P2)

As the platform, I require a valid bearer token on non-public routes and enforce role rules so that customers and admins only perform actions they are allowed to perform.

**Why this priority**: Catalog admin, checkout, and order management depend on consistent auth defaults and trustworthy role checks.

**Independent Test**: Call a protected route without a token (`401`), with a customer token on an admin-only route (`403`), and with a valid admin token (`200` or appropriate success).

**Acceptance Scenarios**:

1. **Given** a route is not on the public allowlist, **When** a request omits a valid bearer token, **Then** the system returns HTTP `401`.
2. **Given** a user is authenticated but lacks the required role, **When** they call a role-restricted route, **Then** the system returns HTTP `403`.
3. **Given** a user is authenticated with the required role, **When** they call an allowed route, **Then** the system processes the request according to that feature’s rules.
4. **Given** a protected request is authorized, **When** role is evaluated, **Then** the system uses the user’s current role from persisted account data (not stale role data embedded only in the token).

---

### Edge Cases

- Register with duplicate email differing only by case → HTTP `409`.
- Login with unknown email vs wrong password → identical HTTP `401` message (no account enumeration).
- Expired or tampered bearer token on protected routes → HTTP `401`.
- Valid token for deleted user → HTTP `401` on profile and protected routes.
- Public allowlist routes remain reachable without a token.
- Passwords and password hashes never appear in any API response or error payload intended for clients.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose `POST /auth/register` as a public endpoint accepting `email`, `full_name`, and `password`.
- **FR-002**: System MUST return HTTP `200` on successful registration with `access_token`, `token_type`, and nested `user` profile.
- **FR-003**: System MUST assign `role` of `customer` on self-registration and MUST ignore any client-supplied role intent.
- **FR-004**: System MUST return HTTP `409` when registering with an email that already exists (case-insensitive normalization).
- **FR-005**: System MUST expose `POST /auth/login` as a public endpoint accepting `email` and `password`.
- **FR-006**: System MUST authenticate login using case-insensitive email lookup against persisted accounts.
- **FR-007**: System MUST return HTTP `401` with a generic invalid-credentials message for unknown email or wrong password on login.
- **FR-008**: System MUST expose `POST /auth/login-form` as a public endpoint accepting form-encoded `username` (email) and `password` with the same success and failure semantics as JSON login.
- **FR-009**: System MUST expose `GET /auth/me` requiring a valid bearer token and returning the caller’s public profile.
- **FR-010**: System MUST issue bearer access tokens on successful register and login; tokens MUST expire after 24 hours.
- **FR-011**: System MUST accept bearer tokens via the `Authorization: Bearer <token>` header on protected routes.
- **FR-012**: System MUST treat all routes as protected by default except the public allowlist: `GET /`, `POST /auth/register`, `POST /auth/login`, `POST /auth/login-form`, `GET /products`, `GET /products/{product_id}`.
- **FR-013**: System MUST resolve the authenticated user’s role from persisted account data on each protected request that enforces role policy.
- **FR-014**: System MUST return HTTP `401` for missing, invalid, or expired bearer tokens; HTTP `403` for authenticated users lacking required role or ownership.
- **FR-015**: System MUST never return `password` or `password_hash` in any auth response.
- **FR-016**: System MUST return errors in the shape `{ "detail": "..." }` (validation failures may use an array under `detail` for HTTP `422`).
- **FR-017**: System MUST persist registered users so accounts remain available across application restarts.
- **FR-018**: System MUST use `/auth/*` paths as the canonical auth surface for this feature (no versioned auth path alias required in v1).

### Key Entities

- **User**: A person who can register and sign in. Attributes: unique id, normalized email, display name (`full_name`), role (`customer` or `admin`), account creation timestamp. Password credentials are stored for verification but never exposed via the API. Identified by numeric id.
- **Access token**: A time-limited credential returned on register/login that clients send on protected requests. Carries enough identity to look up the user; role authorization relies on current persisted user data.
- **Public allowlist**: The fixed set of routes callable without authentication; all other routes require a valid bearer token.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new visitor can register and receive a usable bearer token in one successful request at least 95% of the time when the email is not already taken.
- **SC-002**: A registered user can log in and receive a bearer token in one successful request at least 95% of the time with valid credentials.
- **SC-003**: 100% of login failures for unknown email or wrong password use the same generic unauthorized message (no email enumeration).
- **SC-004**: A signed-in user can retrieve their profile via `GET /auth/me` and see accurate `email`, `full_name`, and `role` without client-side transformation.
- **SC-005**: 100% of requests to non-allowlisted routes without a valid token are rejected with HTTP `401`.
- **SC-006**: 100% of role-restricted actions attempted with the wrong role are rejected with HTTP `403`.
- **SC-007**: Registered accounts remain sign-in-able after application restart (persistence verified by integration tests).

## Assumptions

- The React SPA and other API clients obtain the bearer token from register/login responses and attach it to subsequent requests; how the client stores the token is out of scope for this API feature.
- Self-service registration creates **customer** accounts only; **admin** users are provisioned outside registration (seed data or operational process).
- Downstream features (product catalog admin, orders checkout) define their own role rules but depend on this feature for bearer authentication and user identity.
- Access tokens are bearer credentials with a 24-hour lifetime; no refresh or revoke flow in v1.
- Wire JSON shapes for register, login, and profile responses are defined in `specs/user-authentication/contracts/auth-api.yaml` for contract tests and client integration.

## Out of Scope (v1)

- Refresh token issuance, storage, rotation, or revocation.
- Cookie-based sessions or browser cookie transport.
- Password reset, email verification, and multi-factor authentication.
- External identity providers (OAuth, OIDC, social login).
- Versioned `/api/v1/auth/*` path aliases.
- Account lockout policies beyond basic login rate limiting (implementation detail left to plan).
- Server-side session stores or token blocklists.
