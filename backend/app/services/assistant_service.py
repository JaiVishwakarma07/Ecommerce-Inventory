from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.llm_client import AssistantLlmClient
from app.repositories.product_repository import ProductRepository
from app.schemas.assistant import AssistantQueryResponse, build_assistant_answer
from app.schemas.product import ProductResponse


class AssistantService:
    def __init__(
        self,
        llm_client: AssistantLlmClient,
        product_repository: ProductRepository,
    ) -> None:
        self._llm_client = llm_client
        self._product_repository = product_repository

    async def query(self, db: AsyncSession, query_text: str) -> AssistantQueryResponse:
        filters = await self._llm_client.extract_filters(query_text)
        rows = await self._product_repository.search_for_assistant(
            db,
            filters=filters,
            limit=5,
        )
        products = [ProductResponse.model_validate(row) for row in rows]
        answer = build_assistant_answer(products, query=query_text)
        return AssistantQueryResponse(answer=answer, products=products)
