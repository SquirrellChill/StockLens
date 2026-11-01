import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, String, cast

from app.models.invoice_item import InvoiceItem
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate

logger = logging.getLogger(__name__)


class ProductService:
    """
    Business logic layer for Product operations.
    Encapsulates database operations, transaction handling, and queries.
    """

    @staticmethod
    def get_by_id(db: Session, product_id: int) -> Optional[Product]:
        """Fetch a single product by primary key."""
        return db.query(Product).filter(Product.id == product_id).first()

    @staticmethod
    def get_all(
        db: Session,
        search: Optional[str] = None,
        skip: int = 0,
        limit: Optional[int] = None
    ) -> List[Product]:
        """
        List all products with optional name or synonym search.
        Orders by newest products first.
        """
        query = db.query(Product)
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Product.name.ilike(search_term),
                    cast(Product.alternative_names, String).ilike(search_term)
                )
            )
        query = query.order_by(Product.id.desc()).offset(skip)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    @staticmethod
    def create(db: Session, product_in: ProductCreate) -> Product:
        """
        Create a new product record with atomic transaction management.
        """
        db_product = Product(
            name=product_in.name,
            quantity=product_in.quantity,
            unit_price=product_in.unit_price,
            expiration_date=product_in.expiration_date,
            alternative_names=product_in.alternative_names,
        )
        try:
            db.add(db_product)
            db.commit()
            db.refresh(db_product)
            return db_product
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create product: {e}")
            raise

    @staticmethod
    def update(db: Session, product_id: int, product_in: ProductUpdate) -> Optional[Product]:
        """
        Update an existing product's details with atomic transaction management.
        Returns the updated Product instance, or None if product does not exist.
        """
        db_product = ProductService.get_by_id(db, product_id)
        if not db_product:
            return None

        update_data = product_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_product, field, value)

        try:
            db.commit()
            db.refresh(db_product)
            return db_product
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update product {product_id}: {e}")
            raise

    @staticmethod
    def delete(db: Session, product_id: int) -> bool:
        """
        Delete a product by ID with atomic transaction management.
        Nullifies any referencing invoice_items.product_id to preserve invoice history,
        then permanently deletes the product record.
        Returns True if deleted, False if product does not exist.
        """
        db_product = ProductService.get_by_id(db, product_id)
        if not db_product:
            return False

        try:
            # Explicitly nullify foreign key references in invoice_items to maintain audit history
            db.query(InvoiceItem).filter(InvoiceItem.product_id == product_id).update({InvoiceItem.product_id: None})
            db.delete(db_product)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete product {product_id}: {e}")
            raise


product_service = ProductService()
