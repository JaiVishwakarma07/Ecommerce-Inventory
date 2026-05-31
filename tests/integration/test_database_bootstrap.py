import pytest
from fastapi import FastAPI
from sqlalchemy import text


@pytest.mark.anyio
async def test_bootstrap_database_creates_users_table():
    from app.database import bootstrap_database, create_db_engine

    engine = create_db_engine("sqlite+aiosqlite:///:memory:")
    await bootstrap_database(engine)

    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        )
        assert result.scalar_one_or_none() == "users"


@pytest.mark.anyio
async def test_register_database_lifecycle_bootstraps_on_startup():
    from app.database import register_database_lifecycle

    app = FastAPI()
    register_database_lifecycle(app)

    assert len(app.router.on_startup) > 0


@pytest.mark.anyio
async def test_bootstrap_is_idempotent_when_tables_already_exist():
    from app.database import bootstrap_database, create_db_engine

    engine = create_db_engine("sqlite+aiosqlite:///:memory:")
    await bootstrap_database(engine)
    await bootstrap_database(engine)

    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        )
        assert result.scalar_one_or_none() == "users"
