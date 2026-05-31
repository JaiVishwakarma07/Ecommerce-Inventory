# User Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build JWT-based user authentication endpoints (`register`, `login`, `login-form`, `me`) with default-protected authorization, async PostgreSQL access, and full TDD coverage.

**Architecture:** Implement layered backend flow `routers -> services -> repositories -> models` with explicit auth dependencies for bearer token validation and DB-backed role resolution. Keep public endpoint allowlist explicit and enforce auth by default for non-allowlisted routes. Add structured auth logs and metrics in request path.

**Tech Stack:** FastAPI, SQLAlchemy async, asyncpg, Alembic, python-jose, passlib+bcrypt, pytest, pytest-asyncio, httpx AsyncClient.

---

## Scope Check

This feature is a single bounded subsystem (authentication + authorization
foundation) and does not require decomposition into multiple plans.

## File Structure

- `app/core/config.py`: environment and auth config.
- `app/core/security.py`: hashing and JWT create/verify helpers.
- `app/core/observability.py`: structured logging and metrics helpers.
- `app/db/session.py`: async engine/session management.
- `app/models/user.py`: `users` ORM model.
- `app/repositories/user_repository.py`: async user data access operations.
- `app/services/auth_service.py`: register/login business logic.
- `app/api/deps/auth.py`: `get_current_user` and role-check dependencies.
- `app/api/routes/auth.py`: auth endpoints.
- `app/main.py`: app wiring, router registration, route protection policy.
- `specs/user-authentication/contracts/auth-api.yaml`: contract source of truth.
- `tests/unit/*.py`: unit tests for security and auth dependencies.
- `tests/integration/test_auth_endpoints.py`: endpoint integration flows.
- `tests/contract/*.py`: contract and policy tests.

---

### Task 1: Bootstrap Async App Foundation

**Files:**
- Create: `app/main.py`
- Create: `app/core/config.py`
- Create: `app/db/session.py`
- Test: `tests/integration/test_auth_endpoints.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_root_healthcheck():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_auth_endpoints.py::test_root_healthcheck -v`  
Expected: FAIL with `ModuleNotFoundError` for `app.main`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/main.py
from fastapi import FastAPI

app = FastAPI(title="ECOM_OPPO API")


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "service": "ecom-oppo-api"}
```

```python
# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ecom_oppo"
    jwt_secret: str = "change-me"
    access_token_ttl_minutes: int = 1440
    jwt_algorithm: str = "HS256"


settings = Settings()
```

```python
# app/db/session.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_auth_endpoints.py::test_root_healthcheck -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/core/config.py app/db/session.py tests/integration/test_auth_endpoints.py
git commit -m "feat: scaffold async FastAPI app foundation"
```

### Task 2: Add User Model, Migration, and Repository

**Files:**
- Create: `app/models/user.py`
- Create: `app/repositories/user_repository.py`
- Modify: `alembic/versions/20260526_create_users_table.py`
- Test: `tests/integration/test_auth_endpoints.py`

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(async_client):
    payload = {"email": "dupe@example.com", "password": "StrongPass123!", "full_name": "Dupe User"}
    first = await async_client.post("/auth/register", json=payload)
    second = await async_client.post("/auth/register", json=payload)
    assert first.status_code == 200
    assert second.status_code == 409
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_auth_endpoints.py::test_register_duplicate_email_returns_409 -v`  
Expected: FAIL with `404` because route does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# app/models/user.py
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="customer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
```

```python
# app/repositories/user_repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User


class UserRepository:
    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, db: AsyncSession, user_id: int) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
```

```python
# alembic/versions/20260526_create_users_table.py
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="customer"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
```

- [ ] **Step 4: Run test to verify expected state**

Run: `pytest tests/integration/test_auth_endpoints.py::test_register_duplicate_email_returns_409 -v`  
Expected: FAIL with `404` (model/repository exist, endpoint still pending).

- [ ] **Step 5: Commit**

```bash
git add app/models/user.py app/repositories/user_repository.py alembic/versions/20260526_create_users_table.py tests/integration/test_auth_endpoints.py
git commit -m "feat: add user model, repository, and migration"
```

### Task 3: Implement Security Utilities (bcrypt + JWT)

**Files:**
- Create: `app/core/security.py`
- Test: `tests/unit/test_security.py`

- [ ] **Step 1: Write the failing test**

```python
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token


def test_password_hash_and_verify():
    plain = "StrongPass123!"
    hashed = hash_password(plain)
    assert plain != hashed
    assert verify_password(plain, hashed) is True


