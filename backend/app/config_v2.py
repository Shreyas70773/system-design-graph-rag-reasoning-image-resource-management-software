"""V2-specific settings. Layered on top of V1's get_settings()."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class V2Settings(BaseModel):
    """V2 runtime settings. Controlled via environment variables."""

    # Mock / real model dispatch. When true, pipelines use mock implementations.
    # Flip individual per-model switches to force real when that model is installed.
    mock_mode: bool = True

    # Per-model real/mock overrides (mock_mode must be False for these to matter).
    force_real_vlm: bool = False
    force_real_segmenter: bool = False
    force_real_delighter: bool = False
    force_real_mesh: bool = False
    force_real_refiner: bool = False
    force_real_blender: bool = False

    # Storage. Local filesystem under backend/uploads/v2/*; optionally R2 (post-MVP).
    # Path is resolved relative to the backend/ package so cwd doesn't matter.
    storage_dir: Path = (Path(__file__).resolve().parents[1] / "uploads" / "v2")
    public_base_url: str = "http://localhost:8000/uploads/v2"

    # Refinement fallback ladder (per RISK_REGISTER.md R-3).
    refinement_primary: Literal["flux_nf4", "flux_gguf", "sdxl_turbo", "passthrough"] = "passthrough"

    # Worker behaviour.
    worker_poll_interval_s: float = 1.0
    worker_max_jobs: int = 0  # 0 = unlimited

    # Neo4j write-ownership enforcement (advisory in MVP).
    strict_pipeline_acl: bool = False

    # CLIP validation threshold (Pipeline A Step 6).
    clip_validation_min: float = 0.75

    @property
    def storage_root(self) -> Path:
        path = Path(self.storage_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


def _env_bool(key: str, default: bool) -> bool:
    v = os.environ.get(key)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


@lru_cache(maxsize=1)
def get_v2_settings() -> V2Settings:
    return V2Settings(
        mock_mode=_env_bool("V2_MOCK_MODE", True),
        force_real_vlm=_env_bool("V2_REAL_VLM", False),
        force_real_segmenter=_env_bool("V2_REAL_SEGMENTER", False),
        force_real_delighter=_env_bool("V2_REAL_DELIGHTER", False),
        force_real_mesh=_env_bool("V2_REAL_MESH", False),
        force_real_refiner=_env_bool("V2_REAL_REFINER", False),
        force_real_blender=_env_bool("V2_REAL_BLENDER", False),
        storage_dir=Path(os.environ.get("V2_STORAGE_DIR", str(V2Settings.model_fields["storage_dir"].default))),
        public_base_url=os.environ.get("V2_PUBLIC_BASE_URL", V2Settings.model_fields["public_base_url"].default),
        refinement_primary=os.environ.get("V2_REFINEMENT_PRIMARY", "passthrough"),  # type: ignore[arg-type]
        strict_pipeline_acl=_env_bool("V2_STRICT_PIPELINE_ACL", False),
    )
