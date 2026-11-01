from fastapi import APIRouter
from app.routers.products import router as products_router
from app.routers.invoices import router as invoices_router

api_router = APIRouter()

# Mount routers under standard API paths matching frontend expectations
api_router.include_router(products_router, prefix="/products", tags=["Products"])
api_router.include_router(invoices_router, prefix="/invoices", tags=["Invoices"])

__all__ = ["api_router", "products_router", "invoices_router"]
