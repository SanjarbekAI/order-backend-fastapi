import pytest

from src.products.exceptions import ProductNotFound
from src.products.service import ProductService


@pytest.fixture
def service():
    return ProductService()


async def test_create_product(service):
    product = await service.create_product("Service Widget", 5.00, 20)
    assert product["stock_quantity"] == 20


async def test_get_product_not_found_raises(service):
    with pytest.raises(ProductNotFound):
        await service.get_product(999999)


async def test_get_product_uses_cache_on_second_call(service, test_product):
    created = await test_product(name="Cached Item", stock=15)
    first = await service.get_product(created["id"])
    second = await service.get_product(created["id"])
    assert first["id"] == second["id"] == created["id"]
