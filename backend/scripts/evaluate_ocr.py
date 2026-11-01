"""
Comprehensive OCR & Parsing Evaluation Script for StockLens.
Runs real OpenCV preprocessing + Tesseract OCR + InvoiceParser on multiple sample invoices.
Measures exact recognition, parsing, field, quantity, and price accuracy against ground truth.
Reports all errors and metrics without claiming unmeasured accuracy.
"""

import sys
from pathlib import Path
from difflib import SequenceMatcher

# Ensure backend directory is in python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.ocr_service import ocr_service
from app.utils.image_validation import validate_image_file


# Ground Truth Dataset
BENCHMARK_DATASET = [
    {
        "filename": "sample_1_grocery_standard.jpg",
        "description": "Standard Tabular Grocery Invoice (JPG, 4 items)",
        "ground_truth": {
            "supplier": "Fresh Foods Market Co.",
            "invoice_number": "INV-2026-081",
            "date": "2026-11-01",
            "items": [
                {"name": "Organic Fuji Apples", "quantity": 10, "unit_price": 2.50},
                {"name": "Almond Milk 1L", "quantity": 5, "unit_price": 4.20},
                {"name": "Whole Grain Bread", "quantity": 8, "unit_price": 1.80},
                {"name": "Avocados Hass Bag", "quantity": 4, "unit_price": 6.50},
            ],
        },
    },
    {
        "filename": "sample_2_electronics_qty_first.png",
        "description": "Quantity-First Electronics Invoice (PNG, 3 items)",
        "ground_truth": {
            "supplier": "Tech Supply Depot Inc.",
            "invoice_number": "INV-9042",
            "date": "2026-10-28",
            "items": [
                {"name": "USB-C Fast Charging Cable 2m", "quantity": 15, "unit_price": 8.50},
                {"name": "HDMI 2.1 Ultra High Speed Cable", "quantity": 6, "unit_price": 14.00},
                {"name": "Wireless Mouse Silent Click", "quantity": 10, "unit_price": 19.99},
            ],
        },
    },
    {
        "filename": "sample_3_beverage_multiplication.jpg",
        "description": "Inline Multiplication Syntax Beverage Invoice (JPG, 3 items)",
        "ground_truth": {
            "supplier": "Beverage Wholesale Ltd",
            "invoice_number": "BW-402",
            "date": "2026-10-30",
            "items": [
                {"name": "Coca Cola 500ml", "quantity": 20, "unit_price": 0.75},
                {"name": "Red Bull Energy Drink", "quantity": 24, "unit_price": 1.50},
                {"name": "Sparkling Natural Water", "quantity": 12, "unit_price": 1.10},
            ],
        },
    },
    {
        "filename": "sample_4_gourmet_stacked.png",
        "description": "Stacked Multi-Line Gourmet Goods Invoice (PNG, 3 items)",
        "ground_truth": {
            "supplier": "Gourmet Goods Store",
            "invoice_number": "RCT-888",
            "date": "2026-10-25",
            "items": [
                {"name": "French Roast Ground Coffee 250g", "quantity": 5, "unit_price": 8.50},
                {"name": "Organic Raw Forest Honey 500g", "quantity": 2, "unit_price": 12.00},
                {"name": "Belgian Dark Cocoa Powder", "quantity": 3, "unit_price": 7.25},
            ],
        },
    },
    {
        "filename": "sample_5_tilted_grocery.jpg",
        "description": "Tilted 3.5-degree Grocery Invoice with Deskew (JPG, 4 items)",
        "ground_truth": {
            "supplier": "Fresh Foods Market Co.",
            "invoice_number": "INV-2026-081",
            "date": "2026-11-01",
            "items": [
                {"name": "Organic Fuji Apples", "quantity": 10, "unit_price": 2.50},
                {"name": "Almond Milk 1L", "quantity": 5, "unit_price": 4.20},
                {"name": "Whole Grain Bread", "quantity": 8, "unit_price": 1.80},
                {"name": "Avocados Hass Bag", "quantity": 4, "unit_price": 6.50},
            ],
        },
    },
]


