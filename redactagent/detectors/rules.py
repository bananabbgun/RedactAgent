"""Deterministic layer: regular expressions + checksums for structured identifiers.

Fast (<5 ms/page), explainable and high-precision. It covers identifiers with a
fixed format; free-text PII (names, addresses, quasi-identifiers) is left to the
LLM layer. OCR of Traditional Chinese sometimes yields simplified glyphs
(號 -> 号), so keyword classes accept both.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..schema import OcrLine

TW_ID_LETTERS = {
    "A": 10, "B": 11, "C": 12, "D": 13, "E": 14, "F": 15, "G": 16, "H": 17, "I": 34,
    "J": 18, "K": 19, "L": 20, "M": 21, "N": 22, "O": 35, "P": 23, "Q": 24, "R": 25,
    "S": 26, "T": 27, "U": 28, "V": 29, "W": 32, "X": 30, "Y": 31, "Z": 33,
}


def tw_id_valid(s: str) -> bool:
    if not re.fullmatch(r"[A-Z][12]\d{8}", s):
        return False
    code = TW_ID_LETTERS[s[0]]
    total = (code // 10) + (code % 10) * 9 + sum(int(d) * w for d, w in zip(s[1:9], [8, 7, 6, 5, 4, 3, 2, 1]))
    return (total + int(s[9])) % 10 == 0


def luhn_valid(s: str) -> bool:
    digits = [int(c) for c in s if c.isdigit()]
    if len(digits) < 13:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


@dataclass
class RuleHit:
    line_id: str
    start: int
    end: int
    category: str
    confidence: float
    reason: str


MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DATE_PATTERNS = [
    r"民[國国]\s?\d{2,3}\s?年\s?\d{1,2}\s?月\s?\d{1,2}\s?日(?:\s*\d{1,2}\s?[時时]\s?\d{1,2}\s?分)?",
    r"(?<!\d)\d{2,3}\s?年\s?\d{1,2}\s?月\s?\d{1,2}\s?日",
    r"(?<!\d)(?:19|20)\d{2}\s?[/\-.]\s?\d{1,2}\s?[/\-.]\s?\d{1,2}(?!\d)",
    r"(?<!\d)\d{1,2}\s?/\s?\d{1,2}\s?/\s?(?:19|20)\d{2}(?!\d)",
    MONTH + r"\.?\s*\d{1,2}\s*,?\s*(?:19|20)\d{2}",  # OCR often drops the spaces: "October19,2026"
]
DOB_CONTEXT = re.compile(r"birth|DOB|出生|生日", re.I)

# (category, pattern, confidence, reason, validator, required-context regex or None)
PATTERNS = [
    ("GOV_ID", r"(?<![A-Za-z0-9])[A-Z][12]\d{8}(?!\d)", 0.97, "Taiwan national ID format", tw_id_valid, None),
    ("GOV_ID", r"(?<![A-Za-z0-9])[A-Z]?\d{8,9}(?!\d)", 0.85, "passport / ARC number after keyword", None,
     re.compile(r"passport|護照|护照|ARC|居留", re.I)),
    ("EMAIL", r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+", 0.98, "e-mail address", None, None),
    ("PHONE", r"(?<!\d)09\d{2}\s?[-\s]?\s?\d{3}\s?[-\s]?\s?\d{3}(?!\d)", 0.95, "Taiwan mobile number", None, None),
    ("PHONE", r"\(0\d{1,2}\)\s?\d{3,4}\s?-\s?\d{4}", 0.9, "Taiwan landline number", None, None),
    ("PHONE", r"\+886[\s\-]?\d{1,2}[\s\-]?\d{3,4}[\s\-]?\d{3,4}", 0.95, "international phone number", None, None),
    ("FINANCIAL_ACCOUNT", r"(?<!\d)(?:\d{4}[\s\-]?){3}\d{4}(?!\d)", 0.97, "payment card number (Luhn-valid)", luhn_valid, None),
    ("FINANCIAL_ACCOUNT", r"\(\d{3}\)\s?\d{3,4}[\s\-]\d{3}[\s\-]\d{5,7}", 0.93, "bank code + account number", None, None),
    ("FINANCIAL_ACCOUNT", r"(?<![A-Za-z])[A-Z]{2}-\d{6,8}(?!\d)", 0.88, "insurance policy number", None,
     re.compile(r"policy|保單|保单", re.I)),
    ("HEALTH_INSURANCE_NO", r"(?<!\d)0000\s?\d{4}\s?\d{4}(?!\d)", 0.93, "NHI card number format", None, None),
    ("MEDICAL_RECORD_NO", r"MRN[\s\-:]?\d{5,10}", 0.96, "medical record number", None, None),
    ("MEDICAL_RECORD_NO", r"(?<![A-Za-z0-9])[A-Z]?\d{6,9}(?!\d)", 0.9, "chart number after keyword", None,
     re.compile(r"病[歷历][號号]|病[歷历]號碼|病[历歷]号[码碼]|chart", re.I)),
    ("LICENSE_PLATE", r"(?<![A-Za-z0-9])(?:[A-Z]{3}-\d{4}|\d{3}-[A-Z]{3}|[A-Z]{2}-\d{4}|\d{4}-[A-Z]{2})(?![A-Za-z0-9])", 0.9,
     "Taiwan licence plate format", None, None),
]


# Form-field anchoring: the value that follows a well-known label is PII even without a fixed format.
FIELD_LABELS = [
    ("PERSON_NAME", r"(?:中文|英文)?姓\s*名|緊急聯絡人|[緊紧]急[聯联][络絡]人|目擊證人|目[击擊][证證]人|證人|处理員警|處理員警|[诊診]治[医醫]師|"
                    r"Patient Name|Full name of claimant|Attending Physician|Emergency Contact|WITNESS|Name"),
    ("ADDRESS", r"(?:戶籍|户籍|通訊|通讯)?(?:住址|地址)|住\s*址|Residential address|Address"),
]
FIELD_RE = [(cat, re.compile(r"(?:^|\s)(?:" + lab + r")\s*[:：]\s*")) for cat, lab in FIELD_LABELS]
STOP = re.compile(r"\s{2,}|\s*[,，(（]|\s+(?:性\s*别|性\s*別|關係|关系|电话|電話|Sex|Date)|$")
ADDR_PHRASE = re.compile(r"(?:residing at|resides at|located at|living at|住於|居住於)\s*", re.I)
ADDR_STOP = re.compile(r"\s{2,}|\s*[;；]|$")
TITLE_NAME = re.compile(r"(?:Mrs|Mr|Ms|Dr)\.\s?[A-Z][a-z]+(?:\s?[A-Z][a-z]+(?:-[a-z]+)?)?")


def field_hits(text: str) -> list[tuple[int, int, str, str]]:
    out = []
    for cat, rx in FIELD_RE:
        for m in rx.finditer(text):
            start = m.end()
            stop = (ADDR_STOP if cat == "ADDRESS" else STOP).search(text, start)
            end = stop.start() if stop else len(text)
            value = text[start:end].strip()
            if cat == "PERSON_NAME" and not (1 < len(value) <= 30):
                continue
            if cat == "ADDRESS" and len(value) < 6:
                continue
            if value:
                out.append((start, start + len(value), cat, f"value of form field '{m.group(0).strip(' :：')}'"))
    for m in ADDR_PHRASE.finditer(text):
        stop = re.compile(r"\s*[;；(（]|\s{2,}|$").search(text, m.end())
        value = text[m.end():stop.start()].strip().rstrip(",.")
        if len(value) >= 10 and re.search(r"\d", value):
            out.append((m.end(), m.end() + len(value), "ADDRESS", f"address after '{m.group(0).strip()}'"))
    for m in TITLE_NAME.finditer(text):
        out.append((m.start(), m.end(), "PERSON_NAME", "title + surname"))
    return out


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def detect_line(line: OcrLine, prev_text: str = "") -> list[RuleHit]:
    text = line.text
    ctx = prev_text + " " + text
    hits: list[RuleHit] = []
    taken: list[tuple[int, int]] = []

    def add(s, e, cat, conf, reason):
        if any(_overlaps((s, e), t) for t in taken):
            return
        taken.append((s, e))
        hits.append(RuleHit(line.id, s, e, cat, conf, reason))

    for cat, pat, conf, reason, validator, need in PATTERNS:
        if need is not None and not need.search(ctx):
            continue
        for m in re.finditer(pat, text):
            value = m.group(0)
            if validator is not None and not validator(value.replace(" ", "").replace("-", "") if cat != "GOV_ID" else value):
                if cat == "GOV_ID":  # format matches but checksum fails: likely an OCR error, keep with lower confidence
                    add(m.start(), m.end(), cat, 0.7, reason + " (checksum failed - possible OCR error)")
                continue
            add(m.start(), m.end(), cat, conf, reason + (" (checksum valid)" if validator else ""))

    for s0, e0, cat, reason in field_hits(text):
        add(s0, e0, cat, 0.85, reason)

    is_dob = bool(DOB_CONTEXT.search(ctx))
    for pat in DATE_PATTERNS:
        for m in re.finditer(pat, text, re.I):
            cat = "DATE_OF_BIRTH" if is_dob else "DATE"
            add(m.start(), m.end(), cat, 0.9, "date of birth" if is_dob else "calendar date")
    return hits


def detect(lines: list[OcrLine]) -> list[RuleHit]:
    out: list[RuleHit] = []
    for ln in lines:
        out.extend(detect_line(ln, label_context(ln, lines)))
    return out


def label_context(ln: OcrLine, lines: list[OcrLine]) -> str:
    """Text of nearby labels: lines directly above (form-box headers) or to the left on the same row."""
    x0, y0, x1, y1 = ln.bbox
    cy = (y0 + y1) / 2
    ctx = []
    for o in lines:
        if o is ln:
            continue
        ox0, oy0, ox1, oy1 = o.bbox
        above = oy1 <= y0 + 6 and oy1 > y0 - 60 and min(x1, ox1) - max(x0, ox0) > 0
        left = abs((oy0 + oy1) / 2 - cy) < 15 and ox1 <= x0 + 4 and x0 - ox1 < 250
        if above or left:
            ctx.append(o.text)
    return " ".join(ctx)
