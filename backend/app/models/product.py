from sqlalchemy import Column, Integer, String, Float, Date, DateTime, JSON, func
from app.core.database import Base


class Product(Base):
    """
    SQLAlchemy Model for Inventory Products.
    Matches frontend expectations for fields:
    - name: string
    - quantity: integer
    - unit_price: float
    - expiration_date: date (nullable)
    - alternative_names: list of string synonyms
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    unit_price = Column(Float, nullable=False, default=0.0)
    expiration_date = Column(Date, nullable=True)
    alternative_names = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}', quantity={self.quantity}, unit_price={self.unit_price})>"
