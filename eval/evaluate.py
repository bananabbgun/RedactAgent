"""Evaluate RedactAgent on the synthetic corpus with pixel-level ground truth.

Runs the full pipeline once per document (strict policy), stores raw findings, then
computes an ablation by filtering findings by the layer that produced them:

  A  deterministic   rules + colour seal check            (what a regex/DLP tool can do)
  B  + LLM           adds contextual detection (Qwen3-8B)
  C  + VLM           adds visual grounding (Qwen2.5-VL-7B)  = RedactAgent

Metrics
  recall     GT item counts as caught if >= 50 % of its box area is covered by redaction boxes
  precision  a redaction box is correct if >= 30 % of its area overlaps ground-truth PII
  clean docs share of documents with zero leaked PII items

    python eval/evaluate.py                # full run (~20 s/page on an M-series laptop)
    python eval/evaluate.py --reuse        # recompute metrics from saved raw findings
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from redactagent.pipeline import Pipeline  # noqa: E402
from redactagent.schema import CATEGORIES  # noqa: E402

DATA = ROOT / "data" / "synthetic"
OUT = ROOT / "eval" / "results"
ABLATIONS = {
    "A_deterministic": {"rule", "cv"},
    "B_plus_llm": {"rule", "cv", "llm"},
    "C_full": {"rule", "cv", "llm", "vlm"},
}


def mask_of(boxes, w, h):
    m = np.zeros((h, w), dtype=bool)
    for x0, y0, x1, y1 in boxes:
        m[max(0, int(y0)):max(0, int(y1)), max(0, int(x0)):max(0, int(x1))] = True
    return m


def score_doc(gt: dict, findings: list[dict], allowed: set[str]):
    w, h = gt["width"], gt["height"]
    pred = [f for f in findings if set(f["sources"]) & allowed]
    pmask = mask_of([f["bbox"] for f in pred], w, h)
    gmask = mask_of([it["bbox"] for it in gt["items"]], w, h)
    caught = []
    for it in gt["items"]:
        x0, y0, x1, y1 = it["bbox"]
        area = max(1, (x1 - x0) * (y1 - y0))
        cov = pmask[y0:y1, x0:x1].sum() / area
        caught.append((it["cat"], bool(cov >= 0.5), it["text"]))
    tp_boxes = 0
    fps = []
    for f in pred:
        x0, y0, x1, y1 = [max(0, v) for v in f["bbox"]]
        area = max(1, (x1 - x0) * (y1 - y0))
        if gmask[y0:y1, x0:x1].sum() / area >= 0.3:
            tp_boxes += 1
        else:
            fps.append((f["category"], f["text"], f["sources"]))
    return caught, tp_boxes, len(pred), fps


def run_corpus(limit: int | None):
    """Two phases so that only one model is resident at a time (laptop memory):
    phase 1 = OCR + rules + LLM for every page, phase 2 = VLM for every page."""
    from PIL import Image

    from redactagent.detectors import vision as vis_det

    pipe = Pipeline()
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    index = json.loads((DATA / "index.json").read_text())
    if limit:
        index = index[:limit]
    for k, doc in enumerate(index, 1):
        raw = OUT / "raw" / f"{doc['id']}.json"
        if raw.exists():
            continue
        data = (DATA / "images" / f"{doc['id']}.jpg").read_bytes()
        job = pipe.new_job(f"{doc['id']}.jpg", "strict", layers=("rules", "llm"))
        t = time.perf_counter()
        pipe.run(job, data)
        if job.status != "done":
            print(f"[{k}/{len(index)}] {doc['id']} ERROR {job.error}")
            continue
        timings = {k2: v for k2, v in job.timings.items() if k2 not in ("vlm", "total")}
        raw.write_text(json.dumps({"timings": timings, "tokens": job.tokens, "doc_type": job.doc_type,
                                   "findings": [f.to_dict() for f in job.findings], "vlm_done": False}, ensure_ascii=False))
        print(f"[{k}/{len(index)}] {doc['id']}: {len(job.findings)} findings, LLM {job.timings.get('llm', 0):.1f}s", flush=True)
    for k, doc in enumerate(index, 1):
        raw = OUT / "raw" / f"{doc['id']}.json"
        if not raw.exists():
            continue
        r = json.loads(raw.read_text())
        if r.get("vlm_done"):
            continue
        img = Image.open(DATA / "images" / f"{doc['id']}.jpg").convert("RGB")
        t = time.perf_counter()
        vhits, _ = vis_det.detect(img, pipe.vision_client)
        r["timings"]["vlm"] = time.perf_counter() - t
        r["timings"]["total"] = sum(v for k2, v in r["timings"].items() if k2 != "total")
        r["findings"] = [f for f in r["findings"] if f["sources"] != ["cv"]]  # replaced by fused visual results
        for i, h in enumerate(vhits):
            r["findings"].append({"id": f"v{i}", "page": 0, "category": h.category, "text": h.category.lower(),
                                  "bbox": h.bbox, "sources": h.source.split("+"), "confidence": h.confidence,
                                  "role": None, "reason": h.reason})
        r["vlm_done"] = True
        raw.write_text(json.dumps(r, ensure_ascii=False))
        print(f"[VLM {k}/{len(index)}] {doc['id']}: {len(vhits)} visual hits in {r['timings']['vlm']:.1f}s", flush=True)


def metrics():
    index = json.loads((DATA / "index.json").read_text())
    results = {}
    lat = {"ocr": [], "rules": [], "llm": [], "vlm": [], "total": []}
    tok = []
    errors = {}
    for name, allowed in ABLATIONS.items():
        per_cat: dict[str, list[int]] = {c: [0, 0] for c in CATEGORIES}
        tp = npred = 0
        clean = ndocs = 0
        misses = []
        fps_all = []
        for doc in index:
            raw = OUT / "raw" / f"{doc['id']}.json"
            if not raw.exists():
                continue
            r = json.loads(raw.read_text())
            gt = json.loads((DATA / "gt" / f"{doc['id']}.json").read_text())
            caught, t, n, fps = score_doc(gt, r["findings"], allowed)
            ndocs += 1
            clean += all(c for _, c, _ in caught)
            for cat, ok, text in caught:
                per_cat[cat][1] += 1
                per_cat[cat][0] += ok
                if not ok:
                    misses.append({"doc": doc["id"], "cat": cat, "text": text})
            tp += t
            npred += n
            fps_all += [{"doc": doc["id"], "cat": c, "text": x, "sources": s} for c, x, s in fps]
            if name == "C_full":
                for k in lat:
                    lat[k].append(r["timings"].get(k, 0.0))
                tok.append(r["tokens"].get("llm_completion", 0))
        total_ok = sum(v[0] for v in per_cat.values())
        total = sum(v[1] for v in per_cat.values())
        results[name] = {
            "docs": ndocs, "gt_items": total, "caught": total_ok, "recall": total_ok / max(1, total),
            "precision": tp / max(1, npred), "redaction_boxes": npred, "clean_doc_rate": clean / max(1, ndocs),
            "recall_by_category": {c: (v[0] / v[1] if v[1] else None) for c, v in per_cat.items()},
            "support_by_category": {c: v[1] for c, v in per_cat.items()},
        }
        errors[name] = {"missed": misses, "false_positives": fps_all}
    results["latency_seconds_per_page"] = {k: {"mean": statistics.mean(v), "p50": statistics.median(v), "max": max(v)}
                                           for k, v in lat.items() if v}
    results["llm_completion_tokens_mean"] = statistics.mean(tok) if tok else 0
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "metrics.json").write_text(json.dumps(results, indent=1, ensure_ascii=False))
    (OUT / "errors.json").write_text(json.dumps(errors, indent=1, ensure_ascii=False))
    write_markdown(results)
    plot(results)
    return results


def write_markdown(r):
    lines = ["# Evaluation results", "",
             f"Synthetic corpus: {r['C_full']['docs']} scanned pages, {r['C_full']['gt_items']} ground-truth PII items "
             "(6 templates, English + Traditional Chinese). Policy: strict.", "",
             "| Configuration | Recall | Precision | Clean pages |", "|---|---|---|---|"]
    names = {"A_deterministic": "A. Rules + colour (regex/DLP baseline)", "B_plus_llm": "B. + contextual LLM",
             "C_full": "C. + VLM (RedactAgent)"}
    for k, label in names.items():
        x = r[k]
        lines.append(f"| {label} | {x['recall']:.1%} | {x['precision']:.1%} | {x['clean_doc_rate']:.1%} |")
    lines += ["", "## Recall by category", "", "| Category | n | A | B | C |", "|---|---|---|---|---|"]
    for c in CATEGORIES:
        n = r["C_full"]["support_by_category"][c]
        if not n:
            continue
        vals = [r[k]["recall_by_category"][c] for k in names]
        lines.append(f"| {CATEGORIES[c][0]} | {n} | " + " | ".join(f"{v:.0%}" for v in vals) + " |")
    lat = r["latency_seconds_per_page"]
    lines += ["", "## Latency per page (Apple M5 laptop, 24 GB, Ollama)", "", "| Stage | mean | p50 | max |", "|---|---|---|---|"]
    for k in ("ocr", "rules", "llm", "vlm", "total"):
        if k in lat:
            lines.append(f"| {k} | {lat[k]['mean']:.2f} s | {lat[k]['p50']:.2f} s | {lat[k]['max']:.2f} s |")
    (OUT / "RESULTS.md").write_text("\n".join(lines) + "\n")


def plot(r):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    img = ROOT / "docs" / "img"
    img.mkdir(parents=True, exist_ok=True)
    cats = [c for c in CATEGORIES if r["C_full"]["support_by_category"][c]]
    labels = [CATEGORIES[c][0] for c in cats]
    y = np.arange(len(cats))
    fig, ax = plt.subplots(figsize=(8, 6.2), dpi=160)
    colors = {"A_deterministic": "#9aa5b8", "B_plus_llm": "#7c3aed", "C_full": "#1f3a8a"}
    names = {"A_deterministic": "Rules + colour", "B_plus_llm": "+ LLM", "C_full": "+ VLM (full)"}
    for i, k in enumerate(["A_deterministic", "B_plus_llm", "C_full"]):
        vals = [r[k]["recall_by_category"][c] * 100 for c in cats]
        ax.barh(y + (i - 1) * 0.27, vals, height=0.26, color=colors[k], label=names[k])
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 105)
    ax.set_xlabel("Recall (%)")
    ax.legend(loc="lower right", frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(img / "recall_by_category.png", transparent=False)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reuse", action="store_true")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    if not args.reuse:
        run_corpus(args.limit)
    res = metrics()
    for k in ABLATIONS:
        x = res[k]
        print(f"{k:16s} recall {x['recall']:.3f}  precision {x['precision']:.3f}  clean {x['clean_doc_rate']:.3f}")
