"""Idempotent dev seed for admin user (manual testing, Postman, curl)."""

from __future__ import annotations

import asyncio
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import hash_password
from app.database import bootstrap_database, create_db_engine, create_session_factory
from app.models.user import User

DEFAULT_ADMIN_EMAIL = "admin@inventory.com"
DEFAULT_ADMIN_PASSWORD = "AdminPass123!"
DEFAULT_ADMIN_FULL_NAME = "Inventory Admin"


async def seed_admin(session: AsyncSession) -> int:
    email = DEFAULT_ADMIN_EMAIL.strip().lower()
    existing = await session.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        return 0

    password = os.environ.get("ECOM_OPPO_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
    session.add(
        User(
            email=email,
            full_name=DEFAULT_ADMIN_FULL_NAME,
            role="admin",
            password_hash=hash_password(password),
        )
    )
    await session.commit()
    return 1


async def main() -> None:
    engine = create_db_engine(settings.resolved_database_url)
    await bootstrap_database(engine)
    session_factory = create_session_factory(engine)
    async with session_factory() as session:
        count = await seed_admin(session)
    await engine.dispose()
    print(
        f"Seeded {count} admin user(s). "
        f"Login: POST http://127.0.0.1:8000/auth/login "
        f"email={DEFAULT_ADMIN_EMAIL}"
    )


if __name__ == "__main__":
    asyncio.run(main())
