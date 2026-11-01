"""
Dedicated Invoice Parsing Engine for StockLens.
Separates document structure and text parsing from raw OCR recognition.

Extracts:
- Supplier name (when identifiable)
- Invoice number (when identifiable)
- Invoice date (when identifiable)
- Structured line items (product name, quantity, unit price)
Flagging values for owner review when confidence is low, and never fabricating missing data.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Currency symbols and abbreviations to recognize and strip cleanly
CURRENCY_REGEX = re.compile(
    r"(?:\$|€|£|¥|៛|\bUSD\b|\bEUR\b|\bGBP\b|\bKHR\b|\bCAD\b|\bAUD\b)",
    re.IGNORECASE,
)

# Column header keywords
TABLE_HEADER_KEYWORDS = {
    "item", "description", "desc", "particulars", "product", "details",
    "qty", "quantity", "unit", "price", "unit price", "rate", "cost",
    "amount", "total", "net", "disc", "discount", "tax", "vat"
}

# Words that indicate summary lines
SUMMARY_STARTS = (
    "subtotal", "sub-total", "sub total", "tax", "vat", "gst", "hst",
    "discount", "disc", "shipping", "freight", "paid", "payment",
    "change", "cash", "credit", "card", "thank you", "terms", "conditions",
    "bank", "account", "iban", "swift", "balance", "balance due",
    "total due", "amount due", "grand total", "net total"
)

# Business suffixes indicating a company name
BUSINESS_SUFFIX_REGEX = re.compile(
    r"\b(ltd\.?|inc\.?|corp\.?|corporation|co\.?|company|llc|gmbh|sa|plc|wholesale|depot|market|supermarket|distributor|supplies|store|shop)\b",
    re.IGNORECASE,
)

# Supplier anchor keywords
SUPPLIER_PREFIXES = [
    r"^(?:supplier|vendor|from|billed\s*by|sold\s*by|company\s*name)[:.\s\-]+(.+)$",
    r"^(?:store|merchant|retailer)[:.\s\-]+(.+)$",
]

# Invoice number anchor keywords (requires explicit label or identifier token)
INVOICE_NUM_PATTERNS = [
    r"\b(?:invoice|inv|inwoice)\b\s*(?:#|no\.?|not|number|num)?[:.\s\-]+([A-Za-z0-9\-_/]+)",
    r"\b(?:receipt|bill)\b\s*(?:#|no\.?|not|number|num)?[:.\s\-]+([A-Za-z0-9\-_/]+)",
    r"\b(INV-\d{3,}[A-Za-z0-9\-]*)\b",
]

# Date anchor patterns
DATE_PATTERNS = [
    # YYYY-MM-DD or YYYY/MM/DD or YYYY.MM.DD
    r"\b(20\d{2}[-/.](?:0[1-9]|1[0-2])[-/.](?:0[1-9]|[12]\d|3[01]))\b",
    # DD-MM-YYYY or DD/MM/YYYY or DD.MM.YYYY
    r"\b((?:0[1-9]|[12]\d|3[01])[-/.](?:0[1-9]|1[0-2])[-/.](?:20\d{2}))\b",
    # Mon DD, YYYY or DD Mon YYYY
    r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+20\d{2})\b",
    r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*,?\s+20\d{2})\b",
]


@dataclass
class ParsedLineItem:
    name: str
    quantity: int
    unit_price: float
    total_price: Optional[float] = None
    confidence: float = 1.0
    requires_review: bool = False
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total_price": self.total_price,
            "confidence": round(self.confidence, 2),
            "requires_review": self.requires_review,
        }


@dataclass
class ParsedInvoice:
    supplier: str = ""
    invoice_number: str = ""
    date: str = ""
    items: List[ParsedLineItem] = field(default_factory=list)
    raw_text: str = ""
    supplier_confidence: float = 0.0
    invoice_number_confidence: float = 0.0
    overall_confidence: float = 0.0
    requires_review: bool = True
    parsing_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "supplier": self.supplier,
            "invoice_number": self.invoice_number,
            "date": self.date,
            "items": [it.to_dict() for it in self.items],
            "raw_text": self.raw_text,
            "supplier_confidence": round(self.supplier_confidence, 2),
            "invoice_number_confidence": round(self.invoice_number_confidence, 2),
            "overall_confidence": round(self.overall_confidence, 2),
            "requires_review": self.requires_review,
            "parsing_notes": self.parsing_notes,
        }


class InvoiceParser:
    """
    Decoupled invoice text parsing engine.
    Understands invoice structures, headers, and tabular line item layouts.
    """

    @staticmethod
    def clean_text(text: str) -> str:
        """Normalizes unicode spaces, pipe characters, and line breaks."""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\u00a0", " ").replace("\u200b", "")
        lines = []
        for line in text.split("\n"):
            cleaned = re.sub(r"^[|\s]+|[|\s]+$", "", line)
            lines.append(cleaned)
        return "\n".join(lines)

    @staticmethod
    def clean_currency_and_numbers(val_str: str) -> Optional[float]:
        """
        Parses numerical monetary or quantity string handling:
        - Currency symbols ($12.50 -> 12.50)
        - European/Cambodian comma decimals (12,50 -> 12.50)
        - Thousands separators (1,250.00 -> 1250.00)
        - OCR character confusion (e.g. O instead of 0)
        """
        s = val_str.strip()
        if not s:
            return None

        # Remove currency symbols
        s = CURRENCY_REGEX.sub("", s).strip()
        # Clean common OCR confusion: O or o instead of 0 in numbers
        s = re.sub(r"(?<=\d)[Oo](?=\d)|(?<=\.)[Oo]|(?<=\,)[Oo]", "0", s)

        # Handle decimal commas vs thousands separators
        if re.match(r"^\d{1,3}(?:,\d{3})+\.\d+$", s):
            s = s.replace(",", "")
        elif re.match(r"^\d{1,3}(?:\.\d{3})+,\d+$", s):
            s = s.replace(".", "").replace(",", ".")
        elif re.match(r"^\d+,\d{1,2}$", s):
            s = s.replace(",", ".")

        # Remove any remaining unwanted characters except digits and decimal point
        s = re.sub(r"[^\d.]", "", s)

        try:
            return float(s)
        except ValueError:
            return None

    def is_metadata_line(self, line: str) -> bool:
        """Checks if line is an invoice header/metadata line."""
        l = line.lower().strip()
        if any(re.match(pat, l) for pat in SUPPLIER_PREFIXES):
            return True
        if any(re.search(pat, l) for pat in INVOICE_NUM_PATTERNS):
            return True
        if re.search(r"^(?:date|dated|invoice\s*date)[:\s\-]+", l):
            return True
        if re.search(r"^(?:invoice|tax invoice|receipt|bill to|ship to|customer|client|page\s*\d+|tel|phone|fax|email|www|http|address)\b", l):
            return True
        return False

    def extract_supplier(self, lines: List[str]) -> Tuple[str, float]:
        """
        Extracts supplier name with confidence:
        1. Explicit prefix: 'Supplier: Fresh Foods Co.'
        2. Prominent line with business suffix ('Inc', 'Ltd', 'Market', 'Depot', etc.)
        3. Top uppercase line followed by invoice metadata
        """
        # Strategy 1: Explicit prefixes
        for line in lines[:15]:
            for pat in SUPPLIER_PREFIXES:
                m = re.match(pat, line.strip(), re.IGNORECASE)
                if m:
                    cand = m.group(1).strip()
                    cand = re.sub(r"^(?:supplier|vendor|from|billed\s*by|sold\s*by)[:.\s\-]+", "", cand, flags=re.IGNORECASE).strip()
                    cand = re.sub(r"^[:\s\-_]+|[:\s\-_]+$", "", cand).strip()
                    if len(cand) >= 3 and not self._is_table_header(cand):
                        return cand, 0.95

        # Strategy 2: Business suffix in the first 8 lines
        for line in lines[:8]:
            cleaned = line.strip()
            if self._is_metadata_or_skip(cleaned):
                continue
            if BUSINESS_SUFFIX_REGEX.search(cleaned):
                return cleaned, 0.85

        # Strategy 3: Top prominent line if followed by invoice metadata
        if len(lines) >= 2:
            top_line = lines[0].strip()
            if not self._is_metadata_or_skip(top_line) and len(top_line) >= 4:
                following_text = " ".join(lines[1:5]).lower()
                if any(w in following_text for w in ["invoice", "date", "bill", "tax"]):
                    if BUSINESS_SUFFIX_REGEX.search(top_line) or top_line.isupper():
                        return top_line, 0.70

        return "", 0.0

    def extract_invoice_number(self, lines: List[str]) -> Tuple[str, float]:
        """Extracts supplier invoice identifier."""
        for line in lines[:25]:
            for pat in INVOICE_NUM_PATTERNS:
                m = re.search(pat, line, re.IGNORECASE)
                if m:
                    cand = m.group(1).strip()
                    cand = re.sub(r"^[:\s\-_]+|[:\s\-_]+$", "", cand)
                    if cand.lower() in {"date", "total", "number", "due", "tax", "fragment", "not", "no", "num", "id"}:
                        sub_m = re.search(r"\b([A-Za-z0-9]+[-_][A-Za-z0-9\-_]+|\d{3,})\b", line)
                        if sub_m:
                            return sub_m.group(1).strip(), 0.85
                        continue
                    if len(cand) >= 2:
                        return cand, 0.90

        return "", 0.0

    def extract_invoice_date(self, lines: List[str]) -> Tuple[str, float]:
        """Extracts invoice date."""
        date_label_pat = re.compile(r"(?:date|dated|invoice\s*date)[:\s\-]+([A-Za-z0-9\s,/\.\-]+)", re.IGNORECASE)
        for line in lines[:25]:
            m = date_label_pat.search(line)
            if m:
                cand = m.group(1).strip()
                for dpat in DATE_PATTERNS:
                    dm = re.search(dpat, cand, re.IGNORECASE)
                    if dm:
                        return dm.group(1).strip(), 0.90

        for line in lines[:25]:
            for dpat in DATE_PATTERNS:
                dm = re.search(dpat, line, re.IGNORECASE)
                if dm:
                    return dm.group(1).strip(), 0.75

        return "", 0.0

    def extract_line_items(self, lines: List[str]) -> List[ParsedLineItem]:
        """Extracts structured line items."""
        items: List[ParsedLineItem] = []
        pending_name: Optional[str] = None

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            # Header row marks start of items table
            if self._is_table_header(line):
                pending_name = None
                continue

            # Summary lines mark end of item list
            if self._is_summary_line(line):
                pending_name = None
                continue

            # Skip metadata lines
            if self.is_metadata_line(line):
                pending_name = None
                continue

            # Attempt parsing strategies (check qty-first if line starts with a digit)
            if line and line[0].isdigit():
                item = (
                    self._parse_strategy_qty_first(line)
                    or self._parse_strategy_multiplication(line)
                    or self._parse_strategy_standard_table(line)
                    or self._parse_strategy_column_aligned(line)
                )
            else:
                item = (
                    self._parse_strategy_multiplication(line)
                    or self._parse_strategy_standard_table(line)
                    or self._parse_strategy_qty_first(line)
                    or self._parse_strategy_column_aligned(line)
                )

            if item:
                item = self._validate_item_arithmetic(item)
                items.append(item)
                pending_name = None
                continue

            # Multi-line stacked continuation
            if pending_name:
                continuation_item = self._parse_stacked_continuation(pending_name, line)
                if continuation_item:
                    continuation_item = self._validate_item_arithmetic(continuation_item)
                    items.append(continuation_item)
                    pending_name = None
                    continue

            # Candidate pending name for stacked multi-line format
            has_letters = bool(re.search(r"[A-Za-z]", line))
            has_price_indicator = bool(re.search(r"[$€£¥៛]|\b\d+[.,]\d{2}\b|\b(?:qty|total|tax|balance)\b", line, re.IGNORECASE))
            if has_letters and not has_price_indicator and not self._is_metadata_or_skip(line) and len(line) >= 3:
                pending_name = line
            else:
                pending_name = None

        return items

    def _parse_strategy_multiplication(self, line: str) -> Optional[ParsedLineItem]:
        """Layout C: [Description] [qty] x [price] or [qty] @ [price]"""
        pat = re.compile(
            r"^(?P<name>[A-Za-z0-9\s\-_.&/]{2,}?)\s+(?P<qty>\d+)\s*(?:x|@|X)\s*[$€£¥៛]?(?P<price>\d+(?:[\.,]\d{1,2})?)(?:\s*(?:=|\s)\s*[$€£¥៛]?(?P<total>\d+(?:[\.,]\d{1,2})?))?$",
            re.IGNORECASE,
        )
        m = pat.match(line)
        if m:
            name = self._clean_product_name(m.group("name"))
            qty = int(m.group("qty"))
            price = self.clean_currency_and_numbers(m.group("price"))
            total = self.clean_currency_and_numbers(m.group("total")) if m.group("total") else None

            if name and qty > 0 and price is not None and price >= 0:
                return ParsedLineItem(
                    name=name,
                    quantity=qty,
                    unit_price=price,
                    total_price=total,
                    confidence=0.95,
                    raw_text=line,
                )
        return None

    def _parse_strategy_standard_table(self, line: str) -> Optional[ParsedLineItem]:
        """Layout A: [Description] [Quantity] [Unit Price] [Optional Total]"""
        tokens = line.split()
        if len(tokens) < 3:
            return None

        # Pattern: ... [Qty] [Price] [Total]
        if len(tokens) >= 4:
            total_cand = self.clean_currency_and_numbers(tokens[-1])
            price_cand = self.clean_currency_and_numbers(tokens[-2])
            qty_cand = tokens[-3]

            if (
                total_cand is not None
                and price_cand is not None
                and qty_cand.isdigit()
                and int(qty_cand) > 0
            ):
                name = self._clean_product_name(" ".join(tokens[:-3]))
                if name:
                    return ParsedLineItem(
                        name=name,
                        quantity=int(qty_cand),
                        unit_price=price_cand,
                        total_price=total_cand,
                        confidence=0.90,
                        raw_text=line,
                    )

        # Pattern: ... [Qty] [Price]
        price_cand = self.clean_currency_and_numbers(tokens[-1])
        qty_cand = tokens[-2]
        if price_cand is not None and qty_cand.isdigit() and int(qty_cand) > 0:
            name = self._clean_product_name(" ".join(tokens[:-2]))
            if name:
                return ParsedLineItem(
                    name=name,
                    quantity=int(qty_cand),
                    unit_price=price_cand,
                    confidence=0.85,
                    raw_text=line,
                )

        return None

    def _parse_strategy_qty_first(self, line: str) -> Optional[ParsedLineItem]:
        """Layout B: [Quantity] [Description] [Unit Price] [Optional Total]"""
        tokens = line.split()
        if len(tokens) < 3:
            return None

        first_token = tokens[0]
        if not (first_token.isdigit() and int(first_token) > 0):
            return None

        qty = int(first_token)

        # Pattern: [Qty] [Name...] [Price] [Total]
        if len(tokens) >= 4:
            total_cand = self.clean_currency_and_numbers(tokens[-1])
            price_cand = self.clean_currency_and_numbers(tokens[-2])
            if total_cand is not None and price_cand is not None:
                name = self._clean_product_name(" ".join(tokens[1:-2]))
                if name:
                    return ParsedLineItem(
                        name=name,
                        quantity=qty,
                        unit_price=price_cand,
                        total_price=total_cand,
                        confidence=0.90,
                        raw_text=line,
                    )

        # Pattern: [Qty] [Name...] [Price]
        price_cand = self.clean_currency_and_numbers(tokens[-1])
        if price_cand is not None:
            name = self._clean_product_name(" ".join(tokens[1:-1]))
            if name:
                return ParsedLineItem(
                    name=name,
                    quantity=qty,
                    unit_price=price_cand,
                    confidence=0.80,
                    raw_text=line,
                )

        return None

    def _parse_strategy_column_aligned(self, line: str) -> Optional[ParsedLineItem]:
        """Layout E: Columns separated by 2 or more spaces, tabs, or pipes."""
        columns = [c.strip() for c in re.split(r"\s{2,}|\t|\|", line) if c.strip()]
        if len(columns) < 3:
            return None

        name_col = None
        qty_col = None
        price_col = None
        total_col = None

        for col in columns:
            cleaned_num = self.clean_currency_and_numbers(col)
            if col.isdigit() and int(col) > 0 and qty_col is None:
                qty_col = int(col)
            elif cleaned_num is not None:
                if price_col is None:
                    price_col = cleaned_num
                elif total_col is None:
                    total_col = cleaned_num
            elif name_col is None and len(col) >= 2:
                name_col = col

        if name_col and qty_col and price_col is not None:
            clean_name = self._clean_product_name(name_col)
            if clean_name:
                return ParsedLineItem(
                    name=clean_name,
                    quantity=qty_col,
                    unit_price=price_col,
                    total_price=total_col,
                    confidence=0.85,
                    raw_text=line,
                )

        return None

    def _parse_stacked_continuation(self, name: str, line: str) -> Optional[ParsedLineItem]:
        """Layout D: Line 1 name, Line 2 numbers."""
        qty = None
        price = None
        total = None

        # Pattern 1: Explicit labels (Qty: 5, Price: 8.50, Total: 42.50)
        qm = re.search(r"\b(?:qty|quantity)[.:\s\-]*(\d+)\b", line, re.IGNORECASE)
        pm = re.search(r"\b(?:price|unit price|rate)[.:\s\-]*[$€£¥៛]?\s*(\d+(?:[\.,]\d{1,2})?)\b", line, re.IGNORECASE)
        tm = re.search(r"\b(?:total|amount)[.:\s\-]*[$€£¥៛]?\s*(\d+(?:[\.,]\d{1,2})?)\b", line, re.IGNORECASE)

        if qm and pm:
            qty = int(qm.group(1))
            price = self.clean_currency_and_numbers(pm.group(1))
            total = self.clean_currency_and_numbers(tm.group(1)) if tm else None

        # Pattern 2: Multiplication (5 @ $8.50 = $42.50 or 5 x 8.50)
        if qty is None or price is None:
            mult_m = re.search(
                r"^\s*(\d+)\s*(?:@|x|X)\s*[$€£¥៛]?\s*(\d+(?:[\.,]\d{1,2})?)(?:\s*(?:=|\s)\s*[$€£¥៛]?\s*(\d+(?:[\.,]\d{1,2})?))?",
                line,
            )
            if mult_m:
                qty = int(mult_m.group(1))
                price = self.clean_currency_and_numbers(mult_m.group(2))
                total = self.clean_currency_and_numbers(mult_m.group(3)) if mult_m.group(3) else None

        if qty and qty > 0 and price is not None:
            clean_name = self._clean_product_name(name)
            if clean_name:
                return ParsedLineItem(
                    name=clean_name,
                    quantity=qty,
                    unit_price=price,
                    total_price=total,
                    confidence=0.85,
                    raw_text=f"{name} // {line}",
                )
        return None

    def _validate_item_arithmetic(self, item: ParsedLineItem) -> ParsedLineItem:
        """
        Verifies line arithmetic: quantity * unit_price == total.
        Detects and rectifies common OCR decimal point dropout (e.g. 250 -> 2.50)
        while flagging for owner review.
        """
        if item.total_price is not None and item.quantity > 0:
            expected_total = round(item.quantity * item.unit_price, 2)
            diff = abs(expected_total - item.total_price)

            # Check if OCR dropped decimal in unit price (e.g. 250 vs 2.50)
            if diff > 0.05 and item.unit_price >= 10:
                adjusted_price = round(item.unit_price / 100.0, 2)
                if abs(round(item.quantity * adjusted_price, 2) - item.total_price) <= 0.05:
                    item.unit_price = adjusted_price
                    item.confidence = 0.80
                    item.requires_review = True
                    return item

            # Check if OCR dropped decimal in total price (e.g. 1440 vs 14.40)
            if diff > 0.05 and item.total_price >= 10:
                adjusted_total = round(item.total_price / 100.0, 2)
                if abs(expected_total - adjusted_total) <= 0.05:
                    item.total_price = adjusted_total
                    item.confidence = 0.80
                    item.requires_review = True
                    return item

            if diff <= 0.05:
                item.confidence = min(1.0, item.confidence + 0.1)
                item.requires_review = False
            else:
                item.confidence = max(0.4, item.confidence - 0.25)
                item.requires_review = True
        return item

    def _clean_product_name(self, name: str) -> str:
        """Cleans stray characters, leading bullets, and excessive spaces."""
        n = re.sub(r"^[\s\-•*#\d.]+", "", name)
        n = re.sub(r"[\s\-_.:;]+$", "", n)
        n = re.sub(r"\s{2,}", " ", n).strip()
        if len(n) < 2 or not re.search(r"[A-Za-z]", n):
            return ""
        # Check if the product name looks like a table header
        words = set(re.findall(r"\b[A-Za-z]+\b", n.lower()))
        if len(words) >= 2 and words.issubset(TABLE_HEADER_KEYWORDS):
            return ""
        return n

    def _is_table_header(self, line: str) -> bool:
        """Checks if line represents a table column header."""
        # If the line contains numerical quantities or prices, it is a data row, not a header row
        if re.search(r"\b\d+(?:[.,]\d+)?\b", line):
            return False
        words = set(re.findall(r"\b[A-Za-z]+\b", line.lower()))
        matched = words.intersection(TABLE_HEADER_KEYWORDS)
        # Table header must contain at least 2 column keywords (e.g. description and price)
        return len(matched) >= 2

    def _is_summary_line(self, line: str) -> bool:
        """Checks if line is a subtotal, tax, or total summary row."""
        line_lower = line.lower().strip()
        # If line contains both qty and price labels, it's an item row, not a summary
        if re.search(r"\b(?:qty|quantity)\b", line_lower) and re.search(r"\b(?:price|rate|@)\b", line_lower):
            return False
        # Starts with summary keyword
        for s in SUMMARY_STARTS:
            if line_lower.startswith(s):
                return True
        # Total line (e.g. Total: $45.00)
        if re.match(r"^total\s*[:\s]\s*[$€£¥៛]?\d", line_lower):
            return True
        return False

    def _is_metadata_or_skip(self, line: str) -> bool:
        """Checks if line contains standard document metadata to skip."""
        l = line.lower().strip()
        return bool(
            re.search(r"^(?:invoice|tax invoice|receipt|bill to|ship to|customer|page|date|tel|phone|fax|email|www|http)", l)
            or re.search(r"^\d+$", l)
            or len(l) < 3
        )

    def parse(self, text: str) -> ParsedInvoice:
        """Parses full raw OCR text into structured ParsedInvoice."""
        cleaned_text = self.clean_text(text)
        lines = [line.strip() for line in cleaned_text.splitlines() if line.strip()]

        if not lines:
            return ParsedInvoice(
                supplier="",
                invoice_number="",
                date="",
                items=[],
                raw_text=text,
                requires_review=True,
                parsing_notes=["Empty or unreadable OCR text."],
            )

        supplier, supp_conf = self.extract_supplier(lines)
        invoice_num, inv_conf = self.extract_invoice_number(lines)
        inv_date, date_conf = self.extract_invoice_date(lines)
        items = self.extract_line_items(lines)

        notes = []
        if not supplier:
            notes.append("Supplier could not be identified automatically.")
        if not invoice_num:
            notes.append("Invoice number could not be identified automatically.")
        if not items:
            notes.append("No line items could be extracted with sufficient confidence.")
        elif any(it.requires_review for it in items):
            notes.append("One or more line items have arithmetic discrepancies and need review.")

        conf_scores = []
        if supplier:
            conf_scores.append(supp_conf)
        if invoice_num:
            conf_scores.append(inv_conf)
        if items:
            item_confs = [it.confidence for it in items]
            conf_scores.append(sum(item_confs) / len(item_confs))

        overall_conf = (sum(conf_scores) / len(conf_scores)) if conf_scores else 0.0

        return ParsedInvoice(
            supplier=supplier,
            invoice_number=invoice_num,
            date=inv_date,
            items=items,
            raw_text=text,
            supplier_confidence=supp_conf,
            invoice_number_confidence=inv_conf,
            overall_confidence=overall_conf,
            requires_review=True,
            parsing_notes=notes,
        )


invoice_parser = InvoiceParser()
