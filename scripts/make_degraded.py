"""Degraded copies of a corpus for a robustness curve (real scans are worse than synthetic ones).

    python scripts/make_degraded.py --src data/synthetic_v2 --out data/degraded

Creates <out>/<kind>_<level>/{images,gt,index.json}. Image size is kept, so ground-truth boxes stay valid
(rotation transforms them). Kinds: lowres (effective DPI), blur, jpeg, rotate, fax (1-bit threshold).
"""

from __future__ import annotations

import argparse
import io
import json
import math
import random
import shutil
from pathlib import Path

from PIL import Image, ImageFilter

LEVELS = {
    "lowres": [100, 75],  # effective DPI (source pages are rendered at 150 DPI)
    "blur": [1.2, 2.0],  # Gaussian radius in pixels
    "jpeg": [25, 10],  # JPEG quality
    "rotate": [2.0, 5.0],  # degrees
    "fax": [1, 2],  # 1 = clean threshold, 2 = threshold + speckle noise
}


def degrade(img: Image.Image, kind: str, level, rng: random.Random) -> Image.Image:
    w, h = img.size
    if kind == "lowres":
        s = level / 150
        return img.resize((max(1, int(w * s)), max(1, int(h * s))), Image.BILINEAR).resize((w, h), Image.BICUBIC)
    if kind == "blur":
        return img.filter(ImageFilter.GaussianBlur(level))
    if kind == "jpeg":
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=level)
        return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    if kind == "rotate":
        return img.rotate(level, resample=Image.BICUBIC, fillcolor=(255, 255, 255))
    if kind == "fax":
        g = img.convert("L")
        if level == 2:
            px = g.load()
            for _ in range(w * h // 400):
                x, y = rng.randrange(w), rng.randrange(h)
                px[x, y] = 0 if px[x, y] > 128 else 255
        return g.point(lambda v: 255 if v > 150 else 0).convert("RGB")
    raise ValueError(kind)


def rotate_box(b, deg, w, h):
    """Axis-aligned box around a box rotated counter-clockwise by `deg` about the image centre (PIL convention)."""
    a = math.radians(deg)
    cx, cy = w / 2, h / 2
    pts = []
    for x, y in ((b[0], b[1]), (b[2], b[1]), (b[0], b[3]), (b[2], b[3])):
        dx, dy = x - cx, y - cy
        pts.append((cx + dx * math.cos(a) + dy * math.sin(a), cy - dx * math.sin(a) + dy * math.cos(a)))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return [int(max(0, min(xs))), int(max(0, min(ys))), int(math.ceil(min(w, max(xs)))), int(math.ceil(min(h, max(ys))))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/synthetic_v2")
    ap.add_argument("--out", default="data/degraded")
    ap.add_argument("--kinds", default=",".join(LEVELS))
    a = ap.parse_args()
    src, out = Path(a.src), Path(a.out)
    index = json.loads((src / "index.json").read_text())
    for kind in a.kinds.split(","):
        for level in LEVELS[kind]:
            d = out / f"{kind}_{level}"
            if d.exists():
                shutil.rmtree(d)
            (d / "images").mkdir(parents=True)
            (d / "gt").mkdir()
            rng = random.Random(7)
            for doc in index:
                img = Image.open(src / "images" / f"{doc['id']}.jpg").convert("RGB")
                degrade(img, kind, level, rng).save(d / "images" / f"{doc['id']}.jpg", quality=92)
                gt = json.loads((src / "gt" / f"{doc['id']}.json").read_text())
                if kind == "rotate":
                    for it in gt["items"]:
                        it["bbox"] = rotate_box(it["bbox"], level, gt["width"], gt["height"])
                (d / "gt" / f"{doc['id']}.json").write_text(json.dumps(gt, ensure_ascii=False))
            (d / "index.json").write_text(json.dumps(index, indent=1))
            print("wrote", d)


if __name__ == "__main__":
    main()
