"""Composite inpainted region back and compute the three research metrics.

Metrics
-------
background_ssim  : SSIM on non-masked pixels (should be ~1.0 — proves isolation).
brand_delta_e    : Mean CIEDE2000 between dominant colours in the edited region
                   and the brand palette.  Lower = more brand-consistent.
identity_ssim    : Histogram cosine similarity between edited region and brand
                   reference image crop (if provided).
"""
from __future__ import annotations

import io
import logging
import math
import statistics
from collections import Counter
from typing import Dict, List, Optional

import numpy as np
from PIL import Image

from app.rendering.storage import fetch_image_bytes, save_pil

logger = logging.getLogger(__name__)


def composite_and_measure(
    original_url: str,
    inpainted_url: str,
    mask_url: str,
    brand_colors: List[str],
    reference_url: Optional[str] = None,
) -> Dict:
    """
    Paste inpainted pixels into original (non-mask pixels are pixel-exact).
    Returns result_url + metrics dict.
    """
    orig = _load(original_url)
    inp = _load(inpainted_url)
    mask = Image.open(io.BytesIO(fetch_image_bytes(mask_url))).convert("L")

    # Resize to match original
    if inp.size != orig.size:
        inp = inp.resize(orig.size, Image.LANCZOS)
    if mask.size != orig.size:
        mask = mask.resize(orig.size, Image.NEAREST)

    # Composite
    result = orig.copy()
    result.paste(inp, mask=mask)

    result_url = save_pil("composites", "result.png", result, fmt="PNG")

    metrics = {
        "background_ssim": _background_ssim(orig, result, mask),
        "brand_delta_e": _brand_delta_e(result, mask, brand_colors),
        "identity_ssim": _identity_ssim(result, mask, reference_url),
    }

    return {"result_url": result_url, "metrics": metrics}


def _load(url: str) -> Image.Image:
    return Image.open(io.BytesIO(fetch_image_bytes(url))).convert("RGB")


# ---------------------------------------------------------------------------
# Metric implementations
# ---------------------------------------------------------------------------

def _background_ssim(orig: Image.Image, result: Image.Image, mask: Image.Image) -> float:
    """
    SSIM approximation on non-masked pixels.

    Because the compositor pastes pixel-exact values outside the mask, this
    should be extremely close to 1.0.  Any deviation indicates a compositing bug.
    """
    o = np.array(orig, dtype=np.float32) / 255.0
    r = np.array(result, dtype=np.float32) / 255.0
    m = np.array(mask, dtype=np.float32) / 255.0

    bg = m < 0.5  # True where NOT inpainted
    if not bg.any():
        return 1.0

    o_bg = o[bg]
    r_bg = r[bg]
    diff = o_bg - r_bg
    mse = float(np.mean(diff ** 2))

    # When MSE ≈ 0 (pixel-exact), SSIM ≈ 1.
    mu_o = float(np.mean(o_bg))
    mu_r = float(np.mean(r_bg))
    sigma_o = float(np.std(o_bg)) + 1e-6
    sigma_r = float(np.std(r_bg)) + 1e-6
    sigma_or = float(np.mean((o_bg - mu_o) * (r_bg - mu_r)))

    c1, c2 = (0.01 ** 2), (0.03 ** 2)
    ssim = ((2 * mu_o * mu_r + c1) * (2 * sigma_or + c2)) / (
        (mu_o ** 2 + mu_r ** 2 + c1) * (sigma_o ** 2 + sigma_r ** 2 + c2)
    )
    return round(float(np.clip(ssim, 0.0, 1.0)), 6)


def _extract_region_colors(img: Image.Image, mask: Image.Image, n: int = 6) -> List[str]:
    arr = np.array(img.convert("RGB"))
    m = np.array(mask)
    ys, xs = np.where(m > 128)
    if len(ys) == 0:
        return []
    pixels = arr[ys, xs]
    # Round to nearest 16 for quantisation
    q = (pixels // 16) * 16
    rows = [tuple(row) for row in q]
    common = Counter(rows).most_common(n)
    return [f"#{r:02x}{g:02x}{b:02x}" for (r, g, b), _ in common]


def _parse_hex_rgb_safe(h: str):
    """Return (r,g,b) 0-255 or None if not a valid 6-digit hex."""
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


def sanitize_palette_hex(raw: List[str]) -> List[str]:
    """Keep only valid 6-digit RGB hex codes (filters Neo4j junk like 'None', 'No')."""
    out: List[str] = []
    for x in raw or []:
        if not _parse_hex_rgb_safe(str(x)):
            continue
        v = str(x).strip().lstrip("#").lower()
        if len(v) == 3:
            v = "".join(c * 2 for c in v)
        out.append(f"#{v}")
    return out


def _hex_to_lab(h: str):
    rgb = _parse_hex_rgb_safe(h)
    if rgb is None:
        return (0.0, 0.0, 0.0)
    r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = lin(r), lin(g), lin(b)
    x = 0.4124 * r + 0.3576 * g + 0.1805 * b
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = 0.0193 * r + 0.1192 * g + 0.9505 * b

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    return (116 * f(y / 1.0) - 16, 500 * (f(x / 0.95047) - f(y / 1.0)), 200 * (f(y / 1.0) - f(z / 1.08883)))


def _de76(lab1, lab2) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(lab1, lab2)))


def _brand_delta_e(result: Image.Image, mask: Image.Image, brand_colors: List[str]) -> float:
    """Mean ΔE76 between edited-region dominant colours and brand palette."""
    valid_brand = [c for c in brand_colors if _parse_hex_rgb_safe(str(c))]
    if not valid_brand:
        return -1.0
    region_colors = _extract_region_colors(result, mask)
    if not region_colors:
        return -1.0

    b_labs = [_hex_to_lab(c) for c in valid_brand[:5]]
    r_labs = [_hex_to_lab(c) for c in region_colors if _parse_hex_rgb_safe(c)]
    if not r_labs:
        return -1.0

    deltas = [min(_de76(rl, bl) for bl in b_labs) for rl in r_labs]
    return round(statistics.mean(deltas), 4)


def _identity_ssim(result: Image.Image, mask: Image.Image, reference_url: Optional[str]) -> Optional[float]:
    """Histogram cosine similarity between edited region and brand reference crop."""
    if not reference_url:
        return None
    try:
        ref = _load(reference_url)
    except Exception:
        return None

    # Crop result to masked bbox
    m_arr = np.array(mask)
    ys, xs = np.where(m_arr > 128)
    if len(ys) == 0:
        return None

    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
    region = result.crop((x0, y0, x1, y1)).resize((64, 64), Image.LANCZOS)
    ref_crop = ref.resize((64, 64), Image.LANCZOS)

    def hist_vec(img: Image.Image) -> np.ndarray:
        arr = np.array(img.convert("RGB"), dtype=np.uint8)
        parts = [np.histogram(arr[:, :, c], bins=16, range=(0, 256))[0] for c in range(3)]
        v = np.concatenate(parts).astype(np.float32)
        n = float(np.linalg.norm(v))
        return v / n if n > 1e-9 else v

    sim = float(np.dot(hist_vec(region), hist_vec(ref_crop)))
    return round(max(0.0, min(1.0, sim)), 4)
