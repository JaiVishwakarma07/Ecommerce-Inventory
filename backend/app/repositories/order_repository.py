from datetime import datetime, timezone
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderLineItem


class OrderLineSnapshot(TypedDict):
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal


class OrderRepository:
    async def create_with_line_items(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        shipping_address: str,
        total_amount: Decimal,
        lines: list[OrderLineSnapshot],
    ) -> Order:
        now = datetime.now(timezone.utc)
        order = Order(
            user_id=user_id,
            status="pending",
            total_amount=total_amount,
            shipping_address=shipping_address,
            stock_restored=False,
            created_at=now,
            updated_at=now,
        )
        db.add(order)
        await db.flush()
        for line in lines:
            db.add(
                OrderLineItem(
                    order_id=order.id,
                    product_id=line["product_id"],
                    product_name=line["product_name"],
                    quantity=line["quantity"],
                    unit_price=line["unit_price"],
                )
            )
        await db.flush()
        await db.refresh(order, attribute_names=["line_items"])
        return order

    async def get_by_id(
        self,
        db: AsyncSession,
        order_id: int,
    ) -> Order | None:
        result = await db.execute(
            select(Order)
            .options(selectinload(Order.line_items))
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> list[Order]:
        result = await db.execute(
            select(Order)
            .options(selectinload(Order.line_items))
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_all(
        self,
        db: AsyncSession,
        *,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[Order]:
        query = (
            select(Order)
            .options(selectinload(Order.line_items))
            .order_by(Order.created_at.desc())
        )
        if status is not None:
            query = query.where(Order.status == status)
        if limit is not None:
            query = query.limit(min(limit, 100))
        result = await db.execute(query)
        return list(result.scalars().all())

    async def update_status(
        self,
        db: AsyncSession,
        order: Order,
        *,
        status: str,
        stock_restored: bool | None = None,
    ) -> Order:
        order.status = status
        order.updated_at = datetime.now(timezone.utc)
        if stock_restored is not None:
            order.stock_restored = stock_restored
        await db.flush()
        await db.refresh(order, attribute_names=["line_items"])
        return order
