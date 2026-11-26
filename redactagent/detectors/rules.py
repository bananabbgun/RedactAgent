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
    bbox: list[int] | None = None  # set when the value spans several OCR fragments (see row_hits)
    text: str | None = None


MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DATE_PATTERNS = [
    r"民[國国]\s?\d{2,3}\s?年\s?\d{1,2}\s?月\s?\d{1,2}\s?日(?:\s*\d{1,2}\s?[時时]\s?\d{1,2}\s?分)?",
    r"(?<!\d)\d{2,3}\s?年\s?\d{1,2}\s?月\s?\d{1,2}\s?日",
    r"(?<!\d)(?:19|20)\d{2}\s?[/\-.]\s?\d{1,2}\s?[/\-.]\s?\d{1,2}(?:\s*\d{1,2}:\d{2})?(?!\d)",
    r"(?<!\d)\d{1,2}\s?/\s?\d{1,2}\s?/\s?(?:19|20)\d{2}(?!\d)",
    MONTH + r"\.?\s*\d{1,2}\s*,?\s*(?:19|20)\d{2}",  # OCR often drops the spaces: "October19,2026"
    # ROC (Minguo) dates with slashes, e.g. 114/06/06 or 54/6/18; also with a slash lost by OCR (114/0606)
    r"(?<![\d/])(?:\d{2}|1[01]\d)\s?/\s?(?:0?[1-9]|1[0-2])\s?/\s?(?:0?[1-9]|[12]\d|3[01])(?![\d/])",
    r"(?<![\d/])1[01]\d\s?/\s?(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])(?![\d/])",
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
    ("PHONE", r"(?<![\d\-/])0[2-8]\d?-\d{3,4}-?\d{4}(?![\d\-])", 0.88, "Taiwan landline number", None, None),
    ("PHONE", r"\+886[\s\-]?\d{1,2}[\s\-]?\d{3,4}[\s\-]?\d{3,4}", 0.95, "international phone number", None, None),
    ("PHONE", r"(?<![\d\-])\(?[2-9]\d{2}\)?[\s.\-]{0,2}[2-9]\d{2}[\s.\-]\d{4}(?![\d\-])", 0.8, "North American phone number", None, None),
    ("FINANCIAL_ACCOUNT", r"(?<!\d)(?:\d{4}[\s\-]?){3}\d{4}(?!\d)", 0.97, "payment card number (Luhn-valid)", luhn_valid, None),
    ("FINANCIAL_ACCOUNT", r"\(\d{3}\)\s?\d{3,4}[\s\-]\d{3}[\s\-]\d{5,7}", 0.93, "bank code + account number", None, None),
    ("FINANCIAL_ACCOUNT", r"(?<![A-Za-z])[A-Z]{2}-\d{6,8}(?!\d)", 0.88, "insurance policy number", None,
     re.compile(r"policy|保單|保单", re.I)),
    ("HEALTH_INSURANCE_NO", r"(?<!\d)0000\s?\d{4}\s?\d{4}(?!\d)", 0.93, "NHI card number format", None, None),
    ("MEDICAL_RECORD_NO", r"MRN[\s\-:]?\d{5,10}", 0.96, "medical record number", None, None),
    ("MEDICAL_RECORD_NO", r"(?<![A-Za-z0-9])[A-Z]?\d{6,9}(?!\d)", 0.9, "chart number after keyword", None,
     re.compile(r"病[歷历][號号]|病[歷历]號碼|病[历歷]号[码碼]|chart", re.I)),
    ("MEDICAL_RECORD_NO", r"(?<![A-Za-z0-9])[A-Z]{1,3}\d{0,3}-?\d{5,9}(?!\d)", 0.88, "accession / specimen number", None,
     re.compile(r"accession|specimen|檢體|检体|chart\s*no", re.I)),
    ("LICENSE_PLATE", r"(?<![A-Za-z0-9])(?:[A-Z]{3}-\d{4}|\d{3}-[A-Z]{3}|[A-Z]{2}-\d{4}|\d{4}-[A-Z]{2})(?![A-Za-z0-9])", 0.9,
     "Taiwan licence plate format", None, None),
]


