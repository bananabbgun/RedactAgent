"""Build the final (Stage II) deck: HTML -> PDF via headless Chrome.

    python deck/build_final.py [--out ../deliverables/RedactAgent_final.pdf]

Every number on the results slides is read from files produced on the 2x Arc Pro B70 host:
    eval/results_b70/{v1,v2,v3}/metrics.json   final configuration, three corpora
    eval/results_b70/bench/benchmark.json      concurrency sweep with GPU power
    eval/tune3/<config>/<corpus>/              text-model selection sweep
    eval/results_b70/study.json                user study (optional; slide hidden until it exists)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
DECK = ROOT / "deck"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DECK))

import build_deck  # noqa: E402  (Stage I helpers: policy triptych)
from redactagent.schema import CATEGORIES  # noqa: E402

CHROME = build_deck.CHROME
B70 = ROOT / "eval" / "results_b70"

# Stage II baseline sweep (2026-11-06, Qwen3-8B BF16, OCR threads unrestricted) - eval/results_b70/bench_v1/BENCHMARK.md
BENCH0 = [{"c": 1, "ppm": 5.8, "w": 301}, {"c": 4, "ppm": 18.6, "w": 343}, {"c": 8, "ppm": 21.3, "w": 307},
          {"c": 16, "ppm": 22.0, "w": 263}, {"c": 32, "ppm": 15.7, "w": 218}]

TUNE_LABELS = {
    "T2_qwen3-8b-fp8": ("Qwen3-8B", "FP8 (online)"),
    "T3_qwen3-14b-fp8": ("Qwen3-14B", "FP8 (online)"),
    "T4_qwen3-30b-a3b-gptq": ("Qwen3-30B-A3B (MoE)", "GPTQ INT4"),
    "T5b_gpt-oss-20b-low": ("gpt-oss-20b (MoE)", "MXFP4, reasoning low"),
}


def load(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def tune_rows() -> list[dict]:
    rows = []
    for tid, (name, prec) in TUNE_LABELS.items():
        d = ROOT / "eval" / "tune3" / tid
        m1, m2 = load(d / "synthetic" / "metrics.json"), load(d / "synthetic_v2" / "metrics.json")
        t1, t2 = load(d / "synthetic" / "throughput.json"), load(d / "synthetic_v2" / "throughput.json")
        if not (m1 and m2 and t1 and t2):
            continue
        rows.append({"id": tid, "name": name, "prec": prec,
                     "ppm": (t1["pages"] + t2["pages"]) / (t1["wall_seconds"] + t2["wall_seconds"]) * 60,
                     "v1r": m1["D_agentic"]["recall"], "v1p": m1["D_agentic"]["precision"],
                     "v2cr": m2["C_full"]["recall"], "v2cp": m2["C_full"]["precision"],
                     "v2r": m2["D_agentic"]["recall"], "v2p": m2["D_agentic"]["precision"],
                     "failed": m1["D_agentic"].get("failed_docs", 0) + m2["D_agentic"].get("failed_docs", 0)})
    return rows


def renumber(body: str) -> str:
    """Page numbers in slide footers follow slide order, so slides can be inserted or hidden freely."""
    import re

    parts = re.split(r'(?=<section class="slide)', body)
    for i, sec in enumerate(parts[1:], 1):
        parts[i] = re.sub(r'(<div class="foot">.*?<span>[^<]*</span>\s*<span>)[^<]*(</span>\s*</div>)',
                          lambda m: f"{m.group(1)}{i}{m.group(2)}", sec, count=1, flags=re.S)
    return "".join(parts)


def build(out_pdf: Path):
    cfg = yaml.safe_load((DECK / "config.yaml").read_text(encoding="utf-8"))
    fin = {v: load(B70 / v / "metrics.json") for v in ("v1", "v2", "v3")}
    thr = {v: load(B70 / v / "throughput.json") for v in ("v1", "v2", "v3")}
    missing = [v for v, m in fin.items() if m is None]
    if missing:
        sys.exit(f"final results missing for {missing}: run the final evaluation first")
    fast = {v: load(B70 / "fast" / v / "metrics.json") for v in ("v1", "v2", "v3")}
    fast_thr = {v: load(B70 / "fast" / v / "throughput.json") for v in ("v1", "v2", "v3")}
    fast_bench = load(B70 / "fast" / "bench" / "benchmark.json") or []
    bench = load(B70 / "bench" / "benchmark.json") or []
    robust = load(ROOT / "eval" / "robustness" / "summary.json") or []
    tri = load(ROOT / "eval" / "triage" / "triage_rules.json")
    triage = None
    if tri:  # pre-chosen rule: risk score >= 70 or ink the OCR did not read (decided on v1+v2 development data)
        r = next((r for r in tri["rules"] if list(r["params"]) == [70, True, False, False]), None)
        if r:
            triage = {"flagged": r["flagged"] / r["pages"], "caught": r["missed_in_flagged"] / r["missed_items"],
                      "pages": r["pages"], "missed": r["missed_items"]}
    best = max(bench, key=lambda r: r["pages_per_min"]) if bench else None
    v3 = fin["v3"]
    cats = []
    for c in CATEGORIES:
        n = v3["D_agentic"]["support_by_category"].get(c, 0)
        if n:
            cats.append({"name": CATEGORIES[c][0], "n": n, "A": v3["A_deterministic"]["recall_by_category"][c],
                         "D": v3["D_agentic"]["recall_by_category"][c]})
    build_deck.RESULTS = B70 / "v1"
    ctx = dict(robust=robust, robust_min=min((r["D"] for r in robust), default=None), triage=triage, cfg=cfg, fin=fin, thr=thr, fast=fast, fast_thr=fast_thr, fast_bench=fast_bench,
               fast_best=max(fast_bench, key=lambda r: r["pages_per_min"]) if fast_bench else None, bench=bench, bench0=BENCH0, best=best, cats=cats, tune=tune_rows(),
               study=load(B70 / "study_summary.json"), triptych=build_deck.triptych("discharge_summary_en_00"),
               final=cfg.get("final_model", {}))
    env = Environment(loader=FileSystemLoader(DECK), autoescape=False)
    body = "".join(env.get_template(t).render(**ctx) for t in ("final_a.html.j2", "final_b.html.j2", "final_c.html.j2"))
    body = renumber(body)
    html = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>RedactAgent - Final</title>'
            f'<link rel="stylesheet" href="deck.css"></head><body>{body}</body></html>')
    (DECK / "final.html").write_text(html, encoding="utf-8")
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    if Path(CHROME).exists():
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                        f"--print-to-pdf={out_pdf}", (DECK / "final.html").as_uri()], check=True, capture_output=True)
    else:  # e.g. on the B70 host: Playwright's Chromium
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(args=["--allow-file-access-from-files"])
            page = b.new_page(viewport={"width": 1280, "height": 720})
            page.goto((DECK / "final.html").as_uri(), wait_until="networkidle")
            page.pdf(path=str(out_pdf), width="1280px", height="720px", print_background=True)
            b.close()
    print(f"wrote {out_pdf}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT.parent / "deliverables" / "RedactAgent_final.pdf"))
    build(Path(ap.parse_args().out))
