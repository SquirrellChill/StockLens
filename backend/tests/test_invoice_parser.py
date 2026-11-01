"""
Unit tests for the decoupled InvoiceParser.
Tests common table layouts, line-break variations, decimal commas,
currency symbols, supplier and invoice number extraction, and review flagging.
Ensures missing fields are not fabricated.
"""

import pytest
from app.services.invoice_parser import invoice_parser, InvoiceParser


def test_clean_currency_and_numbers():
    assert InvoiceParser.clean_currency_and_numbers("$12.50") == 12.50
    assert InvoiceParser.clean_currency_and_numbers("€ 9.99") == 9.99
    assert InvoiceParser.clean_currency_and_numbers("£1,250.00") == 1250.00
    assert InvoiceParser.clean_currency_and_numbers("12,50") == 12.50  # Decimal comma
    assert InvoiceParser.clean_currency_and_numbers("O.75") == 0.75   # Letter O OCR typo
    assert InvoiceParser.clean_currency_and_numbers("15000 ៛") == 15000.0
    assert InvoiceParser.clean_currency_and_numbers("") is None
    assert InvoiceParser.clean_currency_and_numbers("abc") is None


def test_parse_standard_table_layout():
    text = """
    FRESH FOODS MARKET CO.
    Invoice #: INV-2026-001
    Date: 2026-11-01
    
    Item Description          Qty   Unit Price   Total
    Organic Fuji Apples       10    2.50         25.00
    Almond Milk 1L            5     4.20         21.00
    Whole Grain Bread         8     1.80         14.40
    
    Subtotal: $60.40
    Tax (5%): $3.02
    Total Due: $63.42
    Thank you for your business!
    """
    res = invoice_parser.parse(text)

    assert "fresh foods market" in res.supplier.lower()
    assert res.invoice_number == "INV-2026-001"
    assert res.date == "2026-11-01"
    assert len(res.items) == 3

    assert res.items[0].name == "Organic Fuji Apples"
    assert res.items[0].quantity == 10
    assert res.items[0].unit_price == 2.50

    assert res.items[1].name == "Almond Milk 1L"
    assert res.items[1].quantity == 5
    assert res.items[1].unit_price == 4.20

    assert res.items[2].name == "Whole Grain Bread"
    assert res.items[2].quantity == 8
    assert res.items[2].unit_price == 1.80

    assert res.requires_review is True  # Review is always required


def test_parse_quantity_first_layout():
    text = """
    Supplier: Tech Supplies Depot Inc.
    Invoice Number: INV-9941
    Dated: 15/10/2026

    Qty   Description                 Price    Total
    20    Coca Cola 500ml             0.75     15.00
    12    Sparkling Water 330ml       1.10     13.20
    4     Orange Juice 1L             3.25     13.00

    Total: $41.20
    """
    res = invoice_parser.parse(text)

    assert "Tech Supplies Depot Inc." in res.supplier
    assert res.invoice_number == "INV-9941"
    assert len(res.items) == 3

    assert res.items[0].name == "Coca Cola 500ml"
    assert res.items[0].quantity == 20
    assert res.items[0].unit_price == 0.75

    assert res.items[1].name == "Sparkling Water 330ml"
    assert res.items[1].quantity == 12
    assert res.items[1].unit_price == 1.10


def test_parse_multiplication_syntax_layout():
    text = """
    From: Beverage Wholesale Ltd
    Invoice No: BW-402
    Date: 2026-10-30

    Red Bull Energy Drink 24 x $1.50 = $36.00
    Green Tea Bottled 12 @ 1.25 = 15.00

    Amount Due: $51.00
    """
    res = invoice_parser.parse(text)

    assert "Beverage Wholesale Ltd" in res.supplier
    assert res.invoice_number == "BW-402"
    assert len(res.items) == 2

    assert res.items[0].name == "Red Bull Energy Drink"
    assert res.items[0].quantity == 24
    assert res.items[0].unit_price == 1.50

    assert res.items[1].name == "Green Tea Bottled"
    assert res.items[1].quantity == 12
    assert res.items[1].unit_price == 1.25


def test_parse_stacked_multiline_layout():
    text = """
    Vendor: Gourmet Goods Store
    Receipt #: RCT-888

    French Roast Ground Coffee
    Qty: 5   Price: $8.50   Total: $42.50

    Organic Raw Honey 500g
    Qty: 2   Price: $12.00   Total: $24.00

    Balance Due: $66.50
    """
    res = invoice_parser.parse(text)

    assert "Gourmet Goods Store" in res.supplier
    assert res.invoice_number == "RCT-888"
    assert len(res.items) == 2

    assert "French Roast Ground Coffee" in res.items[0].name
    assert res.items[0].quantity == 5
    assert res.items[0].unit_price == 8.50

    assert "Organic Raw Honey" in res.items[1].name
    assert res.items[1].quantity == 2
    assert res.items[1].unit_price == 12.00


def test_does_not_fabricate_missing_values():
    # Text with unidentifiable supplier and missing quantities
    text = """
    Just a receipt fragment
    Something was purchased
    Thank you for visiting!
    """
    res = invoice_parser.parse(text)

    # Missing values should NOT be fabricated
    assert res.supplier == ""
    assert res.invoice_number == ""
    assert len(res.items) == 0
    assert res.requires_review is True
    assert len(res.parsing_notes) > 0


def test_currency_and_comma_decimal_handling():
    text = """
    Supplier: European Importers GmbH
    Invoice #: EU-777
    
    Belgian Dark Chocolate 10 2,50 25,00
    Italian Olive Oil 4 12,00 48,00
    
    Total: 73,00 €
    """
    res = invoice_parser.parse(text)

    assert res.supplier == "European Importers GmbH"
    assert res.invoice_number == "EU-777"
    assert len(res.items) == 2
    assert res.items[0].name == "Belgian Dark Chocolate"
    assert res.items[0].quantity == 10
    assert res.items[0].unit_price == 2.50
    assert res.items[1].name == "Italian Olive Oil"
    assert res.items[1].quantity == 4
    assert res.items[1].unit_price == 12.00


def test_arithmetic_discrepancy_flags_item():
    text = """
    Supplier: Test Store
    Invoice #: INV-123
    
    Mismatched Item 5 10.00 99.00
    """
    res = invoice_parser.parse(text)
    assert len(res.items) == 1
    # 5 * 10.00 = 50.00, but line total was 99.00 -> discrepancy
    assert res.items[0].requires_review is True
    assert res.items[0].confidence < 0.8
