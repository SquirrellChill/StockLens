"""Detect a ruled table and split it into cells."""
import cv2
import numpy as np


def _clusters(idx: np.ndarray, gap: int = 4) -> list[int]:
    if len(idx) == 0:
        return []
    groups, start, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - prev > gap:
            groups.append((start + prev) // 2)
            start = i
        prev = i
    groups.append((start + prev) // 2)
    return groups


def find_table(gray: np.ndarray):
    """Returns (xs, ys) grid line coordinates, or None if no table found."""
    h, w = gray.shape
    inv = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                cv2.THRESH_BINARY_INV, 31, 15)
    hor = cv2.morphologyEx(inv, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (w // 12, 1)))
    ver = cv2.morphologyEx(inv, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, h // 40)))
    grid = cv2.dilate(cv2.bitwise_or(hor, ver), np.ones((5, 5), np.uint8))

    n, _, stats, _ = cv2.connectedComponentsWithStats(grid)
    best, best_area = None, 0
    for i in range(1, n):
        x, y, cw, ch, _a = stats[i]
        if cw > w * 0.4 and ch > h * 0.08 and cw * ch > best_area:
            best, best_area = (x, y, cw, ch), cw * ch
    if best is None:
        return None
    x, y, cw, ch = best
    hr, vr = hor[y:y + ch, x:x + cw], ver[y:y + ch, x:x + cw]
    ys = [y + v for v in _clusters(np.where(hr.sum(axis=1) / 255 > 0.5 * cw)[0])]
    xs = [x + v for v in _clusters(np.where(vr.sum(axis=0) / 255 > 0.35 * ch)[0])]
    if len(ys) < 3 or len(xs) < 3:
        return None
    return xs, ys


def cells(gray: np.ndarray, xs: list[int], ys: list[int], margin: int = 8):
    """Yield (row_idx, col_idx, crop) for every cell, trimmed to avoid grid lines."""
    for r in range(len(ys) - 1):
        for c in range(len(xs) - 1):
            crop = gray[ys[r] + margin: ys[r + 1] - margin, xs[c] + margin: xs[c + 1] - margin]
            yield r, c, crop


def ink_ratio(crop: np.ndarray) -> float:
    if crop.size == 0:
        return 0.0
    bw = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    # ignore near-uniform crops (Otsu would split pure noise)
    if crop.std() < 12:
        return 0.0
    return float((bw > 0).mean())
