"""Turns OCR output into structured invoice line items."""
import re
from .schemas import Field, LineItem, OcrResult
from .preprocess import prepare
from .table import find_table, cells, ink_ratio
from . import  ocr

LOW_CONF = 60.0
EMPTY_INK = 0.02

# Column header keywords (English + Khmer). Order matters: "amount" must be
# tested before "quantity" because Khmer "ចំនួនសរុប" (amount) contains "ចំនួន" (quantity).
HEADER_RULES = [
    ("total", re.compile(r"amount|total|សរុប", re.I)),
    ("unit_price", re.compile(r"unit|price|rate|តម្លៃ", re.I)),
    ("quantity", re.compile(r"quant|qty|ចំនួន", re.I)),
    ("name", re.compile(r"descr|item|product|name|ឈ្មោះ|ទំនិញ|មុខ", re.I)),
]
DEFAULT_ORDER = ["index", "name", "quantity", "unit_price", "total"]
CURRENCY = "$#៛฿€£"


def parse_number(s: str) -> float | None:
    """'#165' -> 165, '$1,250.50' -> 1250.5, '1.250,50' -> 1250.5. '#' is how many
    people handwrite '$'."""
    s = re.sub(rf"[{re.escape(CURRENCY)}\s]", "", s or "")
    s = re.sub(r"[^\d.,]", "", s)
    if not s:
        return None
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        thou = "." if dec == "," else ","
        s = s.replace(thou, "").replace(dec, ".")
    elif "," in s:
        s = s.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", s) else s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _num_field(text: str, conf: float) -> Field:
    v = parse_number(text)
    if v is not None and v == int(v):
        v = int(v)
    return Field(value=v, confidence=round(conf, 1), needs_review=(v is None or conf < LOW_CONF))


def _map_columns(header_texts: list[str]) -> list[str | None]:
    mapping: list[str | None] = []
    for t in header_texts:
        key = next((k for k, rx in HEADER_RULES if rx.search(t)), None)
        mapping.append(key if key not in mapping else None)
    return mapping


def _validate(item: LineItem) -> None:
    q, u, t = (item.quantity.value, item.unit_price.value, item.total.value)
    if isinstance(q, (int, float)) and isinstance(u, (int, float)):
        if t is None:
            item.total = Field(value=round(q * u, 2), confidence=0, needs_review=True)
            item.warnings.append("total calculated from quantity x unit price")
        elif abs(q * u - t) > 0.01:
            item.warnings.append(f"quantity x unit price = {q * u:g}, but total reads {t:g}")
            for f in (item.quantity, item.unit_price, item.total):
                f.needs_review = True
    elif isinstance(u, (int, float)) and isinstance(t, (int, float)) and q is None and u:
        item.quantity = Field(value=round(t / u, 3), confidence=0, needs_review=True)
        item.warnings.append("quantity calculated from total / unit price")
    if not item.name.value:
        item.name.needs_review = True
        item.warnings.append("missing product name")


def _meta(text: str) -> tuple[str | None, str | None]:
    no = re.search(r"\binvoice\b\s*(?:no|#|number)?[\s.:#]*([A-Z]*-?\d{3,}[A-Z0-9-]*)", text, re.I)
    date = re.search(r"(\d{1,2}\s*[/.-]\s*\d{1,2}\s*[/.-]\s*\d{2,4})", text)
    return (no.group(1) if no else None, re.sub(r"\s", "", date.group(1)) if date else None)


# ---------- strategy 1: ruled table ----------
def parse_table(gray, xs, ys) -> list[LineItem]:
    grid = {(r, c): crop for r, c, crop in cells(gray, xs, ys)}
    ncols, nrows = len(xs) - 1, len(ys) - 1

    header_texts = [ocr.ocr_cell(grid[0, c])[0] if ink_ratio(grid[0, c]) > EMPTY_INK else ""
                    for c in range(ncols)]
    # header cells hold two lines (Khmer + English), so read them with a block psm
    header_texts = [ocr.ocr_text(grid[0, c], psm=6)[0] for c in range(ncols)]
    mapping = _map_columns(header_texts)
    if "name" not in mapping or "quantity" not in mapping:      # fallback: fixed order
        mapping = DEFAULT_ORDER[-ncols:] if ncols <= len(DEFAULT_ORDER) else [None] * ncols

    items = []
    for r in range(1, nrows):
        if all(ink_ratio(grid[r, c]) < EMPTY_INK for c in range(ncols)
               if mapping[c] in ("name", "quantity", "unit_price", "total")):
            continue                                              # blank row
        vals = {}
        for c in range(ncols):
            key = mapping[c]
            if key in (None, "index"):
                continue
            if ink_ratio(grid[r, c]) < EMPTY_INK:
                vals[key] = ("", 0.0)
            else:
                vals[key] = ocr.ocr_cell(grid[r, c], numeric=key != "name")
        name_t, name_c = vals.get("name", ("", 0.0))
        item = LineItem(
            row=r,
            name=Field(value=name_t or None, confidence=round(name_c, 1),
                       needs_review=(not name_t or name_c < LOW_CONF)),
            quantity=_num_field(*vals.get("quantity", ("", 0.0))),
            unit_price=_num_field(*vals.get("unit_price", ("", 0.0))),
            total=_num_field(*vals.get("total", ("", 0.0))),
        )
        _validate(item)
        items.append(item)
    return items


# ---------- strategy 2: plain text lines ----------
_NUM = rf"[{re.escape(CURRENCY)}]?\s*\d[\d.,]*"
LINE_RX = re.compile(rf"^(?P<name>.+?)\s+(?P<q>\d+(?:\.\d+)?)\s+(?P<u>{_NUM})\s+(?P<t>{_NUM})\s*$")
LINE_RX_NO_UNIT = re.compile(rf"^(?P<name>.+?)\s+(?P<q>\d+(?:\.\d+)?)\s+(?P<t>{_NUM})\s*$")


def parse_text(gray) -> list[LineItem]:
    items = []
    for i, (line, conf) in enumerate(ocr.ocr_lines(gray)):
        line = re.sub(r"^\s*\d{1,3}[.)]?\s+(?=\D)", "", line.strip())   # drop row number
        m = LINE_RX.match(line)
        if m:
            q, u, t = m["q"], m["u"], m["t"]
        else:
            m = LINE_RX_NO_UNIT.match(line)
            if not m:
                continue
            q, u, t = m["q"], "", m["t"]
        item = LineItem(
            row=i,
            name=Field(value=m["name"].strip(), confidence=round(conf, 1), needs_review=conf < LOW_CONF),
            quantity=_num_field(q, conf), unit_price=_num_field(u, conf if u else 0), total=_num_field(t, conf),
        )
        _validate(item)
        items.append(item)
    return items


# ---------- entry point ----------
def process_invoice(data: bytes) -> OcrResult:
    gray = prepare(data)
    grid = find_table(gray)
    warnings: list[str] = []
    if grid:
        items, method = parse_table(gray, *grid), "table"
    else:
        items, method = parse_text(gray), "text"
        warnings.append("No ruled table found; used text-line parsing.")
    if not items:
        warnings.append("No line items detected. Try a clearer, straight-on photo.")
    top = gray[: int(gray.shape[0] * 0.4)]
    no, date = _meta(ocr.ocr_text(top)[0])
    return OcrResult(method=method, invoice_number=no, date=date, items=items, warnings=warnings)
