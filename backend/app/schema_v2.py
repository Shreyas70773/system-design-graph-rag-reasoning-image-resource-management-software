"""
schema_v2.py
============

Pydantic models derived from docs/v2/GRAPH_SCHEMA_V2.md (version 2.0.0).

This file is the machine-readable counterpart to the schema spec. It is
validated against the spec in CI via ``backend/scripts/validate_graph_schema.py``.
Do not add, rename, or remove fields here without also updating
``docs/v2/GRAPH_SCHEMA_V2.md`` and bumping both version headers.

All models use ``extra="forbid"`` so unknown fields fail parse. This is the
first line of defense against schema drift (R-1).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


SCHEMA_VERSION = "2.0.0"


# ---------------------------------------------------------------------------
# Base & enums
# ---------------------------------------------------------------------------


class _Node(BaseModel):
    """Common fields on every node."""

    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: datetime
    updated_at: datetime
    schema_version: str = SCHEMA_VERSION


class AssetType(str, Enum):
    PRODUCT = "product"
    LOGO = "logo"
    CHARACTER_REF = "character_ref"
    TEXTURE = "texture"
    ENVIRONMENT_REF = "environment_ref"


class IngestionStatus(str, Enum):
    PENDING = "pending"
    DECOMPOSING = "decomposing"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


class UsageContext(str, Enum):
    DIGITAL = "digital"
    PRINT = "print"
    OOH = "ooh"


class DeploymentContext(str, Enum):
    DIGITAL = "digital"
    PRINT = "print"
    OOH = "ooh"


class ShotType(str, Enum):
    HERO = "hero"
    DETAIL = "detail"
    WIDE = "wide"
    CUSTOM = "custom"


class LightType(str, Enum):
    DIRECTIONAL = "directional"
    POINT = "point"
    AREA = "area"
    HDRI = "hdri"


class PartType(str, Enum):
    STRUCTURAL = "structural"
    LABEL = "label"
    DECORATION = "decoration"
    LOGO_TARGET = "logo_target"


class SceneStatus(str, Enum):
    DRAFT = "draft"
    RENDERED = "rendered"
    PUBLISHED = "published"


class InteractionType(str, Enum):
    SELECT = "select"
    MOVE = "move"
    ROTATE = "rotate"
    SCALE = "scale"
    DELETE = "delete"
    DUPLICATE = "duplicate"
    CHANGE_MATERIAL = "change_material"
    CHANGE_COLOR = "change_color"
    ADD_OBJECT = "add_object"
    REPLACE_OBJECT = "replace_object"
    NL_EDIT = "nl_edit"
    APPROVE_DECOMPOSITION = "approve_decomposition"
    REJECT_DECOMPOSITION = "reject_decomposition"
    REGENERATE_PART = "regenerate_part"
    ADD_CAMERA = "add_camera"
    MOVE_CAMERA = "move_camera"
    CHANGE_LIGHT = "change_light"
    ADD_TEXT = "add_text"
    EDIT_TEXT = "edit_text"
    DELETE_TEXT = "delete_text"
    ADJUST_TERRAIN = "adjust_terrain"


class InteractionSurface(str, Enum):
    THREE_D_CANVAS = "3d_canvas"
    TWO_D_CANVAS = "2d_canvas"
    ASSET_EDITOR = "asset_editor"
    LEARNED_PREFS_PANEL = "learned_prefs_panel"


class EditTargetKind(str, Enum):
    PLACEMENT = "placement"
    MATERIAL = "material"
    CAMERA = "camera"
    LIGHT = "light"
    TEXT_LAYER = "text_layer"
    SCENE = "scene"
    ASSET = "asset"
    SEMANTIC_PART = "semantic_part"
    TERRAIN = "terrain"


# ---------------------------------------------------------------------------
# 1.1  Brand-level nodes
# ---------------------------------------------------------------------------


class Brand(_Node):
    name: str
    source_url: Optional[str] = None
    primary_hex: List[str] = Field(default_factory=list)
    aesthetic_prefs: Optional[dict] = None
    composition_prefs: Optional[dict] = None


class Color(_Node):
    hex: str
    lab_l: float
    lab_a: float
    lab_b: float
    usage_context: List[UsageContext]
    name: Optional[str] = None


class Font(_Node):
    family: str
    weight: int = Field(ge=100, le=900)
    italic: bool
    file_url: Optional[str] = None
    license_status: Literal["ok", "restricted", "unknown"]


# ---------------------------------------------------------------------------
# 1.2  Asset cluster
# ---------------------------------------------------------------------------


class Asset(_Node):
    asset_type: AssetType
    source_url: str
    ingestion_status: IngestionStatus
    vlm_description: Optional[str] = None
    clip_embedding: Optional[List[float]] = None  # len=768 when present
    approved_at: Optional[datetime] = None
    approved_by_user_id: Optional[str] = None


class Mesh3D(_Node):
    file_url: str
    vertex_count: int
    bbox_min: List[float]  # [x, y, z]
    bbox_max: List[float]
    canonical_scale_m: float
    lod_level: int = Field(ge=0, le=3)
    generator_model: str
    generator_version: str


class Material(_Node):
    albedo_url: str
    albedo_dominant_hex: str
    roughness_url: Optional[str] = None
    metallic_url: Optional[str] = None
    normal_url: Optional[str] = None
    emissive_url: Optional[str] = None
    uv_set_index: int = 0


class SemanticPart(_Node):
    name: str
    mask_url: str
    uv_region: dict  # { u_min, v_min, u_max, v_max }
    part_type: PartType
    editable: bool


class LightProbe(_Node):
    hdri_url: Optional[str] = None
    estimated_direction: List[float]
    estimated_color_temp_k: int
    estimated_intensity: float
    confidence: float = Field(ge=0.0, le=1.0)


class CanonicalPose(_Node):
    rotation_quat: List[float]  # [x, y, z, w]
    suggested_camera_position: List[float]
    suggested_camera_focal_mm: float


class LogoAsset(_Node):
    svg_url: Optional[str] = None
    png_url: Optional[str] = None
    dominant_hex: str
    aspect_ratio: float
    min_size_px: int


class DecompositionRun(_Node):
    pipeline_version: str
    vlm_model: str
    segmenter_model: str
    delighter_model: Optional[str] = None
    mesh_model: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    user_approved: bool
    user_regenerated_parts: Optional[List[str]] = None
    user_edits_json: Optional[dict] = None
    confidence_overall: float = Field(ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# 1.3  Scene-level nodes
# ---------------------------------------------------------------------------


class Scene(_Node):
    brand_id: str
    intent_text: str
    scene_graph_json: dict
    deployment_context: DeploymentContext
    status: SceneStatus


class Placement(_Node):
    asset_id: str
    position: List[float]
    rotation_quat: List[float]
    scale: List[float]
    z_order: int
    cast_shadow: bool
    receive_shadow: bool
    material_override_ids: Optional[List[str]] = None
    visible: bool = True


class Camera(_Node):
    position: List[float]
    target: List[float]
    up: List[float] = Field(default_factory=lambda: [0.0, 1.0, 0.0])
    focal_length_mm: float
    fov_deg: float
    shot_type: ShotType
    aspect_ratio: Literal["1:1", "16:9", "9:16", "4:5"]
    resolution_px: List[int]  # [w, h]


class Light(_Node):
    light_type: LightType
    position: Optional[List[float]] = None
    direction: Optional[List[float]] = None
    color_hex: str
    color_temp_k: int
    intensity: float
    casts_shadow: bool
    hdri_url: Optional[str] = None


class Terrain(_Node):
    heightmap_url: str
    size_m: List[float]
    texture_layer_ids: List[str]
    blend_mask_urls: Optional[List[str]] = None


class TextLayer(_Node):
    text: str
    font_id: str
    size_px: int
    color_hex: str
    position_norm: List[float]
    anchor: Literal[
        "top-left", "top-center", "top-right",
        "middle-left", "center", "middle-right",
        "bottom-left", "bottom-center", "bottom-right",
    ]
    max_width_norm: float
    z: int


class Render(_Node):
    scene_id: str
    camera_id: str
    image_url: str
    object_id_pass_url: str
    depth_pass_url: Optional[str] = None
    refinement_model: str
    render_time_sec: float
    peak_vram_mb: int


# ---------------------------------------------------------------------------
# 1.4  Interaction & learning nodes
# ---------------------------------------------------------------------------


class Interaction(_Node):
    session_id: str
    user_id: str
    timestamp: datetime
    interaction_type: InteractionType
    surface: InteractionSurface
    natural_language: Optional[str] = None
    structured_command_json: dict


class PreferenceSignal(_Node):
    subject_kind: str
    direction: float = Field(ge=-1.0, le=1.0)
    weight: float = Field(ge=0.0, le=1.0)
    half_life_days: int = 30
    source_interaction_ids: List[str]
    superseded_by_id: Optional[str] = None


class NaturalLanguageCommand(_Node):
    raw_text: str
    vlm_model: str
    mask_url: Optional[str] = None
    target_placement_ids: List[str]
    resolved_action: InteractionType
    resolved_params_json: dict
    confidence: float = Field(ge=0.0, le=1.0)
    applied: bool


# ---------------------------------------------------------------------------
# Edit-command API models (used by Pipeline C endpoints)
# ---------------------------------------------------------------------------


class StructuredEditCommand(BaseModel):
    """The command grammar every edit path ultimately produces.

    See docs/v2/PIPELINE_C_INTERACTION_LEARNING.md §2 for the full spec.
    """

    model_config = ConfigDict(extra="forbid")

    action: InteractionType
    target_kind: EditTargetKind
    target_id: str
    params: dict  # action-specific; validated by dispatch_schema.py at the boundary
    rerender_cameras: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Scene-graph JSON contract (LLM output)
# ---------------------------------------------------------------------------


class PlacementSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: Optional[str] = None
    asset_query: Optional[str] = None
    role: Literal["hero", "supporting", "environment", "background"]
    position_hint: str
    z_order: int


class CameraSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shot_type: ShotType
    aspect_ratio: Literal["1:1", "16:9", "9:16", "4:5"]


class LightSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mood: Literal["golden-hour", "overcast", "studio", "high-key", "moody"]
    direction_hint: str


class TerrainSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["grass", "sand", "concrete", "water", "none"]
    extent_m: List[float]


class TextLayerSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    position_hint: str
    role: Literal["headline", "body", "cta"]


class SceneGraphSpec(BaseModel):
    """Parsed output of Pipeline B Stage 1.

    Backed by the LLM intent parser. Strict validation prevents hallucinated
    fields from propagating into scene state.
    """

    model_config = ConfigDict(extra="forbid")

    scene_id: str
    brand_id: str
    deployment_context: DeploymentContext
    placements: List[PlacementSpec]
    cameras: List[CameraSpec]
    lights: List[LightSpec]
    terrain: Optional[TerrainSpec] = None
    text_layers: List[TextLayerSpec] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Relationship catalogue (for schema validation)
# ---------------------------------------------------------------------------
# These dataclass-like constants mirror §2 of GRAPH_SCHEMA_V2.md. The schema
# validator cross-checks them against the live Neo4j and the doc.

RELATIONSHIPS = [
    # (from_label, rel_type, to_label)
    ("Brand", "HAS_COLOR", "Color"),
    ("Brand", "HAS_FONT", "Font"),
    ("Brand", "HAS_ASSET", "Asset"),
    ("Brand", "HAS_LOGO", "LogoAsset"),
    ("Brand", "LEARNED_PREF", "PreferenceSignal"),
    ("Asset", "HAS_GEOMETRY", "Mesh3D"),
    ("Asset", "HAS_MATERIAL", "Material"),
    ("Asset", "HAS_PART", "SemanticPart"),
    ("Asset", "HAS_LIGHT_PROBE", "LightProbe"),
    ("Asset", "HAS_CANONICAL_POSE", "CanonicalPose"),
    ("Asset", "DECOMPOSED_BY", "DecompositionRun"),
    ("SemanticPart", "USES_MATERIAL", "Material"),
    ("SemanticPart", "REFERENCES_LOGO", "LogoAsset"),
    ("Brand", "OWNS_SCENE", "Scene"),
    ("Scene", "HAS_PLACEMENT", "Placement"),
    ("Placement", "INSTANCE_OF", "Asset"),
    ("Scene", "HAS_CAMERA", "Camera"),
    ("Scene", "HAS_LIGHT", "Light"),
    ("Scene", "HAS_TERRAIN", "Terrain"),
    ("Scene", "HAS_TEXT_LAYER", "TextLayer"),
    ("Scene", "HAS_RENDER", "Render"),
    ("Interaction", "MODIFIED", "Placement"),
    ("Interaction", "MODIFIED", "Asset"),
    ("Interaction", "MODIFIED", "Material"),
    ("Interaction", "MODIFIED", "Camera"),
    ("Interaction", "MODIFIED", "Light"),
    ("Interaction", "MODIFIED", "TextLayer"),
    ("Interaction", "RESOLVED_BY", "NaturalLanguageCommand"),
    ("Interaction", "CONTRIBUTED_TO", "PreferenceSignal"),
    ("PreferenceSignal", "SUPERSEDES", "PreferenceSignal"),
]


# Master registry used by validate_graph_schema.py and pipeline ACLs.
ALL_NODE_MODELS = {
    "Brand": Brand,
    "Color": Color,
    "Font": Font,
    "Asset": Asset,
    "Mesh3D": Mesh3D,
    "Material": Material,
    "SemanticPart": SemanticPart,
    "LightProbe": LightProbe,
    "CanonicalPose": CanonicalPose,
    "LogoAsset": LogoAsset,
    "DecompositionRun": DecompositionRun,
    "Scene": Scene,
    "Placement": Placement,
    "Camera": Camera,
    "Light": Light,
    "Terrain": Terrain,
    "TextLayer": TextLayer,
    "Render": Render,
    "Interaction": Interaction,
    "PreferenceSignal": PreferenceSignal,
    "NaturalLanguageCommand": NaturalLanguageCommand,
}
