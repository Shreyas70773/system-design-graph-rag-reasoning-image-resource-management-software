"""/api/v2/jobs — read-only job status + SSE stream."""

from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.jobs import default_queue

router = APIRouter(prefix="/api/v2/jobs", tags=["V2 Jobs"])


def _job_to_dict(job) -> Dict[str, Any]:
    return {
        "id": job.id,
        "pipeline": job.pipeline.value,
        "status": job.status.value,
        "progress_pct": job.progress_pct,
        "current_step": job.current_step,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "payload": job.payload,
        "result": job.result_json,
        "error": job.error,
    }


@router.get("/{job_id}")
def get_job(job_id: str) -> Dict[str, Any]:
    job = default_queue().get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return _job_to_dict(job)


@router.get("/{job_id}/stream")
def stream_job(job_id: str):
    queue = default_queue()
    if not queue.get(job_id):
        raise HTTPException(404, "Job not found")

    def event_stream():
        for job in queue.stream_updates(job_id, poll_interval_s=0.8):
            yield f"data: {json.dumps(_job_to_dict(job))}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
