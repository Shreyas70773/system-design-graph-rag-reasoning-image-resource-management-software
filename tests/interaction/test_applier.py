"""AC-3 + AC-5: applier mutations stay in bounds and produce audit trail."""

from __future__ import annotations

from app.interaction.applier import apply
from app.schema_v2 import EditTargetKind, InteractionType, StructuredEditCommand


def test_move_clamps_to_world_bounds(fake_db, brand_in_db):
    scene_id = fake_db._create_node("Scene", {"brand_id": brand_in_db, "deployment_context": "digital"})
    pid = fake_db._create_node("Placement", {"position": [0, 0, 0], "asset_id": "a",
                                              "rotation_quat": [0, 0, 0, 1], "scale": [1, 1, 1]})
    fake_db._link(scene_id, "HAS_PLACEMENT", pid)

    result = apply(
        StructuredEditCommand(
            action=InteractionType.MOVE,
            target_kind=EditTargetKind.PLACEMENT,
            target_id=pid,
            params={"delta": [500.0, 0.0, 0.0], "absolute": True},
        ),
        actor="user", surface="3d_canvas",
    )
    assert result["post_state"]["position"][0] == 50.0  # clamp to +50


def test_scale_clamps_factor(fake_db, brand_in_db):
    pid = fake_db._create_node("Placement", {"position": [0, 0, 0], "asset_id": "a",
                                              "rotation_quat": [0, 0, 0, 1], "scale": [1, 1, 1]})
    result = apply(
        StructuredEditCommand(
            action=InteractionType.SCALE,
            target_kind=EditTargetKind.PLACEMENT,
            target_id=pid,
            params={"factor": 100.0},
        ),
        actor="user", surface="3d_canvas",
    )
    # clamp of 10x per call.
    assert result["post_state"]["scale"][0] <= 10.0


def test_interaction_recorded_with_pre_post_snapshot(fake_db, brand_in_db):
    pid = fake_db._create_node("Placement", {"position": [0, 0, 0], "asset_id": "a",
                                              "rotation_quat": [0, 0, 0, 1], "scale": [1, 1, 1]})
    result = apply(
        StructuredEditCommand(
            action=InteractionType.MOVE,
            target_kind=EditTargetKind.PLACEMENT,
            target_id=pid,
            params={"delta": [0.5, 0.0, 0.0]},
        ),
        actor="user", surface="3d_canvas",
    )
    assert result["interaction_id"] in fake_db.nodes
    node = fake_db.nodes[result["interaction_id"]]
    assert node["action"] == "move"
    assert node["pre_state_json"]
    assert node["post_state_json"]


def test_invalid_params_raise_clean_error():
    import pytest
    from app.interaction.dispatch_schema import validate
    with pytest.raises(ValueError) as exc_info:
        validate(InteractionType.MOVE, {"delta": [1, 2]})
    assert "delta" in str(exc_info.value).lower() or "Invalid params for move" in str(exc_info.value)
