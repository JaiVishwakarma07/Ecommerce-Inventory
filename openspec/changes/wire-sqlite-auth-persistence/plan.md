# SQLite Persistence Foundation Plan (Signatures Only)

## Config / Settings Signatures (DB URL selection: dev vs test)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ECOM_OPPO_", extra="ignore")
    app_env: str
    sqlite_dev_db_path: str
    database_url: str

    @property
    def resolved_database_url(self) -> str: ...

    @classmethod
    def for_test(cls, *, database_url: str = "sqlite+aiosqlite:///:memory:") -> "Settings": ...
```

## DB Engine / Session / Bootstrap Signatures

```python
from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from fastapi import FastAPI

def build_database_url(settings: "Settings") -> str: ...
def create_db_engine(database_url: str) -> AsyncEngine: ...
def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]: ...
async def get_db_session() -> AsyncIterator[AsyncSession]: ...
async def bootstrap_database(engine: AsyncEngine) -> None: ...
def register_database_lifecycle(app: FastAPI) -> None: ...
```

## Repository Base Signatures (DB-backed modules)

```python
from typing import Protocol
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User

class UserRepositoryBase(Protocol):
    async def get_by_email(self, db: AsyncSession, email: str) -> User | None: ...
    async def create_user(
        self,
        db: AsyncSession,
        *,
        email: str,
        full_name: str,
        role: str,
        password_hash: str,
    ) -> User: ...
```

## Auth Service / Router Integration Signatures

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.auth import RegisterRequest, RegisterResponse

class AuthService:
    async def register_user(self, db: AsyncSession, payload: RegisterRequest) -> RegisterResponse: ...

def get_user_repository() -> UserRepositoryBase: ...
def get_auth_service(repository: UserRepositoryBase = Depends(get_user_repository)) -> AuthService: ...
```

## Exact Test Cases (DB wiring / lifecycle) and Assertions

### Config / URL Selection Tests (`tests/unit/test_database_config.py`)

- `test_resolved_database_url_uses_file_sqlite_in_development`
  - asserts `resolved_database_url` equals file-based SQLite URL when `app_env="development"`.
- `test_resolved_database_url_uses_memory_sqlite_in_test_env`
  - asserts `resolved_database_url` equals `sqlite+aiosqlite:///:memory:` when `app_env="test"`.
- `test_for_test_overrides_database_url_with_memory_default`
  - asserts `Settings.for_test()` returns settings whose `resolved_database_url` is in-memory SQLite.

### Engine / Session Wiring Tests (`tests/unit/test_database_wiring.py`)

- `test_create_db_engine_returns_async_engine_for_sqlite_aiosqlite_url`
  - asserts returned engine is `AsyncEngine` and dialect driver is `aiosqlite`.
- `test_create_session_factory_returns_async_sessionmaker`
  - asserts returned factory builds `AsyncSession` instances.
- `test_get_db_session_yields_async_session_and_closes_after_use`
  - asserts dependency yields an `AsyncSession` and closes session after context exit.

### Bootstrap / Lifecycle Tests (`tests/integration/test_database_bootstrap.py`)

- `test_bootstrap_database_creates_users_table`
  - asserts `users` table exists after bootstrap execution.
- `test_register_database_lifecycle_bootstraps_on_startup`
  - asserts app startup hook runs bootstrap and DB is ready before first request.
- `test_bootstrap_is_idempotent_when_tables_already_exist`
  - asserts calling bootstrap twice does not fail and table remains available.

### Repository DB Tests (`tests/integration/test_user_repository_sqlite.py`)

- `test_get_by_email_returns_none_when_user_not_present`
  - asserts repository returns `None` for unknown normalized email.
- `test_create_user_persists_row_and_returns_user_model`
  - asserts row is inserted and returned model contains persisted fields.
- `test_get_by_email_returns_persisted_user_case_insensitive`
  - asserts lookup succeeds across email casing variants.
- `test_create_user_raises_conflict_on_duplicate_normalized_email`
  - asserts duplicate normalized email triggers integrity/conflict path.

### Endpoint Lifecycle / DB Integration Tests (`tests/integration/test_auth_register_sqlite.py`)

- `test_register_endpoint_persists_user_in_sqlite_database`
  - asserts successful register response and persisted row exists in DB.
- `test_register_duplicate_email_returns_409_with_db_unique_constraint`
  - asserts second register with normalized duplicate returns `409`.
- `test_register_persistence_survives_app_restart_for_file_sqlite`
  - asserts user remains available after simulated app restart using file-based SQLite.
- `test_register_tests_use_isolated_memory_sqlite_per_test`
  - asserts test fixture isolation prevents cross-test contamination.
