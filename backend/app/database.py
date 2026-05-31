from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, Request
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import Settings, settings
from app.models.user import Base
from app.models import order as _order_model  # noqa: F401
from app.models import product as _product_model  # noqa: F401

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def build_database_url(app_settings: Settings) -> str:
    return app_settings.resolved_database_url


def create_db_engine(database_url: str) -> AsyncEngine:
    engine_options: dict[str, object] = {}

    is_in_memory = database_url.startswith("sqlite") and ":memory:" in database_url
    if is_in_memory:
        engine_options["poolclass"] = StaticPool
        engine_options["connect_args"] = {"check_same_thread": False}

    if database_url.startswith("sqlite+aiosqlite:///"):
        database_path = database_url.removeprefix("sqlite+aiosqlite:///")
        if database_path and database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    return create_async_engine(database_url, **engine_options)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    global _engine, _session_factory

    if _session_factory is None:
        database_url = build_database_url(settings)
        _engine = create_db_engine(database_url)
        _session_factory = create_session_factory(_engine)
        await bootstrap_database(_engine)
    session = _session_factory()
    try:
        yield session
    finally:
        await session.close()


async def get_db_session_with_request(request: Request) -> AsyncIterator[AsyncSession]:
    async for session in get_db_session():
        if _engine is not None:
            request.app.state.db_engine = _engine
        if _session_factory is not None:
            request.app.state.db_session_factory = _session_factory
        yield session


async def bootstrap_database(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


def register_database_lifecycle(app: FastAPI) -> None:
    @app.on_event("startup")
    async def _startup() -> None:
        global _engine, _session_factory

        database_url = build_database_url(settings)
        _engine = create_db_engine(database_url)
        _session_factory = create_session_factory(_engine)
        app.state.db_engine = _engine
        app.state.db_session_factory = _session_factory
        await bootstrap_database(_engine)

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        global _engine, _session_factory

        if _engine is not None:
            await _engine.dispose()
        _engine = None
        _session_factory = None

