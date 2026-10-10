"""OCR layer: RapidOCR (PP-OCR models on ONNX Runtime / OpenVINO) with per-character boxes."""

from __future__ import annotations

import threading

import numpy as np

from .schema import OcrLine

_engine = None
_lock = threading.Lock()


def _get_engine():
    global _engine
    with _lock:
        if _engine is None:
            from rapidocr_onnxruntime import RapidOCR

            _engine = RapidOCR()
    return _engine


def _quad_to_box(q) -> list[int]:
    xs = [p[0] for p in q]
    ys = [p[1] for p in q]
    return [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]


def run_ocr(img: np.ndarray, page: int = 0) -> list[OcrLine]:
    """Return text lines in reading order, each with one box per character."""
    # NB: RapidOCR resets box_thresh / unclip_ratio / text_score to defaults whenever call-time kwargs are given,
    # so they must be passed here. A wider unclip recovers thin lines the default drops and keeps word spacing.
    res, _ = _get_engine()(img, return_word_box=True, box_thresh=0.3, unclip_ratio=2.0, text_score=0.5)
    lines: list[OcrLine] = []
    for quad, text, score, char_quads, *_ in res or []:
        box = _quad_to_box(quad)
        chars = [_quad_to_box(q) for q in char_quads]
        if len(chars) != len(text):  # defensive: fall back to uniform split
            x0, y0, x1, y1 = box
            step = (x1 - x0) / max(1, len(text))
            chars = [[int(x0 + i * step), y0, int(x0 + (i + 1) * step), y1] for i in range(len(text))]
        lines.append(OcrLine(id="", text=text, bbox=box, char_boxes=chars, score=float(score)))
    # reading order: group into rows by vertical centre, then left-to-right
    lines.sort(key=lambda l: ((l.bbox[1] + l.bbox[3]) / 2 // 18, l.bbox[0]))
    for i, ln in enumerate(lines, 1):
        ln.id = f"P{page + 1}L{i}"
    return lines
