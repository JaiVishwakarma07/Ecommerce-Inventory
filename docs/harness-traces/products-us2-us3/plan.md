# Product Detail (US2) + Admin Inventory (US3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver public `GET /products/{product_id}` (US2), then admin `POST` / `PUT` / `DELETE` on `/products` with JWT admin gating, duplicate-SKU handling, and `GET /products?limit=100` cap (US3).

**Architecture:** Three batches — US2 detail slice, shared foundation (auth deps + `ProductWrite` + repo/service CRUD), US3 write routes. Each batch follows router → service → repository; TDD RED→GREEN per checkpoint.

**Tech Stack:** FastAPI, SQLAlchemy 2.x async, Pydantic v2, python-jose JWT, pytest + httpx AsyncClient, structlog

**Scope source:** `docs/harness-traces/products-us2-us3/brainstorm.md`, `specs/002-product-catalog/spec.md` (US2–US3), `tasks.md` T019–T032

**Prerequisite:** US1 `GET /products` is implemented (`docs/harness-traces/get-products/plan.md`).

---

> This document defines **signatures and test names only** — no implementation bodies.

## File Map

| File | Role |
|------|------|
| `app/schemas/product.py` | `ProductWrite`, `ProductResponse` |
| `app/dependencies/auth.py` | Bearer extraction, `get_current_user`, `require_admin` |
| `app/repositories/product_repository.py` | `ProductRepository` (read + write + `limit`) |
| `app/services/product_service.py` | `ProductService`, domain exceptions |
| `app/routers/products.py` | US2 GET + US3 POST/PUT/DELETE + `limit` on list |
| `app/scripts/seed_admin.py` | Idempotent `admin@inventory.com` |
| `tests/conftest.py` | Admin/customer users + auth header fixtures |
| `tests/integration/test_products.py` | US2 + US3 HTTP tests |
| `tests/contract/test_products_contract.py` | OpenAPI alignment for detail + writes |
| `specs/002-product-catalog/quickstart.md` | Document `seed_admin` + env password |

---

## Execution Batches

| Batch | Delivers | Verify |
|-------|----------|--------|
| **1 — US2** | `GET /products/{product_id}` | `pytest … -k "detail or get_by_id"` |
| **2 — Foundation** | Auth deps, `ProductWrite`, repo/service CRUD, conftest, `seed_admin` | Unit/import smoke; US3 tests still RED |
| **3 — US3** | POST/PUT/DELETE + `?limit=` + error mapping | `pytest … -k "admin or create or update or delete"` |

---

## Domain Exceptions

```python
# app/services/product_service.py

class ProductNotFound(Exception):
    """Raised when product_id does not exist."""

class DuplicateSku(Exception):
    """Raised when sku violates unique constraint on create/update."""
```

```python
# app/repositories/product_repository.py (optional; may map IntegrityError in-repo)

class DuplicateSkuError(Exception):
    """Raised when INSERT/UPDATE hits unique constraint on sku."""
```

---

## Pydantic Schemas Needed

```python
# app/schemas/product.py
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class ProductWrite(BaseModel):
    """Request body for POST /products and PUT /products/{product_id}."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str
    sku: str = Field(min_length=1, max_length=255)
    price: Decimal = Field(ge=0)
    quantity: int = Field(ge=0)
    category: str = Field(min_length=1, max_length=100)
    image_url: str = ""

    @field_validator("image_url", mode="before")
    @classmethod
    def coerce_image_url(cls, value: object) -> str:
        ...

    @field_validator("price")
    @classmethod
    def validate_price_decimal_places(cls, value: Decimal) -> Decimal:
        """At most 2 decimal places (match contract multipleOf 0.01)."""
        ...


class ProductResponse(BaseModel):
    """Already exists (US1); unchanged contract except shared with writes."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str = Field(min_length=1, max_length=255)
    description: str
    sku: str = Field(min_length=1, max_length=255)
    price: Decimal
    quantity: int = Field(ge=0)
    category: str = Field(min_length=1, max_length=100)
    image_url: str = ""
    created_at: datetime
    updated_at: datetime

    @field_validator("image_url", mode="before")
    @classmethod
    def coerce_image_url(cls, value: object) -> str:
        ...

    @field_serializer("price")
    def serialize_price(self, price: Decimal) -> float:
        ...
```

