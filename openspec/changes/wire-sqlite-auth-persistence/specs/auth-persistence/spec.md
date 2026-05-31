## ADDED Requirements

### Requirement: Register endpoint SHALL persist users in SQLite storage
The system SHALL persist successfully registered users in a SQLite database through async repository operations, and persisted users MUST remain available across application restarts.

#### Scenario: Successful registration persists user record
- **WHEN** a client sends a valid `POST /auth/register` request with a new email
- **THEN** the system creates a user row in SQLite with normalized email, hashed password, role `customer`, and creation timestamp

#### Scenario: Persisted user is available after process restart
- **WHEN** a user is registered and the application process is restarted
- **THEN** the user record remains in SQLite and duplicate registration using the same normalized email is rejected

### Requirement: Register endpoint SHALL enforce unique normalized emails at database level
The system SHALL enforce uniqueness for normalized email addresses in persistent storage and MUST map duplicate-email writes to an HTTP `409 Conflict` response.

#### Scenario: Duplicate email with different casing is rejected
- **WHEN** a user exists with email `demo@example.com` and a request attempts `Demo@Example.com`
- **THEN** the database uniqueness rule prevents a second user and the endpoint responds with `409`

### Requirement: Auth data access SHALL use async session dependencies
The system SHALL provide an async database session dependency and repositories MUST use `AsyncSession` for all authentication persistence operations.

#### Scenario: Register flow resolves dependencies through app database session
- **WHEN** `POST /auth/register` is handled
- **THEN** router dependencies provide an `AsyncSession` to repository-backed auth service calls

### Requirement: Test suites SHALL validate SQLite-backed register behavior
The system SHALL include integration/contract tests that run against a SQLite-backed test database and verify persistence, duplicate conflict handling, and response contract behavior.

#### Scenario: Integration tests confirm durable register behavior
- **WHEN** auth integration tests execute with test database fixtures
- **THEN** tests validate create, duplicate conflict, role forcing, and normalized-email conflict behavior using SQLite persistence
