"""Pipeline C — Natural-language edit resolution.

Two parsers:
  * VLM (Qwen2.5-VL on the most recent render + user text) — real path
  * Heuristic regex parser — fallback

Both return a `StructuredEditCommand` or `None`. A confidence score below the
threshold routes the request to the clarification UI (AC-5).
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from app.schema_v2 import EditTargetKind, InteractionType, StructuredEditCommand

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.60


class Resolution(StructuredEditCommand):
    confidence: float = 0.0
    via: str = "heuristic"


def resolve(text: str, *, scene_id: str, selected_placement_ids: List[str] | None = None,
            selected_text_ids: List[str] | None = None,
            last_render_url: Optional[str] = None) -> Resolution:
    # Heuristic pass (fast + deterministic) → always runs; establishes a baseline.
    heuristic = _heuristic(text, selected_placement_ids or [], selected_text_ids or [])
    if heuristic and heuristic.confidence >= CONFIDENCE_THRESHOLD:
        return heuristic

    # Real VLM path is only attempted in non-mock mode.
    try:
        vlm = _try_vlm(text, last_render_url, selected_placement_ids, selected_text_ids)
        if vlm and vlm.confidence > (heuristic.confidence if heuristic else 0.0):
            return vlm
    except Exception as exc:
        logger.debug("VLM parse unavailable (%s); using heuristic", exc)

    if heuristic:
        return heuristic
    # Give a placeholder low-confidence command so the UI can prompt for clarification.
    return Resolution(
        action=InteractionType.NL_EDIT,
        target_kind=EditTargetKind.SCENE,
        target_id=scene_id,
        params={"text": text},
        rerender_cameras=[],
        confidence=0.0,
        via="none",
    )


# ---------------------------------------------------------------------------
# Heuristic parser
# ---------------------------------------------------------------------------

_MOVE_WORDS = {
    "left": [-0.5, 0.0, 0.0],
    "right": [0.5, 0.0, 0.0],
    "up": [0.0, 0.5, 0.0],
    "down": [0.0, -0.5, 0.0],
    "forward": [0.0, 0.0, 0.5],
    "back": [0.0, 0.0, -0.5],
    "backward": [0.0, 0.0, -0.5],
}

_COLOR_WORDS = {
    "red": "#d33838", "blue": "#3872d3", "green": "#3cc85b", "yellow": "#f5d93b",
    "white": "#ffffff", "black": "#111111", "orange": "#f08000", "purple": "#8a3cb7",
    "pink": "#ff7ab3", "grey": "#808080", "gray": "#808080", "teal": "#20a6a6",
    "gold": "#c9a13a", "silver": "#c0c0c0",
}


def _heuristic(text: str, sel_place: List[str], sel_text: List[str]) -> Optional[Resolution]:
    t = text.lower().strip()

    # DELETE
    if re.search(r"\b(delete|remove|get rid of|erase)\b", t):
        if sel_place:
            return Resolution(
                action=InteractionType.DELETE,
                target_kind=EditTargetKind.PLACEMENT,
                target_id=sel_place[0],
                params={},
                confidence=0.85,
                rerender_cameras=[],
                via="heuristic",
            )
        if sel_text:
            return Resolution(
                action=InteractionType.DELETE_TEXT,
                target_kind=EditTargetKind.TEXT_LAYER,
                target_id=sel_text[0],
                params={},
                confidence=0.85,
                rerender_cameras=[],
                via="heuristic",
            )

    # MOVE
    for word, delta in _MOVE_WORDS.items():
        if re.search(rf"\b(move|shift|nudge)\b.*\b{word}\b", t) or re.search(rf"\b{word}\b.*\b(move|shift)\b", t):
            if sel_place:
                return Resolution(
                    action=InteractionType.MOVE,
                    target_kind=EditTargetKind.PLACEMENT,
                    target_id=sel_place[0],
                    params={"delta": delta, "absolute": False},
                    confidence=0.82,
                    rerender_cameras=[],
                    via="heuristic",
                )

    # COLOR CHANGE (text or material)
    hex_match = re.search(r"#([0-9a-f]{6})", t)
    color_word = next((w for w in _COLOR_WORDS if re.search(rf"\b{w}\b", t)), None)
    color_hex = f"#{hex_match.group(1)}" if hex_match else (_COLOR_WORDS[color_word] if color_word else None)

    if color_hex and re.search(r"\b(color|colour|recolou?r|paint|make)\b", t):
        if sel_text:
            return Resolution(
                action=InteractionType.CHANGE_COLOR,
                target_kind=EditTargetKind.TEXT_LAYER,
                target_id=sel_text[0],
                params={"target": "text_layer", "hex": color_hex},
                confidence=0.78,
                rerender_cameras=[],
                via="heuristic",
            )
        if sel_place:
            return Resolution(
                action=InteractionType.CHANGE_COLOR,
                target_kind=EditTargetKind.MATERIAL,
                target_id=sel_place[0],  # applier will resolve to material
                params={"target": "material", "hex": color_hex},
                confidence=0.75,
                rerender_cameras=[],
                via="heuristic",
            )

    # SCALE
    sm = re.search(r"\b(bigger|larger|scale up)\b", t)
    if sm and sel_place:
        return Resolution(
            action=InteractionType.SCALE,
            target_kind=EditTargetKind.PLACEMENT,
            target_id=sel_place[0],
            params={"factor": 1.25},
            confidence=0.7, rerender_cameras=[], via="heuristic",
        )
    sm = re.search(r"\b(smaller|shrink|scale down)\b", t)
    if sm and sel_place:
        return Resolution(
            action=InteractionType.SCALE,
            target_kind=EditTargetKind.PLACEMENT,
            target_id=sel_place[0],
            params={"factor": 0.8},
            confidence=0.7, rerender_cameras=[], via="heuristic",
        )

    # EDIT TEXT (set copy) — match against ORIGINAL text to preserve user casing.
    em = re.search(
        r"""change\s+(?:the\s+)?(?:text|copy)\s+to\s+["'](.+?)["']""",
        text,
        re.IGNORECASE,
    )
    if em and sel_text:
        return Resolution(
            action=InteractionType.EDIT_TEXT,
            target_kind=EditTargetKind.TEXT_LAYER,
            target_id=sel_text[0],
            params={"text": em.group(1)},
            confidence=0.88, rerender_cameras=[], via="heuristic",
        )

    return None


def _try_vlm(text: str, last_render_url: Optional[str],
             sel_place: List[str] | None, sel_text: List[str] | None) -> Optional[Resolution]:
    # VLM parsing is expensive; only attempted when a render is available
    # and deps are installed. Returns None on any failure so heuristic wins.
    from app.rendering.capabilities import detect
    caps = detect()
    if not (caps.transformers and caps.torch_cuda and last_render_url):
        return None
    # Deliberately not wired for MVP; scaffolding only.
    return None
