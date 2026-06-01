import asyncio
import json

import httpx
from openai import APIError, AsyncOpenAI
from pydantic import ValidationError

from app.config import Settings
from app.schemas.assistant import AssistantSearchFilters

SYSTEM_PROMPT = """You extract shopping search filters from user queries.
Return JSON only with keys:
search (string|null), max_price (number|null), min_price (number|null),
category (string|null), include_out_of_stock (boolean).
Never return product ids or a products array.
Default include_out_of_stock to false unless user asks for out-of-stock items."""


class LlmUnavailableError(Exception):
    pass


class AssistantLlmClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: AsyncOpenAI | None = None
        if settings.llm_configured:
            self._client = AsyncOpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                timeout=settings.llm_timeout_seconds,
            )

    async def extract_filters(self, query: str) -> AssistantSearchFilters:
        if self._client is None:
            raise LlmUnavailableError("LLM is not configured")

        try:
            response = await self._client.chat.completions.create(
                model=self._settings.llm_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ],
            )
        except (APIError, asyncio.TimeoutError, httpx.HTTPError) as exc:
            raise LlmUnavailableError("LLM request failed") from exc

        raw = response.choices[0].message.content or "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LlmUnavailableError("LLM returned invalid JSON") from exc

        try:
            return AssistantSearchFilters.model_validate(payload)
        except ValidationError as exc:
            raise LlmUnavailableError("LLM returned invalid filters") from exc
