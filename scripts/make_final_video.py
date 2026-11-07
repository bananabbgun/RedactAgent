"""Assemble the final (Stage II) video, <= 10 min, English narration with burned-in captions.

Inputs in --work (recorded on the organiser's 2x Arc Pro B70 instance):
    terminal_raw.webm + terminal_marks.json   scripts/record_terminal.py (real JupyterLab terminal)
    demo_b70_raw.webm + marks.json            scripts/record_b70.py (the web app)
Slides are rendered from deck/final.html (run deck/build_final.py first); narration text is
scripts/final_narration.yaml with {placeholders} filled from eval/results_b70/.

    python scripts/make_final_video.py --work ../deliverables/final_video --out ../deliverables/RedactAgent_final.mp4
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from make_video import FPS, ROOT, duration, narrate_demo, sh, synth  # Stage I helpers

B70 = ROOT / "eval" / "results_b70"


def spoken_pct(x: float) -> str:
    whole, frac = f"{x:.1f}".split(".")
    return f"{whole} point {frac} percent" if frac != "0" else f"{whole} percent"


def spoken_num(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ")  # Kokoro reads "1 480" naturally; captions keep the comma form


def numbers() -> dict[str, str]:
    m = {v: json.loads((B70 / v / "metrics.json").read_text())["D_agentic"] for v in ("v1", "v2", "v3")}
    bench = json.loads((B70 / "bench" / "benchmark.json").read_text())
    best = max(bench, key=lambda r: r["pages_per_min"])
    out = {}
    for v in ("v1", "v2", "v3"):
        out[f"{v}_recall"] = f"{m[v]['recall'] * 100:.1f}%"
        out[f"{v}_recall_spoken"] = spoken_pct(m[v]["recall"] * 100)
        out[f"{v}_precision"] = f"{m[v]['precision'] * 100:.1f}%"
        out[f"{v}_precision_spoken"] = spoken_pct(m[v]["precision"] * 100)
    live = json.loads((B70 / "video_v3_live" / "take2" / "metrics.json").read_text())["D_agentic"]
    out["live_recall"], out["live_recall_spoken"] = f"{live['recall'] * 100:.1f}%", spoken_pct(live["recall"] * 100)
    out["live_precision"], out["live_precision_spoken"] = f"{live['precision'] * 100:.1f}%", spoken_pct(live["precision"] * 100)
    b8 = next(r for r in bench if r["concurrency"] == 8)  # the batch on screen runs 8 pages in flight
    out["batch_ppm"] = out["batch_ppm_spoken"] = f"{b8['pages_per_min']:.0f}"
    ph = round(best["pages_per_min"] * 60, -1)
    out["pages_hour"] = f"{ph:,.0f}"
    out["pages_hour_spoken"] = spoken_num(ph)
    return out


def narration(nums: dict[str, str]) -> dict[str, list[tuple[str, str]]]:
    raw = yaml.safe_load((ROOT / "scripts" / "final_narration.yaml").read_text(encoding="utf-8"))
    out = {}
    for key, chunks in raw.items():
        out[key] = [(c[0].format(**nums), (c[1] if len(c) > 1 else c[0]).format(**nums)) for c in chunks]
    return out


def render_slides(out_dir: Path) -> dict[int, Path]:
    """Screenshot every slide of deck/final.html at 1920x1080."""
    from playwright.sync_api import sync_playwright

    pngs = {}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", args=["--allow-file-access-from-files"])
        pg = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1.5)
        pg.goto((ROOT / "deck" / "final.html").as_uri(), wait_until="networkidle")
        for i, el in enumerate(pg.query_selector_all(".slide"), 1):
            pngs[i] = out_dir / f"slide_{i:02d}.png"
            el.screenshot(path=str(pngs[i]))
        b.close()
    return pngs


def find_slide(pngs: dict[int, Path], html: str, title: str) -> Path:
    """Locate a slide by (part of) its <h1>, so the cut survives slides being added or reordered."""
    import re

    titles = re.findall(r"<h1[^>]*>(.*?)</h1>", html, flags=re.S)
    for i, t in enumerate(titles, 1):
        if title.lower() in re.sub(r"<[^>]+>|&\w+;", " ", t).lower():
            return pngs[i]
    raise KeyError(title)


def still(png: Path, seconds: float, out: Path):
    sh(["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(png), "-t", f"{seconds:.2f}",
        "-vf", f"scale=1920:1080,fps={FPS},format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20", str(out)])


def concat_video(parts: list[Path], out: Path):
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", f"fps={FPS},format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-an", str(out)])


def label_png(text: str, out: Path):
    from PIL import Image, ImageDraw, ImageFont

    fnt = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 26)
    w = int(fnt.getlength(text)) + 36
    im = Image.new("RGBA", (w, 52), (31, 58, 138, 220))
    ImageDraw.Draw(im).text((18, 12), text, font=fnt, fill=(255, 255, 255, 255))
    im.save(out)


def cut(raw: Path, plan: list[tuple[float, float, float | None]], out: Path, work: Path, tag: str):
    """Concatenate spans of a recording; a span with a target length is sped up and labelled.
    Returns a function mapping raw time -> edited time."""
    parts, labels, inputs, n_in = [], [], ["-i", str(raw)], 1
    for i, (s, e, tgt) in enumerate(plan):
        if tgt is None:
            parts.append(f"[0:v]trim=start={s:.2f}:end={e:.2f},setpts=PTS-STARTPTS,scale=1920:1080[v{i}]")
        else:
            speed = (e - s) / tgt
            png = work / f"label_{tag}_{i}.png"
            label_png(f"waiting for the models  ·  sped up ×{speed:.0f}", png)
            inputs += ["-loop", "1", "-i", str(png)]
            k, n_in = n_in, n_in + 1
            parts.append(f"[0:v]trim=start={s:.2f}:end={e:.2f},setpts=(PTS-STARTPTS)/{speed:.5f},scale=1920:1080[r{i}];"
                         f"[r{i}][{k}:v]overlay=W-w-30:30:shortest=1[v{i}]")
        labels.append(f"[v{i}]")
    fc = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(plan)}:v=1:a=0,fps={FPS},format=yuv420p[v]"
    sh(["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-c:v", "libx264", "-preset", "medium",
        "-crf", "20", str(out)])

    def to_edit(t: float) -> float:
        acc = 0.0
        for s, e, tgt in plan:
            ln = (e - s) if tgt is None else tgt
            if t <= e:
                return acc + max(0.0, t - s) / (e - s) * ln
            acc += ln
        return acc

    return to_edit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    text = narration(numbers())
    audio, caps = {}, {}
    for k, chunks in text.items():
        audio[k] = work / f"n_{k}.wav"
        d, caps[k] = synth(chunks, audio[k])
        print(f"narration {k:9s} {d:5.1f}s")
    total_narr = sum(duration(p) for p in audio.values())
    print(f"narration total {total_narr / 60:.1f} min")

    pngs = render_slides(work)
    html = (ROOT / "deck" / "final.html").read_text(encoding="utf-8")
    S = lambda title: find_slide(pngs, html, title)  # noqa: E731
    clips: list[Path] = []

    def slides_block(tag: str, seq: list[tuple[str, str]]):
        """seq: (slide title, narration key) pairs; each slide is held as long as its narration."""
        for i, (title, key) in enumerate(seq):
            v = work / f"still_{tag}_{i}.mp4"
            still(S(title), duration(audio[key]) + 0.9, v)
            narrate_demo(v, [(0.4, audio[key], caps[key])], work / f"c_{tag}_{i}.mp4", work)
            clips.append(work / f"c_{tag}_{i}.mp4")

    slides_block("open", [("RedactAgent", "intro"), ("Sensitive documents", "problem"),
                          ("Detect, attack, decide", "solution")])

    tm = {m["label"]: m["t"] for m in json.loads((work / "terminal_marks.json").read_text())}
    term = work / "terminal_raw.webm"
    cut(term, [(tm["hw"] - 0.5, tm["servers_done"] + 3.0, None)], work / "term_env.mp4", work, "te")
    narrate_demo(work / "term_env.mp4", [(0.5, audio["env"], caps["env"])], work / "c_env.mp4", work)
    clips.append(work / "c_env.mp4")

    dm = {m["label"]: m["t"] for m in json.loads((work / "marks.json").read_text())}
    demo = work / "demo_b70_raw.webm"
    # one sub-clip per narration segment; a clip holds its last frame while its narration finishes,
    # so speech never drifts behind what is on screen
    segments = [
        ("system", [(dm["system"], dm["review"] - 0.3, None)]),
        ("review", [(dm["review"] - 0.3, dm["detect_start"] + 1.0, None), (dm["detect_start"] + 1.0, dm["detect_done"] - 0.3, 3.0),
                    (dm["detect_done"] - 0.3, dm["risk"] - 0.5, None)]),
        ("risk", [(dm["risk"] - 0.5, dm["select_litigation"] - 0.3, None)]),
        ("policies", [(dm["select_litigation"] - 0.3, dm["export_click"] - 0.3, None)]),
        ("export", [(dm["export_click"] - 0.3, dm["exported"] + 0.5, None)]),
        ("chinese", [(dm["exported"] + 0.5, dm["detect2_start"] + 1.0, None), (dm["detect2_start"] + 1.0, dm["detect2_done"] - 0.3, 2.5),
                     (dm["detect2_done"] - 0.3, dm["batch"] - 0.2, None)]),
        ("batch", [(dm["batch"] - 0.2, dm["batch_start"] + 3.0, None), (dm["batch_start"] + 3.0, dm["batch_done"] - 1.0, 12.0),
                   (dm["batch_done"] - 1.0, dm["end"] + 0.5, None)]),
    ]
    for key, plan in segments:
        cut(demo, plan, work / f"demo_{key}.mp4", work, f"dm_{key}")
        narrate_demo(work / f"demo_{key}.mp4", [(0.3, audio[key], caps[key])], work / f"c_demo_{key}.mp4", work)
        clips.append(work / f"c_demo_{key}.mp4")

    ev = [(tm["eval"] - 0.5, tm["eval"] + 8.0, None), (tm["eval"] + 8.0, tm["eval_done"] - 6.0, 14.0),
          (tm["eval_done"] - 6.0, tm["power_done"] + 4.0, None)]
    cut(term, ev, work / "term_eval.mp4", work, "tv")
    narrate_demo(work / "term_eval.mp4", [(0.5, audio["verify"], caps["verify"])], work / "c_verify.mp4", work)
    clips.append(work / "c_verify.mp4")

    slides_block("mid", [("Throughput on two B70", "perf"), ("Choosing the text model", "perf_model"),
                         ("reasoning loops", "loops"), ("Accuracy on documents", "accuracy"),
                         ("Where it works", "accuracy_miss"), ("replaces a backlog", "business"),
                         ("Business model", "business_model"), ("Private documents, shared safely", "outro")])

    lst = work / "concat.txt"
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", f"fps={FPS},format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", a.out])
    d = duration(Path(a.out))
    print(f"wrote {a.out}  ({d / 60:.2f} min)")
    if d > 600:
        print("WARNING: longer than 10 minutes")


if __name__ == "__main__":
    main()
