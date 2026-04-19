"""Step 4 — delight (IntrinsicAnything real + PIL-heuristic mock)."""

from __future__ import annotations

import io
import logging
from typing import Dict

from PIL import Image, ImageEnhance, ImageOps

from app.config_v2 import get_v2_settings
from app.rendering.capabilities import detect
from app.rendering.storage import fetch_image_bytes, save_pil

logger = logging.getLogger(__name__)


def run(source_image_url: str) -> Dict:
    settings = get_v2_settings()
    caps = detect()
    use_real = (not settings.mock_mode or settings.force_real_delighter) \
        and caps.intrinsic_anything and caps.torch_cuda
    if use_real:
        try:
            return _real(source_image_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Delighter real path failed (%s); using mock", exc)
    return _mock(source_image_url)


def _mock(source_image_url: str) -> Dict:
    data = fetch_image_bytes(source_image_url)
    img = Image.open(io.BytesIO(data)).convert("RGB")

    # Approximate albedo: flatten to midtones via auto-contrast + desaturated lift.
    albedo = ImageOps.autocontrast(img, cutoff=4)
    albedo = ImageEnhance.Brightness(albedo).enhance(1.05)
    # Normal-ish map from edge magnitude (stand-in; not geometrically correct).
    gray = ImageOps.grayscale(img).filter_edge()  # type: ignore[attr-defined]
    albedo_url = save_pil("delight/albedo", "albedo.png", albedo)

    return {
        "albedo_url": albedo_url,
        "albedo_dominant_hex": _dominant_hex(albedo),
        "light_probe": {
            "hdri_url": None,
            "estimated_direction": [0.2, 1.0, 0.4],
            "estimated_color_temp_k": 5600,
            "estimated_intensity": 1.0,
            "confidence": 0.5,
        },
    }


def _dominant_hex(img: Image.Image) -> str:
    small = img.resize((8, 8)).quantize(colors=3)
    rgb = small.convert("RGB").getcolors(maxcolors=256) or [(1, (128, 128, 128))]
    rgb.sort(reverse=True)
    _, (r, g, b) = rgb[0]
    return f"#{r:02x}{g:02x}{b:02x}"


def _real(source_image_url: str) -> Dict:
    # Environment-dependent. Stub raises to trigger fallback until properly wired.
    raise RuntimeError("real delighter not wired; re-enable after installing IntrinsicAnything")


# Filter-edge shim for PIL compatibility (old versions). Pillow provides ImageFilter.FIND_EDGES.
def _monkey_patch():
    from PIL import ImageFilter

    def filter_edge(self):  # type: ignore[misc]
        return self.filter(ImageFilter.FIND_EDGES)

    Image.Image.filter_edge = filter_edge  # type: ignore[attr-defined]


_monkey_patch()
