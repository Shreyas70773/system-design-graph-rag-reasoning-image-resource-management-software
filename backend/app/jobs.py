"""SQLite-backed job queue for Pipeline A and Pipeline B workers.

Phase 0 deliverable. Phase 2 may swap to Redis+RQ or Arq; the interface stays
stable so call sites don't change.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Iterator, Optional


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Pipeline(str, Enum):
    A_INGESTION = "A"
    B_ASSEMBLY = "B"
    C_INTERACTION = "C"


@dataclass
class Job:
    id: str
    pipeline: Pipeline
    status: JobStatus
    payload: dict
    created_at: datetime
    updated_at: datetime
    progress_pct: int = 0
    current_step: Optional[str] = None
    result_json: Optional[dict] = None
    error: Optional[str] = None


_DEFAULT_DB_PATH = Path("backend") / "jobs.sqlite"


class JobQueue:
    """Thread-safe SQLite-backed queue."""

    def __init__(self, db_path: Path = _DEFAULT_DB_PATH) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._path = db_path
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path, isolation_level=None, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    pipeline TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    progress_pct INTEGER NOT NULL DEFAULT 0,
                    current_step TEXT,
                    result_json TEXT,
                    error TEXT
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_jobs_pipeline ON jobs(pipeline)")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, pipeline: Pipeline, payload: dict) -> str:
        job_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with self._conn() as c:
            c.execute(
                "INSERT INTO jobs (id, pipeline, status, payload_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (job_id, pipeline.value, JobStatus.QUEUED.value, json.dumps(payload), now, now),
            )
        return job_id

    def claim_next(self, pipeline: Pipeline) -> Optional[Job]:
        """Atomically mark the oldest queued job for this pipeline as running."""
        now = datetime.utcnow().isoformat()
        with self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute(
                "SELECT id FROM jobs WHERE status = ? AND pipeline = ? "
                "ORDER BY created_at ASC LIMIT 1",
                (JobStatus.QUEUED.value, pipeline.value),
            ).fetchone()
            if row is None:
                c.execute("COMMIT")
                return None
            job_id = row[0]
            c.execute(
                "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
                (JobStatus.RUNNING.value, now, job_id),
            )
            c.execute("COMMIT")
        return self.get(job_id)

    def get(self, job_id: str) -> Optional[Job]:
        with self._conn() as c:
            row = c.execute(
                "SELECT id, pipeline, status, payload_json, created_at, updated_at, "
                "progress_pct, current_step, result_json, error FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        return Job(
            id=row[0],
            pipeline=Pipeline(row[1]),
            status=JobStatus(row[2]),
            payload=json.loads(row[3]),
            created_at=datetime.fromisoformat(row[4]),
            updated_at=datetime.fromisoformat(row[5]),
            progress_pct=row[6],
            current_step=row[7],
            result_json=json.loads(row[8]) if row[8] else None,
            error=row[9],
        )

    def update_progress(self, job_id: str, pct: int, step: Optional[str] = None) -> None:
        now = datetime.utcnow().isoformat()
        with self._conn() as c:
            c.execute(
                "UPDATE jobs SET progress_pct = ?, current_step = ?, updated_at = ? WHERE id = ?",
                (pct, step, now, job_id),
            )

    def complete(self, job_id: str, result: dict) -> None:
        now = datetime.utcnow().isoformat()
        with self._conn() as c:
            c.execute(
                "UPDATE jobs SET status = ?, result_json = ?, progress_pct = 100, updated_at = ? "
                "WHERE id = ?",
                (JobStatus.COMPLETED.value, json.dumps(result), now, job_id),
            )

    def fail(self, job_id: str, error: str) -> None:
        now = datetime.utcnow().isoformat()
        with self._conn() as c:
            c.execute(
                "UPDATE jobs SET status = ?, error = ?, updated_at = ? WHERE id = ?",
                (JobStatus.FAILED.value, error, now, job_id),
            )

    def stream_updates(self, job_id: str, poll_interval_s: float = 1.0) -> Iterator[Job]:
        """Yield job snapshots until the job terminates. Used by SSE endpoint."""
        last_update = None
        while True:
            job = self.get(job_id)
            if job is None:
                return
            if job.updated_at != last_update:
                yield job
                last_update = job.updated_at
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                return
            time.sleep(poll_interval_s)


_default_queue: Optional[JobQueue] = None


def default_queue() -> JobQueue:
    global _default_queue
    if _default_queue is None:
        _default_queue = JobQueue()
    return _default_queue
