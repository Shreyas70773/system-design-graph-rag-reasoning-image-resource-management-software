"""Pipeline B Stage 7 — LAB-space gamut clip toward brand palette."""

from __future__ import annotations

import io
from typing import Any, Dict, List

from PIL import Image

from app.rendering.storage import fetch_image_bytes, save_pil


def grade(rgb_url: str, brand_colors: List[Dict[str, Any]], scene_id: str, camera_id: str,
          strength: float = 0.25) -> str:
    """Soft-pull image mean colour toward brand palette's LAB centroid."""
    if not brand_colors:
        return rgb_url
    data = fetch_image_bytes(rgb_url)
    img = Image.open(io.BytesIO(data)).convert("RGB")

    try:
        import numpy as np
        from skimage import color as skcolor
    except ImportError:
        # Without skimage, we do a simpler RGB-mean pull.
        return _rgb_pull(img, brand_colors, scene_id, camera_id, strength)

    arr = np.asarray(img, dtype=float) / 255.0
    lab = skcolor.rgb2lab(arr)
    mean_lab = lab.reshape(-1, 3).mean(axis=0)

    # Brand palette centroid in LAB.
    brand_rgb = [_hex_to_rgb(c["hex"]) for c in brand_colors if c.get("hex")]
    if not brand_rgb:
        return rgb_url
    target = np.array(brand_rgb, dtype=float) / 255.0
    target_lab = skcolor.rgb2lab(target.reshape(1, -1, 3)).reshape(-1, 3).mean(axis=0)

    delta = (target_lab - mean_lab) * float(strength)
    lab[..., 0] = np.clip(lab[..., 0] + delta[0], 0, 100)
    lab[..., 1] = np.clip(lab[..., 1] + delta[1], -128, 128)
    lab[..., 2] = np.clip(lab[..., 2] + delta[2], -128, 128)

    out_rgb = (np.clip(skcolor.lab2rgb(lab), 0, 1) * 255).astype("uint8")
    graded = Image.fromarray(out_rgb)
    return save_pil("renders", f"{scene_id}-{camera_id}-graded.png", graded, fmt="PNG")


def _rgb_pull(img: Image.Image, brand_colors, scene_id, camera_id, strength: float) -> str:
    brand_rgb = [_hex_to_rgb(c["hex"]) for c in brand_colors if c.get("hex")]
    if not brand_rgb:
        return save_pil("renders", f"{scene_id}-{camera_id}-graded.png", img)
    target = tuple(sum(c) / len(brand_rgb) for c in zip(*brand_rgb))
    from PIL import ImageOps
    img2 = ImageOps.colorize(img.convert("L"), (0, 0, 0), tuple(int(c) for c in target))
    # Blend original with colorised copy.
    blended = Image.blend(img, img2, alpha=strength)
    return save_pil("renders", f"{scene_id}-{camera_id}-graded.png", blended)


def _hex_to_rgb(hx: str):
    hx = hx.lstrip("#")
    return int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
