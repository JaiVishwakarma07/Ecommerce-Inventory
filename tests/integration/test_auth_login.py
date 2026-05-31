import pytest
from httpx import ASGITransport, AsyncClient


async def _register_user(
    client: AsyncClient,
    *,
    email: str = "login-user@example.com",
    password: str = "StrongPass123!",
) -> dict:
    response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Login User",
            "password": password,
        },
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.anyio
async def test_login_success_returns_200_and_token_response():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await _register_user(client)
        response = await client.post(
            "/auth/login",
            json={
                "email": "login-user@example.com",
                "password": "StrongPass123!",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"access_token", "token_type", "user"}
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "login-user@example.com"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]


@pytest.mark.anyio
async def test_login_email_lookup_is_case_insensitive():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await _register_user(client, email="case-login@example.com")
        response = await client.post(
            "/auth/login",
            json={
                "email": "Case-Login@Example.com",
                "password": "StrongPass123!",
            },
        )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "case-login@example.com"


@pytest.mark.anyio
async def test_login_unknown_email_returns_401_with_generic_detail():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={
                "email": "missing-login@example.com",
                "password": "StrongPass123!",
            },
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


@pytest.mark.anyio
async def test_login_wrong_password_returns_401_with_generic_detail():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await _register_user(client, email="wrong-password@example.com")
        response = await client.post(
            "/auth/login",
            json={
                "email": "wrong-password@example.com",
                "password": "WrongPass123!",
            },
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


@pytest.mark.anyio
async def test_login_form_success_with_username_email_field():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await _register_user(client, email="form-login@example.com")
        response = await client.post(
            "/api/v1/auth/login-form",
            data={
                "username": "form-login@example.com",
                "password": "StrongPass123!",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "form-login@example.com"


@pytest.mark.anyio
async def test_login_form_invalid_credentials_returns_401_with_generic_detail():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login-form",
            data={
                "username": "missing-form@example.com",
                "password": "StrongPass123!",
            },
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


@pytest.mark.anyio
async def test_me_returns_public_user_for_valid_bearer_token():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        register_body = await _register_user(client, email="me-user@example.com")
        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {register_body['access_token']}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"id", "email", "full_name", "role", "created_at"}
    assert body["email"] == "me-user@example.com"


@pytest.mark.anyio
async def test_me_missing_token_returns_401_with_detail():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.anyio
async def test_me_invalid_token_returns_401_with_detail():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/auth/me",
            headers={"Authorization": "Bearer not-a-valid-token"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.anyio
async def test_versioned_me_is_not_implemented_now():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_versioned_json_login_is_not_implemented_now():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/auth/login")

    assert response.status_code == 404
