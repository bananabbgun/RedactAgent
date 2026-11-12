"""Accuracy on hospital documents only (the beachhead), per corpus and per document type.

    python eval/subset.py                       # final run 3 (eval/results_b70/{v1,v2,v3})
    python eval/subset.py --json eval/results_b70/hospital_subset.json

Re-scores the stored raw findings with the same pixel-level rules as eval/evaluate.py (no model calls).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
from evaluate import ABLATIONS, score_doc  # noqa: E402

HOSPITAL = ("discharge_summary", "medical_certificate", "lab_report", "referral_letter", "prescription_label")
CORPORA = {"v1": "synthetic", "v2": "synthetic_v2", "v3": "synthetic_v3"}


def score(run: Path, corpus: Path, keep) -> dict:
    out = {}
    index = [d for d in json.loads((corpus / "index.json").read_text()) if keep(d)]
    for name in ("A_deterministic", "C_full", "D_agentic"):
        caught = items = tp = pred = clean = pages = 0
        for d in index:
            raw = run / "raw" / f"{d['id']}.json"
            gt = json.loads((corpus / "gt" / f"{d['id']}.json").read_text())
            findings = json.loads(raw.read_text())["findings"] if raw.exists() else []  # failed page = fully leaked
            c, t, n, _ = score_doc(gt, findings, ABLATIONS[name])
            hit = sum(1 for x in c if x[1])
            caught, items, tp, pred = caught + hit, items + len(c), tp + t, pred + n
            clean, pages = clean + (hit == len(c)), pages + 1
        out[name] = {"recall": caught / items, "precision": tp / pred if pred else 0, "clean_pages": clean / pages,
                     "pages": pages, "items": items}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(ROOT / "eval" / "results_b70"))
    ap.add_argument("--json")
    a = ap.parse_args()
    res = {}
    for v, c in CORPORA.items():
        run, corpus = Path(a.runs) / v, ROOT / "data" / c
        if not run.exists():
            continue
        types = sorted({d["template"] for d in json.loads((corpus / "index.json").read_text()) if d["id"].startswith(HOSPITAL)})
        res[v] = {"hospital": score(run, corpus, lambda d: d["id"].startswith(HOSPITAL)),
                  "other": score(run, corpus, lambda d: not d["id"].startswith(HOSPITAL)),
                  "types": {t: score(run, corpus, lambda d, t=t: d["template"] == t)["D_agentic"] for t in types}}
        for grp in ("hospital", "other"):
            r = res[v][grp]
            print(f"{v} {grp:8s} pages {r['D_agentic']['pages']:2d} items {r['D_agentic']['items']:3d} | rules {r['A_deterministic']['recall']*100:5.1f}"
                  f" | full {r['D_agentic']['recall']*100:5.1f} / {r['D_agentic']['precision']*100:5.1f}, clean {r['D_agentic']['clean_pages']*100:3.0f} %")
        for t, r in res[v]["types"].items():
            print(f"     {t:24s} {r['recall']*100:5.1f} / {r['precision']*100:5.1f}  ({r['pages']} pages)")
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
