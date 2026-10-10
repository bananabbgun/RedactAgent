"""Assemble the Stage I demo video (< 3 min, English narration).

Inputs: the deck PDF, demo_raw.webm + marks.json from record_demo.py, eval metrics.
Narration: Kokoro-82M (Apache-2.0) via kokoro-onnx, with burned-in captions; editing uses ffmpeg.

    python scripts/make_video.py --deck ../deliverables/RedactAgent_proposal.pdf --work ../deliverables/video_work \
        --out ../deliverables/RedactAgent_demo.mp4
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KOKORO_DIR = Path.home() / ".local" / "kokoro"
VOICE = "af_heart"  # Kokoro-82M (Apache-2.0), US English
SPEED = 0.94
GAP = 0.22  # pause between caption chunks (s)
FPS = 30
CAP_FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
_kokoro = None


def sh(cmd: list[str]):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(" ".join(cmd[:6]) + "...\n" + r.stderr[-2000:])
    return r.stdout


def duration(path: Path) -> float:
    return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]).strip())


def synth(chunks: list[tuple[str, str]], out: Path) -> tuple[float, list[tuple[float, float, str]]]:
    """Speak each (display, spoken) chunk with Kokoro; return total length and caption timings."""
    global _kokoro
    import numpy as np
    import soundfile as sf
    from kokoro_onnx import Kokoro

    if _kokoro is None:
        _kokoro = Kokoro(str(KOKORO_DIR / "kokoro-v1.0.onnx"), str(KOKORO_DIR / "voices-v1.0.bin"))
    parts, caps, t, sr = [], [], 0.0, 24000
    for display, spoken in chunks:
        samples, sr = _kokoro.create(spoken, voice=VOICE, speed=SPEED, lang="en-us")
        d = len(samples) / sr
        caps.append((t, t + d, display))
        parts += [samples, np.zeros(int(GAP * sr), dtype=samples.dtype)]
        t += d + GAP
    sf.write(out, np.concatenate(parts), sr)
    return t, caps


def caption_png(text: str, out: Path) -> None:
    """White text on a translucent dark box, wrapped to at most two lines."""
    from PIL import Image, ImageDraw, ImageFont

    fnt = ImageFont.truetype(CAP_FONT, 40)
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if fnt.getlength(trial) > 1500 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    lines.append(cur)
    w = int(max(fnt.getlength(l) for l in lines)) + 56
    h = 58 * len(lines) + 26
    im = Image.new("RGBA", (w, h), (8, 15, 40, 205))
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        d.text((w / 2, 13 + 58 * i + 29), l, font=fnt, fill=(255, 255, 255, 255), anchor="mm")
    im.save(out)


def caption_filter(base: str, caps: list[tuple[float, float, str]], first_input: int, work: Path, tag: str
                   ) -> tuple[list[str], str, str]:
    """Return (extra ffmpeg inputs, filter chain, output label) overlaying each caption during its time window."""
    inputs, chain, cur = [], [], base
    for i, (t0, t1, text) in enumerate(caps):
        png = work / f"cap_{tag}_{i}.png"
        caption_png(text, png)
        inputs += ["-loop", "1", "-i", str(png)]
        nxt = f"{tag}c{i}"
        chain.append(f"[{cur}][{first_input + i}:v]overlay=(W-w)/2:H-h-48:enable='between(t,{t0:.2f},{t1 + 0.12:.2f})'"
                     f":eof_action=pass[{nxt}]")
        cur = nxt
    return inputs, ";".join(chain), cur


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


def slide_clip(png: Path, audio: Path, caps, out: Path, work: Path, tag: str, pad: float = 0.9):
    d = duration(audio) + pad
    cap_in, chain, last = caption_filter("bg", caps, 2, work, tag)
    fc = f"[0:v]scale=1920:1080,format=yuv420p,fade=t=in:st=0:d=0.3[bg];[1:a]apad=pad_dur={pad}[a]"
    fc += (";" + chain) if chain else ""
    sh(["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(png), "-i", str(audio), *cap_in,
        "-filter_complex", fc, "-map", f"[{last}]", "-map", "[a]", "-t", f"{d:.2f}", "-c:v", "libx264",
        "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-r", str(FPS), str(out)])


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
                         f"[r{i}][l{i}]overlay=W-w-30:96:shortest=1[v{i}]")
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


def narrate_demo(video: Path, clips: list[tuple[float, Path, list]], out: Path, work: Path):
    """Overlay narration clips (and their captions) at given times; never let two clips overlap."""
    vd = duration(video)
    placed, cursor = [], 0.0
    for t, a, caps in clips:
        t = max(t, cursor + 0.25)
        placed.append((t, a, caps))
        cursor = t + duration(a)
    total = max(vd, cursor + 0.8)
    print("narration placed at", [round(t, 1) for t, _, _ in placed], f"demo {vd:.1f}s -> {total:.1f}s")
    inputs = ["-i", str(video)]
    for _, a, _ in placed:
        inputs += ["-i", str(a)]
    delays = ";".join(f"[{i + 1}:a]adelay={int(t * 1000)}|{int(t * 1000)}[a{i}]" for i, (t, _, _) in enumerate(placed))
    mix = "".join(f"[a{i}]" for i in range(len(placed))) + f"amix=inputs={len(placed)}:normalize=0,apad[a]"
    pad = f"[0:v]tpad=stop_mode=clone:stop_duration={max(0.0, total - vd):.2f}[bg]"
    all_caps = [(t + c0, t + c1, txt) for t, _, caps in placed for c0, c1, txt in caps]
    cap_in, chain, last = caption_filter("bg", all_caps, 1 + len(placed), work, "demo")
    fc = f"{delays};{mix};{pad}" + (";" + chain if chain else "")
    sh(["ffmpeg", "-y", *inputs, *cap_in, "-filter_complex", fc, "-map", f"[{last}]", "-map", "[a]",
        "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", str(out)])


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
        d.text((150, y), p["name"] + (f"  \u00b7  {p['student_id']}" if p.get("student_id") else ""), font=ImageFont.truetype(reg, 40), fill="white")
        y += 60
    d.text((150, 780), "2026 ASUS UGen AI League  \u00b7  Battlefield Thunderstorm  \u00b7  Workplace AI",
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

    pct = lambda x: f"{x:.0f}%"  # noqa: E731
    say_pct = lambda x: f"{x:.0f} percent"  # noqa: E731
    # (caption text, spoken text) - spoken text spells out acronyms so the voice pronounces them clearly
    script = {
        "s1": [("This is RedactAgent: on-premises AI that finds and removes personal data from scanned documents,",
                "This is Redact Agent: on-premises A I that finds and removes personal data from scanned documents,"),
               ("built for the ASUS UGen Intel Arc Pro B70.", "built for the Asus You-Gen Intel Arc Pro B seventy.")],
        "s2": [("Hospitals, law firms and government agencies share sensitive documents every day,",) * 2,
               ("for research, court cases and public-information requests.",) * 2,
               ("Every copy must be de-identified first — usually by hand.", "Every copy must be de-identified first, usually by hand."),
               ("And cloud AI is not an option: the data is not allowed to leave the building.",
                "And cloud A I is not an option, because the data is not allowed to leave the building.")],
        "s5": [("RedactAgent reads each page with OCR,", "Redact Agent reads each page with O C R,"),
               ("then detects personal data with three layers:",) * 2,
               ("deterministic rules, a local language model, and a local vision model.",) * 2,
               ("A purpose-based policy decides what to do, and a person approves the result.",) * 2],
        "d1": [("Here is a scanned discharge summary.",) * 2,
               ("I choose the research policy and start detection.",) * 2,
               ("Everything runs on this machine.",) * 2],
        "d2": [("It finds names, ID numbers, dates, addresses, the signature and the seal,",
                "It finds names, I D numbers, dates, addresses, the signature and the seal,"),
               ("and shows which layer found each one.",) * 2,
               ("For research, people become consistent pseudonyms, and dates keep only the year.",) * 2],
        "d3": [("The reviewer stays in control: any box can be rejected or restored.",) * 2],
        "d4": [("Changing the purpose changes the output instantly.",) * 2,
               ("A court filing keeps the parties and the dates.",) * 2,
               ("A public release removes private individuals, but keeps the physician acting officially.",) * 2],
        "d5": [("Export burns the redactions into the pixels,",) * 2,
               ("and every step is recorded in a tamper-evident audit log.",) * 2],
        "d6": [("Traditional Chinese works too.",) * 2,
               ("The red seals are found by colour detection and the vision model.",) * 2],
        "s7": [("On the Arc Pro B70, a larger language model and the vision model stay loaded together,",
                "On the Arc Pro B seventy, a larger language model and the vision model stay loaded together,"),
               ("in 32 GB of error-correcting memory,", "in thirty-two gigabytes of error-correcting memory,"),
               ("served by vLLM through the same API the prototype already uses.",
                "served by V L L M, through the same A P I the prototype already uses."),
               ("Moving from laptop to B70 is a configuration change.",
                "Moving from the laptop to the B seventy is just a configuration change.")],
        "s12": [(f"On {n_docs} synthetic scanned pages with {n_items} personal-data items,",
                 f"On {n_docs} synthetic scanned pages, with {n_items} personal data items,"),
                (f"rules alone remove {pct(base)}.", f"rules alone remove {say_pct(base)}."),
                (f"Adding the language and vision models raises recall to {pct(rec)},",
                 f"Adding the language and vision models raises recall to {say_pct(rec)},"),
                (f"at {pct(prec)} precision.", f"at {say_pct(prec)} precision.")],
        "s18": [("RedactAgent. Share the document, not the person.", "Redact Agent. Share the document, not the person."),
                ("The code and the full evaluation are on GitHub. Thank you.",) * 2],
    }
    audio, caps = {}, {}
    for k, chunks in script.items():
        audio[k] = work / f"n_{k}.wav"
        d, caps[k] = synth(chunks, audio[k])
        print(f"narration {k}: {d:.1f}s")

    render_slides(Path(a.deck), [1, 2, 5, 7, 12], work)
    clips = []
    for k, page in [("s1", 1), ("s2", 2), ("s5", 5)]:
        slide_clip(work / f"slide_{page}.png", audio[k], caps[k], work / f"c_{k}.mp4", work, k)
        clips.append(work / f"c_{k}.mp4")

    marks = {mk["label"]: mk["t"] for mk in json.loads((work / "marks.json").read_text())}
    to_edit = edit_demo(work / "demo_raw.webm", marks, work / "demo_edit.mp4")
    narrate_demo(work / "demo_edit.mp4", [
        (0.3, audio["d1"], caps["d1"]),
        (to_edit(marks["detect_done"]) + 0.3, audio["d2"], caps["d2"]),
        (to_edit(marks["reject_click"]) - 0.5, audio["d3"], caps["d3"]),
        (to_edit(marks["select_litigation"]) - 0.3, audio["d4"], caps["d4"]),
        (to_edit(marks["export_click"]), audio["d5"], caps["d5"]),
        (to_edit(marks["detect2_start"]), audio["d6"], caps["d6"]),
    ], work / "c_demo.mp4", work)
    clips.append(work / "c_demo.mp4")
    for k, page in [("s7", 7), ("s12", 12)]:
        slide_clip(work / f"slide_{page}.png", audio[k], caps[k], work / f"c_{k}.mp4", work, k)
        clips.append(work / f"c_{k}.mp4")
    import yaml

    cfg = yaml.safe_load((ROOT / "deck" / "config.yaml").read_text(encoding="utf-8"))
    end_card(work / "end_card.png", cfg.get("github", ""), cfg["team"])
    slide_clip(work / "end_card.png", audio["s18"], caps["s18"], work / "c_s18.mp4", work, "s18", pad=1.6)
    clips.append(work / "c_s18.mp4")

    lst = work / "concat.txt"
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    # re-encode on concat so all clips share identical stream parameters
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", f"fps={FPS},format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", a.out])
    print(f"wrote {a.out}  ({duration(Path(a.out)):.1f}s)")


if __name__ == "__main__":
    main()
