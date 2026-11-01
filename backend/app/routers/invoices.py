import logging
from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import (
    CorruptedImageError,
    EmptyImageError,
    ImageProcessingError,
    ImageSizeExceededError,
    OCRDependencyUnavailableError,
    UnsupportedImageFormatError,
)
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceExtractResponse,
    InvoiceResponse,
)
from app.services.invoice_service import invoice_service
from app.services.ocr_service import ocr_service
from app.utils.image_validation import safe_temp_image_file

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/extract",
    response_model=InvoiceExtractResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract invoice data from uploaded image",
    description=(
        "Accepts a supplier invoice image (JPG, JPEG, PNG) via multipart/form-data, "
        "validates file integrity and size, preprocesses with OpenCV, and prepares/executes OCR "
        "with Tesseract to return candidate supplier, invoice number, and line items."
    ),
)
async def extract_invoice(
    file: UploadFile = File(..., description="Invoice image file (JPG, JPEG, or PNG)"),
):
    """
    Invoice upload and OCR extraction endpoint:
    - Validates image format (JPG, JPEG, PNG) via magic bytes and PIL verification.
    - Rejects empty, corrupted, or oversized files.
    - Runs OpenCV preprocessing (rotation correction, grayscale, contrast enhancement, denoising, thresholding).
    - Checks Tesseract availability and performs text extraction.
    """
    logger.info(f"Received invoice upload: filename='{file.filename}', content_type='{file.content_type}'")

    # Read uploaded bytes with size enforcement
    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file '{file.filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read the uploaded file.",
        )

    # Validate non-empty file
    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty. Please choose a valid invoice image.",
        )

    # Check size limit before processing
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"That image is larger than {max_mb} MB. Please choose a smaller one.",
        )

    # Use safe temporary file handling if needed for disk inspection and cleanup
    try:
        with safe_temp_image_file(content, suffix=f"_{file.filename or 'upload.tmp'}") as temp_path:
            # Execute validation and extraction pipeline
            result = ocr_service.extract_from_image(content, filename=file.filename)
            return InvoiceExtractResponse(
                supplier=result.get("supplier", ""),
                invoice_number=result.get("invoice_number", ""),
                date=result.get("date", ""),
                items=result.get("items", []),
                raw_text=result.get("raw_text", ""),
                confidence=result.get("confidence"),
                requires_review=result.get("requires_review", True),
                parsing_notes=result.get("parsing_notes", []),
            )
    except EmptyImageError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except UnsupportedImageFormatError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except ImageSizeExceededError as e:
        raise HTTPException(
            status_code=413,
            detail=e.message,
        )
    except CorruptedImageError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupted or invalid image file. Please provide a clear, readable JPG or PNG image.",
        )
    except OCRDependencyUnavailableError as e:
        logger.warning(f"OCR dependency unavailable: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.message,
        )
    except ImageProcessingError as e:
        logger.error(f"Image preprocessing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal processing failure while preparing invoice image for OCR.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during invoice extraction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during invoice processing.",
        )


@router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirm invoice and sync stock",
    description="Save confirmed supplier invoice and increment inventory product quantities.",
)
def create_invoice(
    invoice_in: InvoiceCreate,
    db: Session = Depends(get_db),
):
    if not invoice_in.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add at least one item before confirming.",
        )
    for item in invoice_in.items:
        if item.quantity <= 0 or item.unit_price < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Every item needs a quantity above 0 and a valid price.",
            )
    try:
        return invoice_service.create(db=db, invoice_in=invoice_in)
    except Exception as e:
        logger.error(f"Failed to confirm invoice: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to confirm invoice.",
        )


@router.get(
    "",
    response_model=List[InvoiceResponse],
    summary="List invoices",
    description="Retrieve confirmed supplier invoices.",
)
def get_invoices(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return invoice_service.get_all(db=db, skip=skip, limit=limit)
