from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.repositories.product_repository import DuplicateSkuError, ProductRepository
from app.schemas.product import ProductResponse, ProductWrite


class ProductNotFound(Exception):
    pass


class DuplicateSku(Exception):
    pass


class ProductService:
    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def list_products(
        self,
        db: AsyncSession,
        *,
        search: str | None = None,
        limit: int | None = None,
    ) -> list[ProductResponse]:
        products = await self._repository.list_products(db, search=search, limit=limit)
        return [self._to_response(product) for product in products]

    async def get_product(
        self,
        db: AsyncSession,
        product_id: int,
    ) -> ProductResponse:
        product = await self._repository.get_by_id(db, product_id)
        if product is None:
            raise ProductNotFound("Product not found")
        return self._to_response(product)

    async def create_product(
        self,
        db: AsyncSession,
        payload: ProductWrite,
    ) -> ProductResponse:
        normalized = self._normalize_write(payload)
        try:
            product = await self._repository.create(db, **normalized)
        except DuplicateSkuError as exc:
            raise DuplicateSku("SKU already exists") from exc
        return self._to_response(product)

    async def update_product(
        self,
        db: AsyncSession,
        product_id: int,
        payload: ProductWrite,
    ) -> ProductResponse:
        normalized = self._normalize_write(payload)
        try:
            product = await self._repository.update(db, product_id, **normalized)
        except DuplicateSkuError as exc:
            raise DuplicateSku("SKU already exists") from exc
        if product is None:
            raise ProductNotFound("Product not found")
        return self._to_response(product)

    async def delete_product(
        self,
        db: AsyncSession,
        product_id: int,
    ) -> None:
        deleted = await self._repository.delete(db, product_id)
        if not deleted:
            raise ProductNotFound("Product not found")

    @staticmethod
    def _normalize_write(payload: ProductWrite) -> dict[str, object]:
        return {
            "name": payload.name,
            "description": payload.description,
            "sku": payload.sku,
            "price": payload.price,
            "quantity": payload.quantity,
            "category": payload.category,
            "image_url": payload.image_url or "",
        }

    @staticmethod
    def _to_response(product: Product) -> ProductResponse:
        return ProductResponse(
            id=product.id,
            name=product.name,
            description=product.description,
            sku=product.sku,
            price=product.price,
            quantity=product.quantity,
            category=product.category,
            image_url=product.image_url or "",
            created_at=product.created_at,
            updated_at=product.updated_at,
        )
