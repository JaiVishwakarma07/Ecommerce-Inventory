from datetime import datetime, timezone

from jose import jwt

from app.config import settings
from app.core.security import create_access_token, hash_password, verify_password


def test_hash_password_returns_non_plaintext_hash():
    password = "StrongPass123!"

    password_hash = hash_password(password)

    assert password_hash != password
    assert password_hash.startswith("$2")


def test_verify_password_accepts_valid_password():
    password = "StrongPass123!"
    password_hash = hash_password(password)

    assert verify_password(password, password_hash) is True
    assert verify_password("WrongPass123!", password_hash) is False


def test_create_access_token_contains_subject_and_expiry_claims():
    token = create_access_token("42")
    claims = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    now = int(datetime.now(timezone.utc).timestamp())
    expected_ttl_seconds = settings.access_token_expire_minutes * 60
    actual_ttl_seconds = claims["exp"] - claims["iat"]

    assert claims["sub"] == "42"
    assert claims["exp"] > now
    assert actual_ttl_seconds == expected_ttl_seconds
