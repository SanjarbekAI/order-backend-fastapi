from src.database import get_pool
from src.products.cache import ProductCache
from src.products.exceptions import ProductNotFound
from src.products.repository import ProductRepository
from src.redis_client import get_redis


class ProductService:
    def __init__(self) -> None:
        self.repo = ProductRepository()
        self.cache = ProductCache(get_redis())

    async def create_product(self, name: str, price, stock_quantity: int) -> dict:
        async with get_pool().acquire() as conn:
            return await self.repo.create(conn, name, price, stock_quantity)

    async def get_product(self, product_id: int) -> dict:
        cached = await self.cache.get(product_id)
        if cached is not None:
            return cached

        async with get_pool().acquire() as conn:
            product = await self.repo.get_by_id(conn, product_id)
        if product is None:
            raise ProductNotFound(product_id)

        await self.cache.set(product_id, product)
        return product
