from sqlalchemy import Column, Integer, String, Float, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Invoice(Base):
    """
    SQLAlchemy ORM Model for Supplier Invoices.
    Stores invoice header information and relationships to invoice line items.
    """
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    supplier = Column(String(255), nullable=False, index=True)
    invoice_number = Column(String(100), nullable=False, default="—")
    date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    total = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # One-to-many relationship with InvoiceItem
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Invoice(id={self.id}, supplier='{self.supplier}', invoice_number='{self.invoice_number}', total={self.total})>"
