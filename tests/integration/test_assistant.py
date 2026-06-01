"""Integration tests for assistant endpoint (auth, grounding, mock LLM)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers_for_user, create_admin_user, create_customer_user


class StubLlmClient:
    async def extract_filters(self, query: str):
        from app.schemas.assistant import AssistantSearchFilters

        return AssistantSearchFilters(search="laptop", max_price=Decimal("10000"))


class StubLlmClientNoMatch:
    async def extract_filters(self, query: str):
        from app.schemas.assistant import AssistantSearchFilters

        return AssistantSearchFilters(search="nonexistent-item-xyz")


class StubLlmClientWithFakeProductIds:
    async def extract_filters(self, query: str):
        from app.schemas.assistant import AssistantSearchFilters

        return AssistantSearchFilters.model_validate(
            {
                "search": "laptop",
                "max_price": 10000,
                "product_ids": [99999, 88888],
                "products": [{"id": 77777}],
            }
        )


@pytest.fixture
def stub_llm_client():
    from app.main import app
    from app.routers.assistant import get_llm_client

    app.dependency_overrides[get_llm_client] = lambda: StubLlmClient()
    yield
    app.dependency_overrides.pop(get_llm_client, None)


@pytest.fixture
def stub_llm_client_no_match():
    from app.main import app
    from app.routers.assistant import get_llm_client

    app.dependency_overrides[get_llm_client] = lambda: StubLlmClientNoMatch()
    yield
    app.dependency_overrides.pop(get_llm_client, None)


@pytest.fixture
def stub_llm_client_fake_ids():
    from app.main import app
    from app.routers.assistant import get_llm_client

    app.dependency_overrides[get_llm_client] = lambda: StubLlmClientWithFakeProductIds()
    yield
    app.dependency_overrides.pop(get_llm_client, None)


@pytest.mark.anyio
async def test_assistant_query_requires_authentication() -> None:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/assistant/query",
            json={"query": "laptop under 10000"},
        )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_assistant_query_forbidden_for_admin(
    db_session: AsyncSession,
    stub_llm_client,
) -> None:
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


@pytest.mark.anyio
async def test_assistant_query_customer_success_grounded_ids(
    db_session: AsyncSession,
    stub_llm_client,
) -> None:
    from app.main import app
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
async def test_assistant_query_grounded_ids_exist_in_database(
    db_session: AsyncSession,
    stub_llm_client,
) -> None:
    from app.main import app
    from app.models.product import Product

    product = Product(
        name="Budget Laptop",
        description="affordable",
        sku="LAP-GROUND",
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
    product_ids = {item["id"] for item in response.json()["products"]}
    result = await db_session.execute(
        select(Product.id).where(Product.id.in_(product_ids))
    )
    db_ids = set(result.scalars().all())
    assert product_ids == db_ids


@pytest.mark.anyio
async def test_assistant_query_fake_llm_product_ids_not_in_response(
    db_session: AsyncSession,
    stub_llm_client_fake_ids,
) -> None:
    from app.main import app
    from app.models.product import Product

    product = Product(
        name="Budget Laptop",
        description="affordable",
        sku="LAP-FAKE",
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
    returned_ids = {item["id"] for item in response.json()["products"]}
    assert 99999 not in returned_ids
    assert 88888 not in returned_ids
    assert 77777 not in returned_ids
    assert returned_ids == {product.id}


@pytest.mark.anyio
async def test_assistant_query_empty_results_returns_200(
    db_session: AsyncSession,
    stub_llm_client_no_match,
) -> None:
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
async def test_assistant_query_blank_query_returns_422(
    db_session: AsyncSession,
    stub_llm_client,
) -> None:
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
async def test_assistant_query_rate_limited_after_threshold(
    db_session: AsyncSession,
    stub_llm_client,
) -> None:
    from app.main import app

    customer = await create_customer_user(db_session)
    headers = auth_headers_for_user(customer.id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(10):
            response = await client.post(
                "/assistant/query",
                json={"query": "laptop"},
                headers=headers,
            )
            assert response.status_code == 200

        response = await client.post(
            "/assistant/query",
            json={"query": "laptop"},
            headers=headers,
        )

    assert response.status_code == 429
    assert response.json() == {"detail": "Rate limit exceeded"}


@pytest.mark.anyio
async def test_assistant_query_llm_unavailable_returns_503(
    db_session: AsyncSession,
) -> None:
    from app.clients.llm_client import LlmUnavailableError
    from app.main import app
    from app.routers.assistant import get_llm_client

    class BrokenLlm:
        async def extract_filters(self, query: str):
            raise LlmUnavailableError("down")

    app.dependency_overrides[get_llm_client] = lambda: BrokenLlm()
    try:
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
    finally:
        app.dependency_overrides.pop(get_llm_client, None)
