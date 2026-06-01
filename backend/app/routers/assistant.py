from functools import lru_cache
from time import perf_counter

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.llm_client import AssistantLlmClient, LlmUnavailableError
from app.config import settings
from app.database import get_db_session_with_request
from app.dependencies.auth import require_customer
from app.dependencies.rate_limit import enforce_assistant_rate_limit
from app.repositories.product_repository import ProductRepository
from app.schemas.assistant import AssistantQueryRequest, AssistantQueryResponse
from app.schemas.auth import RegisterUserResponse
from app.services.assistant_service import AssistantService

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["assistant"])
_metrics: dict[str, int] = {"success": 0, "no_results": 0, "llm_error": 0}


def reset_assistant_metrics() -> None:
    _metrics.clear()
    _metrics.update({"success": 0, "no_results": 0, "llm_error": 0})


@lru_cache(maxsize=1)
def _llm_client_singleton() -> AssistantLlmClient:
    return AssistantLlmClient(settings)


def get_llm_client() -> AssistantLlmClient:
    return _llm_client_singleton()


def get_product_repository() -> ProductRepository:
    return ProductRepository()


def get_assistant_service(
    llm_client: AssistantLlmClient = Depends(get_llm_client),
    repository: ProductRepository = Depends(get_product_repository),
) -> AssistantService:
    return AssistantService(llm_client, repository)


@router.post(
    "/assistant/query",
    response_model=AssistantQueryResponse,
    status_code=status.HTTP_200_OK,
)
async def assistant_query(
    payload: AssistantQueryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session_with_request),
    current_user: RegisterUserResponse = Depends(require_customer),
    service: AssistantService = Depends(get_assistant_service),
) -> AssistantQueryResponse:
    enforce_assistant_rate_limit(current_user.id)
    start = perf_counter()
    request_id = request.headers.get("x-request-id", "")
    try:
        result = await service.query(db, payload.query)
        latency_ms = round((perf_counter() - start) * 1000, 2)
        outcome = "success" if result.products else "no_results"
        _metrics[outcome] = _metrics.get(outcome, 0) + 1
        logger.info(
            f"assistant_query_{outcome}",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            user_id=current_user.id,
            status_code=200,
            latency_ms=latency_ms,
            result_count=len(result.products),
        )
        return result
    except LlmUnavailableError as exc:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        _metrics["llm_error"] = _metrics.get("llm_error", 0) + 1
        logger.info(
            "assistant_query_llm_error",
            request_id=request_id,
            path=str(request.url.path),
            method=request.method,
            user_id=current_user.id,
            status_code=503,
            latency_ms=latency_ms,
            outcome="llm_error",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Assistant temporarily unavailable",
        ) from exc
