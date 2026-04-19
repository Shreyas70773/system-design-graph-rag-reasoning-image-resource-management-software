"""Pipeline C — Applier. Maps validated StructuredEditCommand → scene graph mutation.

The applier owns ALL writes to placement / material / light / text_layer /
camera / terrain nodes. It records an :Interaction node with MODIFIED edges
pointing to whatever changed, so the distiller can compute preference signals.
"""

from __future__ import annotations

import json
import logging
import math
from typing import Any, Dict, List, Optional

from app.database.neo4j_v2 import neo4j_v2
from app.interaction.dispatch_schema import validate
from app.schema_v2 import EditTargetKind, InteractionType, StructuredEditCommand

logger = logging.getLogger(__name__)


def apply(command: StructuredEditCommand, *, actor: str, surface: str,
          nl_text: Optional[str] = None, confidence: float = 1.0) -> Dict[str, Any]:
    # Validate params first.
    validate(command.action, command.params)

    pre_state = _snapshot(command.target_kind, command.target_id)
    post_state: Dict[str, Any] = {}
    rerender_needed = True
    mutation_notes: List[str] = []

    action = command.action
    kind = command.target_kind
    tid = command.target_id
    params = command.params or {}

    if action == InteractionType.MOVE and kind == EditTargetKind.PLACEMENT:
        post_state = _move_placement(tid, params)
        mutation_notes.append("placement.position")

    elif action == InteractionType.ROTATE and kind == EditTargetKind.PLACEMENT:
        post_state = _rotate_placement(tid, params)
        mutation_notes.append("placement.rotation_quat")

    elif action == InteractionType.SCALE and kind == EditTargetKind.PLACEMENT:
        post_state = _scale_placement(tid, params)
        mutation_notes.append("placement.scale")

    elif action == InteractionType.DELETE and kind == EditTargetKind.PLACEMENT:
        post_state = _delete_placement(tid)
        mutation_notes.append("placement.deleted")

    elif action == InteractionType.CHANGE_COLOR and kind == EditTargetKind.TEXT_LAYER:
        post_state = _change_text_color(tid, params)
        mutation_notes.append("text_layer.color_hex")

    elif action == InteractionType.CHANGE_COLOR and kind == EditTargetKind.MATERIAL:
        post_state = _change_material_color(tid, params)
        mutation_notes.append("material.albedo_dominant_hex")

    elif action == InteractionType.CHANGE_LIGHT and kind == EditTargetKind.LIGHT:
        post_state = _change_light(tid, params)
        mutation_notes.append("light.updated")

    elif action == InteractionType.EDIT_TEXT and kind == EditTargetKind.TEXT_LAYER:
        post_state = _edit_text(tid, params)
        mutation_notes.append("text_layer.text")

    elif action == InteractionType.DELETE_TEXT and kind == EditTargetKind.TEXT_LAYER:
        post_state = _delete_text(tid)
        mutation_notes.append("text_layer.deleted")

    elif action == InteractionType.ADD_TEXT and kind == EditTargetKind.SCENE:
        post_state = _add_text(tid, params)
        mutation_notes.append("text_layer.created")

    elif action == InteractionType.ADD_CAMERA and kind == EditTargetKind.SCENE:
        post_state = _add_camera(tid, params)
        mutation_notes.append("camera.created")

    elif action == InteractionType.ADJUST_TERRAIN:
        post_state = _adjust_terrain(tid, params)
        mutation_notes.append("terrain.updated")

    elif action == InteractionType.REGENERATE_PART:
        post_state = {"note": "regenerate_part queued", "strategy": params.get("strategy")}
        rerender_needed = False
        mutation_notes.append("part.regeneration_queued")

    elif action == InteractionType.APPROVE_DECOMPOSITION:
        post_state = _approve_decomposition(tid)
        rerender_needed = False
        mutation_notes.append("asset.approved")

    elif action == InteractionType.REJECT_DECOMPOSITION:
        post_state = _reject_decomposition(tid, params.get("reason") if params else None)
        rerender_needed = False
        mutation_notes.append("asset.rejected")

    else:
        # Unhandled actions — log but record the interaction so the audit trail stays complete.
        mutation_notes.append(f"unhandled:{action.value}:{kind.value}")
        rerender_needed = False

    # Record the interaction node.
    interaction_id = neo4j_v2.pipeline_c_record_interaction(
        {
            "action": action.value,
            "target_kind": kind.value,
            "target_id": tid,
            "params_json": json.dumps(params),
            "actor": actor,
            "surface": surface,
            "pre_state_json": json.dumps(pre_state) if pre_state else None,
            "post_state_json": json.dumps(post_state) if post_state else None,
            "confidence": confidence,
        },
        target_ids=[tid] if tid else [],
    )
    if nl_text:
        neo4j_v2.pipeline_c_record_nl_command(
            {"text": nl_text, "resolved_command": action.value, "confidence": confidence},
            interaction_id=interaction_id,
        )

    return {
        "interaction_id": interaction_id,
        "pre_state": pre_state,
        "post_state": post_state,
        "rerender_needed": rerender_needed,
        "mutation_notes": mutation_notes,
        "rerender_cameras": command.rerender_cameras,
    }


