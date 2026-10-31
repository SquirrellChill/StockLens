"""Tesseract wrappers. Languages: Khmer + English."""
import cv2
import numpy as np
import pytesseract
from pytesseract import Output

LANG = "khm+eng"
NUM_CFG = "--psm 7 -c tessedit_char_whitelist=0123456789.,$#៛"


def _clean_for_ocr(gray_crop: np.ndarray, scale: int = 3) -> np.ndarray:
    g = cv2.resize(gray_crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    g = cv2.GaussianBlur(g, (3, 3), 0)
    bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return cv2.copyMakeBorder(bw, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)


def ocr_text(gray: np.ndarray, psm: int = 6, lang: str = LANG) -> tuple[str, float]:
    """Full-region OCR. Returns (text, mean word confidence)."""
    d = pytesseract.image_to_data(gray, lang=lang, config=f"--psm {psm}",
                                  output_type=Output.DICT)
    words = [(t, float(c)) for t, c in zip(d["text"], d["conf"]) if t.strip() and float(c) >= 0]
    text = pytesseract.image_to_string(gray, lang=lang, config=f"--psm {psm}").strip()
    conf = sum(c for _, c in words) / len(words) if words else 0.0
    return text, conf


def ocr_cell(gray_crop: np.ndarray, numeric: bool = False) -> tuple[str, float]:
    img = _clean_for_ocr(gray_crop)
    cfg = NUM_CFG if numeric else "--psm 7"
    lang = "eng" if numeric else LANG
    d = pytesseract.image_to_data(img, lang=lang, config=cfg, output_type=Output.DICT)
    parts, confs = [], []
    for t, c in zip(d["text"], d["conf"]):
        if t.strip() and float(c) >= 0:
            parts.append(t.strip())
            confs.append(float(c))
    return " ".join(parts), (sum(confs) / len(confs) if confs else 0.0)


def ocr_lines(gray: np.ndarray) -> list[tuple[str, float]]:
    """Line-by-line OCR for invoices without a ruled table."""
    d = pytesseract.image_to_data(gray, lang=LANG, config="--psm 6", output_type=Output.DICT)
    lines: dict[tuple, list] = {}
    for i, t in enumerate(d["text"]):
        if t.strip() and float(d["conf"][i]) >= 0:
            key = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
            lines.setdefault(key, []).append((d["left"][i], t, float(d["conf"][i])))
    out = []
    for words in lines.values():
        words.sort()
        out.append((" ".join(w[1] for w in words), sum(w[2] for w in words) / len(words)))
    return out
