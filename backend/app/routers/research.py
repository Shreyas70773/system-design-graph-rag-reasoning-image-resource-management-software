"""
Research router for controlled generation experiments and ablations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
import csv
import io

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.database.neo4j_client import neo4j_client
from app.services.experiment_runner import ManifestConflictError, get_experiment_runner
from app.services.stats_analyzer import StatsAnalyzer


router = APIRouter(prefix="/research", tags=["Research"])
stats_analyzer = StatsAnalyzer()


def _flatten_run_for_export(run: Dict[str, Any], metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten run + candidate metrics into export-friendly rows."""
    rows: List[Dict[str, Any]] = []

    # Build lookup for latest candidate metric by candidate_id.
    metric_lookup: Dict[str, Dict[str, Any]] = {}
    for metric_node in metrics:
        if metric_node.get("level") != "candidate":
            continue
        candidate_id = metric_node.get("candidate_id")
        if not candidate_id:
            continue
        metric_lookup[candidate_id] = metric_node.get("metrics", {})

    for candidate in run.get("candidates", []):
        candidate_id = candidate.get("id")
        candidate_metrics = metric_lookup.get(candidate_id, {})
        rows.append({
            "run_id": run.get("id"),
            "experiment_id": run.get("experiment_id"),
            "brand_id": run.get("brand_id"),
            "method_name": run.get("method_name"),
            "candidate_id": candidate_id,
            "seed": candidate.get("seed"),
            "status": candidate.get("status"),
            "image_url": candidate.get("image_url"),
            "model_used": candidate.get("model_used"),
            "provider": candidate.get("provider"),
            "latency_ms": candidate.get("latency_ms"),
            "brand_score": candidate_metrics.get("brand_score"),
            "color_alignment_score": candidate_metrics.get("color_alignment_score"),
            "palette_match_rate": candidate_metrics.get("palette_match_rate"),
            "delta_e_proxy": candidate_metrics.get("delta_e_proxy"),
            "delta_e_ciede2000_mean": candidate_metrics.get("delta_e_ciede2000_mean"),
            "delta_e_ciede2000_median": candidate_metrics.get("delta_e_ciede2000_median"),
            "delta_e_ciede2000_pass_rate": candidate_metrics.get("delta_e_ciede2000_pass_rate"),
        })

    return rows


def _csv_response(rows: List[Dict[str, Any]], filename: str) -> StreamingResponse:
    """Create CSV download response from list of dict rows."""
    if not rows:
        rows = [{"message": "no rows"}]

    output = io.StringIO()
    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

    csv_data = output.getvalue()
    output.close()

    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


class ControlledGenerationRequest(BaseModel):
    brand_id: str
    prompt: str
    method_name: Literal[
        "prompt_only",
        "retrieval_prompt",
        "adapter_only",
        "graph_guided",
    ] = "graph_guided"
    image_provider: Literal["fal.ai", "replicate", "fallback", "comfyui"] = "comfyui"

    experiment_id: Optional[str] = None
    seeds: List[int] = Field(default_factory=lambda: [11, 22, 33])
    product_ids: List[str] = Field(default_factory=list)

    aspect_ratio: str = "1:1"
    num_inference_steps: int = Field(default=30, ge=5, le=100)
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0)

    use_comfyui: bool = False
    comfy_workflow: Optional[Dict[str, Any]] = None
    use_proxy_color: bool = True

    module_toggles: Dict[str, bool] = Field(
        default_factory=lambda: {
            "color_regularizer": True,
            "layout_constraint": True,
            "identity_lock": True,
            "dynamic_cfg": True,
        }
    )

    character_reference_url: Optional[str] = None
    notes: Optional[str] = None


class AblationRequest(BaseModel):
    brand_id: str
    prompt: str
    experiment_id: Optional[str] = None
    base_method: Literal["graph_guided", "adapter_only"] = "graph_guided"
    image_provider: Literal["fal.ai", "replicate", "fallback", "comfyui"] = "comfyui"
    seeds: List[int] = Field(default_factory=lambda: [11, 22, 33])
    product_ids: List[str] = Field(default_factory=list)

    num_inference_steps: int = Field(default=30, ge=5, le=100)
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0)

    ablations: List[Literal[
        "without_color_regularizer",
        "without_layout_constraint",
        "without_identity_lock",
        "fixed_cfg",
    ]] = Field(default_factory=lambda: [
        "without_color_regularizer",
        "without_layout_constraint",
        "without_identity_lock",
        "fixed_cfg",
    ])

    use_comfyui: bool = False
    comfy_workflow: Optional[Dict[str, Any]] = None


class ManifestValidationRequest(BaseModel):
    experiment_id: str
    brand_id: str
    prompt: str
    seeds: List[int] = Field(default_factory=lambda: [11, 22, 33])
    locked_config: Dict[str, Any] = Field(default_factory=dict)


@router.post("/generate-controlled")
async def generate_controlled(request: ControlledGenerationRequest):
    """Run a controlled experiment for one method across configured seeds."""
    runner = get_experiment_runner()
    try:
        return await runner.run_controlled_generation(request.model_dump())
    except ManifestConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "manifest_conflict",
                "message": str(exc),
                "conflict": exc.conflict,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/run-ablation")
