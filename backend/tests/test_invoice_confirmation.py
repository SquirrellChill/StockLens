"""
Tests for StockLens invoice confirmation and inventory integration.
Verifies:
- Existing product stock incremented (matched by name or synonym).
- New product creation when uncatalogued.
- Product linking via product_id in InvoiceItem.
- Owner-corrected data saved accurately.
- Validation: rejected on empty supplier, empty items, invalid quantities/prices.
- Duplicate invoice rejection: 409 Conflict for same supplier + reliable invoice number.
- Cross-supplier duplicate tolerance (same number, different supplier allowed).
- Placeholder invoice numbers allowed multiple times.
- Atomic rollback on transaction failures: no partial stock updates.
- OCR extraction never modifies stock directly.
- GET /api/invoices returns confirmed invoices with items.
"""

from decimal import Decimal
from unittest.mock import patch
import pytest
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.product import Product
from app.services.invoice_service import invoice_service


def test_confirm_invoice_increases_existing_product_stock_by_name(client, db_session):
    """Confirming an invoice increases stock and updates price for an existing product matched by name."""
    existing_product = Product(
        name="Organic Almond Milk",
        quantity=15,
        unit_price=Decimal("3.50"),
        alternative_names=["Almond Milk"],
    )
    db_session.add(existing_product)
    db_session.commit()
    db_session.refresh(existing_product)
    product_id = existing_product.id

    payload = {
        "supplier": "Green Grocer Ltd",
        "invoice_number": "INV-ALMOND-01",
        "date": "2026-10-25T10:00:00Z",
        "items": [
            {"name": "organic almond milk", "quantity": 10, "unit_price": 3.75}
        ],
    }

    response = client.post("/api/invoices", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["supplier"] == "Green Grocer Ltd"
    assert data["invoice_number"] == "INV-ALMOND-01"
    assert data["total"] == 37.50
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == product_id

    # Verify database state
    db_session.expire_all()
    updated_product = db_session.query(Product).filter(Product.id == product_id).first()
    assert updated_product.quantity == 25  # 15 + 10
    assert updated_product.unit_price == Decimal("3.75")


def test_confirm_invoice_matches_product_by_alternative_names(client, db_session):
    """Confirming an invoice matches existing product via alternative_names synonym and increases stock."""
    prod = Product(
        name="Coca-Cola Classic 500ml",
        quantity=50,
        unit_price=Decimal("1.25"),
        alternative_names=["Coke 500ml", "Coca Cola 0.5L", "Coke Regular"],
    )
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)
    prod_id = prod.id

    payload = {
        "supplier": "Beverage Distributors Inc",
        "invoice_number": "INV-BEV-9901",
        "items": [
            {"name": "COKE 500ML", "quantity": 24, "unit_price": 1.10}
        ],
    }

    response = client.post("/api/invoices", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["items"][0]["product_id"] == prod_id

    # Verify no new product was created and stock updated
    db_session.expire_all()
    all_products = db_session.query(Product).all()
    assert len(all_products) == 1
    assert all_products[0].id == prod_id
    assert all_products[0].quantity == 74  # 50 + 24
    assert all_products[0].unit_price == Decimal("1.10")


def test_confirm_invoice_creates_new_product(client, db_session):
    """Confirming an invoice with a new uncatalogued item creates a new product record."""
    payload = {
        "supplier": "Bakery Delights",
        "invoice_number": "INV-BAKE-501",
        "items": [
            {"name": "Artisan Sourdough Loaf", "quantity": 12, "unit_price": 4.50}
        ],
    }

    response = client.post("/api/invoices", json=payload)
    assert response.status_code == 201
    data = response.json()

    item_res = data["items"][0]
    assert item_res["name"] == "Artisan Sourdough Loaf"
    assert item_res["product_id"] is not None

    db_session.expire_all()
    created_product = db_session.query(Product).filter(Product.id == item_res["product_id"]).first()
    assert created_product is not None
    assert created_product.name == "Artisan Sourdough Loaf"
    assert created_product.quantity == 12
    assert created_product.unit_price == Decimal("4.50")
    assert created_product.alternative_names == []


def test_confirm_invoice_saves_owner_corrected_data(client, db_session):
    """Owner edits extracted OCR fields before confirming; backend persists corrected values."""
    # Simulates owner correcting noisy OCR "0rgan1c Bananas" to "Organic Bananas",
    # fixing qty 5 to 50, and fixing price 0.2 to 0.25.
    corrected_payload = {
        "supplier": "Sunshine Fruits Corp",
        "invoice_number": "CORRECTED-INV-44",
        "date": "2026-10-30T12:00:00Z",
        "items": [
            {"name": "Organic Cavendish Bananas", "quantity": 50, "unit_price": 0.25},
            {"name": "Dragon Fruit Fresh", "quantity": 20, "unit_price": 2.50},
        ],
    }

    res = client.post("/api/invoices", json=corrected_payload)
    assert res.status_code == 201
    data = res.json()

    assert data["supplier"] == "Sunshine Fruits Corp"
    assert data["invoice_number"] == "CORRECTED-INV-44"
    assert data["total"] == 62.50  # 50*0.25 + 20*2.50 = 12.50 + 50.00
    assert len(data["items"]) == 2
    assert data["items"][0]["name"] == "Organic Cavendish Bananas"
    assert data["items"][0]["quantity"] == 50
    assert data["items"][0]["unit_price"] == 0.25


def test_confirm_invoice_validation_rejects_empty_items(client):
    """Empty line items list is rejected with 400 or 422."""
    payload = {
        "supplier": "Acme Corp",
        "invoice_number": "INV-EMPTY",
        "items": [],
    }
    res = client.post("/api/invoices", json=payload)
    assert res.status_code in (400, 422)


def test_confirm_invoice_validation_rejects_invalid_item_values(client):
    """Rejects items with zero/negative quantity or negative unit price."""
    # Zero quantity
    res1 = client.post("/api/invoices", json={
        "supplier": "Acme Corp",
        "invoice_number": "INV-BAD-QTY",
        "items": [{"name": "Item A", "quantity": 0, "unit_price": 10.0}],
    })
    assert res1.status_code in (400, 422)

    # Negative quantity
    res2 = client.post("/api/invoices", json={
        "supplier": "Acme Corp",
        "invoice_number": "INV-NEG-QTY",
        "items": [{"name": "Item B", "quantity": -3, "unit_price": 10.0}],
    })
    assert res2.status_code in (400, 422)

    # Negative price
    res3 = client.post("/api/invoices", json={
        "supplier": "Acme Corp",
        "invoice_number": "INV-NEG-PRICE",
        "items": [{"name": "Item C", "quantity": 5, "unit_price": -1.50}],
    })
    assert res3.status_code in (400, 422)

    # Empty item name
    res4 = client.post("/api/invoices", json={
        "supplier": "Acme Corp",
        "invoice_number": "INV-EMPTY-NAME",
        "items": [{"name": "   ", "quantity": 5, "unit_price": 1.50}],
    })
    assert res4.status_code in (400, 422)

    # Whitespace supplier name
    res5 = client.post("/api/invoices", json={
        "supplier": "   ",
        "invoice_number": "INV-EMPTY-SUPPLIER",
        "items": [{"name": "Item D", "quantity": 1, "unit_price": 1.50}],
    })
    assert res5.status_code in (400, 422)


def test_duplicate_invoice_rejection_same_supplier_and_number(client):
    """Rejects second confirmation of the same invoice from the same supplier with 409 Conflict."""
    payload = {
        "supplier": "Global Tech Distributors",
        "invoice_number": "GTD-2026-881",
        "items": [
            {"name": "HDMI Cable 2m", "quantity": 10, "unit_price": 5.00}
        ],
    }

    # First confirmation succeeds
    res1 = client.post("/api/invoices", json=payload)
    assert res1.status_code == 201

    # Second confirmation with same supplier and invoice number is rejected
    res2 = client.post("/api/invoices", json=payload)
    assert res2.status_code == 409
    assert "already been confirmed" in res2.json()["detail"].lower()

    # Case-insensitive duplicate check
    payload_diff_case = {
        "supplier": "global tech distributors",
        "invoice_number": "gtd-2026-881",
        "items": [
            {"name": "HDMI Cable 2m", "quantity": 5, "unit_price": 5.00}
        ],
    }
    res3 = client.post("/api/invoices", json=payload_diff_case)
    assert res3.status_code == 409
    assert "already been confirmed" in res3.json()["detail"].lower()


def test_cross_supplier_same_invoice_number_allowed(client):
    """Different suppliers may share the same invoice number (e.g. INV-001) without collision."""
    inv_supplier_a = {
        "supplier": "Supplier Alpha",
        "invoice_number": "INV-COMMON-100",
        "items": [{"name": "Product Alpha Item", "quantity": 2, "unit_price": 15.00}],
    }
    inv_supplier_b = {
        "supplier": "Supplier Beta",
        "invoice_number": "INV-COMMON-100",
        "items": [{"name": "Product Beta Item", "quantity": 4, "unit_price": 25.00}],
    }

    res_a = client.post("/api/invoices", json=inv_supplier_a)
    assert res_a.status_code == 201

    res_b = client.post("/api/invoices", json=inv_supplier_b)
    assert res_b.status_code == 201


def test_placeholder_invoice_numbers_allowed_multiple_times(client):
    """Receipts without reliable invoice numbers (dash, empty, n/a) are not rejected as duplicates."""
    placeholders = ["—", "-", "N/A", "none", ""]
    for ph in placeholders:
        payload = {
            "supplier": "Local Cash Register",
            "invoice_number": ph,
            "items": [{"name": f"Daily Receipt Item {ph}", "quantity": 1, "unit_price": 2.00}],
        }
        res = client.post("/api/invoices", json=payload)
        assert res.status_code == 201


def test_transaction_rollback_on_failure_no_partial_stock_update(client, db_session):
    """
    If any operation fails during confirmation, the transaction rolls back completely.
    Existing product stock must remain intact and no orphan invoice record is created.
    """
    p = Product(name="Safe Product", quantity=100, unit_price=Decimal("10.00"), alternative_names=[])
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    p_id = p.id

    inv_count_before = db_session.query(Invoice).count()

    # Simulate a crash right after product update during InvoiceItem creation
    with patch.object(db_session, "commit", side_effect=RuntimeError("Simulated database failure")):
        with pytest.raises(RuntimeError):
            invoice_service.create(
                db=db_session,
                invoice_in=type("InvoiceCreateObj", (), {
                    "supplier": "Failing Supplier",
                    "invoice_number": "FAIL-001",
                    "date": None,
                    "items": [
                        type("ItemObj", (), {"name": "Safe Product", "quantity": 50, "unit_price": 12.00})()
                    ],
                })(),
            )

    # Verify atomic rollback: product stock was NOT incremented to 150
    db_session.expire_all()
    p_after = db_session.query(Product).filter(Product.id == p_id).first()
    assert p_after.quantity == 100
    assert p_after.unit_price == Decimal("10.00")

    # Verify no invoice was saved
    inv_count_after = db_session.query(Invoice).count()
    assert inv_count_after == inv_count_before


def test_ocr_extraction_does_not_update_stock(client, db_session):
    """
    POST /api/invoices/extract must NEVER modify product stock directly.
    Only owner confirmation via POST /api/invoices can update inventory.
    """
    # Create an initial product
    prod = Product(name="Frozen Berries", quantity=20, unit_price=Decimal("5.00"), alternative_names=[])
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)
    prod_id = prod.id

    from tests.test_invoices_api import generate_sample_invoice_bytes
    sample_bytes = generate_sample_invoice_bytes("JPEG")

    mock_ocr = {
        "supplier": "Berry Farm Co",
        "invoice_number": "BERRY-999",
        "items": [{"name": "Frozen Berries", "quantity": 100, "unit_price": 4.50}],
        "raw_text": "Berry Farm Co Frozen Berries 100 4.50",
    }

    with patch("app.services.ocr_service.ocr_service.is_tesseract_installed", return_value=True), \
         patch("app.services.ocr_service.ocr_service.extract_from_image", return_value=mock_ocr):
        extract_res = client.post(
            "/api/invoices/extract",
            files={"file": ("invoice.jpg", sample_bytes, "image/jpeg")},
        )
        assert extract_res.status_code == 200

    # Verify product stock is STILL 20, NOT 120!
    db_session.expire_all()
    prod_after = db_session.query(Product).filter(Product.id == prod_id).first()
    assert prod_after.quantity == 20
    assert prod_after.unit_price == Decimal("5.00")

    # Verify no invoices exist for BERRY-999
    assert db_session.query(Invoice).filter(Invoice.invoice_number == "BERRY-999").first() is None


