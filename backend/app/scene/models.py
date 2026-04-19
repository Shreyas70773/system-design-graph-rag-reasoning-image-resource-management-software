"""Internal scene-state models for Pipeline B.

These are runtime structures held in memory during scene assembly + render.
They are distinct from the graph models in ``backend.app.schema_v2``: those
represent durable graph state, these represent the in-flight computation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.schema_v2 import (
    Camera,
    Light,
    Placement,
    Scene,
    TextLayer,
    Terrain,
)


@dataclass
class SceneState:
    """Everything needed to hand off to Blender for rendering."""

    scene: Scene
    placements: List[Placement] = field(default_factory=list)
    cameras: List[Camera] = field(default_factory=list)
    lights: List[Light] = field(default_factory=list)
    terrain: Optional[Terrain] = None
    text_layers: List[TextLayer] = field(default_factory=list)

    # Conditioning bundle from Graph-RAG stage 2
    brand_colors_lab: List[tuple] = field(default_factory=list)
    brand_fonts_by_id: Dict[str, str] = field(default_factory=dict)
    preference_biases: Dict[str, float] = field(default_factory=dict)

    # Per-asset resolved artefacts (URLs) — populated at assembly time
    asset_mesh_urls: Dict[str, str] = field(default_factory=dict)
    asset_material_ids: Dict[str, List[str]] = field(default_factory=dict)

    def placement_by_id(self, pid: str) -> Optional[Placement]:
        return next((p for p in self.placements if p.id == pid), None)

    def camera_by_id(self, cid: str) -> Optional[Camera]:
        return next((c for c in self.cameras if c.id == cid), None)
