"""Canva-style text: rasterise user wording inside the segmentation mask.

No image model — only Pillow. The compositor then pastes through the mask so
pixels outside the selection stay byte-identical (same preservation story as inpaint).
"""
from __future__ import annotations

import io
import logging
import os
import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from app.rendering.storage import fetch_image_bytes, save_pil

logger = logging.getLogger(__name__)


def _parse_hex_rgb(h: Optional[str]) -> Optional[Tuple[int, int, int]]:
    if not h or not isinstance(h, str):
        return None
    v = h.strip().lstrip("#").lower()
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if len(v) != 6:
        return None
    try:
        return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    except ValueError:
        return None


def _font_path() -> Optional[Path]:
    system = platform.system()
    if system == "Windows":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        for name in ("arial.ttf", "segoeui.ttf", "calibri.ttf"):
            p = Path(windir) / "Fonts" / name
            if p.exists():
                return p
    if system == "Darwin":
        p = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
        if p.exists():
            return p
    for p in (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ):
        if p.exists():
            return p
    return None


def _mask_mean_background(img: Image.Image, mask: Image.Image) -> Tuple[int, int, int]:
    """Average RGB of pixels just outside the mask (near the bbox)."""
    import numpy as np

    arr = np.array(img.convert("RGB"))
    m = np.array(mask) > 128
    if not m.any():
        return (248, 248, 248)
    ys, xs = np.where(m)
    y0, y1 = max(ys.min() - 3, 0), min(ys.max() + 4, arr.shape[0])
    x0, x1 = max(xs.min() - 3, 0), min(xs.max() + 4, arr.shape[1])
    ring = np.zeros_like(m, dtype=bool)
    ring[y0:y1, x0:x1] = True
    ring &= ~m
    if not ring.any():
        ring = ~m
    pixels = arr[ring]
    if len(pixels) == 0:
        return (248, 248, 248)
    return tuple(int(x) for x in pixels.mean(axis=0))


def _contrast_text_color(bg: Tuple[int, int, int]) -> Tuple[int, int, int]:
    lum = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
    return (15, 15, 15) if lum > 128 else (250, 250, 250)


def _wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> List[str]:
    words = text.replace("\r", "").split()
    if not words:
        return [""]
    lines: List[str] = []
    cur: List[str] = []
    for w in words:
        trial = " ".join(cur + [w])
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_w or not cur:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def _line_metrics(draw: ImageDraw.ImageDraw, line: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
    bb = draw.textbbox((0, 0), line or " ", font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def _pick_font(
    max_w: int,
    max_h: int,
    lines: List[str],
    path: Optional[Path],
    base_size: int,
) -> ImageFont.FreeTypeFont:
    draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    if path and path.exists():
        for size in range(base_size, 7, -2):
            try:
                font = ImageFont.truetype(str(path), size)
            except OSError:
                continue
            widths, heights = zip(*[_line_metrics(draw, ln, font) for ln in (lines or [""])])
            line_h = max(heights)
            total_h = line_h * len(lines) + (len(lines) - 1) * 4
            max_line_w = max(widths)
            if max_line_w <= max_w and total_h <= max_h:
                return font
        try:
            return ImageFont.truetype(str(path), 10)
        except OSError:
            pass
    return ImageFont.load_default()


def render_text_in_masked_region(
    image_url: str,
    mask_url: str,
    text: str,
    color_hex: Optional[str] = None,
    font_scale: float = 1.0,
) -> Dict:
    """
    Paint ``text`` centred in the mask bbox. Masked area is first filled with
    the local background colour so old glyphs are covered, then the new text is drawn.

    Returns {result_url, method, prompt_used}.
    """
    img = Image.open(io.BytesIO(fetch_image_bytes(image_url))).convert("RGB")
    mask = Image.open(io.BytesIO(fetch_image_bytes(mask_url))).convert("L")
    if mask.size != img.size:
        mask = mask.resize(img.size, Image.NEAREST)

    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("mask is empty")

    x0, y0, x1, y1 = bbox
    bw, bh = x1 - x0, y1 - y0
    bg_rgb = _mask_mean_background(img, mask)
    fill_rgb = _parse_hex_rgb(color_hex) or _contrast_text_color(bg_rgb)

    out = img.copy()
    bg_layer = Image.new("RGB", img.size, bg_rgb)
    out = Image.composite(bg_layer, out, mask)

    pad_x = max(4, int(bw * 0.04))
    pad_y = max(4, int(bh * 0.08))
    inner_w = max(8, bw - 2 * pad_x)
    inner_h = max(8, bh - 2 * pad_y)

    draw = ImageDraw.Draw(out)
    fp = _font_path()
    base = max(10, min(72, int(min(bw, bh) * 0.22 * font_scale)))
    single = (text or "").strip()
    wrap_font = _pick_font(inner_w, inner_h, ["Hello"], fp, base)
    if "\n" in single:
        lines = [ln.strip() for ln in single.split("\n")]
    else:
        lines = _wrap_lines(draw, single, wrap_font, inner_w)
    if not lines:
        lines = [""]
    font = _pick_font(inner_w, inner_h, lines, fp, base)

    line_heights = []
    line_widths = []
    for ln in lines:
        bb = draw.textbbox((0, 0), ln or " ", font=font)
        line_heights.append(bb[3] - bb[1])
        line_widths.append(bb[2] - bb[0])
    gap = 4
    total_h = sum(line_heights) + gap * max(0, len(lines) - 1)
    max_line_w = max(line_widths) if line_widths else 0

    cx = x0 + bw // 2
    cy = y0 + bh // 2
    y_text = cy - total_h // 2
    for i, ln in enumerate(lines):
        bb = draw.textbbox((0, 0), ln or " ", font=font)
        wln = bb[2] - bb[0]
        x_text = cx - wln // 2
        draw.text((x_text, y_text - bb[1]), ln, font=font, fill=fill_rgb)
        y_text += line_heights[i] + gap

    result_url = save_pil("text_overlays", "overlay.png", out, fmt="PNG")
    return {
        "result_url": result_url,
        "method": "pillow/text_overlay",
        "prompt_used": text[:500],
    }
