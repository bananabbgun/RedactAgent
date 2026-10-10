"""Visual layer: identifiers that are not text.

* A vision-language model (Qwen2.5-VL) localises handwritten signatures, portrait
  photos and ink seals (印章) with bounding boxes ("grounding").
* A colour-segmentation pass finds red seal impressions, which are common on
  Taiwanese documents and cheap to detect deterministically. It also cross-checks
  the VLM: a box confirmed by both gets higher confidence.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

from ..llm_client import CallStats, ModelClient

LABEL_TO_CAT = {"signature": "SIGNATURE", "face_photo": "FACE_PHOTO", "seal_stamp": "SEAL_STAMP"}

SYSTEM = "You are a document layout analyst. You localise visual elements on scanned documents precisely."
PROMPT = """Detect all of the following on this scanned document page and output their bounding boxes:
- signature: each handwritten cursive signature (there may be several, e.g. one per party). Not printed names.
- face_photo: a photograph or portrait of a person.
- seal_stamp: an ink seal, chop or rubber stamp impression.
Output JSON {"objects": [{"label": ..., "bbox_2d": [x1, y1, x2, y2]}]}. Output an empty list if none are present."""

SCHEMA = {
    "type": "object",
    "properties": {
        "objects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "enum": list(LABEL_TO_CAT)},
                    "bbox_2d": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4},
                },
                "required": ["label", "bbox_2d"],
            },
        }
    },
    "required": ["objects"],
}


@dataclass
class VisionHit:
    category: str
    bbox: list[int]
    confidence: float
    reason: str
    source: str  # "vlm" | "cv"


def _resize_for_vlm(img: Image.Image, max_side: int = 1260) -> tuple[Image.Image, float]:
    """Qwen2.5-VL works on 28-px patches; feed an exact multiple so returned coordinates map back 1:1.
    Below ~1.1 MP the Ollama runtime rescales the image internally and the boxes drift, so stay at 1260 px."""
    w, h = img.size
    s = min(1.0, max_side / max(w, h))
    nw, nh = max(28, round(w * s / 28) * 28), max(28, round(h * s / 28) * 28)
    return img.resize((nw, nh), Image.LANCZOS), w / nw


def vlm_detect(img: Image.Image, client: ModelClient) -> tuple[list[VisionHit], CallStats]:
    small, scale = _resize_for_vlm(img)
    out, stats = client.chat_json(SYSTEM, PROMPT, SCHEMA, images=[small], max_tokens=512, num_ctx=4096)
    W, H = img.size
    hits = []
    for o in out.get("objects", []):
        cat = LABEL_TO_CAT.get(o.get("label"))
        bb = o.get("bbox_2d") or []
        if not cat or len(bb) != 4:
            continue
        x0, y0, x1, y1 = [v * scale for v in bb]
        x0, x1 = sorted((max(0, x0), min(W, x1)))
        y0, y1 = sorted((max(0, y0), min(H, y1)))
        if (x1 - x0) < 12 or (y1 - y0) < 12 or (x1 - x0) * (y1 - y0) > 0.25 * W * H:
            continue
        pad = 6
        hits.append(VisionHit(cat, [int(x0) - pad, int(y0) - pad, int(x1) + pad, int(y1) + pad], 0.8,
                              f"VLM grounding: {o['label'].replace('_', ' ')}", "vlm"))
    return hits, stats


def seal_detect(img: Image.Image) -> list[VisionHit]:
    """Red-ink connected components that look like a seal impression."""
    arr = np.asarray(img.convert("RGB")).astype(np.int16)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    mask = ((r > 140) & (r - g > 70) & (r - b > 60)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    hits = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if w < 50 or h < 50 or w > 450 or h > 450:
            continue
        if not 0.5 < w / h < 2.0 or area < 0.04 * w * h:
            continue
        hits.append(VisionHit("SEAL_STAMP", [int(x) - 4, int(y) - 4, int(x + w) + 4, int(y + h) + 4], 0.85,
                              "red ink seal impression (colour segmentation)", "cv"))
    return hits


def iou(a, b) -> float:
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def detect(img: Image.Image, client: ModelClient | None) -> tuple[list[VisionHit], CallStats]:
    cv_hits = seal_detect(img)
    if client is None:
        return cv_hits, CallStats(0.0)
    vlm_hits, stats = vlm_detect(img, client)
    merged: list[VisionHit] = []
    for h in vlm_hits:
        twin = next((c for c in cv_hits if c.category == h.category and iou(c.bbox, h.bbox) > 0.3), None)
        if twin is not None:
            # trust the pixel-accurate colour box, mark as confirmed by both
            merged.append(VisionHit(h.category, twin.bbox, 0.95, h.reason + " + colour check", "vlm+cv"))
            cv_hits.remove(twin)
        else:
            merged.append(h)
    merged.extend(cv_hits)
    return merged, stats
