"""Capstone GraphRAG image-manipulation endpoints."""

from __future__ import annotations

import io
import math

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image

from app.capstone.models import (
    BoundingBox,
    CreateObjectRequest,
    CreateSceneRequest,
    CreateTextRegionRequest,
    InpaintTuning,
    RemoveObjectRequest,
    RecordEditRequest,
    SegmentationTuning,
    SegmentClickRequest,
    UpdateAspectRatioRequest,
)
from app.capstone.inference import LaMaUnavailableError, SAM2UnavailableError, lama_inpainter, sam2_segmenter
from app.capstone.store import capstone_scene_store
from app.rendering.storage import put_bytes


router = APIRouter(prefix="/api/v3", tags=["Capstone V3"])


def _ratio_string(width: int, height: int) -> str:
    divisor = math.gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


@router.get("/capabilities")
def get_capstone_capabilities():
    return {
        "sam2": sam2_segmenter.status(),
        "lama": lama_inpainter.status(),
    }


@router.get("/accuracy-presets")
def get_accuracy_presets():
    return {
        "segmentation": {
            "balanced": SegmentationTuning().model_dump(),
            "tight_edges": SegmentationTuning(dilate_px=0, erode_px=1, min_area_fraction=0.0005).model_dump(),
            "object_recall": SegmentationTuning(
                multimask_strategy="largest_mask",
                dilate_px=2,
                erode_px=0,
                min_area_fraction=0.002,
            ).model_dump(),
        },
        "inpainting": {
            "balanced": InpaintTuning().model_dump(),
            "background_cleanup": InpaintTuning(mask_dilate_px=8, neighbor_limit=6).model_dump(),
            "detail_preserve": InpaintTuning(mask_dilate_px=2, neighbor_limit=4).model_dump(),
        },
    }


@router.post("/scenes/upload")
async def upload_scene_image(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    owner_user_id: str = Form(default="local-user"),
    email: str | None = Form(default=None),
):
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        image = Image.open(io.BytesIO(payload)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="File is not a readable image") from exc

    width, height = image.size
    suffix = ".png"
    if file.filename and "." in file.filename:
        suffix = "." + file.filename.rsplit(".", 1)[-1].lower()
    image_url = put_bytes("capstone/originals", f"scene-upload{suffix}", payload, mime=file.content_type or "image/png")

    doc = capstone_scene_store.create_scene(
        CreateSceneRequest(
            image_path=image_url,
            canvas_width=width,
            canvas_height=height,
            aspect_ratio=_ratio_string(width, height),
            owner_user_id=owner_user_id,
            title=title or file.filename,
            email=email,
        )
    )
    return doc


@router.post("/scenes")
def create_scene(req: CreateSceneRequest):
    doc = capstone_scene_store.create_scene(req)
    return {
        "scene_id": doc.scene.scene_id,
        "schema_version": doc.scene.schema_version,
        "storage_mode": "json+neo4j_optional",
        "scene": doc.scene,
        "user": doc.user,
        "objects": doc.objects,
        "edit_events": doc.edit_events,
        "canvas_versions": doc.canvas_versions,
    }


