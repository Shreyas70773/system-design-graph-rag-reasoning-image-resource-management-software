"""Brand-conditioned layer inpainting.

Core idea
---------
We treat the mask as the source of truth for preservation. Whatever backend we
use to generate the edited pixels, the compositor then pastes only the masked
region back into the original image — so pixels outside the mask are
byte-identical, regardless of model.

Preferred backend: OpenRouter "Nano Banana" (google/gemini-2.5-flash-image)
for **non-text** region edits only. Text on canvas is handled by Pillow in
``text_overlay.py``, not by this module.

It does not accept a mask natively, so we crop the padded mask bbox, edit that
crop, and put it back. The compositor enforces preservation.

Priority ladder (first success wins):
  1. OpenRouter Nano Banana  — crop-edit path (objects, materials, lighting)
  2. Replicate FLUX Fill Dev — native masked inpainting (if Replicate has credit)
  3. Replicate SDXL Inpainting — classic masked inpainting fallback
  4. Pillow brand-colour tint — last-resort mock so the UI never hangs
"""
from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
from typing import Dict, List, Optional, Tuple

import httpx
from PIL import Image, ImageFilter

from app.rendering.storage import fetch_image_bytes, save_pil
from app.layers.compositor import sanitize_palette_hex

logger = logging.getLogger(__name__)

_FLUX_FILL_MODEL = "black-forest-labs/flux-fill-dev"
_SD_INPAINT_MODEL = (
    "stability-ai/stable-diffusion-inpainting:"
    "95b7223104132402a9ae91cc677285bc5eb997834bd2349fa486f53910fd68b3"
)
_NANO_BANANA = "google/gemini-2.5-flash-image"
_CROP_PAD_RATIO = 0.20   # 20 % padding around mask bbox so the model sees context
_CROP_MIN_SIDE = 64
_CROP_MAX_SIDE = 1536    # keep payload sane


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def inpaint(
    image_url: str,
    mask_url: str,
    prompt: str,
    brand_conditioning: Dict,
    seed: Optional[int] = None,
) -> Dict:
    """
    Inpaint the masked region (image models only — no text-replace here).

    Returns {result_url, method, prompt_used, conditioning_applied, attempts}.
    """
    conditioned_prompt, applied = _build_conditioned_prompt(prompt, brand_conditioning)

    attempts: List[str] = []

    # 1 — Nano Banana (crop-edit)
    or_key = os.environ.get("OPENROUTER_API_KEY", "")
    if or_key:
        try:
            result = _nano_banana_edit(image_url, mask_url, conditioned_prompt, or_key)
            result["conditioning_applied"] = applied
            attempts.append("nano_banana:ok")
            result["attempts"] = attempts
            return result
        except Exception as exc:
            attempts.append(f"nano_banana:failed ({type(exc).__name__}: {exc})")
            logger.warning("Nano Banana edit failed: %s", exc)

    # 2/3 — Replicate backends
    rep_token = os.environ.get("REPLICATE_API_TOKEN", "")
    if rep_token:
        try:
            result = _replicate_flux_fill(image_url, mask_url, conditioned_prompt, seed, rep_token)
            result["conditioning_applied"] = applied
            attempts.append("replicate_flux_fill:ok")
            result["attempts"] = attempts
            return result
        except Exception as exc:
            attempts.append(f"replicate_flux_fill:failed ({type(exc).__name__}: {exc})")
            logger.warning("FLUX Fill failed: %s", exc)
        try:
            result = _replicate_sd_inpaint(image_url, mask_url, conditioned_prompt, seed, rep_token)
            result["conditioning_applied"] = applied
            attempts.append("replicate_sd_inpaint:ok")
            result["attempts"] = attempts
            return result
        except Exception as exc:
            attempts.append(f"replicate_sd_inpaint:failed ({type(exc).__name__}: {exc})")
            logger.warning("SD inpaint failed: %s", exc)

    # 4 — Pillow mock so the UI never hangs
    attempts.append("falling_back_to_mock_tint")
    result = _mock_tint(image_url, mask_url, brand_conditioning, prompt)
    result["conditioning_applied"] = applied
    result["attempts"] = attempts
    return result


# ---------------------------------------------------------------------------
# Prompt shaping
# ---------------------------------------------------------------------------

