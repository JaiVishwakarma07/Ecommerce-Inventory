# AI Shopping Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship customer-only natural-language product discovery via `POST /assistant/query` returning `{ answer, products }` with **zero hallucinated product IDs**, plus a minimal “Ask AI” box on `/products`.

**Architecture:** Groq (OpenAI-compatible `AsyncOpenAI`) extracts **filter JSON only** → `ProductRepository.search_for_assistant` reads SQLite → server template builds `answer` → route returns DB-sourced `ProductResponse[]` (max 5, in-stock default). Frontend calls API only for authenticated customers.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, Pydantic v2, `openai` async SDK, pytest + httpx AsyncClient, structlog, React 18 / Vite 5.

**Spec / contract references:**
- `specs/004-ai-shopping-assistant/spec.md`
- `specs/004-ai-shopping-assistant/plan.md`
- `specs/004-ai-shopping-assistant/contracts/assistant-api.yaml`
- `docs/superpowers/specs/2026-06-01-ai-shopping-assistant-design.md`

---

## File map (create / modify)

| File | Responsibility |
|------|----------------|
| `backend/requirements.txt` | Add `openai` |
| `backend/app/config.py` | LLM env settings (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`) |
| `backend/app/schemas/assistant.py` | Request/response + `AssistantSearchFilters` |
| `backend/app/clients/llm_client.py` | Async Groq filter extraction |
| `backend/app/services/assistant_service.py` | Orchestration + template `answer` |
| `backend/app/repositories/product_repository.py` | `search_for_assistant` |
| `backend/app/dependencies/rate_limit.py` | `assistant_rate_limiter`, `enforce_assistant_rate_limit` |
| `backend/app/routers/assistant.py` | `POST /assistant/query` + structlog |
| `backend/app/main.py` | Include assistant router |
| `tests/conftest.py` | Reset assistant rate limiter; optional product insert helper reuse |
| `tests/unit/test_assistant_answer.py` | Template answer builder |
| `tests/unit/test_assistant_repository.py` | Repository filters |
| `tests/unit/test_assistant_service.py` | Service with fake LLM |
| `tests/integration/test_assistant.py` | HTTP + auth + grounding |
| `tests/contract/test_assistant_contract.py` | Schema shape |
| `tests/contract/test_route_access_policy.py` | `/assistant/query` requires auth |
| `frontend/src/context/AuthContext.jsx` | Expose `isCustomer` |
| `frontend/src/pages/Products.jsx` | Ask AI UI |

---

### Task 1: Runtime dependency and LLM configuration

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`
- Test: `tests/unit/test_assistant_config.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_assistant_config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def test_settings_reads_llm_env_without_ecom_prefix(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("LLM_MODEL", "llama-3.3-70b-versatile")

    from app.config import Settings

    settings = Settings()
    assert settings.llm_api_key == "test-key"
    assert settings.llm_base_url == "https://api.groq.com/openai/v1"
    assert settings.llm_model == "llama-3.3-70b-versatile"
    assert settings.llm_timeout_seconds == 15


def test_settings_llm_configured_when_key_and_base_url_present(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")

    from app.config import Settings

    assert Settings().llm_configured is True


def test_settings_llm_not_configured_when_key_missing(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")

    from app.config import Settings

    assert Settings().llm_configured is False
```

- [ ] **Step 2: Run test to verify it fails**

Run from repo root:

```bash
cd backend
pytest ../tests/unit/test_assistant_config.py -v
```

Expected: FAIL (`Settings` has no `llm_api_key`)

- [ ] **Step 3: Add dependency and settings fields**

Add to `backend/requirements.txt`:

```text
openai==1.109.1
```

Add to `backend/app/config.py` (after existing fields):

```python
from pydantic import Field

class Settings(BaseSettings):
    # ... existing fields ...
    llm_api_key: str = Field(default="", validation_alias="LLM_API_KEY")
    llm_base_url: str = Field(default="", validation_alias="LLM_BASE_URL")
    llm_model: str = Field(
        default="llama-3.3-70b-versatile",
        validation_alias="LLM_MODEL",
    )
    llm_timeout_seconds: int = Field(default=15, validation_alias="LLM_TIMEOUT_SECONDS")

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key.strip() and self.llm_base_url.strip())
```

Ensure `model_config` includes `populate_by_name=True`:

```python
model_config = SettingsConfigDict(
    env_prefix="ECOM_OPPO_",
    extra="ignore",
    populate_by_name=True,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest ../tests/unit/test_assistant_config.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/app/config.py tests/unit/test_assistant_config.py
git commit -m "feat(assistant): add openai dependency and LLM settings"
```

---

### Task 2: Assistant schemas and answer builder

**Files:**
- Create: `backend/app/schemas/assistant.py`
- Create: `tests/unit/test_assistant_answer.py`

- [ ] **Step 1: Write failing answer builder tests**

```python
# tests/unit/test_assistant_answer.py
from decimal import Decimal

from app.schemas.assistant import AssistantSearchFilters, build_assistant_answer
from app.schemas.product import ProductResponse
from datetime import datetime, timezone


def _product(product_id: int, name: str) -> ProductResponse:
    now = datetime.now(timezone.utc)
    return ProductResponse(
        id=product_id,
        name=name,
        description="",
        sku=f"SKU-{product_id}",
        price=Decimal("99.99"),
        quantity=5,
        category="general",
        image_url="",
        created_at=now,
        updated_at=now,
    )


def test_build_assistant_answer_zero_results():
    answer = build_assistant_answer([], query="laptop under 10000")
    assert "No in-stock products" in answer


def test_build_assistant_answer_one_result():
    answer = build_assistant_answer([_product(1, "Budget Laptop")], query="laptop")
    assert "Found 1 product" in answer


def test_build_assistant_answer_multiple_results():
    products = [_product(1, "A"), _product(2, "B")]
    answer = build_assistant_answer(products, query="gadget")
    assert "Found 2 products" in answer


def test_assistant_search_filters_defaults():
    filters = AssistantSearchFilters.model_validate({})
    assert filters.search is None
    assert filters.include_out_of_stock is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest ../tests/unit/test_assistant_answer.py -v`  
Expected: FAIL (`ModuleNotFoundError: app.schemas.assistant`)

- [ ] **Step 3: Implement schemas and answer builder**

```python
# backend/app/schemas/assistant.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest ../tests/unit/test_assistant_answer.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/assistant.py tests/unit/test_assistant_answer.py
git commit -m "feat(assistant): add schemas and template answer builder"
```

---

### Task 3: Product repository assistant search

**Files:**
- Modify: `backend/app/repositories/product_repository.py`
- Create: `tests/unit/test_assistant_repository.py`

- [ ] **Step 1: Write failing repository tests**

```python
# tests/unit/test_assistant_repository.py
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.product_repository import ProductRepository
from app.schemas.assistant import AssistantSearchFilters


@pytest.mark.anyio
async def test_search_for_assistant_filters_by_max_price_and_stock(db_session: AsyncSession):
    from app.models.product import Product

    db_session.add_all(
        [
            Product(
                name="Budget Laptop",
                description="cheap laptop",
                sku="LAP-001",
                price=Decimal("8999.00"),
                quantity=2,
                category="electronics",
                image_url="",
            ),
            Product(
                name="Premium Laptop",
                description="expensive",
                sku="LAP-002",
                price=Decimal("45000.00"),
                quantity=1,
                category="electronics",
                image_url="",
            ),
            Product(
                name="Sold Out Laptop",
                description="none left",
                sku="LAP-003",
                price=Decimal("5000.00"),
                quantity=0,
                category="electronics",
                image_url="",
            ),
        ]
    )
    await db_session.commit()

    repo = ProductRepository()
    filters = AssistantSearchFilters(
        search="laptop",
        max_price=Decimal("10000"),
        include_out_of_stock=False,
    )
    results = await repo.search_for_assistant(db_session, filters=filters, limit=5)

    assert len(results) == 1
    assert results[0].sku == "LAP-001"


@pytest.mark.anyio
async def test_search_for_assistant_respects_limit_five(db_session: AsyncSession):
    from app.models.product import Product

    for i in range(7):
        db_session.add(
            Product(
                name=f"Widget {i}",
                description="",
                sku=f"W-{i}",
                price=Decimal("10.00"),
                quantity=10,
                category="general",
                image_url="",
            )
        )
    await db_session.commit()

    repo = ProductRepository()
    results = await repo.search_for_assistant(
        db_session,
        filters=AssistantSearchFilters(search="widget"),
        limit=5,
    )
    assert len(results) == 5
```

Add `db_session` fixture to `tests/conftest.py` if missing:

```python
@pytest.fixture
async def db_session():
    from app.database import bootstrap_database, create_db_engine, create_session_factory
    from app.config import Settings

    settings = Settings.for_test()
    engine = create_db_engine(settings.resolved_database_url)
    session_factory = create_session_factory(engine)
    await bootstrap_database(engine)
    async with session_factory() as session:
        yield session
    await engine.dispose()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest ../tests/unit/test_assistant_repository.py -v`  
Expected: FAIL (`search_for_assistant` not defined)

- [ ] **Step 3: Implement `search_for_assistant`**

Add to `backend/app/repositories/product_repository.py`:

```python
from app.schemas.assistant import AssistantSearchFilters

class ProductRepository:
    # ... existing methods ...

    async def search_for_assistant(
        self,
        db: AsyncSession,
        *,
        filters: AssistantSearchFilters,
        limit: int = 5,
    ) -> list[Product]:
        capped_limit = min(limit, 5)
        query = select(Product)

        normalized_search = (filters.search or "").strip()
        if normalized_search:
            pattern = f"%{normalized_search.lower()}%"
            query = query.where(
                or_(
                    func.lower(Product.name).like(pattern),
                    func.lower(Product.sku).like(pattern),
                    func.lower(Product.category).like(pattern),
                    func.lower(Product.description).like(pattern),
                )
            )

        if filters.category:
            category_pattern = f"%{filters.category.strip().lower()}%"
            query = query.where(func.lower(Product.category).like(category_pattern))

        if filters.max_price is not None:
            query = query.where(Product.price <= filters.max_price)

        if filters.min_price is not None:
            query = query.where(Product.price >= filters.min_price)

        if not filters.include_out_of_stock:
            query = query.where(Product.quantity > 0)

        query = query.order_by(Product.price.asc(), Product.name.asc()).limit(capped_limit)

        result = await db.execute(query)
        return list(result.scalars().all())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest ../tests/unit/test_assistant_repository.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/product_repository.py tests/unit/test_assistant_repository.py tests/conftest.py
git commit -m "feat(assistant): add search_for_assistant repository query"
```

---

### Task 4: LLM client (filter extraction only)

**Files:**
- Create: `backend/app/clients/llm_client.py`
- Create: `tests/unit/test_assistant_llm_client.py`

- [ ] **Step 1: Write failing LLM client tests**

```python
# tests/unit/test_assistant_llm_client.py
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.clients.llm_client import AssistantLlmClient, LlmUnavailableError
from app.config import Settings


@pytest.mark.anyio
async def test_extract_filters_parses_json_content():
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
async def test_extract_filters_raises_when_not_configured():
    settings = Settings(llm_api_key="", llm_base_url="")
    client = AssistantLlmClient(settings)

    with pytest.raises(LlmUnavailableError):
        await client.extract_filters("laptop")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest ../tests/unit/test_assistant_llm_client.py -v`  
Expected: FAIL (module missing)

- [ ] **Step 3: Implement LLM client**

```python
# backend/app/clients/llm_client.py
import json

from openai import AsyncOpenAI

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
            raw = response.choices[0].message.content or "{}"
            payload = json.loads(raw)
            return AssistantSearchFilters.model_validate(payload)
        except Exception as exc:
            raise LlmUnavailableError("LLM request failed") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest ../tests/unit/test_assistant_llm_client.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/clients/llm_client.py tests/unit/test_assistant_llm_client.py
git commit -m "feat(assistant): add Groq filter extraction client"
```

---

### Task 5: Assistant service orchestration

**Files:**
- Create: `backend/app/services/assistant_service.py`
- Create: `tests/unit/test_assistant_service.py`

- [ ] **Step 1: Write failing service tests**

```python
# tests/unit/test_assistant_service.py
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.llm_client import LlmUnavailableError
from app.repositories.product_repository import ProductRepository
from app.schemas.assistant import AssistantSearchFilters
from app.services.assistant_service import AssistantService


class FakeLlmClient:
    def __init__(self, filters: AssistantSearchFilters | None = None, error: Exception | None = None):
        self._filters = filters or AssistantSearchFilters(search="laptop", max_price=Decimal("10000"))
        self._error = error

    async def extract_filters(self, query: str) -> AssistantSearchFilters:
        if self._error:
            raise self._error
        return self._filters


@pytest.mark.anyio
async def test_assistant_service_returns_db_products_only(db_session: AsyncSession):
    from app.models.product import Product

    db_session.add(
        Product(
            name="Budget Laptop",
            description="",
            sku="LAP-001",
            price=Decimal("8999.00"),
            quantity=3,
            category="electronics",
            image_url="",
        )
    )
    await db_session.commit()

    service = AssistantService(FakeLlmClient(), ProductRepository())
    result = await service.query(db_session, "laptop under 10000")

    assert len(result.products) == 1
    assert result.products[0].sku == "LAP-001"
    assert "Found 1 product" in result.answer


@pytest.mark.anyio
async def test_assistant_service_propagates_llm_unavailable(db_session: AsyncSession):
    service = AssistantService(
        FakeLlmClient(error=LlmUnavailableError("down")),
        ProductRepository(),
    )
    with pytest.raises(LlmUnavailableError):
        await service.query(db_session, "laptop")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest ../tests/unit/test_assistant_service.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement service**

```python
# backend/app/services/assistant_service.py
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.llm_client import AssistantLlmClient
from app.repositories.product_repository import ProductRepository
from app.schemas.assistant import AssistantQueryResponse, build_assistant_answer
from app.services.product_service import ProductService


class AssistantService:
    def __init__(
        self,
        llm_client: AssistantLlmClient,
        product_repository: ProductRepository,
    ) -> None:
        self._llm_client = llm_client
        self._product_repository = product_repository
        self._product_mapper = ProductService(product_repository)

    async def query(self, db: AsyncSession, query_text: str) -> AssistantQueryResponse:
        filters = await self._llm_client.extract_filters(query_text)
        rows = await self._product_repository.search_for_assistant(
            db,
            filters=filters,
            limit=5,
        )
        products = [self._product_mapper._to_response(row) for row in rows]
        answer = build_assistant_answer(products, query=query_text)
        return AssistantQueryResponse(answer=answer, products=products)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest ../tests/unit/test_assistant_service.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/assistant_service.py tests/unit/test_assistant_service.py
git commit -m "feat(assistant): add AssistantService orchestration"
```

---

### Task 6: Rate limiting, router, and app wiring

**Files:**
- Modify: `backend/app/dependencies/rate_limit.py`
- Create: `backend/app/routers/assistant.py`
- Modify: `backend/app/main.py`
- Modify: `tests/conftest.py`
- Create: `tests/integration/test_assistant.py` (first tests)

- [ ] **Step 1: Write failing integration tests (auth + happy path skeleton)**

```python
# tests/integration/test_assistant.py
import pytest
from httpx import ASGITransport, AsyncClient

from tests.conftest import auth_headers_for_user, create_admin_user, create_customer_user


class StubLlmClient:
    async def extract_filters(self, query: str):
        from app.schemas.assistant import AssistantSearchFilters
        from decimal import Decimal

        return AssistantSearchFilters(search="laptop", max_price=Decimal("10000"))


@pytest.fixture
def stub_llm_client(monkeypatch):
    from app.routers import assistant as assistant_router

    monkeypatch.setattr(
        assistant_router,
        "get_llm_client",
        lambda: StubLlmClient(),
    )


@pytest.mark.anyio
async def test_assistant_query_requires_authentication():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/assistant/query",
            json={"query": "laptop under 10000"},
        )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_assistant_query_forbidden_for_admin(db_session, stub_llm_client):
    from app.main import app

    admin = await create_admin_user(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/assistant/query",
            json={"query": "laptop"},
            headers=auth_headers_for_user(admin.id),
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Customer access required"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest ../tests/integration/test_assistant.py -v`  
Expected: FAIL (404 — route missing)

- [ ] **Step 3: Add rate limiter**

Add to `backend/app/dependencies/rate_limit.py`:

```python
assistant_rate_limiter = InMemoryRateLimiter(
    max_requests=10,
    window_seconds=60,
    detail="Rate limit exceeded",
)


def enforce_assistant_rate_limit(request: Request) -> None:
    client_host = _get_client_ip(request)
    assistant_rate_limiter.check(client_host)
```

Update `tests/conftest.py` autouse fixture to reset:

```python
from app.dependencies.rate_limit import assistant_rate_limiter
assistant_rate_limiter.reset()
```

- [ ] **Step 4: Implement router**

```python
# backend/app/routers/assistant.py
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


def get_llm_client() -> AssistantLlmClient:
    return AssistantLlmClient(settings)


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
    dependencies=[Depends(enforce_assistant_rate_limit)],
)
async def assistant_query(
    payload: AssistantQueryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session_with_request),
    current_user: RegisterUserResponse = Depends(require_customer),
    service: AssistantService = Depends(get_assistant_service),
) -> AssistantQueryResponse:
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
```

- [ ] **Step 5: Register router in main**

Add to `backend/app/main.py`:

```python
from app.routers.assistant import router as assistant_router

app.include_router(assistant_router)
```

- [ ] **Step 6: Run integration tests**

Run: `pytest ../tests/integration/test_assistant.py -v`  
Expected: PASS for auth tests

- [ ] **Step 7: Commit**

```bash
git add backend/app/dependencies/rate_limit.py backend/app/routers/assistant.py backend/app/main.py tests/integration/test_assistant.py tests/conftest.py
git commit -m "feat(assistant): add POST /assistant/query with auth and rate limit"
```

---

### Task 7: Integration tests — grounding, empty results, validation, 503

**Files:**
- Modify: `tests/integration/test_assistant.py`

- [ ] **Step 1: Add remaining integration tests**

```python
@pytest.mark.anyio
async def test_assistant_query_customer_success_grounded_ids(db_session, stub_llm_client):
    from app.main import app
    from decimal import Decimal
    from app.models.product import Product

    product = Product(
        name="Budget Laptop",
        description="affordable",
        sku="LAP-001",
        price=Decimal("8999.00"),
        quantity=2,
        category="electronics",
        image_url="",
    )
    db_session.add(product)
    await db_session.commit()

    customer = await create_customer_user(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/assistant/query",
            json={"query": "laptop under 10000"},
            headers=auth_headers_for_user(customer.id),
        )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"answer", "products"}
    assert len(body["products"]) == 1
    assert body["products"][0]["id"] == product.id


@pytest.mark.anyio
async def test_assistant_query_empty_results_returns_200(db_session, stub_llm_client):
    from app.main import app

    customer = await create_customer_user(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/assistant/query",
            json={"query": "laptop under 10000"},
            headers=auth_headers_for_user(customer.id),
        )

    assert response.status_code == 200
    assert response.json()["products"] == []


@pytest.mark.anyio
async def test_assistant_query_blank_query_returns_422(db_session, stub_llm_client):
    from app.main import app

    customer = await create_customer_user(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/assistant/query",
            json={"query": "   "},
            headers=auth_headers_for_user(customer.id),
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_assistant_query_llm_unavailable_returns_503(db_session, monkeypatch):
    from app.main import app
    from app.clients.llm_client import LlmUnavailableError

    class BrokenLlm:
        async def extract_filters(self, query: str):
            raise LlmUnavailableError("down")

    from app.routers import assistant as assistant_router

    monkeypatch.setattr(assistant_router, "get_llm_client", lambda: BrokenLlm())

    customer = await create_customer_user(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/assistant/query",
            json={"query": "laptop"},
            headers=auth_headers_for_user(customer.id),
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Assistant temporarily unavailable"}
    assert "products" not in response.json()
```

- [ ] **Step 2: Run full integration suite**

Run: `pytest ../tests/integration/test_assistant.py -v`  
Expected: all PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_assistant.py
git commit -m "test(assistant): add grounding, empty, validation, and 503 integration tests"
```

---

### Task 8: Contract and route access policy tests

**Files:**
- Create: `tests/contract/test_assistant_contract.py`
- Modify: `tests/contract/test_route_access_policy.py`

- [ ] **Step 1: Write contract tests**

```python
# tests/contract/test_assistant_contract.py
from datetime import datetime, timezone
from decimal import Decimal

from app.schemas.assistant import AssistantQueryRequest, AssistantQueryResponse
from app.schemas.product import ProductResponse


def test_assistant_query_request_rejects_blank_query():
    try:
        AssistantQueryRequest.model_validate({"query": "   "})
        assert False, "expected validation error"
    except Exception:
        pass


def test_assistant_query_response_shape():
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
```

- [ ] **Step 2: Add route access policy test**

Append to `tests/contract/test_route_access_policy.py`:

```python
@pytest.mark.anyio
async def test_post_assistant_query_requires_authentication():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/assistant/query",
            json={"query": "laptop"},
        )

    assert response.status_code == 401