@router.get("/scenes/{scene_id}")
def get_scene(scene_id: str):
    try:
        return capstone_scene_store.get_scene(scene_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Scene not found") from exc


@router.post("/scenes/{scene_id}/objects")
def add_object(scene_id: str, req: CreateObjectRequest):
    try:
        doc = capstone_scene_store.add_object(scene_id, req)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Scene not found") from exc
    return {
        "scene_id": scene_id,
        "objects": doc.objects,
        "spatial_relationships": doc.spatial_relationships,
    }


@router.post("/scenes/{scene_id}/text-regions")
def add_text_region(scene_id: str, req: CreateTextRegionRequest):
    try:
        doc = capstone_scene_store.add_text_region(scene_id, req)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Scene not found") from exc
    return {
        "scene_id": scene_id,
        "objects": doc.objects,
        "text_regions": doc.text_regions,
        "spatial_relationships": doc.spatial_relationships,
    }


@router.post("/scenes/{scene_id}/edits")
def record_edit(scene_id: str, req: RecordEditRequest):
    try:
        event = capstone_scene_store.record_edit(scene_id, req)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Scene not found") from exc
    return event


@router.post("/scenes/{scene_id}/aspect-ratio")
def update_aspect_ratio(scene_id: str, req: UpdateAspectRatioRequest):
    try:
        return capstone_scene_store.update_aspect_ratio(scene_id, req)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Scene not found") from exc


@router.get("/scenes/{scene_id}/history")
def get_history(scene_id: str):
    try:
        history = capstone_scene_store.get_history(scene_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Scene not found") from exc
    return {"scene_id": scene_id, "history": history}


@router.get("/scenes/{scene_id}/inpaint-context/{object_id}")
def get_inpaint_context(scene_id: str, object_id: str, limit: int = 5):
    try:
        neighbors = capstone_scene_store.get_inpaint_context(scene_id, object_id, limit=limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Scene not found") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Object not found") from exc
    return {"scene_id": scene_id, "object_id": object_id, "neighbors": neighbors}


@router.post("/scenes/{scene_id}/segment-click")
def segment_click(scene_id: str, req: SegmentClickRequest):
    try:
        scene_doc = capstone_scene_store.get_scene(scene_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Scene not found") from exc

    try:
        result = sam2_segmenter.segment_from_click(
            scene_doc.scene.image_path,
            req.click_x,
            req.click_y,
            req.label,
            req.tuning,
        )
    except SAM2UnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"SAM 2 segmentation failed: {exc}") from exc

    if req.register_object:
        bbox = result["bbox"]
        updated = capstone_scene_store.upsert_segmented_object(
            scene_id,
            class_label=req.label,
            bbox=BoundingBox(x=bbox[0], y=bbox[1], w=bbox[2] - bbox[0], h=bbox[3] - bbox[1]),
            mask_path=result["mask_url"],
            confidence=min(req.confidence, float(result.get("score", req.confidence))),
            object_id=req.object_id,
            z_order=req.z_order,
        )
        object_id = req.object_id
        if object_id is None:
            object_id = updated.objects[-1].object_id
        result["scene_object_id"] = object_id
        result["spatial_relationships"] = updated.spatial_relationships
        result["registered_object"] = next((obj for obj in updated.objects if obj.object_id == object_id), None)

    return result


@router.post("/scenes/{scene_id}/remove-object")
def remove_object(scene_id: str, req: RemoveObjectRequest):
    try:
        scene_doc = capstone_scene_store.get_scene(scene_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Scene not found") from exc

    target = next((obj for obj in scene_doc.objects if obj.object_id == req.object_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Object not found")
    if not target.mask_path:
        raise HTTPException(status_code=400, detail="Object does not have a stored segmentation mask")

    neighbor_limit = req.tuning.neighbor_limit if req.tuning else 5
    neighbors = capstone_scene_store.get_inpaint_context(scene_id, req.object_id, limit=neighbor_limit)
    try:
        result = lama_inpainter.inpaint(scene_doc.scene.image_path, target.mask_path, req.tuning)
    except LaMaUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LaMa inpainting failed: {exc}") from exc

    updated = capstone_scene_store.remove_object(
        scene_id,
        object_id=req.object_id,
        composite_image_path=result["result_url"],
        context_neighbors=neighbors,
        metadata={"inpaint_tuning": req.tuning.model_dump() if req.tuning else {}},
    )
    return {
        "scene_id": scene_id,
        "removed_object_id": req.object_id,
        "result_url": result["result_url"],
        "method": result["method"],
        "context_neighbors": neighbors,
        "scene": updated.scene,
        "objects": updated.objects,
        "history_size": len(updated.edit_events),
    }