def _build_conditioned_prompt(
    base_prompt: str,
    brand_conditioning: Dict,
) -> Tuple[str, Dict]:
    """Return a strong natural-language edit instruction + audit dict."""
    applied: Dict = {}

    tokens: List[str] = []
    style_kw = brand_conditioning.get("style_keywords", [])
    if style_kw:
        tokens.extend(style_kw[:4])
        applied["style_keywords"] = style_kw[:4]

    palette = sanitize_palette_hex([str(x) for x in brand_conditioning.get("palette_hex", [])])
    if palette:
        hex_str = ", ".join(palette[:3])
        tokens.append(f"use brand colours {hex_str}")
        applied["palette_hex"] = palette[:3]

    voice = brand_conditioning.get("notes", {}).get("voice", "")
    if voice:
        tokens.append(voice)
        applied["voice"] = voice

    base = base_prompt.strip() or "improve this region"
    seed_instruction = (
        f"Edit the highlighted region: {base}. "
        "Match the lighting, perspective, and materials of the surrounding image. "
        "Do not add text. Do not alter anything outside the highlighted region."
    )
    if tokens:
        seed_instruction = f"{seed_instruction} Style: {', '.join(tokens)}."
    applied["mode"] = "region_edit"
    return seed_instruction, applied


# ---------------------------------------------------------------------------
# Nano Banana (OpenRouter) crop-edit path
# ---------------------------------------------------------------------------

def _nano_banana_edit(
    image_url: str, mask_url: str, prompt: str, api_key: str
) -> Dict:
    """Crop the padded mask bbox, edit with Nano Banana, paste back into full canvas."""
    src = Image.open(io.BytesIO(fetch_image_bytes(image_url))).convert("RGB")
    mask = Image.open(io.BytesIO(fetch_image_bytes(mask_url))).convert("L")
    if mask.size != src.size:
        mask = mask.resize(src.size, Image.NEAREST)

    bbox = _padded_bbox(mask, src.size, pad_ratio=_CROP_PAD_RATIO)
    if bbox is None:
        raise RuntimeError("mask is empty — nothing to edit")

    crop = src.crop(bbox)
    crop_size = crop.size
    # Respect model's max side
    if max(crop_size) > _CROP_MAX_SIDE:
        scale = _CROP_MAX_SIDE / max(crop_size)
        crop = crop.resize(
            (int(crop_size[0] * scale), int(crop_size[1] * scale)),
            Image.LANCZOS,
        )

    buf = io.BytesIO()
    crop.save(buf, format="PNG")
    crop_bytes = buf.getvalue()
    cw, ch = crop.size

    edited_bytes = asyncio.run(_call_nano_banana(crop_bytes, prompt, api_key, cw, ch))
    edited = Image.open(io.BytesIO(edited_bytes)).convert("RGB")

    # Resize back to the exact bbox size so paste lines up pixel-for-pixel
    edited = edited.resize((bbox[2] - bbox[0], bbox[3] - bbox[1]), Image.LANCZOS)

    # Build a full-size canvas where everything outside bbox = original
    canvas = src.copy()
    canvas.paste(edited, (bbox[0], bbox[1]))

    result_url = save_pil("inpaints/nano_banana", "result.png", canvas, fmt="PNG")
    return {
        "result_url": result_url,
        "method": f"openrouter/{_NANO_BANANA}",
        "prompt_used": prompt,
    }