**Auth types (existing — used by dependencies):**

```python
# app/schemas/auth.py — consumed, not modified in this harness
class RegisterUserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    created_at: datetime
```

---

## Auth Dependency Signatures

```python
# app/dependencies/auth.py
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_session_with_request
from app.schemas.auth import RegisterUserResponse
from app.services.auth_service import AuthService, UnauthenticatedError


def extract_bearer_token(
    authorization: str | None = Header(default=None),
) -> str:
    """
    Parse Authorization header.
  - Missing / non-Bearer → raise HTTPException 401, detail="Not authenticated"
    """


async def get_current_user(
    token: str = Depends(extract_bearer_token),
    db: AsyncSession = Depends(get_db_session_with_request),
    service: AuthService = Depends(get_auth_service),
) -> RegisterUserResponse:
    """
    Decode JWT, load user from DB via AuthService.get_current_user.
  - UnauthenticatedError → HTTPException 401, detail="Not authenticated"
    """


async def require_admin(
    current_user: RegisterUserResponse = Depends(get_current_user),
) -> RegisterUserResponse:
    """
  - role != "admin" → HTTPException 403, detail="Admin access required"
  - else return current_user
    """


def get_auth_service(...) -> AuthService:
    ...
```

---

## Repository Layer Signatures

```python
# app/repositories/product_repository.py
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import Product


class ProductRepository:
    async def list_products(
        self,
        db: AsyncSession,
        *,
        search: str | None = None,
        limit: int | None = None,
    ) -> list[Product]:
        """
        Existing search behavior (US1).
  - When limit is None: no SQL LIMIT.
  - When limit is set: LIMIT min(limit, 100).
        """

    async def get_by_id(
        self,
        db: AsyncSession,
        product_id: int,
    ) -> Product | None:
        """SELECT by primary key; None if missing."""

    async def create(
        self,
        db: AsyncSession,
        *,
        name: str,
        description: str,
        sku: str,
        price: Decimal,
        quantity: int,
        category: str,
        image_url: str,
    ) -> Product:
        """
        INSERT row; set created_at/updated_at.
  - IntegrityError on sku → raise DuplicateSkuError
        """

    async def update(
        self,
        db: AsyncSession,
        product_id: int,
        *,
        name: str,
        description: str,
        sku: str,
        price: Decimal,
        quantity: int,
        category: str,
        image_url: str,
    ) -> Product | None:
        """
        Full replace mutable fields; bump updated_at.
  - None if product_id not found.
  - IntegrityError on sku (other row) → raise DuplicateSkuError
        """

    async def delete(
        self,
        db: AsyncSession,
        product_id: int,
    ) -> bool:
        """Hard DELETE. Return True if a row was removed, False if not found."""
```

---

## Service Layer Signatures

```python
# app/services/product_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductResponse, ProductWrite


class ProductNotFound(Exception): ...
class DuplicateSku(Exception): ...


class ProductService:
    def __init__(self, repository: ProductRepository) -> None: ...

    async def list_products(
        self,
        db: AsyncSession,
        *,
        search: str | None = None,
        limit: int | None = None,
    ) -> list[ProductResponse]:
        ...

    async def get_product(
        self,
        db: AsyncSession,
        product_id: int,
    ) -> ProductResponse:
        """
  - get_by_id → ProductNotFound if None
  - else _to_response(product)
        """

    async def create_product(
        self,
        db: AsyncSession,
        payload: ProductWrite,
    ) -> ProductResponse:
        """
  - Normalize image_url (None → "").
  - repository.create → DuplicateSkuError → DuplicateSku
  - return _to_response(created)
        """

    async def update_product(
        self,
        db: AsyncSession,
        product_id: int,
        payload: ProductWrite,
    ) -> ProductResponse:
        """
  - repository.update → None → ProductNotFound
  - DuplicateSkuError → DuplicateSku
  - return _to_response(updated)
        """

    async def delete_product(
        self,
        db: AsyncSession,
        product_id: int,
    ) -> None:
        """
  - repository.delete → False → ProductNotFound
  - else return None (router responds 204)
        """

    @staticmethod
    def _to_response(product: Product) -> ProductResponse:
        """Map ORM → API; coerce image_url None → \"\"."""
        ...
```

