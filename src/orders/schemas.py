from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class OrderItemIn(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class OrderCreate(BaseModel):
    items: list[OrderItemIn] = Field(..., min_length=1, max_length=100)


class OrderItemOut(BaseModel):
    product_id: int
    quantity: int
    price_at_purchase: Decimal


class OrderOut(BaseModel):
    id: int
    user_id: int
    status: str
    total_amount: Decimal
    expires_at: datetime
    created_at: datetime
    items: list[OrderItemOut]
