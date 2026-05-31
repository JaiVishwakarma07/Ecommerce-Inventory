from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import DuplicateEmailError, UserRepository
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    RegisterUserResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession


class EmailAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class UnauthenticatedError(Exception):
    pass


class AuthService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def register_user(
        self, db: AsyncSession, payload: RegisterRequest
    ) -> RegisterResponse:
        normalized_email = payload.email.strip().lower()
        existing_user = await self._repository.get_by_email(db, normalized_email)
        if existing_user is not None:
            raise EmailAlreadyExistsError("Email already registered")

        password_hash = hash_password(payload.password)
        try:
            user = await self._repository.create_user(
                db,
                email=normalized_email,
                full_name=payload.full_name,
                role="customer",
                password_hash=password_hash,
            )
        except DuplicateEmailError as exc:
            raise EmailAlreadyExistsError("Email already registered") from exc

        return self._build_auth_response(user)

    async def login_user(
        self, db: AsyncSession, payload: LoginRequest
    ) -> RegisterResponse:
        normalized_email = payload.email.strip().lower()
        user = await self._repository.get_by_email(db, normalized_email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise InvalidCredentialsError("Invalid credentials")

        return self._build_auth_response(user)

    async def get_current_user(
        self, db: AsyncSession, token: str
    ) -> RegisterUserResponse:
        subject = decode_access_token(token)
        if subject is None:
            raise UnauthenticatedError("Not authenticated")
        try:
            user_id = int(subject)
        except ValueError as exc:
            raise UnauthenticatedError("Not authenticated") from exc

        user = await self._repository.get_by_id(db, user_id)
        if user is None:
            raise UnauthenticatedError("Not authenticated")

        return RegisterUserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            created_at=user.created_at,
        )

    def _build_auth_response(self, user: User) -> RegisterResponse:
        token = create_access_token(subject=str(user.id))
        return RegisterResponse(
            access_token=token,
            token_type="bearer",
            user=RegisterUserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                created_at=user.created_at,
            ),
        )
