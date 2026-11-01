"""
Reusable OpenCV image preprocessing functions for StockLens invoice OCR.
All functions preserve original image arrays without in-place mutation.
"""

import io
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import cv2
import numpy as np
from PIL import Image

from app.core.exceptions import CorruptedImageError, ImageProcessingError

logger = logging.getLogger(__name__)


def read_image(source: Union[str, Path, bytes, np.ndarray]) -> np.ndarray:
    """
    Reads an image from bytes, a file path (handling non-ASCII/Windows paths),
    or returns an independent copy if an ndarray is provided.

    Guarantees the returned array is a fresh BGR image and keeps source unchanged.
    """
    try:
        if isinstance(source, np.ndarray):
            if source.size == 0 or source.shape[0] == 0 or source.shape[1] == 0:
                raise ValueError("Input numpy array has invalid or zero dimensions.")
            return source.copy()

        if isinstance(source, bytes):
            if len(source) == 0:
                raise ValueError("Input bytes are empty.")
            arr = np.frombuffer(source, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Failed to decode image from bytes.")
            return img

        if isinstance(source, (str, Path)):
            path_str = str(source)
            if not Path(path_str).is_file():
                raise FileNotFoundError(f"Image file does not exist: {path_str}")
            # Use np.fromfile to safely support Unicode/Windows file paths
            data = np.fromfile(path_str, dtype=np.uint8)
            img = cv2.imdecode(data, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError(f"Failed to decode image from path: {path_str}")
            return img

        raise TypeError(f"Unsupported image source type: {type(source).__name__}")
    except Exception as e:
        logger.error(f"Error reading image: {e}")
        raise CorruptedImageError(f"Could not read or decode image: {e}")


def to_grayscale(img: np.ndarray) -> np.ndarray:
    """
    Converts a color BGR or BGRA image to single-channel 8-bit grayscale.
    If the image is already grayscale, returns a fresh copy.
    The original image is never modified.
    """
    if not isinstance(img, np.ndarray):
        raise TypeError("Input must be a numpy ndarray.")

    if img.ndim == 2:
        return img.copy()

    if img.ndim == 3:
        channels = img.shape[2]
        if channels == 1:
            return img[:, :, 0].copy()
        if channels == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if channels == 4:
            return cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)

    raise ValueError(f"Unexpected image dimensions for grayscale conversion: {img.shape}")


def reduce_noise(
    img: np.ndarray,
    method: str = "gaussian",
    kernel_size: int = 3,
) -> np.ndarray:
    """
    Applies noise reduction to an image.
    Supported methods:
      - 'gaussian': Gaussian blur (fast, smooths high-frequency noise)
      - 'median': Median blur (excellent for salt-and-pepper noise)
      - 'bilateral': Bilateral filter (smooths noise while preserving crisp text edges)

    The original image is never modified.
    """
    if not isinstance(img, np.ndarray):
        raise TypeError("Input must be a numpy ndarray.")

    # Kernel size must be positive and odd
    k = max(1, kernel_size)
    if k % 2 == 0:
        k += 1

    method_clean = method.lower().strip()
    if method_clean == "gaussian":
        return cv2.GaussianBlur(img, (k, k), 0)
    elif method_clean == "median":
        return cv2.medianBlur(img, k)
    elif method_clean == "bilateral":
        # Bilateral filter works on 8-bit single-channel or 3-channel
        d = max(5, k * 2)
        return cv2.bilateralFilter(img, d=d, sigmaColor=75, sigmaSpace=75)
    else:
        raise ValueError(f"Unknown noise reduction method: '{method}'. Use 'gaussian', 'median', or 'bilateral'.")


def apply_threshold(
    img: np.ndarray,
    method: str = "otsu",
    block_size: int = 11,
    c: int = 2,
) -> np.ndarray:
    """
    Applies thresholding to binarize the image for optimal OCR recognition.
    Supported methods:
      - 'otsu': Otsu's automatic thresholding (calculates optimum global threshold)
      - 'adaptive': Adaptive Gaussian thresholding (handles uneven lighting across receipts/invoices)
      - 'binary': Simple binary thresholding at midpoint 127

    If input has multiple channels, it will be automatically converted to grayscale
    without mutating the input array.
    """
    if not isinstance(img, np.ndarray):
        raise TypeError("Input must be a numpy ndarray.")

    gray = to_grayscale(img)
    method_clean = method.lower().strip()

    if method_clean == "otsu":
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh
    elif method_clean == "adaptive":
        bs = max(3, block_size)
        if bs % 2 == 0:
            bs += 1
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, bs, c
        )
    elif method_clean == "binary":
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        return thresh
    else:
        raise ValueError(f"Unknown thresholding method: '{method}'. Use 'otsu', 'adaptive', or 'binary'.")


