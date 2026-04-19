"""Pipeline A — Asset ingestion.

See docs/v2/PIPELINE_A_ASSET_INGESTION.md for the full spec.

Seven sequential steps, each an isolated Python module under
``backend.app.ingestion.steps``. The orchestrator enforces VRAM-aware
sequencing: at most one heavy model in VRAM at any time.
"""

__all__: list[str] = []
