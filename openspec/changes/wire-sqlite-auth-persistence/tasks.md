## 1. Database foundation and configuration

- [x] 1.1 Add SQLite database settings and environment defaults in `app/config.py` for async SQLAlchemy usage.
- [x] 1.2 Create `app/database.py` with async engine, async sessionmaker, and a `get_db_session` dependency.
- [x] 1.3 Add SQLite runtime schema bootstrap for auth user table creation during app startup.

## 2. Persisted auth data model and repository

- [x] 2.1 Refactor `app/models/user.py` to support SQLAlchemy ORM mapping for persisted users.
- [x] 2.2 Refactor `app/repositories/user_repository.py` methods to accept `AsyncSession` and run async DB queries/insert operations.
- [x] 2.3 Enforce unique normalized email at DB level and map integrity violations to auth conflict behavior.

## 3. Router/service dependency integration

- [x] 3.1 Update auth dependency chain so router injects DB session -> repository -> service without global mutable singleton state.
- [x] 3.2 Update `AuthService.register_user` and call sites to use DB-backed repository signatures while preserving response contract.
- [x] 3.3 Ensure register endpoint behavior remains contract-compatible (`200`, bearer token, customer role forcing, conflict mapping).

## 4. Test suite alignment for SQLite persistence

- [x] 4.1 Add/adjust test fixtures in `tests/conftest.py` to initialize isolated SQLite test database per run.
- [x] 4.2 Update integration tests to validate persistence-backed behavior (including case-insensitive duplicate conflict).
- [x] 4.3 Update contract/unit tests to run against new repository/session wiring without shared-state side effects.

## 5. Verification and operational readiness

- [x] 5.1 Run integration, contract, and unit auth tests and ensure all pass with SQLite-backed persistence.
- [x] 5.2 Add verification notes documenting test evidence and any known SQLite trade-offs.
- [x] 5.3 Confirm endpoint startup path initializes DB dependencies cleanly and app boot remains functional.
