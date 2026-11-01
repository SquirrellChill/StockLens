"""
Domain and application exceptions for StockLens.
"""

class StockLensException(Exception):
    """Base exception for all StockLens domain errors."""
    def __init__(self, message: str = "An unexpected error occurred."):
        super().__init__(message)
        self.message = message


class EmptyImageError(StockLensException):
    """Raised when an uploaded image file is empty (0 bytes)."""
    def __init__(self, message: str = "Uploaded image file is empty."):
        super().__init__(message)


class UnsupportedImageFormatError(StockLensException):
    """Raised when an uploaded file is not an allowed image format (JPG, JPEG, PNG)."""
    def __init__(self, message: str = "Unsupported image format. StockLens only accepts JPG, JPEG, and PNG images."):
        super().__init__(message)


class ImageSizeExceededError(StockLensException):
    """Raised when an uploaded image file exceeds the configured size limit."""
    def __init__(self, message: str = "Uploaded image exceeds the allowed file size limit."):
        super().__init__(message)


class CorruptedImageError(StockLensException):
    """Raised when an uploaded file is corrupted or cannot be decoded as an image."""
    def __init__(self, message: str = "Corrupted or invalid image file. Unable to decode image data."):
        super().__init__(message)


class OCRDependencyUnavailableError(StockLensException):
    """Raised when Tesseract OCR is not installed or configured on the server."""
    def __init__(self, message: str = "OCR service unavailable: Tesseract is not installed or configured on the server."):
        super().__init__(message)


class ImageProcessingError(StockLensException):
    """Raised when OpenCV processing encounters an internal failure."""
    def __init__(self, message: str = "Internal image processing failure during invoice preprocessing."):
        super().__init__(message)


class DuplicateInvoiceError(StockLensException):
    """Raised when attempting to confirm an invoice that has already been confirmed for this supplier."""
    def __init__(self, message: str = "This invoice has already been confirmed."):
        super().__init__(message)
