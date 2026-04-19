from __future__ import annotations

from pathlib import Path

from app.capstone.models import BoundingBox, CreateObjectRequest, CreateSceneRequest, CreateTextRegionRequest
from app.capstone.store import CapstoneSceneStore, infer_pair_relationships


def test_infer_pair_relationships_captures_overlap_and_direction():
    left = BoundingBox(x=10, y=20, w=40, h=50)
    right = BoundingBox(x=35, y=25, w=45, h=45)

    predicates = {name for name, _ in infer_pair_relationships(left, right)}

    assert "overlaps" in predicates
    assert "left_of" in predicates


def test_capstone_store_creates_init_history_and_context(tmp_path):
    store = CapstoneSceneStore()
    store.root = Path(tmp_path)

    scene = store.create_scene(
        CreateSceneRequest(
            image_path="/tmp/original.png",
            canvas_width=1280,
            canvas_height=720,
            aspect_ratio="16:9",
        )
    )
    assert scene.edit_events[0].event_type == "INIT"
    assert scene.canvas_versions[0].is_current is True

    updated = store.add_object(
        scene.scene.scene_id,
        CreateObjectRequest(
            class_label="chair",
            bbox=BoundingBox(x=100, y=120, w=150, h=220),
            z_order=1,
        ),
    )
    updated = store.add_object(
        updated.scene.scene_id,
        CreateObjectRequest(
            class_label="table",
            bbox=BoundingBox(x=260, y=140, w=220, h=180),
            z_order=0,
        ),
    )
    updated = store.add_text_region(
        updated.scene.scene_id,
        CreateTextRegionRequest(
            raw_text="SALE",
            bbox=BoundingBox(x=270, y=110, w=120, h=40),
            attached_object_id=updated.objects[1].object_id,
        ),
    )

    neighbors = store.get_inpaint_context(updated.scene.scene_id, updated.objects[0].object_id)
    assert neighbors
    assert any(item["class_label"] == "table" for item in neighbors)

    reloaded = store.get_scene(updated.scene.scene_id)
    assert len(reloaded.text_regions) == 1
    assert reloaded.text_regions[0].raw_text == "SALE"


def test_capstone_store_remove_object_updates_history(tmp_path):
    store = CapstoneSceneStore()
    store.root = Path(tmp_path)

    scene = store.create_scene(
        CreateSceneRequest(
            image_path="/tmp/original.png",
            canvas_width=1000,
            canvas_height=1000,
            aspect_ratio="1:1",
        )
    )
    scene = store.upsert_segmented_object(
        scene.scene.scene_id,
        class_label="lamp",
        bbox=BoundingBox(x=100, y=100, w=120, h=240),
        mask_path="/tmp/lamp-mask.png",
    )

    updated = store.remove_object(
        scene.scene.scene_id,
        object_id=scene.objects[0].object_id,
        composite_image_path="/tmp/inpainted.png",
        context_neighbors=[],
    )

    assert updated.scene.image_path == "/tmp/inpainted.png"
    assert updated.objects == []
    assert updated.edit_events[-1].event_type == "REMOVE_OBJECT"
    assert updated.canvas_versions[-1].is_current is True


def test_json_props_serializes_nested_values_for_neo4j():
    props = CapstoneSceneStore._json_props(
        {
            "scene_id": "scene_1",
            "affected_object_ids": ["obj_1", "obj_2"],
            "bbox": {"x": 10, "y": 20, "w": 100, "h": 80},
            "graph_snapshot_json": {
                "scene": {"scene_id": "scene_1", "aspect_ratio": "10:7"},
                "objects": [],
                "text_regions": [],
                "spatial_relationships": [],
            },
            "list_of_maps": [{"k": "v"}],
        }
    )

    assert props["scene_id"] == "scene_1"
    assert props["affected_object_ids"] == ["obj_1", "obj_2"]
    assert isinstance(props["bbox"], str)
    assert isinstance(props["graph_snapshot_json"], str)
    assert isinstance(props["list_of_maps"], str)