# Form-field anchoring: the value that follows a well-known label is PII even without a fixed format.
FIELD_LABELS = [
    ("PERSON_NAME", r"(?:中文|英文)?姓\s*名|緊急聯絡人|[緊紧]急[聯联][络絡]人|目擊證人|目[击擊][证證]人|證人|处理員警|處理員警|[诊診]治[医醫]師|"
                    r"原\s*告|被\s*告|法\s*官|書記官|处方医师|處方醫師|調劑藥師|调剂药师|"
                    r"Patient Name|Patient|Full name of claimant|Attending Physician|Ordering physician|Verified by|"
                    r"Emergency Contact|WITNESS|Name"),
    ("ADDRESS", r"(?:戶籍|户籍|通訊|通讯)?(?:住址|地址)|住\s*址|Residential address|Address"),
]
FIELD_RE = [(cat, re.compile(r"(?:^|\s)(?:" + lab + r")\s*[:：]\s*")) for cat, lab in FIELD_LABELS]
STOP = re.compile(r"\s{2,}|\s*[,，(（]|\s+(?:性\s*别|性\s*別|關係|关系|电话|電話|Sex|Date)|$")
ADDR_PHRASE = re.compile(r"(?:residing at|resides at|located at|living at|住於|居住於)\s*", re.I)
ADDR_STOP = re.compile(r"\s{2,}|\s*[;；]|\s*(?:電話|电话|Tel\b|TEL\b|Phone)|$")
# Taiwanese court judgments list parties without a colon: label, spaces, then the name.
JUDGMENT_NAME = re.compile(r"^\s*(?:[\u4e00-\u9fff]{1,6}庭[\s　]*)?(?:原\s*告|被\s*告|訴訟代理人|诉讼代理人|法\s*官|書記官|书记官|審判長|审判长|上\s*訴\s*人|"
                           r"被\s*上\s*訴\s*人)[\s　]+([\u4e00-\u9fff]{2,4}?(?:律師|律师)?)(?=[\s　]|$)")
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
    m = JUDGMENT_NAME.search(text)
    if m:
        out.append((m.start(1), m.end(1), "PERSON_NAME", "party/official listed in a court judgment"))
    for m in TITLE_NAME.finditer(text):
        out.append((m.start(), m.end(), "PERSON_NAME", "title + surname"))
    return out


# Lines that carry an organisation's own contact details (letterheads, hotlines, footers).
ORG_LINE = re.compile(r"hotline|www\.|https?://|\.test\b|\.com\b|\.org\b|\.gov\b|accredited|Department of|"
                      r"Hospital|Clinic|Laborator|Bank|Pharmacy|Court|醫院|医院|診所|藥局|药局|銀行|法院|客服|專線", re.I)
# Field labels that make a phone number or e-mail an institution's own contact (a facility's fax, a hospital line).
ORG_LABEL = re.compile(r"院所|機構|机构|傳真|传真|專線|专线|Facility|Provider|Billing|Fax", re.I)


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

    org_line = bool(ORG_LINE.search(text))
    org_field = bool(ORG_LABEL.search(prev_text))  # the field itself is an institution's contact (fax, facility)
    for cat, pat, conf, reason, validator, need in PATTERNS:
        if need is not None and not need.search(ctx):
            continue
        if (cat == "PHONE" and (org_line or org_field)) or (cat == "EMAIL" and org_field):
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
    out.extend(row_hits(lines))
    return out


# ---------------------------------------------------------------------------------------------------------------
# Values split over several OCR fragments on one row: a date written into printed year / month / day blanks
# ("115 年 2 月 28 日"), or characters written one per printed box (ID numbers, postcodes).
# ---------------------------------------------------------------------------------------------------------------

BOXED_LABELS = [
    ("GOV_ID", re.compile(r"身[分份][證证]|統一編號|统一编号|National ID|ID\s*(?:No|number)|Passport|護照|护照|居留", re.I)),
    ("ADDRESS", re.compile(r"郵.?區.?[號号]|邮.?区.?号|郵遞|邮递|ZIP|Postal|Post\s*code", re.I)),
    ("PHONE", re.compile(r"電話|电话|手機|手机|Phone|Tel\b", re.I)),
    ("FINANCIAL_ACCOUNT", re.compile(r"帳號|账号|Account", re.I)),
    ("MEDICAL_RECORD_NO", re.compile(r"病[歷历][號号]|Chart|MRN", re.I)),
]


