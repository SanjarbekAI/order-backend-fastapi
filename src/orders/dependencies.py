from typing import Annotated

from fastapi import Depends

from src.orders.service import OrderService

OrderServiceDep = Annotated[OrderService, Depends(OrderService)]