# ---------------------------------------------------------------------------
# Mutation helpers
# ---------------------------------------------------------------------------


def _snapshot(kind: EditTargetKind, tid: str) -> Dict[str, Any]:
    label = _label_for(kind)
    if not label:
        return {}
    node = neo4j_v2.get_node(label, tid)
    return dict(node) if node else {}


def _label_for(kind: EditTargetKind) -> Optional[str]:
    return {
        EditTargetKind.PLACEMENT: "Placement",
        EditTargetKind.MATERIAL: "Material",
        EditTargetKind.CAMERA: "Camera",
        EditTargetKind.LIGHT: "Light",
        EditTargetKind.TEXT_LAYER: "TextLayer",
        EditTargetKind.SCENE: "Scene",
        EditTargetKind.ASSET: "Asset",
        EditTargetKind.SEMANTIC_PART: "SemanticPart",
        EditTargetKind.TERRAIN: "Terrain",
    }.get(kind)


def _move_placement(tid: str, params: Dict[str, Any]) -> Dict[str, Any]:
    node = neo4j_v2.get_node("Placement", tid) or {}
    current = node.get("position") or [0.0, 0.0, 0.0]
    if params.get("absolute"):
        new_pos = list(params["delta"])
    else:
        new_pos = [current[i] + params["delta"][i] for i in range(3)]
    # Scene-scale clamp: 50 m world bounds.
    new_pos = [max(-50.0, min(50.0, v)) for v in new_pos]
    neo4j_v2.update_node_fields("Placement", tid, {"position": new_pos})
    return {"position": new_pos}


