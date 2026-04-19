"""Layer editing REST API.

Endpoints
---------
POST /api/v2/compose          — generate initial branded composition
POST /api/v2/layers/segment   — click-to-mask (SAM or ellipse mock)
POST /api/v2/layers/edit      — brand-conditioned inpaint + composite + measure
GET  /api/v2/layers/history/{brand_id}  — recent edits stored in Neo4j
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database.neo4j_client import neo4j_client
from app.services.graph_conditioning import GraphConditioner
from app.layers.segmenter import segment_from_click
from app.layers.inpainter import inpaint
from app.layers.compositor import composite_and_measure, sanitize_palette_hex
from app.layers.composer import compose_image_async
from app.layers.text_overlay import render_text_in_masked_region

logger = logging.getLogger(__name__)
router = APIRouter(tags=["v2-layers"])
_conditioner = GraphConditioner()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ComposeRequest(BaseModel):
    brand_id: Optional[str] = None
    prompt: str
    aspect_ratio: str = "1:1"
    seed: Optional[int] = None


class SegmentRequest(BaseModel):
    image_url: str
    click_x: float = Field(ge=0.0, le=1.0)
    click_y: float = Field(ge=0.0, le=1.0)
    label: str = "object"
    selection_scale: float = Field(
        1.0,
        ge=0.35,
        le=2.5,
        description="Mock/SAM ellipse scale: <1 tighter, >1 larger selection",
    )


class EditRequest(BaseModel):
    image_url: str
    mask_url: str
    brand_id: Optional[str] = None
    prompt: str
    layer_name: str = "object"
    conditioned: bool = True   # False = ablation (no graph conditioning)
    seed: Optional[int] = None
    text_mode: bool = False    # True = Canva-style raster text (Pillow), not an image model
    new_text: Optional[str] = None
    text_color_hex: Optional[str] = None   # e.g. #1a1a1a; omit for auto contrast vs background
    text_font_scale: float = Field(1.0, ge=0.4, le=3.0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_brand_conditioning(brand_id: Optional[str]) -> tuple[dict, list[str], Optional[str]]:
    """
    Return (conditioning_packet_dict, brand_color_hexes, reference_url).
    Silently degrades if Neo4j is unavailable or brand not found.
    """
    if not brand_id:
        return {}, [], None
    try:
        ctx = neo4j_client.get_brand_context(brand_id)
        if not ctx:
            return {}, [], None
        packet = _conditioner.build_packet(ctx, {"brand_id": brand_id}, "graph_rag")
        colors = packet.palette_hex
        ref = packet.product_reference_url or packet.character_reference_url
        return packet.as_dict(), colors, ref
    except Exception as exc:
        logger.warning("Brand context fetch failed for %s: %s", brand_id, exc)
        return {}, [], None


def _brand_context_for_compose(
    brand_id: Optional[str],
    conditioning: dict,
    palette_hex: List[str],
) -> dict:
    """Full Neo4j context when available; otherwise a minimal dict for SDXL prompts."""
    if brand_id:
        try:
            ctx = neo4j_client.get_brand_context(brand_id)
            if ctx:
                return ctx
        except Exception as exc:
            logger.debug("get_brand_context failed: %s", exc)
    return {
        "name": "Brand",
        "colors": [{"hex": h} for h in palette_hex if h],
        "styles": [{"name": str(s)} for s in conditioning.get("style_keywords", [])],
        "tagline": "",
        "selected_products": [],
    }


def _record_edit(brand_id: Optional[str], edit_id: str, metrics: dict, layer_name: str, conditioned: bool):
    """Persist edit as a Feedback node in Neo4j (best-effort)."""
    if not brand_id:
        return
    try:
        neo4j_client.execute_query(
            """
            MATCH (b:Brand {id: $brand_id})
            CREATE (f:Feedback {
                id: $edit_id,
                layer_name: $layer_name,
                conditioned: $conditioned,
                background_ssim: $bg_ssim,
                brand_delta_e: $delta_e,
                identity_ssim: $id_ssim,
                created_at: datetime()
            })
            CREATE (b)-[:HAS_FEEDBACK]->(f)
            """,
            {
                "brand_id": brand_id,
                "edit_id": edit_id,
                "layer_name": layer_name,
                "conditioned": conditioned,
                "bg_ssim": metrics.get("background_ssim"),
                "delta_e": metrics.get("brand_delta_e"),
                "id_ssim": metrics.get("identity_ssim"),
            },
        )
    except Exception as exc:
        logger.debug("Could not persist edit to Neo4j: %s", exc)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/api/v2/compose")
async def compose_image(req: ComposeRequest):
    """Generate a full brand-aligned composition as the editing canvas (real models only)."""
    conditioning, brand_colors, _ = _fetch_brand_conditioning(req.brand_id)
    brand_ctx = _brand_context_for_compose(req.brand_id, conditioning, brand_colors)
    try:
        result = await compose_image_async(
            prompt=req.prompt,
            brand_conditioning=conditioning,
            brand_context=brand_ctx,
            aspect_ratio=req.aspect_ratio,
            seed=req.seed,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    result["brand_colors"] = brand_colors
    result["conditioning"] = conditioning
    result["graph_rag"] = {
        "applied": bool(req.brand_id and conditioning),
        "brand_id": req.brand_id,
        "signals": sorted(conditioning.keys()) if conditioning else [],
        "note": "Each request loads Brand + related nodes from Neo4j and builds a GraphConditioner packet (palette, styles, references).",
    }
    return result


@router.post("/api/v2/layers/segment")
def segment_layer(req: SegmentRequest):
    """Return a mask for the clicked region."""
    return segment_from_click(
        req.image_url,
        req.click_x,
        req.click_y,
        req.label,
        selection_scale=req.selection_scale,
    )


@router.post("/api/v2/layers/edit")
def edit_layer(req: EditRequest):
    """
    Brand-conditioned inpaint + composite + measure.

    When conditioned=False, brand context is zeroed out (ablation mode).
    This lets the caller compare the same prompt with and without graph conditioning.
    """
    edit_id = str(uuid.uuid4())[:8]

    if req.conditioned:
        conditioning, brand_colors, reference_url = _fetch_brand_conditioning(req.brand_id)
    else:
        conditioning, brand_colors, reference_url = {}, [], None

    brand_colors_clean = sanitize_palette_hex([str(c) for c in brand_colors]) if brand_colors else []
    graph_rag_used = bool(req.brand_id and conditioning)

    if req.text_mode:
        wording = (req.new_text if req.new_text is not None else req.prompt).strip()
        if not wording:
            raise HTTPException(status_code=400, detail="text_mode requires non-empty text")
        try:
            inpaint_result = render_text_in_masked_region(
                image_url=req.image_url,
                mask_url=req.mask_url,
                text=wording,
                color_hex=req.text_color_hex,
                font_scale=req.text_font_scale,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        inpaint_result["conditioning_applied"] = {"mode": "live_text_overlay", "graph_rag_loaded": graph_rag_used}
        inpaint_result["attempts"] = ["pillow:text_overlay"]
    else:
        inpaint_result = inpaint(
            image_url=req.image_url,
            mask_url=req.mask_url,
            prompt=req.prompt,
            brand_conditioning=conditioning,
            seed=req.seed,
        )

    composite_result = composite_and_measure(
        original_url=req.image_url,
        inpainted_url=inpaint_result["result_url"],
        mask_url=req.mask_url,
        brand_colors=brand_colors_clean,
        reference_url=reference_url,
    )

    metrics = composite_result["metrics"]
    layer_tag = "text" if req.text_mode else req.layer_name
    _record_edit(req.brand_id, edit_id, metrics, layer_tag, req.conditioned)

    return {
        "edit_id": edit_id,
        "result_url": composite_result["result_url"],
        "inpaint_url": inpaint_result["result_url"],
        "metrics": metrics,
        "method": inpaint_result.get("method"),
        "prompt_used": inpaint_result.get("prompt_used"),
        "conditioning_applied": inpaint_result.get("conditioning_applied", {}),
        "attempts": inpaint_result.get("attempts", []),
        "text_mode": req.text_mode,
        "conditioned": req.conditioned,
        "graph_rag": {
            "applied": graph_rag_used,
            "brand_id": req.brand_id,
            "palette_used_in_metrics": len(brand_colors_clean),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api/v2/layers/history/{brand_id}")
def get_layer_history(brand_id: str, limit: int = 20):
    """Fetch recent layer edits for a brand from Neo4j."""
    try:
        rows = neo4j_client.execute_query(
            """
            MATCH (b:Brand {id: $brand_id})-[:HAS_FEEDBACK]->(f:Feedback)
            RETURN f.id AS edit_id,
                   f.layer_name AS layer_name,
                   f.conditioned AS conditioned,
                   f.background_ssim AS background_ssim,
                   f.brand_delta_e AS brand_delta_e,
                   f.identity_ssim AS identity_ssim,
                   toString(f.created_at) AS created_at
            ORDER BY f.created_at DESC
            LIMIT $limit
            """,
            {"brand_id": brand_id, "limit": limit},
        )
        return {"brand_id": brand_id, "edits": rows}
    except Exception as exc:
        logger.warning("History fetch failed: %s", exc)
        return {"brand_id": brand_id, "edits": []}
