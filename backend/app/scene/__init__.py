"""Pipeline B — Scene assembly and rendering.

See docs/v2/PIPELINE_B_SCENE_ASSEMBLY.md for the full spec.

Public surface:
    - assembler.SceneAssembler   — intent + graph → SceneState
    - blender_bridge.BlenderRenderer — subprocess wrapper
    - refinement.Refiner          — neural refinement pass
"""

from .models import SceneState  # noqa: F401

__all__ = ["SceneState"]
