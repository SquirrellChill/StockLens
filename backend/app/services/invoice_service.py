import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional, Union
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateInvoiceError
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.product import Product
from app.schemas.invoice import InvoiceCreate

logger = logging.getLogger(__name__)

UNRELIABLE_INVOICE_NUMBERS = {
    "",
    "—",
    "–",
    "-",
    "n/a",
    "na",
    "none",
    "unknown",
    "null",
    "?",
    "none specified",
    "n / a",
}


def is_reliable_invoice_number(inv_num: Optional[str]) -> bool:
    """
    Determines whether an invoice number string represents a reliable identifier
    or a placeholder / unknown indicator.
    """
    if not inv_num:
        return False
    return inv_num.strip().lower() not in UNRELIABLE_INVOICE_NUMBERS


def parse_invoice_date(date_val: Union[datetime, date, str, None]) -> datetime:
    """
    Parses a date input (string, date, datetime, or None) into a timezone-aware UTC datetime.
    Falls back to current UTC datetime if omitted or invalid.
    """
    if isinstance(date_val, datetime):
        if date_val.tzinfo is None:
            return date_val.replace(tzinfo=timezone.utc)
        return date_val
    if isinstance(date_val, date):
        return datetime(date_val.year, date_val.month, date_val.day, tzinfo=timezone.utc)
    if isinstance(date_val, str) and date_val.strip():
        s = date_val.strip()
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                dt = datetime.strptime(s, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return datetime.now(timezone.utc)


class InvoiceService:
    """
    Service for managing supplier invoices and syncing inventory stock.
    Guarantees atomic execution and rollback on failure.
    """

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[Invoice]:
        """
        Retrieves confirmed supplier invoices, sorted with newest invoices first.
        """
        return (
            db.query(Invoice)
            .order_by(Invoice.date.desc(), Invoice.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, invoice_id: int) -> Optional[Invoice]:
        """
        Retrieves a single invoice by its ID.
        """
        return db.query(Invoice).filter(Invoice.id == invoice_id).first()

    @staticmethod
    def find_product_by_name_or_synonym(db: Session, item_name: str) -> Optional[Product]:
        """
        Matches a product in the catalog by:
        1. Exact case-insensitive match on product name.
        2. Case-insensitive match within product's alternative_names list.
        """
        clean_name = item_name.strip()
        if not clean_name:
            return None
        clean_lower = clean_name.lower()

        # Direct name match
        product = (
            db.query(Product)
            .filter(func.lower(Product.name) == clean_lower)
            .first()
        )
        if product:
            return product

        # Synonym match across alternative_names
        candidates = db.query(Product).filter(Product.alternative_names.isnot(None)).all()
        for cand in candidates:
            alts = cand.alternative_names
            if isinstance(alts, list):
                if any(isinstance(a, str) and a.strip().lower() == clean_lower for a in alts):
                    return cand

        return None

    @staticmethod
    def create(db: Session, invoice_in: InvoiceCreate) -> Invoice:
        """
        Creates a confirmed supplier invoice and updates inventory stock atomically:
        - Validates non-empty supplier and line items.
        - Enforces duplicate protection across reliable (supplier, invoice_number) pairs.
        - Updates stock quantity and unit price for existing products (matching name or alternative_names).
        - Creates new product records for uncatalogued items.
        - Links invoice items to matched/created products via product_id.
        - Rolls back completely if any step fails.
        """
        supplier_clean = invoice_in.supplier.strip()
        if not supplier_clean:
            raise ValueError("Supplier name cannot be empty.")

        if not invoice_in.items:
            raise ValueError("Add at least one item before confirming.")

        for item in invoice_in.items:
            if not item.name or not item.name.strip():
                raise ValueError("Item name cannot be empty.")
            if item.quantity <= 0:
                raise ValueError(f"Quantity for '{item.name}' must be greater than 0.")
            if item.unit_price < 0:
                raise ValueError(f"Unit price for '{item.name}' cannot be negative.")

        inv_num_clean = invoice_in.invoice_number.strip() if invoice_in.invoice_number else "—"
        if not inv_num_clean:
            inv_num_clean = "—"

        # Duplicate protection check
        if is_reliable_invoice_number(inv_num_clean):
            existing = (
                db.query(Invoice)
                .filter(
                    func.lower(Invoice.supplier) == supplier_clean.lower(),
                    func.lower(Invoice.invoice_number) == inv_num_clean.lower(),
                )
                .first()
            )
            if existing:
                raise DuplicateInvoiceError(
                    f"Invoice '{inv_num_clean}' from supplier '{supplier_clean}' has already been confirmed (Invoice #{existing.id})."
                )

        try:
            inv_date = parse_invoice_date(invoice_in.date)
            total = round(sum(item.quantity * item.unit_price for item in invoice_in.items), 2)

            invoice = Invoice(
                supplier=supplier_clean,
                invoice_number=inv_num_clean,
                date=inv_date,
                total=total,
            )
            db.add(invoice)
            db.flush()

            for item_data in invoice_in.items:
                name_clean = item_data.name.strip()
                unit_price_val = round(item_data.unit_price, 2)

                # Match existing product or create new one
                product = InvoiceService.find_product_by_name_or_synonym(db, name_clean)
                if product:
                    product.quantity += item_data.quantity
                    if unit_price_val > 0:
                        product.unit_price = Decimal(str(unit_price_val))
                else:
                    product = Product(
                        name=name_clean,
                        quantity=item_data.quantity,
                        unit_price=Decimal(str(unit_price_val)),
                        alternative_names=[],
                    )
                    db.add(product)
                    db.flush()

                item = InvoiceItem(
                    invoice_id=invoice.id,
                    product_id=product.id,
                    name=name_clean,
                    quantity=item_data.quantity,
                    unit_price=unit_price_val,
                )
                db.add(item)

            db.commit()
            db.refresh(invoice)
            logger.info(
                f"Confirmed invoice #{invoice.id} ('{invoice.invoice_number}') with "
                f"{len(invoice_in.items)} items for supplier '{invoice.supplier}'"
            )
            return invoice
        except Exception as e:
            db.rollback()
            logger.error(f"Transaction rolled back during invoice confirmation: {e}", exc_info=True)
            raise


invoice_service = InvoiceService()
