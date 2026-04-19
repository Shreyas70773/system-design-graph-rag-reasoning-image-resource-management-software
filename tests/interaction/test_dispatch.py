"""AC-5: structured edit commands validated against per-action schemas."""

from __future__ import annotations

import pytest

from app.interaction.dispatch_schema import known_actions, validate
from app.schema_v2 import InteractionType


def test_every_registered_action_has_known_params():
    for action, required in known_actions():
        assert isinstance(required, list)


def test_move_requires_three_component_delta():
    ok = validate(InteractionType.MOVE, {"delta": [1.0, 0.0, 0.0], "absolute": False})
    assert ok.delta == [1.0, 0.0, 0.0]

    with pytest.raises(ValueError):
        validate(InteractionType.MOVE, {"delta": [1.0, 0.0]})
    with pytest.raises(ValueError):
        validate(InteractionType.MOVE, {"delta": [1.0, 0.0, 0.0], "absolute": "yes please"})


def test_scale_requires_factor():
    assert validate(InteractionType.SCALE, {"factor": 1.25}).factor == 1.25
    with pytest.raises(ValueError):
        validate(InteractionType.SCALE, {})


def test_change_color_params_strict_extra():
    ok = validate(InteractionType.CHANGE_COLOR, {"target": "material", "hex": "#ff00aa"})
    assert ok.hex == "#ff00aa"
    with pytest.raises(ValueError):
        validate(InteractionType.CHANGE_COLOR, {"target": "material", "hex": "#ff00aa", "extra": 1})


def test_add_camera_params():
    ok = validate(InteractionType.ADD_CAMERA, {
        "shot_type": "custom", "position": [0, 1, 2], "target": [0, 0, 0],
        "focal_length_mm": 35.0, "aspect_ratio": "16:9", "resolution_px": [1280, 720],
    })
    assert ok.resolution_px == [1280, 720]


def test_nl_edit_params_pass_through():
    ok = validate(InteractionType.NL_EDIT, {"text": "move the bottle left"})
    assert ok.text == "move the bottle left"
