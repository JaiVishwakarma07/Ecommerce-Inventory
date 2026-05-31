from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class DuplicateSkuError(Exception):
    pass


class ProductRepository:
    async def list_products(
        self,
        db: AsyncSession,
        *,
        search: str | None = None,
        limit: int | None = None,
    ) -> list[Product]:
        query = select(Product).order_by(Product.id)

        normalized_search = (search or "").strip()
        if normalized_search:
            pattern = f"%{normalized_search.lower()}%"
            query = query.where(
                or_(
                    func.lower(Product.name).like(pattern),
                    func.lower(Product.sku).like(pattern),
                    func.lower(Product.category).like(pattern),
                )
            )

        if limit is not None:
            capped_limit = min(limit, 100)
            query = query.limit(capped_limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(
        self,
        db: AsyncSession,
        product_id: int,
    ) -> Product | None:
        result = await db.execute(
            select(Product)
            .where(Product.id == product_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_by_ids(
        self,
        db: AsyncSession,
        product_ids: list[int],
    ) -> dict[int, Product]:
        if not product_ids:
            return {}
        result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        products = list(result.scalars().all())
        return {product.id: product for product in products}

    async def adjust_quantity(
        self,
        db: AsyncSession,
        product_id: int,
        delta: int,
    ) -> Product | None:
        product = await self.get_by_id(db, product_id)
        if product is None:
            return None
        product.quantity = product.quantity + delta
        await db.flush()
        return product

    async def decrement_quantity_if_available(
        self,
        db: AsyncSession,
        product_id: int,
        quantity: int,
    ) -> bool:
        """Atomically decrement stock; returns False if product missing or insufficient."""
        if quantity <= 0:
            return False
        result = await db.execute(
            update(Product)
            .where(Product.id == product_id, Product.quantity >= quantity)
            .values(quantity=Product.quantity - quantity)
        )
        await db.flush()
        return (result.rowcount or 0) > 0

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
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise DuplicateSkuError("SKU already exists") from exc
        await db.refresh(product)
        return product

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
        product = await self.get_by_id(db, product_id)
        if product is None:
            return None

        product.name = name
        product.description = description
        product.sku = sku
        product.price = price
        product.quantity = quantity
        product.category = category
        product.image_url = image_url
        product.updated_at = datetime.now(timezone.utc)

        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise DuplicateSkuError("SKU already exists") from exc
        await db.refresh(product)
        return product

    async def delete(
        self,
        db: AsyncSession,
        product_id: int,
    ) -> bool:
        product = await self.get_by_id(db, product_id)
        if product is None:
            return False
        await db.delete(product)
        await db.commit()
        return True