def test_get_invoices_returns_confirmed_invoices_with_items(client):
    """GET /api/invoices returns all confirmed invoices with nested line items."""
    inv1 = {
        "supplier": "Paper & Co",
        "invoice_number": "INV-P-01",
        "items": [{"name": "A4 Paper Ream", "quantity": 10, "unit_price": 3.00}],
    }
    inv2 = {
        "supplier": "Ink Solutions",
        "invoice_number": "INV-I-02",
        "items": [
            {"name": "Black Ink Cartridge", "quantity": 2, "unit_price": 25.00},
            {"name": "Color Ink Cartridge", "quantity": 1, "unit_price": 35.00},
        ],
    }

    client.post("/api/invoices", json=inv1)
    client.post("/api/invoices", json=inv2)

    res = client.get("/api/invoices")
    assert res.status_code == 200
    invoices = res.json()
    assert len(invoices) >= 2

    # Check that items and total are present
    p_inv = next(inv for inv in invoices if inv["invoice_number"] == "INV-P-01")
    assert p_inv["supplier"] == "Paper & Co"
    assert p_inv["total"] == 30.00
    assert len(p_inv["items"]) == 1
    assert p_inv["items"][0]["name"] == "A4 Paper Ream"

    i_inv = next(inv for inv in invoices if inv["invoice_number"] == "INV-I-02")
    assert i_inv["supplier"] == "Ink Solutions"
    assert i_inv["total"] == 85.00
    assert len(i_inv["items"]) == 2


