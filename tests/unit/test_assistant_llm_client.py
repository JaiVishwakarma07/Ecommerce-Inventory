"""Unit tests for AssistantLlmClient filter extraction."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.clients.llm_client import AssistantLlmClient, LlmUnavailableError
from app.config import Settings


@pytest.mark.anyio
async def test_extract_filters_parses_json_content() -> None:
    settings = Settings(
        llm_api_key="test-key",
        llm_base_url="https://api.groq.com/openai/v1",
        llm_model="llama-3.3-70b-versatile",
    )
    client = AssistantLlmClient(settings)

    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps(
                    {
                        "search": "laptop",
                        "max_price": 10000,
                        "min_price": None,
                        "category": None,
                        "include_out_of_stock": False,
                    }
                )
            )
        )
    ]

    client._client = MagicMock()
    client._client.chat.completions.create = AsyncMock(return_value=mock_response)

    filters = await client.extract_filters("laptop under 10000")
    assert filters.search == "laptop"
    assert filters.max_price == 10000
    assert filters.include_out_of_stock is False


@pytest.mark.anyio
async def test_extract_filters_raises_when_not_configured() -> None:
    settings = Settings(llm_api_key="", llm_base_url="")
    client = AssistantLlmClient(settings)

    with pytest.raises(LlmUnavailableError):
        await client.extract_filters("laptop")