def _rotate_placement(tid: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if "quat" in params and params["quat"]:
        q = list(params["quat"])
    else:
        axis = params.get("axis", "y")
        ang = math.radians(float(params.get("angle_deg", 0.0)))
        half = ang / 2.0
        s, c = math.sin(half), math.cos(half)
        vec = {"x": (s, 0, 0), "y": (0, s, 0), "z": (0, 0, s)}.get(axis, (0, s, 0))
        q = [vec[0], vec[1], vec[2], c]
    neo4j_v2.update_node_fields("Placement", tid, {"rotation_quat": q})
    return {"rotation_quat": q}


def _scale_placement(tid: str, params: Dict[str, Any]) -> Dict[str, Any]:
    node = neo4j_v2.get_node("Placement", tid) or {}
    factor = max(0.1, min(10.0, float(params["factor"])))
    current = node.get("scale") or [1.0, 1.0, 1.0]
    new_scale = [current[i] * factor for i in range(3)]
    neo4j_v2.update_node_fields("Placement", tid, {"scale": new_scale})
    return {"scale": new_scale}


def _delete_placement(tid: str) -> Dict[str, Any]:
    neo4j_v2.update_node_fields("Placement", tid, {"visible": False})
    return {"visible": False, "soft_deleted": True}


def _change_text_color(tid: str, params: Dict[str, Any]) -> Dict[str, Any]:
    hx = params["hex"]
    neo4j_v2.update_node_fields("TextLayer", tid, {"color_hex": hx})
    return {"color_hex": hx}


def _change_material_color(placement_or_material_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    # If target is a placement, find its asset's primary material.
    node = neo4j_v2.get_node("Material", placement_or_material_id)
    if node:
        neo4j_v2.update_node_fields("Material", placement_or_material_id, {"albedo_dominant_hex": params["hex"]})
        return {"material_id": placement_or_material_id, "albedo_dominant_hex": params["hex"]}
    # Placement → look up asset → primary material.
    rows = neo4j_v2.run(
        "MATCH (p:Placement {id: $pid})-[:INSTANCE_OF]->(a:Asset)-[:HAS_MATERIAL]->(m:Material) "
        "RETURN m LIMIT 1",
        pid=placement_or_material_id,
    )
    if rows:
        mid = rows[0]["m"]["id"]
        neo4j_v2.update_node_fields("Material", mid, {"albedo_dominant_hex": params["hex"]})
        return {"material_id": mid, "albedo_dominant_hex": params["hex"]}
    return {"noop": True}


def _change_light(tid: str, params: Dict[str, Any]) -> Dict[str, Any]:
    fields = {k: v for k, v in params.items() if v is not None and k in
              {"intensity", "color_hex", "color_temp_k", "direction"}}
    neo4j_v2.update_node_fields("Light", tid, fields)
    return fields


def _edit_text(tid: str, params: Dict[str, Any]) -> Dict[str, Any]:
    fields = {k: v for k, v in params.items() if v is not None}
    neo4j_v2.update_node_fields("TextLayer", tid, fields)
    return fields


def _delete_text(tid: str) -> Dict[str, Any]:
    neo4j_v2.run_write("MATCH (t:TextLayer {id: $id}) DETACH DELETE t", id=tid)
    return {"deleted": True}


def _add_text(scene_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    tl = {
        "text": params["text"],
        "font_id": "default",
        "size_px": int(params.get("size_px", 48)),
        "color_hex": params.get("color_hex", "#111111"),
        "position_norm": params["position_norm"],
        "anchor": "center",
        "max_width_norm": 0.8,
        "z": 100,
    }
    new_id = neo4j_v2.pipeline_b_add_text_layer(scene_id, tl)
    return {"text_layer_id": new_id}


def _add_camera(scene_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    cam = {
        "position": params["position"],
        "target": params["target"],
        "up": [0, 1, 0],
        "focal_length_mm": float(params.get("focal_length_mm", 50.0)),
        "fov_deg": 39.6,
        "shot_type": params.get("shot_type", "custom"),
        "aspect_ratio": params.get("aspect_ratio", "1:1"),
        "resolution_px": params.get("resolution_px", [1024, 1024]),
    }
    new_id = neo4j_v2.pipeline_b_add_camera(scene_id, cam)
    return {"camera_id": new_id}


def _adjust_terrain(scene_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    # Try to locate a Terrain attached to this scene; if none, create one.
    rows = neo4j_v2.run(
        "MATCH (s:Scene {id: $sid})-[:HAS_TERRAIN]->(t:Terrain) RETURN t LIMIT 1",
        sid=scene_id,
    )
    fields = {k: v for k, v in params.items() if v is not None}
    if rows:
        tid = rows[0]["t"]["id"]
        neo4j_v2.update_node_fields("Terrain", tid, fields)
        return {"terrain_id": tid, **fields}
    # Insert Terrain node + HAS_TERRAIN relationship.
    new = {"type": fields.get("type", "grass"), "extent_m": fields.get("extent_m", [10.0, 10.0])}
    tid = neo4j_v2.pipeline_b_create_scene.__self__ if False else None  # keep lint happy
    from app.database.neo4j_v2 import _gen_id, _now_iso  # reused helpers
    tid = _gen_id()
    neo4j_v2.run_write(
        "MATCH (s:Scene {id: $sid}) "
        "CREATE (t:Terrain {id: $tid, created_at: $ts, updated_at: $ts, schema_version: '2.0', "
        "type: $type, extent_m: $extent}) "
        "CREATE (s)-[:HAS_TERRAIN {created_at: $ts}]->(t)",
        sid=scene_id, tid=tid, ts=_now_iso(), type=new["type"], extent=new["extent_m"],
    )
    return {"terrain_id": tid, **new}


def _approve_decomposition(asset_id: str) -> Dict[str, Any]:
    neo4j_v2.pipeline_a_update_asset_status(asset_id, "approved")
    neo4j_v2.run_write(
        "MATCH (a:Asset {id: $aid})-[:DECOMPOSED_BY]->(r:DecompositionRun) "
        "SET r.user_approved = true",
        aid=asset_id,
    )
    return {"status": "approved"}


def _reject_decomposition(asset_id: str, reason: Optional[str]) -> Dict[str, Any]:
    neo4j_v2.pipeline_a_update_asset_status(asset_id, "rejected")
    neo4j_v2.run_write(
        "MATCH (a:Asset {id: $aid})-[:DECOMPOSED_BY]->(r:DecompositionRun) "
        "SET r.user_approved = false, r.rejection_reason = $reason",
        aid=asset_id, reason=reason or "",
    )
    return {"status": "rejected", "reason": reason}
