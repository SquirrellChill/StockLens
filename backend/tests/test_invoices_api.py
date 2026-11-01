"""
API tests for StockLens invoice extraction and confirmation endpoints.
Verifies POST /api/invoices/extract with JPG and PNG samples,
error responses (empty, corrupted, disguised, oversized, missing OCR),
and invoice confirmation and listing.
"""

import io
from unittest.mock import patch
import pytest
from PIL import Image, ImageDraw


def generate_sample_invoice_bytes(fmt: str = "JPEG") -> bytes:
    """Generates a realistic synthetic invoice image."""
    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((40, 30), "Fresh Foods Supply Co.", fill=(0, 0, 0))
    draw.text((40, 60), "Invoice #: INV-2026-99", fill=(0, 0, 0))
    draw.text((40, 100), "Organic Apples 10 2.50", fill=(0, 0, 0))
    draw.text((40, 130), "Almond Milk 5 4.00", fill=(0, 0, 0))
    draw.text((40, 180), "Total: $45.00", fill=(0, 0, 0))

    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_extract_invoice_jpg_success(client):
    jpg_bytes = generate_sample_invoice_bytes("JPEG")
    mock_ocr_result = {
        "supplier": "Fresh Foods Supply Co.",
        "invoice_number": "INV-2026-99",
        "items": [
            {"name": "Organic Apples", "quantity": 10, "unit_price": 2.50},
            {"name": "Almond Milk", "quantity": 5, "unit_price": 4.00},
        ],
        "raw_text": "Fresh Foods Supply Co.\nInvoice #: INV-2026-99\nOrganic Apples 10 2.50\nAlmond Milk 5 4.00\nTotal: $45.00",
    }

    with patch("app.services.ocr_service.ocr_service.is_tesseract_installed", return_value=True), \
         patch("app.services.ocr_service.ocr_service.extract_from_image", return_value=mock_ocr_result):
        response = client.post(
            "/api/invoices/extract",
            files={"file": ("invoice.jpg", jpg_bytes, "image/jpeg")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["supplier"] == "Fresh Foods Supply Co."
    assert data["invoice_number"] == "INV-2026-99"
    assert len(data["items"]) == 2
    assert data["items"][0]["name"] == "Organic Apples"
    assert data["items"][0]["quantity"] == 10
    assert data["items"][0]["unit_price"] == 2.50


def test_extract_invoice_png_success(client):
    png_bytes = generate_sample_invoice_bytes("PNG")
    mock_ocr_result = {
        "supplier": "Tech Supplies Direct",
        "invoice_number": "INV-8888",
        "items": [{"name": "USB-C Cable", "quantity": 4, "unit_price": 9.99}],
        "raw_text": "Tech Supplies Direct\nInvoice: INV-8888\nUSB-C Cable 4 9.99",
    }

    with patch("app.services.ocr_service.ocr_service.is_tesseract_installed", return_value=True), \
         patch("app.services.ocr_service.ocr_service.extract_from_image", return_value=mock_ocr_result):
        response = client.post(
            "/api/invoices/extract",
            files={"file": ("sample_invoice.png", png_bytes, "image/png")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["supplier"] == "Tech Supplies Direct"
    assert data["invoice_number"] == "INV-8888"
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "USB-C Cable"


def test_extract_invoice_live_ocr_sample(client):
    """Verifies live OCR extraction pipeline without mocks on real sample image."""
    from pathlib import Path
    sample_file = Path("sample_invoices/sample_2_electronics_qty_first.png")
    if not sample_file.exists():
        pytest.skip("Sample invoice file not present")

    sample_bytes = sample_file.read_bytes()
    response = client.post(
        "/api/invoices/extract",
        files={"file": ("invoice.png", sample_bytes, "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert "Tech Supply Depot" in data["supplier"]
    assert data["invoice_number"] == "INV-9042"
    assert data["date"] == "2026-10-28"
    assert len(data["items"]) >= 2
    assert data["requires_review"] is True


def test_extract_invoice_empty_file_rejected(client):
    response = client.post(
        "/api/invoices/extract",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_extract_invoice_corrupted_image_rejected(client):
    # Corrupt data pretending to be JPEG
    corrupt_bytes = b"\xff\xd8\xff\xe0" + b"bad_broken_bytes" * 15
    response = client.post(
        "/api/invoices/extract",
        files={"file": ("corrupt.jpg", corrupt_bytes, "image/jpeg")},
    )
    assert response.status_code == 400
    assert "corrupted" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()


def test_extract_invoice_disguised_file_rejected(client):
    # Plain text file disguised as .jpg
    fake_bytes = b"Hello, this is a plain text file pretending to be an image!"
    response = client.post(
        "/api/invoices/extract",
        files={"file": ("invoice.jpg", fake_bytes, "image/jpeg")},
    )
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_extract_invoice_unsupported_format_gif_rejected(client):
    img = Image.new("RGB", (50, 50), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="GIF")
    gif_bytes = buf.getvalue()

    response = client.post(
        "/api/invoices/extract",
        files={"file": ("invoice.gif", gif_bytes, "image/gif")},
    )
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_extract_invoice_oversized_file_rejected(client):
    # Mock settings.MAX_UPLOAD_SIZE_BYTES to 100 bytes
    jpg_bytes = generate_sample_invoice_bytes("JPEG")
    with patch("app.routers.invoices.settings.MAX_UPLOAD_SIZE_BYTES", 50):
        response = client.post(
            "/api/invoices/extract",
            files={"file": ("huge.jpg", jpg_bytes, "image/jpeg")},
        )
    assert response.status_code == 413
    assert "larger than" in response.json()["detail"].lower() or "exceeds" in response.json()["detail"].lower()


def test_extract_invoice_ocr_dependency_unavailable(client):
    jpg_bytes = generate_sample_invoice_bytes("JPEG")
    # Simulate Tesseract not installed on server
    with patch("app.services.ocr_service.ocr_service.is_tesseract_installed", return_value=False):
        response = client.post(
            "/api/invoices/extract",
            files={"file": ("invoice.jpg", jpg_bytes, "image/jpeg")},
        )

    assert response.status_code == 503
    assert "ocr" in response.json()["detail"].lower()
    assert "tesseract" in response.json()["detail"].lower()


def test_confirm_invoice_and_stock_sync(client):
    invoice_payload = {
        "supplier": "Acme Farm Supplies",
        "invoice_number": "INV-777",
        "items": [
            {"name": "Organic Honey", "quantity": 12, "unit_price": 8.50},
            {"name": "Olive Oil 500ml", "quantity": 6, "unit_price": 14.00},
        ],
    }

    # Confirm invoice
    res = client.post("/api/invoices", json=invoice_payload)
    assert res.status_code == 201
    created_inv = res.json()
    assert created_inv["supplier"] == "Acme Farm Supplies"
    assert created_inv["invoice_number"] == "INV-777"
    assert created_inv["total"] == 186.00
    assert len(created_inv["items"]) == 2

    # Check that inventory products were automatically added/updated
    prod_res = client.get("/api/products")
    assert prod_res.status_code == 200
    products = prod_res.json()
    names = [p["name"] for p in products]
    assert "Organic Honey" in names
    assert "Olive Oil 500ml" in names

    # Confirm invoice list endpoint returns the new invoice
    inv_list_res = client.get("/api/invoices")
    assert inv_list_res.status_code == 200
    invoices = inv_list_res.json()
    assert len(invoices) >= 1
    assert any(inv["invoice_number"] == "INV-777" for inv in invoices)
