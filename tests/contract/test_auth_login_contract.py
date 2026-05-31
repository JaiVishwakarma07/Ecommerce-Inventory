from datetime import datetime, timezone


def test_login_request_accepts_email_and_password_only():
    from app.schemas.auth import LoginRequest

    payload = {
        "email": "login-contract@example.com",
        "password": "StrongPass123!",
        "full_name": "Ignored User",
    }

    request = LoginRequest.model_validate(payload)

    assert request.email == "login-contract@example.com"
    assert request.password == "StrongPass123!"
    assert not hasattr(request, "full_name")


def test_login_response_contains_access_token_token_type_user():
    from app.schemas.auth import RegisterResponse, RegisterUserResponse

    response = RegisterResponse(
        access_token="token",
        token_type="bearer",
        user=RegisterUserResponse(
            id=1,
            email="login-contract@example.com",
            full_name="Login Contract",
            role="customer",
            created_at=datetime.now(timezone.utc),
        ),
    )

    body = response.model_dump()

    assert set(body.keys()) == {"access_token", "token_type", "user"}


def test_current_user_response_excludes_password_fields():
    from app.schemas.auth import RegisterUserResponse

    response = RegisterUserResponse(
        id=1,
        email="me-contract@example.com",
        full_name="Me Contract",
        role="customer",
        created_at=datetime.now(timezone.utc),
    )

    body = response.model_dump()

    assert "password" not in body
    assert "password_hash" not in body
