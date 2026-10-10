"""Shared data structures: PII taxonomy, OCR lines and findings."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

# Category id -> (display name, UI colour)
CATEGORIES: dict[str, tuple[str, str]] = {
    "PERSON_NAME": ("Person name", "#e4572e"),
    "GOV_ID": ("Government ID / passport", "#a23b72"),
    "DATE_OF_BIRTH": ("Date of birth", "#f18f01"),
    "DATE": ("Date (event)", "#c99700"),
    "PHONE": ("Phone number", "#2e86ab"),
    "EMAIL": ("E-mail", "#3c91e6"),
    "ADDRESS": ("Address", "#6a4c93"),
    "MEDICAL_RECORD_NO": ("Medical record no.", "#d7263d"),
    "HEALTH_INSURANCE_NO": ("Health insurance no.", "#b5179e"),
    "FINANCIAL_ACCOUNT": ("Bank / card / policy no.", "#1b998b"),
    "LICENSE_PLATE": ("Licence plate", "#5f0f40"),
    "QUASI_IDENTIFIER": ("Quasi-identifier", "#ff006e"),
    "SIGNATURE": ("Signature", "#0f4c5c"),
    "FACE_PHOTO": ("Face photo", "#9a031e"),
    "SEAL_STAMP": ("Seal / chop", "#c1121f"),
}
TEXT_CATEGORIES = [c for c in CATEGORIES if c not in ("SIGNATURE", "FACE_PHOTO", "SEAL_STAMP")]
VISUAL_CATEGORIES = ["SIGNATURE", "FACE_PHOTO", "SEAL_STAMP"]
ROLES = ["subject", "professional", "party", "witness", "family", "other"]


@dataclass
class OcrLine:
    id: str
    text: str
    bbox: list[int]  # x0, y0, x1, y1
    char_boxes: list[list[int]]  # one box per character of `text`
    score: float

    def span_bbox(self, start: int, end: int, pad: int = 3) -> list[int]:
        boxes = [b for ch, b in zip(self.text[start:end], self.char_boxes[start:end]) if not ch.isspace()]
        if not boxes:
            return list(self.bbox)
        x0 = min(b[0] for b in boxes) - pad
        y0 = min(min(b[1] for b in boxes), self.bbox[1]) - pad
        x1 = max(b[2] for b in boxes) + pad
        y1 = max(max(b[3] for b in boxes), self.bbox[3]) + pad
        return [int(x0), int(y0), int(x1), int(y1)]


@dataclass
class Finding:
    id: str
    page: int
    category: str
    text: str
    bbox: list[int]
    sources: list[str]  # "rule" | "llm" | "vlm"
    confidence: float = 0.9
    role: str | None = None
    reason: str = ""
    line_id: str | None = None
    span: tuple[int, int] | None = None
    action: str = "redact"  # redact | pseudonymize | generalize_year | keep
    label: str = ""  # text printed on the redaction box, e.g. "[PATIENT-1]" or "1989"
    accepted: bool = True  # human review decision

    def to_dict(self) -> dict:
        d = asdict(self)
        d["span"] = list(self.span) if self.span else None
        return d
