from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


SCHEMA_VERSION_V3 = "3.0.0"
SCHEMA_FAMILY_V3 = "capstone_v3"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class CapstoneModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TimestampedNode(CapstoneModel):
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    schema_version: str = SCHEMA_VERSION_V3
    schema_family: str = SCHEMA_FAMILY_V3


class BoundingBox(CapstoneModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    w: int = Field(gt=0)
    h: int = Field(gt=0)

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    @property
    def center_x(self) -> float:
        return self.x + (self.w / 2.0)

    @property
    def center_y(self) -> float:
        return self.y + (self.h / 2.0)


class SceneNode(TimestampedNode):
    scene_id: str = Field(default_factory=lambda: gen_id("scene"))
    image_path: str
    canvas_width: int = Field(gt=0)
    canvas_height: int = Field(gt=0)
    aspect_ratio: str
    owner_user_id: str = "local-user"
    title: Optional[str] = None


class UserNode(TimestampedNode):
    user_id: str = "local-user"
    email: Optional[str] = None
    storage_quota_mb: int = Field(default=2048, ge=1)


class ImageObjectNode(TimestampedNode):
    object_id: str = Field(default_factory=lambda: gen_id("obj"))
    class_label: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    bbox: BoundingBox
    mask_path: Optional[str] = None
    z_order: int = 0
    is_locked: bool = False
    is_text: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TextRegionNode(TimestampedNode):
    text_id: str = Field(default_factory=lambda: gen_id("text"))
    object_id: str
    attached_object_id: Optional[str] = None
    raw_text: str
    font_family: Optional[str] = None
    font_size: Optional[int] = Field(default=None, ge=1)
    color_hex: Optional[str] = None
    is_embedded: bool = True
    ocr_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    bbox: BoundingBox


class SpatialRelationshipNode(TimestampedNode):
    rel_id: str = Field(default_factory=lambda: gen_id("rel"))
    source_object_id: str
    target_object_id: str
    predicate: Literal["above", "below", "left_of", "right_of", "overlaps", "contains", "adjacent_to"]
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    distance_px: float = Field(default=0.0, ge=0.0)


class CanvasVersionNode(TimestampedNode):
    version_id: str = Field(default_factory=lambda: gen_id("ver"))
    composite_image_path: str
    graph_snapshot_json: Dict[str, Any] = Field(default_factory=dict)
    is_current: bool = True


class EditEventNode(TimestampedNode):
    event_id: str = Field(default_factory=lambda: gen_id("edit"))
    event_type: str
    delta_json: Dict[str, Any] = Field(default_factory=dict)
    before_state_json: Dict[str, Any] = Field(default_factory=dict)
    after_state_json: Dict[str, Any] = Field(default_factory=dict)
    user_id: str = "local-user"
    affected_object_ids: List[str] = Field(default_factory=list)
    prev_event_id: Optional[str] = None
    canvas_version_id: Optional[str] = None


class SceneDocument(CapstoneModel):
    user: UserNode
    scene: SceneNode
    objects: List[ImageObjectNode] = Field(default_factory=list)
    text_regions: List[TextRegionNode] = Field(default_factory=list)
    spatial_relationships: List[SpatialRelationshipNode] = Field(default_factory=list)
    edit_events: List[EditEventNode] = Field(default_factory=list)
    canvas_versions: List[CanvasVersionNode] = Field(default_factory=list)


class CreateSceneRequest(CapstoneModel):
    image_path: str
    canvas_width: int = Field(gt=0)
    canvas_height: int = Field(gt=0)
    aspect_ratio: str
    owner_user_id: str = "local-user"
    title: Optional[str] = None
    email: Optional[str] = None


class CreateObjectRequest(CapstoneModel):
    class_label: str
    bbox: BoundingBox
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    mask_path: Optional[str] = None
    z_order: int = 0
    is_locked: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CreateTextRegionRequest(CapstoneModel):
    raw_text: str
    bbox: BoundingBox
    font_family: Optional[str] = None
    font_size: Optional[int] = Field(default=None, ge=1)
    color_hex: Optional[str] = None
    is_embedded: bool = True
    ocr_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    attached_object_id: Optional[str] = None


class RecordEditRequest(CapstoneModel):
    event_type: str
    delta_json: Dict[str, Any] = Field(default_factory=dict)
    before_state_json: Dict[str, Any] = Field(default_factory=dict)
    after_state_json: Dict[str, Any] = Field(default_factory=dict)
    affected_object_ids: List[str] = Field(default_factory=list)
    user_id: str = "local-user"
    composite_image_path: Optional[str] = None


class UpdateAspectRatioRequest(CapstoneModel):
    aspect_ratio: str
    canvas_width: int = Field(gt=0)
    canvas_height: int = Field(gt=0)
    composite_image_path: Optional[str] = None


class SegmentationTuning(CapstoneModel):
    multimask_strategy: Literal["best_score", "largest_mask"] = "best_score"
    dilate_px: int = Field(default=0, ge=0, le=64)
    erode_px: int = Field(default=0, ge=0, le=64)
    keep_largest_component: bool = True
    min_area_fraction: float = Field(default=0.001, ge=0.0, le=1.0)


class InpaintTuning(CapstoneModel):
    mask_dilate_px: int = Field(default=4, ge=0, le=64)
    neighbor_limit: int = Field(default=5, ge=1, le=20)
    preserve_text_regions: bool = True


class SegmentClickRequest(CapstoneModel):
    click_x: float = Field(ge=0.0, le=1.0)
    click_y: float = Field(ge=0.0, le=1.0)
    label: str = "object"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    object_id: Optional[str] = None
    register_object: bool = True
    z_order: Optional[int] = None
    tuning: Optional[SegmentationTuning] = None


class RemoveObjectRequest(CapstoneModel):
    object_id: str
    record_event: bool = True
    tuning: Optional[InpaintTuning] = None
