"""OpenCV preprocessing: load, upscale, deskew, binarize."""
import cv2
import numpy as np

TARGET_WIDTH = 1600


def load_image(data: bytes) -> np.ndarray:
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Cannot decode image")
    return img


def upscale(img: np.ndarray, target: int = TARGET_WIDTH) -> np.ndarray:
    h, w = img.shape[:2]
    if w >= target:
        return img
    s = target / w
    return cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)


def to_gray(img: np.ndarray) -> np.ndarray:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    # flatten uneven lighting / shadows from phone photos
    bg = cv2.medianBlur(cv2.dilate(g, np.ones((25, 25), np.uint8)), 51)
    norm = cv2.divide(g, bg, scale=255)
    return norm


def deskew(gray: np.ndarray, max_angle: float = 10.0) -> tuple[np.ndarray, float]:
    """Rotate so ruled lines / text rows are horizontal. Small angles only."""
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    lines = cv2.HoughLinesP(bw, 1, np.pi / 360, threshold=200,
                            minLineLength=gray.shape[1] // 4, maxLineGap=10)
    angles = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2= lines[ 0]
            a = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if abs(a) < max_angle:
                angles.append(a)
    if len(angles) < 3:
        return gray, 0.0
    angle = float(np.median(angles))
    if abs(angle) < 0.15:
        return gray, 0.0
    h, w = gray.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    out = cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC,
                         borderMode=cv2.BORDER_REPLICATE)
    return out, angle


def binarize(gray: np.ndarray) -> np.ndarray:
    """Black ink on white background."""
    return cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]


def prepare(data: bytes) -> np.ndarray:
    """Returns a normalized, deskewed grayscale image."""
    gray = to_gray(upscale(load_image(data)))
    gray, _ = deskew(gray)
    return gray
