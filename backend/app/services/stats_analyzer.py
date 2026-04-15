"""
Statistical analyzer for research experiments.
Provides paired comparisons and optional non-parametric tests.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import hashlib
import math
import random


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    n = len(sorted_values)
    mid = n // 2
    if n % 2 == 1:
        return sorted_values[mid]
    return (sorted_values[mid - 1] + sorted_values[mid]) / 2.0


def _two_sided_sign_test_pvalue(positive: int, negative: int) -> float:
    """Exact two-sided sign test p-value with p=0.5."""
    n = positive + negative
    if n == 0:
        return 1.0

    k = min(positive, negative)
    cumulative = 0.0
    for i in range(0, k + 1):
        cumulative += math.comb(n, i) * (0.5 ** n)

    p_two_sided = min(1.0, 2.0 * cumulative)
    return p_two_sided


def _rank_biserial_from_diffs(diffs: List[float]) -> float:
    """Rank-biserial style proxy from sign dominance when full rank stats are unavailable."""
    if not diffs:
        return 0.0
    positive = len([d for d in diffs if d > 0])
    negative = len([d for d in diffs if d < 0])
    n = positive + negative
    if n == 0:
        return 0.0
    return (positive - negative) / n


def _stdev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = _mean(values)
    var = sum((v - mu) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)


def _cohen_dz_from_diffs(diffs: List[float]) -> float:
    """Paired-sample effect size using mean(diff) / std(diff)."""
    sd = _stdev(diffs)
    if sd == 0.0:
        return 0.0
    return _mean(diffs) / sd


def _percentile(sorted_values: List[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if q <= 0:
        return sorted_values[0]
    if q >= 1:
        return sorted_values[-1]

    pos = (len(sorted_values) - 1) * q
    lower = int(math.floor(pos))
    upper = int(math.ceil(pos))
    if lower == upper:
        return sorted_values[lower]

    frac = pos - lower
    return sorted_values[lower] * (1.0 - frac) + sorted_values[upper] * frac


def _bootstrap_mean_ci(values: List[float], resamples: int, alpha: float, rng: random.Random) -> Dict[str, Any]:
    """Non-parametric bootstrap CI for mean(values)."""
    if not values:
        return {
            "mean": 0.0,
            "ci_lower": 0.0,
            "ci_upper": 0.0,
            "alpha": alpha,
            "resamples": 0,
        }

    n = len(values)
    sample_means: List[float] = []
    for _ in range(resamples):
        sampled = [values[rng.randrange(n)] for _ in range(n)]
        sample_means.append(_mean(sampled))

    sample_means.sort()
    lower_q = alpha / 2.0
    upper_q = 1.0 - (alpha / 2.0)

    return {
        "mean": _mean(values),
        "ci_lower": _percentile(sample_means, lower_q),
        "ci_upper": _percentile(sample_means, upper_q),
        "alpha": alpha,
        "resamples": resamples,
    }


def _holm_bonferroni(p_values: List[float]) -> List[float]:
    """Holm-Bonferroni adjusted p-values preserving original order."""
    if not p_values:
        return []

    m = len(p_values)
    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [1.0 for _ in range(m)]

    running_max = 0.0
    for rank, (original_idx, p_value) in enumerate(indexed, start=1):
        scaled = (m - rank + 1) * p_value
        running_max = max(running_max, scaled)
        adjusted[original_idx] = min(1.0, running_max)

    return adjusted


def _stable_pair_seed(base_seed: int, metric_key: str, baseline_method: str, target_method: str) -> int:
    token = f"{base_seed}:{metric_key}:{baseline_method}:{target_method}"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


class StatsAnalyzer:
    """Compute experiment-level statistical summaries from candidate metrics."""

    def _group_by_method(self, rows: List[Dict[str, Any]], metric_key: str) -> Dict[str, Dict[int, float]]:
        grouped: Dict[str, Dict[int, float]] = {}
        for row in rows:
            method = row.get("method_name")
            metrics = row.get("metrics") or {}
            seed = metrics.get("seed")
            value = metrics.get(metric_key)
            if method is None or seed is None or value is None:
                continue

            grouped.setdefault(method, {})
            grouped[method][int(seed)] = float(value)

        return grouped

    def _paired_vectors(self, baseline_map: Dict[int, float], target_map: Dict[int, float]) -> Tuple[List[float], List[float], List[float], List[int]]:
        shared = sorted(set(baseline_map.keys()).intersection(set(target_map.keys())))
        baseline_vals = [baseline_map[s] for s in shared]
        target_vals = [target_map[s] for s in shared]
        diffs = [t - b for t, b in zip(target_vals, baseline_vals)]
        return baseline_vals, target_vals, diffs, shared

    def _wilcoxon_if_available(self, baseline_vals: List[float], target_vals: List[float]) -> Dict[str, Any]:
        try:
            from scipy.stats import wilcoxon  # type: ignore

            stat, p_value = wilcoxon(target_vals, baseline_vals, zero_method="wilcox", correction=False)
            return {
                "test": "wilcoxon_signed_rank",
                "available": True,
                "statistic": float(stat),
                "p_value": float(p_value),
            }
        except Exception:
            return {
                "test": "wilcoxon_signed_rank",
                "available": False,
                "statistic": None,
                "p_value": None,
                "note": "scipy not available; using sign-test fallback",
            }

    def compare_methods(
        self,
        rows: List[Dict[str, Any]],
        metric_key: str,
        baseline_method: str,
        ci_alpha: float = 0.05,
        bootstrap_resamples: int = 2000,
        random_seed: int = 42,
    ) -> Dict[str, Any]:
        # Keep CI configuration within valid two-sided bounds.
        if ci_alpha <= 0.0 or ci_alpha >= 1.0:
            ci_alpha = 0.05
        ci_alpha = min(max(ci_alpha, 1e-6), 0.499)
        bootstrap_resamples = max(int(bootstrap_resamples), 100)

        grouped = self._group_by_method(rows, metric_key)
        if baseline_method not in grouped:
            return {
                "metric": metric_key,
                "baseline_method": baseline_method,
                "error": "Baseline method not found in candidate metrics",
            }

        baseline_map = grouped[baseline_method]
        pairwise_results: List[Dict[str, Any]] = []

        for method_name, target_map in grouped.items():
            if method_name == baseline_method:
                continue

            baseline_vals, target_vals, diffs, shared_seeds = self._paired_vectors(baseline_map, target_map)
            if not diffs:
                pairwise_results.append({
                    "target_method": method_name,
                    "n_pairs": 0,
                    "error": "No shared seeds for paired comparison",
                })
                continue

            positive = len([d for d in diffs if d > 0])
            negative = len([d for d in diffs if d < 0])
            ties = len(diffs) - positive - negative

            wilcoxon_result = self._wilcoxon_if_available(baseline_vals, target_vals)
            sign_p = _two_sided_sign_test_pvalue(positive, negative)

            bootstrap_seed = _stable_pair_seed(random_seed, metric_key, baseline_method, method_name)
            ci_rng = random.Random(bootstrap_seed)
            delta_mean_ci = _bootstrap_mean_ci(diffs, bootstrap_resamples, ci_alpha, ci_rng)

            wilcoxon_p = wilcoxon_result.get("p_value")
            use_wilcoxon = wilcoxon_result.get("available") and wilcoxon_p is not None
            primary_p = float(wilcoxon_p) if use_wilcoxon else float(sign_p)
            primary_source = "wilcoxon" if use_wilcoxon else "sign_test"

            effect_size = {
                "cohen_dz": _cohen_dz_from_diffs(diffs),
                "rank_biserial_proxy": _rank_biserial_from_diffs(diffs),
            }

            pairwise_results.append({
                "target_method": method_name,
                "n_pairs": len(diffs),
                "shared_seeds": shared_seeds,
                "baseline_mean": _mean(baseline_vals),
                "target_mean": _mean(target_vals),
                "delta_mean": _mean(diffs),
                "delta_median": _median(diffs),
                "delta_mean_ci": delta_mean_ci,
                "rank_biserial_proxy": effect_size["rank_biserial_proxy"],
                "effect_size": effect_size,
                "direction_counts": {
                    "positive": positive,
                    "negative": negative,
                    "ties": ties,
                },
                "p_value_primary": primary_p,
                "p_value_primary_source": primary_source,
                "wilcoxon": wilcoxon_result,
                "sign_test": {
                    "positive": positive,
                    "negative": negative,
                    "p_value": sign_p,
                },
            })

        valid_p_rows: List[int] = []
        valid_p_values: List[float] = []
        for idx, row in enumerate(pairwise_results):
            p_val = row.get("p_value_primary")
            if isinstance(p_val, (int, float)):
                valid_p_rows.append(idx)
                valid_p_values.append(float(p_val))

        if valid_p_values:
            adjusted = _holm_bonferroni(valid_p_values)
            for idx, adjusted_p in zip(valid_p_rows, adjusted):
                pairwise_results[idx]["p_value_adjusted_holm"] = adjusted_p
                pairwise_results[idx]["significant_alpha_0_05"] = adjusted_p < 0.05

        omnibus: Dict[str, Any] = {
            "test": "friedman",
            "available": False,
            "statistic": None,
            "p_value": None,
        }

        # Try Friedman if scipy is available and at least 3 methods have full paired vectors.
        method_names = [m for m in grouped.keys()]
        if len(method_names) >= 3:
            common_seeds = set(grouped[method_names[0]].keys())
            for name in method_names[1:]:
                common_seeds = common_seeds.intersection(set(grouped[name].keys()))

            if len(common_seeds) > 0:
                ordered_seeds = sorted(common_seeds)
                data_vectors = [[grouped[name][seed] for seed in ordered_seeds] for name in method_names]
                try:
                    from scipy.stats import friedmanchisquare  # type: ignore

                    stat, p_value = friedmanchisquare(*data_vectors)
                    omnibus = {
                        "test": "friedman",
                        "available": True,
                        "n_methods": len(method_names),
                        "n_pairs": len(ordered_seeds),
                        "statistic": float(stat),
                        "p_value": float(p_value),
                        "methods": method_names,
                        "shared_seeds": ordered_seeds,
                    }
                except Exception:
                    omnibus = {
                        "test": "friedman",
                        "available": False,
                        "n_methods": len(method_names),
                        "n_pairs": len(ordered_seeds),
                        "statistic": None,
                        "p_value": None,
                        "methods": method_names,
                        "shared_seeds": ordered_seeds,
                        "note": "scipy not available",
                    }

        return {
            "metric": metric_key,
            "baseline_method": baseline_method,
            "methods_detected": sorted(grouped.keys()),
            "analysis_config": {
                "ci_alpha": ci_alpha,
                "bootstrap_resamples": bootstrap_resamples,
                "random_seed": random_seed,
                "multiple_comparison_correction": "holm_bonferroni",
            },
            "pairwise": pairwise_results,
            "omnibus": omnibus,
        }
