"""
Unit tests for OpenCV image preprocessing functions.
Verifies reading, grayscale conversion, noise reduction, thresholding,
contrast improvement, rotation correction, and pipeline orchestration.
Ensures original images are never mutated.
"""

import io
import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw

from app.core.exceptions import CorruptedImageError
from app.utils.image_processing import (
    apply_threshold,
    correct_rotation,
    improve_contrast,
    preprocess_invoice_image,
    read_image,
    reduce_noise,
    to_grayscale,
)


def create_test_image(
    width: int = 300,
    height: int = 200,
    color: tuple = (255, 255, 255),
    text: str = "Invoice INV-1001",
) -> np.ndarray:
    """Creates a synthetic BGR invoice image with text."""
    pil_img = Image.new("RGB", (width, height), color=color)
    draw = ImageDraw.Draw(pil_img)
    draw.text((20, 20), text, fill=(0, 0, 0))
    draw.text((20, 60), "Item A 5 10.00", fill=(0, 0, 0))
    draw.text((20, 100), "Item B 2 25.50", fill=(0, 0, 0))
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def test_read_image_from_numpy():
    img = create_test_image()
    copy_img = read_image(img)
    assert np.array_equal(img, copy_img)
    assert img is not copy_img  # Ensures separate copy

    # Verify mutating copy does not mutate original
    copy_img[0, 0] = [0, 0, 0]
    assert not np.array_equal(img, copy_img)


def test_read_image_from_bytes():
    pil_img = Image.new("RGB", (100, 100), color=(200, 200, 200))
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    img = read_image(img_bytes)
    assert isinstance(img, np.ndarray)
    assert img.shape == (100, 100, 3)


def test_read_image_from_file(tmp_path):
    img_path = tmp_path / "test_invoice.png"
    cv2.imwrite(str(img_path), create_test_image())

    loaded = read_image(img_path)
    assert isinstance(loaded, np.ndarray)
    assert loaded.shape[0] > 0 and loaded.shape[1] > 0


def test_read_image_invalid():
    with pytest.raises(CorruptedImageError):
        read_image(b"invalid image data")

    with pytest.raises(CorruptedImageError):
        read_image(b"")

    with pytest.raises(CorruptedImageError):
        read_image(np.array([]))


def test_to_grayscale():
    img = create_test_image()
    original_copy = img.copy()

    gray = to_grayscale(img)
    assert gray.ndim == 2
    assert gray.shape == (img.shape[0], img.shape[1])
    # Original is unchanged
    assert np.array_equal(img, original_copy)

    # Calling on already grayscale returns a fresh copy
    gray2 = to_grayscale(gray)
    assert np.array_equal(gray, gray2)
    assert gray is not gray2


def test_to_grayscale_bgra():
    bgra = np.zeros((50, 50, 4), dtype=np.uint8)
    bgra[:, :] = [100, 150, 200, 255]
    gray = to_grayscale(bgra)
    assert gray.ndim == 2
    assert gray.shape == (50, 50)


def test_reduce_noise_gaussian():
    img = create_test_image()
    orig = img.copy()
    denoised = reduce_noise(img, method="gaussian", kernel_size=3)

    assert denoised.shape == img.shape
    assert np.array_equal(img, orig)


def test_reduce_noise_median():
    img = create_test_image()
    orig = img.copy()
    denoised = reduce_noise(img, method="median", kernel_size=3)

    assert denoised.shape == img.shape
    assert np.array_equal(img, orig)


def test_reduce_noise_bilateral():
    img = create_test_image()
    orig = img.copy()
    denoised = reduce_noise(img, method="bilateral", kernel_size=3)

    assert denoised.shape == img.shape
    assert np.array_equal(img, orig)


def test_apply_threshold_otsu():
    img = create_test_image()
    orig = img.copy()
    thresh = apply_threshold(img, method="otsu")

    assert thresh.ndim == 2
    unique_vals = set(np.unique(thresh))
    # Threshold produces binary image (values in {0, 255})
    assert unique_vals.issubset({0, 255})
    assert np.array_equal(img, orig)


def test_apply_threshold_adaptive():
    img = create_test_image()
    orig = img.copy()
    thresh = apply_threshold(img, method="adaptive", block_size=11, c=2)

    assert thresh.ndim == 2
    unique_vals = set(np.unique(thresh))
    assert unique_vals.issubset({0, 255})
    assert np.array_equal(img, orig)


def test_improve_contrast_clahe_gray():
    gray = to_grayscale(create_test_image())
    orig = gray.copy()
    enhanced = improve_contrast(gray, method="clahe")

    assert enhanced.shape == gray.shape
    assert np.array_equal(gray, orig)


def test_improve_contrast_clahe_color():
    color = create_test_image()
    orig = color.copy()
    enhanced = improve_contrast(color, method="clahe")

    assert enhanced.shape == color.shape
    assert np.array_equal(color, orig)


def test_improve_contrast_hist_eq():
    gray = to_grayscale(create_test_image())
    orig = gray.copy()
    enhanced = improve_contrast(gray, method="histogram_equalization")

    assert enhanced.shape == gray.shape
    assert np.array_equal(gray, orig)


def test_correct_rotation():
    # Create an image with prominent horizontal lines and rotate it by 5 degrees
    img = np.ones((400, 400, 3), dtype=np.uint8) * 255
    cv2.putText(img, "INVOICE # 12345", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    cv2.putText(img, "Supplier Acme Inc", (50, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    cv2.putText(img, "Product A 10 50.00", (50, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)

    # Intentionally rotate by 5 degrees
    center = (200, 200)
    matrix = cv2.getRotationMatrix2D(center, 5.0, 1.0)
    skewed = cv2.warpAffine(img, matrix, (400, 400), borderValue=(255, 255, 255))
    orig = skewed.copy()

    deskewed, detected_angle = correct_rotation(skewed)
    assert deskewed.shape == skewed.shape
    # Ensure original array was not modified
    assert np.array_equal(skewed, orig)
    # The detected angle should be close to -5 degrees to compensate
    assert abs(detected_angle) > 0.0


def test_preprocess_invoice_image_pipeline():
    img = create_test_image()
    result = preprocess_invoice_image(img)

    assert "processed_image" in result
    assert "grayscale_image" in result
    assert "deskewed_image" in result
    assert "rotation_angle" in result
    assert "original_shape" in result

    assert result["processed_image"].ndim == 2
    assert result["original_shape"] == img.shape
