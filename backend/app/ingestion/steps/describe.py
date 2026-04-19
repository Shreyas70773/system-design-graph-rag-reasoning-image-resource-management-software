"""Step 2 — VLM describe (Qwen2.5-VL-7B AWQ real + heuristic mock)."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Dict, List, Optional, Tuple

from app.config_v2 import get_v2_settings
from app.rendering.capabilities import detect
from app.rendering.storage import fetch_image_bytes

logger = logging.getLogger(__name__)

_DEFAULT_PARTS = {
    "product": ["cap", "neck", "body", "front_label", "base"],
    "logo": ["mark", "wordmark"],
    "character_ref": ["face", "hair", "torso_garment", "legs_garment", "footwear"],
    "texture": ["whole"],
    "environment_ref": ["sky", "ground", "mid_ground"],
}


def run(source_image_url: str, asset_type: str) -> Dict:
    settings = get_v2_settings()
    caps = detect()
    use_real = (not settings.mock_mode or settings.force_real_vlm) and caps.transformers and caps.torch_cuda
    if use_real:
        try:
            return _real_qwen_vl(source_image_url, asset_type)
        except Exception as exc:  # noqa: BLE001
            logger.warning("VLM real path failed (%s); falling back to mock", exc)
    return _mock(source_image_url, asset_type)


def _mock(source_image_url: str, asset_type: str) -> Dict:
    """Heuristic fallback: use ColorThief for palette; descriptor from asset_type."""
    try:
        data = fetch_image_bytes(source_image_url)
        palette = _palette_from_bytes(data)
    except Exception:
        palette = ["#7a7a7a", "#cccccc", "#303030"]

    parts = _DEFAULT_PARTS.get(asset_type, ["whole"])
    description = _canned_description(asset_type, palette[0])

    return {
        "description": description,
        "material_class": "mixed",
        "estimated_parts": parts,
        "palette_hex": palette[:3],
        "confidence": 0.55,  # deliberately low so downstream knows this is mock
        "vlm_model": "mock/heuristic@1",
        "clip_embedding": _pseudo_embedding(source_image_url),
    }


def _canned_description(asset_type: str, first_hex: str) -> str:
    base = {
        "product": f"Product reference photograph with dominant {first_hex} tone",
        "logo": f"Brand logo mark, primary colour {first_hex}",
        "character_ref": "Character reference pose used for identity conditioning",
        "texture": "Surface texture reference for material mapping",
        "environment_ref": "Environment/background reference for scene context",
    }
    return base.get(asset_type, "Brand asset reference.") + " (mock description)"


def _palette_from_bytes(data: bytes) -> List[str]:
    try:
        import io as _io
        from PIL import Image
        img = Image.open(_io.BytesIO(data)).convert("RGB").resize((64, 64))
        # Reduce to 5 dominant colours via Pillow quantize.
        q = img.quantize(colors=5)
        pal = q.getpalette() or []
        colours: List[Tuple[int, Tuple[int, int, int]]] = []
        hist = q.convert("RGB").getcolors(maxcolors=4096) or []
        hist.sort(reverse=True)
        for count, rgb in hist[:5]:
            colours.append((count, rgb))
        if not colours:
            return ["#808080"]
        return [f"#{r:02x}{g:02x}{b:02x}" for _, (r, g, b) in colours]
    except Exception:
        return ["#7a7a7a"]


def _pseudo_embedding(seed: str) -> List[float]:
    """Deterministic 768-dim pseudo-embedding so mocked flows are reproducible."""
    digest = hashlib.sha256(seed.encode()).digest()
    # Expand 32 bytes into 768 floats in [-1, 1].
    floats: List[float] = []
    for i in range(768):
        b = digest[i % len(digest)]
        shift = (i // len(digest)) % 7
        val = ((b >> shift) & 0xFF) / 128.0 - 1.0
        floats.append(round(val, 6))
    return floats


def _real_qwen_vl(source_image_url: str, asset_type: str) -> Dict:
    """Real path: load Qwen2.5-VL-7B AWQ and run description + parts extraction.

    Loaded lazily because imports are expensive. Must fully unload on exit.
    """
    import torch
    from PIL import Image
    import io as _io
    from transformers import AutoModelForVision2Seq, AutoProcessor

    model_id = "Qwen/Qwen2.5-VL-7B-Instruct-AWQ"
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForVision2Seq.from_pretrained(
        model_id, torch_dtype=torch.float16, device_map="cuda", trust_remote_code=True,
    )

    prompt_path = _prompt_path()
    instructions = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""

    data = fetch_image_bytes(source_image_url)
    img = Image.open(_io.BytesIO(data)).convert("RGB")

    messages = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": [
            {"type": "image", "image": img},
            {"type": "text", "text": f"asset_type={asset_type}. Return JSON only."},
        ]},
    ]
    try:
        inputs = processor.apply_chat_template(messages, tokenize=True, return_tensors="pt").to("cuda")
    except Exception:
        # Fallback to basic processor call if chat template fails.
        inputs = processor(text=f"asset_type={asset_type}", images=img, return_tensors="pt").to("cuda")
    with torch.inference_mode():
        out = model.generate(**{k: v for k, v in inputs.items()}, max_new_tokens=512)
    text = processor.batch_decode(out, skip_special_tokens=True)[0]
    parsed = _coerce_json(text, asset_type)

    # Release model immediately.
    del model, processor
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    parsed["vlm_model"] = f"{model_id}@real"
    parsed["clip_embedding"] = _clip_embedding(img)
    return parsed


def _prompt_path():
    from pathlib import Path as _P
    return _P(__file__).resolve().parents[1] / "prompts" / "describe.txt"


def _coerce_json(text: str, asset_type: str) -> Dict:
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
    except Exception:
        pass
    return {
        "description": text[:200] or "VLM produced no text",
        "material_class": "mixed",
        "estimated_parts": _DEFAULT_PARTS.get(asset_type, ["whole"]),
        "palette_hex": ["#7a7a7a", "#cccccc", "#303030"],
        "confidence": 0.4,
    }


def _clip_embedding(img) -> Optional[List[float]]:
    try:
        import torch
        from transformers import CLIPModel, CLIPProcessor
        model_id = "openai/clip-vit-large-patch14"
        proc = CLIPProcessor.from_pretrained(model_id)
        clip = CLIPModel.from_pretrained(model_id, torch_dtype=torch.float16).to("cuda")
        with torch.inference_mode():
            inputs = proc(images=img, return_tensors="pt").to("cuda")
            feat = clip.get_image_features(**inputs)
            feat = feat / feat.norm(dim=-1, keepdim=True)
        out = feat[0].cpu().float().tolist()
        del clip, proc
        torch.cuda.empty_cache()
        # Pad or truncate to 768 (ViT-L is 768 already).
        return out[:768] + [0.0] * max(0, 768 - len(out))
    except Exception:
        return None
