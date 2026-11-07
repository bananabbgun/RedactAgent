"""Score the manual vs. AI-assisted redaction study (web page: /study).

Each participant redacts the same six synthetic pages; half are done by hand, half start from
RedactAgent's suggestions (counterbalanced by participant number). Boxes are scored against the
pixel-level ground truth with the same rule as eval/evaluate.py (an item counts as redacted when
>= 50 % of its area is covered).

    python eval/study_score.py runs/study/*.json
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.evaluate import mask_of  # noqa: E402

TASKS = {t["id"]: t for t in json.loads((ROOT / "study" / "tasks.json").read_text())["tasks"]}


def score(doc_id: str, boxes: list[list[int]]) -> tuple[float, float]:
    gt_path = ROOT / Path(TASKS[doc_id]["image"]).parent.parent / "gt" / f"{doc_id}.json"
    gt = json.loads(gt_path.read_text())
    w, h = gt["width"], gt["height"]
    pmask = mask_of(boxes, w, h)
    gmask = mask_of([it["bbox"] for it in gt["items"]], w, h)
    caught = 0
    for it in gt["items"]:
        x0, y0, x1, y1 = it["bbox"]
        caught += pmask[y0:y1, x0:x1].sum() / max(1, (x1 - x0) * (y1 - y0)) >= 0.5
    good = 0
    for x0, y0, x1, y1 in boxes:
        x0, y0 = max(0, x0), max(0, y0)
        good += gmask[y0:y1, x0:x1].sum() / max(1, (x1 - x0) * (y1 - y0)) >= 0.3
    return caught / max(1, len(gt["items"])), good / max(1, len(boxes))


def main(paths: list[str]):
    tasks = TASKS
    rows = {"manual": [], "assisted": []}
    for p in paths:
        r = json.loads(Path(p).read_text())
        for page in r["pages"]:
            rec, prec = score(page["id"], page["boxes"])
            rows[page["mode"]].append({"who": r["participant"], "doc": page["id"], "s": page["seconds"], "recall": rec,
                                       "precision": prec})
    ai = [score(d, [b[:4] for b in t["suggested"]]) for d, t in tasks.items()]
    print(f"participants: {len(paths)}")
    print("| Condition | pages | time / page (mean) | time / page (median) | recall | precision |")
    print("|---|---|---|---|---|---|")
    for mode, xs in rows.items():
        if xs:
            print(f"| {mode} | {len(xs)} | {statistics.mean(x['s'] for x in xs):.0f} s | {statistics.median(x['s'] for x in xs):.0f} s | "
                  f"{statistics.mean(x['recall'] for x in xs):.1%} | {statistics.mean(x['precision'] for x in xs):.1%} |")
    print(f"| AI suggestions alone (no human) | {len(ai)} | - | - | {statistics.mean(a[0] for a in ai):.1%} | "
          f"{statistics.mean(a[1] for a in ai):.1%} |")
    out = ROOT / "eval" / "results_b70" / "study.json"
    out.write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
