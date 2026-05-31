import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


def test_create_db_engine_returns_async_engine_for_sqlite_aiosqlite_url():
    from app.database import create_db_engine

    engine = create_db_engine("sqlite+aiosqlite:///:memory:")

    assert isinstance(engine, AsyncEngine)
    assert engine.dialect.driver == "aiosqlite"


def test_create_session_factory_returns_async_sessionmaker():
    from app.database import create_db_engine, create_session_factory

    engine = create_db_engine("sqlite+aiosqlite:///:memory:")
    session_factory = create_session_factory(engine)

    assert isinstance(session_factory, async_sessionmaker)


@pytest.mark.anyio
async def test_get_db_session_yields_async_session_and_closes_after_use():
    from app.database import create_db_engine, create_session_factory, get_db_session

    engine = create_db_engine("sqlite+aiosqlite:///:memory:")
    session_factory = create_session_factory(engine)
    get_db_session.__globals__["_session_factory"] = session_factory

    session_generator = get_db_session()
    session = await anext(session_generator)
    assert isinstance(session, AsyncSession)

    await session_generator.aclose()
    assert session.in_transaction() is False
