from time import perf_counter

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session_with_request
from app.dependencies.auth import require_admin
from app.repositories.product_repository import ProductRepository
from app.schemas.auth import RegisterUserResponse
from app.schemas.product import ProductResponse, ProductWrite
from app.services.product_service import DuplicateSku, ProductNotFound, ProductService

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["products"])
_list_metrics: dict[str, int] = {"success": 0}
_get_metrics: dict[str, int] = {"success": 0, "not_found": 0}
_create_metrics: dict[str, int] = {"success": 0, "conflict": 0}
_update_metrics: dict[str, int] = {"success": 0, "not_found": 0, "conflict": 0}
_delete_metrics: dict[str, int] = {"success": 0, "not_found": 0}


def _increment_metric(metrics: dict[str, int], status_name: str) -> None:
    metrics[status_name] = metrics.get(status_name, 0) + 1


def get_product_repository() -> ProductRepository:
    return ProductRepository()


def get_product_service(
    repository: ProductRepository = Depends(get_product_repository),
) -> ProductService:
    return ProductService(repository)


@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    request: Request,
    search: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session_with_request),
    service: ProductService = Depends(get_product_service),
) -> list[ProductResponse]:
    start = perf_counter()
    request_id = request.headers.get("x-request-id", "")
    try:
        products = await service.list_products(db, search=search, limit=limit)
        latency_ms = round((perf_counter() - start) * 1000, 2)
        _increment_metric(_list_metrics, "success")
        logger.info(
            "product_list_success",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=200,
            latency_ms=latency_ms,
            outcome="success",
            result_count=len(products),
            product_list_total=_list_metrics["success"],
        )
        return products
    except Exception:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.exception(
            "product_list_error",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            latency_ms=latency_ms,
            outcome="error",
        )
        raise


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    start = perf_counter()
    request_id = request.headers.get("x-request-id", "")
    try:
        product = await service.get_product(db, product_id)
        latency_ms = round((perf_counter() - start) * 1000, 2)
        _increment_metric(_get_metrics, "success")
        logger.info(
            "product_get_success",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=200,
            latency_ms=latency_ms,
            outcome="success",
            product_id=product_id,
            product_get_total=_get_metrics["success"],
        )
        return product
    except ProductNotFound as exc:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        _increment_metric(_get_metrics, "not_found")
        logger.info(
            "product_get_not_found",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=404,
            latency_ms=latency_ms,
            outcome="not_found",
            product_id=product_id,
            product_get_total=_get_metrics["not_found"],
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        ) from exc
    except Exception:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.exception(
            "product_get_error",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            latency_ms=latency_ms,
            outcome="error",
            product_id=product_id,
        )
        raise


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    request: Request,
    payload: ProductWrite,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: ProductService = Depends(get_product_service),
    _admin: RegisterUserResponse = Depends(require_admin),
) -> ProductResponse:
    start = perf_counter()
    request_id = request.headers.get("x-request-id", "")
    try:
        product = await service.create_product(db, payload)
        latency_ms = round((perf_counter() - start) * 1000, 2)
        _increment_metric(_create_metrics, "success")
        logger.info(
            "product_create_success",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=201,
            latency_ms=latency_ms,
            outcome="success",
            product_id=product.id,
            product_create_total=_create_metrics["success"],
        )
        return product
    except DuplicateSku as exc:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        _increment_metric(_create_metrics, "conflict")
        logger.info(
            "product_create_conflict",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=409,
            latency_ms=latency_ms,
            outcome="conflict",
            product_create_total=_create_metrics["conflict"],
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SKU already exists",
        ) from exc
    except Exception:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.exception(
            "product_create_error",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            latency_ms=latency_ms,
            outcome="error",
        )
        raise


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    request: Request,
    product_id: int,
    payload: ProductWrite,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: ProductService = Depends(get_product_service),
    _admin: RegisterUserResponse = Depends(require_admin),
) -> ProductResponse:
    start = perf_counter()
    request_id = request.headers.get("x-request-id", "")
    try:
        product = await service.update_product(db, product_id, payload)
        latency_ms = round((perf_counter() - start) * 1000, 2)
        _increment_metric(_update_metrics, "success")
        logger.info(
            "product_update_success",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=200,
            latency_ms=latency_ms,
            outcome="success",
            product_id=product_id,
            product_update_total=_update_metrics["success"],
        )
        return product
    except ProductNotFound as exc:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        _increment_metric(_update_metrics, "not_found")
        logger.info(
            "product_update_not_found",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=404,
            latency_ms=latency_ms,
            outcome="not_found",
            product_id=product_id,
            product_update_total=_update_metrics["not_found"],
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        ) from exc
    except DuplicateSku as exc:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        _increment_metric(_update_metrics, "conflict")
        logger.info(
            "product_update_conflict",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=409,
            latency_ms=latency_ms,
            outcome="conflict",
            product_id=product_id,
            product_update_total=_update_metrics["conflict"],
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SKU already exists",
        ) from exc
    except Exception:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.exception(
            "product_update_error",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            latency_ms=latency_ms,
            outcome="error",
            product_id=product_id,
        )
        raise


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: ProductService = Depends(get_product_service),
    _admin: RegisterUserResponse = Depends(require_admin),
) -> Response:
    start = perf_counter()
    request_id = request.headers.get("x-request-id", "")
    try:
        await service.delete_product(db, product_id)
        latency_ms = round((perf_counter() - start) * 1000, 2)
        _increment_metric(_delete_metrics, "success")
        logger.info(
            "product_delete_success",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=204,
            latency_ms=latency_ms,
            outcome="success",
            product_id=product_id,
            product_delete_total=_delete_metrics["success"],
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ProductNotFound as exc:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        _increment_metric(_delete_metrics, "not_found")
        logger.info(
            "product_delete_not_found",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            status_code=404,
            latency_ms=latency_ms,
            outcome="not_found",
            product_id=product_id,
            product_delete_total=_delete_metrics["not_found"],
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        ) from exc
    except Exception:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        logger.exception(
            "product_delete_error",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            latency_ms=latency_ms,
            outcome="error",
            product_id=product_id,
        )
        raise
