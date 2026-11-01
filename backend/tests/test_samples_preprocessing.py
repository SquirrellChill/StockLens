"""
Test preprocessing on sample invoice images.
Verifies that real JPG and PNG sample invoices process successfully.
"""

from pathlib import Path
from app.utils.image_processing import preprocess_invoice_image, read_image, correct_rotation
from app.utils.image_validation import validate_image_file


def test_sample_invoices_preprocessing():
    samples_dir = Path("sample_invoices")
    assert samples_dir.exists(), "sample_invoices directory must exist"

    sample_files = list(samples_dir.glob("*.*"))
    assert len(sample_files) >= 3, "Expected at least 3 sample invoices"

    for sample_path in sample_files:
        content = sample_path.read_bytes()

        # Validate file
        fmt, cv2_img = validate_image_file(content, filename=sample_path.name)
        assert fmt in ("JPEG", "PNG")
        assert cv2_img is not None
        assert cv2_img.shape[0] > 0 and cv2_img.shape[1] > 0

        # Preprocess invoice image
        result = preprocess_invoice_image(cv2_img)
        assert "processed_image" in result
        assert "grayscale_image" in result
        assert "deskewed_image" in result
        assert "rotation_angle" in result

        processed = result["processed_image"]
        assert processed.ndim == 2  # Grayscale / binarized
        assert processed.shape[0] == cv2_img.shape[0]
        assert processed.shape[1] == cv2_img.shape[1]


def test_skewed_sample_rotation_correction():
    skewed_path = Path("sample_invoices/sample_invoice_skewed.jpg")
    content = skewed_path.read_bytes()
    fmt, cv2_img = validate_image_file(content, filename="sample_invoice_skewed.jpg")

    deskewed, angle = correct_rotation(cv2_img)
    assert abs(angle) > 0.0, "Expected non-zero rotation angle detected for skewed sample"
