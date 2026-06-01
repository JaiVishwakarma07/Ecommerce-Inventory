"""Contract tests for POST /assistant/query per assistant-api.yaml."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.assistant import AssistantQueryRequest, AssistantQueryResponse
from app.schemas.product import ProductResponse


def test_assistant_query_request_rejects_blank_query() -> None:
    with pytest.raises(ValidationError):
        AssistantQueryRequest.model_validate({"query": "   "})


def test_assistant_query_request_accepts_valid_query() -> None:
    request = AssistantQueryRequest.model_validate({"query": "  laptop  "})
    assert request.query == "laptop"


def test_assistant_query_response_shape() -> None:
    now = datetime.now(timezone.utc)
    response = AssistantQueryResponse(
        answer="Found 1 product matching your request.",
        products=[
            ProductResponse(
                id=1,
                name="Widget",
                description="",
                sku="W-1",
                price=Decimal("9.99"),
                quantity=1,
                category="general",
                image_url="",
                created_at=now,
                updated_at=now,
            )
        ],
    )
    body = response.model_dump()
    assert set(body.keys()) == {"answer", "products"}
    assert isinstance(body["products"], list)
    assert len(body["products"]) <= 5
