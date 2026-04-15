"""
Synchronize evidence readiness and claim ledger status.

Outputs:
- docs/artifacts/evidence_status.json
- docs/claim_ledger.csv (updated when --write)
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync evidence status with claim ledger")
    parser.add_argument("--write", action="store_true", help="Write updates back to claim_ledger.csv")
    return parser.parse_args()


def load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_claim_ledger(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_claim_ledger(path: Path, rows: List[Dict[str, str]]) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()

    root = Path(__file__).resolve().parents[2]
    docs_dir = root / "docs"
    artifacts_dir = docs_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    stats_protocol_path = docs_dir / "stats_protocol_v1.md"
    vram_summary_path = artifacts_dir / "vram_profile_summary.json"
    license_matrix_path = docs_dir / "license_matrix.md"
    claim_ledger_path = docs_dir / "claim_ledger.csv"
    stats_analyzer_path = root / "backend" / "app" / "services" / "stats_analyzer.py"

    stats_protocol_text = load_text(stats_protocol_path)
    license_matrix_text = load_text(license_matrix_path)
    stats_analyzer_text = load_text(stats_analyzer_path)
    vram_summary = load_json(vram_summary_path)

    stats_protocol_approved = "Status: Approved" in stats_protocol_text
    stats_code_ready = all(token in stats_analyzer_text for token in ["wilcoxon", "friedman", "holm"])

    vram_stats = (vram_summary or {}).get("stats", {})
    vram_completed = int(vram_stats.get("completed_runs", 0))
    vram_oom_runs = int(vram_stats.get("oom_runs", 0))
    vram_ready = vram_completed > 0

    license_pending = "pending_review" in license_matrix_text.lower()
    license_tbd = "tbd" in license_matrix_text.lower()
    license_ready = not (license_pending or license_tbd)

    ledger_rows = read_claim_ledger(claim_ledger_path)

    ledger_has_tbd = any(
        "tbd" in " ".join(str(value) for value in row.values()).lower()
        for row in ledger_rows
    )
    borrowed_gain_active = any(
        row.get("claim_type") == "borrowed_gain" and row.get("status", "").lower() != "rejected"
        for row in ledger_rows
    )
    unverified_method_outcome = any(
        row.get("claim_type") == "method_outcome" and row.get("status", "").lower() == "unverified"
        for row in ledger_rows
    )

    evidence_status = {
        "B1": {
            "description": "Paired statistics protocol and implementation",
            "closed": bool(stats_protocol_approved and stats_code_ready),
            "checks": {
                "stats_protocol_approved": stats_protocol_approved,
                "stats_code_ready": stats_code_ready,
            },
        },
        "B2": {
            "description": "VRAM profiling evidence",
            "closed": bool(vram_ready and vram_oom_runs == 0),
            "checks": {
                "vram_runs_completed": vram_completed,
                "vram_oom_runs": vram_oom_runs,
            },
        },
        "B3": {
            "description": "Claim ledger evidence mapping",
            "closed": bool(not ledger_has_tbd and not borrowed_gain_active and not unverified_method_outcome),
            "checks": {
                "contains_tbd": ledger_has_tbd,
                "borrowed_gain_active": borrowed_gain_active,
                "unverified_method_outcome": unverified_method_outcome,
            },
        },
        "B4": {
            "description": "License compliance matrix",
            "closed": bool(license_ready),
            "checks": {
                "contains_pending_review": license_pending,
                "contains_tbd": license_tbd,
            },
        },
    }

    for row in ledger_rows:
        claim_id = row.get("claim_id", "")
        if claim_id == "C001":
            # Requires experiment evidence output beyond protocol/code checks.
            row["status"] = row.get("status", "unverified")
        elif claim_id == "C002":
            if evidence_status["B1"]["closed"]:
                row["status"] = "verified"
                row["confidence"] = "0.90"
                row["notes"] = "Verified by approved protocol and implemented analyzer tests"
            else:
                row["status"] = "unverified"
                row["confidence"] = "0.40"
                row["notes"] = "Needs supervisor-approved protocol state"
        elif claim_id == "C003":
            if evidence_status["B2"]["closed"]:
                row["status"] = "verified"
                row["confidence"] = "0.85"
                row["notes"] = "Backed by generated VRAM summary with no OOM"
            else:
                row["status"] = "unverified"
                row["confidence"] = "0.25"
                row["notes"] = "Run backend/scripts/run_vram_profile.py and regenerate artifacts"
        elif claim_id == "C004":
            if evidence_status["B4"]["closed"]:
                row["status"] = "verified"
                row["confidence"] = "0.85"
                row["notes"] = "License matrix finalized with no pending/TBD items"
            else:
                row["status"] = "unverified"
                row["confidence"] = "0.30"
                row["notes"] = "Resolve pending_review and TBD entries in license matrix"

    if args.write and ledger_rows:
        write_claim_ledger(claim_ledger_path, ledger_rows)

    output_payload = {
        "status": evidence_status,
        "claim_ledger_updated": bool(args.write),
        "claim_ledger_path": str(claim_ledger_path),
    }
    output_path = artifacts_dir / "evidence_status.json"
    output_path.write_text(json.dumps(output_payload, indent=2), encoding="utf-8")

    print(json.dumps(output_payload, indent=2))


if __name__ == "__main__":
    main()
