"""Throughput / latency / power benchmark on the Arc Pro B70 (or any vLLM backend).

For each concurrency level, N pages are pushed through the full pipeline while
`xpu-smi dump` samples GPU utilisation, power and memory on every card once per second.

    RA_BACKEND=openai RA_BASE_URL=http://localhost:8000 RA_VISION_BASE_URL=http://localhost:8001 \
    RA_TEXT_MODEL=text RA_VISION_MODEL=vision \
    python eval/benchmark.py --pages 36 --levels 1,2,4,8,16 --out eval/results_b70/bench
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import shutil
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from redactagent.pipeline import Pipeline  # noqa: E402

DATA = ROOT / "data" / "synthetic"
METRICS = "0,1,18"  # utilization.gpu %, power.draw W, memory.used MiB


class GpuSampler:
    """One background `xpu-smi dump` per card (long-form flags; this xpu-smi rejects -m/-i)."""

    def __init__(self, devices=("0", "1")):
        self.devices = devices
        self.procs: dict[str, subprocess.Popen] = {}
        self.available = shutil.which("xpu-smi") is not None

    def __enter__(self):
        if self.available:
            for d in self.devices:
                self.procs[d] = subprocess.Popen(
                    ["xpu-smi", "dump", "--device", d, "--metrics", METRICS, "--interval", "1"],
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        return self

    def __exit__(self, *exc):
        self.rows = {}
        for d, p in self.procs.items():
            p.kill()  # xpu-smi ignores SIGTERM
            out, _ = p.communicate()
            self.rows[d] = list(csv.reader(io.StringIO(out)))
        return False

    def summary(self) -> dict:
        """{device: {"util": mean %, "power": mean W, "mem": max MiB}} with columns matched by keyword."""
        out = {}
        for d, rows in getattr(self, "rows", {}).items():
            if len(rows) < 2:
                continue
            header = [h.strip().lower() for h in rows[0]]
            pick = {"util": "util", "power": "power", "mem": "memory"}
            cols = {k: next((i for i, h in enumerate(header) if kw in h), None) for k, kw in pick.items()}
            vals: dict[str, list[float]] = {k: [] for k in pick}
            for row in rows[1:]:
                for k, i in cols.items():
                    try:
                        vals[k].append(float(row[i]))
                    except (TypeError, ValueError, IndexError):
                        pass
            out[d] = {"util_mean": statistics.mean(vals["util"]) if vals["util"] else None,
                      "power_mean_w": statistics.mean(vals["power"]) if vals["power"] else None,
                      "mem_max_mib": max(vals["mem"]) if vals["mem"] else None,
                      "header": rows[0]}
        return out


def pctl(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def run_level(pipe: Pipeline, docs: list[Path], conc: int) -> dict:
    lat: list[float] = []

    def one(path: Path):
        job = pipe.new_job(path.name, "strict")
        t = time.perf_counter()
        pipe.run(job, path.read_bytes())
        lat.append(time.perf_counter() - t)
        return job.status

    with GpuSampler() as gpu:
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=conc) as ex:
            statuses = list(ex.map(one, docs))
        wall = time.perf_counter() - t0
    g = gpu.summary()
    power = sum(d["power_mean_w"] or 0 for d in g.values()) if g else None
    done = sum(s == "done" for s in statuses)  # failed pages do not count as throughput
    res = {
        "concurrency": conc, "pages": done, "errors": len(docs) - done,
        "wall_s": wall, "pages_per_min": done / wall * 60,
        "latency_p50_s": pctl(lat, 50), "latency_p95_s": pctl(lat, 95), "gpu": g,
    }
    if power:
        res["power_w_total"] = power
        res["energy_j_per_page"] = power * wall / max(1, done)
        res["pages_per_kwh"] = 3.6e6 / res["energy_j_per_page"]
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=36)
    ap.add_argument("--levels", default="1,2,4,8,16")
    ap.add_argument("--out", default=str(ROOT / "eval" / "results_b70" / "bench"))
    ap.add_argument("--warmup", type=int, default=2)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    imgs = sorted((DATA / "images").glob("*.jpg"))
    docs = [imgs[i % len(imgs)] for i in range(a.pages)]
    pipe = Pipeline()
    for p in imgs[: a.warmup]:  # load kernels / caches before measuring
        pipe.run(pipe.new_job(p.name, "strict"), p.read_bytes())
    results = []
    for conc in [int(x) for x in a.levels.split(",")]:
        r = run_level(pipe, docs, conc)
        results.append(r)
        print(f"c={conc:3d}  {r['pages_per_min']:7.1f} pages/min  p50 {r['latency_p50_s']:5.1f}s  "
              f"p95 {r['latency_p95_s']:5.1f}s  power {r.get('power_w_total', 0):.0f} W  errors {r['errors']}", flush=True)
        (out / "benchmark.json").write_text(json.dumps(results, indent=1))
    lines = ["| Concurrent pages | Pages / min | Latency p50 | Latency p95 | GPU power (both cards) | Pages / kWh |",
             "|---|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['concurrency']} | {r['pages_per_min']:.1f} | {r['latency_p50_s']:.1f} s | {r['latency_p95_s']:.1f} s | "
                     f"{r.get('power_w_total', 0):.0f} W | {r.get('pages_per_kwh', 0):,.0f} |")
    (out / "BENCHMARK.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
