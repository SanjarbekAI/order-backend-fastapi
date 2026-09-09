from src.exceptions import DomainError


class ProductNotFound(DomainError):
    status_code = 404
    code = "product_not_found"

    def __init__(self, product_id: int):
        self.product_id = product_id
        super().__init__(f"Product {product_id} not found")
