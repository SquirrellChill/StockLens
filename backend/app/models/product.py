from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, JSON, func
from app.core.database import Base


class Product(Base):
    """
    SQLAlchemy ORM Model for Inventory Products.
    Matches frontend expectations for fields:
    - id: integer primary key
    - name: string (max 255)
    - quantity: integer (non-negative stock count)
    - unit_price: numeric/decimal (10, 2) for exact monetary storage
    - expiration_date: date (nullable)
    - alternative_names: JSON array of string synonyms
    - created_at: timezone-aware timestamp
    - updated_at: timezone-aware timestamp with auto-update
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    unit_price = Column(Numeric(precision=10, scale=2), nullable=False, default=Decimal("0.00"))
    expiration_date = Column(Date, nullable=True)
    alternative_names = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}', quantity={self.quantity}, unit_price={self.unit_price})>"
