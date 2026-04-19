"""Pipeline C — Retrieval-bias compiler.

Turns active :PreferenceSignal nodes into scalar modifiers consumed by the
scene assembler (Pipeline B Stage 3). Bounded by hard caps so an aggressive
learning loop cannot run off the rails (Risk R-5 in RISK_REGISTER.md).
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

# Absolute max magnitudes applied to scene state.
_MAX_POSITION_BIAS_M = 1.5
_MAX_LIGHT_INTENSITY_MULT = 0.3   # ±30 %
_MAX_COLOR_TEMP_BIAS_K = 800
_BRAND_COLOR_NUDGE_STRENGTH = 0.25  # unused here; consumed by color grader


def compile_biases(signals: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Aggregate signals into grouped modifiers.

    Returns e.g.::

      {
        "composition": {"product_x_bias": 0.4, "product_y_bias": -0.2, "product_z_bias": 0.0},
        "lighting":    {"intensity_multiplier": 0.12, "color_temp_bias": 300},
        "palette":     {"preferred_material_hex": "#d62828", "preferred_text_hex": "#111111"},
      }
    """
    composition = {"product_x_bias": 0.0, "product_y_bias": 0.0, "product_z_bias": 0.0}
    lighting = {"intensity_multiplier": 0.0, "color_temp_bias": 0.0}
    palette = {"preferred_material_hex": None, "preferred_text_hex": None}

    for s in signals or []:
        name = s.get("name") or ""
        weight = float(s.get("weight", 0.0))
        if weight <= 0:
            continue
        value = _parse_value(s.get("value_json"))
        if not value:
            continue
        if name.startswith("composition.product_bias:x"):
            composition["product_x_bias"] += float(value.get("value", 0.0)) * weight
        elif name.startswith("composition.product_bias:y"):
            composition["product_y_bias"] += float(value.get("value", 0.0)) * weight
        elif name.startswith("composition.product_bias:z"):
            composition["product_z_bias"] += float(value.get("value", 0.0)) * weight
        elif name.startswith("lighting.intensity_preferred"):
            # value is absolute intensity; treat as relative delta from 1.0
            delta = (float(value.get("value", 1.0)) - 1.0) * weight
            lighting["intensity_multiplier"] += delta
        elif name.startswith("lighting.temp_preferred"):
            delta = (float(value.get("value", 5600)) - 5600.0) * weight
            lighting["color_temp_bias"] += delta
        elif name.startswith("color.preferred_hex:material"):
            palette["preferred_material_hex"] = value.get("hex")
        elif name.startswith("color.preferred_hex:text"):
            palette["preferred_text_hex"] = value.get("hex")

    # Clamp.
    for k in composition:
        composition[k] = max(-_MAX_POSITION_BIAS_M, min(_MAX_POSITION_BIAS_M, composition[k]))
    lighting["intensity_multiplier"] = max(-_MAX_LIGHT_INTENSITY_MULT,
                                           min(_MAX_LIGHT_INTENSITY_MULT, lighting["intensity_multiplier"]))
    lighting["color_temp_bias"] = max(-_MAX_COLOR_TEMP_BIAS_K,
                                       min(_MAX_COLOR_TEMP_BIAS_K, lighting["color_temp_bias"]))

    return {"composition": composition, "lighting": lighting, "palette": palette}


def _parse_value(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return {}
