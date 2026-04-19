"""Shared pytest fixtures for V2 tests.

Most tests run without a live Neo4j by providing an in-memory fake that
records writes and answers reads. Integration tests that require a real
database opt in via the `real_neo4j` fixture and are skipped when
NEO4J_URI is unset.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))


class FakeNeo4j:
    """In-memory Neo4j stand-in that mirrors the Neo4jV2 surface we exercise."""

    def __init__(self) -> None:
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.labels: Dict[str, str] = {}
        self.rels: List[tuple] = []  # (from_id, rel_type, to_id, props)

    @property
    def available(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    def _create_node(self, label: str, props: Dict[str, Any]) -> str:
        nid = props.get("id") or str(uuid.uuid4())
        props = {**props, "id": nid}
        self.nodes[nid] = props
        self.labels[nid] = label
        return nid

    def _link(self, src: str, rel: str, dst: str, props: Optional[Dict[str, Any]] = None) -> None:
        self.rels.append((src, rel, dst, props or {}))

    def run(self, query: str, **params):
        # Very small query recogniser for the queries the test suite hits.
        # We don't claim to be a Cypher engine.
        return _FakeRunResult(self, query, params).rows

    def run_write(self, query: str, **params):
        return self.run(query, **params)

    # ------------------------------------------------------------------
    # Pipeline A
    # ------------------------------------------------------------------

    def get_brand_v2(self, brand_id: str):
        for nid, props in self.nodes.items():
            if self.labels.get(nid) == "Brand" and props["id"] == brand_id:
                return props
        return None

    def pipeline_a_create_asset(self, *, brand_id, asset_type, source_url):
        aid = self._create_node("Asset", {
            "asset_type": asset_type, "source_url": source_url,
            "ingestion_status": "pending", "schema_version": "2.0",
        })
        self._link(brand_id, "HAS_ASSET", aid)
        return aid

    def pipeline_a_update_asset_status(self, asset_id, status, **extra):
        if asset_id in self.nodes:
            self.nodes[asset_id]["ingestion_status"] = status
            self.nodes[asset_id].update(extra)

    def pipeline_a_set_vlm_description(self, asset_id, description, embedding):
        if asset_id in self.nodes:
            self.nodes[asset_id]["vlm_description"] = description
            if embedding is not None:
                self.nodes[asset_id]["clip_embedding"] = embedding

    def pipeline_a_attach_mesh(self, asset_id, mesh):
        mid = self._create_node("Mesh3D", mesh)
        self._link(asset_id, "HAS_GEOMETRY", mid)
        return mid

    def pipeline_a_attach_material(self, asset_id, material, part_name=None):
        mid = self._create_node("Material", material)
        self._link(asset_id, "HAS_MATERIAL", mid, {"part_name": part_name})
        return mid

    def pipeline_a_attach_part(self, asset_id, part):
        pid = self._create_node("SemanticPart", part)
        self._link(asset_id, "HAS_PART", pid)
        return pid

    def pipeline_a_attach_light_probe(self, asset_id, probe):
        pid = self._create_node("LightProbe", probe)
        self._link(asset_id, "HAS_LIGHT_PROBE", pid)
        return pid

    def pipeline_a_attach_canonical_pose(self, asset_id, pose):
        pid = self._create_node("CanonicalPose", pose)
        self._link(asset_id, "HAS_CANONICAL_POSE", pid)
        return pid

    def pipeline_a_record_decomposition_run(self, asset_id, run):
        rid = self._create_node("DecompositionRun", run)
        self._link(asset_id, "DECOMPOSED_BY", rid)
        return rid

    def get_asset_full(self, asset_id):
        if asset_id not in self.nodes:
            return {"asset": None}
        asset = self.nodes[asset_id]
        return {
            "asset": asset,
            "geometry": [self.nodes[d] for s, r, d, _ in self.rels if s == asset_id and r == "HAS_GEOMETRY"],
            "materials": [self.nodes[d] for s, r, d, _ in self.rels if s == asset_id and r == "HAS_MATERIAL"],
            "parts": [self.nodes[d] for s, r, d, _ in self.rels if s == asset_id and r == "HAS_PART"],
            "light_probe": next((self.nodes[d] for s, r, d, _ in self.rels if s == asset_id and r == "HAS_LIGHT_PROBE"), None),
            "canonical_pose": next((self.nodes[d] for s, r, d, _ in self.rels if s == asset_id and r == "HAS_CANONICAL_POSE"), None),
            "decomposition_runs": [self.nodes[d] for s, r, d, _ in self.rels if s == asset_id and r == "DECOMPOSED_BY"],
        }

    # ------------------------------------------------------------------
    # Pipeline B
    # ------------------------------------------------------------------

    def pipeline_b_create_scene(self, *, brand_id, intent_text, scene_graph, deployment_context):
        sid = self._create_node("Scene", {
            "brand_id": brand_id, "intent_text": intent_text,
            "scene_graph_json": scene_graph, "deployment_context": deployment_context,
            "status": "draft",
        })
        self._link(brand_id, "OWNS_SCENE", sid)
        return sid

    def pipeline_b_add_placement(self, scene_id, placement):
        pid = self._create_node("Placement", placement)
        self._link(scene_id, "HAS_PLACEMENT", pid)
        self._link(pid, "INSTANCE_OF", placement["asset_id"])
        return pid

    def pipeline_b_add_camera(self, scene_id, cam):
        cid = self._create_node("Camera", cam)
        self._link(scene_id, "HAS_CAMERA", cid)
        return cid

    def pipeline_b_add_light(self, scene_id, light):
        lid = self._create_node("Light", light)
        self._link(scene_id, "HAS_LIGHT", lid)
        return lid

    def pipeline_b_add_text_layer(self, scene_id, tl):
        tid = self._create_node("TextLayer", tl)
        self._link(scene_id, "HAS_TEXT_LAYER", tid)
        return tid

    def pipeline_b_add_render(self, scene_id, render):
        rid = self._create_node("Render", render)
        self._link(scene_id, "HAS_RENDER", rid)
        return rid

    def get_scene_full(self, scene_id):
        if scene_id not in self.nodes:
            return {"scene": None}
        return {
            "scene": self.nodes[scene_id],
            "placements": [self.nodes[d] for s, r, d, _ in self.rels if s == scene_id and r == "HAS_PLACEMENT"],
            "cameras": [self.nodes[d] for s, r, d, _ in self.rels if s == scene_id and r == "HAS_CAMERA"],
            "lights": [self.nodes[d] for s, r, d, _ in self.rels if s == scene_id and r == "HAS_LIGHT"],
            "text_layers": [self.nodes[d] for s, r, d, _ in self.rels if s == scene_id and r == "HAS_TEXT_LAYER"],
            "renders": [self.nodes[d] for s, r, d, _ in self.rels if s == scene_id and r == "HAS_RENDER"],
        }

    # ------------------------------------------------------------------
    # Pipeline C
    # ------------------------------------------------------------------

    def pipeline_c_record_interaction(self, interaction, target_ids=None):
        iid = self._create_node("Interaction", interaction)
        for tid in target_ids or []:
            self._link(iid, "MODIFIED", tid)
        return iid

    def pipeline_c_record_nl_command(self, nl, interaction_id=None):
        nid = self._create_node("NaturalLanguageCommand", nl)
        if interaction_id:
            self._link(interaction_id, "RESOLVED_BY", nid)
        return nid

    def pipeline_c_write_preference_signal(self, brand_id, signal):
        # Upsert by (brand_id, name).
        for nid, props in self.nodes.items():
            if self.labels.get(nid) == "PreferenceSignal" and props.get("name") == signal.get("name") \
                    and any(s == brand_id and r == "LEARNED_PREF" and d == nid for s, r, d, _ in self.rels):
                props.update(signal)
                return nid
        sid = self._create_node("PreferenceSignal", signal)
        self._link(brand_id, "LEARNED_PREF", sid)
        return sid

    def get_active_preferences(self, brand_id, min_weight=0.05):
        out = []
        for s, r, d, _ in self.rels:
            if s == brand_id and r == "LEARNED_PREF":
                p = self.nodes.get(d) or {}
                if float(p.get("weight", 0.0)) > min_weight and not p.get("superseded_by_id"):
                    out.append(p)
        return out

    def delete_preference(self, brand_id, signal_id):
        if signal_id in self.nodes:
            del self.nodes[signal_id]
            self.rels = [t for t in self.rels if t[0] != signal_id and t[2] != signal_id]
            return True
        return False

    def update_node_fields(self, label, node_id, fields):
        if node_id in self.nodes:
            self.nodes[node_id].update(fields)

    def get_node(self, label, node_id):
        if node_id in self.nodes and self.labels.get(node_id) == label:
            return self.nodes[node_id]
        return None

    def retrieve_brand_context(self, brand_id, deployment_context):
        if brand_id not in self.nodes:
            return {"brand": None, "colors": [], "fonts": [], "assets": [], "preferences": []}
        assets = [self.nodes[d] for s, r, d, _ in self.rels if s == brand_id and r == "HAS_ASSET"]
        colors = [self.nodes[d] for s, r, d, _ in self.rels if s == brand_id and r == "HAS_COLOR"]
        fonts = [self.nodes[d] for s, r, d, _ in self.rels if s == brand_id and r == "HAS_FONT"]
        prefs = [self.nodes[d] for s, r, d, _ in self.rels if s == brand_id and r == "LEARNED_PREF"]
        return {
            "brand": self.nodes[brand_id],
            "colors": colors, "fonts": fonts, "assets": assets, "preferences": prefs,
        }


class _FakeRunResult:
    """Tiny query matcher. Recognises a handful of patterns tests exercise."""

    def __init__(self, db: FakeNeo4j, query: str, params: Dict[str, Any]) -> None:
        self.rows: List[Dict[str, Any]] = []
        q = query.strip()

        if "MATCH (n:" in q and "SET " in q:
            label = q.split("MATCH (n:", 1)[1].split(" ", 1)[0]
            db.update_node_fields(label, params.get("id", ""), {
                k: v for k, v in params.items() if k not in ("id", "ts")
            })
        elif "DETACH DELETE t" in q and "TextLayer" in q:
            tid = params.get("id", "")
            if tid in db.nodes:
                del db.nodes[tid]
                db.rels = [t for t in db.rels if t[0] != tid and t[2] != tid]
        elif "MATCH (p:Placement" in q and "INSTANCE_OF" in q and "HAS_MATERIAL" in q:
            pid = params.get("pid", "")
            asset_ids = [d for s, r, d, _ in db.rels if s == pid and r == "INSTANCE_OF"]
            for aid in asset_ids:
                for s2, r2, d2, _ in db.rels:
                    if s2 == aid and r2 == "HAS_MATERIAL":
                        self.rows.append({"m": db.nodes[d2]})
                        return
        elif "(i:Interaction)" in q and "bid" in params:
            # Distiller: find interactions that modified anything reachable from
            # scenes owned by the brand. Fake traversal (no multi-hop Cypher).
            bid = params["bid"]
            scene_ids = {d for s, r, d, _ in db.rels if s == bid and r == "OWNS_SCENE"}
            reachable = set(scene_ids)
            for s, r, d, _ in db.rels:
                if s in scene_ids and r in {
                    "HAS_PLACEMENT", "HAS_LIGHT", "HAS_TEXT_LAYER",
                    "HAS_CAMERA", "HAS_TERRAIN",
                }:
                    reachable.add(d)
            seen = set()
            for s, r, d, _ in db.rels:
                if r == "MODIFIED" and d in reachable and s not in seen:
                    seen.add(s)
                    node = db.nodes.get(s)
                    if node and db.labels.get(s) == "Interaction":
                        self.rows.append({"i": node})


@pytest.fixture
def fake_db():
    fake = FakeNeo4j()

    with patch("app.database.neo4j_v2.neo4j_v2", fake), \
         patch("app.interaction.applier.neo4j_v2", fake), \
         patch("app.interaction.distiller.neo4j_v2", fake), \
         patch("app.interaction.retrieval_bias.compile_biases",
               wraps=__import__("app.interaction.retrieval_bias", fromlist=["compile_biases"]).compile_biases), \
         patch("app.scene.assembler.neo4j_v2", fake), \
         patch("app.scene.pipeline.neo4j_v2", fake), \
         patch("app.ingestion.orchestrator.neo4j_v2", fake):
        yield fake


@pytest.fixture
def brand_in_db(fake_db):
    brand_id = fake_db._create_node("Brand", {
        "name": "TestBrand", "schema_version": "2.0", "primary_hex": ["#ff3344"],
    })
    fake_db._create_node("Color", {"hex": "#ff3344", "role": "primary"})
    return brand_id


@pytest.fixture(autouse=True)
def mock_mode_env(monkeypatch):
    monkeypatch.setenv("V2_MOCK_MODE", "true")
    # Invalidate the cached settings.
    from app.config_v2 import get_v2_settings
    get_v2_settings.cache_clear()
    yield
    get_v2_settings.cache_clear()


@pytest.fixture
def sample_image_bytes():
    """In-memory PNG bytes for pipeline inputs."""
    import io
    from PIL import Image
    img = Image.new("RGB", (1024, 1024), (220, 60, 60))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_image_url(sample_image_bytes, tmp_path, monkeypatch):
    """Write the sample image into a temp dir and return a file:// path that
    storage.fetch_image_bytes can resolve via local-path branch."""
    p = tmp_path / "ref.png"
    p.write_bytes(sample_image_bytes)
    return str(p)
