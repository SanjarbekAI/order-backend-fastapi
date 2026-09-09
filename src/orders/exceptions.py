from src.exceptions import DomainError


class OrderNotFound(DomainError):
    status_code = 404
    code = "order_not_found"

    def __init__(self, order_id: int):
        self.order_id = order_id
        super().__init__(f"Order {order_id} not found")


class InsufficientStock(DomainError):
    status_code = 409
    code = "insufficient_stock"

    def __init__(self, product_id: int):
        self.product_id = product_id
        super().__init__(f"Insufficient stock for product {product_id}")


class InvalidOrderState(DomainError):
    status_code = 422
    code = "invalid_order_state"

    def __init__(self, order_id: int, current_status: str):
        self.order_id = order_id
        self.current_status = current_status
        super().__init__(f"Order {order_id} is '{current_status}' and cannot be cancelled")
