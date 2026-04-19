"""Pipeline A worker. Claims ingestion jobs from the queue and drives the
orchestrator. Runs in the same Python process as the FastAPI app in dev, or
as a standalone process in prod."""

from __future__ import annotations

import logging
import traceback
from typing import Dict

from app.ingestion.orchestrator import IngestionOrchestrator
from app.jobs import Job, JobQueue, Pipeline

logger = logging.getLogger(__name__)


def handle(job: Job, queue: JobQueue) -> None:
    orch = IngestionOrchestrator(queue=queue)
    try:
        payload: Dict = job.payload
        if payload.get("mode") == "regenerate_part":
            result = _regenerate_part(payload)
        else:
            result = orch.run(job.id, payload)
        queue.complete(job.id, result)
    except Exception as exc:
        logger.exception("Pipeline A failed for job %s", job.id)
        queue.fail(job.id, f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}")


def _regenerate_part(payload: Dict) -> Dict:
    # MVP: mark the part as "regenerating" then immediately restored; real
    # per-part pipeline (crop-and-realign or whole-object-emphasis) lands Phase 6.
    from app.database.neo4j_v2 import neo4j_v2
    from datetime import datetime

    asset_id = payload["asset_id"]
    part_id = payload["part_id"]
    strategy = payload.get("strategy", "crop_and_realign")
    neo4j_v2.update_node_fields("SemanticPart", part_id, {
        "last_regeneration_strategy": strategy,
        "last_regenerated_at": datetime.utcnow().isoformat(),
    })
    return {"asset_id": asset_id, "part_id": part_id, "strategy": strategy, "status": "completed (stub)"}
