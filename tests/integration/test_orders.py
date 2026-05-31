"""Integration tests for orders API (US1 checkout + US2–US4 reads/admin)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import auth_headers_for_user, create_customer_user, order_checkout_payload

ORDER_KEYS = frozenset(
    {
        "id",
        "user_id",
        "status",
        "total_amount",
        "shipping_address",
        "created_at",
        "updated_at",
        "items",
    }
)


async def _async_client() -> AsyncIterator[AsyncClient]:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


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


async def count_orders(db: AsyncSession) -> int:
    from app.models.order import Order

    result = await db.execute(select(func.count()).select_from(Order))
    return int(result.scalar_one())


async def _checkout_order(
    client: AsyncClient,
    headers: dict[str, str],
    product_id: int,
    *,
    quantity: int = 1,
) -> dict[str, object]:
    response = await client.post(
        "/orders",
        json=order_checkout_payload(product_id, quantity=quantity),
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


async def set_order_status(
    db_session: AsyncSession,
    order_id: int,
    status: str,
) -> None:
    from sqlalchemy import select

    from app.models.order import Order

    result = await db_session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one()
    order.status = status
    order.updated_at = datetime.now(timezone.utc)
    await db_session.commit()


async def set_order_created_at(
    db_session: AsyncSession,
    order_id: int,
    created_at: datetime,
) -> None:
    from sqlalchemy import select

    from app.models.order import Order

    result = await db_session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one()
    order.created_at = created_at
    order.updated_at = created_at
    await db_session.commit()


async def seed_orders_for_user(
    db_session: AsyncSession,
    *,
    user_id: int,
    count: int,
) -> None:
    from app.models.order import Order, OrderLineItem

    base_time = datetime.now(timezone.utc)
    for index in range(count):
        created_at = base_time - timedelta(seconds=index)
        order = Order(
            user_id=user_id,
            status="pending",
            total_amount=Decimal("1.00"),
            shipping_address="US3 seed address",
            stock_restored=False,
            created_at=created_at,
            updated_at=created_at,
        )
        db_session.add(order)
        await db_session.flush()
        db_session.add(
            OrderLineItem(
                order_id=order.id,
                product_id=1,
                product_name="US3 Seed Product",
                quantity=1,
                unit_price=Decimal("1.00"),
            )
        )
    await db_session.commit()


async def _patch_order_status(
    client: AsyncClient,
    headers: dict[str, str],
    order_id: int,
    status: str,
) -> Response:
    return await client.patch(
        f"/orders/{order_id}/status",
        json={"status": status},
        headers=headers,
    )


async def _get_product_quantity(db_session: AsyncSession, product_id: int) -> int:
    from app.repositories.product_repository import ProductRepository

    product = await ProductRepository().get_by_id(db_session, product_id)
    assert product is not None
    return product.quantity


@pytest.mark.anyio
async def test_order_tables_exist_after_bootstrap(db_session: AsyncSession) -> None:
    bind = db_session.get_bind()

    def _table_names(sync_session: object) -> list[str]:
        from sqlalchemy import inspect

        bind = sync_session.get_bind()  # type: ignore[attr-defined]
        return list(inspect(bind).get_table_names())

    table_names = await db_session.run_sync(_table_names)
    assert "orders" in table_names
    assert "order_line_items" in table_names


@pytest.mark.anyio
async def test_post_orders_checkout_returns_201_with_snapshots_and_decrements_stock(
    db_session: AsyncSession,
    customer_auth_headers: dict[str, str],
) -> None:
    product = await insert_product(
        db_session,
        name="Wireless Mouse",
        sku="ORD-CHK-MOUSE-001",
        price=Decimal("799.00"),
        quantity=10,
    )
    body = order_checkout_payload(product.id, quantity=2)

    async for client in _async_client():
        response = await client.post(
            "/orders",
            json=body,
            headers=customer_auth_headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert set(data.keys()) == ORDER_KEYS
    assert data["status"] == "pending"
    assert len(data["items"]) == 1
    assert data["items"][0]["product_name"] == "Wireless Mouse"
    assert data["items"][0]["unit_price"] == 799.0
    assert data["total_amount"] == 1598.0

    from app.repositories.product_repository import ProductRepository

    refreshed = await ProductRepository().get_by_id(db_session, product.id)
    assert refreshed is not None
    assert refreshed.quantity == 8


@pytest.mark.anyio
async def test_post_orders_merge_duplicate_product_ids_in_request(
    db_session: AsyncSession,
    customer_auth_headers: dict[str, str],
) -> None:
    product = await insert_product(
        db_session,
        name="Merge Widget",
        sku="ORD-CHK-MERGE-001",
        price=Decimal("100.00"),
        quantity=20,
    )
    body = {
        "shipping_address": "1 Test St",
        "items": [
            {"product_id": product.id, "quantity": 2},
            {"product_id": product.id, "quantity": 3},
        ],
    }

    async for client in _async_client():
        response = await client.post(
            "/orders",
            json=body,
            headers=customer_auth_headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 5
    assert data["total_amount"] == 500.0


@pytest.mark.anyio
async def test_post_orders_insufficient_stock_returns_409_and_no_order_row(
    db_session: AsyncSession,
    customer_auth_headers: dict[str, str],
) -> None:
    product = await insert_product(
        db_session,
        name="Low Stock",
        sku="ORD-CHK-LOW-001",
        quantity=1,
    )
    orders_before = await count_orders(db_session)
    body = order_checkout_payload(product.id, quantity=5)

    async for client in _async_client():
        response = await client.post(
            "/orders",
            json=body,
            headers=customer_auth_headers,
        )

    assert response.status_code == 409
    assert "product_id" in response.json()["detail"].lower()
    assert await count_orders(db_session) == orders_before

    from app.repositories.product_repository import ProductRepository

    refreshed = await ProductRepository().get_by_id(db_session, product.id)
    assert refreshed is not None
    assert refreshed.quantity == 1


@pytest.mark.anyio
async def test_post_orders_missing_product_returns_404(
    customer_auth_headers: dict[str, str],
) -> None:
    body = order_checkout_payload(product_id=999_999, quantity=1)

    async for client in _async_client():
        response = await client.post(
            "/orders",
            json=body,
            headers=customer_auth_headers,
        )

    assert response.status_code == 404
    detail = response.json()["detail"].lower()
    assert "product" in detail


@pytest.mark.anyio
async def test_post_orders_as_admin_returns_403(
    db_session: AsyncSession,
    admin_auth_headers: dict[str, str],
) -> None:
    product = await insert_product(
        db_session,
        name="Admin Block",
        sku="ORD-CHK-ADMIN-001",
    )
    body = order_checkout_payload(product.id)

    async for client in _async_client():
        response = await client.post(
            "/orders",
            json=body,
            headers=admin_auth_headers,
        )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_post_orders_without_token_returns_401() -> None:
    body = order_checkout_payload(product_id=1)

    async for client in _async_client():
        response = await client.post("/orders", json=body)

    assert response.status_code == 401


@pytest.mark.anyio
async def test_post_orders_empty_items_returns_422(
    customer_auth_headers: dict[str, str],
) -> None:
    body = {"shipping_address": "1 Test St", "items": []}

    async for client in _async_client():
        response = await client.post(
            "/orders",
            json=body,
            headers=customer_auth_headers,
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_post_orders_empty_shipping_address_returns_422(
    customer_auth_headers: dict[str, str],
) -> None:
    body = {"shipping_address": "   ", "items": [{"product_id": 1, "quantity": 1}]}

    async for client in _async_client():
        response = await client.post(
            "/orders",
            json=body,
            headers=customer_auth_headers,
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_post_orders_invalid_quantity_returns_422(
    customer_auth_headers: dict[str, str],
) -> None:
    body = {
        "shipping_address": "1 Test St",
        "items": [{"product_id": 1, "quantity": 0}],
    }

    async for client in _async_client():
        response = await client.post(
            "/orders",
            json=body,
            headers=customer_auth_headers,
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_get_orders_me_returns_only_own_orders(
    db_session: AsyncSession,
) -> None:
    customer_a = await create_customer_user(
        db_session,
        email="customer-a-orders@example.com",
        full_name="Customer A",
    )
    customer_b = await create_customer_user(
        db_session,
        email="customer-b-orders@example.com",
        full_name="Customer B",
    )
    headers_a = auth_headers_for_user(customer_a.id)
    headers_b = auth_headers_for_user(customer_b.id)

    product = await insert_product(
        db_session,
        name="US2 List Product",
        sku="ORD-US2-LIST-001",
    )

    async for client in _async_client():
        checkout = await _checkout_order(client, headers_a, product.id)
        assert checkout["user_id"] == customer_a.id

        response_a = await client.get("/orders/me", headers=headers_a)
        response_b = await client.get("/orders/me", headers=headers_b)

    assert response_a.status_code == 200
    orders_a = response_a.json()
    assert len(orders_a) == 1
    assert orders_a[0]["user_id"] == customer_a.id
    assert orders_a[0]["id"] == checkout["id"]

    assert response_b.status_code == 200
    assert response_b.json() == []


@pytest.mark.anyio
async def test_get_order_by_id_returns_own_order(
    db_session: AsyncSession,
    customer_auth_headers: dict[str, str],
) -> None:
    product = await insert_product(
        db_session,
        name="US2 Detail Product",
        sku="ORD-US2-DETAIL-001",
        price=Decimal("799.00"),
    )

    async for client in _async_client():
        checkout = await _checkout_order(
            client,
            customer_auth_headers,
            product.id,
            quantity=2,
        )
        order_id = checkout["id"]
        response = await client.get(
            f"/orders/{order_id}",
            headers=customer_auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == ORDER_KEYS
    assert data["id"] == order_id
    assert data["items"][0]["product_name"] == checkout["items"][0]["product_name"]
    assert data["items"][0]["unit_price"] == checkout["items"][0]["unit_price"]


@pytest.mark.anyio
async def test_get_order_by_id_forbidden_for_other_customer(
    db_session: AsyncSession,
) -> None:
    customer_a = await create_customer_user(
        db_session,
        email="customer-a-forbidden@example.com",
    )
    customer_b = await create_customer_user(
        db_session,
        email="customer-b-forbidden@example.com",
    )
    headers_a = auth_headers_for_user(customer_a.id)
    headers_b = auth_headers_for_user(customer_b.id)

    product = await insert_product(
        db_session,
        name="US2 Forbidden Product",
        sku="ORD-US2-FORBID-001",
    )

    async for client in _async_client():
        checkout = await _checkout_order(client, headers_a, product.id)
        order_id = checkout["id"]
        response = await client.get(f"/orders/{order_id}", headers=headers_b)

    assert response.status_code == 403
    assert "detail" in response.json()


@pytest.mark.anyio
async def test_get_order_by_id_allowed_for_admin(
    db_session: AsyncSession,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    product = await insert_product(
        db_session,
        name="US2 Admin Read Product",
        sku="ORD-US2-ADMIN-001",
    )

    async for client in _async_client():
        checkout = await _checkout_order(client, customer_auth_headers, product.id)
        order_id = checkout["id"]
        response = await client.get(f"/orders/{order_id}", headers=admin_auth_headers)

    assert response.status_code == 200
    assert response.json()["id"] == order_id


@pytest.mark.anyio
async def test_get_order_by_id_not_found(
    customer_auth_headers: dict[str, str],
) -> None:
    async for client in _async_client():
        response = await client.get("/orders/999999", headers=customer_auth_headers)

    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.anyio
async def test_get_orders_me_without_token_returns_401() -> None:
    async for client in _async_client():
        response = await client.get("/orders/me")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_order_by_id_without_token_returns_401() -> None:
    async for client in _async_client():
        response = await client.get("/orders/1")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_orders_admin_returns_all_orders_newest_first(
    db_session: AsyncSession,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    product = await insert_product(
        db_session,
        name="US3 List Product",
        sku="ORD-US3-LIST-001",
        quantity=50,
    )

    async for client in _async_client():
        first = await _checkout_order(client, customer_auth_headers, product.id)
        second = await _checkout_order(client, customer_auth_headers, product.id)
        older = datetime.now(timezone.utc) - timedelta(hours=1)
        await set_order_created_at(db_session, int(first["id"]), older)

        response = await client.get("/orders", headers=admin_auth_headers)

    assert response.status_code == 200
    orders = response.json()
    assert len(orders) >= 2
    ids = [order["id"] for order in orders]
    assert int(second["id"]) in ids
    assert int(first["id"]) in ids
    assert orders[0]["created_at"] >= orders[1]["created_at"]


@pytest.mark.anyio
async def test_get_orders_admin_filters_by_status(
    db_session: AsyncSession,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    product = await insert_product(
        db_session,
        name="US3 Filter Product",
        sku="ORD-US3-FILTER-001",
        quantity=50,
    )

    async for client in _async_client():
        pending_order = await _checkout_order(client, customer_auth_headers, product.id)
        shipped_order = await _checkout_order(client, customer_auth_headers, product.id)
        await set_order_status(db_session, int(shipped_order["id"]), "shipped")

        response = await client.get(
            "/orders",
            params={"status": "shipped"},
            headers=admin_auth_headers,
        )

    assert response.status_code == 200
    orders = response.json()
    assert len(orders) == 1
    assert orders[0]["id"] == shipped_order["id"]
    assert orders[0]["status"] == "shipped"
    assert orders[0]["id"] != pending_order["id"]


@pytest.mark.anyio
async def test_get_orders_admin_respects_limit(
    db_session: AsyncSession,
    admin_auth_headers: dict[str, str],
) -> None:
    customer = await create_customer_user(
        db_session,
        email="us3-limit-customer@example.com",
    )
    headers = auth_headers_for_user(customer.id)
    product = await insert_product(
        db_session,
        name="US3 Limit Product",
        sku="ORD-US3-LIMIT-001",
        quantity=50,
    )

    async for client in _async_client():
        for _ in range(3):
            await _checkout_order(client, headers, product.id)

        response = await client.get(
            "/orders",
            params={"limit": 2},
            headers=admin_auth_headers,
        )

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.anyio
async def test_get_orders_admin_limit_over_100_capped(
    db_session: AsyncSession,
    admin_auth_headers: dict[str, str],
) -> None:
    customer = await create_customer_user(
        db_session,
        email="us3-cap-customer@example.com",
    )
    await seed_orders_for_user(db_session, user_id=customer.id, count=101)

    async for client in _async_client():
        response = await client.get(
            "/orders",
            params={"limit": 200},
            headers=admin_auth_headers,
        )

    assert response.status_code == 200
    assert len(response.json()) == 100


@pytest.mark.anyio
async def test_get_orders_admin_as_customer_returns_403(
    customer_auth_headers: dict[str, str],
) -> None:
    async for client in _async_client():
        response = await client.get("/orders", headers=customer_auth_headers)

    assert response.status_code == 403
    assert "detail" in response.json()


@pytest.mark.anyio
async def test_get_orders_admin_invalid_status_returns_422(
    admin_auth_headers: dict[str, str],
) -> None:
    async for client in _async_client():
        response = await client.get(
            "/orders",
            params={"status": "invalid"},
            headers=admin_auth_headers,
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_get_orders_admin_without_token_returns_401() -> None:
    async for client in _async_client():
        response = await client.get("/orders")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_patch_order_status_returns_200_with_updated_order(
    db_session: AsyncSession,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    product = await insert_product(
        db_session,
        name="US4 Status Product",
        sku="ORD-US4-STATUS-001",
        quantity=10,
    )

    async for client in _async_client():
        checkout = await _checkout_order(client, customer_auth_headers, product.id)
        order_id = int(checkout["id"])
        response = await _patch_order_status(
            client,
            admin_auth_headers,
            order_id,
            "processing",
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == order_id
    assert data["status"] == "processing"
    assert "updated_at" in data


@pytest.mark.anyio
async def test_patch_cancel_restock_once(
    db_session: AsyncSession,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    product = await insert_product(
        db_session,
        name="US4 Restock Product",
        sku="ORD-US4-RESTOCK-001",
        quantity=10,
    )

    async for client in _async_client():
        checkout = await _checkout_order(
            client,
            customer_auth_headers,
            product.id,
            quantity=2,
        )
        order_id = int(checkout["id"])
        assert await _get_product_quantity(db_session, product.id) == 8

        response = await _patch_order_status(
            client,
            admin_auth_headers,
            order_id,
            "cancelled",
        )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert await _get_product_quantity(db_session, product.id) == 10


@pytest.mark.anyio
async def test_patch_cancel_idempotent_no_double_restock(
    db_session: AsyncSession,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    product = await insert_product(
        db_session,
        name="US4 Idempotent Product",
        sku="ORD-US4-IDEM-001",
        quantity=10,
    )

    async for client in _async_client():
        checkout = await _checkout_order(
            client,
            customer_auth_headers,
            product.id,
            quantity=2,
        )
        order_id = int(checkout["id"])

        first_cancel = await _patch_order_status(
            client,
            admin_auth_headers,
            order_id,
            "cancelled",
        )
        assert first_cancel.status_code == 200
        assert await _get_product_quantity(db_session, product.id) == 10

        second_cancel = await _patch_order_status(
            client,
            admin_auth_headers,
            order_id,
            "cancelled",
        )

    assert second_cancel.status_code == 200
    assert await _get_product_quantity(db_session, product.id) == 10


@pytest.mark.anyio
async def test_patch_cancel_skips_restock_when_product_deleted(
    db_session: AsyncSession,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    product_keep = await insert_product(
        db_session,
        name="US4 Keep Product",
        sku="ORD-US4-KEEP-001",
        quantity=10,
    )
    product_delete = await insert_product(
        db_session,
        name="US4 Delete Product",
        sku="ORD-US4-DEL-001",
        quantity=5,
    )
    body = order_checkout_payload(
        product_keep.id,
        quantity=1,
        extra_items=[{"product_id": product_delete.id, "quantity": 2}],
    )

    async for client in _async_client():
        checkout_response = await client.post(
            "/orders",
            json=body,
            headers=customer_auth_headers,
        )
        assert checkout_response.status_code == 201
        order_id = int(checkout_response.json()["id"])
        assert await _get_product_quantity(db_session, product_keep.id) == 9
        assert await _get_product_quantity(db_session, product_delete.id) == 3

        delete_response = await client.delete(
            f"/products/{product_delete.id}",
            headers=admin_auth_headers,
        )
        assert delete_response.status_code == 204

        patch_response = await _patch_order_status(
            client,
            admin_auth_headers,
            order_id,
            "cancelled",
        )

    assert patch_response.status_code == 200
    assert await _get_product_quantity(db_session, product_keep.id) == 10
    from app.repositories.product_repository import ProductRepository

    assert await ProductRepository().get_by_id(db_session, product_delete.id) is None


@pytest.mark.anyio
async def test_patch_order_status_as_customer_returns_403(
    db_session: AsyncSession,
    customer_auth_headers: dict[str, str],
) -> None:
    product = await insert_product(
        db_session,
        name="US4 Customer Forbidden",
        sku="ORD-US4-CUST-403",
        quantity=10,
    )

    async for client in _async_client():
        checkout = await _checkout_order(client, customer_auth_headers, product.id)
        order_id = int(checkout["id"])
        response = await _patch_order_status(
            client,
            customer_auth_headers,
            order_id,
            "processing",
        )

    assert response.status_code == 403
    assert "detail" in response.json()


@pytest.mark.anyio
async def test_patch_order_status_not_found(
    admin_auth_headers: dict[str, str],
) -> None:
    async for client in _async_client():
        response = await _patch_order_status(
            client,
            admin_auth_headers,
            999_999,
            "cancelled",
        )

    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.anyio
async def test_patch_order_status_without_token_returns_401() -> None:
    async for client in _async_client():
        response = await client.patch(
            "/orders/1/status",
            json={"status": "cancelled"},
        )

    assert response.status_code == 401
