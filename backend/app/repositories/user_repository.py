from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class DuplicateEmailError(Exception):
    pass


class UserRepository:
    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        normalized_email = email.strip().lower()
        query = select(User).where(User.email == normalized_email)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id(self, db: AsyncSession, user_id: int) -> User | None:
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        db: AsyncSession,
        *,
        email: str,
        full_name: str,
        role: str,
        password_hash: str,
    ) -> User:
        normalized_email = email.strip().lower()
        user = User(
            email=normalized_email,
            full_name=full_name.strip(),
            role=role,
            password_hash=password_hash,
        )
        db.add(user)
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise DuplicateEmailError("Email already registered") from exc
        await db.refresh(user)
        return user
