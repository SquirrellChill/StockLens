from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, String, cast

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


class ProductService:
    """
    Business logic layer for Product operations.
    Keeps database queries separated from API route handlers.
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
        limit: int = 100
    ) -> List[Product]:
        """
        List all products with optional name or synonym search.
        Orders by latest id.
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
        return query.order_by(Product.id.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def create(db: Session, product_in: ProductCreate) -> Product:
        """Create a new product record."""
        db_product = Product(
            name=product_in.name,
            quantity=product_in.quantity,
            unit_price=product_in.unit_price,
            expiration_date=product_in.expiration_date,
            alternative_names=product_in.alternative_names,
        )
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product

    @staticmethod
    def update(db: Session, product_id: int, product_in: ProductUpdate) -> Optional[Product]:
        """
        Edit / Update product details (Milestone 2 priority).
        
        Args:
            db: Active SQLAlchemy database session.
            product_id: ID of the product to update.
            product_in: Validated updated fields.

        Returns:
            Updated Product model instance if found, or None if not found.
        """
        db_product = ProductService.get_by_id(db, product_id)
        if not db_product:
            return None

        update_data = product_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_product, field, value)

        db.commit()
        db.refresh(db_product)
        return db_product

    @staticmethod
    def delete(db: Session, product_id: int) -> bool:
        """Delete a product by ID."""
        db_product = ProductService.get_by_id(db, product_id)
        if not db_product:
            return False

        db.delete(db_product)
        db.commit()
        return True


product_service = ProductService()
