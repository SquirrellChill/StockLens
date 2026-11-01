"""
Image validation and safe temporary file handling utilities for StockLens.
"""

import io
import logging
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional, Tuple
import cv2
import numpy as np
from PIL import Image

from app.core.config import settings
from app.core.exceptions import (
    CorruptedImageError,
    EmptyImageError,
    ImageSizeExceededError,
    UnsupportedImageFormatError,
)

logger = logging.getLogger(__name__)

# Standard magic bytes signatures
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def detect_magic_format(data: bytes) -> Optional[str]:
    """
    Detect format based purely on file header magic bytes without trusting extensions.
    Returns 'JPEG', 'PNG', or None.
    """
    if len(data) >= 3 and data.startswith(JPEG_MAGIC):
        return "JPEG"
    if len(data) >= 8 and data.startswith(PNG_MAGIC):
        return "PNG"
    return None


def validate_image_file(
    file_bytes: bytes,
    filename: Optional[str] = None,
    max_size_bytes: int = settings.MAX_UPLOAD_SIZE_BYTES,
) -> Tuple[str, np.ndarray]:
    """
    Validates uploaded image bytes thoroughly:
    1. Rejects empty files.
    2. Rejects files exceeding the configurable size limit.
    3. Rejects unsupported formats by verifying magic bytes and PIL format (never trusting extension alone).
    4. Rejects corrupted files that fail PIL verification or OpenCV image decoding.

    Returns:
        Tuple of (detected_format: str, decoded_image: np.ndarray).
    """
    if not file_bytes or len(file_bytes) == 0:
        logger.warning(f"Rejected empty image upload. Filename: {filename}")
        raise EmptyImageError("Uploaded image file is empty.")

    if len(file_bytes) > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        actual_mb = len(file_bytes) / (1024 * 1024)
        logger.warning(
            f"Rejected oversized image upload: {actual_mb:.2f} MB exceeds limit of {max_mb:.0f} MB."
        )
        raise ImageSizeExceededError(
            f"Image file size ({actual_mb:.2f} MB) exceeds the maximum allowed limit of {max_mb:.0f} MB."
        )

    # Magic bytes check
    magic_fmt = detect_magic_format(file_bytes)
    if not magic_fmt:
        logger.warning(f"Rejected upload with invalid or unsupported magic bytes: {filename}")
        raise UnsupportedImageFormatError(
            "Unsupported image format. StockLens only accepts JPG, JPEG, and PNG images."
        )

    # PIL verification (verifies structural integrity and image header)
    try:
        with Image.open(io.BytesIO(file_bytes)) as pil_img:
            pil_img.verify()
            detected_format = pil_img.format
    except Exception as e:
        logger.warning(f"PIL verification failed for upload '{filename}': {e}")
        raise CorruptedImageError("Corrupted or invalid image file. Header verification failed.")

    if detected_format not in settings.ALLOWED_IMAGE_FORMATS:
        logger.warning(f"Rejected unsupported format '{detected_format}' for upload '{filename}'")
        raise UnsupportedImageFormatError(
            f"Unsupported image format: '{detected_format}'. StockLens only accepts JPG, JPEG, and PNG images."
        )

    # OpenCV decoding check to verify raster image integrity
    try:
        np_arr = np.frombuffer(file_bytes, np.uint8)
        decoded = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if decoded is None or decoded.size == 0 or decoded.shape[0] == 0 or decoded.shape[1] == 0:
            raise ValueError("Decoded image matrix is empty or invalid.")
    except Exception as e:
        logger.warning(f"OpenCV decoding failed for upload '{filename}': {e}")
        raise CorruptedImageError("Corrupted or unreadable image file. Unable to decode image raster.")

    logger.info(
        f"Image validated successfully: format={detected_format}, "
        f"dimensions={decoded.shape[1]}x{decoded.shape[0]}, channels={decoded.shape[2]}"
    )
    return detected_format, decoded


@contextmanager
def safe_temp_image_file(
    content: bytes,
    suffix: str = ".tmp",
    prefix: str = "stocklens_invoice_",
) -> Generator[Path, None, None]:
    """
    Safely writes raw image bytes to an isolated temporary file on disk,
    yields the Path object to the caller, and guarantees cleanup upon exit
    regardless of exceptions.
    """
    fd, tmp_name = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
            f.flush()
        yield tmp_path
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
                logger.debug(f"Cleaned up temporary file: {tmp_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {tmp_path}: {e}")
