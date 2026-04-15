"""
ComfyUI custom node scaffold for research controls.

This module provides first-pass implementations of the planned research nodes
using ComfyUI-compatible class signatures.
"""

from __future__ import annotations

from typing import Dict, List, Tuple
import json
import math


def _parse_csv(raw: str) -> List[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _hex_to_rgb(hex_color: str) -> Tuple[float, float, float]:
    value = hex_color.strip().lstrip("#")
    if len(value) != 6:
        return (0.0, 0.0, 0.0)
    return (
        int(value[0:2], 16) / 255.0,
        int(value[2:4], 16) / 255.0,
        int(value[4:6], 16) / 255.0,
    )


class GraphConditionerNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "brand_id": ("STRING", {"default": "brand_001"}),
                "palette_hex": ("STRING", {"default": "#FF6A4D,#1F2937"}),
                "style_keywords": ("STRING", {"default": "premium,editorial"}),
                "w_color": ("FLOAT", {"default": 0.35, "min": 0.0, "max": 1.0, "step": 0.01}),
                "w_layout": ("FLOAT", {"default": 0.25, "min": 0.0, "max": 1.0, "step": 0.01}),
                "w_identity": ("FLOAT", {"default": 0.20, "min": 0.0, "max": 1.0, "step": 0.01}),
                "w_text": ("FLOAT", {"default": 0.20, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("STRING", "FLOAT")
    RETURN_NAMES = ("conditioning_json", "confidence")
    FUNCTION = "build"
    CATEGORY = "Research/Graph"

    def build(
        self,
        brand_id: str,
        palette_hex: str,
        style_keywords: str,
        w_color: float,
        w_layout: float,
        w_identity: float,
        w_text: float,
    ):
        palette = _parse_csv(palette_hex)
        styles = _parse_csv(style_keywords)

        weights = {
            "w_color": max(w_color, 0.0),
            "w_layout": max(w_layout, 0.0),
            "w_identity": max(w_identity, 0.0),
            "w_text": max(w_text, 0.0),
        }
        total = sum(weights.values())
        if total <= 1e-9:
            weights = {"w_color": 0.0, "w_layout": 0.0, "w_identity": 0.0, "w_text": 1.0}
        else:
            weights = {k: round(v / total, 6) for k, v in weights.items()}

        confidence = _clamp(
            (0.5 if palette else 0.0)
            + (0.3 * min(len(styles) / 4.0, 1.0))
            + 0.2,
            0.0,
            1.0,
        )

        payload = {
            "brand_id": brand_id,
            "palette_hex": palette,
            "style_keywords": styles,
            "constraint_weight_map": weights,
            "confidence": round(confidence, 6),
        }
        return (json.dumps(payload), float(round(confidence, 6)))


class DynamicCFGSchedulerNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_cfg": ("FLOAT", {"default": 7.5, "min": 1.0, "max": 20.0, "step": 0.1}),
                "step": ("INT", {"default": 20, "min": 0, "max": 200}),
                "total_steps": ("INT", {"default": 30, "min": 2, "max": 300}),
                "confidence": ("FLOAT", {"default": 0.75, "min": 0.0, "max": 1.0, "step": 0.01}),
                "alpha_max": ("FLOAT", {"default": 0.35, "min": 0.0, "max": 2.0, "step": 0.01}),
                "gamma": ("FLOAT", {"default": 1.6, "min": 0.5, "max": 4.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("FLOAT", "FLOAT")
    RETURN_NAMES = ("cfg_t", "alpha_t")
    FUNCTION = "schedule"
    CATEGORY = "Research/Graph"

    def schedule(
        self,
        base_cfg: float,
        step: int,
        total_steps: int,
        confidence: float,
        alpha_max: float,
        gamma: float,
    ):
        progress = _clamp(step / max(total_steps - 1, 1), 0.0, 1.0)
        alpha_t = alpha_max * (progress ** gamma)
        cfg_t = _clamp(base_cfg * (1.0 + alpha_t * (0.75 + 0.5 * confidence)), 1.0, 20.0)
        return (float(round(cfg_t, 6)), float(round(alpha_t, 6)))


class PaletteRegularizerNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "generated_palette": ("STRING", {"default": "#E56A4D,#2A2D3F"}),
                "target_palette": ("STRING", {"default": "#FF6A4D,#1F2937"}),
                "pass_threshold": ("FLOAT", {"default": 0.12, "min": 0.0, "max": 2.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("FLOAT", "FLOAT", "STRING")
    RETURN_NAMES = ("delta_proxy", "pass_rate", "details_json")
    FUNCTION = "regularize"
    CATEGORY = "Research/Color"

    def regularize(self, generated_palette: str, target_palette: str, pass_threshold: float):
        gen = _parse_csv(generated_palette)
        tgt = _parse_csv(target_palette)
        if not gen or not tgt:
            details = {"comparisons": 0, "note": "missing palette inputs"}
            return (0.0, 0.0, json.dumps(details))

        deltas: List[float] = []
        for g in gen:
            gr, gg, gb = _hex_to_rgb(g)
            best = 999.0
            for t in tgt:
                tr, tg, tb = _hex_to_rgb(t)
                d = math.sqrt(((gr - tr) ** 2) + ((gg - tg) ** 2) + ((gb - tb) ** 2))
                best = min(best, d)
            deltas.append(best)

        mean_delta = sum(deltas) / len(deltas)
        pass_rate = len([d for d in deltas if d <= pass_threshold]) / len(deltas)
        details = {
            "comparisons": len(deltas),
            "threshold": pass_threshold,
            "deltas": [round(d, 6) for d in deltas],
        }
        return (float(round(mean_delta, 6)), float(round(pass_rate, 6)), json.dumps(details))


class LayoutConstraintNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "centroid_x": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.001}),
                "centroid_y": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.001}),
                "expected_layout": ("STRING", {"default": "centered"}),
            }
        }

    RETURN_TYPES = ("FLOAT", "STRING")
    RETURN_NAMES = ("layout_score", "details_json")
    FUNCTION = "score"
    CATEGORY = "Research/Layout"

    def score(self, centroid_x: float, centroid_y: float, expected_layout: str):
        targets = {
            "centered": (0.5, 0.5),
            "left": (0.35, 0.5),
            "right": (0.65, 0.5),
            "top": (0.5, 0.35),
            "bottom": (0.5, 0.65),
        }
        tx, ty = targets.get(expected_layout, targets["centered"])
        distance = math.sqrt(((centroid_x - tx) ** 2) + ((centroid_y - ty) ** 2))
        score = _clamp(1.0 - (1.35 * (distance / math.sqrt(2.0))), 0.0, 1.0)
        details = {
            "expected_layout": expected_layout,
            "target": [tx, ty],
            "centroid": [centroid_x, centroid_y],
            "distance": distance,
        }
        return (float(round(score, 6)), json.dumps(details))


class IdentityLockNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "identity_similarity": ("FLOAT", {"default": 0.75, "min": 0.0, "max": 1.0, "step": 0.001}),
                "threshold": ("FLOAT", {"default": 0.70, "min": 0.0, "max": 1.0, "step": 0.001}),
            }
        }

    RETURN_TYPES = ("FLOAT", "BOOLEAN")
    RETURN_NAMES = ("identity_score", "passed")
    FUNCTION = "enforce"
    CATEGORY = "Research/Identity"

    def enforce(self, identity_similarity: float, threshold: float):
        score = _clamp(identity_similarity, 0.0, 1.0)
        passed = score >= threshold
        return (float(round(score, 6)), bool(passed))


class ConstraintViolationCheckerNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "layout_score": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 1.0}),
                "identity_score": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 1.0}),
                "text_legibility_score": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 1.0}),
                "minimum_threshold": ("FLOAT", {"default": 0.65, "min": 0.0, "max": 1.0}),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("passed", "violation_report")
    FUNCTION = "check"
    CATEGORY = "Research/Validation"

    def check(self, layout_score: float, identity_score: float, text_legibility_score: float, minimum_threshold: float):
        violations: Dict[str, float] = {}
        if layout_score < minimum_threshold:
            violations["layout_score"] = layout_score
        if identity_score < minimum_threshold:
            violations["identity_score"] = identity_score
        if text_legibility_score < minimum_threshold:
            violations["text_legibility_score"] = text_legibility_score

        payload = {
            "minimum_threshold": minimum_threshold,
            "violations": violations,
        }
        return (len(violations) == 0, json.dumps(payload))


class FeedbackWeightAdapterNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "w_color": ("FLOAT", {"default": 0.35, "min": 0.0, "max": 1.0}),
                "w_layout": ("FLOAT", {"default": 0.25, "min": 0.0, "max": 1.0}),
                "w_identity": ("FLOAT", {"default": 0.20, "min": 0.0, "max": 1.0}),
                "w_text": ("FLOAT", {"default": 0.20, "min": 0.0, "max": 1.0}),
                "feedback_score": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0}),
                "adapt_rate": ("FLOAT", {"default": 0.15, "min": 0.0, "max": 1.0}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("updated_weight_json",)
    FUNCTION = "adapt"
    CATEGORY = "Research/Feedback"

    def adapt(
        self,
        w_color: float,
        w_layout: float,
        w_identity: float,
        w_text: float,
        feedback_score: float,
        adapt_rate: float,
    ):
        weights = {
            "w_color": max(w_color, 0.0),
            "w_layout": max(w_layout, 0.0),
            "w_identity": max(w_identity, 0.0),
            "w_text": max(w_text, 0.0),
        }

        # Positive feedback reinforces current distribution; low feedback rebalances toward layout and text.
        if feedback_score < 0.5:
            weights["w_layout"] += adapt_rate * (0.5 - feedback_score)
            weights["w_text"] += adapt_rate * (0.5 - feedback_score)
        else:
            weights["w_color"] += adapt_rate * (feedback_score - 0.5)
            weights["w_identity"] += adapt_rate * (feedback_score - 0.5)

        total = sum(weights.values())
        if total <= 1e-9:
            normalized = {"w_color": 0.35, "w_layout": 0.25, "w_identity": 0.20, "w_text": 0.20}
        else:
            normalized = {k: round(v / total, 6) for k, v in weights.items()}

        return (json.dumps(normalized),)


class MultiSeedEvaluatorNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed_list": ("STRING", {"default": "11,22,33"}),
                "score_list": ("STRING", {"default": "0.62,0.75,0.71"}),
            }
        }

    RETURN_TYPES = ("INT", "FLOAT", "STRING")
    RETURN_NAMES = ("best_seed", "best_score", "table_json")
    FUNCTION = "select"
    CATEGORY = "Research/Eval"

    def select(self, seed_list: str, score_list: str):
        seeds = [int(s) for s in _parse_csv(seed_list)]
        scores = [float(s) for s in _parse_csv(score_list)]

        if not seeds or not scores or len(seeds) != len(scores):
            return (0, 0.0, json.dumps({"rows": [], "error": "invalid seed/score inputs"}))

        rows = [{"seed": seed, "score": score} for seed, score in zip(seeds, scores)]
        best = max(rows, key=lambda row: row["score"])
        return (int(best["seed"]), float(best["score"]), json.dumps({"rows": rows}))
