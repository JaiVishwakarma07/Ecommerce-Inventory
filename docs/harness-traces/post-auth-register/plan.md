# POST /auth/register Signatures-Only Plan

> Scope source: `docs/harness-traces/post-auth-register/brainstorm.md`  
> Canonical route in approved brainstorm: `POST /auth/register`

## Service Layer Signatures

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.auth import RegisterRequest, RegisterResponse

class AuthService:
    async def register_user(
        self,
        db: AsyncSession,
        payload: RegisterRequest,
    ) -> RegisterResponse: ...
```

## Repository Layer Signatures

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User

class UserRepository:
    async def get_by_email(
        self,
        db: AsyncSession,
        email: str,
    ) -> User | None: ...

    async def create_user(
        self,
        db: AsyncSession,
        *,
        email: str,
        password_hash: str,
        full_name: str,
        role: str = "customer",
    ) -> User: ...
```

## Pydantic Schemas Needed

```python
from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str

class RegisterUserView(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    created_at: datetime

class RegisterResponse(BaseModel):
    access_token: str
    token_type: str
    user: RegisterUserView

class ErrorPayload(BaseModel):
    code: str
    message: str

class ErrorResponse(BaseModel):
    error: ErrorPayload
```

## Exact Test Case Names And Assertions

### Contract Tests (`tests/contract/test_auth_contract.py`)

- `test_register_accepts_email_full_name_password_only`
  - asserts request schema accepts `email`, `full_name`, `password`
  - asserts unknown/extra fields are rejected or ignored per schema policy
- `test_register_response_contains_access_token_token_type_user`
  - asserts response keys include `access_token`, `token_type`, `user`
- `test_register_response_excludes_password_fields`
  - asserts `password` and `password_hash` are absent in response JSON

### Integration Tests (`tests/integration/test_auth_endpoints.py`)

- `test_register_success_returns_200_and_valid_payload`
  - asserts status code `200`
  - asserts `token_type == "bearer"`
  - asserts `user.email` matches input email
- `test_register_duplicate_email_returns_409`
  - asserts second registration for same normalized email returns `409`
- `test_register_invalid_payload_returns_400`
  - asserts invalid email/missing required fields returns `400`
- `test_register_forces_customer_role_on_self_registration`
  - asserts persisted/returned role is always `customer`

### Unit Tests (`tests/unit/test_security.py`, `tests/unit/test_auth_service.py`)

- `test_hash_password_returns_non_plaintext_hash`
  - asserts hashed password differs from raw input
- `test_verify_password_accepts_valid_password`
  - asserts verify helper returns `True` for matching pair
- `test_create_access_token_contains_subject_and_expiry_claims`
  - asserts token payload includes `sub` and `exp` with 24h TTL intent
- `test_register_service_normalizes_email_before_lookup_and_create`
  - asserts email normalization is applied before repository calls
- `test_register_service_raises_conflict_for_existing_email`
  - asserts duplicate email path maps to conflict error behavior
