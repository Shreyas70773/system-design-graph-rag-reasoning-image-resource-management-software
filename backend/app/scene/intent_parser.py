"""Pipeline B Stage 1 — Intent parser.

Tries Groq Llama 3.3 if `GROQ_API_KEY` is set; otherwise uses a rule-based
parser that extracts a usable scene-graph from keyword patterns. Both paths
return strictly-validated `SceneGraphSpec` instances.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Dict, List

from app.schema_v2 import (
    CameraSpec,
    LightSpec,
    PlacementSpec,
    SceneGraphSpec,
    TerrainSpec,
    TextLayerSpec,
)

logger = logging.getLogger(__name__)

_POSITION_KEYWORDS = {
    "center": "center", "middle": "center",
    "left": "left-third", "right": "right-third",
    "foreground": "foreground", "background": "background",
}

_MOOD_KEYWORDS = {
    "golden hour": "golden-hour", "sunset": "golden-hour", "sunrise": "golden-hour",
    "overcast": "overcast", "cloudy": "overcast",
    "studio": "studio", "clean": "studio",
    "high key": "high-key", "bright": "high-key",
    "moody": "moody", "dramatic": "moody", "dark": "moody",
}

_TERRAIN_KEYWORDS = {
    "beach": "sand", "sand": "sand", "desert": "sand",
    "grass": "grass", "lawn": "grass", "park": "grass",
    "concrete": "concrete", "street": "concrete", "studio": "concrete",
    "water": "water", "pool": "water", "ocean": "water",
}


def parse_intent(brief: str, brand_id: str, deployment_context: str,
                 camera_requests: List[Dict] | None = None) -> SceneGraphSpec:
    """Parse a user brief into a strict SceneGraphSpec.

    `camera_requests`, when provided by the caller (frontend or API), is the
    authoritative list of cameras and always overrides whatever the LLM
    produces — the UI is the source of truth for camera slots. The LLM is
    used for placement / mood / text-layer extraction even when cameras are
    explicit.
    """
    spec: SceneGraphSpec
    parser = _try_groq if os.environ.get("GROQ_API_KEY") else None
    if parser:
        try:
            spec = parser(brief, brand_id, deployment_context, camera_requests)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Groq intent parse failed (%s); falling back to rule-based", exc)
            spec = _rule_based(brief, brand_id, deployment_context, camera_requests)
    else:
        spec = _rule_based(brief, brand_id, deployment_context, camera_requests)

    if camera_requests:
        spec = spec.model_copy(update={"cameras": [
            CameraSpec(
                shot_type=c.get("shot_type", "hero"),
                aspect_ratio=c.get("aspect_ratio", "1:1"),
            ) for c in camera_requests
        ]})
    return spec


def _rule_based(brief: str, brand_id: str, deployment_context: str,
                camera_requests: List[Dict] | None) -> SceneGraphSpec:
    text = brief.lower()
    placements: List[PlacementSpec] = [
        PlacementSpec(
            asset_id=None,
            asset_query="hero_product",
            role="hero",
            position_hint=_pick(text, _POSITION_KEYWORDS, "center"),
            z_order=1,
        ),
    ]

    mood = _pick(text, _MOOD_KEYWORDS, "studio")
    cameras: List[CameraSpec] = []
    if camera_requests:
        for c in camera_requests:
            cameras.append(CameraSpec(
                shot_type=c.get("shot_type", "hero"),
                aspect_ratio=c.get("aspect_ratio", "1:1"),
            ))
    else:
        cameras.append(CameraSpec(shot_type="hero", aspect_ratio="1:1"))

    lights = [LightSpec(mood=mood, direction_hint="upper-left")]

    terrain = None
    terrain_type = _pick(text, _TERRAIN_KEYWORDS, "none")
    if terrain_type != "none":
        terrain = TerrainSpec(type=terrain_type, extent_m=[10.0, 10.0])

    text_layers: List[TextLayerSpec] = []
    for tagline in _extract_quoted(brief):
        text_layers.append(TextLayerSpec(text=tagline, position_hint="bottom-center", role="headline"))

    return SceneGraphSpec(
        scene_id=str(uuid.uuid4()),
        brand_id=brand_id,
        deployment_context=deployment_context,  # type: ignore[arg-type]
        placements=placements,
        cameras=cameras,
        lights=lights,
        terrain=terrain,
        text_layers=text_layers,
    )


def _pick(text: str, mapping: Dict[str, str], default: str) -> str:
    for k, v in mapping.items():
        if k in text:
            return v
    return default


def _extract_quoted(text: str) -> List[str]:
    return re.findall(r"[\"']([^\"']{3,80})[\"']", text)


def _try_groq(brief: str, brand_id: str, deployment_context: str,
              camera_requests: List[Dict] | None) -> SceneGraphSpec:
    from openai import OpenAI  # Groq is OpenAI-compatible
    client = OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")
    from pathlib import Path
    prompt_path = Path(__file__).resolve().parent / "prompts" / "parser.txt"
    system = prompt_path.read_text(encoding="utf-8").replace("{{BRIEF}}", brief)

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": brief}],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    data = json.loads(raw)
    data["scene_id"] = str(uuid.uuid4())
    data["brand_id"] = brand_id
    data["deployment_context"] = deployment_context
    # Validate with Pydantic — raises on malformed output.
    return SceneGraphSpec.model_validate(data)
