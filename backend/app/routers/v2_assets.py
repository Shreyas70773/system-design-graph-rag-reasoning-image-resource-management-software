"""/api/v2/assets — Pipeline A endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database.neo4j_v2 import neo4j_v2
from app.jobs import Pipeline, default_queue
from app.schema_v2 import AssetType, EditTargetKind, InteractionType, StructuredEditCommand

router = APIRouter(prefix="/api/v2/assets", tags=["V2 Assets"])


class AssetIngestRequest(BaseModel):
    brand_id: str
    asset_type: AssetType
    source_image_url: str
    notes: Optional[str] = None
    # When true, runs the ingestion orchestrator inline instead of queueing.
    # Useful for tests / smoke runs / small assets in mock mode. Real ML paths
    # should always use the async queue.
    sync: bool = False


class AssetIngestResponse(BaseModel):
    job_id: Optional[str] = None
    asset_id: Optional[str] = None
    status: str = "queued"


class PartRegenerateRequest(BaseModel):
    part_id: str
    strategy: str = Field(default="crop_and_realign", pattern="^(crop_and_realign|whole_object_emphasis)$")


@router.post("", response_model=AssetIngestResponse)
def ingest_asset(req: AssetIngestRequest) -> AssetIngestResponse:
    brand = neo4j_v2.get_brand_v2(req.brand_id)
    if not brand:
        raise HTTPException(404, f"Brand {req.brand_id} not found or not V2-compatible")
    if req.sync:
        from app.ingestion.orchestrator import IngestionOrchestrator
        result = IngestionOrchestrator().run("ingest", req.model_dump(mode="json"))
        return AssetIngestResponse(
            job_id=None,
            asset_id=result.get("asset_id"),
            status=result.get("status", "completed"),
        )
    queue = default_queue()
    job_id = queue.submit(Pipeline.A_INGESTION, req.model_dump(mode="json"))
    return AssetIngestResponse(job_id=job_id, status="queued")


@router.get("/{asset_id}")
def get_asset(asset_id: str) -> Dict[str, Any]:
    data = neo4j_v2.get_asset_full(asset_id)
    if not data["asset"]:
        raise HTTPException(404, "Asset not found")
    return data


@router.post("/{asset_id}/approve")
def approve_asset(asset_id: str) -> Dict[str, Any]:
    from app.interaction.applier import apply

    data = neo4j_v2.get_asset_full(asset_id)
    if not data["asset"]:
        raise HTTPException(404, "Asset not found")
    cmd = StructuredEditCommand(
        action=InteractionType.APPROVE_DECOMPOSITION,
        target_kind=EditTargetKind.ASSET,
        target_id=asset_id,
        params={},
    )
    result = apply(cmd, actor="creative_director", surface="asset_editor")
    return {"asset_id": asset_id, **result}


@router.post("/{asset_id}/reject")
def reject_asset(asset_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    from app.interaction.applier import apply

    cmd = StructuredEditCommand(
        action=InteractionType.REJECT_DECOMPOSITION,
        target_kind=EditTargetKind.ASSET,
        target_id=asset_id,
        params={"reason": reason} if reason else {},
    )
    result = apply(cmd, actor="creative_director", surface="asset_editor")
    return {"asset_id": asset_id, **result}


@router.post("/{asset_id}/regenerate-part")
def regenerate_part(asset_id: str, req: PartRegenerateRequest) -> Dict[str, Any]:
    queue = default_queue()
    job_id = queue.submit(Pipeline.A_INGESTION, {
        "mode": "regenerate_part",
        "asset_id": asset_id,
        "part_id": req.part_id,
        "strategy": req.strategy,
    })
    return {"job_id": job_id, "status": "queued"}


@router.get("")
def list_assets(brand_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    where = "a.ingestion_status = $status" if status else "true"
    rows = neo4j_v2.run(
        f"MATCH (b:Brand {{id: $bid}})-[:HAS_ASSET]->(a:Asset) WHERE {where} "
        "RETURN a ORDER BY a.created_at DESC",
        bid=brand_id, status=status or "",
    )
    return [r["a"] for r in rows]
