"""
Research metric evaluator.
Computes measurable metrics from generated candidates and aggregates run-level summaries.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import base64
import io
import statistics
import math

import httpx
import numpy as np
from PIL import Image

from app.scraping.color_extractor import extract_colors_from_image, compare_colors
from app.generation.validator import calculate_brand_score


def _safe_mean(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return float(sum(values) / len(values))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _hex_to_rgb(hex_color: str) -> Optional[tuple[float, float, float]]:
    try:
        value = hex_color.strip().lstrip("#")
        if len(value) != 6:
            return None
        r = int(value[0:2], 16)
        g = int(value[2:4], 16)
        b = int(value[4:6], 16)
        return (float(r), float(g), float(b))
    except Exception:
        return None


def _srgb_to_linear(channel: float) -> float:
    c = channel / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _rgb_to_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    r_lin = _srgb_to_linear(rgb[0])
    g_lin = _srgb_to_linear(rgb[1])
    b_lin = _srgb_to_linear(rgb[2])

    x = (0.4124564 * r_lin) + (0.3575761 * g_lin) + (0.1804375 * b_lin)
    y = (0.2126729 * r_lin) + (0.7151522 * g_lin) + (0.0721750 * b_lin)
    z = (0.0193339 * r_lin) + (0.1191920 * g_lin) + (0.9503041 * b_lin)

    # D65 white point
    xn = 0.95047
    yn = 1.00000
    zn = 1.08883

    def f(t: float) -> float:
        threshold = 216.0 / 24389.0
        if t > threshold:
            return t ** (1.0 / 3.0)
        return ((24389.0 / 27.0) * t + 16.0) / 116.0

    fx = f(x / xn)
    fy = f(y / yn)
    fz = f(z / zn)

    l = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    return (l, a, b)


def _ciede2000(lab1: tuple[float, float, float], lab2: tuple[float, float, float]) -> float:
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2

    c1 = math.sqrt((a1 * a1) + (b1 * b1))
    c2 = math.sqrt((a2 * a2) + (b2 * b2))
    c_bar = (c1 + c2) / 2.0

    c_bar_7 = c_bar ** 7
    g = 0.5 * (1.0 - math.sqrt(c_bar_7 / (c_bar_7 + (25.0 ** 7)))) if c_bar > 0 else 0.0

    a1_prime = (1.0 + g) * a1
    a2_prime = (1.0 + g) * a2

    c1_prime = math.sqrt((a1_prime * a1_prime) + (b1 * b1))
    c2_prime = math.sqrt((a2_prime * a2_prime) + (b2 * b2))

    def hue_angle_deg(x: float, y: float) -> float:
        angle = math.degrees(math.atan2(y, x))
        return angle + 360.0 if angle < 0 else angle

    h1_prime = 0.0 if c1_prime == 0 else hue_angle_deg(a1_prime, b1)
    h2_prime = 0.0 if c2_prime == 0 else hue_angle_deg(a2_prime, b2)

    delta_l_prime = l2 - l1
    delta_c_prime = c2_prime - c1_prime

    if c1_prime == 0 or c2_prime == 0:
        delta_h_prime = 0.0
    else:
        delta_h = h2_prime - h1_prime
        if abs(delta_h) <= 180.0:
            delta_h_prime = delta_h
        elif delta_h > 180.0:
            delta_h_prime = delta_h - 360.0
        else:
            delta_h_prime = delta_h + 360.0

    delta_big_h_prime = 2.0 * math.sqrt(c1_prime * c2_prime) * math.sin(math.radians(delta_h_prime / 2.0))

    l_bar_prime = (l1 + l2) / 2.0
    c_bar_prime = (c1_prime + c2_prime) / 2.0

    if c1_prime == 0 or c2_prime == 0:
        h_bar_prime = h1_prime + h2_prime
    else:
        h_diff = abs(h1_prime - h2_prime)
        if h_diff <= 180.0:
            h_bar_prime = (h1_prime + h2_prime) / 2.0
        elif (h1_prime + h2_prime) < 360.0:
            h_bar_prime = (h1_prime + h2_prime + 360.0) / 2.0
        else:
            h_bar_prime = (h1_prime + h2_prime - 360.0) / 2.0

    t = (
        1.0
        - 0.17 * math.cos(math.radians(h_bar_prime - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * h_bar_prime))
        + 0.32 * math.cos(math.radians(3.0 * h_bar_prime + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * h_bar_prime - 63.0))
    )

    delta_theta = 30.0 * math.exp(-(((h_bar_prime - 275.0) / 25.0) ** 2))
    c_bar_prime_7 = c_bar_prime ** 7
    r_c = 2.0 * math.sqrt(c_bar_prime_7 / (c_bar_prime_7 + (25.0 ** 7))) if c_bar_prime > 0 else 0.0

    s_l = 1.0 + ((0.015 * ((l_bar_prime - 50.0) ** 2)) / math.sqrt(20.0 + ((l_bar_prime - 50.0) ** 2)))
    s_c = 1.0 + (0.045 * c_bar_prime)
    s_h = 1.0 + (0.015 * c_bar_prime * t)

    r_t = -math.sin(math.radians(2.0 * delta_theta)) * r_c

    delta_e = math.sqrt(
        (delta_l_prime / s_l) ** 2
        + (delta_c_prime / s_c) ** 2
        + (delta_big_h_prime / s_h) ** 2
        + r_t * (delta_c_prime / s_c) * (delta_big_h_prime / s_h)
    )
    return float(delta_e)


class MetricEvaluator:
    """Evaluates candidate-level and run-level research metrics."""

    async def _fetch_image_bytes(self, image_url: Optional[str]) -> Optional[bytes]:
        """Fetch image bytes from HTTP URL or data URI."""
        if not image_url:
            return None

        if image_url.startswith("data:image"):
            try:
                encoded = image_url.split(",", 1)[1]
                return base64.b64decode(encoded)
            except Exception:
                return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(image_url)
                if response.status_code == 200:
                    return response.content
        except Exception:
            return None

        return None

    def _extract_colors_from_image_bytes(self, image_bytes: Optional[bytes], max_colors: int = 5) -> List[str]:
        """Extract dominant colors from raw image bytes."""
        if not image_bytes:
            return []

        colors = extract_colors_from_image(image_bytes, color_count=max_colors)
        return [c.get("hex", "") for c in colors if c.get("hex")]

    @staticmethod
    def _center_crop_resize(image: Image.Image, size: int = 128) -> Image.Image:
        width, height = image.size
        side = min(width, height)
        left = int((width - side) / 2)
        top = int((height - side) / 2)
        crop = image.crop((left, top, left + side, top + side))
        return crop.resize((size, size), Image.Resampling.BILINEAR)

    @staticmethod
    def _rgb_hist_vector(image: Image.Image, bins: int = 16) -> np.ndarray:
        arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
        hist_parts: List[np.ndarray] = []
        for channel in range(3):
            hist, _ = np.histogram(arr[:, :, channel], bins=bins, range=(0, 256))
            hist_parts.append(hist.astype(np.float32))

        vector = np.concatenate(hist_parts)
        norm = float(np.linalg.norm(vector))
        if norm <= 1e-9:
            return vector
        return vector / norm

    async def extract_colors_from_image_url(self, image_url: Optional[str], max_colors: int = 5) -> List[str]:
        """Extract dominant color hex values from a generated image URL or data URI."""
        image_bytes = await self._fetch_image_bytes(image_url)
        return self._extract_colors_from_image_bytes(image_bytes, max_colors=max_colors)

    def compute_layout_compliance_score(self, image_bytes: Optional[bytes], expected_layout: str = "centered") -> Optional[float]:
        """
        Compute a lightweight layout proxy score from image gradient-energy centroid.

        This is a practical proxy and not a full scene-graph detector.
        """
        if not image_bytes:
            return None

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("L")
            arr = np.asarray(image, dtype=np.float32) / 255.0
            if arr.size == 0:
                return None

            grad_y, grad_x = np.gradient(arr)
            energy = np.sqrt((grad_x ** 2) + (grad_y ** 2)) + 1e-6

            h, w = energy.shape
            yy = np.arange(h, dtype=np.float32)[:, None]
            xx = np.arange(w, dtype=np.float32)[None, :]
            total = float(np.sum(energy))
            if total <= 1e-9:
                return 0.0

            centroid_x = float(np.sum(xx * energy) / total) / max(w - 1, 1)
            centroid_y = float(np.sum(yy * energy) / total) / max(h - 1, 1)

            target_map = {
                "centered": (0.5, 0.5),
                "left": (0.35, 0.5),
                "left_focus": (0.35, 0.5),
                "right": (0.65, 0.5),
                "right_focus": (0.65, 0.5),
                "top": (0.5, 0.35),
                "bottom": (0.5, 0.65),
            }
            target_x, target_y = target_map.get(expected_layout, target_map["centered"])

            distance = math.sqrt(((centroid_x - target_x) ** 2) + ((centroid_y - target_y) ** 2))
            normalized_distance = distance / math.sqrt(2.0)
            score = 1.0 - (1.35 * normalized_distance)
            return round(_clamp(score, 0.0, 1.0), 4)
        except Exception:
            return None

    def compute_text_legibility_score(self, image_bytes: Optional[bytes], text_position: str = "bottom") -> Optional[float]:
        """Estimate text region legibility from luminance spread and local contrast."""
        if not image_bytes:
            return None

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("L")
            arr = np.asarray(image, dtype=np.float32) / 255.0
            if arr.size == 0:
                return None

            h = arr.shape[0]
            third = max(h // 3, 1)
            if text_position == "top":
                region = arr[:third, :]
            elif text_position == "center":
                region = arr[third: 2 * third, :]
            else:
                region = arr[-third:, :]

            p95 = float(np.percentile(region, 95))
            p5 = float(np.percentile(region, 5))
            contrast = p95 - p5
            std_dev = float(np.std(region))

            # Weighted blend of coarse contrast and pixel variation.
            score = (0.70 * contrast) + (0.60 * std_dev)
            return round(_clamp(score, 0.0, 1.0), 4)
        except Exception:
            return None

    async def compute_identity_consistency_score(
        self,
        generated_image_bytes: Optional[bytes],
        reference_image_url: Optional[str],
    ) -> Optional[float]:
        """
        Compute a lightweight identity consistency proxy using center-crop RGB histogram cosine similarity.
        """
        if not generated_image_bytes or not reference_image_url:
            return None

        reference_bytes = await self._fetch_image_bytes(reference_image_url)
        if not reference_bytes:
            return None

        try:
            generated_image = Image.open(io.BytesIO(generated_image_bytes)).convert("RGB")
            reference_image = Image.open(io.BytesIO(reference_bytes)).convert("RGB")

            generated_crop = self._center_crop_resize(generated_image, size=128)
            reference_crop = self._center_crop_resize(reference_image, size=128)

            gen_vec = self._rgb_hist_vector(generated_crop)
            ref_vec = self._rgb_hist_vector(reference_crop)
            similarity = float(np.dot(gen_vec, ref_vec))

            return round(_clamp(similarity, 0.0, 1.0), 4)
        except Exception:
            return None

    def compute_color_alignment(self, brand_colors: List[str], generated_colors: List[str]) -> Dict[str, Any]:
        """
        Compute color alignment metrics using available color-similarity primitives.

        Notes:
        - This is an RGB-similarity proxy, not true DeltaE.
        - True DeltaE should be computed in Lab space in dedicated evaluation jobs.
        """
        if not brand_colors or not generated_colors:
            return {
                "color_alignment_score": None,
                "palette_match_rate": None,
                "delta_e_proxy": None,
            }

        best_matches: List[float] = []
        matched_count = 0

        for gen in generated_colors:
            similarities = [compare_colors(gen, brand) for brand in brand_colors]
            if not similarities:
                continue
            best = max(similarities)
            best_matches.append(best)
            if best >= 0.75:
                matched_count += 1

        if not best_matches:
            return {
                "color_alignment_score": None,
                "palette_match_rate": None,
                "delta_e_proxy": None,
            }

        alignment_score = float(round(sum(best_matches) / len(best_matches), 4))
        match_rate = float(round(matched_count / len(best_matches), 4))

        # Proxy only. 0 means perfect alignment, higher means larger drift.
        delta_e_proxy = float(round((1.0 - alignment_score) * 100.0, 4))

        return {
            "color_alignment_score": alignment_score,
            "palette_match_rate": match_rate,
            "delta_e_proxy": delta_e_proxy,
        }

    def compute_delta_e_ciede2000(self, brand_colors: List[str], generated_colors: List[str]) -> Dict[str, Any]:
        """Compute true CIEDE2000 metrics in Lab space using color swatches."""
        if not brand_colors or not generated_colors:
            return {
                "delta_e_ciede2000_mean": None,
                "delta_e_ciede2000_median": None,
                "delta_e_ciede2000_pass_rate": None,
                "delta_e_ciede2000_values": [],
            }

        brand_labs = []
        for color in brand_colors:
            rgb = _hex_to_rgb(color)
            if rgb is None:
                continue
            brand_labs.append(_rgb_to_lab(rgb))

        gen_labs = []
        for color in generated_colors:
            rgb = _hex_to_rgb(color)
            if rgb is None:
                continue
            gen_labs.append(_rgb_to_lab(rgb))

        if not brand_labs or not gen_labs:
            return {
                "delta_e_ciede2000_mean": None,
                "delta_e_ciede2000_median": None,
                "delta_e_ciede2000_pass_rate": None,
                "delta_e_ciede2000_values": [],
            }

        min_delta_values: List[float] = []
        for gen_lab in gen_labs:
            deltas = [_ciede2000(gen_lab, brand_lab) for brand_lab in brand_labs]
            min_delta_values.append(min(deltas))

        mean_delta = float(round(sum(min_delta_values) / len(min_delta_values), 4))
        median_delta = float(round(statistics.median(min_delta_values), 4))
        pass_rate = float(round(len([d for d in min_delta_values if d <= 2.0]) / len(min_delta_values), 4))

        return {
            "delta_e_ciede2000_mean": mean_delta,
            "delta_e_ciede2000_median": median_delta,
            "delta_e_ciede2000_pass_rate": pass_rate,
            "delta_e_ciede2000_values": [round(v, 4) for v in min_delta_values],
        }

    async def evaluate_candidate(
        self,
        brand_context: Dict[str, Any],
        candidate: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate measurable metrics for a single candidate output."""
        image_url = candidate.get("image_url")
        image_bytes = await self._fetch_image_bytes(image_url)
        generated_colors = candidate.get("colors") or self._extract_colors_from_image_bytes(image_bytes)

        brand_colors = [c.get("hex", "") for c in brand_context.get("colors", []) if c.get("hex")]

        color_metrics = self.compute_color_alignment(brand_colors, generated_colors)
        delta_e_metrics = self.compute_delta_e_ciede2000(brand_colors, generated_colors)

        metadata = candidate.get("metadata") or {}
        expected_layout = metadata.get("layout", "centered")
        text_position = metadata.get("text_position", "bottom")
        reference_face = metadata.get("character_reference_url")

        layout_score = self.compute_layout_compliance_score(image_bytes, expected_layout=expected_layout)
        text_legibility_score = self.compute_text_legibility_score(image_bytes, text_position=text_position)
        identity_score = await self.compute_identity_consistency_score(image_bytes, reference_face)

        brand_score = await calculate_brand_score(
            brand_context=brand_context,
            image_url=image_url,
            colors_extracted=generated_colors,
        )

        metrics = {
            "success": candidate.get("status") == "completed",
            "brand_score": brand_score,
            "latency_ms": candidate.get("latency_ms"),
            "method_name": candidate.get("method_name"),
            "seed": candidate.get("seed"),
            "colors_used": generated_colors,
            # Measured now
            "color_alignment_score": color_metrics["color_alignment_score"],
            "palette_match_rate": color_metrics["palette_match_rate"],
            "delta_e_proxy": color_metrics["delta_e_proxy"],
            "delta_e_ciede2000_mean": delta_e_metrics["delta_e_ciede2000_mean"],
            "delta_e_ciede2000_median": delta_e_metrics["delta_e_ciede2000_median"],
            "delta_e_ciede2000_pass_rate": delta_e_metrics["delta_e_ciede2000_pass_rate"],
            "delta_e_ciede2000_values": delta_e_metrics["delta_e_ciede2000_values"],
            # Practical proxy scores for structure, identity, and text region quality.
            "layout_compliance_score": candidate.get("layout_compliance_score") if candidate.get("layout_compliance_score") is not None else layout_score,
            "identity_consistency_score": candidate.get("identity_consistency_score") if candidate.get("identity_consistency_score") is not None else identity_score,
            "text_legibility_score": candidate.get("text_legibility_score") if candidate.get("text_legibility_score") is not None else text_legibility_score,
        }

        return metrics

    def aggregate_run_metrics(self, candidate_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate candidate metrics into a run-level summary."""
        total = len(candidate_metrics)
        success_count = len([m for m in candidate_metrics if m.get("success")])

        brand_scores = [m["brand_score"] for m in candidate_metrics if m.get("brand_score") is not None]
        color_scores = [m["color_alignment_score"] for m in candidate_metrics if m.get("color_alignment_score") is not None]
        match_rates = [m["palette_match_rate"] for m in candidate_metrics if m.get("palette_match_rate") is not None]
        delta_e_means = [m["delta_e_ciede2000_mean"] for m in candidate_metrics if m.get("delta_e_ciede2000_mean") is not None]
        delta_e_pass_rates = [m["delta_e_ciede2000_pass_rate"] for m in candidate_metrics if m.get("delta_e_ciede2000_pass_rate") is not None]
        latencies = [m["latency_ms"] for m in candidate_metrics if m.get("latency_ms") is not None]

        run_summary = {
            "candidate_count": total,
            "success_count": success_count,
            "failure_count": max(total - success_count, 0),
            "success_rate": float(round(success_count / total, 4)) if total > 0 else 0.0,
            "brand_score_mean": _safe_mean(brand_scores),
            "brand_score_median": float(statistics.median(brand_scores)) if brand_scores else None,
            "color_alignment_mean": _safe_mean(color_scores),
            "palette_match_rate_mean": _safe_mean(match_rates),
            "delta_e_ciede2000_mean": _safe_mean(delta_e_means),
            "delta_e_ciede2000_pass_rate_mean": _safe_mean(delta_e_pass_rates),
            "latency_ms_mean": _safe_mean(latencies),
            "latency_ms_median": float(statistics.median(latencies)) if latencies else None,
            "metric_availability": {
                "brand_score": len(brand_scores),
                "color_alignment_score": len(color_scores),
                "palette_match_rate": len(match_rates),
                "delta_e_ciede2000_mean": len(delta_e_means),
                "delta_e_ciede2000_pass_rate": len(delta_e_pass_rates),
                "latency_ms": len(latencies),
                "layout_compliance_score": len([m for m in candidate_metrics if m.get("layout_compliance_score") is not None]),
                "identity_consistency_score": len([m for m in candidate_metrics if m.get("identity_consistency_score") is not None]),
                "text_legibility_score": len([m for m in candidate_metrics if m.get("text_legibility_score") is not None]),
            },
        }

        return run_summary

    def summarize_comparison(self, runs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build a compact comparison summary across runs in an experiment."""
        summary_rows = []
        for run in runs:
            run_metrics_nodes = run.get("metrics", [])
            run_metric_payload = None
            if run_metrics_nodes:
                run_metric_payload = run_metrics_nodes[-1].get("metrics")

            summary_rows.append({
                "run_id": run.get("id"),
                "method_name": run.get("method_name"),
                "status": run.get("status"),
                "started_at": str(run.get("started_at")),
                "completed_at": str(run.get("completed_at")) if run.get("completed_at") is not None else None,
                "summary": run_metric_payload,
            })

        baseline_row = next(
            (
                row
                for row in summary_rows
                if row.get("method_name") == "prompt_only" and isinstance(row.get("summary"), dict)
            ),
            None,
        )

        if baseline_row is not None:
            baseline_summary = baseline_row.get("summary") or {}
            delta_metrics = [
                "brand_score_mean",
                "color_alignment_mean",
                "palette_match_rate_mean",
                "delta_e_ciede2000_mean",
                "delta_e_ciede2000_pass_rate_mean",
                "latency_ms_mean",
            ]

            for row in summary_rows:
                run_summary = row.get("summary")
                if not isinstance(run_summary, dict):
                    continue

                deltas: Dict[str, float] = {}
                for metric_key in delta_metrics:
                    baseline_value = baseline_summary.get(metric_key)
                    run_value = run_summary.get(metric_key)
                    if baseline_value is None or run_value is None:
                        continue

                    try:
                        deltas[f"{metric_key}_delta"] = round(float(run_value) - float(baseline_value), 4)
                    except (TypeError, ValueError):
                        continue

                row["delta_vs_prompt_only"] = deltas

        return {
            "run_count": len(runs),
            "baseline_method": "prompt_only" if baseline_row is not None else None,
            "baseline_run_id": baseline_row.get("run_id") if baseline_row is not None else None,
            "delta_direction": {
                "brand_score_mean_delta": "higher_is_better",
                "color_alignment_mean_delta": "higher_is_better",
                "palette_match_rate_mean_delta": "higher_is_better",
                "delta_e_ciede2000_mean_delta": "lower_is_better",
                "delta_e_ciede2000_pass_rate_mean_delta": "higher_is_better",
                "latency_ms_mean_delta": "lower_is_better",
            },
            "runs": summary_rows,
        }
