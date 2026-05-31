## Context

The current auth register flow is functionally correct but persists data only in process memory. This causes data loss on restart, prevents realistic multi-request behavior, and does not satisfy durable storage expectations for authentication. The implementation must remain async, preserve existing API contract behavior, and align with layered architecture (`routers -> services -> repositories -> models`) while introducing database lifecycle management.

## Goals / Non-Goals

**Goals:**
- Persist registered users in SQLite instead of in-memory state.
- Keep `POST /auth/register` contract-compatible while moving reads/writes to database-backed repository methods.
- Introduce app-level async database engine and session dependency wiring.
- Enforce unique normalized email at storage level and map uniqueness conflicts to `409`.
- Provide deterministic integration testing with a SQLite-backed test database.

**Non-Goals:**
- Implement login, refresh-token flows, or authorization middleware.
- Replace JWT strategy or change token response shape.
- Introduce PostgreSQL in this change (SQLite only as requested).
- Build full migration history beyond the minimum table setup needed for auth persistence.

## Decisions

1. **Use SQLAlchemy async with SQLite driver (`sqlite+aiosqlite`)**
   - **Why:** Fits existing async service/repository architecture and allows smooth upgrade path to PostgreSQL later.
   - **Alternatives considered:** direct `sqlite3` access (rejected: sync I/O and bypasses repository abstraction), synchronous SQLAlchemy engine (rejected: violates async-throughout principle).

2. **Add centralized database module with engine + sessionmaker**
   - **Why:** Keeps connection/session lifecycle in one place and allows dependency injection into repository calls.
   - **Alternatives considered:** creating sessions directly in routers/services (rejected: leaks infrastructure concerns into business layers).

3. **Keep domain model mapping simple with SQLAlchemy ORM user model**
   - **Why:** Repository can return consistent user domain objects while persisting with ORM, minimizing service-level changes.
   - **Alternatives considered:** raw SQL in repository (rejected: harder maintainability and testability for evolving auth logic).

4. **Normalize email before persistence and enforce DB unique constraint**
   - **Why:** Prevents duplicate accounts across case variants and matches current service behavior.
   - **Alternatives considered:** app-only duplicate check without DB constraint (rejected: race condition risk).

5. **Introduce startup schema initialization for SQLite path**
   - **Why:** Provides quick functional setup for this change without requiring full migration workflow.
   - **Alternatives considered:** Alembic-only setup now (deferred: can be added in a follow-up migration hardening pass).

## Risks / Trade-offs

- **[SQLite concurrency limits]** -> Mitigation: keep writes scoped to register path, use short transactions, and document SQLite as development/small-scale target.
- **[Constraint error mapping differences]** -> Mitigation: repository catches/normalizes integrity exceptions and raises domain conflict error consumed by router.
- **[Test flakiness due to shared DB state]** -> Mitigation: create per-test database/session fixtures and clean tables between tests.
- **[Future DB portability gaps]** -> Mitigation: keep repository interfaces AsyncSession-based and avoid SQLite-specific SQL where possible.

## Migration Plan

1. Add config values for SQLite DSN and create async database module (engine/session factory).
2. Define/create users table with unique normalized email constraint.
3. Refactor repository to use `AsyncSession` for `get_by_email` and `create_user`.
4. Refactor router dependencies to inject session -> repository -> service.
5. Update tests to use SQLite test DB fixtures and verify persistence behavior.
6. Validate with integration + contract + unit suites.

**Rollback strategy:** revert to previous in-memory repository wiring if DB integration introduces blocking runtime issues.

## Open Questions

- Should route canonicalization (`/auth` vs `/api/v1/auth`) be handled in this same change or a follow-up?
- Should table creation be runtime bootstrap only, or should Alembic migration be mandatory in this phase?
- Do we want file-based SQLite for local dev and in-memory SQLite for tests by default?
