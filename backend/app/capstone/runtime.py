from __future__ import annotations

import importlib.util
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel
from dotenv import load_dotenv


_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_env_path)


def _env_bool(key: str, default: bool) -> bool:
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class CapstoneRuntimeSettings(BaseModel):
    sam2_checkpoint: Path = Path("checkpoints/sam2.1_hiera_large.pt")
    sam2_config: str = "configs/sam2.1/sam2.1_hiera_l.yaml"
    lama_repo_path: Optional[Path] = None
    lama_model_path: Optional[Path] = None
    lama_python_executable: str = sys.executable
    device_preference: Literal["auto", "cuda", "cpu"] = "auto"
    public_upload_subdir: str = "capstone"
    allow_mock_fallbacks: bool = False

    @property
    def resolved_sam2_checkpoint(self) -> Path:
        path = Path(self.sam2_checkpoint)
        if path.is_absolute():
            return path
        return Path(__file__).resolve().parents[2] / path

    @property
    def resolved_lama_repo_path(self) -> Optional[Path]:
        if self.lama_repo_path is None:
            return None
        path = Path(self.lama_repo_path)
        if path.is_absolute():
            return path
        return Path(__file__).resolve().parents[2] / path

    @property
    def resolved_lama_model_path(self) -> Optional[Path]:
        if self.lama_model_path is None:
            return None
        path = Path(self.lama_model_path)
        if path.is_absolute():
            resolved = path
        else:
            resolved = Path(__file__).resolve().parents[2] / path
        if (resolved / "config.yaml").exists():
            return resolved
        nested = resolved / "big-lama"
        if (nested / "config.yaml").exists():
            return nested
        return resolved


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def has_sam2() -> bool:
    return _has_module("sam2")


def has_torch() -> bool:
    return _has_module("torch")


def resolve_device(preference: str) -> str:
    if preference == "cpu":
        return "cpu"
    if preference == "cuda":
        return "cuda"
    if has_torch():
        import torch  # noqa: WPS433
        if torch.cuda.is_available():
            return "cuda"
    return "cpu"


@lru_cache(maxsize=1)
def get_capstone_runtime_settings() -> CapstoneRuntimeSettings:
    lama_repo = os.environ.get("CAPSTONE_LAMA_REPO_PATH")
    lama_model = os.environ.get("CAPSTONE_LAMA_MODEL_PATH")
    return CapstoneRuntimeSettings(
        sam2_checkpoint=Path(os.environ.get("CAPSTONE_SAM2_CHECKPOINT", "checkpoints/sam2.1_hiera_large.pt")),
        sam2_config=os.environ.get("CAPSTONE_SAM2_CONFIG", "configs/sam2.1/sam2.1_hiera_l.yaml"),
        lama_repo_path=Path(lama_repo) if lama_repo else None,
        lama_model_path=Path(lama_model) if lama_model else None,
        lama_python_executable=os.environ.get("CAPSTONE_LAMA_PYTHON", sys.executable),
        device_preference=os.environ.get("CAPSTONE_DEVICE", "auto"),  # type: ignore[arg-type]
        public_upload_subdir=os.environ.get("CAPSTONE_UPLOAD_SUBDIR", "capstone"),
        allow_mock_fallbacks=_env_bool("CAPSTONE_ALLOW_MOCK_FALLBACKS", False),
    )
