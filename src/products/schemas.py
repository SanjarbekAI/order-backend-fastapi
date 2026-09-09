from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    price: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    stock_quantity: int = Field(..., ge=0)


class ProductOut(BaseModel):
    id: int
    name: str
    price: Decimal
    stock_quantity: int
    created_at: datetime
    updated_at: datetime
