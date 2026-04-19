"""Step 1 — intake and validation. CPU-only."""

from __future__ import annotations

import hashlib
from typing import Dict

from app.rendering.storage import fetch_image_bytes, put_bytes


def run_intake(source_image_url: str, asset_type: str) -> Dict:
    """Fetch the image, compute a hash, persist canonical copy, return metadata."""
    data = fetch_image_bytes(source_image_url)
    sha = hashlib.sha256(data).hexdigest()

    try:
        from PIL import Image
        import io as _io
        img = Image.open(_io.BytesIO(data))
        width, height = img.size
    except Exception:
        width, height = 0, 0

    # Minimum resolution rules per PIPELINE_A §Step 1.
    min_side = 512 if asset_type == "texture" else 1024
    if min(width or 0, height or 0) and min(width, height) < min_side:
        # Soft-warn: we proceed but flag low confidence downstream.
        low_res = True
    else:
        low_res = False

    canonical_url = put_bytes("assets/original", f"{sha[:12]}.bin", data, mime="image/png")
    return {
        "sha256": sha,
        "width": width,
        "height": height,
        "low_res": low_res,
        "canonical_url": canonical_url,
        "bytes_len": len(data),
    }
