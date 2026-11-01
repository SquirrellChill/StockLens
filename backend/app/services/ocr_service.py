"""
OCR and Invoice Extraction Service for StockLens.
Integrates OpenCV image preprocessing, Tesseract OCR recognition,
and decoupled invoice parsing logic.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
import pytesseract

from app.core.config import settings
from app.core.exceptions import (
    OCRDependencyUnavailableError,
)
from app.services.invoice_parser import invoice_parser
from app.utils.image_processing import preprocess_invoice_image
from app.utils.image_validation import validate_image_file, safe_temp_image_file

logger = logging.getLogger(__name__)

# Common default installation paths for Tesseract
WORKSPACE_TESSERACT = Path(__file__).resolve().parent.parent.parent / "tools" / "tesseract" / "tesseract.exe"
WINDOWS_COMMON_PATHS = [
    str(WORKSPACE_TESSERACT),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
if os.environ.get("LOCALAPPDATA"):
    WINDOWS_COMMON_PATHS.append(
        str(Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Tesseract-OCR" / "tesseract.exe")
    )


class OCRService:
    """
    Service managing OCR operations, Tesseract runtime resolution,
    and invoking the decoupled invoice parser.
    """

    def __init__(self):
        self._tesseract_cmd: Optional[str] = None
        self._is_available: Optional[bool] = None
        self.resolve_tesseract_path()

    def resolve_tesseract_path(self) -> Optional[str]:
        """
        Attempts to resolve the Tesseract OCR binary:
        1. Configured TESSERACT_CMD from settings / environment.
        2. System PATH.
        3. Standard Windows installation directories.

        Configures pytesseract with the resolved binary path.
        """
        candidate = settings.TESSERACT_CMD.strip() if settings.TESSERACT_CMD else "tesseract"

        # Check if configured binary is directly on PATH or is a valid absolute/relative file
        resolved = shutil.which(candidate)
        if not resolved and Path(candidate).is_file():
            resolved = str(Path(candidate).resolve())

        # If on Windows and not yet found, check standard locations
        if not resolved and os.name == "nt":
            for common_path in WINDOWS_COMMON_PATHS:
                if Path(common_path).is_file():
                    resolved = common_path
                    logger.info(f"Auto-discovered Tesseract OCR at: {resolved}")
                    break

        if resolved:
            self._tesseract_cmd = resolved
            pytesseract.pytesseract.tesseract_cmd = resolved
        else:
            self._tesseract_cmd = None

        return self._tesseract_cmd

    def is_tesseract_installed(self) -> bool:
        """
        Verifies whether Tesseract OCR application is installed and working.
        Executes a version check to guarantee the binary is functional.
        """
        cmd = self.resolve_tesseract_path()
        if not cmd:
            self._is_available = False
            return False

        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract OCR verified: version {version} at '{cmd}'")
            self._is_available = True
            return True
        except Exception as e:
            logger.warning(f"Tesseract executable '{cmd}' verification failed: {e}")
            self._is_available = False
            return False

    def get_tesseract_info(self) -> Dict[str, Any]:
        """
        Returns diagnostic information about the Tesseract installation status.
        """
        cmd = self.resolve_tesseract_path()
        available = self.is_tesseract_installed()
        version = None
        if available:
            try:
                version = str(pytesseract.get_tesseract_version())
            except Exception:
                pass

        return {
            "available": available,
            "cmd": cmd,
            "configured_setting": settings.TESSERACT_CMD,
            "version": version,
        }

    def run_ocr(self, primary_img, fallback_img) -> str:
        """
        Runs Tesseract OCR recognition on preprocessed image arrays.
        Uses PSM 6 (uniform block of text) and falls back to PSM 3 (auto page segmentation)
        or binary image if output is sparse.
        """
        try:
            text = pytesseract.image_to_string(primary_img, config="--psm 6")
        except Exception as e:
            logger.warning(f"Primary OCR failed: {e}")
            text = ""

        # If primary text is very short, try fallback image
        if len(text.strip()) < 20:
            try:
                fallback_text = pytesseract.image_to_string(fallback_img, config="--psm 6")
                if len(fallback_text.strip()) > len(text.strip()):
                    text = fallback_text
            except Exception as e:
                logger.warning(f"Fallback OCR failed: {e}")

        # If still sparse, try default auto-segmentation (PSM 3)
        if len(text.strip()) < 20:
            try:
                psm3_text = pytesseract.image_to_string(primary_img, config="--psm 3")
                if len(psm3_text.strip()) > len(text.strip()):
                    text = psm3_text
            except Exception as e:
                logger.warning(f"PSM 3 fallback failed: {e}")

        return text

    def extract_from_image(
        self,
        image_bytes: bytes,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes the full invoice upload and OCR pipeline:
        1. Validates image bytes, dimensions, and formats (rejects unsupported/empty/corrupted/oversized).
        2. Checks Tesseract availability, raising OCRDependencyUnavailableError if missing.
        3. Runs OpenCV preprocessing (deskew, resolution normalization, contrast enhancement, denoising, binarization).
        4. Executes Tesseract OCR recognition.
        5. Parses structured invoice information via decoupled InvoiceParser.
        6. Returns structured response with owner review flag.
        """
        import cv2
        from app.utils.image_processing import improve_contrast, apply_threshold

        # Step 1: Validate image
        detected_fmt, decoded_img = validate_image_file(image_bytes, filename=filename)

        # Step 2: Check Tesseract dependency
        if not self.is_tesseract_installed():
            logger.error("OCR requested but Tesseract application is not installed on the server.")
            raise OCRDependencyUnavailableError(
                "OCR dependency unavailable: Tesseract OCR is not installed or configured on the server. "
                "Please install Tesseract-OCR and configure TESSERACT_CMD in your environment."
            )

        # Step 3: OpenCV image preprocessing
        preprocess_result = preprocess_invoice_image(decoded_img)
        deskewed = preprocess_result["deskewed_image"]

        # Scale image to optimal DPI (~300 DPI / 2x) for Tesseract character recognition
        h, w = deskewed.shape[:2]
        if max(h, w) < 2400:
            scale_factor = 2.0
            enhanced = cv2.resize(deskewed, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
        else:
            enhanced = deskewed

        enhanced_gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY) if enhanced.ndim == 3 else enhanced
        clahe_gray = improve_contrast(enhanced_gray, method="clahe", clip_limit=1.5)
        binary_img = apply_threshold(clahe_gray, method="otsu")

        # Step 4: Perform OCR recognition
        # High-resolution smooth grayscale preserves delicate character strokes and periods
        raw_text = self.run_ocr(enhanced_gray, clahe_gray)

        # Step 5: Decoupled parsing of invoice information and line items
        parsed = invoice_parser.parse(raw_text)

        return {
            "supplier": parsed.supplier,
            "invoice_number": parsed.invoice_number,
            "date": parsed.date,
            "items": [
                {
                    "name": it.name,
                    "quantity": it.quantity,
                    "unit_price": it.unit_price,
                }
                for it in parsed.items
            ],
            "raw_text": parsed.raw_text,
            "confidence": parsed.overall_confidence,
            "requires_review": parsed.requires_review,
            "parsing_notes": parsed.parsing_notes,
        }


ocr_service = OCRService()
