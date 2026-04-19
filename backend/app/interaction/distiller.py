"""Pipeline C — Distiller. Reads recent :Interaction events and emits/updates
:PreferenceSignal nodes per brand.

Thresholds & rules per PIPELINE_C_INTERACTION_LEARNING.md:
  - Repeats ≥ 3 similar events → raise signal
  - Each compatible repeat raises weight by +0.15 (capped at 1.0)
  - Each ignored suggestion (opposite edit) decays weight by -0.1
  - Signals below 0.05 are soft-deleted (superseded)
  - Hard bound per brand: max(N_signals) = 32; oldest-lowest pruned
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.database.neo4j_v2 import neo4j_v2
from app.schema_v2 import InteractionType

logger = logging.getLogger(__name__)

_REPEAT_THRESHOLD = 3
_WEIGHT_INCREMENT = 0.15
_WEIGHT_DECREMENT = 0.10
_WEIGHT_MIN = 0.05
_WEIGHT_CAP = 1.0
_MAX_SIGNALS_PER_BRAND = 32


def distill_for_brand(brand_id: str, recent_interaction_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Aggregate recent interactions into preference signals.

    Called after every apply() in foreground (cheap). Also safe to run on a cron.
    """
    # Pull last N interactions on scenes owned by brand_id.
    rows = neo4j_v2.run(
        """
        MATCH (b:Brand {id: $bid})-[:OWNS_SCENE]->(s:Scene)<-[:MODIFIED*0..2]-(i:Interaction)
        RETURN i
        UNION
        MATCH (b:Brand {id: $bid})-[:OWNS_SCENE]->(s:Scene)-[:HAS_PLACEMENT|HAS_LIGHT|HAS_TEXT_LAYER|HAS_CAMERA|HAS_TERRAIN]->(t)
        <-[:MODIFIED]-(i:Interaction)
        RETURN i
        """,
        bid=brand_id,
    )
    interactions = [r["i"] for r in rows if r.get("i")]
    if recent_interaction_ids:
        ids = set(recent_interaction_ids)
        interactions = [i for i in interactions if i.get("id") in ids] or interactions
    if not interactions:
        return {"brand_id": brand_id, "created": [], "updated": [], "decayed": [], "pruned": []}

    # Bucket by (signal_kind, key). Signal kinds:
    #   - color.material_preferred_hex
    #   - color.text_preferred_hex
    #   - composition.product_x_bias (continuous)
    #   - composition.product_y_bias
    #   - composition.product_z_bias
    #   - lighting.intensity_preferred
    #   - lighting.temp_preferred
    buckets: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    opposing: Dict[Tuple[str, str], int] = defaultdict(int)

    for i in interactions:
        for bucket_key, evidence in _extract_signals(i):
            buckets[bucket_key].append(evidence)
        for ob in _opposing_signals(i):
            opposing[ob] += 1

    existing = {s.get("name"): s for s in neo4j_v2.get_active_preferences(brand_id, min_weight=0.0)}
    created: List[str] = []
    updated: List[str] = []
    decayed: List[str] = []

    for (kind, key), items in buckets.items():
        if len(items) < _REPEAT_THRESHOLD:
            continue
        name = f"{kind}:{key}"
        consolidated_value = _consolidate(kind, items)
        if name in existing:
            current = existing[name]
            w = min(_WEIGHT_CAP, float(current.get("weight", 0.0)) + _WEIGHT_INCREMENT)
            neo4j_v2.pipeline_c_write_preference_signal(brand_id, {
                "name": name,
                "kind": kind.split(".")[0],
                "value_json": json.dumps(consolidated_value),
                "weight": w,
                "source_count": int(current.get("source_count", 0)) + len(items),
                "last_reinforced_at": _now(),
                "superseded_by_id": "",
                "description": f"learned from {len(items)} recent interactions",
            })
            updated.append(name)
        else:
            neo4j_v2.pipeline_c_write_preference_signal(brand_id, {
                "name": name,
                "kind": kind.split(".")[0],
                "value_json": json.dumps(consolidated_value),
                "weight": min(_WEIGHT_CAP, _WEIGHT_INCREMENT * len(items)),
                "source_count": len(items),
                "last_reinforced_at": _now(),
                "superseded_by_id": "",
                "description": f"formed from {len(items)} repeated interactions",
            })
            created.append(name)

    # Apply decay for opposing edits.
    for (kind, key), count in opposing.items():
        name = f"{kind}:{key}"
        if name in existing:
            w = float(existing[name].get("weight", 0.0)) - _WEIGHT_DECREMENT * count
            if w < _WEIGHT_MIN:
                decayed.append(name)
                neo4j_v2.delete_preference(brand_id, existing[name]["id"])
            else:
                neo4j_v2.update_node_fields("PreferenceSignal", existing[name]["id"], {"weight": w})

    pruned = _enforce_bound(brand_id)
    return {"brand_id": brand_id, "created": created, "updated": updated, "decayed": decayed, "pruned": pruned}