def _rows(lines: list[OcrLine]) -> list[list[OcrLine]]:
    """Group fragments into rows by vertical centre: a fragment joins the row whose running mean centre is within
    0.4 of a character height (rows do not grow into the lines above and below)."""
    rows: list[tuple[list[OcrLine], list[float]]] = []
    for ln in sorted(lines, key=lambda l: (l.bbox[1] + l.bbox[3]) / 2):
        cy, h = (ln.bbox[1] + ln.bbox[3]) / 2, ln.bbox[3] - ln.bbox[1]
        for row, cys in rows:
            hs = sorted(o.bbox[3] - o.bbox[1] for o in row)
            if abs(cy - sum(cys) / len(cys)) <= 0.4 * min(h, hs[len(hs) // 2]):
                row.append(ln)
                cys.append(cy)
                break
        else:
            rows.append(([ln], [cy]))
    return [sorted(r, key=lambda l: l.bbox[0]) for r, _ in rows]


def _chains(row: list[OcrLine]) -> list[list[OcrLine]]:
    """Consecutive fragments on a row that sit close together (gap up to ~2.5 character heights)."""
    out, cur = [], [row[0]]
    for a, b in zip(row, row[1:]):
        h = max(8, min(a.bbox[3] - a.bbox[1], b.bbox[3] - b.bbox[1]))
        if b.bbox[0] - a.bbox[2] <= 2.5 * h:
            cur.append(b)
        else:
            out.append(cur)
            cur = [b]
    out.append(cur)
    return [c for c in out if len(c) > 1]


def _joined(chain: list[OcrLine]):
    """Text of a chain joined with spaces, one box and one (fragment, char index) per character. Characters that
    overlap the previous fragment (OCR sometimes reads the same digit twice where two detections overlap) are dropped."""
    text, boxes, where, right = "", [], [], -10**9
    for k, ln in enumerate(chain):
        if text:
            text += " "
            boxes.append(None)
            where.append(None)
        for i, (ch, b) in enumerate(zip(ln.text, ln.char_boxes)):
            if (b[0] + b[2]) / 2 < right:
                continue
            text += ch
            boxes.append(b)
            where.append((k, i))
        right = max(right, ln.bbox[2])
    return text, boxes, where


def _per_fragment(chain, where, start: int, end: int) -> list[tuple[OcrLine, int, int]]:
    spans: dict[int, list[int]] = {}
    for w in where[start:end]:
        if w is not None:
            spans.setdefault(w[0], []).append(w[1])
    return [(chain[k], min(ix), max(ix) + 1) for k, ix in sorted(spans.items())]


def _union(boxes) -> list[int]:
    bs = [b for b in boxes if b]
    return [min(b[0] for b in bs) - 3, min(b[1] for b in bs) - 3, max(b[2] for b in bs) + 3, max(b[3] for b in bs) + 3]


def row_hits(lines: list[OcrLine]) -> list[RuleHit]:
    out: list[RuleHit] = []
    for row in _rows(lines):
        for chain in _chains(row):
            text, boxes, where = _joined(chain)
            ctx = label_context(chain[0], lines) + " " + text
            is_dob = bool(DOB_CONTEXT.search(ctx))
            for pat in DATE_PATTERNS:
                for m in re.finditer(pat, text, re.I):
                    frags = _per_fragment(chain, where, m.start(), m.end())
                    if len(frags) < 2:
                        continue  # a single fragment is already handled line by line
                    cat = "DATE_OF_BIRTH" if is_dob else "DATE"
                    reason = ("date of birth" if is_dob else "calendar date") + " written across form blanks"
                    (l0, a0, b0), rest = frags[0], frags[1:]
                    # one finding carries the box over the whole date; the other fragments get their own text spans
                    out.append(RuleHit(l0.id, a0, b0, cat, 0.88, reason, bbox=_union(boxes[m.start():m.end()]), text=m.group(0)))
                    out.extend(RuleHit(l.id, a, b, cat, 0.88, reason) for l, a, b in rest)
        # characters written one per printed box: runs of single-character fragments on the row (unread boxes
        # may sit between them, so the gap allowed is wider than within a chain)
        run: list[OcrLine] = []
        for ln in row + [None]:
            single = ln is not None and re.fullmatch(r"[A-Za-z0-9]{1,2}", ln.text.strip()) is not None
            if single and run:
                h = max(10, run[-1].bbox[3] - run[-1].bbox[1])
                if ln.bbox[0] - run[-1].bbox[2] > max(5 * h, 120):
                    out.extend(_boxed(run, lines))
                    run = []
            if single:
                run.append(ln)
            else:
                out.extend(_boxed(run, lines))
                run = []
    return out


def _boxed(run: list[OcrLine], lines: list[OcrLine]) -> list[RuleHit]:
    if len(run) < 2:
        return []
    label = label_context(run[0], lines)
    cat = next((c for c, rx in BOXED_LABELS if rx.search(label)), None)
    if not cat:
        return []
    rx = dict(BOXED_LABELS)[cat]
    x0, y0 = min(l.bbox[0] for l in run), min(l.bbox[1] for l in run)
    x1, y1 = max(l.bbox[2] for l in run), max(l.bbox[3] for l in run)
    for o in lines:  # stretch over the printed boxes that the OCR did not read
        if not rx.search(o.text):
            continue
        if o.bbox[3] <= y0 + 6 and o.bbox[3] > y0 - 60 and min(x1, o.bbox[2]) > max(x0, o.bbox[0]):
            x0, x1 = min(x0, o.bbox[0]), max(x1, o.bbox[2])      # label above the boxes
        elif abs((o.bbox[1] + o.bbox[3]) / 2 - (y0 + y1) / 2) < 20 and o.bbox[2] <= x0 and x0 - o.bbox[2] < 250:
            x0 = min(x0, o.bbox[2] + 2)                            # label to the left
    value = "".join(l.text.strip() for l in run)
    reason = f"characters written one per box after '{label.strip()[:12]}'"
    return [RuleHit(run[0].id, 0, len(run[0].text), cat, 0.85, reason, bbox=[x0 - 3, y0 - 3, x1 + 3, y1 + 3], text=value)] + \
        [RuleHit(l.id, 0, len(l.text), cat, 0.85, reason) for l in run[1:]]


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
