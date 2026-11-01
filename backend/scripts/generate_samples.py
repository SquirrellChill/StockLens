"""
Generates realistic sample invoice images for testing and benchmarking StockLens OCR.
"""

from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def generate_samples():
    out_dir = Path("sample_invoices")
    out_dir.mkdir(exist_ok=True)

    # -------------------------------------------------------------
    # Sample 1: Standard Tabular Grocery Invoice (JPG)
    # -------------------------------------------------------------
    img1 = Image.new("RGB", (900, 1100), color=(255, 255, 255))
    d1 = ImageDraw.Draw(img1)
    d1.text((60, 50), "Fresh Foods Market Co.", fill=(0, 0, 0))
    d1.text((60, 80), "123 Monivong Blvd, Phnom Penh, Cambodia", fill=(80, 80, 80))
    d1.text((60, 110), "Tel: +855 23 888 999 | Email: contact@freshfoods.com", fill=(80, 80, 80))
    d1.line([(60, 140), (840, 140)], fill=(0, 0, 0), width=2)

    d1.text((60, 160), "Supplier: Fresh Foods Market Co.", fill=(0, 0, 0))
    d1.text((60, 190), "Invoice #: INV-2026-081", fill=(0, 0, 0))
    d1.text((60, 220), "Date: 2026-11-01", fill=(0, 0, 0))

    d1.line([(60, 260), (840, 260)], fill=(120, 120, 120), width=1)
    d1.text((60, 275), "Item Description", fill=(0, 0, 0))
    d1.text((500, 275), "Qty", fill=(0, 0, 0))
    d1.text((600, 275), "Unit Price", fill=(0, 0, 0))
    d1.text((740, 275), "Total", fill=(0, 0, 0))
    d1.line([(60, 305), (840, 305)], fill=(120, 120, 120), width=1)

    items1 = [
        ("Organic Fuji Apples", "10", "2.50", "25.00"),
        ("Almond Milk 1L", "5", "4.20", "21.00"),
        ("Whole Grain Bread", "8", "1.80", "14.40"),
        ("Avocados Hass Bag", "4", "6.50", "26.00"),
    ]
    y = 330
    for name, qty, price, total in items1:
        d1.text((60, y), name, fill=(0, 0, 0))
        d1.text((510, y), qty, fill=(0, 0, 0))
        d1.text((610, y), price, fill=(0, 0, 0))
        d1.text((740, y), total, fill=(0, 0, 0))
        y += 40

    d1.line([(60, y + 20), (840, y + 20)], fill=(0, 0, 0), width=1)
    d1.text((560, y + 40), "Subtotal: $86.40", fill=(0, 0, 0))
    d1.text((560, y + 70), "Tax (0%): $0.00", fill=(0, 0, 0))
    d1.text((560, y + 100), "Total Due: $86.40", fill=(0, 0, 0))
    img1.save(out_dir / "sample_1_grocery_standard.jpg", "JPEG", quality=95)

    # -------------------------------------------------------------
    # Sample 2: Quantity-First Electronics Invoice (PNG)
    # -------------------------------------------------------------
    img2 = Image.new("RGB", (900, 1000), color=(255, 255, 255))
    d2 = ImageDraw.Draw(img2)
    d2.text((60, 50), "TECH SUPPLY DEPOT INC.", fill=(0, 0, 0))
    d2.text((60, 80), "Warehouse Logistics Hub, Phnom Penh", fill=(80, 80, 80))
    d2.line([(60, 110), (840, 110)], fill=(0, 0, 0), width=2)

    d2.text((60, 130), "Supplier: Tech Supply Depot Inc.", fill=(0, 0, 0))
    d2.text((60, 160), "Invoice Number: INV-9042", fill=(0, 0, 0))
    d2.text((60, 190), "Invoice Date: 2026-10-28", fill=(0, 0, 0))

    d2.line([(60, 230), (840, 230)], fill=(120, 120, 120), width=1)
    d2.text((60, 245), "Qty", fill=(0, 0, 0))
    d2.text((160, 245), "Description", fill=(0, 0, 0))
    d2.text((620, 245), "Unit Price", fill=(0, 0, 0))
    d2.text((740, 245), "Total", fill=(0, 0, 0))
    d2.line([(60, 275), (840, 275)], fill=(120, 120, 120), width=1)

    items2 = [
        ("15", "USB-C Fast Charging Cable 2m", "8.50", "127.50"),
        ("6", "HDMI 2.1 Ultra High Speed Cable", "14.00", "84.00"),
        ("10", "Wireless Mouse Silent Click", "19.99", "199.90"),
    ]
    y = 300
    for qty, name, price, total in items2:
        d2.text((70, y), qty, fill=(0, 0, 0))
        d2.text((160, y), name, fill=(0, 0, 0))
        d2.text((630, y), price, fill=(0, 0, 0))
        d2.text((740, y), total, fill=(0, 0, 0))
        y += 40

    d2.line([(60, y + 20), (840, y + 20)], fill=(0, 0, 0), width=1)
    d2.text((560, y + 40), "Total: $411.40", fill=(0, 0, 0))
    img2.save(out_dir / "sample_2_electronics_qty_first.png", "PNG")

    # -------------------------------------------------------------
    # Sample 3: Inline Multiplication Syntax Beverage Invoice (JPG)
    # -------------------------------------------------------------
    img3 = Image.new("RGB", (900, 950), color=(255, 255, 255))
    d3 = ImageDraw.Draw(img3)
    d3.text((60, 50), "BEVERAGE WHOLESALE DISTRIBUTORS", fill=(0, 0, 0))
    d3.text((60, 80), "From: Beverage Wholesale Ltd", fill=(0, 0, 0))
    d3.text((60, 110), "Invoice No: BW-402", fill=(0, 0, 0))
    d3.text((60, 140), "Date: 2026-10-30", fill=(0, 0, 0))
    d3.line([(60, 175), (840, 175)], fill=(0, 0, 0), width=2)

    items3 = [
        ("Coca Cola 500ml", "20", "0.75", "15.00"),
        ("Red Bull Energy Drink", "24", "1.50", "36.00"),
        ("Sparkling Natural Water", "12", "1.10", "13.20"),
    ]
    y = 210
    for name, qty, price, total in items3:
        d3.text((60, y), f"{name} {qty} x ${price} = ${total}", fill=(0, 0, 0))
        y += 45

    d3.line([(60, y + 20), (840, y + 20)], fill=(0, 0, 0), width=1)
    d3.text((540, y + 40), "Amount Due: $64.20", fill=(0, 0, 0))
    img3.save(out_dir / "sample_3_beverage_multiplication.jpg", "JPEG", quality=95)

    # -------------------------------------------------------------
    # Sample 4: Stacked Multi-Line Gourmet Invoice (PNG)
    # -------------------------------------------------------------
    img4 = Image.new("RGB", (900, 1000), color=(255, 255, 255))
    d4 = ImageDraw.Draw(img4)
    d4.text((60, 50), "GOURMET GOODS SPECIALTY STORE", fill=(0, 0, 0))
    d4.text((60, 80), "Vendor: Gourmet Goods Store", fill=(0, 0, 0))
    d4.text((60, 110), "Receipt #: RCT-888", fill=(0, 0, 0))
    d4.text((60, 140), "Date: 2026-10-25", fill=(0, 0, 0))
    d4.line([(60, 175), (840, 175)], fill=(0, 0, 0), width=2)

    items4 = [
        ("French Roast Ground Coffee 250g", "5", "8.50", "42.50"),
        ("Organic Raw Forest Honey 500g", "2", "12.00", "24.00"),
        ("Belgian Dark Cocoa Powder", "3", "7.25", "21.75"),
    ]
    y = 210
    for name, qty, price, total in items4:
        d4.text((60, y), name, fill=(0, 0, 0))
        y += 28
        d4.text((80, y), f"Qty: {qty}   Price: ${price}   Total: ${total}", fill=(50, 50, 50))
        y += 45

    d4.line([(60, y + 20), (840, y + 20)], fill=(0, 0, 0), width=1)
    d4.text((540, y + 40), "Balance Due: $88.25", fill=(0, 0, 0))
    img4.save(out_dir / "sample_4_gourmet_stacked.png", "PNG")

    # -------------------------------------------------------------
    # Sample 5: Tilted / Skewed Image (Simulating phone capture)
    # -------------------------------------------------------------
    arr1 = cv2.cvtColor(np.array(img1), cv2.COLOR_RGB2BGR)
    center = (450, 550)
    matrix = cv2.getRotationMatrix2D(center, 3.5, 1.0)
    skewed = cv2.warpAffine(arr1, matrix, (900, 1100), borderValue=(255, 255, 255))
    cv2.imwrite(str(out_dir / "sample_5_tilted_grocery.jpg"), skewed)

    print("Successfully generated 5 diverse invoice samples in 'sample_invoices/'.")


if __name__ == "__main__":
    generate_samples()