```

- [ ] **Step 3: Run contract tests**

Run: `pytest ../tests/contract/test_assistant_contract.py ../tests/contract/test_route_access_policy.py -v`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/contract/test_assistant_contract.py tests/contract/test_route_access_policy.py
git commit -m "test(assistant): add contract and route access policy tests"
```

---

### Task 9: Frontend — Ask AI on Products page

**Files:**
- Modify: `frontend/src/context/AuthContext.jsx`
- Modify: `frontend/src/pages/Products.jsx`

- [ ] **Step 1: Expose `isCustomer` in auth context**

In `frontend/src/context/AuthContext.jsx`, add to `value`:

```javascript
isCustomer: user?.role === "customer",
```

- [ ] **Step 2: Add Ask AI UI to Products page**

Add state and handler in `frontend/src/pages/Products.jsx`:

```javascript
const { isAuthenticated, isAdmin, isCustomer } = useAuth();
const [aiQuery, setAiQuery] = useState("");
const [aiAnswer, setAiAnswer] = useState("");
const [aiProducts, setAiProducts] = useState([]);
const [aiLoading, setAiLoading] = useState(false);
const [aiError, setAiError] = useState("");

async function submitAiQuery(event) {
  event.preventDefault();
  const trimmed = aiQuery.trim();
  if (!trimmed) return;
  setAiLoading(true);
  setAiError("");
  setAiAnswer("");
  setAiProducts([]);
  try {
    const { data } = await api.post("/assistant/query", { query: trimmed });
    setAiAnswer(data.answer);
    setAiProducts(data.products || []);
  } catch (err) {
    setAiError(formatApiError(err, "Assistant temporarily unavailable"));
  } finally {
    setAiLoading(false);
  }
}
```

