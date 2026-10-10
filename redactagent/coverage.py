"""Safety net: find text-like ink that OCR did not read.

If the OCR detector drops a line, nothing downstream can redact it. This pass looks
for dark, line-shaped ink blobs that no OCR line (or visual finding) covers and
returns them as review warnings, so a human checks the region instead of the page
silently passing.
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def unread_regions(img: Image.Image, covered: list[list[int]], pad: int = 6) -> list[list[int]]:
    gray = np.asarray(img.convert("L"))
    ink = (gray < 110).astype(np.uint8)
    # join characters of a line, but not neighbouring lines
    ink = cv2.dilate(ink, np.ones((3, 15), np.uint8))
    mask = np.zeros_like(ink)
    for x0, y0, x1, y1 in covered:
        mask[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad] = 1
    ink[mask == 1] = 0
    n, _, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    out = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        # text-line shaped: reasonably wide, glyph-height, not a ruling line or table border
        if w >= 60 and 12 <= h <= 60 and w / h <= 50 and area >= 0.25 * w * h:
            out.append([int(x), int(y), int(x + w), int(y + h)])
    return out
