"""Assemble the Stage I demo video (< 3 min, English narration).

Inputs: the deck PDF, demo_raw.webm + marks.json from record_demo.py, eval metrics.
Narration uses the macOS `say` voice; editing uses ffmpeg.

    python scripts/make_video.py --deck ../deliverables/B12902026_CN_league.pdf --work ../deliverables/video_work \
        --out ../deliverables/RedactAgent_demo.mp4
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOICE = "Samantha"
RATE = "178"
FPS = 30


def sh(cmd: list[str]):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(" ".join(cmd[:6]) + "...\n" + r.stderr[-2000:])
    return r.stdout


def duration(path: Path) -> float:
    return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]).strip())


def tts(text: str, out: Path) -> float:
    aiff = out.with_suffix(".aiff")
    sh(["say", "-v", VOICE, "-r", RATE, "-o", str(aiff), text])
    sh(["ffmpeg", "-y", "-i", str(aiff), "-ar", "48000", "-ac", "2", str(out)])
    aiff.unlink()
    return duration(out)


def render_slides(pdf: Path, pages: list[int], out_dir: Path):
    swift = out_dir / "render.swift"
    swift.write_text("""import PDFKit; import AppKit
let a=CommandLine.arguments; let doc=PDFDocument(url:URL(fileURLWithPath:a[1]))!
for s in a[3].split(separator: ",") { let i=Int(s)!; let p=doc.page(at:i-1)!
 let im=p.thumbnail(of:NSSize(width:1920,height:1080),for:.mediaBox)
 let rep=NSBitmapImageRep(data:im.tiffRepresentation!)!
 try! rep.representation(using:.png,properties:[:])!.write(to:URL(fileURLWithPath:"\\(a[2])/slide_\\(i).png")) }