Render below page header (only when `isCustomer`):

```jsx
{isCustomer && (
  <form className="assistant-bar" onSubmit={submitAiQuery}>
    <input
      className="search"
      type="text"
      placeholder='Ask AI — e.g. "laptop under 10000"'
      value={aiQuery}
      onChange={(e) => setAiQuery(e.target.value)}
      maxLength={500}
    />
    <button className="btn btn-primary" type="submit" disabled={aiLoading}>
      {aiLoading ? "Searching..." : "Ask AI"}
    </button>
  </form>
)}
{aiError && <div className="alert error">{aiError}</div>}
{aiAnswer && <p className="assistant-answer">{aiAnswer}</p>}
```

Reuse existing product card grid for `aiProducts` (map same markup as catalog `products`).

- [ ] **Step 3: Manual smoke test**

1. Login as customer → `/products` shows Ask AI.
2. Logout → Ask AI hidden.
3. Login as admin → Ask AI hidden.
4. Submit query with backend running + LLM env set → answer + cards appear.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/context/AuthContext.jsx frontend/src/pages/Products.jsx
git commit -m "feat(assistant): add Ask AI query box for customers on products page"
```

---

### Task 10: Full verification

**Files:**
- None (verification only)

- [ ] **Step 1: Run backend test suite for assistant**

```bash
cd backend
pip install openai
pytest ../tests/unit/test_assistant_config.py \
  ../tests/unit/test_assistant_answer.py \
  ../tests/unit/test_assistant_repository.py \
  ../tests/unit/test_assistant_llm_client.py \
  ../tests/unit/test_assistant_service.py \
  ../tests/integration/test_assistant.py \
  ../tests/contract/test_assistant_contract.py \
  ../tests/contract/test_route_access_policy.py::test_post_assistant_query_requires_authentication \
  -v
