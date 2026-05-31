import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.anyio
async def test_get_by_email_returns_none_when_user_not_present():
    from app.database import create_db_engine, create_session_factory, bootstrap_database
    from app.repositories.user_repository import UserRepository

    engine = create_db_engine("sqlite+aiosqlite:///:memory:")
    await bootstrap_database(engine)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        assert isinstance(session, AsyncSession)
        repository = UserRepository()
        user = await repository.get_by_email(session, "missing@example.com")
        assert user is None


@pytest.mark.anyio
async def test_create_user_persists_row_and_returns_user_model():
    from app.database import create_db_engine, create_session_factory, bootstrap_database
    from app.repositories.user_repository import UserRepository

    engine = create_db_engine("sqlite+aiosqlite:///:memory:")
    await bootstrap_database(engine)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        repository = UserRepository()
        user = await repository.create_user(
            session,
            email="new@example.com",
            full_name="New User",
            role="customer",
            password_hash="hash",
        )
        assert user.id is not None
        assert user.email == "new@example.com"


@pytest.mark.anyio
async def test_get_by_email_returns_persisted_user_case_insensitive():
    from app.database import create_db_engine, create_session_factory, bootstrap_database
    from app.repositories.user_repository import UserRepository

    engine = create_db_engine("sqlite+aiosqlite:///:memory:")
    await bootstrap_database(engine)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        repository = UserRepository()
        await repository.create_user(
            session,
            email="case-user@example.com",
            full_name="Case User",
            role="customer",
            password_hash="hash",
        )
        user = await repository.get_by_email(session, "Case-User@Example.com")
        assert user is not None
        assert user.email == "case-user@example.com"


@pytest.mark.anyio
async def test_create_user_raises_conflict_on_duplicate_normalized_email():
    from app.database import create_db_engine, create_session_factory, bootstrap_database
    from app.repositories.user_repository import DuplicateEmailError, UserRepository

    engine = create_db_engine("sqlite+aiosqlite:///:memory:")
    await bootstrap_database(engine)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        repository = UserRepository()
        await repository.create_user(
            session,
            email="dupe@example.com",
            full_name="Dupe One",
            role="customer",
            password_hash="hash",
        )

        with pytest.raises(DuplicateEmailError):
            await repository.create_user(
                session,
                email="Dupe@Example.com",
                full_name="Dupe Two",
                role="customer",
                password_hash="hash",
            )
