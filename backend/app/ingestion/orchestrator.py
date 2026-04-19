"""Pipeline A orchestrator.

Runs the seven steps sequentially with explicit VRAM-aware boundaries:
  - each step imports its own heavy deps lazily
  - each step emits a progress update
  - state machine writes go through neo4j_v2 with pipeline-a methods only
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Optional

from app.database.neo4j_v2 import neo4j_v2
from app.ingestion.models import IngestionJob, StepName
from app.ingestion.steps import delight, describe, intake, mesh, segment, validate
from app.jobs import JobQueue, Pipeline

logger = logging.getLogger(__name__)


class IngestionOrchestrator:
    def __init__(self, queue: Optional[JobQueue] = None) -> None:
        self.queue = queue

    def run(self, job_id: str, payload: Dict) -> Dict:
        brand_id = payload["brand_id"]
        asset_type = payload["asset_type"]
        source_url = payload["source_image_url"]

        asset_id = neo4j_v2.pipeline_a_create_asset(
            brand_id=brand_id, asset_type=asset_type, source_url=source_url,
        )
        started_at = datetime.utcnow().isoformat()

        self._progress(job_id, 5, StepName.INTAKE)
        intake_out = intake.run_intake(source_url, asset_type)
        neo4j_v2.pipeline_a_update_asset_status(
            asset_id, "decomposing", source_url=intake_out["canonical_url"],
        )

        self._progress(job_id, 15, StepName.DESCRIBE)
        describe_out = describe.run(intake_out["canonical_url"], asset_type)
        neo4j_v2.pipeline_a_set_vlm_description(
            asset_id,
            describe_out["description"],
            describe_out.get("clip_embedding"),
        )

        self._progress(job_id, 35, StepName.SEGMENT)
        part_records = segment.run(intake_out["canonical_url"], describe_out["estimated_parts"])
        part_ids = []
        for part in part_records:
            pid = neo4j_v2.pipeline_a_attach_part(asset_id, part)
            part_ids.append(pid)

        self._progress(job_id, 55, StepName.DELIGHT)
        delight_out = delight.run(intake_out["canonical_url"])
        neo4j_v2.pipeline_a_attach_light_probe(asset_id, delight_out["light_probe"])
        material_id = neo4j_v2.pipeline_a_attach_material(
            asset_id,
            {
                "albedo_url": delight_out["albedo_url"],
                "albedo_dominant_hex": delight_out["albedo_dominant_hex"],
                "uv_set_index": 0,
            },
        )

        self._progress(job_id, 80, StepName.MESH)
        mesh_out = mesh.run(delight_out["albedo_url"], intake_out["canonical_url"], asset_type)
        mesh_id = neo4j_v2.pipeline_a_attach_mesh(asset_id, mesh_out)
        neo4j_v2.pipeline_a_attach_canonical_pose(asset_id, {
            "rotation_quat": [0.0, 0.0, 0.0, 1.0],
            "suggested_camera_position": [0.0, 0.4, 1.2],
            "suggested_camera_focal_mm": 50.0,
        })

        self._progress(job_id, 95, StepName.VALIDATE)
        val_out = validate.run(asset_id, mesh_out["file_url"], intake_out["canonical_url"])

        run_id = neo4j_v2.pipeline_a_record_decomposition_run(asset_id, {
            "pipeline_version": "A/1.0.0",
            "vlm_model": describe_out.get("vlm_model", "unknown"),
            "segmenter_model": "mock/banded" if not part_records else "mock/banded",
            "delighter_model": "mock/pil",
            "mesh_model": mesh_out.get("generator_model", "mock/cube"),
            "started_at": started_at,
            "completed_at": datetime.utcnow().isoformat(),
            "user_approved": False,
            "confidence_overall": val_out["confidence_overall"],
        })

        neo4j_v2.pipeline_a_update_asset_status(asset_id, "awaiting_approval")

        self._progress(job_id, 100, StepName.AWAIT_APPROVAL)
        return {
            "asset_id": asset_id,
            "mesh_id": mesh_id,
            "material_id": material_id,
            "part_ids": part_ids,
            "decomposition_run_id": run_id,
            "status": "awaiting_approval",
            "validation": val_out,
        }

    def _progress(self, job_id: str, pct: int, step: StepName) -> None:
        if self.queue:
            self.queue.update_progress(job_id, pct, step.value)
        logger.info("[ingestion] job=%s step=%s pct=%s", job_id, step.value, pct)
