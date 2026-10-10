"""Build the Stage I proposal deck (HTML -> PDF via headless Chrome).

    python deck/build_deck.py [--out ../deliverables/RedactAgent_proposal.pdf]

Numbers on the results slides come straight from eval/results/metrics.json, and the
policy triptych is rendered by the real pipeline code from saved findings.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DECK = ROOT / "deck"
sys.path.insert(0, str(ROOT))

from redactagent import policy as policy_mod  # noqa: E402
from redactagent import render  # noqa: E402
from redactagent.schema import CATEGORIES, Finding  # noqa: E402

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DETECTOR = {
    "PERSON_NAME": "form fields + LLM", "GOV_ID": "regex + checksum", "DATE_OF_BIRTH": "regex + label context / LLM",
    "DATE": "regex", "PHONE": "regex", "EMAIL": "regex", "ADDRESS": "form fields + LLM", "MEDICAL_RECORD_NO": "regex + keyword",
    "HEALTH_INSURANCE_NO": "regex", "FINANCIAL_ACCOUNT": "regex + Luhn", "LICENSE_PLATE": "regex", "QUASI_IDENTIFIER": "LLM only",
    "SIGNATURE": "VLM", "FACE_PHOTO": "VLM", "SEAL_STAMP": "colour + VLM",
}


RESULTS = ROOT / "eval" / "results"


def triptych(doc_id: str = "discharge_summary_en_00") -> list[dict]:
    raw = json.loads((RESULTS / "raw" / f"{doc_id}.json").read_text())
    img = Image.open(ROOT / "data" / "synthetic" / "images" / f"{doc_id}.jpg").convert("RGB")
    pols = policy_mod.load_policies()
    out = []
    (DECK / "assets").mkdir(exist_ok=True)
    for pid, title, desc in [
        ("research", "Research extract (IRB)", "Patients & staff pseudonymised consistently; dates kept as year only."),
        ("litigation", "Court filing", "Parties, dates and signatures kept; IDs, accounts, contacts and relatives masked."),
        ("public_release", "Public release (FOI)", "Private individuals removed; the physician acting officially is kept."),
    ]:
        fs = []
        for d in raw["findings"]:
            d = dict(d)
            d["span"] = tuple(d["span"]) if d.get("span") else None
            fs.append(Finding(**d))
        policy_mod.apply(pols[pid], fs)
        red = render.redact_page(img, fs).crop((40, 40, 1200, 1700))
        p = DECK / "assets" / f"policy_{pid}.png"
        red.save(p)
        out.append({"title": title, "desc": desc, "img": f"assets/policy_{pid}.png"})
    return out


def error_notes(errors: dict) -> list[str]:
    miss = errors["C_full"]["missed"]
    fps = errors["C_full"]["false_positives"]
    by = Counter(m["cat"] for m in miss)
    notes = []
    for cat, n in by.most_common(3):
        ex = next(m["text"] for m in miss if m["cat"] == cat)
        ex = ex if len(ex) <= 30 else ex[:30].rsplit(" ", 1)[0] + "…"
        notes.append(f"{n} missed {CATEGORIES[cat][0].lower()} item(s), e.g. “{ex}”")
    if fps:
        fc = Counter(f["cat"] for f in fps).most_common(2)
        notes.append("Most frequent extra boxes: " + ", ".join(f"{CATEGORIES.get(c, (c,))[0].lower()} ({n})" for c, n in fc)
                     + " (e.g. hospital phone, title kept with name)")
    notes.append("Next: larger contextual model on the B70 + a second verification pass")
    return notes


def quasi_example(errors: dict) -> dict:
    """A narrative sentence whose name, quasi-identifier and date were all removed in the final run."""
    missed = {(e["doc"], e["text"]) for e in errors["C_full"]["missed"]}
    for k in range(6):
        doc = f"discharge_summary_en_{k:02d}"
        gt = json.loads((ROOT / "data" / "synthetic" / "gt" / f"{doc}.json").read_text())["items"]
        quasi = next((g for g in gt if g["cat"] == "QUASI_IDENTIFIER"), None)
        name = next((g for g in gt if g["cat"] == "PERSON_NAME" and " " not in g["text"]), None)
        dates = [g for g in gt if g["cat"] == "DATE" and quasi and abs(g["bbox"][1] - quasi["bbox"][1]) < 60]
        if quasi and name and dates and not ({(doc, quasi["text"]), (doc, name["text"]), (doc, dates[0]["text"])} & missed):
            raw = json.loads((RESULTS / "raw" / f"{doc}.json").read_text())["findings"]
            title = next((f["text"][:3] for f in raw if f["text"][:3] in ("Mr.", "Ms.")), "Ms.")
            return {"doc": doc, "title": title, "name": name["text"], "quasi": quasi["text"], "date": dates[0]["text"]}
    return {"doc": "discharge_summary_en_00", "title": "Ms.", "name": "Hsu",
            "quasi": "the only licensed ferry captain on Green Island", "date": "04/15/2025"}


def build(out_pdf: Path):
    cfg = yaml.safe_load((DECK / "config.yaml").read_text(encoding="utf-8"))
    m = json.loads((RESULTS / "metrics.json").read_text())
    errors = json.loads((RESULTS / "errors.json").read_text())
    lat = m["latency_seconds_per_page"]
    cats = []
    for c in CATEGORIES:
        n = m["C_full"]["support_by_category"].get(c, 0)
        if n:
            cats.append({"id": c, "name": CATEGORIES[c][0], "n": n, "A": m["A_deterministic"]["recall_by_category"][c],
                         "C": m["C_full"]["recall_by_category"][c], "detector": DETECTOR[c]})
    env = Environment(loader=FileSystemLoader(DECK), autoescape=False)
    missed_docs = {e["doc"] for e in errors["C_full"]["missed"]}
    clean = [f"discharge_summary_en_{k:02d}" for k in range(6) if f"discharge_summary_en_{k:02d}" not in missed_docs]
    ctx = dict(cfg=cfg, m=m, lat=lat, cats=cats, triptych=triptych(clean[0] if clean else "discharge_summary_en_00"),
               error_notes=error_notes(errors), ex=quasi_example(errors),
               policy_yaml=(ROOT / "policies" / "research.yaml").read_text(encoding="utf-8").strip())
    body = "".join(env.get_template(t).render(**ctx) for t in ("slides_a.html.j2", "slides_b.html.j2", "slides_c.html.j2"))
    html = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>RedactAgent - Stage I proposal</title>'
            f'<link rel="stylesheet" href="deck.css"></head><body>{body}</body></html>')
    (DECK / "deck.html").write_text(html, encoding="utf-8")
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                    f"--print-to-pdf={out_pdf}", (DECK / "deck.html").as_uri()], check=True, capture_output=True)
    print(f"wrote {out_pdf}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT.parent / "deliverables" / "RedactAgent_proposal.pdf"))
    ap.add_argument("--results", default=str(RESULTS))
    a = ap.parse_args()
    RESULTS = Path(a.results)
    build(Path(a.out))
