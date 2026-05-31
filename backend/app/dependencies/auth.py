from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session_with_request
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterUserResponse
from app.services.auth_service import AuthService, UnauthenticatedError


def get_user_repository() -> UserRepository:
    return UserRepository()


def get_auth_service(
    repository: UserRepository = Depends(get_user_repository),
) -> AuthService:
    return AuthService(repository)


def extract_bearer_token(
    authorization: str | None = Header(default=None),
) -> str:
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return token


async def get_current_user(
    token: str = Depends(extract_bearer_token),
    db: AsyncSession = Depends(get_db_session_with_request),
    service: AuthService = Depends(get_auth_service),
) -> RegisterUserResponse:
    try:
        return await service.get_current_user(db, token)
    except UnauthenticatedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        ) from exc


async def require_admin(
    current_user: RegisterUserResponse = Depends(get_current_user),
) -> RegisterUserResponse:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_customer(
    current_user: RegisterUserResponse = Depends(get_current_user),
) -> RegisterUserResponse:
    if current_user.role != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access required",
        )
    return current_user