```

Expected: all PASS

- [ ] **Step 2: Run regression slice**

```bash
pytest ../tests/integration/test_auth_login.py ../tests/integration/test_products.py -q
```

Expected: PASS (no auth/catalog regressions)

- [ ] **Step 3: Commit** (only if doc updates made)

Optional: add assistant section to `docs/architecture.md`.

```bash
git commit -m "docs(assistant): document assistant query flow in architecture"
```

---

## Spec coverage self-review

| Spec requirement | Task |
|------------------|------|
| FR-001 customer-only auth | Task 6 (`require_customer`), Task 7 |
| FR-002 query validation 1–500 | Task 2, Task 7 |
| FR-003 response shape | Task 2, Task 8 |
| FR-004 DB-only products | Task 5, Task 7 |
| FR-005 max 5 products | Task 3 |
| FR-006 in-stock default | Task 3 |
| FR-007 NL price/text filters | Task 3, Task 4 |
| FR-008 empty results 200 | Task 7 |
| FR-009 LLM failure 503 | Task 4, Task 6, Task 7 |
| FR-010 `{ detail }` errors | Task 6 (FastAPI defaults) |
| FR-011 not public allowlist | Task 8 |
| FR-012 rate limit | Task 6 |
| FR-013 frontend customer UI | Task 9 |
| US2 UI scenarios | Task 9 |
| US3 anti-hallucination | Task 5, Task 7 |

No placeholder steps remain. All types (`AssistantSearchFilters`, `AssistantQueryResponse`, `search_for_assistant`, `extract_filters`) defined before use.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-01-ai-shopping-assistant.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
