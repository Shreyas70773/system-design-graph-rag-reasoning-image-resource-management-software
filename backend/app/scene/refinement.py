"""Pipeline B Stage 5 — Neural refinement.

Fallback ladder, controlled by `V2Settings.refinement_primary`:
  - flux_nf4   → FLUX.1-schnell NF4 + CNet Union + IP-Adapter (+ PuLID when character)
  - flux_gguf  → FLUX.1-schnell Q4_K_S GGUF (smaller, lower quality ceiling)
  - sdxl_turbo → SDXL-Turbo + CNet Depth
  - passthrough → no refinement; previz is the output
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.config_v2 import get_v2_settings
from app.rendering.capabilities import detect

logger = logging.getLogger(__name__)


def refine(render: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    settings = get_v2_settings()
    caps = detect()
    mode = settings.refinement_primary
    if settings.mock_mode and not settings.force_real_refiner:
        mode = "passthrough"
    if mode != "passthrough" and not (caps.diffusers and caps.torch_cuda):
        logger.info("Refinement %s requested but deps unavailable; passthrough", mode)
        mode = "passthrough"

    if mode == "flux_nf4":
        try:
            return _flux_nf4(render, plan)
        except Exception as exc:  # noqa: BLE001
            logger.warning("FLUX-NF4 failed (%s); trying SDXL fallback", exc)
            mode = "sdxl_turbo"
    if mode == "flux_gguf":
        try:
            return _flux_gguf(render, plan)
        except Exception as exc:  # noqa: BLE001
            logger.warning("FLUX-GGUF failed (%s); trying SDXL fallback", exc)
            mode = "sdxl_turbo"
    if mode == "sdxl_turbo":
        try:
            return _sdxl_turbo(render, plan)
        except Exception as exc:  # noqa: BLE001
            logger.warning("SDXL-Turbo failed (%s); passthrough", exc)
            mode = "passthrough"
    return _passthrough(render)


def _passthrough(render: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "refined_url": render["rgb_url"],
        "refinement_model": "passthrough",
        "peak_vram_mb": 0,
        "refine_time_sec": 0.0,
    }


def _flux_nf4(render: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    raise RuntimeError("FLUX-NF4 refinement stub — wire in Phase 4 Week 10")


def _flux_gguf(render: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    raise RuntimeError("FLUX-GGUF refinement stub — wire in Phase 4")


def _sdxl_turbo(render: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    raise RuntimeError("SDXL-Turbo refinement stub — wire in Phase 4")
