"""Contextual layer: a local LLM reads the OCR text and finds PII that has no fixed format.

Names, addresses, a person's role in the document (patient vs. physician, party vs.
witness) and quasi-identifiers ("the only dentist on Orchid Island") all need
language understanding. The model sees numbered OCR lines and must quote each
entity exactly, so every finding maps back to pixel coordinates.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

from ..llm_client import CallStats, ModelClient
from ..schema import ROLES, TEXT_CATEGORIES, OcrLine

SYSTEM = """You are RedactAgent, an on-premises de-identification engine for scanned Taiwanese and English documents \
(medical records, contracts, police reports, insurance and HR forms). You receive OCR lines, each prefixed with an id \
like [P1L7]. OCR may contain small errors or simplified Chinese glyphs - copy text exactly as it appears in the line.

Find every piece of personally identifiable information (PII) and label it with one category:
- PERSON_NAME: a person's name (Chinese or romanised, full name, surname alone, or "Dr./Mr./Ms. X"). Include the title "Dr." if present.
- GOV_ID: national ID, passport, resident certificate (ARC) numbers.
- DATE_OF_BIRTH: a birth date.
- DATE: any other date tied to the individual (admission, visit, accident, signing, issue date), including ROC calendar dates such as 民國112年3月4日 or 112年3月4日.
- PHONE, EMAIL: contact details of a person.
- ADDRESS: a residential or property street address (the whole address as one entity).
- MEDICAL_RECORD_NO, HEALTH_INSURANCE_NO, FINANCIAL_ACCOUNT (bank account, credit card, insurance policy number), LICENSE_PLATE.
- QUASI_IDENTIFIER: a phrase that would single out one person even without a name, e.g. a unique job or role in a small place \
("the only licensed ferry captain on Green Island", "現任國家女子冰壺隊總教練"). Quote the whole phrase.

Also give the person's role in the document when the entity is about a person: subject (patient, claimant, employee), \
professional (physician, officer, lawyer acting in official capacity), party (contract or accident party), witness, family, other.

Do NOT flag: form labels ("Name:", "姓名"), role words alone ("LANDLORD", "Patient", "當事人"), hospital/company/agency names, \
departments, diagnoses, drugs, amounts of money (NT$...), case or certificate serial numbers, generic places like road \
intersections, the document title, or footer disclaimers.
"text" must be ONLY the value, never the form label: for "Patient Name: Hsu Chih-wei" return "Hsu Chih-wei"; \
for "住址：臺北市大安區…" return "臺北市大安區…".
Return each distinct occurrence separately (if a name appears on two lines, return two entities).

Before answering, scan EVERY line top to bottom, including free-text paragraphs: names in 姓名/中文姓名 fields, \
surnames with a title inside sentences ("Ms. Hsu", "Mr. Lin"), names after 病人/當事人/駕駛, and quasi-identifying \
job/role descriptions. Missing PII is far worse than an extra entity.