---

## Router Signatures (reference)

```python
# app/routers/products.py — additions to existing router

@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: ProductService = Depends(get_product_service),
) -> ProductResponse:
    """ProductNotFound → 404 detail=\"Product not found\"; structlog product_get_*"""

@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    ...,
    limit: int | None = Query(default=None, ge=1, le=100),
) -> list[ProductResponse]:
    """Extend US1 handler: pass limit to service."""

@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(
    request: Request,
    payload: ProductWrite,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: ProductService = Depends(get_product_service),
    _admin: RegisterUserResponse = Depends(require_admin),
) -> ProductResponse:
    """DuplicateSku → 409; structlog product_create_*"""

@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    request: Request,
    product_id: int,
    payload: ProductWrite,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: ProductService = Depends(get_product_service),
    _admin: RegisterUserResponse = Depends(require_admin),
) -> ProductResponse:
    """ProductNotFound → 404; DuplicateSku → 409; structlog product_update_*"""

@router.delete("/products/{product_id}", status_code=204)
async def delete_product(
    request: Request,
    product_id: int,
    db: AsyncSession = Depends(get_db_session_with_request),
    service: ProductService = Depends(get_product_service),
    _admin: RegisterUserResponse = Depends(require_admin),
) -> None:
    """ProductNotFound → 404; empty body on 204; structlog product_delete_*"""
```

---

## Seed & Test Fixture Signatures

```python
# app/scripts/seed_admin.py
async def seed_admin(db: AsyncSession) -> int:
    """Insert admin@inventory.com if missing. Password from ECOM_OPPO_ADMIN_PASSWORD. Returns 0 or 1."""

async def main() -> None:
    """CLI: python -m app.scripts.seed_admin"""
```

```python
# tests/conftest.py — additions
async def create_admin_user(
    db: AsyncSession,
    *,
    email: str = "admin@inventory.com",
    password: str = "AdminPass123!",
    full_name: str = "Inventory Admin",
) -> User:
    """Insert user with role=\"admin\" via UserRepository."""

async def create_customer_user(
    db: AsyncSession,
    *,
    email: str = "customer@example.com",
    password: str = "CustomerPass123!",
    full_name: str = "Test Customer",
) -> User:
    """Insert user with role=\"customer\"."""

def auth_headers_for_user(user_id: int) -> dict[str, str]:
    """Return {\"Authorization\": \"Bearer <token>\"} using create_access_token."""

@pytest.fixture
async def admin_auth_headers(db_session: AsyncSession) -> dict[str, str]:
    ...

@pytest.fixture
async def customer_auth_headers(db_session: AsyncSession) -> dict[str, str]:
    ...

def product_write_payload(**overrides: object) -> dict[str, object]:
    """Default valid POST/PUT JSON body; merge overrides."""
```

---

## Exact Test Case Names And Assertions

### Batch 1 — US2 Contract (`tests/contract/test_products_contract.py`)

- `test_get_product_by_id_path_exists_in_contract`
  - asserts `"/products/{product_id}"` in OpenAPI `paths`
  - asserts `"get"` operation present
- `test_get_product_by_id_has_no_security_requirement`
  - asserts GET operation `security == []` (public)
- `test_get_product_by_id_response_is_product_schema`
  - asserts `200` response `$ref` is `#/components/schemas/Product`
- `test_get_product_by_id_404_uses_not_found_response`
  - asserts `404` response `$ref` is `#/components/responses/NotFound`

### Batch 1 — US2 Integration (`tests/integration/test_products.py`)

- `test_get_product_by_id_without_auth_returns_200`
  - asserts `GET /products/{id}` without `Authorization` returns `200`
- `test_get_product_by_id_returns_full_product_shape`
  - asserts body keys equal `PRODUCT_REQUIRED_FIELDS` (same set as list tests)
  - asserts `id` matches requested product
- `test_get_product_by_id_includes_zero_quantity_product`
  - asserts product seeded with `quantity=0` returns `200` and `quantity == 0`
