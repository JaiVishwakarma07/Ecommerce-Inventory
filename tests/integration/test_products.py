"""Integration tests for GET /products (US1 browse slice)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import product_write_payload

PRODUCT_KEYS = frozenset(
    {
        "id",
        "name",
        "description",
        "sku",
        "price",
        "quantity",
        "category",
        "image_url",
        "created_at",
        "updated_at",
    }
)


async def _async_client() -> AsyncIterator[AsyncClient]:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _db_session() -> AsyncIterator[AsyncSession]:
    from app.database import get_db_session

    async for session in get_db_session():
        yield session


async def insert_product(
    db: AsyncSession,
    *,
    name: str,
    sku: str,
    price: Decimal = Decimal("9.99"),
    quantity: int = 10,
    category: str = "general",
    description: str = "",
    image_url: str = "",
) -> object:
    from app.models.product import Product

    product = Product(
        name=name,
        description=description,
        sku=sku,
        price=price,
        quantity=quantity,
        category=category,
        image_url=image_url,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def insert_products_bulk(
    db: AsyncSession,
    count: int,
    *,
    prefix: str = "SKU",
) -> list[object]:
    products: list[object] = []
    for index in range(count):
        product = await insert_product(
            db,
            name=f"Product {index}",
            sku=f"{prefix}-{index:04d}",
            price=Decimal("1.00"),
            quantity=1,
            category="bulk",
        )
        products.append(product)
    return products


@pytest.mark.anyio
async def test_list_products_without_auth_returns_200_and_array():
    async for client in _async_client():
        response = await client.get("/products")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)


@pytest.mark.anyio
async def test_list_products_empty_catalog_returns_empty_array():
    async for client in _async_client():
        response = await client.get("/products")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_list_products_returns_product_shape():
    async for session in _db_session():
        await insert_product(
            session,
            name="Shape Widget",
            sku="SHAPE-001",
            description="Desc",
            category="gadgets",
        )

    async for client in _async_client():
        response = await client.get("/products")

    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    item = body[0]
    assert set(item.keys()) == PRODUCT_KEYS
    assert "password" not in item
    assert "password_hash" not in item


@pytest.mark.anyio
async def test_list_products_image_url_never_null():
    async for session in _db_session():
        await insert_product(
            session,
            name="No Image",
            sku="IMG-001",
            image_url="",
        )

    async for client in _async_client():
        response = await client.get("/products")

    assert response.status_code == 200
    for item in response.json():
        assert "image_url" in item
        assert item["image_url"] is not None
        assert isinstance(item["image_url"], str)


@pytest.mark.anyio
async def test_list_products_includes_zero_quantity_item():
    async for session in _db_session():
        await insert_product(
            session,
            name="Out of Stock",
            sku="OUT-003",
            quantity=0,
        )

    async for client in _async_client():
        response = await client.get("/products")

    assert response.status_code == 200
    skus = {item["sku"] for item in response.json()}
    assert "OUT-003" in skus


@pytest.mark.anyio
async def test_list_products_search_matches_name():
    async for session in _db_session():
        await insert_product(session, name="Super Widget", sku="NAM-001")
        await insert_product(session, name="Other Item", sku="NAM-002")

    async for client in _async_client():
        response = await client.get("/products", params={"search": "widget"})

    assert response.status_code == 200
    names = [item["name"] for item in response.json()]
    assert names == ["Super Widget"]
    assert all("widget" in name.lower() for name in names)


@pytest.mark.anyio
async def test_list_products_search_matches_sku():
    async for session in _db_session():
        await insert_product(session, name="SKU Target", sku="WGT-001")
        await insert_product(session, name="SKU Other", sku="ABC-999")

    async for client in _async_client():
        response = await client.get("/products", params={"search": "wgt-001"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["sku"] == "WGT-001"


@pytest.mark.anyio
async def test_list_products_search_matches_category():
    async for session in _db_session():
        await insert_product(
            session,
            name="Phone",
            sku="CAT-001",
            category="electronics",
        )
        await insert_product(
            session,
            name="Shirt",
            sku="CAT-002",
            category="apparel",
        )

    async for client in _async_client():
        response = await client.get("/products", params={"search": "electronics"})

    assert response.status_code == 200
    categories = {item["category"] for item in response.json()}
    assert categories == {"electronics"}


@pytest.mark.anyio
async def test_list_products_search_whitespace_only_returns_all():
    async for session in _db_session():
        await insert_product(session, name="One", sku="WS-001")
        await insert_product(session, name="Two", sku="WS-002")

    async for client in _async_client():
        unfiltered = await client.get("/products")
        whitespace = await client.get("/products", params={"search": "  "})

    assert unfiltered.status_code == 200
    assert whitespace.status_code == 200
    assert len(whitespace.json()) == len(unfiltered.json())


@pytest.mark.anyio
async def test_list_products_without_limit_returns_all_when_over_100_rows():
    async for session in _db_session():
        await insert_products_bulk(session, 101, prefix="BULK")

    async for client in _async_client():
        response = await client.get("/products")

    assert response.status_code == 200
    assert len(response.json()) >= 101


@pytest.mark.anyio
async def test_list_products_price_is_numeric_json():
    async for session in _db_session():
        await insert_product(
            session,
            name="Priced",
            sku="PRC-001",
            price=Decimal("19.99"),
        )

    async for client in _async_client():
        response = await client.get("/products")

    assert response.status_code == 200
    price = response.json()[0]["price"]
    assert isinstance(price, (int, float))
    assert not isinstance(price, str)


@pytest.mark.anyio
async def test_list_products_quantity_is_integer_json():
    async for session in _db_session():
        await insert_product(session, name="Stocked", sku="QTY-001", quantity=7)

    async for client in _async_client():
        response = await client.get("/products")

    assert response.status_code == 200
    quantity = response.json()[0]["quantity"]
    assert isinstance(quantity, int)
    assert not isinstance(quantity, bool)


# --- US2: GET /products/{product_id} (T020) ---


@pytest.mark.anyio
async def test_get_product_by_id_without_auth_returns_200():
    async for session in _db_session():
        product = await insert_product(
            session,
            name="Detail Widget",
            sku="DET-001",
        )

    async for client in _async_client():
        response = await client.get(f"/products/{product.id}")

    assert response.status_code == 200


@pytest.mark.anyio
async def test_get_product_by_id_returns_full_product_shape():
    async for session in _db_session():
        product = await insert_product(
            session,
            name="Shape Detail",
            sku="DET-SHAPE",
            description="Full desc",
            category="gadgets",
        )

    async for client in _async_client():
        response = await client.get(f"/products/{product.id}")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == PRODUCT_KEYS
    assert body["id"] == product.id


@pytest.mark.anyio
async def test_get_product_by_id_includes_zero_quantity_product():
    async for session in _db_session():
        product = await insert_product(
            session,
            name="Zero Stock Detail",
            sku="DET-ZERO",
            quantity=0,
        )

    async for client in _async_client():
        response = await client.get(f"/products/{product.id}")

    assert response.status_code == 200
    assert response.json()["quantity"] == 0


@pytest.mark.anyio
async def test_get_product_by_id_unknown_returns_404_with_detail():
    async for client in _async_client():
        response = await client.get("/products/999999")

    assert response.status_code == 404
    body = response.json()
    assert isinstance(body, dict)
    assert "detail" in body


@pytest.mark.anyio
async def test_get_product_by_id_non_integer_path_returns_422():
    async for client in _async_client():
        response = await client.get("/products/not-an-id")

    assert response.status_code == 422


# --- US3: POST/PUT/DELETE /products (T026) ---


@pytest.mark.anyio
async def test_create_product_as_admin_returns_201_with_id_and_timestamps(
    admin_auth_headers: dict[str, str],
):
    payload = product_write_payload(sku="CREATE-ADMIN-001")

    async for client in _async_client():
        response = await client.post(
            "/products",
            json=payload,
            headers=admin_auth_headers,
        )

    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body
    assert body["sku"] == payload["sku"]


@pytest.mark.anyio
async def test_create_product_without_auth_returns_401():
    async for client in _async_client():
        response = await client.post(
            "/products",
            json=product_write_payload(sku="CREATE-NOAUTH-001"),
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.anyio
async def test_create_product_as_customer_returns_403(
    customer_auth_headers: dict[str, str],
):
    async for client in _async_client():
        response = await client.post(
            "/products",
            json=product_write_payload(sku="CREATE-CUST-001"),
            headers=customer_auth_headers,
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


@pytest.mark.anyio
async def test_create_product_duplicate_sku_returns_409(
    admin_auth_headers: dict[str, str],
):
    payload = product_write_payload(sku="DUP-SKU-001")

    async for client in _async_client():
        first = await client.post(
            "/products",
            json=payload,
            headers=admin_auth_headers,
        )
        second = await client.post(
            "/products",
            json=product_write_payload(sku="DUP-SKU-001", name="Duplicate"),
            headers=admin_auth_headers,
        )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "SKU already exists"


@pytest.mark.anyio
async def test_create_product_invalid_payload_returns_422(
    admin_auth_headers: dict[str, str],
):
    async for client in _async_client():
        negative_price = await client.post(
            "/products",
            json=product_write_payload(price=-1, sku="INV-PRICE-001"),
            headers=admin_auth_headers,
        )
        empty_name = await client.post(
            "/products",
            json=product_write_payload(name="", sku="INV-NAME-001"),
            headers=admin_auth_headers,
        )

    for response in (negative_price, empty_name):
        assert response.status_code == 422
        assert isinstance(response.json()["detail"], list)


@pytest.mark.anyio
async def test_create_product_omitted_image_url_defaults_to_empty_string(
    admin_auth_headers: dict[str, str],
):
    payload = product_write_payload(sku="NO-IMG-001")
    payload.pop("image_url", None)

    async for client in _async_client():
        response = await client.post(
            "/products",
            json=payload,
            headers=admin_auth_headers,
        )

    assert response.status_code == 201
    assert response.json()["image_url"] == ""


@pytest.mark.anyio
async def test_update_product_as_admin_returns_200(
    admin_auth_headers: dict[str, str],
):
    async for session in _db_session():
        product = await insert_product(
            session,
            name="Before Update",
            sku="UPD-001",
            price=Decimal("10.00"),
        )

    update_body = product_write_payload(
        name="After Update",
        sku="UPD-001",
        price=25.5,
        quantity=3,
        category="updated",
        description="Updated desc",
    )

    async for client in _async_client():
        response = await client.put(
            f"/products/{product.id}",
            json=update_body,
            headers=admin_auth_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "After Update"
    assert body["price"] == 25.5
    assert body["quantity"] == 3
    assert body["category"] == "updated"


@pytest.mark.anyio
async def test_update_product_without_auth_returns_401():
    async for session in _db_session():
        product = await insert_product(session, name="Auth Update", sku="UPD-AUTH-001")

    async for client in _async_client():
        response = await client.put(
            f"/products/{product.id}",
            json=product_write_payload(sku="UPD-AUTH-001"),
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.anyio
async def test_update_product_as_customer_returns_403(
    customer_auth_headers: dict[str, str],
):
    async for session in _db_session():
        product = await insert_product(session, name="Cust Update", sku="UPD-CUST-001")

    async for client in _async_client():
        response = await client.put(
            f"/products/{product.id}",
            json=product_write_payload(sku="UPD-CUST-001"),
            headers=customer_auth_headers,
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


@pytest.mark.anyio
async def test_update_product_unknown_id_returns_404(
    admin_auth_headers: dict[str, str],
):
    async for client in _async_client():
        response = await client.put(
            "/products/999999",
            json=product_write_payload(sku="UPD-MISSING-001"),
            headers=admin_auth_headers,
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


@pytest.mark.anyio
async def test_update_product_duplicate_sku_returns_409(
    admin_auth_headers: dict[str, str],
):
    async for session in _db_session():
        first = await insert_product(session, name="First", sku="SKU-A-001")
        second = await insert_product(session, name="Second", sku="SKU-B-001")

    async for client in _async_client():
        response = await client.put(
            f"/products/{second.id}",
            json=product_write_payload(sku=first.sku, name="Second"),
            headers=admin_auth_headers,
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "SKU already exists"


@pytest.mark.anyio
async def test_delete_product_as_admin_returns_204_empty_body(
    admin_auth_headers: dict[str, str],
):
    async for session in _db_session():
        product = await insert_product(session, name="Delete Me", sku="DEL-001")

    async for client in _async_client():
        response = await client.delete(
            f"/products/{product.id}",
            headers=admin_auth_headers,
        )

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.anyio
async def test_delete_product_without_auth_returns_401():
    async for session in _db_session():
        product = await insert_product(session, name="Delete Auth", sku="DEL-AUTH-001")

    async for client in _async_client():
        response = await client.delete(f"/products/{product.id}")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_delete_product_as_customer_returns_403(
    customer_auth_headers: dict[str, str],
):
    async for session in _db_session():
        product = await insert_product(session, name="Delete Cust", sku="DEL-CUST-001")

    async for client in _async_client():
        response = await client.delete(
            f"/products/{product.id}",
            headers=customer_auth_headers,
        )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_delete_product_unknown_id_returns_404(
    admin_auth_headers: dict[str, str],
):
    async for client in _async_client():
        response = await client.delete(
            "/products/999999",
            headers=admin_auth_headers,
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


@pytest.mark.anyio
async def test_get_product_after_delete_returns_404(
    admin_auth_headers: dict[str, str],
):
    async for session in _db_session():
        product = await insert_product(session, name="Gone", sku="DEL-GONE-001")

    async for client in _async_client():
        delete_response = await client.delete(
            f"/products/{product.id}",
            headers=admin_auth_headers,
        )
        get_response = await client.get(f"/products/{product.id}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


@pytest.mark.anyio
async def test_list_products_with_limit_100_caps_results_when_over_100_rows(
    admin_auth_headers: dict[str, str],
):
    async for session in _db_session():
        await insert_products_bulk(session, 101, prefix="LIMIT")

    async for client in _async_client():
        response = await client.get(
            "/products",
            params={"limit": 100},
            headers=admin_auth_headers,
        )

    assert response.status_code == 200
    assert len(response.json()) == 100
