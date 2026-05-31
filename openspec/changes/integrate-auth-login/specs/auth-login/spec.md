## ADDED Requirements

### Requirement: Login endpoint SHALL authenticate persisted users
The system SHALL expose `POST /auth/login` to authenticate users stored in the SQLite-backed `users` table using email and password credentials.

#### Scenario: Successful login returns bearer token
- **WHEN** a persisted user submits a valid email and matching password
- **THEN** the system returns HTTP `200` with `access_token`, `token_type="bearer"`, and the public user view

#### Scenario: Login email lookup is case-insensitive
- **WHEN** a user registered as `demo@example.com` logs in with `Demo@Example.com`
- **THEN** the system authenticates the same persisted user and returns HTTP `200`

### Requirement: Form login endpoint SHALL authenticate persisted users
The system SHALL expose `POST /api/v1/auth/login-form` to authenticate users using form-encoded `username` and `password` fields.

#### Scenario: Successful form login returns bearer token
- **WHEN** a persisted user submits form fields `username` with their email and `password` with the matching password
- **THEN** the system returns HTTP `200` with `access_token`, `token_type="bearer"`, and the public user view

#### Scenario: Form login rejects invalid credentials generically
- **WHEN** a form login request uses an unknown email or wrong password
- **THEN** the system returns HTTP `401` with the same generic invalid credentials message

### Requirement: Login endpoint SHALL reject invalid credentials securely
The system SHALL reject unknown emails and wrong passwords with HTTP `401 Unauthorized` and MUST NOT reveal whether the email exists.

#### Scenario: Unknown email returns generic unauthorized response
- **WHEN** a login request uses an email that does not exist
- **THEN** the system returns HTTP `401` with a generic invalid credentials message

#### Scenario: Wrong password returns generic unauthorized response
- **WHEN** a login request uses an existing email but incorrect password
- **THEN** the system returns HTTP `401` with the same generic invalid credentials message

### Requirement: Login endpoint SHALL preserve sensitive data boundaries
The system SHALL never return `password` or `password_hash` fields in login responses.

#### Scenario: Login response excludes password fields
- **WHEN** login succeeds
- **THEN** the response user payload excludes `password` and `password_hash`

### Requirement: Current-user endpoint SHALL return authenticated user profile
The system SHALL expose `GET /api/v1/auth/me` to return the current authenticated user's public profile using the bearer token subject.

#### Scenario: Valid bearer token returns current user
- **WHEN** a request includes a valid bearer token for a persisted user
- **THEN** the system returns HTTP `200` with the public user view for that user

#### Scenario: Missing bearer token is rejected
- **WHEN** a request omits the `Authorization` header
- **THEN** the system returns HTTP `401`

#### Scenario: Invalid bearer token is rejected
- **WHEN** a request includes an invalid, expired, or malformed bearer token
- **THEN** the system returns HTTP `401`

#### Scenario: Deleted user token is rejected
- **WHEN** a bearer token subject no longer resolves to a persisted user
- **THEN** the system returns HTTP `401`

### Requirement: Login endpoint SHALL use existing auth persistence foundation
The system SHALL use the existing async DB session dependency and repository layer to read users during login.

#### Scenario: Login resolves user through repository and database session
- **WHEN** `POST /auth/login` is handled
- **THEN** the service receives an `AsyncSession` and retrieves the user through `UserRepository.get_by_email`

#### Scenario: Current-user resolves user through repository and database session
- **WHEN** `GET /api/v1/auth/me` is handled
- **THEN** the service receives an `AsyncSession` and retrieves the user through repository lookup by token subject
