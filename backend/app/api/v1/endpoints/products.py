from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.services.product_service import product_service

router = APIRouter()


@router.get(
    "",
    response_model=List[ProductResponse],
    summary="List all products",
    description="Retrieve inventory products with optional search filter by name or alternative names."
)
def get_products(
    search: Optional[str] = Query(None, description="Search term for name or synonym"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Maximum items to return"),
    db: Session = Depends(get_db),
):
    return product_service.get_all(db, search=search, skip=skip, limit=limit)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID",
    description="Retrieve a single product by its unique database ID."
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
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
    summary="Create a new product",
    description="Add a new product to the inventory."
)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
):
    return product_service.create(db, product_in=product_in)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update/Edit a product",
    description="Edit product details (name, quantity, unit price, expiration date, alternative names). Main Milestone 2 demonstration story."
)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
):
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
    description="Remove a product from the inventory by ID."
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    deleted = product_service.delete(db, product_id=product_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    return {"ok": True, "message": "Product removed successfully."}