- `test_get_product_by_id_unknown_returns_404_with_detail`
  - asserts `GET /products/999999` returns `404`
  - asserts `"detail" in body` and body is `dict`
- `test_get_product_by_id_non_integer_path_returns_422`
  - asserts `GET /products/not-an-id` returns `422`

### Batch 2 — US3 Contract (`tests/contract/test_products_contract.py`)

- `test_post_products_requires_bearer_auth`
  - asserts `POST /products` operation references `bearerAuth` (inherits global security or explicit)
- `test_put_products_by_id_requires_bearer_auth`
  - asserts `PUT /products/{product_id}` requires `bearerAuth`
- `test_delete_products_by_id_requires_bearer_auth`
  - asserts `DELETE /products/{product_id}` requires `bearerAuth`
- `test_post_products_request_body_is_product_write`
  - asserts POST `requestBody` schema `$ref` is `#/components/schemas/ProductWrite`
- `test_put_products_request_body_is_product_write`
  - asserts PUT `requestBody` schema `$ref` is `#/components/schemas/ProductWrite`
- `test_post_products_201_response_is_product`
  - asserts `201` response `$ref` is `#/components/schemas/Product`
- `test_product_write_schema_required_fields`
  - asserts `ProductWrite.required` includes `name`, `description`, `sku`, `price`, `quantity`, `category`, `image_url`

### Batch 2 — US3 Integration (`tests/integration/test_products.py`)

**POST /products**

- `test_create_product_as_admin_returns_201_with_id_and_timestamps`
  - asserts admin `POST /products` with valid body returns `201`
  - asserts response includes `id`, `created_at`, `updated_at`
  - asserts `sku` matches request
- `test_create_product_without_auth_returns_401`
  - asserts `POST /products` without header returns `401`
  - asserts `body["detail"] == "Not authenticated"`
- `test_create_product_as_customer_returns_403`
  - asserts customer Bearer on `POST /products` returns `403`
  - asserts `body["detail"] == "Admin access required"`
- `test_create_product_duplicate_sku_returns_409`
  - asserts second `POST` with same `sku` returns `409`
  - asserts `body["detail"] == "SKU already exists"`
- `test_create_product_invalid_payload_returns_422`
  - asserts `POST` with negative `price` or empty `name` returns `422`
  - asserts `detail` is a `list` (Pydantic validation)
- `test_create_product_omitted_image_url_defaults_to_empty_string`
  - asserts `POST` without `image_url` key returns `201`
  - asserts response `"image_url" == ""`

**PUT /products/{product_id}**

- `test_update_product_as_admin_returns_200`
  - asserts admin `PUT /products/{id}` returns `200`
  - asserts updated fields reflected in body (`name`, `price`, etc.)
- `test_update_product_without_auth_returns_401`
  - asserts no token → `401`, `detail == "Not authenticated"`
- `test_update_product_as_customer_returns_403`
  - asserts customer token → `403`, `detail == "Admin access required"`
- `test_update_product_unknown_id_returns_404`
  - asserts `PUT /products/999999` returns `404`, `detail == "Product not found"`
- `test_update_product_duplicate_sku_returns_409`
  - asserts changing `sku` to another product's sku → `409`, `detail == "SKU already exists"`

**DELETE /products/{product_id}**

- `test_delete_product_as_admin_returns_204_empty_body`
  - asserts admin `DELETE /products/{id}` returns `204`
  - asserts response body is empty
- `test_delete_product_without_auth_returns_401`
  - asserts no token → `401`
- `test_delete_product_as_customer_returns_403`
  - asserts customer token → `403`
- `test_delete_product_unknown_id_returns_404`
  - asserts `DELETE /products/999999` → `404`, `detail == "Product not found"`
- `test_get_product_after_delete_returns_404`
  - asserts after successful `DELETE`, `GET /products/{id}` → `404` (depends on US2)

**Admin list limit**

- `test_list_products_with_limit_100_caps_results_when_over_100_rows`
  - asserts after seeding 101+ products, `GET /products?limit=100` returns `200`
  - asserts `len(body) == 100`
- `test_list_products_without_limit_still_returns_all_when_over_100_rows`
  - asserts `GET /products` (no `limit`) still returns `len(body) >= 101` (US1 regression)