def test_delete_product_sets_invoice_item_product_id_null(client, db_session):
    """
    Deleting an inventory product sets the referencing invoice_items.product_id to NULL,
    preserving invoice records without breaking on foreign key constraints.
    """
    prod = Product(name="Discontinued Item", quantity=5, unit_price=Decimal("10.00"), alternative_names=[])
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)
    prod_id = prod.id

    inv_payload = {
        "supplier": "Old Supplier",
        "invoice_number": "INV-OLD-999",
        "items": [{"name": "Discontinued Item", "quantity": 5, "unit_price": 10.00}],
    }
    confirm_res = client.post("/api/invoices", json=inv_payload)
    assert confirm_res.status_code == 201
    inv_id = confirm_res.json()["id"]

    # Verify item is linked
    item = db_session.query(InvoiceItem).filter(InvoiceItem.invoice_id == inv_id).first()
    assert item.product_id == prod_id

    # Delete product
    del_res = client.delete(f"/api/products/{prod_id}")
    assert del_res.status_code == 200

    # Verify invoice item still exists and has product_id set to None
    db_session.expire_all()
    item_after = db_session.query(InvoiceItem).filter(InvoiceItem.invoice_id == inv_id).first()
    assert item_after is not None
    assert item_after.product_id is None
    assert item_after.name == "Discontinued Item"
