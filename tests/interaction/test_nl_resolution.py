"""AC-6: natural-language edit resolution — heuristic + confidence gating."""

from __future__ import annotations

from app.interaction.command_parser import CONFIDENCE_THRESHOLD, resolve
from app.schema_v2 import EditTargetKind, InteractionType


def test_move_left_with_selected_placement_resolves():
    r = resolve("move it left please", scene_id="s1", selected_placement_ids=["p1"])
    assert r.action == InteractionType.MOVE
    assert r.target_kind == EditTargetKind.PLACEMENT
    assert r.target_id == "p1"
    assert r.params["delta"][0] < 0
    assert r.confidence >= CONFIDENCE_THRESHOLD


def test_color_change_on_text_layer():
    r = resolve("make the text blue", scene_id="s1", selected_text_ids=["t1"])
    assert r.action == InteractionType.CHANGE_COLOR
    assert r.target_kind == EditTargetKind.TEXT_LAYER
    assert r.params["hex"].startswith("#")
    assert r.confidence >= CONFIDENCE_THRESHOLD


def test_delete_selected_placement():
    r = resolve("remove that", scene_id="s1", selected_placement_ids=["p9"])
    assert r.action == InteractionType.DELETE
    assert r.target_id == "p9"


def test_ambiguous_input_falls_below_threshold():
    r = resolve("can you make it better", scene_id="s1")
    assert r.confidence < CONFIDENCE_THRESHOLD


def test_edit_text_quoted():
    r = resolve('change the text to "Launch Day"', scene_id="s1", selected_text_ids=["t9"])
    assert r.action == InteractionType.EDIT_TEXT
    assert r.params["text"] == "Launch Day"
