from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class InvoiceItem(Base):
    """
    SQLAlchemy ORM Model for Invoice Line Items.
    Stores individual items extracted/confirmed on a supplier invoice,
    including foreign key relationship to the matched inventory product.
    """
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False, default=0.0)

    # Relationships
    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product")

    def __repr__(self) -> str:
        return (
            f"<InvoiceItem(id={self.id}, invoice_id={self.invoice_id}, "
            f"product_id={self.product_id}, name='{self.name}', "
            f"quantity={self.quantity}, unit_price={self.unit_price})>"
        )
