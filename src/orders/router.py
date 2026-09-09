from typing import Annotated

from fastapi import APIRouter, Header, status

from src.auth.dependencies import CurrentUserId
from src.orders.dependencies import OrderServiceDep
from src.orders.schemas import OrderCreate, OrderOut

router = APIRouter(prefix="/orders", tags=["orders"])

IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)]


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    idempotency_key: IdempotencyKey,
    user_id: CurrentUserId,
    service: OrderServiceDep,
) -> dict:
    return await service.create_order(user_id, payload.items, idempotency_key)


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    user_id: CurrentUserId,
    service: OrderServiceDep,
) -> dict:
    return await service.get_order(order_id, user_id)


@router.post("/{order_id}/cancel", response_model=OrderOut)
async def cancel_order(
    order_id: int,
    user_id: CurrentUserId,
    service: OrderServiceDep,
) -> dict:
    return await service.cancel_order(order_id, user_id)
