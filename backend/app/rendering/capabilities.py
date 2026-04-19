"""Runtime detection of which optional ML deps are installed.

Each pipeline step asks the CapabilityRegistry which implementation to use.
This keeps mock/real dispatch in one place and makes it honest about what
is actually available.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict


def _has_module(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


@dataclass(frozen=True)
class Capabilities:
    torch: bool
    torch_cuda: bool
    diffusers: bool
    transformers: bool
    clip: bool
    sam2: bool
    groundingdino: bool
    trellis: bool
    intrinsic_anything: bool
    flux: bool          # FLUX pipelines in diffusers
    pulid: bool
    controlnet: bool
    ip_adapter: bool
    blender_cli: bool
    scikit_image: bool

    def summary(self) -> Dict[str, bool]:
        return {
            "torch": self.torch,
            "torch_cuda": self.torch_cuda,
            "diffusers": self.diffusers,
            "transformers": self.transformers,
            "clip": self.clip,
            "sam2": self.sam2,
            "groundingdino": self.groundingdino,
            "trellis": self.trellis,
            "intrinsic_anything": self.intrinsic_anything,
            "flux": self.flux,
            "pulid": self.pulid,
            "controlnet": self.controlnet,
            "ip_adapter": self.ip_adapter,
            "blender_cli": self.blender_cli,
            "scikit_image": self.scikit_image,
        }


@lru_cache(maxsize=1)
def detect() -> Capabilities:
    torch_avail = _has_module("torch")
    cuda = False
    if torch_avail:
        try:
            import torch  # noqa: WPS433
            cuda = bool(torch.cuda.is_available())
        except Exception:
            cuda = False

    blender_cli = False
    try:
        import shutil
        blender_cli = shutil.which("blender") is not None
    except Exception:
        blender_cli = False

    return Capabilities(
        torch=torch_avail,
        torch_cuda=cuda,
        diffusers=_has_module("diffusers"),
        transformers=_has_module("transformers"),
        clip=_has_module("open_clip") or _has_module("clip"),
        sam2=_has_module("sam2"),
        groundingdino=_has_module("groundingdino"),
        trellis=_has_module("trellis"),
        intrinsic_anything=_has_module("intrinsic_anything"),
        flux=_has_module("diffusers"),  # FLUX ships via diffusers
        pulid=_has_module("pulid"),
        controlnet=_has_module("diffusers"),
        ip_adapter=_has_module("diffusers"),
        blender_cli=blender_cli,
        scikit_image=_has_module("skimage"),
    )