async def run_ablation(request: AblationRequest):
    """Run base method and ablation variants under a shared experiment ID."""
    runner = get_experiment_runner()
    try:
        return await runner.run_ablation(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/metrics/{run_id}")
async def get_run_metrics(run_id: str):
    """Return run metadata plus all metric snapshots for a run."""
    run = neo4j_client.get_experiment_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found")

    metrics = neo4j_client.get_metrics_for_run(run_id)
    return {
        "run": run,
        "metrics": metrics,
    }


@router.get("/manifest/{experiment_id}")
async def get_manifest(experiment_id: str):
    """Get locked manifest for an experiment."""
    manifest = neo4j_client.get_experiment_manifest(experiment_id)
    if not manifest:
        raise HTTPException(status_code=404, detail="Experiment manifest not found")
    return manifest


@router.post("/manifest/validate")
async def validate_manifest(request: ManifestValidationRequest):
    """Validate a requested manifest against an existing experiment lock and return field-level diffs."""
    try:
        return neo4j_client.validate_experiment_manifest(request.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/compare/{experiment_id}")
async def compare_runs(experiment_id: str):
    """Return cross-run comparison payload for a shared experiment ID."""
    runner = get_experiment_runner()
    try:
        return await runner.compare_experiment(experiment_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stats/{experiment_id}")
async def compare_stats(
    experiment_id: str,
    metric: str = "brand_score",
    baseline_method: str = "prompt_only",
    bootstrap_resamples: int = Query(default=2000, ge=100, le=50000),
    ci_alpha: float = Query(default=0.05, gt=0.0, lt=0.5),
    random_seed: int = Query(default=42, ge=0),
):
    """Compute paired statistical comparisons for one metric across experiment methods."""
    try:
        rows = neo4j_client.get_candidate_metrics_for_experiment(experiment_id)
        if not rows:
            raise HTTPException(status_code=404, detail="No candidate metrics found for this experiment")

        comparison = stats_analyzer.compare_methods(
            rows=rows,
            metric_key=metric,
            baseline_method=baseline_method,
            ci_alpha=ci_alpha,
            bootstrap_resamples=bootstrap_resamples,
            random_seed=random_seed,
        )

        return {
            "experiment_id": experiment_id,
            "metric": metric,
            "baseline_method": baseline_method,
            "analysis": {
                "bootstrap_resamples": bootstrap_resamples,
                "ci_alpha": ci_alpha,
                "random_seed": random_seed,
            },
            "result": comparison,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/jobs/deltae/{run_id}")
async def run_deltae_job(run_id: str):
    """Run Lab-space DeltaE refinement job on a completed run."""
    runner = get_experiment_runner()
    try:
        return await runner.run_deltae_refinement_job(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/export/run/{run_id}")
async def export_run(run_id: str, format: Literal["json", "csv"] = "json"):
    """Export one run for thesis tables."""
    run = neo4j_client.get_experiment_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found")

    metrics = neo4j_client.get_metrics_for_run(run_id)
    rows = _flatten_run_for_export(run, metrics)

    payload = {
        "run": run,
        "metrics": metrics,
        "rows": rows,
    }

    if format == "csv":
        return _csv_response(rows, filename=f"run_{run_id}.csv")

    return payload


@router.get("/export/experiment/{experiment_id}")
async def export_experiment(experiment_id: str, format: Literal["json", "csv"] = "json"):
    """Export experiment-level method comparison table for reporting."""
    runs = neo4j_client.compare_experiment_runs(experiment_id)
    if not runs:
        raise HTTPException(status_code=404, detail="Experiment not found")

    rows: List[Dict[str, Any]] = []
    for run in runs:
        latest_run_metric = run.get("metrics", [])[-1].get("metrics", {}) if run.get("metrics") else {}
        rows.append({
            "experiment_id": experiment_id,
            "run_id": run.get("id"),
            "method_name": run.get("method_name"),
            "status": run.get("status"),
            "candidate_count": latest_run_metric.get("candidate_count"),
            "success_rate": latest_run_metric.get("success_rate"),
            "brand_score_mean": latest_run_metric.get("brand_score_mean"),
            "color_alignment_mean": latest_run_metric.get("color_alignment_mean"),
            "delta_e_ciede2000_mean": latest_run_metric.get("delta_e_ciede2000_mean"),
            "delta_e_ciede2000_pass_rate_mean": latest_run_metric.get("delta_e_ciede2000_pass_rate_mean"),
            "latency_ms_mean": latest_run_metric.get("latency_ms_mean"),
            "started_at": str(run.get("started_at")),
            "completed_at": str(run.get("completed_at")) if run.get("completed_at") is not None else None,
        })

    payload = {
        "experiment_id": experiment_id,
        "run_count": len(runs),
        "rows": rows,
    }

    if format == "csv":
        return _csv_response(rows, filename=f"experiment_{experiment_id}.csv")

    return payload


@router.get("/runs/{brand_id}")
async def list_runs(brand_id: str, limit: int = 20):
    """List recent research runs for a brand."""
    try:
        runs = neo4j_client.list_research_runs(brand_id, limit)
        return {
            "brand_id": brand_id,
            "count": len(runs),
            "runs": runs,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
