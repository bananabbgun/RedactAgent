"""Build study/tasks.json (pages and RedactAgent suggestions for the /study page) from an evaluation run.

The suggestions are exactly what the full pipeline (rules + LLM + VLM + accepted agentic findings) proposed
for each page in that run, so the "assisted" condition shows participants the real system output.

    python scripts/make_study_tasks.py --source eval/results_b70/v3
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# six pages from the untouched final corpus (v3), so the suggestions are not tuned on these documents.
# Each half (manual / assisted, counterbalanced) has 2 English + 1 Chinese page and both capture styles.
CORPUS = "data/synthetic_v3"
DOCS = ["lab_report_en_02", "court_judgment_zh_01", "referral_letter_en_02",          # scan, phone, scan
        "prescription_label_zh_03", "bank_statement_en_02", "referral_letter_en_05"]  # phone, scan, phone


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="evaluation output directory with raw/<doc>.json")
    ap.add_argument("--out", default=str(ROOT / "study" / "tasks.json"))
    a = ap.parse_args()
    src = Path(a.source)
    tasks = []
    for doc in DOCS:
        raw = json.loads((src / "raw" / f"{doc}.json").read_text())
        sugg = [[*f["bbox"], f["category"]] for f in raw["findings"] if f.get("accepted", True)]
        tasks.append({"id": doc, "image": f"{CORPUS}/images/{doc}.jpg", "suggested": sugg})
    rel = src.resolve().relative_to(ROOT) if src.resolve().is_relative_to(ROOT) else src
    Path(a.out).write_text(json.dumps({"source": str(rel), "tasks": tasks}, indent=1))
    print(f"wrote {a.out}: {sum(len(t['suggested']) for t in tasks)} suggested boxes on {len(tasks)} pages")


if __name__ == "__main__":
    main()
