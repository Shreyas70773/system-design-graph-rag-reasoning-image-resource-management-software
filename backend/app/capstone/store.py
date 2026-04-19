from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.capstone.models import (
    BoundingBox,
    CanvasVersionNode,
    CreateObjectRequest,
    CreateSceneRequest,
    CreateTextRegionRequest,
    EditEventNode,
    ImageObjectNode,
    RecordEditRequest,
    SceneDocument,
    SceneNode,
    SpatialRelationshipNode,
    TextRegionNode,
    UpdateAspectRatioRequest,
    UserNode,
    utc_now,
)
from app.database.neo4j_client import neo4j_client


class CapstoneSceneStore:
    """Single-user JSON-backed store with optional Neo4j sync."""

    def __init__(self) -> None:
        self.root = Path(__file__).resolve().parents[2] / "uploads" / "capstone" / "scenes"
        self.root.mkdir(parents=True, exist_ok=True)

    def create_scene(self, req: CreateSceneRequest) -> SceneDocument:
        doc = SceneDocument(
            user=UserNode(user_id=req.owner_user_id, email=req.email),
            scene=SceneNode(
                image_path=req.image_path,
                canvas_width=req.canvas_width,
                canvas_height=req.canvas_height,
                aspect_ratio=req.aspect_ratio,
                owner_user_id=req.owner_user_id,
                title=req.title,
            ),
        )
        init_snapshot = self._snapshot(doc)
        version = CanvasVersionNode(
            composite_image_path=req.image_path,
            graph_snapshot_json=init_snapshot,
            is_current=True,
        )
        init_edit = EditEventNode(
            event_type="INIT",
            after_state_json=init_snapshot,
            canvas_version_id=version.version_id,
            user_id=req.owner_user_id,
        )
        doc.canvas_versions.append(version)
        doc.edit_events.append(init_edit)
        self._touch_scene(doc)
        self._write(doc)
        self._sync_to_neo4j(doc)
        return doc

    def get_scene(self, scene_id: str) -> SceneDocument:
        path = self.root / f"{scene_id}.json"
        if not path.exists():
            raise FileNotFoundError(scene_id)
        return SceneDocument.model_validate_json(path.read_text(encoding="utf-8"))

    def add_object(self, scene_id: str, req: CreateObjectRequest) -> SceneDocument:
        doc = self.get_scene(scene_id)
        obj = ImageObjectNode(
            class_label=req.class_label,
            confidence=req.confidence,
            bbox=req.bbox,
            mask_path=req.mask_path,
            z_order=req.z_order,
            is_locked=req.is_locked,
            metadata=req.metadata,
        )
        doc.objects.append(obj)
        self._recompute_relationships(doc)
        self._touch_scene(doc)
        self._write(doc)
        self._sync_to_neo4j(doc)
        return doc

    def add_text_region(self, scene_id: str, req: CreateTextRegionRequest) -> SceneDocument:
        doc = self.get_scene(scene_id)
        text_object = ImageObjectNode(
            class_label="text_region",
            confidence=req.ocr_confidence,
            bbox=req.bbox,
            z_order=max([obj.z_order for obj in doc.objects], default=0) + 1,
            is_text=True,
            metadata={"attached_object_id": req.attached_object_id},
        )
        text_region = TextRegionNode(
            object_id=text_object.object_id,
            attached_object_id=req.attached_object_id,
            raw_text=req.raw_text,
            font_family=req.font_family,
            font_size=req.font_size,
            color_hex=req.color_hex,
            is_embedded=req.is_embedded,
            ocr_confidence=req.ocr_confidence,
            bbox=req.bbox,
        )
        doc.objects.append(text_object)
        doc.text_regions.append(text_region)
        self._recompute_relationships(doc)
        self._touch_scene(doc)
        self._write(doc)
        self._sync_to_neo4j(doc)
        return doc

    def record_edit(self, scene_id: str, req: RecordEditRequest) -> EditEventNode:
        doc = self.get_scene(scene_id)
        snapshot = self._snapshot(doc)
        for version in doc.canvas_versions:
            version.is_current = False
            version.updated_at = utc_now()
        version = CanvasVersionNode(
            composite_image_path=req.composite_image_path or doc.scene.image_path,
            graph_snapshot_json=snapshot,
            is_current=True,
        )
        prev_event_id = doc.edit_events[-1].event_id if doc.edit_events else None
        event = EditEventNode(
            event_type=req.event_type,
            delta_json=req.delta_json,
            before_state_json=req.before_state_json,
            after_state_json=req.after_state_json or snapshot,
            user_id=req.user_id,
            affected_object_ids=req.affected_object_ids,
            prev_event_id=prev_event_id,
            canvas_version_id=version.version_id,
        )
        doc.canvas_versions.append(version)
        doc.edit_events.append(event)
        self._touch_scene(doc)
        self._write(doc)
        self._sync_to_neo4j(doc)
        return event

    def update_aspect_ratio(self, scene_id: str, req: UpdateAspectRatioRequest) -> SceneDocument:
        doc = self.get_scene(scene_id)
        before = {
            "aspect_ratio": doc.scene.aspect_ratio,
            "canvas_width": doc.scene.canvas_width,
            "canvas_height": doc.scene.canvas_height,
        }
        doc.scene.aspect_ratio = req.aspect_ratio
        doc.scene.canvas_width = req.canvas_width
        doc.scene.canvas_height = req.canvas_height
        self._touch_scene(doc)
        self._write(doc)
        self._sync_to_neo4j(doc)
        self.record_edit(
            scene_id,
            RecordEditRequest(
                event_type="ASPECT_RATIO_CHANGE",
                before_state_json=before,
                after_state_json={
                    "aspect_ratio": req.aspect_ratio,
                    "canvas_width": req.canvas_width,
                    "canvas_height": req.canvas_height,
                },
                composite_image_path=req.composite_image_path,
            ),
        )
        return self.get_scene(scene_id)

    def get_inpaint_context(self, scene_id: str, object_id: str, limit: int = 5) -> List[Dict]:
        doc = self.get_scene(scene_id)
        object_map = {obj.object_id: obj for obj in doc.objects}
        if object_id not in object_map:
            raise KeyError(object_id)

        allowed = {"adjacent_to", "overlaps", "contains"}
        neighbors: List[Dict] = []
        for rel in doc.spatial_relationships:
            if rel.target_object_id != object_id or rel.predicate not in allowed:
                continue
            neighbor = object_map.get(rel.source_object_id)
            if neighbor is None:
                continue
            neighbors.append(
                {
                    "object_id": neighbor.object_id,
                    "class_label": neighbor.class_label,
                    "bbox": neighbor.bbox.model_dump(),
                    "predicate": rel.predicate,
                    "distance_px": rel.distance_px,
                    "z_order": neighbor.z_order,
                }
            )

        neighbors.sort(key=lambda item: (item["distance_px"], -item["z_order"]))
        return neighbors[:limit]

    def get_history(self, scene_id: str) -> List[EditEventNode]:
        doc = self.get_scene(scene_id)
        return list(reversed(doc.edit_events))

    def upsert_segmented_object(
        self,
        scene_id: str,
        *,
        class_label: str,
        bbox: BoundingBox,
        mask_path: str,
        confidence: float = 1.0,
        object_id: Optional[str] = None,
        z_order: Optional[int] = None,
    ) -> SceneDocument:
        doc = self.get_scene(scene_id)
        existing = None
        if object_id:
            existing = next((obj for obj in doc.objects if obj.object_id == object_id), None)

        if existing is None:
            obj = ImageObjectNode(
                class_label=class_label,
                confidence=confidence,
                bbox=bbox,
                mask_path=mask_path,
                z_order=z_order if z_order is not None else max([o.z_order for o in doc.objects], default=-1) + 1,
            )
            doc.objects.append(obj)
        else:
            existing.class_label = class_label
            existing.confidence = confidence
            existing.bbox = bbox
            existing.mask_path = mask_path
            existing.updated_at = utc_now()
            if z_order is not None:
                existing.z_order = z_order

        self._recompute_relationships(doc)
        self._touch_scene(doc)
        self._write(doc)
        self._sync_to_neo4j(doc)
        return doc

    def remove_object(
        self,
        scene_id: str,
        *,
        object_id: str,
        composite_image_path: str,
        context_neighbors: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None,
        user_id: str = "local-user",
    ) -> SceneDocument:
        doc = self.get_scene(scene_id)
        target = next((obj for obj in doc.objects if obj.object_id == object_id), None)
        if target is None:
            raise KeyError(object_id)

        before = self._snapshot(doc)
        doc.objects = [obj for obj in doc.objects if obj.object_id != object_id]
        doc.text_regions = [
            text
            for text in doc.text_regions
            if text.object_id != object_id and text.attached_object_id != object_id
        ]
        doc.scene.image_path = composite_image_path
        doc.scene.updated_at = utc_now()
        self._recompute_relationships(doc)

        after = self._snapshot(doc)
        for version in doc.canvas_versions:
            version.is_current = False
            version.updated_at = utc_now()
        version = CanvasVersionNode(
            composite_image_path=composite_image_path,
            graph_snapshot_json=after,
            is_current=True,
        )
        prev_event_id = doc.edit_events[-1].event_id if doc.edit_events else None
        doc.canvas_versions.append(version)
        doc.edit_events.append(
            EditEventNode(
                event_type="REMOVE_OBJECT",
                delta_json={
                    "removed_object_id": object_id,
                    "removed_class_label": target.class_label,
                    "context_neighbors": context_neighbors or [],
                    "metadata": metadata or {},
                },
                before_state_json=before,
                after_state_json=after,
                user_id=user_id,
                affected_object_ids=[object_id],
                prev_event_id=prev_event_id,
                canvas_version_id=version.version_id,
            )
        )

        self._touch_scene(doc)
        self._write(doc)
        self._sync_to_neo4j(doc)
        return doc

    def _write(self, doc: SceneDocument) -> None:
        path = self.root / f"{doc.scene.scene_id}.json"
        path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")

    def _touch_scene(self, doc: SceneDocument) -> None:
        ts = utc_now()
        doc.scene.updated_at = ts
        doc.user.updated_at = ts

    def _snapshot(self, doc: SceneDocument) -> Dict:
        return {
            "scene": doc.scene.model_dump(mode="json"),
            "objects": [obj.model_dump(mode="json") for obj in doc.objects],
            "text_regions": [text.model_dump(mode="json") for text in doc.text_regions],
            "spatial_relationships": [rel.model_dump(mode="json") for rel in doc.spatial_relationships],
        }

    def _recompute_relationships(self, doc: SceneDocument) -> None:
        relationships: List[SpatialRelationshipNode] = []
        objects = doc.objects
        for i, source in enumerate(objects):
            for j, target in enumerate(objects):
                if i == j:
                    continue
                for predicate, distance_px in infer_pair_relationships(source.bbox, target.bbox):
                    relationships.append(
                        SpatialRelationshipNode(
                            source_object_id=source.object_id,
                            target_object_id=target.object_id,
                            predicate=predicate,
                            distance_px=distance_px,
                        )
                    )
        doc.spatial_relationships = relationships

    def _sync_to_neo4j(self, doc: SceneDocument) -> None:
        try:
            driver = neo4j_client.driver
        except Exception:
            return

        if driver is None:
            return

        scene_props = self._json_props(doc.scene.model_dump(mode="json"))
        user_props = self._json_props(doc.user.model_dump(mode="json"))
        neo4j_client.execute_query(
            """
            MERGE (u:User:CapstoneUser {user_id: $user.user_id})
            SET u += $user
            MERGE (s:Scene:CapstoneScene {scene_id: $scene.scene_id})
            SET s += $scene
            MERGE (u)-[:OWNS]->(s)
            """,
            {"user": user_props, "scene": scene_props},
        )

        neo4j_client.execute_query(
            """
            MATCH (s:CapstoneScene {scene_id: $scene_id})
            OPTIONAL MATCH (s)-[:CONTAINS_OBJECT|CONTAINS_TEXT|HAS_VERSION|HAS_EDIT]->(n)
            DETACH DELETE n
            """,
            {"scene_id": doc.scene.scene_id},
        )

        for obj in doc.objects:
            neo4j_client.execute_query(
                """
                MATCH (s:CapstoneScene {scene_id: $scene_id})
                CREATE (o:ImageObject:CapstoneImageObject $props)
                CREATE (s)-[:CONTAINS_OBJECT {layer_index: $layer_index}]->(o)
                """,
                {
                    "scene_id": doc.scene.scene_id,
                    "layer_index": obj.z_order,
                    "props": self._json_props(obj.model_dump(mode="json")),
                },
            )

        for rel in doc.spatial_relationships:
            neo4j_client.execute_query(
                """
                MATCH (src:CapstoneImageObject {object_id: $source_id})
                MATCH (dst:CapstoneImageObject {object_id: $target_id})
                CREATE (src)-[:SPATIAL_REL {
                    rel_id: $rel_id,
                    predicate: $predicate,
                    confidence: $confidence,
                    distance_px: $distance_px
                }]->(dst)
                """,
                {
                    "source_id": rel.source_object_id,
                    "target_id": rel.target_object_id,
                    "rel_id": rel.rel_id,
                    "predicate": rel.predicate,
                    "confidence": rel.confidence,
                    "distance_px": rel.distance_px,
                },
            )

        for text in doc.text_regions:
            neo4j_client.execute_query(
                """
                MATCH (s:CapstoneScene {scene_id: $scene_id})
                MATCH (o:CapstoneImageObject {object_id: $text_object_id})
                OPTIONAL MATCH (attached:CapstoneImageObject {object_id: $attached_object_id})
                CREATE (t:TextRegion:CapstoneTextRegion $props)
                CREATE (s)-[:CONTAINS_TEXT]->(t)
                CREATE (t)-[:TEXT_ON]->(o)
                FOREACH (_ IN CASE WHEN attached IS NULL THEN [] ELSE [1] END |
                    CREATE (t)-[:TEXT_ATTACHED_TO]->(attached)
                )
                """,
                {
                    "scene_id": doc.scene.scene_id,
                    "text_object_id": text.object_id,
                    "attached_object_id": text.attached_object_id,
                    "props": self._json_props(text.model_dump(mode="json")),
                },
            )

        previous_event_id: Optional[str] = None
        for version, event in zip(doc.canvas_versions, doc.edit_events):
            neo4j_client.execute_query(
                """
                MATCH (s:CapstoneScene {scene_id: $scene_id})
                CREATE (v:CanvasVersion:CapstoneCanvasVersion $props)
                CREATE (s)-[:HAS_VERSION {is_current: $is_current}]->(v)
                """,
                {
                    "scene_id": doc.scene.scene_id,
                    "is_current": version.is_current,
                    "props": self._json_props(version.model_dump(mode="json")),
                },
            )
            neo4j_client.execute_query(
                """
                MATCH (s:CapstoneScene {scene_id: $scene_id})
                CREATE (e:EditEvent:CapstoneEditEvent $props)
                CREATE (s)-[:HAS_EDIT]->(e)
                """,
                {
                    "scene_id": doc.scene.scene_id,
                    "props": self._json_props(event.model_dump(mode="json")),
                },
            )
            if previous_event_id is not None:
                neo4j_client.execute_query(
                    """
                    MATCH (prev:CapstoneEditEvent {event_id: $prev_event_id})
                    MATCH (curr:CapstoneEditEvent {event_id: $event_id})
                    CREATE (curr)-[:PREV_EDIT]->(prev)
                    """,
                    {"prev_event_id": previous_event_id, "event_id": event.event_id},
                )
            previous_event_id = event.event_id

    @staticmethod
    def _is_neo4j_primitive(value: Any) -> bool:
        return value is None or isinstance(value, (str, int, float, bool))

    @classmethod
    def _to_neo4j_prop_value(cls, value: Any) -> Any:
        if cls._is_neo4j_primitive(value):
            return value
        if isinstance(value, list):
            # Neo4j permits arrays of primitives but not arrays containing maps/lists.
            if all(cls._is_neo4j_primitive(item) for item in value):
                return value
            return json.dumps(value, default=str)
        if isinstance(value, dict):
            return json.dumps(value, default=str)
        return str(value)

    @classmethod
    def _json_props(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = json.loads(json.dumps(payload, default=str))
        return {k: cls._to_neo4j_prop_value(v) for k, v in normalized.items()}


def _axis_gap(a0: int, a1: int, b0: int, b1: int) -> int:
    if a1 < b0:
        return b0 - a1
    if b1 < a0:
        return a0 - b1
    return 0


def _contains(a: BoundingBox, b: BoundingBox) -> bool:
    return a.x <= b.x and a.y <= b.y and a.x2 >= b.x2 and a.y2 >= b.y2


def _overlap_area(a: BoundingBox, b: BoundingBox) -> int:
    x_overlap = max(0, min(a.x2, b.x2) - max(a.x, b.x))
    y_overlap = max(0, min(a.y2, b.y2) - max(a.y, b.y))
    return x_overlap * y_overlap


def _distance_between_boxes(a: BoundingBox, b: BoundingBox) -> float:
    dx = _axis_gap(a.x, a.x2, b.x, b.x2)
    dy = _axis_gap(a.y, a.y2, b.y, b.y2)
    if dx == 0 and dy == 0:
        return 0.0
    return round(math.sqrt((dx * dx) + (dy * dy)), 2)


def infer_pair_relationships(source: BoundingBox, target: BoundingBox) -> List[Tuple[str, float]]:
    """Infer directional scene-graph predicates from two bounding boxes."""
    predicates: List[Tuple[str, float]] = []
    distance_px = _distance_between_boxes(source, target)

    if _contains(source, target):
        predicates.append(("contains", distance_px))

    overlap = _overlap_area(source, target)
    if overlap > 0:
        predicates.append(("overlaps", distance_px))
    elif distance_px <= 48:
        predicates.append(("adjacent_to", distance_px))

    if source.center_x < target.center_x:
        predicates.append(("left_of", abs(target.center_x - source.center_x)))
    elif source.center_x > target.center_x:
        predicates.append(("right_of", abs(target.center_x - source.center_x)))

    if source.center_y < target.center_y:
        predicates.append(("above", abs(target.center_y - source.center_y)))
    elif source.center_y > target.center_y:
        predicates.append(("below", abs(target.center_y - source.center_y)))

    return predicates


capstone_scene_store = CapstoneSceneStore()
