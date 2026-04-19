"""V2 Neo4j client. Reuses V1's driver; adds V2 schema-scoped operations.

Every write method is named after its pipeline owner to enforce the
write-ownership matrix in GRAPH_SCHEMA_V2.md §4.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.database.neo4j_client import neo4j_client
from app.schema_v2 import SCHEMA_VERSION


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _gen_id() -> str:
    return str(uuid.uuid4())


def _node_common(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now = _now_iso()
    common = {
        "id": _gen_id(),
        "created_at": now,
        "updated_at": now,
        "schema_version": SCHEMA_VERSION,
    }
    if extra:
        common.update(extra)
    return common


def _serialize_props(props: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten dict / list-of-dict props to JSON strings for Neo4j compatibility."""
    out: Dict[str, Any] = {}
    for k, v in props.items():
        if isinstance(v, dict):
            out[k] = json.dumps(v)
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            out[k] = json.dumps(v)
        else:
            out[k] = v
    return out


class Neo4jV2:
    """V2-scoped operations. Prefers V1's connection; silently no-ops if unavailable."""

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        return neo4j_client.driver is not None

    def run(self, query: str, **params) -> List[Dict[str, Any]]:
        if not self.available:
            return []
        with neo4j_client.driver.session() as s:
            result = s.run(query, **params)
            return [r.data() for r in result]

    def run_write(self, query: str, **params) -> List[Dict[str, Any]]:
        return self.run(query, **params)

    # ------------------------------------------------------------------
    # Brand lookup (shared with V1)
    # ------------------------------------------------------------------

    def get_brand_v2(self, brand_id: str) -> Optional[Dict[str, Any]]:
        rows = self.run(
            "MATCH (b:Brand {id: $id}) WHERE b.schema_version = '2.0' OR b.schema_version IS NULL "
            "RETURN b",
            id=brand_id,
        )
        return rows[0]["b"] if rows else None

    def upgrade_brand_to_v2(self, brand_id: str) -> None:
        self.run_write(
            "MATCH (b:Brand {id: $id}) SET b.schema_version = '2.0', b.updated_at = $ts",
            id=brand_id, ts=_now_iso(),
        )

    # ------------------------------------------------------------------
    # Pipeline A writes — asset decomposition cluster
    # ------------------------------------------------------------------

    def pipeline_a_create_asset(
        self,
        *,
        brand_id: str,
        asset_type: str,
        source_url: str,
    ) -> str:
        asset = _node_common({
            "asset_type": asset_type,
            "source_url": source_url,
            "ingestion_status": "pending",
        })
        self.run_write(
            "MATCH (b:Brand {id: $bid}) "
            "CREATE (a:Asset $props) "
            "CREATE (b)-[:HAS_ASSET {created_at: $ts}]->(a)",
            bid=brand_id, props=asset, ts=_now_iso(),
        )
        return asset["id"]

    def pipeline_a_update_asset_status(self, asset_id: str, status: str, **extra) -> None:
        set_clauses = ["a.ingestion_status = $status", "a.updated_at = $ts"]
        params: Dict[str, Any] = {"id": asset_id, "status": status, "ts": _now_iso()}
        for k, v in extra.items():
            set_clauses.append(f"a.{k} = ${k}")
            params[k] = v
        self.run_write(
            f"MATCH (a:Asset {{id: $id}}) SET {', '.join(set_clauses)}",
            **params,
        )

    def pipeline_a_set_vlm_description(self, asset_id: str, description: str, embedding: Optional[List[float]]) -> None:
        params: Dict[str, Any] = {"id": asset_id, "desc": description, "ts": _now_iso()}
        if embedding is not None:
            params["emb"] = embedding
            self.run_write(
                "MATCH (a:Asset {id: $id}) SET a.vlm_description = $desc, "
                "a.clip_embedding = $emb, a.updated_at = $ts",
                **params,
            )
        else:
            self.run_write(
                "MATCH (a:Asset {id: $id}) SET a.vlm_description = $desc, a.updated_at = $ts",
                **params,
            )

    def pipeline_a_attach_mesh(self, asset_id: str, mesh: Dict[str, Any]) -> str:
        node = _node_common(mesh)
        self.run_write(
            "MATCH (a:Asset {id: $aid}) "
            "CREATE (m:Mesh3D $props) "
            "CREATE (a)-[:HAS_GEOMETRY {created_at: $ts}]->(m)",
            aid=asset_id, props=_serialize_props(node), ts=_now_iso(),
        )
        return node["id"]

    def pipeline_a_attach_material(self, asset_id: str, material: Dict[str, Any], part_name: Optional[str] = None) -> str:
        node = _node_common(material)
        self.run_write(
            "MATCH (a:Asset {id: $aid}) "
            "CREATE (m:Material $props) "
            "CREATE (a)-[:HAS_MATERIAL {created_at: $ts, part_name: $part}]->(m)",
            aid=asset_id, props=_serialize_props(node), ts=_now_iso(), part=part_name,
        )
        return node["id"]

    def pipeline_a_attach_part(self, asset_id: str, part: Dict[str, Any]) -> str:
        node = _node_common(part)
        self.run_write(
            "MATCH (a:Asset {id: $aid}) "
            "CREATE (p:SemanticPart $props) "
            "CREATE (a)-[:HAS_PART {created_at: $ts}]->(p)",
            aid=asset_id, props=_serialize_props(node), ts=_now_iso(),
        )
        return node["id"]

    def pipeline_a_attach_light_probe(self, asset_id: str, probe: Dict[str, Any]) -> str:
        node = _node_common(probe)
        self.run_write(
            "MATCH (a:Asset {id: $aid}) "
            "CREATE (p:LightProbe $props) "
            "CREATE (a)-[:HAS_LIGHT_PROBE {created_at: $ts}]->(p)",
            aid=asset_id, props=_serialize_props(node), ts=_now_iso(),
        )
        return node["id"]

    def pipeline_a_attach_canonical_pose(self, asset_id: str, pose: Dict[str, Any]) -> str:
        node = _node_common(pose)
        self.run_write(
            "MATCH (a:Asset {id: $aid}) "
            "CREATE (p:CanonicalPose $props) "
            "CREATE (a)-[:HAS_CANONICAL_POSE {created_at: $ts}]->(p)",
            aid=asset_id, props=_serialize_props(node), ts=_now_iso(),
        )
        return node["id"]

    def pipeline_a_record_decomposition_run(self, asset_id: str, run: Dict[str, Any]) -> str:
        node = _node_common(run)
        self.run_write(
            "MATCH (a:Asset {id: $aid}) "
            "CREATE (r:DecompositionRun $props) "
            "CREATE (a)-[:DECOMPOSED_BY {created_at: $ts}]->(r)",
            aid=asset_id, props=_serialize_props(node), ts=_now_iso(),
        )
        return node["id"]

    def get_asset_full(self, asset_id: str) -> Dict[str, Any]:
        rows = self.run(
            """
            MATCH (a:Asset {id: $id})
            OPTIONAL MATCH (a)-[:HAS_GEOMETRY]->(m:Mesh3D)
            OPTIONAL MATCH (a)-[:HAS_MATERIAL]->(mat:Material)
            OPTIONAL MATCH (a)-[:HAS_PART]->(p:SemanticPart)
            OPTIONAL MATCH (a)-[:HAS_LIGHT_PROBE]->(lp:LightProbe)
            OPTIONAL MATCH (a)-[:HAS_CANONICAL_POSE]->(cp:CanonicalPose)
            OPTIONAL MATCH (a)-[:DECOMPOSED_BY]->(r:DecompositionRun)
            RETURN a, collect(DISTINCT m) AS meshes, collect(DISTINCT mat) AS materials,
                   collect(DISTINCT p) AS parts, lp AS light_probe, cp AS canonical_pose,
                   collect(DISTINCT r) AS decompositions
            """,
            id=asset_id,
        )
        if not rows:
            return {"asset": None}
        r = rows[0]
        return {
            "asset": r["a"],
            "geometry": r["meshes"],
            "materials": r["materials"],
            "parts": r["parts"],
            "light_probe": r["light_probe"],
            "canonical_pose": r["canonical_pose"],
            "decomposition_runs": r["decompositions"],
        }

    # ------------------------------------------------------------------
    # Pipeline B writes — scene
    # ------------------------------------------------------------------

    def pipeline_b_create_scene(self, *, brand_id: str, intent_text: str, scene_graph: Dict[str, Any],
                                deployment_context: str) -> str:
        node = _node_common({
            "brand_id": brand_id,
            "intent_text": intent_text,
            "scene_graph_json": json.dumps(scene_graph),
            "deployment_context": deployment_context,
            "status": "draft",
        })
        self.run_write(
            "MATCH (b:Brand {id: $bid}) "
            "CREATE (s:Scene $props) "
            "CREATE (b)-[:OWNS_SCENE {created_at: $ts}]->(s)",
            bid=brand_id, props=node, ts=_now_iso(),
        )
        return node["id"]

    def pipeline_b_add_placement(self, scene_id: str, placement: Dict[str, Any]) -> str:
        node = _node_common(placement)
        self.run_write(
            "MATCH (s:Scene {id: $sid}), (a:Asset {id: $aid}) "
            "CREATE (p:Placement $props) "
            "CREATE (s)-[:HAS_PLACEMENT {created_at: $ts}]->(p) "
            "CREATE (p)-[:INSTANCE_OF {created_at: $ts}]->(a)",
            sid=scene_id, aid=placement["asset_id"], props=_serialize_props(node), ts=_now_iso(),
        )
        return node["id"]

    def pipeline_b_add_camera(self, scene_id: str, cam: Dict[str, Any]) -> str:
        node = _node_common(cam)
        self.run_write(
            "MATCH (s:Scene {id: $sid}) "
            "CREATE (c:Camera $props) "
            "CREATE (s)-[:HAS_CAMERA {created_at: $ts}]->(c)",
            sid=scene_id, props=_serialize_props(node), ts=_now_iso(),
        )
        return node["id"]

    def pipeline_b_add_light(self, scene_id: str, light: Dict[str, Any]) -> str:
        node = _node_common(light)
        self.run_write(
            "MATCH (s:Scene {id: $sid}) "
            "CREATE (l:Light $props) "
            "CREATE (s)-[:HAS_LIGHT {created_at: $ts}]->(l)",
            sid=scene_id, props=_serialize_props(node), ts=_now_iso(),
        )
        return node["id"]

    def pipeline_b_add_text_layer(self, scene_id: str, tl: Dict[str, Any]) -> str:
        node = _node_common(tl)
        self.run_write(
            "MATCH (s:Scene {id: $sid}) "
            "CREATE (t:TextLayer $props) "
            "CREATE (s)-[:HAS_TEXT_LAYER {created_at: $ts}]->(t)",
            sid=scene_id, props=_serialize_props(node), ts=_now_iso(),
        )
        return node["id"]

    def pipeline_b_add_render(self, scene_id: str, render: Dict[str, Any]) -> str:
        node = _node_common(render)
        self.run_write(
            "MATCH (s:Scene {id: $sid}) "
            "CREATE (r:Render $props) "
            "CREATE (s)-[:HAS_RENDER {created_at: $ts}]->(r)",
            sid=scene_id, props=_serialize_props(node), ts=_now_iso(),
        )
        return node["id"]

    def get_scene_full(self, scene_id: str) -> Dict[str, Any]:
        rows = self.run(
            """
            MATCH (s:Scene {id: $id})
            OPTIONAL MATCH (s)-[:HAS_PLACEMENT]->(p:Placement)
            OPTIONAL MATCH (s)-[:HAS_CAMERA]->(c:Camera)
            OPTIONAL MATCH (s)-[:HAS_LIGHT]->(l:Light)
            OPTIONAL MATCH (s)-[:HAS_TEXT_LAYER]->(t:TextLayer)
            OPTIONAL MATCH (s)-[:HAS_RENDER]->(r:Render)
            RETURN s, collect(DISTINCT p) AS placements, collect(DISTINCT c) AS cameras,
                   collect(DISTINCT l) AS lights, collect(DISTINCT t) AS text_layers,
                   collect(DISTINCT r) AS renders
            """,
            id=scene_id,
        )
        if not rows:
            return {"scene": None}
        r = rows[0]
        return {
            "scene": r["s"],
            "placements": r["placements"],
            "cameras": r["cameras"],
            "lights": r["lights"],
            "text_layers": r["text_layers"],
            "renders": r["renders"],
        }

    # ------------------------------------------------------------------
    # Pipeline C writes — interactions & preferences
    # ------------------------------------------------------------------

    def pipeline_c_record_interaction(self, interaction: Dict[str, Any], target_ids: Optional[List[str]] = None) -> str:
        node = _node_common(interaction)
        self.run_write(
            "CREATE (i:Interaction $props)",
            props=_serialize_props(node),
        )
        for tid in target_ids or []:
            self.run_write(
                "MATCH (i:Interaction {id: $iid}), (t {id: $tid}) "
                "CREATE (i)-[:MODIFIED {created_at: $ts}]->(t)",
                iid=node["id"], tid=tid, ts=_now_iso(),
            )
        return node["id"]

    def pipeline_c_record_nl_command(self, nl: Dict[str, Any], interaction_id: Optional[str] = None) -> str:
        node = _node_common(nl)
        self.run_write("CREATE (n:NaturalLanguageCommand $props)", props=_serialize_props(node))
        if interaction_id:
            self.run_write(
                "MATCH (i:Interaction {id: $iid}), (n:NaturalLanguageCommand {id: $nid}) "
                "CREATE (i)-[:RESOLVED_BY {created_at: $ts}]->(n)",
                iid=interaction_id, nid=node["id"], ts=_now_iso(),
            )
        return node["id"]

    def pipeline_c_write_preference_signal(self, brand_id: str, signal: Dict[str, Any]) -> str:
        node = _node_common(signal)
        self.run_write(
            "MATCH (b:Brand {id: $bid}) "
            "CREATE (p:PreferenceSignal $props) "
            "CREATE (b)-[:LEARNED_PREF {created_at: $ts}]->(p)",
            bid=brand_id, props=_serialize_props(node), ts=_now_iso(),
        )
        return node["id"]

    def get_active_preferences(self, brand_id: str, min_weight: float = 0.05) -> List[Dict[str, Any]]:
        rows = self.run(
            "MATCH (b:Brand {id: $bid})-[:LEARNED_PREF]->(p:PreferenceSignal) "
            "WHERE p.weight > $min AND (p.superseded_by_id IS NULL OR p.superseded_by_id = '') "
            "RETURN p",
            bid=brand_id, min=min_weight,
        )
        return [r["p"] for r in rows]

    def delete_preference(self, brand_id: str, signal_id: str) -> bool:
        rows = self.run_write(
            "MATCH (b:Brand {id: $bid})-[:LEARNED_PREF]->(p:PreferenceSignal {id: $sid}) "
            "DETACH DELETE p RETURN count(p) AS removed",
            bid=brand_id, sid=signal_id,
        )
        return bool(rows and rows[0].get("removed", 0))

    # ------------------------------------------------------------------
    # Scene mutation (Pipeline C applier)
    # ------------------------------------------------------------------

    def update_node_fields(self, label: str, node_id: str, fields: Dict[str, Any]) -> None:
        set_clauses = [f"n.{k} = ${k}" for k in fields]
        set_clauses.append("n.updated_at = $ts")
        params: Dict[str, Any] = {"id": node_id, "ts": _now_iso()}
        params.update(_serialize_props(fields))
        self.run_write(
            f"MATCH (n:{label} {{id: $id}}) SET {', '.join(set_clauses)}",
            **params,
        )

    def get_node(self, label: str, node_id: str) -> Optional[Dict[str, Any]]:
        rows = self.run(f"MATCH (n:{label} {{id: $id}}) RETURN n", id=node_id)
        return rows[0]["n"] if rows else None

    # ------------------------------------------------------------------
    # Graph-RAG retrieval for Pipeline B Stage 2
    # ------------------------------------------------------------------

    def retrieve_brand_context(self, brand_id: str, deployment_context: str) -> Dict[str, Any]:
        """Gather everything Pipeline B needs for scene assembly."""
        rows = self.run(
            """
            MATCH (b:Brand {id: $bid})
            OPTIONAL MATCH (b)-[:HAS_COLOR]->(c:Color)
            OPTIONAL MATCH (b)-[:HAS_FONT]->(f:Font)
            OPTIONAL MATCH (b)-[:HAS_ASSET]->(a:Asset)
            WHERE a IS NULL OR a.ingestion_status = 'approved'
            OPTIONAL MATCH (b)-[:LEARNED_PREF]->(ps:PreferenceSignal)
            WHERE ps IS NULL OR ps.weight > 0.05
            RETURN b,
              collect(DISTINCT c) AS colors,
              collect(DISTINCT f) AS fonts,
              collect(DISTINCT a) AS assets,
              collect(DISTINCT ps) AS preferences
            """,
            bid=brand_id,
        )
        if not rows:
            return {"brand": None, "colors": [], "fonts": [], "assets": [], "preferences": []}
        r = rows[0]
        # Filter out nulls that OPTIONAL MATCH + collect may produce.
        return {
            "brand": r["b"],
            "colors": [x for x in r["colors"] if x],
            "fonts": [x for x in r["fonts"] if x],
            "assets": [x for x in r["assets"] if x],
            "preferences": [x for x in r["preferences"] if x],
        }


neo4j_v2 = Neo4jV2()
