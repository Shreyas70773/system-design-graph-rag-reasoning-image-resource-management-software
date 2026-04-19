"""Click-to-mask segmentation for layer editing.

Real path: SAM 2.1 with a single point prompt.
Mock path: elliptical mask centred on the click (20 % of image radius).
"""
from __future__ import annotations

import io
import logging
import math
from typing import Dict

from PIL import Image, ImageDraw

from app.rendering.storage import fetch_image_bytes, save_pil

logger = logging.getLogger(__name__)


def segment_from_click(
    image_url: str,
    click_x: float,
    click_y: float,
    label: str = "object",
    selection_scale: float = 1.0,
) -> Dict:
    """
    Return mask_url, bbox (pixel coords), area_fraction, method.

    click_x / click_y are normalised [0, 1].
    """
    try:
        return _real_sam(image_url, click_x, click_y, label)
    except Exception as exc:
        logger.info("SAM unavailable (%s) — using ellipse mock", exc)
    return _mock_ellipse(image_url, click_x, click_y, label, selection_scale=selection_scale)


def _mock_ellipse(
    image_url: str,
    click_x: float,
    click_y: float,
    label: str,
    selection_scale: float = 1.0,
) -> Dict:
    data = fetch_image_bytes(image_url)
    img = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = img.size

    cx = int(click_x * w)
    cy = int(click_y * h)

    scale = max(0.35, min(2.5, float(selection_scale or 1.0)))

    is_text = "text" in label.lower()
    if is_text:
        # Wide, shallow rounded rectangle — matches the typical aspect of a text line.
        rx = max(int(w * 0.28 * scale), 40)
        ry = max(int(h * 0.06 * scale), 14)
        shape = "rect"
    else:
        rx = max(int(w * 0.22 * scale), 20)
        ry = max(int(h * 0.22 * scale), 20)
        shape = "ellipse"

    x0, y0 = max(0, cx - rx), max(0, cy - ry)
    x1, y1 = min(w, cx + rx), min(h, cy + ry)

    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    if shape == "rect":
        radius = min(ry, 24)
        draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=255)
        area = (x1 - x0) * (y1 - y0) / (w * h)
    else:
        draw.ellipse([x0, y0, x1, y1], fill=255)
        area = math.pi * rx * ry / (w * h)

    mask_url = save_pil("masks", f"{label}-{cx}-{cy}.png", mask, fmt="PNG")

    return {
        "mask_url": mask_url,
        "bbox": [x0, y0, x1, y1],
        "img_width": w,
        "img_height": h,
        "area_fraction": round(min(area, 1.0), 4),
        "method": f"mock_{shape}",
    }


def _real_sam(image_url: str, click_x: float, click_y: float, label: str) -> Dict:
    """SAM 2.1 point-prompt path. Lazy-imported; raises if model not installed."""
    import numpy as np
    import torch
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor

    data = fetch_image_bytes(image_url)
    img = Image.open(io.BytesIO(data)).convert("RGB")
    arr = np.array(img)
    w, h = img.size

    device = "cuda" if torch.cuda.is_available() else "cpu"
    checkpoint = "checkpoints/sam2.1_hiera_large.pt"
    cfg = "configs/sam2.1/sam2.1_hiera_l.yaml"
    model = build_sam2(cfg, checkpoint, device=device)
    predictor = SAM2ImagePredictor(model)
    predictor.set_image(arr)

    point_coords = np.array([[click_x * w, click_y * h]])
    point_labels = np.array([1])
    masks, scores, _ = predictor.predict(
        point_coords=point_coords,
        point_labels=point_labels,
        multimask_output=True,
    )
    best = masks[int(np.argmax(scores))]
    mask_img = Image.fromarray((best * 255).astype(np.uint8), mode="L")

    ys, xs = np.where(best)
    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
    area = float(best.sum()) / (w * h)

    mask_url = save_pil("masks", f"{label}-sam.png", mask_img, fmt="PNG")
    return {
        "mask_url": mask_url,
        "bbox": [x0, y0, x1, y1],
        "img_width": w,
        "img_height": h,
        "area_fraction": round(area, 4),
        "method": "sam2.1",
    }
