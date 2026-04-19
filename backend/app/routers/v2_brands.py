"""/api/v2/brands — brand CRUD (create + get), preferences panel, retrieval preview."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database.neo4j_v2 import _gen_id, _now_iso, neo4j_v2
from app.interaction.retrieval_bias import compile_biases

router = APIRouter(prefix="/api/v2/brands", tags=["V2 Brands"])


class CreateBrandRequest(BaseModel):
    name: str
    primary_hex: List[str] = Field(default_factory=list)
    secondary_hex: List[str] = Field(default_factory=list)
    accent_hex: List[str] = Field(default_factory=list)
    voice_keywords: List[str] = Field(default_factory=list)
    description: Optional[str] = None


@router.post("")
def create_brand(req: CreateBrandRequest) -> Dict[str, Any]:
    """Create a V2-conformant brand. Attaches primary colors as :Color nodes."""
    brand_id = _gen_id()
    ts = _now_iso()
    neo4j_v2.run_write(
        "CREATE (b:Brand {id: $id, name: $name, schema_version: '2.0', "
        "primary_hex: $primary, secondary_hex: $secondary, accent_hex: $accent, "
        "voice_keywords: $voice, description: $desc, "
        "created_at: $ts, updated_at: $ts})",
        id=brand_id, name=req.name,
        primary=req.primary_hex, secondary=req.secondary_hex, accent=req.accent_hex,
        voice=req.voice_keywords, desc=req.description or "", ts=ts,
    )
    for idx, hx in enumerate(req.primary_hex):
        # MERGE on hex so we share Color nodes with legacy data that enforces
        # a uniqueness constraint on Color.hex. Each brand→color relationship
        # is still a distinct edge.
        neo4j_v2.run_write(
            "MATCH (b:Brand {id: $bid}) "
            "MERGE (c:Color {hex: $hex}) "
            "  ON CREATE SET c.id = $cid, c.role = 'primary', c.rank = $rank, "
            "                c.schema_version = '2.0', c.created_at = $ts, c.updated_at = $ts "
            "MERGE (b)-[r:HAS_COLOR]->(c) "
            "  ON CREATE SET r.created_at = $ts, r.rank = $rank",
            bid=brand_id, cid=_gen_id(), hex=hx, rank=idx, ts=ts,
        )
    return {"brand_id": brand_id, "name": req.name}


@router.get("/{brand_id}")
def get_brand(brand_id: str) -> Dict[str, Any]:
    brand = neo4j_v2.get_brand_v2(brand_id)
    if not brand:
        raise HTTPException(404, "Brand not found")
    return {"brand": brand}


@router.get("/{brand_id}/preferences")
def list_preferences(brand_id: str) -> Dict[str, Any]:
    sigs = neo4j_v2.get_active_preferences(brand_id)
    biases = compile_biases(sigs)
    return {"signals": sigs, "compiled_biases": biases}


@router.delete("/{brand_id}/preferences/{signal_id}")
def delete_preference(brand_id: str, signal_id: str) -> Dict[str, Any]:
    removed = neo4j_v2.delete_preference(brand_id, signal_id)
    if not removed:
        raise HTTPException(404, "Preference signal not found")
    return {"removed": True, "signal_id": signal_id}


@router.get("/{brand_id}/retrieval-preview")
def retrieval_preview(brand_id: str, deployment_context: str = "digital") -> Dict[str, Any]:
    ctx = neo4j_v2.retrieve_brand_context(brand_id, deployment_context)
    biases = compile_biases(ctx.get("preferences") or [])
    # Strip big props (e.g., clip_embedding).
    def _slim(node: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(node or {})
        out.pop("clip_embedding", None)
        return out
    return {
        "brand": _slim(ctx.get("brand") or {}),
        "colors": [_slim(c) for c in ctx.get("colors") or []],
        "fonts": [_slim(f) for f in ctx.get("fonts") or []],
        "approved_assets": len([a for a in ctx.get("assets") or [] if a.get("ingestion_status") == "approved"]),
        "total_assets": len(ctx.get("assets") or []),
        "compiled_biases": biases,
    }
