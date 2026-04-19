"""Pipeline B Stage 4 — Blender render via subprocess.

In mock mode (Blender CLI not available or V2_MOCK_MODE=true), we synthesise
a plausible 2D previz render + depth + normal + object-ID passes using PIL.
This is enough to exercise the rest of the pipeline end-to-end; the real
Blender subprocess will slot in here once Blender 4.2+ is installed.
"""

from __future__ import annotations

import io
import logging
import math
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFilter

from app.config_v2 import get_v2_settings
from app.rendering.capabilities import detect
from app.rendering.storage import save_pil

logger = logging.getLogger(__name__)


def render_scene(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Render every camera. Returns list of render dicts."""
    settings = get_v2_settings()
    caps = detect()
    use_real = (not settings.mock_mode or settings.force_real_blender) and caps.blender_cli
    if use_real:
        try:
            return _real_blender(plan)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Blender real path failed (%s); using PIL previz", exc)
    return [_mock_render(plan, cam) for cam in plan.get("cameras", [])]


def _mock_render(plan: Dict[str, Any], cam: Dict[str, Any]) -> Dict[str, Any]:
    """Compose a previz image: placements painted as coloured rectangles on a
    sky-gradient background, with a matching object-ID pass for click-resolution.
    """
    w, h = cam["resolution_px"]
    brand_colors = plan.get("brand_context", {}).get("colors") or []
    primary = (brand_colors[0].get("hex") if brand_colors else "#2f5f9e")
    secondary = (brand_colors[1].get("hex") if len(brand_colors) > 1 else "#f5f5f5")

    rgb = _sky_gradient(w, h, _mix_hex("#87ceeb", primary, 0.15), _mix_hex("#ffffff", secondary, 0.2))
    depth = Image.new("L", (w, h), 180)
    normal = Image.new("RGB", (w, h), (128, 128, 255))
    id_pass = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    id_draw = ImageDraw.Draw(id_pass)
    rgb_draw = ImageDraw.Draw(rgb)
    depth_draw = ImageDraw.Draw(depth)

    # Place each placement as a proportional rectangle based on its X/Y + camera.
    for idx, p in enumerate(plan.get("placements", [])):
        cx, cy = _project_to_image(p.get("position", [0, 0, 0]), cam, w, h)
        size = max(60, int(min(w, h) * 0.22))
        box = (cx - size // 2, cy - size // 2, cx + size // 2, cy + size // 2)
        colour = _deterministic_colour(p.get("asset_id", str(idx)))
        rgb_draw.rectangle(box, fill=colour, outline=primary, width=4)
        id_bytes = _placement_to_id_color(p["id"], idx)
        id_draw.rectangle(box, fill=id_bytes)
        depth_draw.rectangle(box, fill=120)

    # Lights → simple brightness adjust on RGB.
    rgb = _apply_lighting(rgb, plan.get("lights", []))

    # Text layers are composited in a later stage, not here.

    rgb_url = save_pil("renders", f"{plan['scene_id']}-{cam['id']}-rgb.png", rgb, fmt="PNG")
    depth_url = save_pil("renders", f"{plan['scene_id']}-{cam['id']}-depth.png", depth, fmt="PNG")
    normal_url = save_pil("renders", f"{plan['scene_id']}-{cam['id']}-normal.png", normal, fmt="PNG")
    id_url = save_pil("renders", f"{plan['scene_id']}-{cam['id']}-ids.png", id_pass, fmt="PNG")

    return {
        "camera_id": cam["id"],
        "rgb_url": rgb_url,
        "depth_url": depth_url,
        "normal_url": normal_url,
        "object_id_pass_url": id_url,
        "render_time_sec": 0.0,
        "backend": "mock-pil",
    }


def _sky_gradient(w: int, h: int, top_hex: str, bottom_hex: str) -> Image.Image:
    img = Image.new("RGB", (w, h))
    top = _hex_to_rgb(top_hex)
    bot = _hex_to_rgb(bottom_hex)
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top[0] * (1 - t) + bot[0] * t)
        g = int(top[1] * (1 - t) + bot[1] * t)
        b = int(top[2] * (1 - t) + bot[2] * t)
        for x in range(w):
            img.putpixel((x, y), (r, g, b))
    # Slight blur for softness.
    return img.filter(ImageFilter.GaussianBlur(radius=1))


def _hex_to_rgb(hx: str) -> Tuple[int, int, int]:
    hx = hx.lstrip("#")
    return int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)


def _mix_hex(a: str, b: str, t: float) -> str:
    ar, ag, ab = _hex_to_rgb(a)
    br, bg, bb = _hex_to_rgb(b)
    r = int(ar * (1 - t) + br * t)
    g = int(ag * (1 - t) + bg * t)
    bch = int(ab * (1 - t) + bb * t)
    return f"#{r:02x}{g:02x}{bch:02x}"


def _project_to_image(pos: List[float], cam: Dict[str, Any], w: int, h: int) -> Tuple[int, int]:
    # Simplified projection: look from cam.position toward cam.target.
    # We convert scene-space X/Y directly into centred image coords.
    px, py, pz = pos
    cam_z = cam["position"][2] or 2.5
    scale = 180.0 / max(0.1, cam_z)
    cx = int(w // 2 + px * scale)
    cy = int(h // 2 - py * scale)
    return max(0, min(w - 1, cx)), max(0, min(h - 1, cy))


def _deterministic_colour(key: str) -> Tuple[int, int, int]:
    import hashlib
    d = hashlib.sha256(key.encode()).digest()
    return d[0] | 64, d[1] | 64, d[2] | 64


def _placement_to_id_color(placement_id: str, idx: int) -> Tuple[int, int, int, int]:
    """Encode placement ID as an RGBA colour in the object-ID pass.

    Uses a 24-bit index (1..2^24-1); alpha always 255. Reversed by the
    picking endpoint via a per-scene lookup map (stored elsewhere).
    """
    i = (idx + 1) & 0xFFFFFF
    return ((i >> 16) & 0xFF, (i >> 8) & 0xFF, i & 0xFF, 255)


def _apply_lighting(img: Image.Image, lights: List[Dict[str, Any]]) -> Image.Image:
    if not lights:
        return img
    # Combine intensity multipliers.
    mult = sum(l.get("intensity", 1.0) for l in lights) / max(1, len(lights))
    from PIL import ImageEnhance
    return ImageEnhance.Brightness(img).enhance(min(1.5, max(0.6, 0.6 + 0.4 * mult)))


def _real_blender(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    raise RuntimeError("Blender real path not wired; keep V2_REAL_BLENDER off until blender_script.py finalised")
