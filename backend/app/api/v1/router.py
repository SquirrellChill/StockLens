from fastapi import APIRouter
from app.api.v1.endpoints import products

api_router = APIRouter()

# Mount product routes under /products
# Since api_router is mounted at /api, full path is /api/products
api_router.include_router(products.router, prefix="/products", tags=["Products"])