""")
    sh(["swift", str(swift), str(pdf), str(out_dir), ",".join(map(str, pages))])


def slide_clip(png: Path, audio: Path, out: Path, pad: float = 0.9):
    d = duration(audio) + pad
    sh(["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(png), "-i", str(audio),
        "-filter_complex", f"[0:v]scale=1920:1080,format=yuv420p,fade=t=in:st=0:d=0.3[v];[1:a]apad=pad_dur={pad}[a]",
        "-map", "[v]", "-map", "[a]", "-t", f"{d:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k", "-r", str(FPS), str(out)])


def edit_demo(raw: Path, marks: dict[str, float], out: Path, fast: float = 3.0) -> callable:
    """Keep interaction at normal speed, compress the two model-wait periods to `fast` seconds each."""
    end = duration(raw)
    plan = [  # (start, end, target_len or None)
        (marks["start"], marks["detect_start"] + 1.0, None),
        (marks["detect_start"] + 1.0, marks["detect_done"] - 0.3, fast),
        (marks["detect_done"] - 0.3, marks["detect2_start"] + 1.0, None),
        (marks["detect2_start"] + 1.0, marks["detect2_done"] - 0.3, fast),
        (marks["detect2_done"] - 0.3, min(end, marks["end"] + 0.5), None),
    ]
    from PIL import Image, ImageDraw, ImageFont

    fast_parts = [i for i, (_, _, tgt) in enumerate(plan) if tgt is not None]
    span = plan[fast_parts[0]]
    speed = (span[1] - span[0]) / fast
    label = out.parent / "label_fast.png"
    fnt = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 26)
    text = f"on-device inference  \u00b7  sped up \u00d7{speed:.0f}"
    w = int(fnt.getlength(text)) + 36
    im = Image.new("RGBA", (w, 52), (31, 58, 138, 220))
    ImageDraw.Draw(im).text((18, 12), text, font=fnt, fill=(255, 255, 255, 255))
    im.save(label)
    parts, labels = [f"[1:v]split={len(fast_parts)}" + "".join(f"[l{i}]" for i in fast_parts)], []
    for i, (s, e, tgt) in enumerate(plan):
        f = 1.0 if tgt is None else tgt / (e - s)
        if tgt is None:
            parts.append(f"[0:v]trim=start={s:.2f}:end={e:.2f},setpts=PTS-STARTPTS[v{i}]")
        else:
            parts.append(f"[0:v]trim=start={s:.2f}:end={e:.2f},setpts=(PTS-STARTPTS)*{f:.5f}[r{i}];"
                         f"[r{i}][l{i}]overlay=W-w-30:H-h-30:shortest=1[v{i}]")
        labels.append(f"[v{i}]")
    fc = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(plan)}:v=1:a=0,scale=1920:1080,fps={FPS},format=yuv420p[v]"
    sh(["ffmpeg", "-y", "-i", str(raw), "-loop", "1", "-i", str(label), "-filter_complex", fc, "-map", "[v]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-shortest", str(out)])

    def to_edit(t_raw: float) -> float:
        acc = 0.0
        for s, e, tgt in plan:
            ln = (e - s) if tgt is None else tgt
            if t_raw <= e:
                frac = max(0.0, t_raw - s) / (e - s)
                return acc + frac * ln
            acc += ln
        return acc

    return to_edit


def narrate_demo(video: Path, clips: list[tuple[float, Path]], out: Path):
    """Overlay narration clips at given times; if a clip would overrun the next one, freeze-extend the video end."""
    vd = duration(video)
    # shift clips so they do not overlap
    placed, cursor = [], 0.0
    for t, a in clips:
        t = max(t, cursor + 0.25)
        placed.append((t, a))
        cursor = t + duration(a)
    total = max(vd, cursor + 0.8)
    print("narration placed at", [round(t, 1) for t, _ in placed], f"demo {vd:.1f}s -> {total:.1f}s")
    inputs = ["-i", str(video)]
    for _, a in placed:
        inputs += ["-i", str(a)]
    delays = ";".join(f"[{i + 1}:a]adelay={int(t * 1000)}|{int(t * 1000)}[a{i}]" for i, (t, _) in enumerate(placed))
    mix = "".join(f"[a{i}]" for i in range(len(placed))) + f"amix=inputs={len(placed)}:normalize=0,apad[a]"
    pad = f"[0:v]tpad=stop_mode=clone:stop_duration={max(0.0, total - vd):.2f}[v]"
    sh(["ffmpeg", "-y", *inputs, "-filter_complex", f"{delays};{mix};{pad}", "-map", "[v]", "-map", "[a]",
        "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", str(out)])


def end_card(out: Path, github: str, team: list[dict]):
    """Closing frame for the video: the video cannot show its own YouTube link, so only GitHub + team."""
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1920, 1080
    im = Image.new("RGB", (W, H), (11, 29, 77))
    d = ImageDraw.Draw(im)
    for y in range(H):  # subtle vertical gradient
        c = int(29 + 40 * y / H)
        d.line([(0, y), (W, y)], fill=(11 + int(20 * y / H), c, 77 + int(61 * y / H)))
    bold = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    reg = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
    d.text((150, 300), "RedactAgent", font=ImageFont.truetype(bold, 110), fill="white")
    d.text((150, 450), "Share the document, not the person.", font=ImageFont.truetype(reg, 52), fill=(200, 211, 245))
    y = 600
    if github and "<" not in github:
        d.text((150, y), github, font=ImageFont.truetype(reg, 44), fill=(143, 179, 255))
        y += 80
    for p in team:
        d.text((150, y), f"{p['name']}  \u00b7  {p['student_id']}", font=ImageFont.truetype(reg, 40), fill="white")
        y += 60
    d.text((150, 940), "2026 ASUS UGen AI League  \u00b7  Battlefield Thunderstorm  \u00b7  Workplace AI",
           font=ImageFont.truetype(reg, 32), fill=(160, 175, 220))
    im.save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    work = Path(a.work)
    m = json.loads((ROOT / "eval" / "results" / "metrics.json").read_text())
    rec, prec = m["C_full"]["recall"] * 100, m["C_full"]["precision"] * 100
    base = m["A_deterministic"]["recall"] * 100
    n_items, n_docs = m["C_full"]["gt_items"], m["C_full"]["docs"]

    script = {
        "s1": "This is RedactAgent: an on-premises AI that finds and removes personal data from scanned documents, "
              "built for the ASUS U Gen Intel Arc Pro B70.",
        "s2": "Hospitals, law firms and government agencies share sensitive documents every day, for research, court cases "
              "and public information requests. Every copy must be de-identified first, usually by hand. And cloud AI is not "
              "an option, because the data is not allowed to leave the building.",
        "s5": "RedactAgent reads each page with OCR, and detects personal data with three layers: deterministic rules, a local "
              "language model, and a local vision model. A purpose-based policy decides what to do, and a human approves the result.",
        "d1": "Here is a scanned discharge summary. I choose the research policy, and start detection. Everything runs on this machine.",
        "d2": "It finds names, ID numbers, dates, addresses, the signature and the seal, and shows which layer found each one. "
              "For research, people become consistent pseudonyms, and dates keep only the year.",
        "d3": "The reviewer stays in control: any box can be rejected, or restored.",
        "d4": "Changing the purpose changes the output instantly. A court filing keeps the parties and dates. A public release "
              "removes private individuals, but keeps the physician acting in an official role.",
        "d5": "Export burns the redactions into the pixels, and every step is recorded in a hash-chained audit log.",
        "d6": "Traditional Chinese works too. Here, the red seals are found by colour segmentation and the vision model.",
        "s7": "On the Arc Pro B70, a larger language model and the vision model stay resident together in thirty-two gigabytes of "
              "E C C memory, served by v L L M through the same API the prototype already uses. Moving from laptop to B70 is a "
              "configuration change.",
        "s12": f"On {n_docs} synthetic scanned pages with {n_items} personal data items, rules alone remove {base:.0f} percent. "
               f"Adding the language and vision models raises recall to {rec:.0f} percent, at {prec:.0f} percent precision.",
        "s18": "RedactAgent. Share the document, not the person. The code and the full evaluation are on GitHub. Thank you.",
    }
    audio = {k: work / f"n_{k}.m4a" for k in script}
    for k, t in script.items():
        tts(t, audio[k])
        print(f"narration {k}: {duration(audio[k]):.1f}s")

    render_slides(Path(a.deck), [1, 2, 5, 7, 12], work)
    clips = []
    for k, page in [("s1", 1), ("s2", 2), ("s5", 5)]:
        slide_clip(work / f"slide_{page}.png", audio[k], work / f"c_{k}.mp4")
        clips.append(work / f"c_{k}.mp4")

    marks = {mk["label"]: mk["t"] for mk in json.loads((work / "marks.json").read_text())}
    to_edit = edit_demo(work / "demo_raw.webm", marks, work / "demo_edit.mp4")
    narrate_demo(work / "demo_edit.mp4", [
        (0.3, audio["d1"]),
        (to_edit(marks["detect_done"]) + 0.3, audio["d2"]),
        (to_edit(marks["reject_click"]) - 0.5, audio["d3"]),
        (to_edit(marks["select_litigation"]) - 0.3, audio["d4"]),
        (to_edit(marks["export_click"]), audio["d5"]),
        (to_edit(marks["detect2_start"]), audio["d6"]),
    ], work / "c_demo.mp4")
    clips.append(work / "c_demo.mp4")
    for k, page in [("s7", 7), ("s12", 12)]:
        slide_clip(work / f"slide_{page}.png", audio[k], work / f"c_{k}.mp4")
        clips.append(work / f"c_{k}.mp4")
    import yaml

    cfg = yaml.safe_load((ROOT / "deck" / "config.yaml").read_text(encoding="utf-8"))
    end_card(work / "end_card.png", cfg.get("github", ""), cfg["team"])
    slide_clip(work / "end_card.png", audio["s18"], work / "c_s18.mp4", pad=1.6)
    clips.append(work / "c_s18.mp4")

    lst = work / "concat.txt"
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    # re-encode on concat so all clips share identical stream parameters
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", f"fps={FPS},format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", a.out])
    print(f"wrote {a.out}  ({duration(Path(a.out)):.1f}s)")


if __name__ == "__main__":
    main()
