from time import perf_counter

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session_with_request
from app.dependencies.auth import get_current_user, require_admin, require_customer
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.auth import RegisterUserResponse
from app.schemas.order import OrderCreate, OrderResponse, OrderStatus, OrderStatusUpdate
from app.services.order_service import (
    ForbiddenOrderAccessError,
    InsufficientStockError,
    OrderNotFoundError,
    OrderService,
    ProductNotFoundForOrderError,
)

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["orders"])


def get_order_repository() -> OrderRepository:
    return OrderRepository()


def get_product_repository() -> ProductRepository:
    return ProductRepository()


def get_order_service(
    order_repository: OrderRepository = Depends(get_order_repository),
    product_repository: ProductRepository = Depends(get_product_repository),
) -> OrderService:
    return OrderService(order_repository, product_repository)


@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
    request: Request,
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: OrderService = Depends(get_order_service),
    current_user: RegisterUserResponse = Depends(require_customer),
) -> OrderResponse:
    start = perf_counter()
    request_id = request.headers.get("x-request-id", "")
    try:
        order = await service.checkout(
            db,
            user_id=current_user.id,
            payload=payload,
        )
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.info(
            "order_checkout_success",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=201,
            latency_ms=latency_ms,
            outcome="success",
            user_id=current_user.id,
            order_id=order.id,
        )
        return order
    except ProductNotFoundForOrderError as exc:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.info(
            "order_checkout_not_found",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=404,
            latency_ms=latency_ms,
            outcome="not_found",
            product_id=exc.product_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InsufficientStockError as exc:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.info(
            "order_checkout_conflict",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=409,
            latency_ms=latency_ms,
            outcome="conflict",
            product_id=exc.product_id,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except Exception:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.exception(
            "order_checkout_error",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            latency_ms=latency_ms,
            outcome="error",
            user_id=current_user.id,
        )
        raise


@router.get("/orders/me", response_model=list[OrderResponse])
async def list_my_orders(
    request: Request,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: OrderService = Depends(get_order_service),
    current_user: RegisterUserResponse = Depends(get_current_user),
) -> list[OrderResponse]:
    start = perf_counter()
    request_id = request.headers.get("x-request-id", "")
    try:
        orders = await service.list_mine(db, user_id=current_user.id)
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.info(
            "order_list_success",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=200,
            latency_ms=latency_ms,
            outcome="success",
            user_id=current_user.id,
            result_count=len(orders),
        )
        return orders
    except Exception:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.exception(
            "order_list_error",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            latency_ms=latency_ms,
            outcome="error",
            user_id=current_user.id,
        )
        raise


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order_by_id(
    request: Request,
    order_id: int,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: OrderService = Depends(get_order_service),
    current_user: RegisterUserResponse = Depends(get_current_user),
) -> OrderResponse:
    start = perf_counter()
    request_id = request.headers.get("x-request-id", "")
    is_admin = current_user.role == "admin"
    try:
        order = await service.get_order(
            db,
            order_id=order_id,
            user_id=current_user.id,
            is_admin=is_admin,
        )
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.info(
            "order_get_success",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=200,
            latency_ms=latency_ms,
            outcome="success",
            user_id=current_user.id,
            order_id=order_id,
        )
        return order
    except OrderNotFoundError as exc:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.info(
            "order_get_not_found",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=404,
            latency_ms=latency_ms,
            outcome="not_found",
            user_id=current_user.id,
            order_id=order_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ForbiddenOrderAccessError as exc:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.info(
            "order_get_forbidden",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=403,
            latency_ms=latency_ms,
            outcome="forbidden",
            user_id=current_user.id,
            order_id=order_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except Exception:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.exception(
            "order_get_error",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            latency_ms=latency_ms,
            outcome="error",
            user_id=current_user.id,
            order_id=order_id,
        )
        raise


@router.get("/orders", response_model=list[OrderResponse])
async def list_orders_admin(
    request: Request,
    status: OrderStatus | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db_session_with_request),
    service: OrderService = Depends(get_order_service),
    admin_user: RegisterUserResponse = Depends(require_admin),
) -> list[OrderResponse]:
    start = perf_counter()
    request_id = request.headers.get("x-request-id", "")
    try:
        orders = await service.list_admin(db, status=status, limit=limit)
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.info(
            "order_admin_list_success",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=200,
            latency_ms=latency_ms,
            outcome="success",
            user_id=admin_user.id,
            result_count=len(orders),
            status_filter=status,
            limit=limit,
        )
        return orders
    except Exception:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.exception(
            "order_admin_list_error",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            latency_ms=latency_ms,
            outcome="error",
            user_id=admin_user.id,
            status_filter=status,
            limit=limit,
        )
        raise


@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
async def patch_order_status(
    request: Request,
    order_id: int,
    payload: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: OrderService = Depends(get_order_service),
    admin_user: RegisterUserResponse = Depends(require_admin),
) -> OrderResponse:
    start = perf_counter()
    request_id = request.headers.get("x-request-id", "")
    try:
        order, restocked, old_status = await service.update_status(
            db,
            order_id=order_id,
            status=payload.status,
        )
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.info(
            "order_status_update_success",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=200,
            latency_ms=latency_ms,
            outcome="success",
            user_id=admin_user.id,
            order_id=order_id,
            old_status=old_status,
            new_status=payload.status,
            restocked=restocked,
        )
        return order
    except OrderNotFoundError as exc:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.info(
            "order_status_update_not_found",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=404,
            latency_ms=latency_ms,
            outcome="not_found",
            user_id=admin_user.id,
            order_id=order_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.exception(
            "order_status_update_error",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            latency_ms=latency_ms,
            outcome="error",
            user_id=admin_user.id,
            order_id=order_id,
        )
        raise
