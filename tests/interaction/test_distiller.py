"""AC-7 + AC-8: distiller thresholds, decay, and preference bounds."""

from __future__ import annotations

from app.interaction.applier import apply
from app.interaction.distiller import distill_for_brand
from app.interaction.retrieval_bias import compile_biases
from app.schema_v2 import EditTargetKind, InteractionType, StructuredEditCommand


def _seed_scene_with_placement(fake_db, brand_id):
    scene_id = fake_db._create_node("Scene", {
        "brand_id": brand_id, "deployment_context": "digital", "status": "draft",
        "intent_text": "stub", "scene_graph_json": {}, "schema_version": "2.0",
    })
    fake_db._link(brand_id, "OWNS_SCENE", scene_id)
    placement_ids = []
    for i in range(3):
        pid = fake_db._create_node("Placement", {
            "asset_id": f"asset-{i}", "position": [0.0, 0.0, 0.0],
            "rotation_quat": [0, 0, 0, 1], "scale": [1, 1, 1],
            "z_order": 1, "visible": True,
        })
        fake_db._link(scene_id, "HAS_PLACEMENT", pid)
        placement_ids.append(pid)
    return scene_id, placement_ids


def test_three_repeats_trigger_signal_creation(fake_db, brand_in_db):
    scene_id, placements = _seed_scene_with_placement(fake_db, brand_in_db)
    for pid in placements:
        apply(
            StructuredEditCommand(
                action=InteractionType.MOVE,
                target_kind=EditTargetKind.PLACEMENT,
                target_id=pid,
                params={"delta": [0.0, 0.7, 0.0], "absolute": False},
            ),
            actor="user", surface="3d_canvas",
        )
    summary = distill_for_brand(brand_in_db)
    # Expect a y-bias signal created.
    assert any("product_bias:y" in name for name in summary["created"] + summary["updated"])


def test_under_threshold_creates_no_signal(fake_db, brand_in_db):
    scene_id, placements = _seed_scene_with_placement(fake_db, brand_in_db)
    apply(
        StructuredEditCommand(
            action=InteractionType.MOVE,
            target_kind=EditTargetKind.PLACEMENT,
            target_id=placements[0],
            params={"delta": [0.5, 0.0, 0.0]},
        ),
        actor="user", surface="3d_canvas",
    )
    summary = distill_for_brand(brand_in_db)
    assert summary["created"] == [] and summary["updated"] == []


def test_retrieval_bias_clamps_position():
    # Synthetic preferences: push x-bias to +99 (way beyond cap).
    sigs = [
        {"name": "composition.product_bias:x", "weight": 1.0,
         "value_json": '{"value": 99.0, "sample_size": 10}'}
    ]
    b = compile_biases(sigs)
    assert b["composition"]["product_x_bias"] <= 1.5
    assert b["composition"]["product_x_bias"] >= -1.5


def test_retrieval_bias_combines_multiple_signals():
    sigs = [
        {"name": "composition.product_bias:x", "weight": 0.6, "value_json": '{"value": 1.0}'},
        {"name": "composition.product_bias:y", "weight": 0.4, "value_json": '{"value": -1.2}'},
    ]
    b = compile_biases(sigs)
    assert abs(b["composition"]["product_x_bias"] - 0.6) < 1e-6
    assert abs(b["composition"]["product_y_bias"] + 0.48) < 1e-6


def test_hard_bound_prunes_oldest_weakest(fake_db, brand_in_db):
    # Plant 40 signals; distiller's enforce_bound should leave ≤ 32.
    for i in range(40):
        fake_db.pipeline_c_write_preference_signal(brand_in_db, {
            "name": f"color.preferred_hex:material_{i}",
            "kind": "color",
            "value_json": '{"hex": "#123456", "support": 3, "sample_size": 3}',
            "weight": 0.1 + 0.01 * i,
            "source_count": 3,
            "last_reinforced_at": "2024-01-01T00:00:00",
            "superseded_by_id": "",
            "description": "seed",
        })
    # Trigger distill (empty interaction stream → only enforces bound).
    from app.interaction.distiller import _enforce_bound
    pruned = _enforce_bound(brand_in_db)
    assert len(pruned) >= 8
    active = fake_db.get_active_preferences(brand_in_db, min_weight=0.0)
    assert len(active) <= 32
