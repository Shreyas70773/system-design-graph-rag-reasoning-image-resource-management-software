"""
Phase 0 Acceptance Gate
=======================

Runs all the checks that must be green before Phase 1 begins.
Invoked from the command line or CI.

  python tests/phase0_gate.py

Exit 0 only if ALL of:
  - validate_graph_schema.py passes (doc/code; db check if NEO4J_URI set)
  - vram_profile_v2.py gate passes (skipped on machines without the
    verify scripts yet — logged as warning, not failure, for week-1)
  - app.schema_v2 imports cleanly and contains all expected models
  - backend.app.main imports without raising (V1 regression check)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> int:
    print(f"\n$ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=REPO_ROOT)
    return proc.returncode


def check_pydantic_imports() -> int:
    print("\n[check] importing app.schema_v2 ...")
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    try:
        from app import schema_v2  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        return 1
    expected = {
        "Brand", "Color", "Font", "Asset", "Mesh3D", "Material", "SemanticPart",
        "LightProbe", "CanonicalPose", "LogoAsset", "DecompositionRun",
        "Scene", "Placement", "Camera", "Light", "Terrain", "TextLayer", "Render",
        "Interaction", "PreferenceSignal", "NaturalLanguageCommand",
    }
    missing = expected - set(schema_v2.ALL_NODE_MODELS.keys())
    if missing:
        print(f"FAIL: schema_v2 missing models {missing}")
        return 1
    print(f"  OK ({len(schema_v2.ALL_NODE_MODELS)} models)")
    return 0


def check_v1_import() -> int:
    print("\n[check] importing app.main (V1 regression) ...")
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    try:
        from app import main  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        return 1
    print("  OK")
    return 0


def main() -> int:
    failures = 0

    # 1. Schema validator (doc ↔ pydantic at minimum)
    rc = run([sys.executable, "backend/scripts/validate_graph_schema.py"])
    if rc != 0:
        failures += 1

    # 2. Pydantic imports
    if check_pydantic_imports() != 0:
        failures += 1

    # 3. V1 regression
    if check_v1_import() != 0:
        failures += 1

    # 4. VRAM profile (only if verify scripts exist; otherwise informational)
    verify_dir = REPO_ROOT / "backend" / "scripts" / "verify"
    has_verifies = verify_dir.exists() and any(verify_dir.glob("verify_*.py"))
    if has_verifies:
        rc = run([sys.executable, "backend/scripts/vram_profile_v2.py", "--gate"])
        if rc != 0:
            failures += 1
    else:
        print("\n[check] vram_profile_v2.py skipped — no verify scripts yet (expected on day 1)")

    print()
    if failures == 0:
        print("Phase 0 gate: PASS")
        return 0
    print(f"Phase 0 gate: FAIL ({failures} check(s) failed)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
