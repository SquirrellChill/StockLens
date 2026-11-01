"""
Unit tests for image validation and safe temporary file handling.
Verifies format checks, size limits, rejection of empty/corrupted/disguised files,
and automatic cleanup of temporary files.
"""

import io
import pytest
from PIL import Image

from app.core.exceptions import (
    CorruptedImageError,
    EmptyImageError,
    ImageSizeExceededError,
    UnsupportedImageFormatError,
)
from app.utils.image_validation import (
    detect_magic_format,
    safe_temp_image_file,
    validate_image_file,
)


def make_image_bytes(fmt: str = "JPEG", size: tuple = (100, 100)) -> bytes:
    img = Image.new("RGB", size, color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_detect_magic_format():
    jpeg_bytes = make_image_bytes("JPEG")
    png_bytes = make_image_bytes("PNG")
    gif_bytes = make_image_bytes("GIF")
    text_bytes = b"Hello, world!"

    assert detect_magic_format(jpeg_bytes) == "JPEG"
    assert detect_magic_format(png_bytes) == "PNG"
    assert detect_magic_format(gif_bytes) is None
    assert detect_magic_format(text_bytes) is None


def test_validate_valid_jpeg():
    jpeg_bytes = make_image_bytes("JPEG")
    fmt, decoded = validate_image_file(jpeg_bytes, filename="invoice.jpg")
    assert fmt == "JPEG"
    assert decoded.shape == (100, 100, 3)


def test_validate_valid_png():
    png_bytes = make_image_bytes("PNG")
    fmt, decoded = validate_image_file(png_bytes, filename="invoice.png")
    assert fmt == "PNG"
    assert decoded.shape == (100, 100, 3)


def test_validate_empty_file():
    with pytest.raises(EmptyImageError) as exc_info:
        validate_image_file(b"", filename="empty.jpg")
    assert "empty" in str(exc_info.value).lower()


def test_validate_size_limit_exceeded():
    jpeg_bytes = make_image_bytes("JPEG")
    with pytest.raises(ImageSizeExceededError):
        # Set artificial small limit of 50 bytes
        validate_image_file(jpeg_bytes, filename="large.jpg", max_size_bytes=50)


def test_validate_disguised_file_rejected():
    # Text file with .jpg extension
    fake_jpg = b"This is just a plain text document pretending to be an invoice image."
    with pytest.raises(UnsupportedImageFormatError):
        validate_image_file(fake_jpg, filename="invoice.jpg")


def test_validate_unsupported_format_gif():
    gif_bytes = make_image_bytes("GIF")
    with pytest.raises(UnsupportedImageFormatError):
        validate_image_file(gif_bytes, filename="invoice.gif")


def test_validate_corrupted_image():
    # Valid JPEG header followed by corrupt junk
    corrupt_bytes = b"\xff\xd8\xff\xe0" + b"random_corrupt_data" * 20
    with pytest.raises(CorruptedImageError):
        validate_image_file(corrupt_bytes, filename="corrupt.jpg")


def test_safe_temp_image_file_cleanup():
    content = b"test temporary file content"
    temp_path = None
    with safe_temp_image_file(content, suffix=".jpg") as path:
        temp_path = path
        assert temp_path.exists()
        assert temp_path.read_bytes() == content

    # File must be cleaned up automatically after exiting block
    assert not temp_path.exists()


def test_safe_temp_image_file_cleanup_on_exception():
    content = b"test error cleanup"
    temp_path = None
    try:
        with safe_temp_image_file(content, suffix=".jpg") as path:
            temp_path = path
            assert temp_path.exists()
            raise RuntimeError("Simulated processing error")
    except RuntimeError:
        pass

    # File must be removed even when exception was thrown
    assert temp_path is not None
    assert not temp_path.exists()