def improve_contrast(
    img: np.ndarray,
    method: str = "clahe",
    clip_limit: float = 2.0,
    tile_grid_size: Tuple[int, int] = (8, 8),
) -> np.ndarray:
    """
    Enhances contrast across the image.
    Supported methods:
      - 'clahe': Contrast Limited Adaptive Histogram Equalization (prevents noise amplification)
      - 'histogram_equalization': Standard global histogram equalization

    Supports both grayscale and BGR color images without mutating the input.
    """
    if not isinstance(img, np.ndarray):
        raise TypeError("Input must be a numpy ndarray.")

    method_clean = method.lower().strip()

    if img.ndim == 2 or (img.ndim == 3 and img.shape[2] == 1):
        gray = img[:, :, 0] if img.ndim == 3 else img
        if method_clean == "clahe":
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
            return clahe.apply(gray)
        elif method_clean in ("histogram_equalization", "hist_eq"):
            return cv2.equalizeHist(gray)
        else:
            raise ValueError(f"Unknown contrast enhancement method: '{method}'.")

    # For 3-channel color images
    if img.ndim == 3 and img.shape[2] == 3:
        if method_clean == "clahe":
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
            cl = clahe.apply(l)
            merged = cv2.merge((cl, a, b))
            return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        elif method_clean in ("histogram_equalization", "hist_eq"):
            yuv = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)
            yuv[:, :, 0] = cv2.equalizeHist(yuv[:, :, 0])
            return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
        else:
            raise ValueError(f"Unknown contrast enhancement method: '{method}'.")

    raise ValueError(f"Unsupported image shape for contrast improvement: {img.shape}")


def correct_rotation(
    img: np.ndarray,
    max_angle: float = 45.0,
) -> Tuple[np.ndarray, float]:
    """
    Detects skew angle in text lines and deskews the image when practical.
    Uses minimum bounding area rectangle of thresholded text components.

    Returns:
        Tuple of (deskewed_image: np.ndarray, corrected_angle_degrees: float).
        If angle is negligible (< 0.2 deg) or exceeds max_angle, returns (copy, 0.0).
    """
    if not isinstance(img, np.ndarray):
        raise TypeError("Input must be a numpy ndarray.")

    try:
        gray = to_grayscale(img)
        # Invert Otsu threshold so text/ink pixels are foreground (white = 255)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Find coordinates of all text/ink pixels
        pts = np.column_stack(np.where(thresh > 0))
        if len(pts) < 100:
            # Insufficient text content to determine rotation reliably
            return img.copy(), 0.0

        # Compute minimum area bounding box
        rect = cv2.minAreaRect(pts)
        angle = rect[-1]

        # Determine skew angle based on OpenCV angle conventions
        # minAreaRect returns angle in [-90, 0)
        if angle < -45:
            skew_angle = -(90 + angle)
        elif angle > 45:
            skew_angle = -(angle - 90)
        else:
            skew_angle = -angle

        # If angle is beyond realistic invoice tilt or negligible, do not rotate
        if abs(skew_angle) > max_angle or abs(skew_angle) < 0.2:
            return img.copy(), 0.0

        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
        rotated = cv2.warpAffine(
            img,
            rotation_matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return rotated, float(skew_angle)
    except Exception as e:
        logger.warning(f"Rotation correction skipped due to error: {e}")
        return img.copy(), 0.0


def preprocess_invoice_image(
    source: Union[str, Path, bytes, np.ndarray],
) -> Dict[str, Any]:
    """
    Full OpenCV preprocessing pipeline preparing an invoice image for OCR:
    1. Read and validate raw image.
    2. Correct skew and rotation.
    3. Convert to grayscale.
    4. Enhance contrast using CLAHE.
    5. Reduce noise using Gaussian filter.
    6. Apply Otsu binarization.

    Returns:
        Dictionary with:
          - 'processed_image': final binary image ready for OCR
          - 'grayscale_image': contrast-enhanced grayscale image
          - 'deskewed_image': rotated image
          - 'rotation_angle': detected and applied rotation angle
          - 'original_shape': dimensions of original image (H, W, C)
    """
    try:
        # Step 1: Read image
        original = read_image(source)
        original_shape = original.shape

        # Step 2: Correct rotation
        deskewed, angle = correct_rotation(original)

        # Step 3: Convert to grayscale
        gray = to_grayscale(deskewed)

        # Step 4: Enhance contrast
        enhanced_gray = improve_contrast(gray, method="clahe")

        # Step 5: Reduce noise
        denoised = reduce_noise(enhanced_gray, method="gaussian", kernel_size=3)

        # Step 6: Binarization / Thresholding
        binary = apply_threshold(denoised, method="otsu")

        return {
            "processed_image": binary,
            "grayscale_image": enhanced_gray,
            "deskewed_image": deskewed,
            "rotation_angle": angle,
            "original_shape": original_shape,
        }
    except Exception as e:
        logger.error(f"Invoice image preprocessing failed: {e}")
        raise ImageProcessingError(f"Invoice preprocessing failed: {e}")


def validate_and_load_image(image_bytes: bytes) -> Optional[Image.Image]:
    """
    Legacy helper preserved for backward compatibility.
    Validates input bytes and returns a PIL Image object if valid.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.verify()
        return Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        logger.error(f"Image validation failed: {e}")
        return None
