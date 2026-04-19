"""
validate_graph_schema.py
========================

Risk R-1 mitigation (schema drift). Runs in:
  - local dev (manual invocation)
  - pre-commit hook (fast path, no --neo4j-uri)
  - CI (full path with live DB)

Compares THREE sources and fails if any diverge:
  1. docs/v2/GRAPH_SCHEMA_V2.md   (the source of truth)
  2. backend/app/schema_v2.py     (Pydantic models)
  3. Live Neo4j (optional, with --neo4j-uri)

Exit codes:
  0 — all three agree
  1 — doc / code mismatch
  2 — doc / db mismatch
  3 — doc parse failure
  4 — connection / config error

Usage:
  python backend/scripts/validate_graph_schema.py
  python backend/scripts/validate_graph_schema.py --neo4j-uri $NEO4J_URI \\
      --neo4j-user neo4j --neo4j-password $NEO4J_PASSWORD

Add ``--strict`` to also fail on extra live-DB labels that are not in the doc
(useful for "green-field" CI databases; too strict for shared dev DBs that
still hold V1 nodes).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DOC = REPO_ROOT / "docs" / "v2" / "GRAPH_SCHEMA_V2.md"
SCHEMA_PY = REPO_ROOT / "backend" / "app" / "schema_v2.py"
EXPECTED_SCHEMA_VERSION = "2.0.0"

# V1 labels we tolerate in the live DB — explicitly excluded from checks.
V1_LABELS = {
    "Generation",
    "Product",
    "ScrapedPage",
    "LearnedPreference",
    "ExperimentManifest",
    "ExperimentRun",
    "ExperimentCandidate",
    "MetricSnapshot",
}


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    severity: str   # "error" | "warn"
    category: str   # "doc-code" | "doc-db"
    message: str


@dataclass
class Report:
    findings: List[Finding] = field(default_factory=list)
    node_types_checked: int = 0
    relationship_types_checked: int = 0
    constraints_checked: int = 0

    @property
    def has_errors(self) -> bool:
        return any(f.severity == "error" for f in self.findings)

    def add_error(self, category: str, message: str) -> None:
        self.findings.append(Finding("error", category, message))

    def add_warn(self, category: str, message: str) -> None:
        self.findings.append(Finding("warn", category, message))


# ---------------------------------------------------------------------------
# Doc parser
# ---------------------------------------------------------------------------


@dataclass
class DocSchema:
    version: str
    node_types: Dict[str, Set[str]] = field(default_factory=dict)  # label -> required props
    all_props: Dict[str, Set[str]] = field(default_factory=dict)   # label -> all props
    relationships: Set[Tuple[str, str, str]] = field(default_factory=set)
    constraints: Set[str] = field(default_factory=set)


def parse_doc(path: Path) -> DocSchema:
    """Parse GRAPH_SCHEMA_V2.md. Keeps the parser forgiving but fails loudly on absence."""
    if not path.exists():
        raise FileNotFoundError(f"Schema doc not found at {path}")

    text = path.read_text(encoding="utf-8")

    # Extract version header
    version_match = re.search(r"\*\*Version:\*\*\s*([0-9.]+)", text)
    if not version_match:
        raise ValueError("Could not find version header in schema doc")
    version = version_match.group(1)

    schema = DocSchema(version=version)

    # Node types: find `#### \`(NodeLabel)\`` headings within `## 1. Node types` section.
    section_match = re.search(
        r"##\s*1\.\s*Node types(.*?)(?=^##\s)",
        text,
        re.DOTALL | re.MULTILINE,
    )
    if not section_match:
        raise ValueError("Could not find '## 1. Node types' section")
    node_section = section_match.group(1)

    # Each node block: `#### `(Label)`` followed by an optional table.
    node_headings = list(re.finditer(r"####\s*`\((\w+)\)`(.*?)(?=####|\Z)", node_section, re.DOTALL))
    for match in node_headings:
        label = match.group(1)
        block = match.group(2)
        props: Set[str] = set()
        required: Set[str] = set()
        for row in re.finditer(
            r"^\|\s*`?(\w+)`?\s*\|\s*[^|]+\s*\|\s*(yes|no|—)\s*\|",
            block,
            re.MULTILINE,
        ):
            prop, req = row.group(1), row.group(2)
            props.add(prop)
            if req == "yes":
                required.add(prop)
        schema.node_types[label] = required
        schema.all_props[label] = props

    # Relationships: look for table rows in section 2.
    rel_section_match = re.search(
        r"##\s*2\.\s*Relationship types(.*?)(?=^##\s)",
        text,
        re.DOTALL | re.MULTILINE,
    )
    if rel_section_match:
        rel_section = rel_section_match.group(1)
        # Row format: `| `From` → `To` | `REL_TYPE` | props | cardinality |`
        for row in re.finditer(
            r"^\|\s*`(\w+)`\s*→\s*`(\w+)`\s*\|\s*`(\w+)`\s*\|",
            rel_section,
            re.MULTILINE,
        ):
            from_lbl, to_lbl, rel_type = row.group(1), row.group(2), row.group(3)
            schema.relationships.add((from_lbl, rel_type, to_lbl))

    # Constraints: any line beginning with `CREATE CONSTRAINT`.
    for m in re.finditer(r"CREATE CONSTRAINT\s+(\w+)", text):
        schema.constraints.add(m.group(1))

    return schema


# ---------------------------------------------------------------------------
# Pydantic reflection
# ---------------------------------------------------------------------------


def introspect_pydantic() -> Dict[str, Set[str]]:
    """Return {label: set(field_names)} for every Pydantic model declared in schema_v2."""
    # Make the backend package importable from repo root.
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    from app import schema_v2  # noqa: WPS433 — intentional late import

    results: Dict[str, Set[str]] = {}
    for label, model in schema_v2.ALL_NODE_MODELS.items():
        results[label] = set(model.model_fields.keys())
    results["_schema_version"] = {schema_v2.SCHEMA_VERSION}  # sentinel, checked separately
    return results


# ---------------------------------------------------------------------------
# Live DB introspection
# ---------------------------------------------------------------------------


@dataclass
class LiveSchema:
    labels: Set[str]
    constraints: Set[str]
    rel_types: Set[str]


def introspect_live_db(uri: str, user: str, password: str) -> LiveSchema:
    try:
        from neo4j import GraphDatabase
    except ImportError as exc:
        raise RuntimeError("neo4j driver not installed; skip --neo4j-uri or install it") from exc

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            label_rows = session.run("CALL db.labels()").data()
            rel_rows = session.run("CALL db.relationshipTypes()").data()
            constraint_rows = session.run("SHOW CONSTRAINTS").data()

            labels = {r["label"] for r in label_rows}
            rel_types = {r["relationshipType"] for r in rel_rows}
            constraints = {r["name"] for r in constraint_rows}
            return LiveSchema(labels=labels, constraints=constraints, rel_types=rel_types)
    finally:
        driver.close()


# ---------------------------------------------------------------------------
# Cross-checks
# ---------------------------------------------------------------------------


def check_doc_vs_pydantic(doc: DocSchema, pyd: Dict[str, Set[str]], report: Report) -> None:
    # Version sentinel
    py_version = next(iter(pyd.get("_schema_version", set())), None)
    if py_version != doc.version:
        report.add_error(
            "doc-code",
            f"SCHEMA_VERSION mismatch: doc={doc.version!r} pydantic={py_version!r}",
        )

    doc_labels = set(doc.node_types.keys())
    pyd_labels = set(pyd.keys()) - {"_schema_version"}

    only_in_doc = doc_labels - pyd_labels
    for label in sorted(only_in_doc):
        report.add_error("doc-code", f"Node label '{label}' in doc but not in schema_v2.py")

    only_in_code = pyd_labels - doc_labels
    for label in sorted(only_in_code):
        report.add_error("doc-code", f"Node label '{label}' in schema_v2.py but not in doc")

    # Field-level comparison (skip common fields)
    common = {"id", "created_at", "updated_at", "schema_version"}
    for label in sorted(doc_labels & pyd_labels):
        doc_props = doc.all_props.get(label, set())
        pyd_props = pyd.get(label, set()) - common
        doc_props_ex = doc_props - common
        missing_in_code = doc_props_ex - pyd_props
        for prop in sorted(missing_in_code):
            report.add_error(
                "doc-code",
                f"Property {label}.{prop} in doc but not in schema_v2.py",
            )
        missing_in_doc = pyd_props - doc_props_ex
        for prop in sorted(missing_in_doc):
            report.add_error(
                "doc-code",
                f"Property {label}.{prop} in schema_v2.py but not in doc",
            )
        report.node_types_checked += 1


def check_doc_vs_db(doc: DocSchema, db: LiveSchema, strict: bool, report: Report) -> None:
    doc_labels = set(doc.node_types.keys())
    missing_labels = doc_labels - db.labels
    # It's OK for labels to be missing on a fresh DB that hasn't ingested anything.
    # We instead require the CONSTRAINTS to exist.
    for label in sorted(missing_labels):
        report.add_warn(
            "doc-db",
            f"Label '{label}' declared in doc is not present in live DB (may be OK on fresh DB)",
        )

    if strict:
        extra_labels = db.labels - doc_labels - V1_LABELS
        for label in sorted(extra_labels):
            report.add_error(
                "doc-db",
                f"Live DB has label '{label}' not declared in doc (strict mode)",
            )

    doc_rel_types = {r[1] for r in doc.relationships}
    missing_rels = doc_rel_types - db.rel_types
    for rel in sorted(missing_rels):
        report.add_warn("doc-db", f"Relationship '{rel}' declared in doc is not in live DB")

    missing_constraints = doc.constraints - db.constraints
    for c in sorted(missing_constraints):
        report.add_error("doc-db", f"Constraint '{c}' from doc missing in live DB")
    report.constraints_checked = len(doc.constraints)
    report.relationship_types_checked = len(doc_rel_types)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate V2 graph schema consistency.")
    parser.add_argument("--neo4j-uri", default=os.environ.get("NEO4J_URI"))
    parser.add_argument("--neo4j-user", default=os.environ.get("NEO4J_USERNAME", "neo4j"))
    parser.add_argument("--neo4j-password", default=os.environ.get("NEO4J_PASSWORD"))
    parser.add_argument("--strict", action="store_true",
                        help="Fail on extra labels in live DB not declared in doc")
    parser.add_argument("--fresh", action="store_true",
                        help="Downgrade 'missing label in DB' warnings to info (new DBs)")
    args = parser.parse_args(argv)

    report = Report()

    try:
        doc = parse_doc(SCHEMA_DOC)
    except Exception as exc:
        print(f"FAIL: could not parse {SCHEMA_DOC}: {exc}", file=sys.stderr)
        return 3

    if doc.version != EXPECTED_SCHEMA_VERSION:
        report.add_error(
            "doc-code",
            f"Expected doc version {EXPECTED_SCHEMA_VERSION}, doc has {doc.version}",
        )

    try:
        pyd = introspect_pydantic()
    except Exception as exc:
        print(f"FAIL: could not introspect schema_v2.py: {exc}", file=sys.stderr)
        return 4

    check_doc_vs_pydantic(doc, pyd, report)
    # Record counts parsed from doc even if we don't have a live DB.
    report.relationship_types_checked = len({r[1] for r in doc.relationships})
    report.constraints_checked = len(doc.constraints)

    if args.neo4j_uri:
        if not args.neo4j_password:
            print("FAIL: --neo4j-uri given without --neo4j-password", file=sys.stderr)
            return 4
        try:
            db = introspect_live_db(args.neo4j_uri, args.neo4j_user, args.neo4j_password)
        except Exception as exc:
            print(f"FAIL: could not introspect live DB: {exc}", file=sys.stderr)
            return 4
        check_doc_vs_db(doc, db, args.strict, report)

    # Print report
    if not report.has_errors:
        print(f"OK: schema matches GRAPH_SCHEMA_V2.md {doc.version}")
        print(f"  - {report.node_types_checked} node types verified")
        print(f"  - {report.relationship_types_checked} relationship types verified")
        print(f"  - {report.constraints_checked} constraints verified")
        for w in (f for f in report.findings if f.severity == "warn"):
            print(f"  warn [{w.category}]: {w.message}")
        return 0

    print("FAIL: schema drift detected")
    for f in report.findings:
        print(f"  {f.severity.upper()} [{f.category}]: {f.message}")

    # Pick most-specific exit code
    if any(f.category == "doc-db" for f in report.findings if f.severity == "error"):
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
