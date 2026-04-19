"""Per-action parameter schemas for the structured edit dispatch table.

The applier calls `validate(action, params)` to ensure incoming payloads match
what each handler expects. Invalid params → ValueError with a readable message.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, ConfigDict, Field

from app.schema_v2 import InteractionType


class _P(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MoveParams(_P):
    delta: List[float] = Field(..., min_length=3, max_length=3)
    absolute: bool = False


class RotateParams(_P):
    axis: str  # "x" | "y" | "z" | "quat"
    angle_deg: float = 0.0
    quat: List[float] | None = None


class ScaleParams(_P):
    factor: float


class ChangeColorParams(_P):
    target: str  # "material" | "text_layer" | "light"
    hex: str


class ChangeMaterialParams(_P):
    material_ref: str  # another Material id


class ChangeLightParams(_P):
    intensity: float | None = None
    color_hex: str | None = None
    color_temp_k: int | None = None
    direction: List[float] | None = None


class AddTextParams(_P):
    text: str
    position_norm: List[float] = Field(..., min_length=2, max_length=2)
    size_px: int = 48
    color_hex: str = "#111111"


class EditTextParams(_P):
    text: str | None = None
    color_hex: str | None = None
    size_px: int | None = None
    position_norm: List[float] | None = None


class DeleteParams(_P):
    pass  # no params — target_id carries everything


class AddCameraParams(_P):
    shot_type: str = "custom"
    position: List[float] = Field(..., min_length=3, max_length=3)
    target: List[float] = Field(..., min_length=3, max_length=3)
    focal_length_mm: float = 50.0
    aspect_ratio: str = "1:1"
    resolution_px: List[int] = Field(default_factory=lambda: [1024, 1024], min_length=2, max_length=2)


class RegeneratePartParams(_P):
    part_id: str
    strategy: str = "crop_and_realign"  # or "whole_object_emphasis"


class AdjustTerrainParams(_P):
    type: str | None = None  # grass|sand|concrete|water
    extent_m: List[float] | None = None


class NlEditParams(_P):
    text: str
    context_url: str | None = None


_DISPATCH: Dict[InteractionType, type[_P]] = {
    InteractionType.MOVE: MoveParams,
    InteractionType.ROTATE: RotateParams,
    InteractionType.SCALE: ScaleParams,
    InteractionType.CHANGE_COLOR: ChangeColorParams,
    InteractionType.CHANGE_MATERIAL: ChangeMaterialParams,
    InteractionType.CHANGE_LIGHT: ChangeLightParams,
    InteractionType.ADD_TEXT: AddTextParams,
    InteractionType.EDIT_TEXT: EditTextParams,
    InteractionType.DELETE: DeleteParams,
    InteractionType.DELETE_TEXT: DeleteParams,
    InteractionType.ADD_CAMERA: AddCameraParams,
    InteractionType.REGENERATE_PART: RegeneratePartParams,
    InteractionType.ADJUST_TERRAIN: AdjustTerrainParams,
    InteractionType.NL_EDIT: NlEditParams,
}


def validate(action: InteractionType, params: Dict[str, Any]) -> _P:
    schema = _DISPATCH.get(action)
    if schema is None:
        # No params expected (e.g., select, duplicate, approve_decomposition). Accept empty.
        if params:
            raise ValueError(f"Action {action.value} takes no params, got: {list(params.keys())}")
        return _P()
    try:
        return schema.model_validate(params)
    except Exception as exc:
        raise ValueError(f"Invalid params for {action.value}: {exc}") from exc


def known_actions() -> List[Tuple[str, List[str]]]:
    """For debugging / docs — returns every (action, required_field_names)."""
    out = []
    for action, model in _DISPATCH.items():
        required = [name for name, field in model.model_fields.items() if field.is_required()]
        out.append((action.value, required))
    return out
