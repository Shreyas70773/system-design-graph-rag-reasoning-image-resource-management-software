"""Apply the capstone V3 Neo4j constraints."""

from __future__ import annotations

from pathlib import Path

from app.database.neo4j_client import neo4j_client


def main() -> int:
    if not neo4j_client.verify_connection():
        print("Neo4j unavailable. Check backend/.env before running migration.")
        return 1

    schema_path = Path(__file__).resolve().parents[1] / "app" / "database" / "capstone_schema_v3.cypher"
    statements = [stmt.strip() for stmt in schema_path.read_text(encoding="utf-8").split(";") if stmt.strip()]
    for statement in statements:
        neo4j_client.execute_query(statement)
        print(f"[OK] {statement.splitlines()[0]}")

    print("Capstone V3 schema ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
