"""
Graph-conditioning runtime services.

These services provide a backend-operational bridge between Brand DNA context
and controlled generation parameters used during research runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import math


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _hex_to_rgb01(hex_color: str) -> Optional[List[float]]:
    try:
        value = hex_color.strip().lstrip("#")
        if len(value) != 6:
            return None

        r = int(value[0:2], 16) / 255.0
        g = int(value[2:4], 16) / 255.0
        b = int(value[4:6], 16) / 255.0
        return [r, g, b]
    except Exception:
        return None


@dataclass
class GraphConditioningPacket:
    """Structured packet used to condition downstream generation logic."""

    brand_id: str
    method_name: str
    palette_hex: List[str] = field(default_factory=list)
    palette_vector: List[float] = field(default_factory=list)
    style_keywords: List[str] = field(default_factory=list)
    constraint_weight_map: Dict[str, float] = field(default_factory=dict)
    layout_priors: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    retrieval_quality: float = 0.0
    product_reference_url: Optional[str] = None
    character_reference_url: Optional[str] = None
    notes: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "brand_id": self.brand_id,
            "method_name": self.method_name,
            "palette_hex": self.palette_hex,
            "palette_vector": self.palette_vector,
            "style_keywords": self.style_keywords,
            "constraint_weight_map": self.constraint_weight_map,
            "layout_priors": self.layout_priors,
            "confidence": self.confidence,
            "retrieval_quality": self.retrieval_quality,
            "product_reference_url": self.product_reference_url,
            "character_reference_url": self.character_reference_url,
            "notes": self.notes,
        }


@dataclass
class CFGScheduleSnapshot:
    """One schedule point for dynamic guidance diagnostics."""

    step: int
    total_steps: int
    alpha_t: float
    cfg_scale: float

    def as_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "total_steps": self.total_steps,
            "alpha_t": self.alpha_t,
            "cfg_scale": self.cfg_scale,
        }


class GraphConditioner:
    """Convert Brand DNA context plus request params into control packet."""

    def _extract_palette(self, brand_context: Dict[str, Any], max_colors: int = 8) -> List[str]:
        seen = set()
        palette: List[str] = []

        for color in brand_context.get("colors", []):
            hex_value = str(color.get("hex", "")).strip()
            if not hex_value:
                continue
            normalized = hex_value.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            palette.append(hex_value)
            if len(palette) >= max_colors:
                break

        return palette

    def _palette_to_vector(self, palette_hex: List[str], max_colors: int = 6) -> List[float]:
        values: List[float] = []
        for hex_color in palette_hex[:max_colors]:
            rgb = _hex_to_rgb01(hex_color)
            if rgb is None:
                continue
            values.extend(rgb)

        target_len = max_colors * 3
        if len(values) < target_len:
            values.extend([0.0] * (target_len - len(values)))

        return [round(v, 6) for v in values[:target_len]]

    def _extract_style_keywords(self, brand_context: Dict[str, Any], max_keywords: int = 8) -> List[str]:
        values: List[str] = []

        for style in brand_context.get("styles", []):
            if isinstance(style, str):
                values.append(style)
            elif isinstance(style, dict):
                token = style.get("name") or style.get("value") or style.get("style")
                if token:
                    values.append(str(token))

        tagline = str(brand_context.get("tagline", "")).strip()
        if tagline:
            values.extend([part.strip() for part in tagline.split() if len(part.strip()) > 4])

        deduped: List[str] = []
        seen = set()
        for value in values:
            normalized = value.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(value)
            if len(deduped) >= max_keywords:
                break

        return deduped

    def _layout_priors(self, request: Dict[str, Any], method_name: str) -> Dict[str, float]:
        layout = str(request.get("layout", "centered"))
        text_position = str(request.get("text_position", "bottom"))
        toggles = request.get("module_toggles") or {}

        # Priors can be consumed by workflow nodes or downstream diagnostics.
        priors = {
            "center_bias": 1.0 if layout == "centered" else 0.6,
            "left_bias": 1.0 if layout in {"left", "left_focus"} else 0.3,
            "right_bias": 1.0 if layout in {"right", "right_focus"} else 0.3,
            "top_text_zone": 1.0 if text_position == "top" else 0.35,
            "bottom_text_zone": 1.0 if text_position == "bottom" else 0.35,
            "layout_constraint_enabled": 1.0 if toggles.get("layout_constraint", True) else 0.0,
        }

        if method_name == "prompt_only":
            priors["layout_constraint_enabled"] = 0.0

        return {k: round(float(v), 6) for k, v in priors.items()}

    def _constraint_weights(self, request: Dict[str, Any], method_name: str) -> Dict[str, float]:
        provided = request.get("constraint_weights") or {}

        weights = {
            "w_color": float(provided.get("w_color", 0.35)),
            "w_layout": float(provided.get("w_layout", 0.25)),
            "w_identity": float(provided.get("w_identity", 0.20)),
            "w_text": float(provided.get("w_text", 0.20)),
        }

        toggles = request.get("module_toggles") or {}
        if toggles.get("color_regularizer", True) is False:
            weights["w_color"] = 0.0
        if toggles.get("layout_constraint", True) is False:
            weights["w_layout"] = 0.0
        if toggles.get("identity_lock", True) is False:
            weights["w_identity"] = 0.0

        if method_name == "prompt_only":
            for key in list(weights.keys()):
                weights[key] = 0.0
            weights["w_text"] = 1.0

        total = sum(max(v, 0.0) for v in weights.values())
        if total <= 1e-9:
            return {
                "w_color": 0.0,
                "w_layout": 0.0,
                "w_identity": 0.0,
                "w_text": 1.0,
            }

        return {k: round(max(v, 0.0) / total, 6) for k, v in weights.items()}

    def build_packet(self, brand_context: Dict[str, Any], request: Dict[str, Any], method_name: str) -> GraphConditioningPacket:
        """Build graph conditioning packet for one run or candidate."""
        palette_hex = self._extract_palette(brand_context)
        palette_vector = self._palette_to_vector(palette_hex)
        style_keywords = self._extract_style_keywords(brand_context)

        selected_products = brand_context.get("selected_products", [])
        product_reference_url = None
        if selected_products and isinstance(selected_products, list):
            product_reference_url = selected_products[0].get("image_url") if selected_products[0] else None

        character_reference_url = request.get("character_reference_url")

        retrieval_quality_components = [
            1.0 if palette_hex else 0.0,
            min(len(style_keywords) / 4.0, 1.0),
            1.0 if product_reference_url else 0.0,
            1.0 if character_reference_url else 0.0,
        ]
        retrieval_quality = _clamp(sum(retrieval_quality_components) / len(retrieval_quality_components), 0.0, 1.0)

        confidence = _clamp(
            (0.45 * (1.0 if palette_hex else 0.0))
            + (0.25 * min(len(style_keywords) / 5.0, 1.0))
            + (0.20 * retrieval_quality)
            + (0.10 * (1.0 if request.get("module_toggles", {}).get("dynamic_cfg", True) else 0.5)),
            0.0,
            1.0,
        )

        return GraphConditioningPacket(
            brand_id=str(request.get("brand_id", "")),
            method_name=method_name,
            palette_hex=palette_hex,
            palette_vector=palette_vector,
            style_keywords=style_keywords,
            constraint_weight_map=self._constraint_weights(request, method_name),
            layout_priors=self._layout_priors(request, method_name),
            confidence=round(confidence, 6),
            retrieval_quality=round(retrieval_quality, 6),
            product_reference_url=product_reference_url,
            character_reference_url=character_reference_url,
            notes={
                "has_selected_products": bool(selected_products),
                "module_toggles": request.get("module_toggles", {}),
            },
        )


class DynamicCFGScheduler:
    """Adaptive CFG helper for graph-guided runs."""

    def cfg_at_step(
        self,
        base_cfg: float,
        step: int,
        total_steps: int,
        confidence: float,
        profile: str = "polynomial",
        alpha_max: float = 0.35,
        gamma: float = 1.6,
    ) -> CFGScheduleSnapshot:
        if total_steps <= 1:
            total_steps = 2

        progress = _clamp(step / float(total_steps - 1), 0.0, 1.0)
        confidence = _clamp(confidence, 0.0, 1.0)

        if profile == "linear":
            alpha_t = alpha_max * progress
        elif profile == "exponential":
            alpha_t = alpha_max * ((math.exp(progress) - 1.0) / (math.e - 1.0))
        else:
            alpha_t = alpha_max * (progress ** gamma)

        # Confidence scales how aggressively CFG rises in later steps.
        confidence_gain = 0.75 + (0.5 * confidence)
        cfg_scale = _clamp(base_cfg * (1.0 + (alpha_t * confidence_gain)), 1.0, 20.0)

        return CFGScheduleSnapshot(
            step=step,
            total_steps=total_steps,
            alpha_t=round(alpha_t, 6),
            cfg_scale=round(cfg_scale, 6),
        )

    def build_schedule_preview(
        self,
        base_cfg: float,
        total_steps: int,
        confidence: float,
        profile: str = "polynomial",
    ) -> List[Dict[str, Any]]:
        checkpoints = sorted(set([
            0,
            int((total_steps - 1) * 0.25),
            int((total_steps - 1) * 0.50),
            int((total_steps - 1) * 0.75),
            max(total_steps - 1, 0),
        ]))

        return [
            self.cfg_at_step(base_cfg, step, total_steps, confidence, profile=profile).as_dict()
            for step in checkpoints
        ]

    def effective_cfg_for_run(
        self,
        base_cfg: float,
        total_steps: int,
        confidence: float,
        dynamic_enabled: bool,
        method_name: str,
    ) -> float:
        """Compute practical single CFG value for backends that do not support per-step schedule injection."""
        if not dynamic_enabled or method_name in {"prompt_only", "retrieval_prompt"}:
            return float(base_cfg)

        target_step = int(max(total_steps - 1, 1) * 0.70)
        snapshot = self.cfg_at_step(base_cfg, target_step, total_steps, confidence)
        return float(snapshot.cfg_scale)
