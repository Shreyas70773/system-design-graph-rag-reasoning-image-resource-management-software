"""
Check project dependency compliance against docs/license_policy.json.

Outputs:
- docs/artifacts/license_compliance_report.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="License compliance checker")
    parser.add_argument("--scope", choices=["research", "deployment"], default="research")
    parser.add_argument("--policy", default="../docs/license_policy.json")
    parser.add_argument("--requirements", default="requirements.txt")
    parser.add_argument("--fail-on-unknown", action="store_true")
    return parser.parse_args()


def normalize_package_name(raw: str) -> str:
    token = raw.strip().lower()
    if "==" in token:
        token = token.split("==", 1)[0]
    if ">=" in token:
        token = token.split(">=", 1)[0]
    if "[" in token:
        token = token.split("[", 1)[0]
    return token.strip()


def load_requirements(path: Path) -> List[str]:
    packages: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        packages.append(normalize_package_name(stripped))
    return packages


def main() -> None:
    args = parse_args()
    backend_dir = Path(__file__).resolve().parents[1]
    root = backend_dir.parent

    policy_path = (backend_dir / args.policy).resolve()
    requirements_path = (backend_dir / args.requirements).resolve()
    artifacts_path = (root / "docs" / "artifacts" / "license_compliance_report.json").resolve()
    artifacts_path.parent.mkdir(parents=True, exist_ok=True)

    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    requirements = load_requirements(requirements_path)

    python_policy: Dict[str, Dict[str, Any]] = policy.get("python_dependencies", {})

    violations: List[Dict[str, Any]] = []
    unknown: List[str] = []
    checked: List[Dict[str, Any]] = []

    for package in requirements:
        entry = python_policy.get(package)
        if not entry:
            unknown.append(package)
            continue

        decision = entry.get("decision", "manual_review_required")
        allowed_scopes = entry.get("allowed_scopes", [])
        allowed = decision == "allowed" and args.scope in allowed_scopes

        checked.append({
            "package": package,
            "decision": decision,
            "allowed_scopes": allowed_scopes,
            "scope": args.scope,
            "allowed": allowed,
        })

        if not allowed:
            violations.append({
                "package": package,
                "decision": decision,
                "allowed_scopes": allowed_scopes,
                "scope": args.scope,
            })

    pass_unknown = not args.fail_on_unknown or not unknown
    passed = len(violations) == 0 and pass_unknown

    report = {
        "scope": args.scope,
        "policy_path": str(policy_path),
        "requirements_path": str(requirements_path),
        "passed": passed,
        "violations": violations,
        "unknown_dependencies": unknown,
        "checked": checked,
    }

    artifacts_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