### Optional — Route Access Policy (polish / T037)

- `test_get_product_by_id_is_public_allowlisted`
  - asserts `GET /products/1` without token returns status `< 401`

---

## Task Checklist (TDD order)

### Batch 1 — US2

- [ ] **T019** Add US2 contract tests (names above) → run → expect FAIL
- [ ] **T020** Add US2 integration tests (names above) → run → expect FAIL
- [ ] **T022** Add `get_by_id` + `get_product` + `GET /products/{product_id}` signatures
- [ ] **T023** Add `product_get_*` structlog events
- [ ] **T024** Run `pytest tests/integration/test_products.py -k "detail or get_by_id" -v` → PASS

### Batch 2 — Foundation

- [ ] Add `ProductWrite` schema (signatures above)
- [ ] Create `app/dependencies/auth.py` (signatures above)
- [ ] Extend `ProductRepository` + `ProductService` with CRUD signatures
- [ ] Add `tests/conftest.py` admin/customer fixtures
- [ ] Add `app/scripts/seed_admin.py`
- [ ] Update `quickstart.md` for admin seed

### Batch 3 — US3

- [ ] **T025** Add US3 contract tests → run → expect FAIL
- [ ] **T026** Add US3 integration tests → run → expect FAIL
- [ ] **T028** Wire `Depends(require_admin)` on POST/PUT/DELETE
- [ ] **T029** Implement POST (201), PUT (200), DELETE (204) routes
- [ ] **T030** Map `ProductNotFound` / `DuplicateSku` to 404 / 409
- [ ] **T031** Add `product_create_*`, `product_update_*`, `product_delete_*` structlog
- [ ] Extend `list_products` router + repo with `limit` param
- [ ] **T032** Run `pytest tests/integration/test_products.py -k "admin or create or update or delete" -v` → PASS

---

## Spec Coverage Map

| Requirement | Test(s) |
|-------------|---------|
| FR-005 `GET /products/{id}` public | `test_get_product_by_id_*`, `test_get_product_by_id_has_no_security_requirement` |
| FR-006 admin writes | `test_*_requires_bearer_auth`, `test_create_product_as_admin_*` |
| FR-007 full body POST/PUT | `test_product_write_schema_required_fields`, create/update happy paths |
| FR-008 response with id/timestamps | `test_create_product_as_admin_returns_201_with_id_and_timestamps` |
| FR-009 duplicate SKU 409 | `test_create_product_duplicate_sku_returns_409`, `test_update_product_duplicate_sku_returns_409` |
| FR-010 hard delete 204 | `test_delete_product_as_admin_returns_204_empty_body` |
| FR-011 error `detail` shape | all `404`/`409`/`401`/`403` tests above |
| FR-012 401/403 auth | `test_*_without_auth_returns_401`, `test_*_as_customer_returns_403` |
| FR-013 zero qty in detail | `test_get_product_by_id_includes_zero_quantity_product` |
| FR-015 image_url never null | `test_create_product_omitted_image_url_defaults_to_empty_string` |
| Admin `limit=100` (US3 scenario 6) | `test_list_products_with_limit_100_caps_results_when_over_100_rows` |

---

## Self-Review

- **Spec coverage:** US2 acceptance scenarios + US3 scenarios 1–6 mapped to named tests above.
- **Placeholder scan:** None.
- **Type consistency:** `ProductWrite` in service create/update; repository uses explicit fields; router `response_model=ProductResponse`; delete returns `None` with `status_code=204`.
- **Batch order:** US2 GREEN before `test_get_product_after_delete_returns_404`.

---

## Verification Commands

```bash
# After Batch 1 (US2)
pytest tests/contract/test_products_contract.py tests/integration/test_products.py -k "detail or get_by_id or product_id" -v

# After Batch 3 (US3)
pytest tests/contract/test_products_contract.py tests/integration/test_products.py -k "admin or create or update or delete or limit_100" -v

# Full product suite
pytest tests/integration/test_products.py tests/contract/test_products_contract.py -v
```

---

## Execution Handoff

**Plan saved to** `docs/harness-traces/products-us2-us3/plan.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — run batches in this session with checkpoints after US2 and US3  

Which approach do you want?
