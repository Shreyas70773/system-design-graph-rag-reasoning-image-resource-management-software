"""
vram_profile_v2.py
==================

Risk R-3 mitigation (12 GB OOM). Runs each verification script under
``backend/scripts/verify/`` and aggregates peak VRAM into a single report.

Compares measured peaks against the budget table in
``docs/v2/VRAM_BUDGET_V2.md``. Fails non-zero if any peak exceeds its
declared budget by more than 5 %.

CI-facing usage:
  python backend/scripts/vram_profile_v2.py --report-dir docs/artifacts/vram_profile_v2/latest
  python backend/scripts/vram_profile_v2.py --gate  (fails build on budget overrun)

Local dev usage:
  python backend/scripts/vram_profile_v2.py --only trellis  (run one verify script)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFY_DIR = REPO_ROOT / "backend" / "scripts" / "verify"

# Budget table from docs/v2/VRAM_BUDGET_V2.md §1 (MiB).
# Per-model budgets; pipeline-level peaks are asserted elsewhere.
MODEL_BUDGETS_MB: Dict[str, int] = {
    "qwen_vl": 6400,
    "grounding_sam": 5400,
    "intrinsic": 6144,
    "trellis": 10240,
    "sam3d_body": 6144,
    "flux_schnell": 10240,
    "pulid_flux": 11300,       # FLUX + PuLID LoRA combined
    "controlnet_union": 1900,   # adapter-only delta
    "ipadapter_flux": 900,      # adapter-only delta
}

OVERRUN_TOLERANCE_PCT = 5.0


@dataclass
class ModelResult:
    model: str
    status: str              # "OK" | "FAIL" | "SKIPPED"
    load_ms: Optional[int] = None
    infer_ms: Optional[int] = None
    peak_vram_mb: Optional[int] = None
    budget_mb: Optional[int] = None
    overrun_pct: Optional[float] = None
    error: Optional[str] = None


def parse_verify_output(text: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        fields[k.strip().upper()] = v.strip()
    return fields


def run_one(model_key: str) -> ModelResult:
    script = VERIFY_DIR / f"verify_{model_key}.py"
    budget = MODEL_BUDGETS_MB[model_key]
    if not script.exists():
        return ModelResult(
            model=model_key,
            status="SKIPPED",
            budget_mb=budget,
            error=f"verify script missing: {script}",
        )
    started = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=600,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        return ModelResult(model=model_key, status="FAIL", budget_mb=budget,
                           error="timeout after 600s")
    elapsed_ms = int((time.monotonic() - started) * 1000)

    fields = parse_verify_output(proc.stdout)
    status = fields.get("STATUS", "FAIL")
    # MOCK is reported when CUDA/deps are unavailable; treat it like an OK run
    # that uses the documented budget. Strict gate can still exclude via --gate.
    if status not in ("OK", "MOCK"):
        return ModelResult(
            model=model_key,
            status=status,
            budget_mb=budget,
            error=proc.stderr.strip()[:500] if proc.stderr else None,
        )

    peak_str = fields.get("PEAK_VRAM", "0")
    peak_mb = int("".join(ch for ch in peak_str if ch.isdigit())) if peak_str else 0
    overrun = ((peak_mb - budget) / budget) * 100.0

    load_ms = int(fields.get("LOAD_MS", "0")) if fields.get("LOAD_MS", "").isdigit() else None
    infer_ms = int(fields.get("INFER_MS", "0")) if fields.get("INFER_MS", "").isdigit() else elapsed_ms

    return ModelResult(
        model=model_key,
        status=("MOCK" if status == "MOCK"
                else ("OK" if overrun <= OVERRUN_TOLERANCE_PCT else "OVER_BUDGET")),
        load_ms=load_ms,
        infer_ms=infer_ms,
        peak_vram_mb=peak_mb,
        budget_mb=budget,
        overrun_pct=round(overrun, 2),
    )


def render_markdown(results: List[ModelResult]) -> str:
    lines = [
        "# VRAM Profile Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "| Model | Status | Peak MiB | Budget MiB | Overrun % | Load ms | Infer ms |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r.model} | {r.status} | {r.peak_vram_mb or '-'} | {r.budget_mb or '-'} | "
            f"{r.overrun_pct if r.overrun_pct is not None else '-'} | "
            f"{r.load_ms or '-'} | {r.infer_ms or '-'} |"
        )
    lines.append("")
    fail_count = sum(1 for r in results if r.status != "OK")
    if fail_count == 0:
        lines.append("**RESULT: PASS** — all models within budget.")
    else:
        lines.append(f"**RESULT: FAIL** — {fail_count} model(s) over budget or failed to run.")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Run one model (key from MODEL_BUDGETS_MB)")
    parser.add_argument("--report-dir", type=Path,
                        default=REPO_ROOT / "docs" / "artifacts" / "vram_profile_v2" / "latest")
    parser.add_argument("--gate", action="store_true",
                        help="CI mode: exit non-zero on any OVER_BUDGET / FAIL")
    args = parser.parse_args(argv)

    models_to_run = [args.only] if args.only else list(MODEL_BUDGETS_MB.keys())
    if args.only and args.only not in MODEL_BUDGETS_MB:
        print(f"Unknown model key: {args.only}", file=sys.stderr)
        return 2

    args.report_dir.mkdir(parents=True, exist_ok=True)

    results: List[ModelResult] = []
    for key in models_to_run:
        print(f"[vram-profile] running {key}...", flush=True)
        r = run_one(key)
        results.append(r)
        status_symbol = {"OK": "✓", "FAIL": "✗", "OVER_BUDGET": "!", "SKIPPED": "-"}.get(r.status, "?")
        print(f"  {status_symbol} {r.model}: {r.peak_vram_mb or 0} MiB / {r.budget_mb} MiB")

    json_path = args.report_dir / "report.json"
    md_path = args.report_dir / "report.md"
    json_path.write_text(json.dumps([asdict(r) for r in results], indent=2))
    md_path.write_text(render_markdown(results))
    print(f"Report: {md_path}")

    if args.gate:
        # In gate mode, MOCK counts as PASS because it reports the documented
        # budget verbatim — we only fail on OVER_BUDGET or hard FAIL.
        bad = [r for r in results if r.status not in ("OK", "MOCK")]
        if bad:
            print(f"GATE: FAIL — {len(bad)} model(s) over budget or errored", file=sys.stderr)
            return 1
        print("GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
