"""Burn redactions into the page pixels and export.

Redaction is applied to the raster image itself and the output PDF contains no text
layer, so nothing can be recovered by copy-pasting or removing a black rectangle -
the classic failure of "redacted" PDFs.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .schema import CATEGORIES, Finding

_FONT_CANDIDATES = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
_FONT = next((f for f in _FONT_CANDIDATES if Path(f).exists()), _FONT_CANDIDATES[0])


def _label_font(h: int, text: str, w: int) -> ImageFont.ImageFont:
    size = max(10, min(int(h * 0.62), 30))
    while size > 9:
        try:
            f = ImageFont.truetype(_FONT, size)
        except OSError:
            return ImageFont.load_default()
        if f.getlength(text) <= w - 6:
            return f
        size -= 1
    return ImageFont.truetype(_FONT, 9) if Path(_FONT).exists() else ImageFont.load_default()


def redact_page(img: Image.Image, findings: list[Finding]) -> Image.Image:
    out = img.convert("RGB").copy()
    d = ImageDraw.Draw(out)
    for f in findings:
        if not f.accepted or f.action == "keep":
            continue
        x0, y0, x1, y1 = f.bbox
        d.rectangle([x0, y0, x1, y1], fill=(0, 0, 0))
        if f.label:
            fnt = _label_font(y1 - y0, f.label, x1 - x0)
            d.text(((x0 + x1) / 2, (y0 + y1) / 2), f.label, font=fnt, fill=(255, 255, 255), anchor="mm")
    return out


def overlay_page(img: Image.Image, findings: list[Finding]) -> Image.Image:
    """Review view: translucent category-coloured boxes on the original."""
    base = img.convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for f in findings:
        col = CATEGORIES.get(f.category, ("", "#ff0000"))[1].lstrip("#")
        rgb = tuple(int(col[i:i + 2], 16) for i in (0, 2, 4))
        d.rectangle(f.bbox, fill=rgb + (60,), outline=rgb + (255,), width=3)
    return Image.alpha_composite(base, layer).convert("RGB")


def to_pdf(pages: list[Image.Image], dpi: int = 150) -> bytes:
    buf = io.BytesIO()
    rgb = [p.convert("RGB") for p in pages]
    rgb[0].save(buf, format="PDF", save_all=True, append_images=rgb[1:], resolution=dpi)
    return buf.getvalue()
