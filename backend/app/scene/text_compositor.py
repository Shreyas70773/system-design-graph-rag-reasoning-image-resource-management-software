"""Pipeline B Stage 6 — 2D text compositing (Pillow)."""

from __future__ import annotations

import io
from typing import Any, Dict, List

from PIL import Image, ImageDraw, ImageFont

from app.rendering.storage import fetch_image_bytes, save_pil


def composite_text(rgb_url: str, text_layers: List[Dict[str, Any]], scene_id: str, camera_id: str) -> str:
    if not text_layers:
        return rgb_url
    data = fetch_image_bytes(rgb_url)
    img = Image.open(io.BytesIO(data)).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    for layer in text_layers:
        font = _load_font(layer.get("size_px", 48))
        text = layer["text"]
        px = int(w * layer["position_norm"][0])
        py = int(h * layer["position_norm"][1])
        color = layer.get("color_hex", "#111111")
        rgb = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        # Anchor "center" for position.
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            (px - tw // 2, py - th // 2),
            text,
            fill=rgb,
            font=font,
            stroke_width=2,
            stroke_fill=(255, 255, 255) if _is_dark(rgb) else (20, 20, 20),
        )

    return save_pil("renders", f"{scene_id}-{camera_id}-rgb+text.png", img, fmt="PNG")


def _is_dark(rgb):
    r, g, b = rgb
    return (0.299 * r + 0.587 * g + 0.114 * b) < 128


def _load_font(size: int):
    # Try a common bundled font; fall back to PIL default.
    for name in ("arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            continue
    return ImageFont.load_default()
