## Why

The current authentication flow stores users in an in-memory repository, so registered users are lost on process restart and endpoints are not backed by durable storage. We need SQLite-backed persistence now so auth behavior is stable, testable, and ready for real-world usage patterns.

## What Changes

- Replace in-memory auth user persistence with SQLite persistence through SQLAlchemy async sessions.
- Add database configuration and connection/session management for the FastAPI app lifecycle.
- Update auth repository/service integration so `POST /auth/register` writes and reads from the database.
- Add schema/migration support for the users table and required constraints (including unique email).
- Extend tests to verify persistence behavior and endpoint functionality against a real SQLite database.

## Capabilities

### New Capabilities
- `auth-persistence`: Durable database-backed persistence for authentication user records and register endpoint flows.

### Modified Capabilities
- None.

## Impact

- Affected code: `app/main.py`, `app/repositories/user_repository.py`, `app/services/auth_service.py`, auth dependencies, and new database/config modules.
- Affected APIs: `POST /auth/register` behavior remains contract-compatible but now persists data durably.
- New dependencies: SQLAlchemy async stack and SQLite async driver integration.
- System impact: introduces migration/setup workflow and test database fixtures for integration/contract tests.
