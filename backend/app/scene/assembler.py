"""Pipeline B Stages 2 & 3 — Graph-RAG retrieval + scene state build."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from app.database.neo4j_v2 import neo4j_v2
from app.interaction.retrieval_bias import compile_biases
from app.schema_v2 import SceneGraphSpec

logger = logging.getLogger(__name__)


# Simple mapping from position hint → 3D world coordinates (metres).
_POSITION_MAP = {
    "center": (0.0, 0.0, 0.0),
    "left-third": (-1.5, 0.0, 0.0),
    "right-third": (1.5, 0.0, 0.0),
    "upper-left": (-1.5, 1.0, 0.0),
    "upper-right": (1.5, 1.0, 0.0),
    "lower-left": (-1.5, -1.0, 0.0),
    "lower-right": (1.5, -1.0, 0.0),
    "foreground": (0.0, 0.0, 1.5),
    "background": (0.0, 0.0, -3.0),
}


def assemble_scene_state(spec: SceneGraphSpec, brand_id: str) -> Tuple[str, Dict[str, Any]]:
    """Run Stage 2 (retrieve) and Stage 3 (build) and persist all scene nodes.

    Returns (scene_id, plan_dict) where plan_dict contains everything a Blender
    render script would need.
    """
    context = neo4j_v2.retrieve_brand_context(brand_id, spec.deployment_context.value)
    biases = compile_biases(context.get("preferences") or [])

    scene_id = neo4j_v2.pipeline_b_create_scene(
        brand_id=brand_id,
        intent_text=f"[scene:{spec.scene_id}]",
        scene_graph=spec.model_dump(mode="json"),
        deployment_context=spec.deployment_context.value,
    )

    # Resolve placements (Stage 3).
    placements_out: List[Dict[str, Any]] = []
    for idx, p in enumerate(spec.placements):
        asset_id = p.asset_id or _resolve_by_query(context["assets"], p.asset_query)
        if asset_id is None:
            # Nothing approved yet — skip rather than crash.
            logger.warning("Placement %s has no resolvable asset; skipping", idx)
            continue
        pos = list(_POSITION_MAP.get(p.position_hint, (0.0, 0.0, 0.0)))
        pos = _apply_bias(pos, biases.get("composition", {}))
        pid = neo4j_v2.pipeline_b_add_placement(scene_id, {
            "asset_id": asset_id,
            "position": pos,
            "rotation_quat": [0.0, 0.0, 0.0, 1.0],
            "scale": [1.0, 1.0, 1.0],
            "z_order": p.z_order,
            "cast_shadow": True,
            "receive_shadow": True,
            "visible": True,
        })
        placements_out.append({"id": pid, "asset_id": asset_id, "position": pos, "role": p.role})

    # Cameras.
    cameras_out: List[Dict[str, Any]] = []
    for idx, c in enumerate(spec.cameras):
        cam_data = _build_camera(c, idx)
        cid = neo4j_v2.pipeline_b_add_camera(scene_id, cam_data)
        cameras_out.append({**cam_data, "id": cid})

    # Lights.
    lights_out: List[Dict[str, Any]] = []
    for ls in spec.lights:
        l_data = _build_light(ls, biases.get("lighting", {}))
        lid = neo4j_v2.pipeline_b_add_light(scene_id, l_data)
        lights_out.append({**l_data, "id": lid})

    # Text layers.
    text_out: List[Dict[str, Any]] = []
    for ts in spec.text_layers:
        t_data = _build_text_layer(ts, context.get("colors") or [])
        tid = neo4j_v2.pipeline_b_add_text_layer(scene_id, t_data)
        text_out.append({**t_data, "id": tid})

    plan = {
        "scene_id": scene_id,
        "brand_id": brand_id,
        "deployment_context": spec.deployment_context.value,
        "brand_context": {
            "brand": context["brand"],
            "colors": context["colors"],
            "fonts": context["fonts"],
            "preferences": context["preferences"],
        },
        "placements": placements_out,
        "cameras": cameras_out,
        "lights": lights_out,
        "text_layers": text_out,
        "biases": biases,
    }
    return scene_id, plan


def _resolve_by_query(assets: List[Dict[str, Any]], query: Optional[str]) -> Optional[str]:
    if not assets:
        return None
    # MVP resolution: pick the first approved asset. A future version performs
    # vector search via the asset_clip_embedding index.
    for a in assets:
        if a.get("ingestion_status") == "approved":
            return a["id"]
    return assets[0]["id"]


def _apply_bias(position: List[float], comp_bias: Dict[str, float]) -> List[float]:
    x, y, z = position
    y += comp_bias.get("product_y_bias", 0.0)
    x += comp_bias.get("product_x_bias", 0.0)
    z += comp_bias.get("product_z_bias", 0.0)
    return [x, y, z]


def _build_camera(c, idx: int) -> Dict[str, Any]:
    resolution_map = {
        "1:1": (1024, 1024), "16:9": (1280, 720), "9:16": (720, 1280), "4:5": (1024, 1280),
    }
    res = resolution_map.get(c.aspect_ratio.value if hasattr(c.aspect_ratio, "value") else c.aspect_ratio,
                             (1024, 1024))
    shot_positions = {
        "hero": ([0.0, 0.4, 2.5], 50.0, 39.6),
        "detail": ([0.0, 0.2, 1.2], 85.0, 24.0),
        "wide": ([0.0, 0.6, 4.5], 35.0, 54.0),
        "custom": ([idx * 1.5, 0.5, 2.5], 50.0, 39.6),
    }
    shot_val = c.shot_type.value if hasattr(c.shot_type, "value") else c.shot_type
    position, focal, fov = shot_positions.get(shot_val, shot_positions["hero"])
    return {
        "position": position,
        "target": [0.0, 0.0, 0.0],
        "up": [0.0, 1.0, 0.0],
        "focal_length_mm": focal,
        "fov_deg": fov,
        "shot_type": shot_val,
        "aspect_ratio": c.aspect_ratio.value if hasattr(c.aspect_ratio, "value") else c.aspect_ratio,
        "resolution_px": list(res),
    }


def _build_light(ls, light_bias: Dict[str, float]) -> Dict[str, Any]:
    mood_map = {
        "golden-hour": {"temp": 3400, "intensity": 1.6, "dir": [0.4, 0.4, 0.8]},
        "overcast":    {"temp": 6500, "intensity": 1.0, "dir": [0.0, 1.0, 0.2]},
        "studio":      {"temp": 5600, "intensity": 1.4, "dir": [0.3, 0.6, 0.7]},
        "high-key":    {"temp": 6200, "intensity": 2.0, "dir": [0.0, 1.0, 0.5]},
        "moody":       {"temp": 4200, "intensity": 0.8, "dir": [0.8, 0.3, 0.5]},
    }
    mood_val = ls.mood.value if hasattr(ls.mood, "value") else ls.mood
    d = mood_map.get(mood_val, mood_map["studio"])
    temp = int(d["temp"] + light_bias.get("color_temp_bias", 0.0))
    intensity = float(d["intensity"]) * (1.0 + light_bias.get("intensity_multiplier", 0.0))
    return {
        "light_type": "directional",
        "direction": d["dir"],
        "color_hex": "#ffffff",
        "color_temp_k": temp,
        "intensity": intensity,
        "casts_shadow": True,
    }


def _build_text_layer(ts, brand_colors: List[Dict]) -> Dict[str, Any]:
    # Default font_id uses the first brand font if any — else a placeholder.
    color = "#111111"
    if brand_colors:
        color = brand_colors[0].get("hex") or color
    return {
        "text": ts.text,
        "font_id": "default",
        "size_px": 72 if (ts.role.value if hasattr(ts.role, "value") else ts.role) == "headline" else 36,
        "color_hex": color,
        "position_norm": [0.5, 0.85 if "bottom" in ts.position_hint else 0.5],
        "anchor": "center",
        "max_width_norm": 0.8,
        "z": 100,
    }
