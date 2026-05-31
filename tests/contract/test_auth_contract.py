import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.anyio
async def test_register_accepts_email_full_name_password_only():
    from app.main import app

    payload = {
        "email": "contract-user@example.com",
        "full_name": "Contract User",
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
async def test_register_response_contains_access_token_token_type_user():
    from app.main import app

    payload = {
        "email": "contract-shape@example.com",
        "full_name": "Contract Shape",
        "password": "StrongPass123!",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/auth/register", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"access_token", "token_type", "user"}


@pytest.mark.anyio
async def test_register_response_excludes_password_fields():
    from app.main import app

    payload = {
        "email": "contract-no-password@example.com",
        "full_name": "Contract No Password",
        "password": "StrongPass123!",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/auth/register", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]