def text_similarity(a: str, b: str) -> float:
    """Computes string similarity ratio between 0.0 and 1.0."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def run_evaluation():
    samples_dir = Path("sample_invoices")
    results = []

    total_fields_expected = 0
    total_fields_correct = 0

    total_items_expected = 0
    total_items_extracted = 0
    total_quantities_correct = 0
    total_prices_correct = 0

    recognition_errors = []
    parsing_errors = []
    missing_fields = []
    incorrect_quantities = []
    incorrect_prices = []

    print("\n" + "=" * 80)
    print(" STOCKLENS OCR & INVOICE PARSING ACCURACY BENCHMARK ")
    print("=" * 80)

    for entry in BENCHMARK_DATASET:
        filename = entry["filename"]
        file_path = samples_dir / filename
        gt = entry["ground_truth"]

        if not file_path.exists():
            print(f"File missing: {file_path}")
            continue

        raw_bytes = file_path.read_bytes()
        extracted = ocr_service.extract_from_image(raw_bytes, filename=filename)

        ext_supplier = extracted.get("supplier", "").strip()
        ext_invoice_num = extracted.get("invoice_number", "").strip()
        ext_date = extracted.get("date", "").strip()
        ext_items = extracted.get("items", [])
        raw_text = extracted.get("raw_text", "")

        # 1. Supplier Evaluation
        total_fields_expected += 1
        supplier_sim = text_similarity(ext_supplier, gt["supplier"])
        supplier_match = supplier_sim >= 0.85
        if supplier_match:
            total_fields_correct += 1
        else:
            if not ext_supplier:
                missing_fields.append(f"[{filename}] Missing supplier (expected '{gt['supplier']}')")
            else:
                recognition_errors.append(f"[{filename}] Supplier mismatch: extracted '{ext_supplier}', expected '{gt['supplier']}'")

        # 2. Invoice Number Evaluation
        total_fields_expected += 1
        inv_num_match = ext_invoice_num.lower() == gt["invoice_number"].lower()
        if inv_num_match:
            total_fields_correct += 1
        else:
            if not ext_invoice_num:
                missing_fields.append(f"[{filename}] Missing invoice_number (expected '{gt['invoice_number']}')")
            else:
                recognition_errors.append(f"[{filename}] Invoice number mismatch: extracted '{ext_invoice_num}', expected '{gt['invoice_number']}'")

        # 3. Date Evaluation
        total_fields_expected += 1
        date_match = ext_date == gt["date"]
        if date_match:
            total_fields_correct += 1
        else:
            if not ext_date:
                missing_fields.append(f"[{filename}] Missing date (expected '{gt['date']}')")
            else:
                parsing_errors.append(f"[{filename}] Date mismatch: extracted '{ext_date}', expected '{gt['date']}'")

        # 4. Line Items Evaluation
        total_items_expected += len(gt["items"])
        total_items_extracted += len(ext_items)

        # Match extracted items with ground truth items
        matched_gt_indices = set()
        for it in ext_items:
            best_idx = None
            best_sim = 0.0
            for idx, gt_it in enumerate(gt["items"]):
                if idx in matched_gt_indices:
                    continue
                sim = text_similarity(it["name"], gt_it["name"])
                if sim > best_sim:
                    best_sim = sim
                    best_idx = idx

            if best_idx is not None and best_sim >= 0.5:
                matched_gt_indices.add(best_idx)
                gt_match = gt["items"][best_idx]

                # Check quantity
                if it["quantity"] == gt_match["quantity"]:
                    total_quantities_correct += 1
                else:
                    incorrect_quantities.append(
                        f"[{filename}] '{it['name']}': extracted qty {it['quantity']}, expected {gt_match['quantity']}"
                    )

                # Check price
                if abs(it["unit_price"] - gt_match["unit_price"]) <= 0.02:
                    total_prices_correct += 1
                else:
                    incorrect_prices.append(
                        f"[{filename}] '{it['name']}': extracted price ${it['unit_price']:.2f}, expected ${gt_match['unit_price']:.2f}"
                    )
            else:
                parsing_errors.append(
                    f"[{filename}] Extracted unexpected or poorly matched item: '{it['name']}'"
                )

        unmatched_count = len(gt["items"]) - len(matched_gt_indices)
        if unmatched_count > 0:
            for idx, gt_it in enumerate(gt["items"]):
                if idx not in matched_gt_indices:
                    missing_fields.append(
                        f"[{filename}] Unextracted line item: '{gt_it['name']}' (qty {gt_it['quantity']}, price {gt_it['unit_price']})"
                    )

        results.append({
            "filename": filename,
            "description": entry["description"],
            "supplier": (ext_supplier, supplier_match),
            "invoice_number": (ext_invoice_num, inv_num_match),
            "date": (ext_date, date_match),
            "items_expected": len(gt["items"]),
            "items_extracted": len(ext_items),
            "items_matched": len(matched_gt_indices),
        })

    # Summary Statistics
    header_field_accuracy = (total_fields_correct / total_fields_expected * 100) if total_fields_expected else 0.0
    item_recall = (total_items_extracted / total_items_expected * 100) if total_items_expected else 0.0
    qty_accuracy = (total_quantities_correct / total_items_expected * 100) if total_items_expected else 0.0
    price_accuracy = (total_prices_correct / total_items_expected * 100) if total_items_expected else 0.0

    print("\nSAMPLE RESULTS SUMMARY:")
    for r in results:
        supp_st = "PASS" if r["supplier"][1] else "FAIL"
        inv_st = "PASS" if r["invoice_number"][1] else "FAIL"
        date_st = "PASS" if r["date"][1] else "FAIL"
        print(f"  * {r['filename']} ({r['description']}):")
        print(f"      - Supplier:       '{r['supplier'][0]}' [{supp_st}]")
        print(f"      - Invoice Number: '{r['invoice_number'][0]}' [{inv_st}]")
        print(f"      - Invoice Date:   '{r['date'][0]}' [{date_st}]")
        print(f"      - Line Items:     {r['items_matched']}/{r['items_expected']} matched ({r['items_extracted']} parsed)")

    print("\n" + "=" * 80)
    print(" MEASURED ACCURACY METRICS ")
    print("=" * 80)
    print(f"  Total Invoices Tested:              {len(BENCHMARK_DATASET)}")
    print(f"  Header Fields Accuracy:             {header_field_accuracy:.1f}% ({total_fields_correct}/{total_fields_expected})")
    print(f"  Line Item Detection Recall:         {item_recall:.1f}% ({total_items_extracted}/{total_items_expected})")
    print(f"  Quantity Extraction Accuracy:       {qty_accuracy:.1f}% ({total_quantities_correct}/{total_items_expected})")
    print(f"  Unit Price Extraction Accuracy:     {price_accuracy:.1f}% ({total_prices_correct}/{total_items_expected})")

    print("\n" + "=" * 80)
    print(" ERROR CATEGORIZATION REPORT ")
    print("=" * 80)

    print(f"\n1. Recognition Errors ({len(recognition_errors)}):")
    if recognition_errors:
        for err in recognition_errors:
            print(f"   - {err}")
    else:
        print("   - None detected.")

    print(f"\n2. Parsing Errors ({len(parsing_errors)}):")
    if parsing_errors:
        for err in parsing_errors:
            print(f"   - {err}")
    else:
        print("   - None detected.")

    print(f"\n3. Missing Fields ({len(missing_fields)}):")
    if missing_fields:
        for err in missing_fields:
            print(f"   - {err}")
    else:
        print("   - None detected.")

    print(f"\n4. Incorrect Quantities ({len(incorrect_quantities)}):")
    if incorrect_quantities:
        for err in incorrect_quantities:
            print(f"   - {err}")
    else:
        print("   - None detected.")

    print(f"\n5. Incorrect Prices ({len(incorrect_prices)}):")
    if incorrect_prices:
        for err in incorrect_prices:
            print(f"   - {err}")
    else:
        print("   - None detected.")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    run_evaluation()
