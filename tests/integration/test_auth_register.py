import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.config import settings


@pytest.mark.anyio
async def test_register_success_returns_200_and_valid_payload():
    from app.main import app

    payload = {
        "email": "new-user@example.com",
        "full_name": "New User",
        "password": "StrongPass123!",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/auth/register", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == payload["email"]
    assert body["user"]["role"] == "customer"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]
    claims = jwt.decode(
        body["access_token"],
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    assert claims["sub"] == str(body["user"]["id"])


@pytest.mark.anyio
async def test_register_duplicate_email_returns_409():
    from app.main import app

    payload = {
        "email": "dupe@example.com",
        "full_name": "Dupe User",
        "password": "StrongPass123!",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/auth/register", json=payload)
        second = await client.post("/auth/register", json=payload)

    assert first.status_code == 200
    assert second.status_code == 409


@pytest.mark.anyio
async def test_register_invalid_payload_returns_400():
    from app.main import app

    payload = {
        "email": "not-an-email",
        "full_name": "Bad User",
        "password": "x",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/auth/register", json=payload)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_register_forces_customer_role_on_self_registration():
    from app.main import app

    payload = {
        "email": "role-test@example.com",
        "full_name": "Role Test",
        "password": "StrongPass123!",
        "role": "admin",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/auth/register", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "customer"


@pytest.mark.anyio
async def test_register_normalizes_email_for_duplicate_lookup():
    from app.main import app

    first_payload = {
        "email": "normalize@example.com",
        "full_name": "Normalize One",
        "password": "StrongPass123!",
    }
    second_payload = {
        "email": "Normalize@Example.com",
        "full_name": "Normalize Two",
        "password": "StrongPass123!",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/auth/register", json=first_payload)
        second = await client.post("/auth/register", json=second_payload)

    assert first.status_code == 200
    assert second.status_code == 409
