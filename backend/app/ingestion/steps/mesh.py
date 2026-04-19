"""Step 5 — image → 3D mesh.

Priority chain
──────────────
1. TRELLIS (local, real ML — wired when verify_trellis.py passes).
2. TripoAI  (cloud, set env TRIPO_API_KEY)  → production-quality full 3-D mesh.
3. Meshy    (cloud, set env MESHY_API_KEY)  → production-quality full 3-D mesh.
4. Depth-mesh fallback — monocular depth → displaced plane (preview only).

TripoAI  : https://platform.tripo3d.ai  — free trial credits, 30-90 s per model.
Meshy    : https://meshy.ai             — free tier (200 credits/month), 30-90 s.

Both APIs accept a base64 data-URI so no public URL is required.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import os
import struct
import time
from typing import Dict, Optional, Tuple

import numpy as np
from PIL import Image

from app.config_v2 import get_v2_settings
from app.rendering.capabilities import detect
from app.rendering.storage import fetch_image_bytes, put_bytes

logger = logging.getLogger(__name__)

_GRID = 96
_DEPTH_SCALE = 0.40
_TEX_SIZE = 512
_TRIPO_UPLOAD = "https://api.tripo3d.ai/v2/openapi/upload"
_TRIPO_TASK   = "https://api.tripo3d.ai/v2/openapi/task"
_MESHY_CREATE = "https://api.meshy.ai/openapi/v1/image-to-3d"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(albedo_url: str, reference_url: str, asset_type: str) -> Dict:
    settings = get_v2_settings()
    caps = detect()

    # ── Real TRELLIS ────────────────────────────────────────────────────────
    if (not settings.mock_mode or settings.force_real_mesh) and caps.trellis and caps.torch_cuda:
        try:
            return _real_trellis(albedo_url, reference_url)
        except Exception as exc:
            logger.warning("TRELLIS failed (%s); trying cloud API", exc)

    image_bytes = fetch_image_bytes(albedo_url)

    # ── TripoAI ─────────────────────────────────────────────────────────────
    tripo_key = os.environ.get("TRIPO_API_KEY", "").strip()
    if tripo_key:
        try:
            logger.info("Submitting to TripoAI image_to_model …")
            glb_bytes = _tripo_image_to_3d(image_bytes, tripo_key)
            return _save_cloud_glb(glb_bytes, asset_type, albedo_url, "tripo-v2.5")
        except Exception as exc:
            logger.warning("TripoAI failed (%s); trying Meshy", exc)

    # ── Meshy ────────────────────────────────────────────────────────────────
    meshy_key = os.environ.get("MESHY_API_KEY", "").strip()
    if meshy_key:
        try:
            logger.info("Submitting to Meshy image-to-3d …")
            glb_bytes = _meshy_image_to_3d(image_bytes, meshy_key)
            return _save_cloud_glb(glb_bytes, asset_type, albedo_url, "meshy-4")
        except Exception as exc:
            logger.warning("Meshy failed (%s); falling back to depth mesh", exc)

    # ── Depth-mesh fallback ──────────────────────────────────────────────────
    if not tripo_key and not meshy_key:
        logger.warning(
            "No TRIPO_API_KEY or MESHY_API_KEY found — using depth-mesh preview. "
            "Set one of these env vars to get a real 3-D model."
        )
    return _depth_mesh(image_bytes, asset_type, albedo_url)


# ---------------------------------------------------------------------------
# TripoAI integration
# ---------------------------------------------------------------------------

def _tripo_image_to_3d(image_bytes: bytes, api_key: str) -> bytes:
    """Upload image → create task → poll → download GLB."""
    import httpx

    headers_auth = {"Authorization": f"Bearer {api_key}"}

    # Step 1: upload image to get a file_token.
    with httpx.Client(timeout=60) as client:
        up = client.post(
            _TRIPO_UPLOAD,
            headers=headers_auth,
            files={"file": ("asset.png", image_bytes, "image/png")},
        )
        up.raise_for_status()
        upload_data = up.json()

    # Tripo upload response schema: {"code":0,"data":{"image_token":"..."}}
    file_token = upload_data["data"]["image_token"]
    logger.debug("TripoAI file_token=%s", file_token[:12])

    # Step 2: create image_to_model task.
    with httpx.Client(timeout=30) as client:
        cr = client.post(
            _TRIPO_TASK,
            headers={**headers_auth, "Content-Type": "application/json"},
            json={
                "type": "image_to_model",
                "file": {"type": "png", "file_token": file_token},
                "model_version": "v2.5-20250123",
                "texture": True,
                "pbr": True,
                "texture_alignment": "original_image",
            },
        )
        cr.raise_for_status()
        task_id = cr.json()["data"]["task_id"]
    logger.info("TripoAI task_id=%s — polling …", task_id)

    # Step 3: poll until success or failure (max 8 min).
    for attempt in range(96):
        time.sleep(5)
        with httpx.Client(timeout=30) as client:
            poll = client.get(f"{_TRIPO_TASK}/{task_id}", headers=headers_auth)
            poll.raise_for_status()
            data = poll.json()["data"]

        status = data.get("status", "")
        logger.debug("TripoAI attempt=%d status=%s", attempt, status)
        if status == "success":
            glb_url = data["output"]["model"]
            with httpx.Client(timeout=120) as client:
                resp = client.get(glb_url)
                resp.raise_for_status()
            logger.info("TripoAI GLB downloaded (%d bytes)", len(resp.content))
            return resp.content
        if status in ("failed", "cancelled", "unknown"):
            msg = data.get("error", {}).get("message", status)
            raise RuntimeError(f"TripoAI task {status}: {msg}")

    raise TimeoutError("TripoAI task did not complete within 8 minutes")


# ---------------------------------------------------------------------------
# Meshy integration
# ---------------------------------------------------------------------------

def _meshy_image_to_3d(image_bytes: bytes, api_key: str) -> bytes:
    """Submit base64 image → poll → download GLB."""
    import httpx

    b64 = base64.b64encode(image_bytes).decode()
    data_uri = f"data:image/png;base64,{b64}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    with httpx.Client(timeout=30) as client:
        cr = client.post(
            _MESHY_CREATE,
            headers=headers,
            json={
                "image_url": data_uri,
                "enable_pbr": True,
                "should_remesh": True,
                "should_texture": True,
                "target_formats": ["glb"],
            },
        )
        cr.raise_for_status()
        task_id = cr.json()["result"]
    logger.info("Meshy task_id=%s — polling …", task_id)

    for attempt in range(96):
        time.sleep(5)
        with httpx.Client(timeout=30) as client:
            poll = client.get(f"{_MESHY_CREATE}/{task_id}", headers=headers)
            poll.raise_for_status()
            data = poll.json()

        status = data.get("status", "")
        logger.debug("Meshy attempt=%d status=%s progress=%s", attempt, status, data.get("progress"))
        if status == "SUCCEEDED":
            glb_url = data["model_urls"]["glb"]
            with httpx.Client(timeout=120) as client:
                resp = client.get(glb_url)
                resp.raise_for_status()
            logger.info("Meshy GLB downloaded (%d bytes)", len(resp.content))
            return resp.content
        if status in ("FAILED", "EXPIRED"):
            msg = data.get("task_error", {}).get("message", status)
            raise RuntimeError(f"Meshy task {status}: {msg}")

    raise TimeoutError("Meshy task did not complete within 8 minutes")


# ---------------------------------------------------------------------------
# Shared helper — save cloud GLB and return the mesh dict
# ---------------------------------------------------------------------------

def _save_cloud_glb(glb_bytes: bytes, asset_type: str, albedo_url: str, model: str) -> Dict:
    slug = hashlib.sha1(albedo_url.encode()).hexdigest()[:12]
    glb_url = put_bytes("meshes/cloud", f"{asset_type}-{slug}.glb", glb_bytes, mime="model/gltf-binary")
    verts = _count_glb_vertices(glb_bytes)
    return {
        "file_url": glb_url,
        "vertex_count": verts,
        "bbox_min": [-0.5, -0.5, -0.5],
        "bbox_max": [0.5, 0.5, 0.5],
        "canonical_scale_m": 0.3 if asset_type in ("product", "logo") else 1.8,
        "lod_level": 2,
        "generator_model": model,
        "generator_version": "1.0.0",
    }


def _count_glb_vertices(glb: bytes) -> int:
    """Best-effort vertex count by peeking at the JSON chunk of the GLB."""
    try:
        json_len = struct.unpack_from("<I", glb, 12)[0]
        gltf = json.loads(glb[20:20 + json_len])
        total = 0
        for acc in gltf.get("accessors", []):
            if acc.get("type") == "VEC3":
                total += acc.get("count", 0)
        return total or -1
    except Exception:
        return -1


# ---------------------------------------------------------------------------
# Depth-mesh fallback (preview only — not a real 3-D reconstruction)
# ---------------------------------------------------------------------------

def _depth_mesh(image_bytes: bytes, asset_type: str, albedo_url: str) -> Dict:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    depth_arr, gen_model = _estimate_depth(img)

    d_small = _resize_depth(depth_arr, _GRID)
    positions = _make_positions(d_small)
    uvs = _make_uvs(_GRID)
    indices = _make_indices(_GRID)
    texture_png = _make_texture_png(img, _TEX_SIZE)
    glb_bytes = _build_glb(positions, uvs, indices, texture_png)

    slug = hashlib.sha1(albedo_url.encode()).hexdigest()[:12]
    glb_url = put_bytes("meshes/depth", f"{asset_type}-{slug}.glb", glb_bytes, mime="model/gltf-binary")

    return {
        "file_url": glb_url,
        "vertex_count": int(_GRID * _GRID),
        "bbox_min": positions.min(axis=0).tolist(),
        "bbox_max": positions.max(axis=0).tolist(),
        "canonical_scale_m": 0.3 if asset_type in ("product", "logo") else 1.8,
        "lod_level": 0,
        "generator_model": f"depth-preview/{gen_model}",
        "generator_version": "1.0.0",
    }


def _estimate_depth(img: Image.Image) -> Tuple[np.ndarray, str]:
    try:
        import torch
        from transformers import pipeline as hf_pipe
        device = 0 if torch.cuda.is_available() else -1
        pipe = hf_pipe("depth-estimation", model="LiheYoung/depth-anything-small-hf", device=device)
        out = pipe(img)
        depth = np.array(out["depth"], dtype=np.float32)
        depth = (depth - depth.min()) / (depth.max() - depth.min() + 1e-6)
        return depth, "depth-anything-small"
    except Exception as exc:
        logger.warning("Depth model unavailable (%s); using luminance heuristic", exc)
        gray = np.array(img.convert("L"), dtype=np.float32) / 255.0
        return (gray - gray.min()) / (gray.max() - gray.min() + 1e-6), "luminance-heuristic"


def _resize_depth(depth: np.ndarray, g: int) -> np.ndarray:
    pil = Image.fromarray((depth * 255).astype(np.uint8)).resize((g, g), Image.BILINEAR)
    return np.array(pil, dtype=np.float32) / 255.0


def _make_positions(d: np.ndarray) -> np.ndarray:
    g = d.shape[0]
    xx, yy = np.meshgrid(np.linspace(-0.5, 0.5, g, dtype=np.float32),
                         np.linspace(-0.5, 0.5, g, dtype=np.float32))
    zz = d.astype(np.float32) * _DEPTH_SCALE - _DEPTH_SCALE * 0.5
    return np.stack([xx, -yy, zz], axis=-1).reshape(-1, 3)


def _make_uvs(g: int) -> np.ndarray:
    uu, vv = np.meshgrid(np.linspace(0, 1, g, dtype=np.float32),
                         np.linspace(1, 0, g, dtype=np.float32))
    return np.stack([uu, vv], axis=-1).reshape(-1, 2)


def _make_indices(g: int) -> np.ndarray:
    rows = []
    for i in range(g - 1):
        for j in range(g - 1):
            a, b = i * g + j, i * g + j + 1
            c, d = (i + 1) * g + j, (i + 1) * g + j + 1
            rows += [(a, b, c), (b, d, c)]
    return np.array(rows, dtype=np.uint16)


def _make_texture_png(img: Image.Image, size: int) -> bytes:
    buf = io.BytesIO()
    img.resize((size, size), Image.LANCZOS).save(buf, format="PNG")
    return buf.getvalue()


def _build_glb(positions: np.ndarray, uvs: np.ndarray, indices: np.ndarray, texture_png: bytes) -> bytes:
    def pad4(b):
        r = len(b) % 4
        return b if r == 0 else b + b"\x00" * (4 - r)

    pos_b = pad4(positions.astype(np.float32).tobytes())
    uv_b  = pad4(uvs.astype(np.float32).tobytes())
    idx_b = pad4(indices.astype(np.uint16).ravel().tobytes())
    img_b = pad4(texture_png)

    pos_off, uv_off = 0, len(pos_b)
    idx_off, img_off = uv_off + len(uv_b), uv_off + len(uv_b) + len(idx_b)
    buf = pos_b + uv_b + idx_b + img_b

    bmin = positions.min(axis=0).tolist()
    bmax = positions.max(axis=0).tolist()

    gltf = {
        "asset": {"version": "2.0", "generator": "v2-depth-preview"},
        "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "TEXCOORD_0": 1}, "indices": 2, "material": 0}]}],
        "materials": [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}, "metallicFactor": 0.0, "roughnessFactor": 0.75}, "doubleSided": True}],
        "textures": [{"source": 0, "sampler": 0}],
        "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}],
        "images": [{"bufferView": 3, "mimeType": "image/png"}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": pos_off, "byteLength": len(pos_b), "target": 34962},
            {"buffer": 0, "byteOffset": uv_off,  "byteLength": len(uv_b),  "target": 34962},
            {"buffer": 0, "byteOffset": idx_off, "byteLength": len(idx_b), "target": 34963},
            {"buffer": 0, "byteOffset": img_off, "byteLength": len(img_b)},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": len(positions), "type": "VEC3", "min": bmin, "max": bmax},
            {"bufferView": 1, "componentType": 5126, "count": len(uvs),       "type": "VEC2"},
            {"bufferView": 2, "componentType": 5123, "count": int(indices.ravel().shape[0]), "type": "SCALAR"},
        ],
        "buffers": [{"byteLength": len(buf)}],
    }

    json_b = json.dumps(gltf, separators=(",", ":")).encode()
    json_b = pad4(json_b + b" " * ((4 - len(json_b) % 4) % 4))
    total = 12 + 8 + len(json_b) + 8 + len(buf)
    return (struct.pack("<III", 0x46546C67, 2, total)
            + struct.pack("<II", len(json_b), 0x4E4F534A) + json_b
            + struct.pack("<II", len(buf),    0x004E4942) + buf)


# ---------------------------------------------------------------------------
# Real TRELLIS path
# ---------------------------------------------------------------------------

def _real_trellis(albedo_url: str, reference_url: str) -> Dict:
    raise RuntimeError("TRELLIS real path not wired; keep V2_REAL_MESH off until verify_trellis.py passes")
