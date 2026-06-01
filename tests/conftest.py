import asyncio
import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("ECOM_OPPO_APP_ENV", "test")
os.environ.setdefault("ECOM_OPPO_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(autouse=True)
def reset_user_repository():
    import app.database as database_module
    from app.dependencies.rate_limit import (
        assistant_rate_limiter,
        login_rate_limiter,
        register_rate_limiter,
    )
    from app.routers.assistant import reset_assistant_metrics

    restart_db = BACKEND_ROOT / "data" / "test-restart.db"
    if restart_db.exists():
        restart_db.unlink()

    _dispose_database_engine(database_module)
    database_module._session_factory = None
    register_rate_limiter.reset()
    login_rate_limiter.reset()
    assistant_rate_limiter.reset()
    reset_assistant_metrics()


@pytest.fixture(autouse=True)
async def dispose_database_engine_after_async_test():
    yield
    import app.database as database_module

    engine = database_module._engine
    if engine is not None:
        await engine.dispose()
    database_module._engine = None
    database_module._session_factory = None


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _dispose_database_engine(database_module) -> None:
    engine = database_module._engine
    if engine is None:
        return
    asyncio.run(engine.dispose())
    database_module._engine = None


def pytest_sessionfinish(session, exitstatus):
    import app.database as database_module

    _dispose_database_engine(database_module)
    database_module._session_factory = None


async def create_admin_user(
    db: AsyncSession,
    *,
    email: str = "admin@inventory.com",
    password: str = "AdminPass123!",
    full_name: str = "Inventory Admin",
) -> Any:
    from app.core.security import hash_password
    from app.repositories.user_repository import UserRepository

    repository = UserRepository()
    return await repository.create_user(
        db,
        email=email,
        full_name=full_name,
        role="admin",
        password_hash=hash_password(password),
    )


async def create_customer_user(
    db: AsyncSession,
    *,
    email: str = "customer@example.com",
    password: str = "CustomerPass123!",
    full_name: str = "Test Customer",
) -> Any:
    from app.core.security import hash_password
    from app.repositories.user_repository import UserRepository

    repository = UserRepository()
    return await repository.create_user(
        db,
        email=email,
        full_name=full_name,
        role="customer",
        password_hash=hash_password(password),
    )


def auth_headers_for_user(user_id: int) -> dict[str, str]:
    from app.core.security import create_access_token

    token = create_access_token(str(user_id))
    return {"Authorization": f"Bearer {token}"}


def order_checkout_payload(
    product_id: int,
    *,
    quantity: int = 1,
    shipping_address: str = "42 MG Road, Bengaluru, Karnataka 560001, India",
    extra_items: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    items: list[dict[str, object]] = [
        {"product_id": product_id, "quantity": quantity},
    ]
    if extra_items is not None:
        items.extend(extra_items)
    return {
        "shipping_address": shipping_address,
        "items": items,
    }


def product_write_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Test Product",
        "description": "Test description",
        "sku": "TEST-SKU-001",
        "price": 19.99,
        "quantity": 10,
        "category": "general",
        "image_url": "",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    from app.database import get_db_session

    async for session in get_db_session():
        yield session


@pytest.fixture
async def admin_auth_headers(db_session: AsyncSession) -> dict[str, str]:
    admin = await create_admin_user(db_session)
    return auth_headers_for_user(admin.id)


@pytest.fixture
async def customer_auth_headers(db_session: AsyncSession) -> dict[str, str]:
    customer = await create_customer_user(db_session)
    return auth_headers_for_user(customer.id)
