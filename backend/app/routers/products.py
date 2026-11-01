from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.services.product_service import product_service

router = APIRouter()


@router.get(
    "",
    response_model=List[ProductResponse],
    status_code=status.HTTP_200_OK,
    summary="List all products",
    description="Retrieve all inventory products with optional search query across name and alternative names.",
)
def get_products(
    search: Optional[str] = Query(None, description="Search term matching product name or synonyms"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: Optional[int] = Query(None, ge=1, le=500, description="Maximum number of items to return"),
    db: Session = Depends(get_db),
):
    """
    1. GET /api/products
    Retrieve all products, optionally filtered by search query.
    """
    return product_service.get_all(db, search=search, skip=skip, limit=limit)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve one product",
    description="Retrieve a single product by its unique database ID.",
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    2. GET /api/products/{product_id}
    Retrieve details for a single product. Returns 404 if not found.
    """
    product = product_service.get_by_id(db, product_id=product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    return product


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
    description="Add a new product to inventory. Name, non-negative integer quantity, and non-negative unit price are required.",
)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
):
    """
    3. POST /api/products
    Create a new inventory product.
    """
    return product_service.create(db, product_in=product_in)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing product",
    description="Update product details. Supports partial updates for name, quantity, unit price, expiration date, and alternative names.",
)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
):
    """
    4. PUT /api/products/{product_id}
    Update an existing product. Returns 404 if product does not exist.
    """
    updated = product_service.update(db, product_id=product_id, product_in=product_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    return updated


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a product",
    description="Remove a product from inventory by its unique database ID.",
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    5. DELETE /api/products/{product_id}
    Delete a product from inventory. Returns 404 if product does not exist.
    """
    deleted = product_service.delete(db, product_id=product_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    return {"ok": True, "message": "Product removed successfully."}
