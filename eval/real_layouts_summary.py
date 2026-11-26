"""Summarise the real-layout check (data/real_layouts/): per form, per language, and the review-triage signal.

    python eval/real_layouts_summary.py   # writes eval/results_b70/real_layouts/summary.json

Uses the stored raw findings of the single evaluation run; nothing is re-run. Triage rule as in the deck and
eval/triage.py (fixed on v1+v2 development data): re-identification risk >= 70 or ink the OCR did not read.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
from evaluate import ABLATIONS, score_doc  # noqa: E402

RUN = ROOT / "eval" / "results_b70" / "real_layouts"
CORPUS = ROOT / "data" / "real_layouts" / "corpus"
NAMES = {"nhi_referral_zh": "NHI referral form (MOHW)", "nhi_card_zh": "NHI card application (NHIA)",
         "va_release_p1_en": "VA Form 10-5345, page 1", "va_release_p2_en": "VA Form 10-5345, page 2",
         "cms1500_en": "CMS-1500 claim form (SAMPLE watermark)"}


def main():
    allowed = ABLATIONS["D_agentic"]
    rows: dict[str, dict] = {}
    tri = {"pages": 0, "flagged": 0, "missed": 0, "missed_flagged": 0}
    for g in sorted((CORPUS / "gt").glob("*.json")):
        gt = json.loads(g.read_text())
        r = json.loads((RUN / "raw" / g.name).read_text())
        caught, tp, npred, _ = score_doc(gt, r["findings"], allowed)
        missed = sum(not c[1] for c in caught)
        for key in (gt["template"], "lang_" + gt["lang"], "all"):
            s = rows.setdefault(key, {"pages": 0, "items": 0, "caught": 0, "tp": 0, "pred": 0, "clean": 0})
            s["pages"] += 1; s["items"] += len(caught); s["caught"] += len(caught) - missed
            s["tp"] += tp; s["pred"] += npred; s["clean"] += missed == 0
        risk = (r.get("risk") or {}).get("residual", (r.get("risk") or {}).get("score", 0)) or 0
        flagged = risk >= 70 or len(r.get("warnings") or []) > 0
        tri["pages"] += 1; tri["flagged"] += flagged; tri["missed"] += missed; tri["missed_flagged"] += missed * flagged
    out = {"forms": [], "triage": tri}
    for key, s in rows.items():
        s.update(recall=s["caught"] / s["items"], precision=s["tp"] / max(1, s["pred"]), clean_pages=s["clean"] / s["pages"])
        if key in NAMES:
            out["forms"].append({"id": key, "name": NAMES[key], **s})
        else:
            out[key] = s
    out["forms"].sort(key=lambda f: list(NAMES).index(f["id"]))
    (RUN / "summary.json").write_text(json.dumps(out, indent=1))
    for f in out["forms"] + [dict(name=k, **out[k]) for k in ("lang_zh", "lang_en", "all")]:
        print(f"{f['name']:40s} {f['pages']:2d} pages {f['items']:3d} items  recall {f['recall']:.1%}  precision {f['precision']:.1%}")
    print(f"triage: {tri['flagged']}/{tri['pages']} pages flagged, holding {tri['missed_flagged']}/{tri['missed']} missed items")


if __name__ == "__main__":
    main()
