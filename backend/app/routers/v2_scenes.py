"""/api/v2/scenes and /api/v2/renders — Pipeline B endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database.neo4j_v2 import neo4j_v2
from app.jobs import Pipeline, default_queue

router = APIRouter(prefix="/api/v2", tags=["V2 Scenes"])


class CameraRequest(BaseModel):
    shot_type: str = "hero"
    aspect_ratio: str = "1:1"


class SceneCreateRequest(BaseModel):
    brand_id: str
    intent_text: str
    deployment_context: str = "digital"
    # Accept either `cameras` or `camera_requests` from the client (legacy alias).
    cameras: Optional[List[CameraRequest]] = None
    camera_requests: Optional[List[CameraRequest]] = None
    sync: bool = False


class SceneResponse(BaseModel):
    job_id: Optional[str] = None
    scene_id: Optional[str] = None
    status: str = "queued"
    renders: List[Dict[str, Any]] = Field(default_factory=list)


class RenderRequest(BaseModel):
    camera_ids: Optional[List[str]] = None


@router.post("/scenes", response_model=SceneResponse)
def create_scene(req: SceneCreateRequest) -> SceneResponse:
    cams = req.cameras or req.camera_requests or [CameraRequest()]
    payload = {
        "brand_id": req.brand_id,
        "intent_text": req.intent_text,
        "deployment_context": req.deployment_context,
        "camera_requests": [c.model_dump() for c in cams],
    }
    if req.sync:
        from app.scene.pipeline import ScenePipeline
        result = ScenePipeline().create_and_render(payload)
        return SceneResponse(
            job_id=None,
            scene_id=result.get("scene_id"),
            status="completed",
            renders=result.get("renders", []),
        )
    queue = default_queue()
    job_id = queue.submit(Pipeline.B_ASSEMBLY, payload)
    return SceneResponse(job_id=job_id, status="queued")


@router.get("/scenes/{scene_id}")
def get_scene(scene_id: str) -> Dict[str, Any]:
    data = neo4j_v2.get_scene_full(scene_id)
    if not data["scene"]:
        raise HTTPException(404, "Scene not found")
    return data


@router.post("/scenes/{scene_id}/render")
def render(scene_id: str, req: Optional[RenderRequest] = None) -> Dict[str, Any]:
    payload = {
        "mode": "render_only",
        "scene_id": scene_id,
        "camera_ids": (req.camera_ids if req else None) or None,
    }
    queue = default_queue()
    job_id = queue.submit(Pipeline.B_ASSEMBLY, payload)
    return {"job_id": job_id, "status": "queued"}


@router.get("/renders/{render_id}")
def get_render(render_id: str) -> Dict[str, Any]:
    rows = neo4j_v2.run("MATCH (r:Render {id: $id}) RETURN r", id=render_id)
    if not rows:
        raise HTTPException(404, "Render not found")
    return rows[0]["r"]


@router.get("/renders/{render_id}/object-at")
def object_at_pixel(render_id: str, x: int, y: int) -> Dict[str, Any]:
    """Resolve a pixel click → placement / text-layer id via the object-ID pass."""
    rows = neo4j_v2.run("MATCH (r:Render {id: $id}) RETURN r", id=render_id)
    if not rows:
        raise HTTPException(404, "Render not found")
    render = rows[0]["r"]
    id_url = render.get("object_id_pass_url")
    if not id_url:
        return {"resolved": False, "reason": "no object_id pass"}

    # Load the PNG and sample (x,y). Convert RGB triplet → placement index.
    from app.rendering.storage import fetch_image_bytes
    from PIL import Image
    import io
    data = fetch_image_bytes(id_url)
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    w, h = img.size
    if not (0 <= x < w and 0 <= y < h):
        raise HTTPException(400, f"pixel ({x},{y}) outside render {w}x{h}")
    r, g, b, a = img.getpixel((x, y))
    if a == 0 or (r, g, b) == (0, 0, 0):
        return {"resolved": False}
    idx = (r << 16) | (g << 8) | b
    # Look up the placement by position in the ordered placements list.
    scene = neo4j_v2.get_scene_full(render["scene_id"])
    placements = scene.get("placements", [])
    if 1 <= idx <= len(placements):
        placement = placements[idx - 1]
        return {"resolved": True, "placement_id": placement["id"], "asset_id": placement.get("asset_id")}
    return {"resolved": False}
