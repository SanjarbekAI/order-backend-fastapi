from typing import Annotated

from fastapi import Depends

from src.products.service import ProductService

ProductServiceDep = Annotated[ProductService, Depends(ProductService)]
