"""V2 health router. Mounted under /api/v2/*.

Phase 0 Friday deliverable. Later phases extend this router with the full
API surface defined in docs/v2/API_CONTRACT_V2.md.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.schema_v2 import SCHEMA_VERSION

router = APIRouter(prefix="/api/v2", tags=["v2"])


@router.get("/health")
def health() -> dict:
    try:
        import torch
        if torch.cuda.is_available():
            total_mb = torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
            free_mb, _ = torch.cuda.mem_get_info()
            free_mb = free_mb // (1024 * 1024)
            gpu_info = {
                "name": torch.cuda.get_device_name(0),
                "vram_total_mb": int(total_mb),
                "vram_free_mb": int(free_mb),
            }
        else:
            gpu_info = {"name": "cpu-only", "vram_total_mb": 0, "vram_free_mb": 0}
    except Exception as exc:
        gpu_info = {"name": "unknown", "error": str(exc)}

    import os
    mesh_backend = (
        "tripo" if os.environ.get("TRIPO_API_KEY", "").strip()
        else "meshy" if os.environ.get("MESHY_API_KEY", "").strip()
        else "depth-preview"
    )
    return {
        "status": "ok",
        "schema_version": SCHEMA_VERSION,
        "model_stack_version": "2.0.0",
        "mock_mode": os.environ.get("V2_MOCK_MODE", "false").lower() in ("1", "true"),
        "mesh_backend": mesh_backend,
        "gpu": gpu_info,
    }