Output format - plain text, nothing else. First line: DOC | <short document type>. Then one entity per line:
<line id> | <CATEGORY> | <role or none> | <exact text>
Example:
DOC | discharge summary
P1L4 | PERSON_NAME | subject | Hsu Chih-wei
P1L9 | ADDRESS | subject | No. 372, Fuxing S. Rd., Sec. 4, Zuoying Dist., Kaohsiung City"""

SCHEMA = {
    "type": "object",
    "properties": {
        "doc_type": {"type": "string"},
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "line": {"type": "string"},
                    "text": {"type": "string"},
                    "category": {"type": "string", "enum": TEXT_CATEGORIES},
                    "role": {"type": "string", "enum": ROLES + ["none"]},
                },
                "required": ["line", "text", "category", "role"],
            },
        },
    },
    "required": ["doc_type", "entities"],
}


ROLE_ALIASES = {"patient": "subject", "claimant": "subject", "employee": "subject", "applicant": "subject",
                "landlord": "party", "tenant": "party", "driver": "party", "physician": "professional",
                "doctor": "professional", "officer": "professional", "police": "professional",
                "relative": "family", "emergency contact": "family", "spouse": "family", "mother": "family"}


@dataclass
class LlmHit:
    line_id: str
    start: int
    end: int
    text: str
    category: str
    role: str | None
    reason: str


LABEL_PREFIX = re.compile(r"^\s*([^:：\d]{1,24})[:：]\s*(.+)$")


def strip_label(text: str) -> str:
    """Drop a leading form label ("Name:", "住址：") that the model sometimes copies along with the value."""
    m = LABEL_PREFIX.match(text)
    return m.group(2).strip() if m else text


def fuzzy_find(hay: str, needle: str) -> tuple[int, int] | None:
    """Locate `needle` in `hay`, tolerating OCR noise and whitespace differences."""
    if not needle:
        return None
    i = hay.find(needle)
    if i >= 0:
        return i, i + len(needle)
    # whitespace-insensitive match
    squeezed = [(c, k) for k, c in enumerate(hay) if not c.isspace()]
    hs = "".join(c for c, _ in squeezed)
    ns = "".join(c for c in needle if not c.isspace())
    j = hs.find(ns)
    if j >= 0 and ns:
        return squeezed[j][1], squeezed[j + len(ns) - 1][1] + 1
    # approximate match: best window by similarity
    sm = difflib.SequenceMatcher(None, hay, needle, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size > 0]
    if not blocks:
        return None
    start = blocks[0].a
    end = blocks[-1].a + blocks[-1].size
    matched = sum(b.size for b in blocks)
    if matched / max(1, len(needle)) >= 0.75 and (end - start) <= len(needle) * 1.5 + 2:
        return start, end
    return None


def _masked(ln: OcrLine, spans: list[tuple[int, int, str]]) -> str:
    s = ln.text
    for a, b, cat in sorted(spans, key=lambda x: -x[0]):
        s = s[:a] + f"⟦{cat}⟧" + s[b:]
    return s


def plausible(text: str, cat: str) -> bool:
    """Cheap sanity checks against typical LLM over-flagging."""
    t = text.strip()
    if cat == "QUASI_IDENTIFIER":
        words = len(t.split())
        cjk = sum(1 for c in t if "\u4e00" <= c <= "\u9fff")
        return (words >= 4 or cjk >= 6) and len(t) <= 80 and "RedactAgent" not in t
    if cat == "FINANCIAL_ACCOUNT":
        return "$" not in t and sum(c.isdigit() for c in t) >= 6
    if cat == "PERSON_NAME":
        return not (t.isupper() and " " not in t and len(t) > 4)  # "LANDLORD", "TENANT"
    digits = sum(c.isdigit() for c in t)
    if cat in ("GOV_ID", "MEDICAL_RECORD_NO", "HEALTH_INSURANCE_NO", "PHONE"):
        return digits >= 6 and not re.search(r"\bmg\b|字第", t)
    if cat == "EMAIL":
        return "@" in t
    if cat == "LICENSE_PLATE":
        return digits >= 2
    return True


def detect(lines: list[OcrLine], client: ModelClient, known: dict[str, list[tuple[int, int, str]]] | None = None
           ) -> tuple[list[LlmHit], str, CallStats]:
    """`known`: spans already found by the rule engine, per line id; they are masked so the model fills the gaps."""
    if not lines:
        return [], "", CallStats(0.0)
    known = known or {}
    numbered = "\n".join(f"[{ln.id}] {_masked(ln, known.get(ln.id, []))}" for ln in lines)
    user = f"OCR lines:\n{numbered}\n\nList the PII entities in the output format."
    raw, stats = client.chat_text(SYSTEM, user, max_tokens=1500, num_ctx=4096)
    out = parse_output(raw)
    by_id = {ln.id: ln for ln in lines}
    hits: list[LlmHit] = []
    used: set[tuple[str, int, int]] = {(lid, a, b) for lid, sp in known.items() for a, b, _ in sp}
    for ent in out.get("entities", []):
        text = strip_label((ent.get("text") or "").strip())
        cat = ent.get("category")
        if not text or cat not in TEXT_CATEGORIES or not plausible(text, cat) or "⟦" in text:
            continue
        candidates = [by_id[ent["line"]]] if ent.get("line") in by_id else []
        candidates += [ln for ln in lines if ln not in candidates]
        for ln in candidates:
            span = fuzzy_find(ln.text, text)
            if span is None:
                continue
            key = (ln.id, span[0], span[1])
            if key in used:  # same text repeated: look for the next occurrence on the line
                nxt = ln.text.find(text, span[1])
                if nxt < 0:
                    continue
                span = (nxt, nxt + len(text))
                key = (ln.id, *span)
            used.add(key)
            role = ROLE_ALIASES.get(ent.get("role") or "", ent.get("role"))
            role = role if role in ROLES else None
            hits.append(LlmHit(ln.id, span[0], span[1], ln.text[span[0]:span[1]], cat,
                               role, _reason(cat, role)))
            break
    hits += propagate(hits, lines, used)
    return hits, out.get("doc_type", ""), stats


def parse_output(raw: str) -> dict:
    """Parse 'DOC | type' and 'line | CATEGORY | role | text' lines; ignore anything malformed."""
    doc_type, ents = "", []
    for row in raw.splitlines():
        parts = [p.strip() for p in row.strip().strip("`").split("|")]
        if len(parts) == 2 and parts[0].upper() == "DOC":
            doc_type = parts[1]
        elif len(parts) >= 4:
            line, cat, role = parts[0], parts[1].upper(), parts[2].lower()
            text = "|".join(parts[3:]).strip()
            ents.append({"line": line, "category": cat, "role": role, "text": text})
    return {"doc_type": doc_type, "entities": ents}


def _reason(cat: str, role: str | None) -> str:
    who = f" of the {role}" if role and role != "none" else ""
    return f"contextual LLM: {cat.replace('_', ' ').lower()}{who}"


def propagate(hits: list[LlmHit], lines: list[OcrLine], used: set) -> list[LlmHit]:
    """The model often reports a name once; copy every confirmed entity to its other exact occurrences."""
    extra = []
    seen = {(h.text, h.category) for h in hits}
    for text, cat in seen:
        if len(text.strip()) < 2 or cat in ("DATE", "QUASI_IDENTIFIER"):
            continue
        role = next((h.role for h in hits if h.text == text and h.category == cat), None)
        for ln in lines:
            start = ln.text.find(text)
            while start >= 0:
                key = (ln.id, start, start + len(text))
                if not any(k[0] == ln.id and k[1] < key[2] and key[1] < k[2] for k in used):
                    used.add(key)
                    extra.append(LlmHit(ln.id, start, start + len(text), text, cat, role,
                                        _reason(cat, role) + " (repeated mention)"))
                start = ln.text.find(text, start + len(text))
    return extra
