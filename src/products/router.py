from fastapi import APIRouter, status

from src.auth.dependencies import CurrentUserId
from src.products.dependencies import ProductServiceDep
from src.products.schemas import ProductCreate, ProductOut

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    _: CurrentUserId,
    service: ProductServiceDep,
) -> dict:
    return await service.create_product(payload.name, payload.price, payload.stock_quantity)


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: int, service: ProductServiceDep) -> dict:
    return await service.get_product(product_id)
