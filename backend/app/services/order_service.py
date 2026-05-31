from decimal import Decimal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.repositories.order_repository import OrderLineSnapshot, OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.order import OrderCreate, OrderLineItemCreate, OrderLineItemResponse, OrderResponse

logger = structlog.get_logger(__name__)


class InsufficientStockError(Exception):
    def __init__(self, product_id: int) -> None:
        self.product_id = product_id
        super().__init__(f"Insufficient stock for product_id {product_id}")


class ProductNotFoundForOrderError(Exception):
    def __init__(self, product_id: int) -> None:
        self.product_id = product_id
        super().__init__(f"Product {product_id} not found")


class OrderNotFoundError(Exception):
    def __init__(self, message: str = "Order not found") -> None:
        super().__init__(message)


class ForbiddenOrderAccessError(Exception):
    def __init__(self, message: str = "Not allowed to access this order") -> None:
        super().__init__(message)


def merge_line_items(
    items: list[OrderLineItemCreate],
) -> list[OrderLineItemCreate]:
    quantities: dict[int, int] = {}
    for item in items:
        quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity
    return [
        OrderLineItemCreate(product_id=product_id, quantity=quantity)
        for product_id, quantity in sorted(quantities.items())
    ]


def compute_total_amount(lines: list[tuple[int, Decimal]]) -> Decimal:
    total = Decimal("0")
    for quantity, unit_price in lines:
        total += Decimal(quantity) * unit_price
    return total


class OrderService:
    def __init__(
        self,
        order_repository: OrderRepository,
        product_repository: ProductRepository,
    ) -> None:
        self._orders = order_repository
        self._products = product_repository

    async def checkout(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        payload: OrderCreate,
    ) -> OrderResponse:
        merged = merge_line_items(payload.items)
        product_ids = [line.product_id for line in merged]
        products = await self._products.get_by_ids(db, product_ids)

        snapshot_lines: list[OrderLineSnapshot] = []
        priced_lines: list[tuple[int, Decimal]] = []

        for line in merged:
            product = products.get(line.product_id)
            if product is None:
                raise ProductNotFoundForOrderError(line.product_id)
            if product.quantity < line.quantity:
                raise InsufficientStockError(line.product_id)
            snapshot_lines.append(
                {
                    "product_id": product.id,
                    "product_name": product.name,
                    "quantity": line.quantity,
                    "unit_price": product.price,
                }
            )
            priced_lines.append((line.quantity, product.price))

        total_amount = compute_total_amount(priced_lines)

        try:
            order = await self._orders.create_with_line_items(
                db,
                user_id=user_id,
                shipping_address=payload.shipping_address,
                total_amount=total_amount,
                lines=snapshot_lines,
            )
            for line in merged:
                decremented = await self._products.decrement_quantity_if_available(
                    db,
                    line.product_id,
                    line.quantity,
                )
                if not decremented:
                    raise InsufficientStockError(line.product_id)
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        logger.info(
            "order_checkout_committed",
            user_id=user_id,
            order_id=order.id,
            line_count=len(order.line_items),
        )
        return self._to_response(order)

    async def list_mine(
        self,
        db: AsyncSession,
        *,
        user_id: int,
    ) -> list[OrderResponse]:
        orders = await self._orders.list_for_user(db, user_id)
        return [self._to_response(order) for order in orders]

    async def get_order(
        self,
        db: AsyncSession,
        *,
        order_id: int,
        user_id: int,
        is_admin: bool,
    ) -> OrderResponse:
        order = await self._orders.get_by_id(db, order_id)
        if order is None:
            raise OrderNotFoundError()
        if order.user_id != user_id and not is_admin:
            raise ForbiddenOrderAccessError()
        return self._to_response(order)

    async def list_admin(
        self,
        db: AsyncSession,
        *,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[OrderResponse]:
        orders = await self._orders.list_all(db, status=status, limit=limit)
        return [self._to_response(order) for order in orders]

    async def update_status(
        self,
        db: AsyncSession,
        *,
        order_id: int,
        status: str,
    ) -> tuple[OrderResponse, bool, str]:
        order = await self._orders.get_by_id(db, order_id)
        if order is None:
            raise OrderNotFoundError()

        old_status = order.status
        should_restock = (
            status == "cancelled"
            and order.status != "cancelled"
            and not order.stock_restored
        )

        try:
            if should_restock:
                for line in order.line_items:
                    product = await self._products.get_by_id(db, line.product_id)
                    if product is None:
                        logger.warning(
                            "order_restock_product_missing",
                            order_id=order_id,
                            product_id=line.product_id,
                        )
                        continue
                    await self._products.adjust_quantity(
                        db,
                        line.product_id,
                        line.quantity,
                    )
                await self._orders.update_status(
                    db,
                    order,
                    status=status,
                    stock_restored=True,
                )
            else:
                await self._orders.update_status(db, order, status=status)
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        reloaded = await self._orders.get_by_id(db, order_id)
        if reloaded is None:
            raise OrderNotFoundError()
        return self._to_response(reloaded), should_restock, old_status

    @staticmethod
    def _to_response(order: Order) -> OrderResponse:
        return OrderResponse(
            id=order.id,
            user_id=order.user_id,
            status=order.status,  # type: ignore[arg-type]
            total_amount=order.total_amount,
            shipping_address=order.shipping_address,
            created_at=order.created_at,
            updated_at=order.updated_at,
            items=[
                OrderLineItemResponse.model_validate(item)
                for item in order.line_items
            ],
        )
