"""Fast unit tests for the deterministic parts of RedactAgent (no models needed).

    python -m pytest -q tests
"""

import json

import pytest

from redactagent import policy as policy_mod
from redactagent import verifier
from redactagent.audit import AuditLog
from redactagent.detectors import rules
from redactagent.detectors.llm import clean_name, fuzzy_find, parse_output, plausible, strip_label
from redactagent.llm_client import CallStats
from redactagent.schema import Finding, OcrLine


def line(text: str, lid: str = "P1L1") -> OcrLine:
    return OcrLine(lid, text, [0, 0, 10 * len(text), 30], [[10 * i, 0, 10 * i + 10, 30] for i in range(len(text))], 1.0)


def hits(text: str) -> list[tuple[str, str]]:
    return [(h.category, text[h.start:h.end]) for h in rules.detect_line(line(text))]


# --- rule engine ---------------------------------------------------------------------------------

@pytest.mark.parametrize("tid,ok", [("A123456789", True), ("A123456788", False), ("F131104093", True)])
def test_tw_id_checksum(tid, ok):
    assert rules.tw_id_valid(tid) is ok


def test_card_luhn():
    assert rules.luhn_valid("4111 1111 1111 1111")
    assert not rules.luhn_valid("4111 1111 1111 1112")


@pytest.mark.parametrize("text,expected", [
    ("National ID: A123456789", ("GOV_ID", "A123456789")),
    ("Phone: 0912-345-678", ("PHONE", "0912-345-678")),
    ("Collected:2026-03-22 09:57", ("DATE", "2026-03-22 09:57")),
    ("Admission:October19,2026", ("DATE", "October19,2026")),
    ("出生日期：民國78年5月3日", ("DATE_OF_BIRTH", "民國78年5月3日")),
    ("Accession:SP98-692018", ("MEDICAL_RECORD_NO", "SP98-692018")),
    ("姓名：王小明", ("PERSON_NAME", "王小明")),
    ("訴訟代理人　林仁傑律師", ("PERSON_NAME", "林仁傑律師")),
    ("民事庭　法　官　蔡俊良", ("PERSON_NAME", "蔡俊良")),
    ("residing at No. 377, Ziyou Rd., Sec. 1, Xitun Dist.;", ("ADDRESS", "No. 377, Ziyou Rd., Sec. 1, Xitun Dist")),
])
def test_rule_hits(text, expected):
    assert expected in hits(text)


def test_organisation_phone_is_not_pii():
    assert hits("Department of Internal Medicine | Tel (02) 2700-0000") == []
    assert hits("Report lost cards via our 24-hour hotline (02) 2181-0000.") == []


def test_address_stops_before_phone():
    assert ("ADDRESS", "臺南市安平區中正路二段209號八樓") in hits("地址：臺南市安平區中正路二段209號八樓　電話：(02)2100-7901")


# --- LLM output handling --------------------------------------------------------------------------

def test_parse_and_clean():
    out = parse_output("DOC | discharge summary\nP1L4 | PERSON_NAME | subject | Hsu Chih-wei\ngarbage line")
    assert out["doc_type"] == "discharge summary" and out["entities"][0]["text"] == "Hsu Chih-wei"
    assert strip_label("Patient Name:Hsu Chih-wei") == "Hsu Chih-wei"
    assert clean_name("Transfer to YANG HAN-MING") == "YANG HAN-MING"


@pytest.mark.parametrize("text,cat,ok", [
    ("31-year-old", "DATE", False), ("Date of treatment", "DATE", False), ("04/15/2025", "DATE", True),
    ("Riverside Memorial Hospital", "ADDRESS", False), ("No.122,Heping E.Rd.", "ADDRESS", True),
    ("Taipower", "PERSON_NAME", False), ("City Supermarket", "PERSON_NAME", False), ("Yang Shu-hsin", "PERSON_NAME", True),
    ("the only licensed ferry captain on Green Island", "QUASI_IDENTIFIER", True),
    ("worked as a software engineer for three years", "QUASI_IDENTIFIER", False),
])
def test_plausibility(text, cat, ok):
    assert plausible(text, cat) is ok


def test_fuzzy_find_tolerates_ocr_spacing():
    assert fuzzy_find("Specimen from YangShu-hsin, who", "Yang Shu-hsin") is not None


# --- policies ---------------------------------------------------------------------------------------

def test_research_policy_pseudonymises_consistently():
    pol = policy_mod.load_policies()["research"]
    fs = [Finding("1", 0, "PERSON_NAME", "Hsu Chih-wei", [0, 0, 1, 1], ["rule"], role="subject"),
          Finding("2", 0, "PERSON_NAME", "Ms. Hsu", [0, 0, 1, 1], ["rule"], role="subject"),
          Finding("3", 0, "DATE", "04/15/2025", [0, 0, 1, 1], ["rule"]),
          Finding("4", 0, "GOV_ID", "A123456789", [0, 0, 1, 1], ["rule"])]
    policy_mod.apply(pol, fs)
    assert fs[0].label == fs[1].label == "[PERSON-1]"
    assert fs[2].action == "generalize_year" and fs[2].label == "2025"
    assert fs[3].action == "redact"


def test_litigation_keeps_parties_masks_ids():
    pol = policy_mod.load_policies()["litigation"]
    fs = [Finding("1", 0, "PERSON_NAME", "Lee", [0, 0, 1, 1], ["rule"], role="party"),
          Finding("2", 0, "GOV_ID", "A123456789", [0, 0, 1, 1], ["rule"])]
    policy_mod.apply(pol, fs)
    assert fs[0].action == "keep" and fs[1].action == "redact"


# --- audit trail --------------------------------------------------------------------------------------

def test_audit_chain_detects_tampering(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    for i in range(3):
        log.append("detect", f"job{i}", n=i)
    assert log.verify()["ok"]
    lines = (tmp_path / "audit.jsonl").read_text().splitlines()
    rec = json.loads(lines[1]); rec["data"]["n"] = 99
    lines[1] = json.dumps(rec)
    (tmp_path / "audit.jsonl").write_text("\n".join(lines) + "\n")
    v = log.verify()
    assert not v["ok"] and v["broken_at"] == 1


# --- agentic verifier (fake model) -----------------------------------------------------------------------

class FakeAttacker:
    model = "fake"

    def chat_text(self, system, user, max_tokens=900):
        assert "[PERSON-1]" in user  # the attacker only ever sees redacted text
        return ("P1L2 | the only licensed ferry captain on Green Island | QUASI_IDENTIFIER | high | rare job + island\n"
                "P1L1 | [PERSON-1] | PERSON_NAME | high | label only\n"
                "RISK | 85 | unique occupation on a small island"), CallStats(0.1)


def test_verifier_adds_residual_clue_and_score():
    l1, l2 = line("Patient Name:Hsu Chih-wei", "P1L1"), line("the only licensed ferry captain on Green Island.", "P1L2")
    f = Finding("f1", 0, "PERSON_NAME", "Hsu Chih-wei", [0, 0, 1, 1], ["rule"], line_id="P1L1", span=(13, 25),
                label="[PERSON-1]", action="pseudonymize")
    ids = iter(range(10))
    v = verifier.verify(0, [l1, l2], [f], FakeAttacker(), lambda: f"a{next(ids)}")
    assert v.risk == 85
    assert [(a.category, a.accepted) for a in v.added] == [("QUASI_IDENTIFIER", True)]
