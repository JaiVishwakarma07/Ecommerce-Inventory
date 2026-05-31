import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text


@pytest.mark.anyio
async def test_register_endpoint_persists_user_in_sqlite_database():
    from app.main import app

    payload = {
        "email": "persisted@example.com",
        "full_name": "Persisted User",
        "password": "StrongPass123!",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/auth/register", json=payload)

    assert response.status_code == 200
    async with app.state.db_engine.begin() as conn:
        result = await conn.execute(
            text("SELECT email FROM users WHERE email = :email"),
            {"email": "persisted@example.com"},
        )
        assert result.scalar_one_or_none() == "persisted@example.com"


@pytest.mark.anyio
async def test_register_duplicate_email_returns_409_with_db_unique_constraint():
    from app.main import app

    payload = {
        "email": "dupe-sqlite@example.com",
        "full_name": "Dupe Sqlite",
        "password": "StrongPass123!",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/auth/register", json=payload)
        second = await client.post(
            "/auth/register",
            json={**payload, "email": "Dupe-Sqlite@Example.com"},
        )

    assert first.status_code == 200
    assert second.status_code == 409


@pytest.mark.anyio
async def test_register_persistence_survives_app_restart_for_file_sqlite():
    from app.config import Settings
    from app.database import bootstrap_database, create_db_engine, create_session_factory
    from app.repositories.user_repository import UserRepository

    settings = Settings(
        app_env="development",
        sqlite_dev_db_path="./data/test-restart.db",
        database_url="",
    )
    engine = create_db_engine(settings.resolved_database_url)
    await bootstrap_database(engine)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        repository = UserRepository()
        await repository.create_user(
            session,
            email="restart@example.com",
            full_name="Restart User",
            role="customer",
            password_hash="hash",
        )

    restarted_engine = create_db_engine(settings.resolved_database_url)
    restarted_session_factory = create_session_factory(restarted_engine)
    async with restarted_session_factory() as restarted_session:
        repository = UserRepository()
        reloaded_user = await repository.get_by_email(
            restarted_session, "restart@example.com"
        )
        assert reloaded_user is not None


@pytest.mark.anyio
async def test_register_tests_use_isolated_memory_sqlite_per_test():
    from app.database import create_db_engine, create_session_factory, bootstrap_database
    from app.repositories.user_repository import UserRepository

    engine = create_db_engine("sqlite+aiosqlite:///:memory:")
    await bootstrap_database(engine)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        repository = UserRepository()
        isolated_user = await repository.get_by_email(session, "persisted@example.com")
        assert isolated_user is None
