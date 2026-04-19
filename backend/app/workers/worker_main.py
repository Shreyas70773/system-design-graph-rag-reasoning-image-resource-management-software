"""Long-running worker loop.

Runs two background threads — one polling Pipeline A, one polling Pipeline B —
off the shared SQLite queue. Invoked either:
  - programmatically from the FastAPI startup (dev mode)
  - as a standalone script: `python -m app.workers.worker_main`
"""

from __future__ import annotations

import logging
import signal
import threading
import time
from typing import Optional

from app.config_v2 import get_v2_settings
from app.jobs import JobQueue, Pipeline, default_queue
from app.workers import pipeline_a_worker, pipeline_b_worker

logger = logging.getLogger(__name__)


class WorkerLoop:
    def __init__(self, queue: Optional[JobQueue] = None) -> None:
        self.queue = queue or default_queue()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        if self._threads:
            return
        cfg = get_v2_settings()
        for pipeline, handler in (
            (Pipeline.A_INGESTION, pipeline_a_worker.handle),
            (Pipeline.B_ASSEMBLY, pipeline_b_worker.handle),
        ):
            t = threading.Thread(
                target=self._loop,
                args=(pipeline, handler, cfg.worker_poll_interval_s),
                name=f"worker-{pipeline.value}",
                daemon=True,
            )
            t.start()
            self._threads.append(t)
        logger.info("Worker loop started: %d threads", len(self._threads))

    def stop(self) -> None:
        self._stop.set()
        for t in self._threads:
            t.join(timeout=5)
        self._threads = []

    def _loop(self, pipeline: Pipeline, handler, poll: float) -> None:
        processed = 0
        max_jobs = get_v2_settings().worker_max_jobs
        while not self._stop.is_set():
            job = self.queue.claim_next(pipeline)
            if job is None:
                time.sleep(poll)
                continue
            try:
                handler(job, self.queue)
            except Exception:  # noqa: BLE001
                logger.exception("Unhandled worker error in pipeline %s", pipeline.value)
            processed += 1
            if max_jobs and processed >= max_jobs:
                logger.info("Worker %s reached max_jobs=%d; stopping", pipeline.value, max_jobs)
                return


_global_loop: Optional[WorkerLoop] = None


def start_background_workers() -> WorkerLoop:
    global _global_loop
    if _global_loop is None:
        _global_loop = WorkerLoop()
        _global_loop.start()
    return _global_loop


def stop_background_workers() -> None:
    global _global_loop
    if _global_loop is not None:
        _global_loop.stop()
        _global_loop = None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    loop = WorkerLoop()
    loop.start()
    logger.info("worker_main: running. Ctrl+C to stop.")

    def _sigint(signum, frame):  # noqa: ARG001
        logger.info("Shutting down workers...")
        loop.stop()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _sigint)
    try:
        while True:
            time.sleep(60)
    except SystemExit:
        pass


if __name__ == "__main__":
    main()
