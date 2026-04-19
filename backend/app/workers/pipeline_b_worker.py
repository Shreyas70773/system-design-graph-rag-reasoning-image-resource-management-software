"""Pipeline B worker. Handles both 'create new scene + render' jobs and
're-render existing scene' jobs."""

from __future__ import annotations

import logging
import traceback
from typing import Dict

from app.jobs import Job, JobQueue
from app.scene.pipeline import ScenePipeline

logger = logging.getLogger(__name__)


def handle(job: Job, queue: JobQueue) -> None:
    pipeline = ScenePipeline(queue=queue)
    try:
        payload: Dict = job.payload
        queue.update_progress(job.id, 5, "intent_parse")
        if payload.get("mode") == "render_only":
            result = pipeline.render_scene_cameras(
                payload["scene_id"],
                only_camera_ids=payload.get("camera_ids"),
            )
            queue.complete(job.id, {"scene_id": payload["scene_id"], "renders": result})
            return
        queue.update_progress(job.id, 20, "retrieve")
        result = pipeline.create_and_render(payload)
        queue.complete(job.id, result)
    except Exception as exc:
        logger.exception("Pipeline B failed for job %s", job.id)
        queue.fail(job.id, f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}")
