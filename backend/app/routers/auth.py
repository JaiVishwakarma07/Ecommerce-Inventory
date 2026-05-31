from time import perf_counter
from urllib.parse import parse_qs

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session_with_request
from app.dependencies.auth import extract_bearer_token
from app.dependencies.rate_limit import enforce_login_rate_limit, enforce_register_rate_limit
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, RegisterResponse, RegisterUserResponse
from app.services.auth_service import (
    AuthService,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    UnauthenticatedError,
)

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["auth"])
login_router = APIRouter(tags=["auth"])
versioned_router = APIRouter(tags=["auth"])
me_router = APIRouter(tags=["auth"])
_register_metrics: dict[str, int] = {"success": 0, "conflict": 0}
_login_metrics: dict[str, int] = {"success": 0, "invalid": 0}
_me_metrics: dict[str, int] = {"success": 0, "unauthenticated": 0}


def _increment_register_metric(status_name: str) -> None:
    _register_metrics[status_name] = _register_metrics.get(status_name, 0) + 1


def _increment_login_metric(status_name: str) -> None:
    _login_metrics[status_name] = _login_metrics.get(status_name, 0) + 1


def _increment_me_metric(status_name: str) -> None:
    _me_metrics[status_name] = _me_metrics.get(status_name, 0) + 1


def get_user_repository() -> UserRepository:
    return UserRepository()


def get_auth_service(
    repository: UserRepository = Depends(get_user_repository),
) -> AuthService:
    return AuthService(repository)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(enforce_register_rate_limit)],
)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    start = perf_counter()
    request_id = request.headers.get("x-request-id", "")
    path = str(request.url.path)
    method = request.method
    try:
        result = await service.register_user(db, payload)
        latency_ms = round((perf_counter() - start) * 1000, 2)
        _increment_register_metric("success")
        logger.info(
            "auth_register_success",
            request_id=request_id,
            path=path,
            method=method,
            status_code=status.HTTP_200_OK,
            latency_ms=latency_ms,
            outcome="success",
            user_id=result.user.id,
            auth_register_total=_register_metrics["success"],
        )
        return result
    except EmailAlreadyExistsError as exc:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        _increment_register_metric("conflict")
        logger.info(
            "auth_register_conflict",
            request_id=request_id,
            path=path,
            method=method,
            status_code=status.HTTP_409_CONFLICT,
            latency_ms=latency_ms,
            outcome="conflict",
            auth_register_total=_register_metrics["conflict"],
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from exc


async def _parse_oauth2_password_form(request: Request) -> LoginRequest:
    raw_body = (await request.body()).decode("utf-8")
    form = parse_qs(raw_body, keep_blank_values=True)
    try:
        return LoginRequest(
            email=form.get("username", [""])[0],
            password=form.get("password", [""])[0],
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.errors(),
        ) from exc


async def _login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession,
    service: AuthService,
) -> RegisterResponse:
    start = perf_counter()
    request_id = request.headers.get("x-request-id", "")
    path = str(request.url.path)
    method = request.method
    try:
        result = await service.login_user(db, payload)
        latency_ms = round((perf_counter() - start) * 1000, 2)
        _increment_login_metric("success")
        logger.info(
            "auth_login_success",
            request_id=request_id,
            path=path,
            method=method,
            status_code=status.HTTP_200_OK,
            latency_ms=latency_ms,
            outcome="success",
            user_id=result.user.id,
            auth_login_total=_login_metrics["success"],
        )
        return result
    except InvalidCredentialsError as exc:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        _increment_login_metric("invalid")
        logger.info(
            "auth_login_invalid",
            request_id=request_id,
            path=path,
            method=method,
            status_code=status.HTTP_401_UNAUTHORIZED,
            latency_ms=latency_ms,
            outcome="invalid_credentials",
            auth_login_total=_login_metrics["invalid"],
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        ) from exc


@login_router.post(
    "/login",
    response_model=RegisterResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(enforce_login_rate_limit)],
)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    return await _login(payload, request, db, service)


@versioned_router.post(
    "/login-form",
    response_model=RegisterResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(enforce_login_rate_limit)],
)
async def login_form(
    request: Request,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    payload = await _parse_oauth2_password_form(request)
    return await _login(payload, request, db, service)


@me_router.get(
    "/me",
    response_model=RegisterUserResponse,
    status_code=status.HTTP_200_OK,
)
async def me(
    request: Request,
    token: str = Depends(extract_bearer_token),
    db: AsyncSession = Depends(get_db_session_with_request),
    service: AuthService = Depends(get_auth_service),
) -> RegisterUserResponse:
    start = perf_counter()
    request_id = request.headers.get("x-request-id", "")
    try:
        result = await service.get_current_user(db, token)
        latency_ms = round((perf_counter() - start) * 1000, 2)
        _increment_me_metric("success")
        logger.info(
            "auth_me_success",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=status.HTTP_200_OK,
            latency_ms=latency_ms,
            outcome="success",
            user_id=result.id,
            auth_me_total=_me_metrics["success"],
        )
        return result
    except UnauthenticatedError as exc:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        _increment_me_metric("unauthenticated")
        logger.info(
            "auth_me_unauthenticated",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=status.HTTP_401_UNAUTHORIZED,
            latency_ms=latency_ms,
            outcome="unauthenticated",
            auth_me_total=_me_metrics["unauthenticated"],
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        ) from exc
