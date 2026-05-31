"""Public route access policy for catalog browse and protected orders."""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.anyio
async def test_get_products_is_public_allowlisted():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/products")

    assert response.status_code == 200


@pytest.mark.anyio
async def test_get_product_by_id_is_public_allowlisted():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/products/1")

    assert response.status_code not in (401, 403)


@pytest.mark.anyio
async def test_post_orders_requires_authentication():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/orders",
            json={
                "shipping_address": "1 Test St",
                "items": [{"product_id": 1, "quantity": 1}],
            },
        )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_orders_me_requires_authentication():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/orders/me")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_order_by_id_requires_authentication():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/orders/1")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_orders_admin_requires_authentication():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/orders")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_patch_order_status_requires_authentication():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            "/orders/1/status",
            json={"status": "cancelled"},
        )

    assert response.status_code == 401
