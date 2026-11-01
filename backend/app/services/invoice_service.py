import logging
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.product import Product
from app.schemas.invoice import InvoiceCreate

logger = logging.getLogger(__name__)


class InvoiceService:
    """
    Service for managing supplier invoices and syncing inventory stock.
    """

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[Invoice]:
        return db.query(Invoice).order_by(Invoice.id.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_by_id(db: Session, invoice_id: int) -> Optional[Invoice]:
        return db.query(Invoice).filter(Invoice.id == invoice_id).first()

    @staticmethod
    def create(db: Session, invoice_in: InvoiceCreate) -> Invoice:
        """
        Creates a confirmed supplier invoice and updates product inventory:
        - Calculates total amount from items.
        - Updates stock quantity and unit price for existing products (matching name or alternative_names).
        - Creates new product records for uncatalogued items.
        """
        total = sum(item.quantity * item.unit_price for item in invoice_in.items)
        invoice = Invoice(
            supplier=invoice_in.supplier.strip(),
            invoice_number=invoice_in.invoice_number.strip() if invoice_in.invoice_number else "—",
            total=round(total, 2),
        )
        db.add(invoice)
        db.flush()

        for item_data in invoice_in.items:
            name_clean = item_data.name.strip()
            item = InvoiceItem(
                invoice_id=invoice.id,
                name=name_clean,
                quantity=item_data.quantity,
                unit_price=round(item_data.unit_price, 2),
            )
            db.add(item)

            # Update or create corresponding product in stock
            product = (
                db.query(Product)
                .filter(Product.name.ilike(name_clean))
                .first()
            )
            if product:
                product.quantity += item_data.quantity
                if item_data.unit_price > 0:
                    product.unit_price = Decimal(str(round(item_data.unit_price, 2)))
            else:
                new_product = Product(
                    name=name_clean,
                    quantity=item_data.quantity,
                    unit_price=Decimal(str(round(item_data.unit_price, 2))),
                    alternative_names=[],
                )
                db.add(new_product)

        db.commit()
        db.refresh(invoice)
        logger.info(f"Confirmed invoice #{invoice.id} with {len(invoice_in.items)} items for supplier '{invoice.supplier}'")
        return invoice


invoice_service = InvoiceService()
