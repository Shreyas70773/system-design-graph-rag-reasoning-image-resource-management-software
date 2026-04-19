"""/api/v2/interactions — Pipeline C endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database.neo4j_v2 import neo4j_v2
from app.interaction.applier import apply
from app.interaction.command_parser import CONFIDENCE_THRESHOLD, resolve
from app.interaction.distiller import distill_for_brand
from app.schema_v2 import EditTargetKind, InteractionType, StructuredEditCommand

router = APIRouter(prefix="/api/v2/interactions", tags=["V2 Interactions"])


class StructuredInteractionRequest(BaseModel):
    brand_id: str
    action: InteractionType
    target_kind: EditTargetKind
    target_id: str
    params: Dict[str, Any] = {}
    rerender_cameras: List[str] = []
    surface: str = "3d_canvas"
    actor: str = "user"


class NlInteractionRequest(BaseModel):
    brand_id: str
    scene_id: str
    text: str
    selected_placement_ids: List[str] = []
    selected_text_ids: List[str] = []
    last_render_url: Optional[str] = None
    surface: str = "2d_canvas"
    actor: str = "user"


@router.post("/structured")
def structured(req: StructuredInteractionRequest) -> Dict[str, Any]:
    cmd = StructuredEditCommand(
        action=req.action,
        target_kind=req.target_kind,
        target_id=req.target_id,
        params=req.params,
        rerender_cameras=req.rerender_cameras,
    )
    try:
        result = apply(cmd, actor=req.actor, surface=req.surface, confidence=1.0)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    # Foreground distill.
    distill_summary = distill_for_brand(req.brand_id)
    return {"result": result, "learning": distill_summary}


@router.post("/natural-language")
def natural_language(req: NlInteractionRequest) -> Dict[str, Any]:
    resolution = resolve(
        req.text,
        scene_id=req.scene_id,
        selected_placement_ids=req.selected_placement_ids,
        selected_text_ids=req.selected_text_ids,
        last_render_url=req.last_render_url,
    )
    if resolution.confidence < CONFIDENCE_THRESHOLD:
        return {
            "status": "needs_clarification",
            "proposed": resolution.model_dump(mode="json"),
            "confidence_threshold": CONFIDENCE_THRESHOLD,
        }
    cmd = StructuredEditCommand(
        action=resolution.action,
        target_kind=resolution.target_kind,
        target_id=resolution.target_id,
        params=resolution.params,
        rerender_cameras=resolution.rerender_cameras,
    )
    try:
        result = apply(cmd, actor=req.actor, surface=req.surface,
                       nl_text=req.text, confidence=resolution.confidence)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    distill_summary = distill_for_brand(req.brand_id)
    return {"status": "applied", "resolution": resolution.model_dump(mode="json"),
            "result": result, "learning": distill_summary}


@router.get("/recent")
def recent(brand_id: str, limit: int = 25) -> List[Dict[str, Any]]:
    rows = neo4j_v2.run(
        """
        MATCH (b:Brand {id: $bid})-[:OWNS_SCENE]->(s:Scene)
        OPTIONAL MATCH (s)-[:HAS_PLACEMENT|HAS_LIGHT|HAS_CAMERA|HAS_TEXT_LAYER|HAS_TERRAIN]->(t)
        OPTIONAL MATCH (t)<-[:MODIFIED]-(i:Interaction)
        RETURN DISTINCT i ORDER BY i.created_at DESC LIMIT $limit
        """,
        bid=brand_id, limit=limit,
    )
    return [r["i"] for r in rows if r.get("i")]
