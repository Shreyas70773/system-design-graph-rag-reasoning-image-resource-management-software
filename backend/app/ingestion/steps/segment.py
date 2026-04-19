"""Step 3 — segment parts (GroundingDINO + SAM 2.1 real + bbox-grid mock)."""

from __future__ import annotations

import io
import logging
from typing import Dict, List

from PIL import Image, ImageDraw

from app.config_v2 import get_v2_settings
from app.rendering.capabilities import detect
from app.rendering.storage import fetch_image_bytes, save_pil

logger = logging.getLogger(__name__)


def run(source_image_url: str, part_names: List[str]) -> List[Dict]:
    """Return list of part dicts: name, mask_url, uv_region, part_type, editable."""
    settings = get_v2_settings()
    caps = detect()
    use_real = (not settings.mock_mode or settings.force_real_segmenter) \
        and caps.sam2 and caps.groundingdino and caps.torch_cuda
    if use_real:
        try:
            return _real_grounded_sam(source_image_url, part_names)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Segmenter real path failed (%s); using mock", exc)
    return _mock(source_image_url, part_names)


def _mock(source_image_url: str, part_names: List[str]) -> List[Dict]:
    """Produce simple horizontally-banded masks for each part name."""
    data = fetch_image_bytes(source_image_url)
    img = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = img.size
    band_h = max(h // max(1, len(part_names)), 1)

    parts = []
    for i, name in enumerate(part_names):
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        y0 = min(i * band_h, h - 1)
        y1 = h if i == len(part_names) - 1 else min(y0 + band_h, h)
        if y1 <= y0:
            y1 = min(y0 + 1, h)
        draw.rectangle([0, y0, w, y1], fill=255)
        url = save_pil("parts/mock_masks", f"{name}-mask.png", mask, fmt="PNG")
        parts.append({
            "name": name,
            "mask_url": url,
            "uv_region": {"u_min": 0.0, "v_min": y0 / h, "u_max": 1.0, "v_max": y1 / h},
            "part_type": _classify(name),
            "editable": True,
        })
    return parts


def _classify(name: str) -> str:
    n = name.lower()
    if "label" in n or "wordmark" in n or "mark" in n:
        return "label"
    if "logo" in n:
        return "logo_target"
    if n in {"ornament", "decoration", "trim"}:
        return "decoration"
    return "structural"


def _real_grounded_sam(source_image_url: str, part_names: List[str]) -> List[Dict]:
    """Load GroundingDINO for boxes, SAM 2.1 for masks. Lazy import."""
    import torch
    from groundingdino.util.inference import load_model, predict, load_image  # noqa: F401

    # NOTE: full real path is environment-dependent (checkpoint paths, config yamls).
    # This branch is a placeholder; production implementation lives in Week 2.
    # For now, fall back to mock so the pipeline stays operational.
    raise RuntimeError("real-grounded-sam not wired yet; set V2_REAL_SEGMENTER only after Phase-0 verify step")
