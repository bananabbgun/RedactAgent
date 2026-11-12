"""Final video, story cut: one idea per screen, the live demo in the middle, details left to the deck.

Structure (chapters shown on every card): 1 problem, 2 idea, 3 live demo on the organiser's B70 instance,
4 proof (live evaluation, hospital numbers, degraded scans), 5 built on the B70 (dual-card host, model choice,
measured bottlenecks, reasoning loops, cost), 6 ready. Cards come from deck/video_cards.html.j2 (1920x1080, bottom band
kept free for captions); footage is the same recordings as scripts/make_final_video.py, cut per narration
segment, with zoomed crops where the narration points at something small.

    python scripts/make_story_video.py --work ../deliverables/final_video --out ../deliverables/RedactAgent_final.mp4
    python scripts/make_story_video.py ... --no-captions      # clean version without burned-in captions
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

import make_video
from make_final_video import numbers
from make_video import FPS, ROOT, duration, narrate_demo, sh, synth

BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
# crops of the 1600x900 demo recording (x, y, w, h), all 16:9
DOC = (300, 160, 960, 540)      # detected + redacted page side by side
FERRY = (300, 380, 640, 360)    # hospital course paragraph with the combination clue
LEFT = (0, 300, 960, 540)       # risk result, approve & export, audit trail
RESULT = (30, 440, 800, 450, (14, 888, 1200, 54))  # terminal: evaluation table, full-system row boxed


def caption_png(text: str, out: Path) -> None:
    """Smaller, lighter captions than Stage I: one line where possible, two at most."""
    from PIL import Image, ImageDraw, ImageFont

    fnt = ImageFont.truetype(BOLD, 36)
    lines, cur = [], ""
    for w in text.split():
        trial = (cur + " " + w).strip()
        if fnt.getlength(trial) > 1560 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    lines.append(cur)
    w = int(max(fnt.getlength(l) for l in lines)) + 48
    h = 50 * len(lines) + 22
    im = Image.new("RGBA", (w, h), (8, 15, 40, 190))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        d.text((w / 2, 11 + 50 * i + 25), l, font=fnt, fill=(255, 255, 255, 255), anchor="mm")
    im.save(out)


make_video.caption_png = caption_png  # caption_filter looks the function up at call time


def pill(text: str, out: Path, bg=(31, 58, 138, 230)):
    from PIL import Image, ImageDraw, ImageFont

    fnt = ImageFont.truetype(BOLD, 26)
    w = int(fnt.getlength(text)) + 40
    im = Image.new("RGBA", (w, 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, 49), radius=25, fill=bg)
    d.text((20, 25), text, font=fnt, fill=(255, 255, 255, 255), anchor="lm")
    im.save(out)


def story_context(nums: dict) -> dict:
    """Numbers for the cards beyond numbers(): robustness, model sweep, loops, cost; all read from result files."""
    import sys

    sys.path.insert(0, str(ROOT / "deck"))
    from build_final import tune_rows

    ctx = dict(nums)
    robust = json.loads((ROOT / "eval" / "robustness" / "summary.json").read_text())
    worst = {}
    for r in robust:  # worst setting of each kind
        if r["kind"] not in worst or r["D"] < worst[r["kind"]]["D"]:
            worst[r["kind"]] = r
    names = {"clean": ("Clean scan", "test set v2"), "fax": ("Fax", None), "rotate": ("Skewed", None), "jpeg": ("JPEG", None),
             "lowres": ("Low resolution", None), "blur": ("Blur", None)}
    ctx["robust"] = sorted(({"label": names[k][0], "level": names[k][1] or r["level"], "A": r["A"], "D": r["D"]}
                            for k, r in worst.items()), key=lambda r: -r["D"])
    ctx["robust_min"] = f"{int(min(r['D'] for r in robust) * 100)}%"
    rows = tune_rows()
    for r in rows:
        r["name"], r["final"] = r["name"].replace(" (MoE)", ""), r["id"].startswith("T5b")
    ctx["tune"] = rows
    b70 = ROOT / "eval" / "results_b70"
    bench = json.loads((b70 / "bench" / "benchmark.json").read_text())
    fast = json.loads((b70 / "fast" / "bench" / "benchmark.json").read_text())
    acc8, fast8 = (next(r for r in x if r["concurrency"] == 8)["pages_per_min"] for x in (bench, fast))
    ctx["fast_gain"] = f"{(fast8 / acc8 - 1) * 100:.0f}%"
    best = max(bench, key=lambda r: r["pages_per_min"])
    ctx["min_per_1000"] = f"{1000 / best['pages_per_min']:.0f}"
    ctx["kwh_per_1000"] = f"{1000 / best['pages_per_kwh']:.2f}"
    return ctx


def render_cards(nums: dict, out_dir: Path) -> dict[str, Path]:
    from jinja2 import Template
    from playwright.sync_api import sync_playwright

    html = out_dir / "video_cards.html"
    html.write_text(Template((ROOT / "deck" / "video_cards.html.j2").read_text(encoding="utf-8")).render(**nums), encoding="utf-8")
    pngs = {}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto(html.as_uri(), wait_until="networkidle")
        for el in pg.query_selector_all(".card"):
            k = el.get_attribute("data-key")
            pngs[k] = out_dir / f"card_{k}.png"
            el.screenshot(path=str(pngs[k]))
        b.close()
    return pngs


def still(png: Path, seconds: float, out: Path):
    sh(["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(png), "-t", f"{seconds:.2f}",
        "-vf", f"scale=1920:1080,fps={FPS},format=yuv420p,fade=t=in:st=0:d=0.25", "-c:v", "libx264", "-preset", "medium",
        "-crf", "20", str(out)])


def cut(raw: Path, plan: list[tuple], out: Path, work: Path, tag: str, chapter: str | None):
    """plan: (start, end, target_len or None, crop or None). Sped-up spans get a label; every span gets the chapter pill."""
    inputs, n_in, parts, labels = ["-i", str(raw)], 1, [], []
    chap_idx = None
    if chapter:
        cp = work / f"pill_{tag}.png"
        pill(chapter, cp)
        inputs += ["-loop", "1", "-i", str(cp)]
        chap_idx, n_in = n_in, n_in + 1
    for i, (s, e, tgt, crop) in enumerate(plan):
        f = f"[0:v]trim=start={s:.2f}:end={e:.2f}"
        f += ",setpts=PTS-STARTPTS" if tgt is None else f",setpts=(PTS-STARTPTS)/{(e - s) / tgt:.5f}"
        if crop:
            x, y, w, h = crop[:4]
            f += f",crop={w}:{h}:{x}:{y}"
        f += ",scale=1920:1080:flags=lanczos,setsar=1"
        if crop and len(crop) > 4:  # highlight box in output pixels: (x, y, w, h)
            bx, by, bw, bh = crop[4]
            f += f",drawbox=x={bx}:y={by}:w={bw}:h={bh}:color=0xFACC15:t=6"
        f += f"[s{i}]"
        parts.append(f)
        cur = f"s{i}"
        if tgt is not None:
            lp = work / f"label_{tag}_{i}.png"
            pill(f"sped up ×{(e - s) / tgt:.0f}", lp, bg=(90, 98, 120, 220))
            inputs += ["-loop", "1", "-i", str(lp)]
            parts.append(f"[{cur}][{n_in}:v]overlay=W-w-30:30:shortest=1[t{i}]")
            cur, n_in = f"t{i}", n_in + 1
        if chap_idx is not None:
            parts.append(f"[{cur}][cp{i}]overlay=(W-w)/2:14:shortest=1[v{i}]")
            cur = f"v{i}"
        labels.append(f"[{cur}]")
    if chap_idx is not None:
        parts.insert(0, f"[{chap_idx}:v]split={len(plan)}" + "".join(f"[cp{i}]" for i in range(len(plan))))
    fc = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(plan)}:v=1:a=0,fps={FPS},format=yuv420p[v]"
    sh(["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-c:v", "libx264", "-preset", "medium",
        "-crf", "20", str(out)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-captions", action="store_true")
    a = ap.parse_args()
    work = Path(a.work).resolve() / "story"
    work.mkdir(parents=True, exist_ok=True)
    rec = Path(a.work).resolve()

    nums = story_context(numbers())
    nums["robust_min_spoken"] = nums["robust_min"].replace("%", " percent")
    nums["fast_gain_spoken"] = nums["fast_gain"].replace("%", " percent")
    raw = yaml.safe_load((ROOT / "scripts" / "story_narration.yaml").read_text(encoding="utf-8"))
    audio, caps = {}, {}
    for k, chunks in raw.items():
        pairs = [(c[0].format(**nums), (c[1] if len(c) > 1 else c[0]).format(**nums)) for c in chunks]
        audio[k] = work / f"n_{k}.wav"
        d, caps[k] = synth(pairs, audio[k])
        if a.no_captions:
            caps[k] = []
        print(f"narration {k:9s} {d:5.1f}s")
    print(f"narration total {sum(duration(p) for p in audio.values()) / 60:.1f} min")

    cards = render_cards(nums, work)
    clips: list[Path] = []

    def card(key: str, hold: float = 0.9):
        v = work / f"still_{key}.mp4"
        still(cards[key], duration(audio[key]) + hold, v)
        narrate_demo(v, [(0.35, audio[key], caps[key])], work / f"c_{key}.mp4", work)
        clips.append(work / f"c_{key}.mp4")

    def footage(key: str, src: Path, plan, chapter: str, extra: list[tuple[float, str]] = ()):
        """extra: further narration segments placed at given times of the edited clip (e.g. when a result appears)."""
        v = work / f"cut_{key}.mp4"
        cut(src, plan, v, work, key, chapter)
        narr = [(0.3, audio[key], caps[key])] + [(t, audio[k], caps[k]) for t, k in extra]
        narrate_demo(v, narr, work / f"c_{key}.mp4", work)
        clips.append(work / f"c_{key}.mp4")

    for k in ("cover", "volume", "humans", "notool", "idea", "combo"):
        card(k)

    LIVE = "3 · LIVE DEMO  —  organiser's Intel Cloud instance, 2× Arc Pro B70"
    tm = {m["label"]: m["t"] for m in json.loads((rec / "terminal_marks.json").read_text())}
    term = rec / "terminal_raw.webm"
    footage("env", term, [(tm["hw"] - 0.5, tm["gpus_done"] + 1.5, None, None),
                          (tm["servers_done"] - 4.0, tm["servers_done"] + 2.0, None, None)], LIVE)

    dm = {m["label"]: m["t"] for m in json.loads((rec / "marks.json").read_text())}
    demo = rec / "demo_b70_raw.webm"
    footage("review", demo, [(dm["review"] - 0.3, dm["detect_start"] + 1.0, None, None),
                             (dm["detect_start"] + 1.0, dm["detect_done"] - 0.3, 3.0, None),
                             (dm["detect_done"] - 0.3, dm["detect_done"] + 2.5, None, None),
                             (dm["detect_done"] + 2.5, dm["risk"] - 0.5, None, DOC)], LIVE,
            extra=[((dm["detect_start"] + 1.0) - (dm["review"] - 0.3) + 3.0 + 0.3, "review_found")])
    footage("ferry", demo, [(dm["risk"] - 0.5, dm["select_litigation"] - 0.3, None, FERRY)], LIVE)
    footage("policies", demo, [(dm["select_litigation"] - 0.3, dm["export_click"] - 0.3, None, None)], LIVE)
    footage("export", demo, [(dm["export_click"] - 0.3, dm["exported"] + 1.0, None, LEFT)], LIVE)
    footage("chinese", demo, [(dm["exported"] + 1.0, dm["detect2_start"] + 1.0, None, None),
                              (dm["detect2_start"] + 1.0, dm["detect2_done"] - 0.3, 2.5, None),
                              (dm["detect2_done"] - 0.3, dm["batch"] - 0.2, None, DOC)], LIVE)
    footage("batch", demo, [(dm["batch"] - 0.2, dm["batch_start"] + 2.0, None, None),
                            (dm["batch_start"] + 2.0, dm["batch_done"] - 1.0, 8.0, None),
                            (dm["batch_done"] - 1.0, dm["batch_done"] + 3.0, None, None)], LIVE)

    footage("verify", term, [(tm["eval"] - 0.5, tm["eval"] + 7.0, None, None),
                             (tm["eval"] + 7.0, tm["eval_done"] - 4.0, 8.0, None),
                             (tm["eval_done"] - 4.0, tm["eval_done"] + 0.8, None, None),
                             (tm["eval_done"] + 0.8, tm["eval_done"] + 6.0, None, RESULT)],
            "4 · PROOF  —  live evaluation on the B70, unseen test set",
            extra=[(7.5 + 8.0 + 4.8 + 0.3, "verify_result")])

    for k in ("proof", "robust", "hardware", "model", "ocr", "loops", "cost", "ready", "next"):
        card(k)
    card("outro", hold=2.0)

    lst = work / "concat.txt"
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", f"fps={FPS},format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", a.out])
    d = duration(Path(a.out))
    print(f"wrote {a.out}  ({d / 60:.2f} min)")


if __name__ == "__main__":
    main()
