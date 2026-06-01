from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.product import ProductResponse


class AssistantQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=500)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query must not be empty")
        return stripped


class AssistantQueryResponse(BaseModel):
    answer: str
    products: list[ProductResponse]


class AssistantSearchFilters(BaseModel):
    model_config = ConfigDict(extra="ignore")

    search: str | None = None
    max_price: Decimal | None = None
    min_price: Decimal | None = None
    category: str | None = None
    include_out_of_stock: bool = False


def build_assistant_answer(
    products: list[ProductResponse],
    *,
    query: str,
) -> str:
    count = len(products)
    if count == 0:
        return (
            "No in-stock products match your search. "
            "Try different keywords or a higher budget."
        )
    if count == 1:
        return f'Found 1 product matching your request for "{query}".'
    return f'Found {count} products matching your request for "{query}".'