async def _call_nano_banana(
    image_bytes: bytes,
    prompt: str,
    api_key: str,
    crop_w: int,
    crop_h: int,
) -> bytes:
    """Send one crop + edit brief to Gemini image via OpenRouter.

    Content order: image first (better tool adherence), then a short structured brief.
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:image/png;base64,{b64}"
    user_text = (
        f"[REGION_EDIT]\n"
        f"Canvas: {crop_w}×{crop_h} px — output MUST be exactly this size (no borders, frames, captions).\n"
        f"Task: {prompt}\n"
        f"Rules: change only what the task requires; keep edges seamless with context."
    )
    payload = {
        "model": _NANO_BANANA,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a precise image patch editor. "
                    "Return exactly one edited image as your primary output. "
                    "Match resolution and aspect ratio of the provided crop. "
                    "No watermarks or UI chrome."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url, "detail": "high"},
                    },
                    {"type": "text", "text": user_text},
                ],
            },
        ],
        "modalities": ["image", "text"],
        "max_tokens": 8192,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://brand-content-generator.app",
        "X-Title": "Brand Layer Studio",
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"OpenRouter HTTP {resp.status_code}: {resp.text[:500]}")
        result = resp.json()

    message = result.get("choices", [{}])[0].get("message", {})
    # Preferred path: message.images[*].image_url.url
    image_url: Optional[str] = None
    for img in message.get("images", []) or []:
        if not isinstance(img, dict):
            continue
        u = img.get("image_url", {})
        if isinstance(u, dict):
            image_url = u.get("url")
        elif isinstance(u, str):
            image_url = u
        if image_url:
            break

    # Fallback: inline content image
    if not image_url:
        content = message.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "image_url":
                        url_obj = item.get("image_url")
                        if isinstance(url_obj, dict):
                            image_url = url_obj.get("url")
                        elif isinstance(url_obj, str):
                            image_url = url_obj
                        if image_url:
                            break
                    inline = item.get("inline_data")
                    if isinstance(inline, dict) and "data" in inline:
                        mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                        image_url = f"data:{mime};base64,{inline['data']}"
                        break
        elif isinstance(content, str) and content.startswith("data:image"):
            image_url = content

    if not image_url:
        raise RuntimeError(
            "Nano Banana returned no image (usually a content filter or rate limit)."
        )

    if image_url.startswith("data:"):
        _, _, payload_b64 = image_url.partition(",")
        return base64.b64decode(payload_b64)

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(image_url)
        r.raise_for_status()
        return r.content


def _padded_bbox(
    mask: Image.Image, image_size: Tuple[int, int], pad_ratio: float
) -> Optional[Tuple[int, int, int, int]]:
    """Bounding box of the mask + padding, clamped to the image."""
    bbox = mask.getbbox()
    if bbox is None:
        return None
    x0, y0, x1, y1 = bbox
    w, h = image_size
    bw, bh = x1 - x0, y1 - y0
    pad_x = int(bw * pad_ratio)
    pad_y = int(bh * pad_ratio)
    x0 = max(0, x0 - pad_x)
    y0 = max(0, y0 - pad_y)
    x1 = min(w, x1 + pad_x)
    y1 = min(h, y1 + pad_y)
    # Enforce minimum side
    if (x1 - x0) < _CROP_MIN_SIDE:
        cx = (x0 + x1) // 2
        x0 = max(0, cx - _CROP_MIN_SIDE // 2)
        x1 = min(w, x0 + _CROP_MIN_SIDE)
    if (y1 - y0) < _CROP_MIN_SIDE:
        cy = (y0 + y1) // 2
        y0 = max(0, cy - _CROP_MIN_SIDE // 2)
        y1 = min(h, y0 + _CROP_MIN_SIDE)
    return (x0, y0, x1, y1)


# ---------------------------------------------------------------------------
# Replicate fallbacks (native masked inpainting)
# ---------------------------------------------------------------------------

def _replicate_flux_fill(image_url, mask_url, prompt, seed, token) -> Dict:
    import replicate

    os.environ["REPLICATE_API_TOKEN"] = token
    img_bytes = fetch_image_bytes(image_url)
    mask_bytes = fetch_image_bytes(mask_url)

    output = replicate.run(
        _FLUX_FILL_MODEL,
        input={
            "image": io.BytesIO(img_bytes),
            "mask": io.BytesIO(mask_bytes),
            "prompt": prompt,
            "num_inference_steps": 28,
            "guidance": 30,
            "seed": seed or 42,
            "output_format": "png",
        },
    )
    result_url = str(list(output)[0]) if not isinstance(output, str) else output
    return {"result_url": result_url, "method": "replicate/flux-fill-dev", "prompt_used": prompt}


def _replicate_sd_inpaint(image_url, mask_url, prompt, seed, token) -> Dict:
    import replicate

    os.environ["REPLICATE_API_TOKEN"] = token
    img_bytes = fetch_image_bytes(image_url)
    mask_bytes = fetch_image_bytes(mask_url)

    output = replicate.run(
        _SD_INPAINT_MODEL,
        input={
            "image": io.BytesIO(img_bytes),
            "mask_image": io.BytesIO(mask_bytes),
            "prompt": prompt,
            "num_inference_steps": 30,
            "guidance_scale": 7.5,
            "seed": seed or 42,
        },
    )
    result_url = str(list(output)[0]) if not isinstance(output, str) else output
    return {"result_url": result_url, "method": "replicate/sd-inpainting", "prompt_used": prompt}


# ---------------------------------------------------------------------------
# Last-resort mock so the UI never hangs
# ---------------------------------------------------------------------------

def _mock_tint(image_url: str, mask_url: str, brand_conditioning: Dict, prompt: str) -> Dict:
    img = Image.open(io.BytesIO(fetch_image_bytes(image_url))).convert("RGB")
    mask = Image.open(io.BytesIO(fetch_image_bytes(mask_url))).convert("L")

    palette = sanitize_palette_hex([str(x) for x in brand_conditioning.get("palette_hex", [])]) or ["#6366f1"]
    primary = palette[0].lstrip("#")
    r, g, b = int(primary[0:2], 16), int(primary[2:4], 16), int(primary[4:6], 16)

    overlay = Image.new("RGB", img.size, (r, g, b))
    blended = Image.blend(img, overlay, alpha=0.45)
    blended = blended.filter(ImageFilter.SMOOTH_MORE)

    result = img.copy()
    result.paste(blended, mask=mask)

    result_url = save_pil("inpaints/mock", "result.png", result, fmt="PNG")
    return {
        "result_url": result_url,
        "method": "mock/pillow_tint",
        "prompt_used": prompt,
    }