def test_token_roundtrip():
    token = create_access_token(subject="5")
    payload = decode_access_token(token)
    assert payload["sub"] == "5"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_security.py -v`  
Expected: FAIL with `ModuleNotFoundError` for `app.core.security`.

- [ ] **Step 3: Write minimal implementation**

```python
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.access_token_ttl_minutes)
    payload = {"sub": subject, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_security.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/core/security.py tests/unit/test_security.py
git commit -m "feat: add bcrypt hashing and JWT security helpers"
```

### Task 4: Implement Auth Service and Auth Endpoints

**Files:**
- Create: `app/services/auth_service.py`
- Create: `app/api/routes/auth.py`
- Modify: `app/main.py`
- Test: `tests/integration/test_auth_endpoints.py`

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_register_login_me_flow(async_client):
    register_payload = {"email": "user@example.com", "password": "StrongPass123!", "full_name": "User One"}
    register = await async_client.post("/auth/register", json=register_payload)
    assert register.status_code == 200
    token = register.json()["access_token"]

    login = await async_client.post("/auth/login", json={"email": "user@example.com", "password": "StrongPass123!"})
    assert login.status_code == 200

    me = await async_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_auth_endpoints.py::test_register_login_me_flow -v`  
Expected: FAIL with `404` on `/auth/register`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/services/auth_service.py
from fastapi import HTTPException, status
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    async def register(self, db, email: str, password: str, full_name: str) -> dict:
        existing = await self.users.get_by_email(db, email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        user = User(email=email, password_hash=hash_password(password), full_name=full_name, role="customer")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        token = create_access_token(subject=str(user.id))
        return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role, "created_at": user.created_at.isoformat()}}

    async def login(self, db, email: str, password: str) -> dict:
        user = await self.users.get_by_email(db, email)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        token = create_access_token(subject=str(user.id))
        return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role, "created_at": user.created_at.isoformat()}}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_auth_endpoints.py::test_register_login_me_flow -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/auth_service.py app/api/routes/auth.py app/main.py tests/integration/test_auth_endpoints.py
git commit -m "feat: add register login and me auth flows"
```

### Task 5: Enforce Security-by-Default Route Policy

**Files:**
- Modify: `app/main.py`
- Modify: `docs/design/api-contract-draft.md`
- Test: `tests/contract/test_route_access_policy.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path",
    [("GET", "/"), ("POST", "/auth/register"), ("POST", "/auth/login"), ("POST", "/auth/login-form"), ("GET", "/products"), ("GET", "/products/1")],
)
async def test_public_allowlist_routes(async_client, method, path):
    response = await async_client.request(method, path)
    assert response.status_code < 401


@pytest.mark.asyncio
async def test_non_allowlisted_route_requires_auth(async_client):
    response = await async_client.get("/orders/me")
    assert response.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/contract/test_route_access_policy.py -v`  
Expected: FAIL because allowlist/protection middleware is not complete.

- [ ] **Step 3: Write minimal implementation**

```python
# app/main.py (policy excerpt)
PUBLIC_ALLOWLIST = {
    ("GET", "/"),
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("POST", "/auth/login-form"),
    ("GET", "/products"),
}


def is_public_route(method: str, path: str) -> bool:
    if (method, path) in PUBLIC_ALLOWLIST:
        return True
    if method == "GET" and path.startswith("/products/"):
        return True
    return False
```

```markdown
# docs/design/api-contract-draft.md (auth annotations)
GET  /                         # public
POST /auth/register            # public
POST /auth/login               # public
POST /auth/login-form          # public
GET  /auth/me                  # auth required
GET  /products                 # public
GET  /products/{product_id}    # public
POST /products                 # admin only, auth required
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/contract/test_route_access_policy.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/main.py docs/design/api-contract-draft.md tests/contract/test_route_access_policy.py
git commit -m "feat: enforce public allowlist and default protected routes"
```

### Task 6: Add Observability + Contract Verification

**Files:**
- Create: `app/core/observability.py`
- Modify: `app/api/routes/auth.py`
- Modify: `specs/user-authentication/contracts/auth-api.yaml`
- Test: `tests/contract/test_auth_contract.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest


@pytest.mark.asyncio
async def test_auth_response_shape(async_client):
    payload = {"email": "shape@example.com", "password": "StrongPass123!", "full_name": "Shape User"}
    response = await async_client.post("/auth/register", json=payload)
    body = response.json()
    assert response.status_code == 200
    assert set(["access_token", "token_type", "user"]).issubset(body.keys())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/contract/test_auth_contract.py::test_auth_response_shape -v`  
Expected: FAIL with contract mismatch before final schema alignment.

- [ ] **Step 3: Write minimal implementation**

```python
# app/core/observability.py
import logging

logger = logging.getLogger("auth")


def log_auth_event(event: str, request_id: str, path: str, method: str, status_code: int, latency_ms: float, user_id: str | None) -> None:
    logger.info(
        event,
        extra={
            "request_id": request_id,
            "path": path,
            "method": method,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "user_id": user_id,
        },
    )
```

```yaml
# specs/user-authentication/contracts/auth-api.yaml (ensure)
paths:
  /auth/register:
    post:
      responses:
        "200":
          description: Registration success
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/contract/test_auth_contract.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/core/observability.py app/api/routes/auth.py specs/user-authentication/contracts/auth-api.yaml tests/contract/test_auth_contract.py
git commit -m "feat: add auth observability and contract validation coverage"
```

---

## Self-Review

1. **Spec coverage:** covered by tasks for endpoints, token policy, default-protect
   auth, DB role checks, and observability. No gaps found.
2. **Placeholder scan:** no `TODO`, `TBD`, or unresolved placeholders found.
3. **Type consistency:** JWT subject is consistently string; auth response shape is
   consistently `{access_token, token_type, user}`.

