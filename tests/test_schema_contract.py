"""AC-10: schema is locked against drift — validator + Pydantic + docs agree."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _clean_env() -> dict:
    """Strip Neo4j connection env vars so the validator runs in doc-only mode.

    Tests should not depend on the dev's .env pointing at a migrated database;
    live-DB validation happens in Phase 0 gate in CI (with migrations run).
    """
    env = dict(os.environ)
    for k in ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD"):
        env.pop(k, None)
    return env


def test_schema_validator_doc_vs_pydantic_green():
    repo = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, str(repo / "backend" / "scripts" / "validate_graph_schema.py")],
        capture_output=True, text=True, timeout=60, cwd=repo, env=_clean_env(),
    )
    assert proc.returncode == 0, f"validator failed:\n{proc.stdout}\n{proc.stderr}"


def test_phase0_gate_doc_only_green():
    """Phase 0 gate (doc-only mode). Full gate with live DB runs post-migration."""
    repo = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, str(repo / "tests" / "phase0_gate.py")],
        capture_output=True, text=True, timeout=120, cwd=repo, env=_clean_env(),
    )
    assert proc.returncode == 0, f"phase 0 gate failed:\n{proc.stdout}\n{proc.stderr}"
