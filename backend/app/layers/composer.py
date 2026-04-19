"""Initial full-image composition — real backends only (no fake product art).

Priority ladder (first success wins):
  1. OpenRouter Nano Banana  (OPENROUTER_API_KEY) — `google/gemini-2.5-flash-image`
     Strong text-in-image + brand reasoning, and matches the inpainting backend
     so the canvas and the edits share the same visual language.
  2. Replicate FLUX Schnell  (REPLICATE_API_TOKEN)
  3. Existing marketing pipeline: ComfyUI FLUX → Hugging Face SDXL
     (same as /api/generate) — needs a minimal brand_context dict

If every backend fails, the API returns HTTP 502 with a detail string listing
attempts. We deliberately do **not** draw a pretend "product on gradient" canvas;
that was misleading when cloud credits run out.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from app.rendering.storage import put_bytes

logger = logging.getLogger(__name__)

_FLUX_SCHNELL = "black-forest-labs/flux-schnell"
_OPENROUTER_MODEL = "google/gemini-2.5-flash-image"


def _build_prompt(base: str, conditioning: Dict[str, Any]) -> str:
    tokens: List[str] = []
    kw = conditioning.get("style_keywords", [])
    if kw:
        tokens.extend(str(k) for k in kw[:4])
    palette = conditioning.get("palette_hex", [])
    if palette:
        tokens.append(f"brand colour palette {' '.join(str(p) for p in palette[:3])}")
    if tokens:
        return ", ".join(tokens) + ", " + base
    return base


def _persist_if_data_url(url: str) -> str:
    """Store data URLs under /uploads/v2 so segment/edit can read them locally."""
    if not url.startswith("data:"):
        return url
    header, payload = url.split(",", 1)
    raw = base64.b64decode(payload)
    mime = "image/png"
    if "jpeg" in header.lower() or "jpg" in header.lower():
        mime = "image/jpeg"
    elif "webp" in header.lower():
        mime = "image/webp"
    return put_bytes("composites/generated", "composed.png", raw, mime)


async def _try_replicate(
    prompt: str, aspect_ratio: str, seed: Optional[int], token: str
) -> Optional[Dict[str, Any]]:
    import replicate

    os.environ["REPLICATE_API_TOKEN"] = token

    def _run():
        return replicate.run(
            _FLUX_SCHNELL,
            input={
                "prompt": prompt,
                "num_outputs": 1,
                "aspect_ratio": aspect_ratio,
                "output_format": "png",
                "seed": seed or 42,
            },
        )

    output = await asyncio.to_thread(_run)
    url = str(list(output)[0]) if not isinstance(output, str) else output
    return {"image_url": url, "method": "replicate/flux-schnell", "prompt_used": prompt}


async def _try_marketing_pipeline(
    brand_context: Dict[str, Any],
    prompt: str,
    aspect_ratio: str,
) -> Optional[Dict[str, Any]]:
    from app.generation.image_generator import generate_marketing_image

    res = await generate_marketing_image(
        brand_context,
        prompt,
        style=None,
        negative_prompt=None,
        aspect_ratio=aspect_ratio,
    )
    url = res.get("url")
    if not url:
        return None
    stored = _persist_if_data_url(url)
    prov = res.get("provider", "unknown")
    model = res.get("model_used", "")
    return {
        "image_url": stored,
        "method": f"pipeline/{prov}:{model}",
        "prompt_used": res.get("prompt_used", prompt),
    }


async def _try_openrouter(conditioned_prompt: str) -> Optional[Dict[str, Any]]:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return None

    payload = {
        "model": _OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": conditioned_prompt}],
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
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        if response.status_code != 200:
            raise RuntimeError(f"OpenRouter HTTP {response.status_code}: {response.text[:500]}")

        result = response.json()
    message = result.get("choices", [{}])[0].get("message", {})
    images = message.get("images", [])
    image_url = None
    for img in images:
        if not isinstance(img, dict):
            continue
        img_url_obj = img.get("image_url", {})
        if isinstance(img_url_obj, dict):
            image_url = img_url_obj.get("url")
        elif isinstance(img_url_obj, str):
            image_url = img_url_obj
        if image_url:
            break

    if not image_url and isinstance(message.get("content"), str):
        c = message["content"]
        if c.startswith("data:image"):
            image_url = c

    if not image_url:
        raise RuntimeError("OpenRouter returned no image in the response")

    stored = _persist_if_data_url(image_url)
    return {
        "image_url": stored,
        "method": f"openrouter/{_OPENROUTER_MODEL}",
        "prompt_used": conditioned_prompt,
    }


async def compose_image_async(
    prompt: str,
    brand_conditioning: Dict[str, Any],
    brand_context: Dict[str, Any],
    aspect_ratio: str = "1:1",
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate a real composition. Raises RuntimeError if every backend fails.

    Returns image_url, method, prompt_used, attempts (list of status strings).
    """
    conditioned = _build_prompt(prompt, brand_conditioning)
    attempts: List[str] = []

    # 1 — OpenRouter Nano Banana (primary)
    try:
        out = await _try_openrouter(conditioned)
        if out:
            attempts.append("openrouter:ok")
            out["attempts"] = attempts
            return out
        attempts.append("openrouter:no_key")
    except Exception as exc:
        attempts.append(f"openrouter:failed ({exc})")
        logger.warning("OpenRouter compose failed: %s", exc)

    # 2 — Replicate FLUX Schnell
    rep_token = os.environ.get("REPLICATE_API_TOKEN", "")
    if rep_token:
        try:
            out = await _try_replicate(conditioned, aspect_ratio, seed, rep_token)
            if out:
                attempts.append("replicate:ok")
                out["attempts"] = attempts
                return out
        except Exception as exc:
            attempts.append(f"replicate:failed ({exc})")
            logger.warning("Replicate compose failed: %s", exc)
    else:
        attempts.append("replicate:no_token")

    # 3 — ComfyUI / Hugging Face (existing app pipeline)
    try:
        out = await _try_marketing_pipeline(brand_context, prompt, aspect_ratio)
        if out and out.get("image_url"):
            attempts.append("marketing_pipeline:ok")
            out["attempts"] = attempts
            return out
        attempts.append("marketing_pipeline:no_url")
    except Exception as exc:
        attempts.append(f"marketing_pipeline:failed ({exc})")
        logger.warning("Marketing pipeline compose failed: %s", exc)

    raise RuntimeError(
        "Could not generate an image. Tried: OpenRouter Nano Banana → Replicate FLUX → Comfy/HF SDXL. "
        f"Details: {'; '.join(attempts)}. "
        "Ensure OPENROUTER_API_KEY has access to google/gemini-2.5-flash-image, "
        "or add Replicate billing, or run ComfyUI + FLUX / set HUGGINGFACE_TOKEN for SDXL fallback."
    )
