from enum import StrEnum


class OrderStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


# Backwards-friendly flat aliases used across the codebase and tests.
ORDER_STATUS_PENDING = OrderStatus.PENDING
ORDER_STATUS_CONFIRMED = OrderStatus.CONFIRMED
ORDER_STATUS_CANCELLED = OrderStatus.CANCELLED
