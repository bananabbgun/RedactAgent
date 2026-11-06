"""Agentic second pass: an adversarial LLM tries to re-identify people in the *redacted* text.

The detectors answer "what looks like PII?". The verifier answers the question a privacy
officer actually cares about: "after redaction, could someone still work out who this is?".
It reads the de-identified text (every accepted finding already replaced by its label),
lists any residual clue - a missed name, an exact date, a rare job-and-place combination -
and gives the page a re-identification risk score. Each clue is mapped back to pixels and
added as a finding from the "agent" source, so the reviewer sees it like any other box.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .detectors.llm import UNIQUE_CUE, clean_name, fuzzy_find, plausible
from .llm_client import CallStats, ModelClient
from .schema import TEXT_CATEGORIES, Finding, OcrLine

SYSTEM = """You are a privacy auditor performing a re-identification attack on a REDACTED document.
Removed information appears as labels such as [PERSON-1], [ID], [PHONE] or [ADDRESS]; ignore those labels.
Your goal: find anything still visible that would let a motivated reader identify, locate or contact a specific
private individual. Look for:
- personal names or surnames that were missed (including "Mr./Ms./Dr. X", romanised and Chinese names)
- ID, account, chart, policy, card, plate or phone numbers, e-mail or street addresses that were missed
- exact dates tied to the person (birth, admission, signing, accident)
- quasi-identifiers: a unique job, role or title combined with a small place, team or community
  (e.g. "the only ... in ...", "唯一的...", "現任...隊長"), or rare combinations of age, job and location
Do NOT report: organisation names (hospitals, banks, courts, companies), generic medical terms or advice, drugs,
amounts of money, durations or ages ("30 days", "56-year-old"), form labels ("Date of birth", "Address"), legal
boilerplate, generic job histories ("worked as a software engineer for three years"), or redaction labels.
A quasi-identifier must point at ONE person: a rare role tied to a specific small place, team or community.

Output plain text only. One clue per line:
<line id> | <exact remaining text copied from that line> | <CATEGORY> | <high|medium|low> | <few-word reason>
CATEGORY is one of: PERSON_NAME, GOV_ID, DATE_OF_BIRTH, DATE, PHONE, EMAIL, ADDRESS, MEDICAL_RECORD_NO,
HEALTH_INSURANCE_NO, FINANCIAL_ACCOUNT, LICENSE_PLATE, QUASI_IDENTIFIER.
Last line: RISK | <0-100 probability that a private individual can still be re-identified> | <one short sentence>
If nothing remains, output only the RISK line."""

LABEL = re.compile(r"\[[A-Z][A-Z\-]*(?:-\d+)?\]|^\d{4}$")
RISK_CONF = {"high": 0.85, "medium": 0.7, "low": 0.5}


@dataclass
class Verdict:
    risk: int
    summary: str
    added: list[Finding]
    stats: CallStats


def redacted_lines(lines: list[OcrLine], findings: list[Finding]) -> dict[str, str]:
    """Line id -> text with every accepted, non-kept finding replaced by its label."""
    by_line: dict[str, list[Finding]] = {}
    for f in findings:
        if f.line_id and f.span and f.accepted and f.action != "keep":
            by_line.setdefault(f.line_id, []).append(f)
    out = {}
    for ln in lines:
        s = ln.text
        # replace right-to-left; skip spans that overlap one already replaced
        last_start = len(s) + 1
        for f in sorted(by_line.get(ln.id, []), key=lambda f: -f.span[0]):
            a, b = f.span
            if b > last_start:
                continue
            s = s[:a] + (f.label or f"[{f.category.replace('_', '-')}]") + s[b:]
            last_start = a
        out[ln.id] = s
    return out


def _covered(f_span: tuple[int, int], line_id: str, findings: list[Finding]) -> bool:
    for f in findings:
        # kept-by-policy items count as covered: they are visible on purpose, not leaks
        if f.line_id == line_id and f.span and f.accepted:
            a, b = f.span
            inter = max(0, min(b, f_span[1]) - max(a, f_span[0]))
            if inter >= 0.6 * (f_span[1] - f_span[0]):
                return True
    return False


def verify(page: int, lines: list[OcrLine], findings: list[Finding], client: ModelClient, next_id) -> Verdict:
    red = redacted_lines(lines, findings)
    numbered = "\n".join(f"[{lid}] {txt}" for lid, txt in red.items())
    raw, stats = client.chat_text(SYSTEM, f"Redacted document:\n{numbered}\n\nList the residual clues.", max_tokens=900)
    by_id = {ln.id: ln for ln in lines}
    added: list[Finding] = []
    risk, summary = 0, ""
    for row in raw.splitlines():
        parts = [p.strip() for p in row.strip().strip("`").split("|")]
        if parts and parts[0].upper() == "RISK" and len(parts) >= 2:
            m = re.search(r"\d+", parts[1])
            risk = min(100, int(m.group(0))) if m else 0
            summary = parts[2] if len(parts) > 2 else ""
            continue
        if len(parts) < 4:
            continue
        lid, text, cat, level = parts[0].strip("[]"), parts[1], parts[2].upper(), parts[3].lower()
        if cat == "PERSON_NAME":
            text = clean_name(text)
        reason = parts[4] if len(parts) > 4 else ""
        if cat not in TEXT_CATEGORIES or not text or LABEL.search(text) or not plausible(text, cat):
            continue
        cands = [by_id[lid]] if lid in by_id else []
        cands += [ln for ln in lines if ln not in cands]
        for ln in cands:
            span = fuzzy_find(ln.text, text)
            if span is None:
                continue
            if _covered(span, ln.id, findings + added):
                break  # the attacker quoted something we already redact (or keep on purpose)
            # auto-accept only confident clues; a quasi-identifier also needs an explicit uniqueness cue.
            # Everything else is shown to the reviewer as an unticked suggestion.
            accept = level == "high" or (level == "medium" and cat != "QUASI_IDENTIFIER")
            if cat == "QUASI_IDENTIFIER" and not UNIQUE_CUE.search(text):
                accept = False
            added.append(Finding(next_id(), page, cat, ln.text[span[0]:span[1]], ln.span_bbox(*span), ["agent"],
                                 RISK_CONF.get(level, 0.6), None, f"re-identification check ({level}): {reason}",
                                 ln.id, span, accepted=accept))
            break
    return Verdict(risk, summary, added, stats)
