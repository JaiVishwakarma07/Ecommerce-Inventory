# Brainstorm Output: SQLite Auth Persistence

## Scope Confirmation

- Implement SQLite persistence for auth with `/auth/*` as canonical routes.
- Keep `/api/v1/auth/*` only as optional temporary alias; no dual-route long-term policy.
- Include only `users` table plus reusable DB/session/repository foundation for future DB-backed auth endpoints.
- Use startup table bootstrap in this phase; defer Alembic migrations to follow-up.
- Environment strategy:
  - Dev: file-based SQLite (persistent across restarts).
  - Tests: in-memory SQLite (fast and isolated).

## Selected Approach

**Chosen:** Approach 1 (Thin DB Infrastructure + Targeted Auth Refactor)

Rationale:
- Lowest implementation risk and fastest path to durable persistence.
- Preserves existing endpoint contract and test behavior.
- Establishes reusable DB/session/repository pattern without premature abstraction.

## Design Section 1: Architecture and Components

- Add `app/database.py` for centralized async database wiring:
  - Async engine using `sqlite+aiosqlite`.
  - `async_sessionmaker`.
  - `get_db_session()` FastAPI dependency.
- Refactor `app/models/user.py` into SQLAlchemy ORM mapping for `users` table:
  - `id`, normalized unique `email`, `full_name`, `role`, `password_hash`, `created_at`.
- Refactor `app/repositories/user_repository.py` to async DB methods:
  - `get_by_email(db, email)`
  - `create_user(db, ...)`
- Keep `app/services/auth_service.py` business logic intact:
  - normalize email, hash password, enforce `role="customer"`, create JWT.
- Refactor `app/routers/auth.py` dependency chain:
  - `db: AsyncSession = Depends(get_db_session)`
  - build repository/service from session.
- Update `app/main.py` startup lifecycle:
  - create tables at startup for this phase.
  - keep `/auth/*` canonical and optional versioned alias.
- Ensure this wiring is reusable for future DB-backed auth endpoints.

## Design Section 2: Data Flow, Error Handling, and Testing

### Data Flow
1. Request enters `POST /auth/register`.
2. Payload validated by Pydantic.
3. Router resolves `AsyncSession` via dependency.
4. Service normalizes email and checks repository for existing user.
5. Service hashes password and repository inserts user row in SQLite.
6. Transaction commits and service returns signed JWT response.

### Error Handling
- DB-level unique constraint on normalized email is authoritative.
- Repository maps integrity conflicts to domain duplicate error.
- Router maps duplicate to `409 Conflict`.
- Existing validation and response envelope behavior remain unchanged for the endpoint contract.

### Bootstrap and Environment
- Dev: file SQLite database path to preserve state across restarts.
- Tests: in-memory SQLite with isolated fixtures and clean state per test.
- Startup bootstrap creates required auth tables for this phase.
- Alembic migration workflow explicitly deferred.

### Test Strategy
- Keep and adapt contract tests for response shape and secret-field exclusion.
- Integration tests run against SQLite-backed session and verify:
  - successful registration persistence,
  - duplicate conflict handling,
  - role forcing,
  - case-insensitive duplicate handling.
- Keep security unit tests for password hashing and JWT claims.

## Out of Scope (This Phase)

- Refresh token, password reset, and audit login tables.
- Login/me endpoint implementation details.
- Canonical route migration to `/api/v1/auth/*`.
- Full Alembic migration setup.

## Success Criteria

- Register endpoint writes and reads from SQLite-backed persistence.
- Duplicate normalized email is consistently rejected with `409`.
- Existing endpoint response contract remains stable.
- Tests pass with SQLite-backed integration and in-memory test isolation.