# ---------------------------------------------------------------------------
# Signal extraction
# ---------------------------------------------------------------------------


def _extract_signals(interaction: Dict[str, Any]) -> List[Tuple[Tuple[str, str], Dict[str, Any]]]:
    """Return list of (bucket_key, evidence) pairs from an interaction."""
    action = interaction.get("action")
    post_raw = interaction.get("post_state_json") or "{}"
    try:
        post = json.loads(post_raw) if isinstance(post_raw, str) else post_raw
    except Exception:
        post = {}

    signals: List[Tuple[Tuple[str, str], Dict[str, Any]]] = []

    if action == InteractionType.CHANGE_COLOR.value:
        hex_val = post.get("albedo_dominant_hex") or post.get("color_hex")
        if hex_val:
            channel = "material" if "albedo" in json.dumps(post) else "text"
            signals.append((("color.preferred_hex", channel), {"hex": hex_val}))

    elif action == InteractionType.MOVE.value:
        pos = post.get("position")
        if isinstance(pos, list) and len(pos) == 3:
            # Store each axis as a continuous bias.
            for axis, idx in (("x", 0), ("y", 1), ("z", 2)):
                signals.append((("composition.product_bias", axis), {"value": pos[idx]}))

    elif action == InteractionType.CHANGE_LIGHT.value:
        if "intensity" in post:
            signals.append((("lighting.intensity_preferred", "scalar"), {"value": post["intensity"]}))
        if "color_temp_k" in post:
            signals.append((("lighting.temp_preferred", "kelvin"), {"value": post["color_temp_k"]}))

    return signals


def _opposing_signals(interaction: Dict[str, Any]) -> List[Tuple[str, str]]:
    # An interaction that *undoes* a previous signal decays that signal.
    # MVP implementation: an EDIT_TEXT or CHANGE_COLOR that sets an explicitly
    # different value counts as "opposing" nothing yet — full logic deferred to
    # Week 13 per IMPLEMENTATION_ROADMAP.md.
    return []


# ---------------------------------------------------------------------------
# Consolidation
# ---------------------------------------------------------------------------


def _consolidate(kind: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    if "color.preferred_hex" in kind:
        # Pick the modal hex; ties broken by most recent.
        counts: Dict[str, int] = defaultdict(int)
        for it in items:
            counts[it["hex"]] += 1
        best = max(counts.items(), key=lambda kv: kv[1])[0]
        return {"hex": best, "support": counts[best], "sample_size": len(items)}
    if "composition.product_bias" in kind:
        values = [float(it.get("value", 0.0)) for it in items]
        # Mean with clamping.
        mean = sum(values) / len(values)
        return {"value": round(max(-5.0, min(5.0, mean)), 4), "sample_size": len(items)}
    if "lighting.intensity_preferred" in kind:
        values = [float(it.get("value", 1.0)) for it in items]
        mean = sum(values) / len(values)
        return {"value": round(max(0.0, min(5.0, mean)), 3), "sample_size": len(items)}
    if "lighting.temp_preferred" in kind:
        values = [float(it.get("value", 5600)) for it in items]
        mean = sum(values) / len(values)
        return {"value": int(max(1500, min(10000, mean))), "sample_size": len(items)}
    return {"sample_size": len(items)}


def _enforce_bound(brand_id: str) -> List[str]:
    all_sigs = neo4j_v2.get_active_preferences(brand_id, min_weight=0.0)
    if len(all_sigs) <= _MAX_SIGNALS_PER_BRAND:
        return []
    sorted_sigs = sorted(all_sigs, key=lambda s: (float(s.get("weight", 0.0)),
                                                   s.get("last_reinforced_at") or s.get("created_at") or ""))
    to_prune = sorted_sigs[: len(all_sigs) - _MAX_SIGNALS_PER_BRAND]
    pruned_names = []
    for s in to_prune:
        neo4j_v2.delete_preference(brand_id, s["id"])
        pruned_names.append(s.get("name", s["id"]))
    return pruned_names


def _now() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat()
