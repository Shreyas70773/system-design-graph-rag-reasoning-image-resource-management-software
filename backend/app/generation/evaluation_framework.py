"""
Evaluation Framework for GraphRAG-Guided Image Generation
==========================================================
This module provides comprehensive evaluation metrics for the capstone research.
It measures system performance across multiple dimensions:

1. Brand Alignment - How well generated content matches brand guidelines
2. Constraint Satisfaction - How well constraints are respected
3. User Satisfaction - Feedback-based satisfaction scoring
4. Learning Effectiveness - How well the system learns from feedback
5. Generation Quality - Technical quality metrics

Part of Capstone Research: GraphRAG-Guided Compositional Image Generation
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import math
from collections import defaultdict


class MetricType(str, Enum):
    """Types of evaluation metrics."""
    BRAND_ALIGNMENT = "brand_alignment"
    CONSTRAINT_SATISFACTION = "constraint_satisfaction"
    USER_SATISFACTION = "user_satisfaction"
    LEARNING_EFFECTIVENESS = "learning_effectiveness"
    GENERATION_QUALITY = "generation_quality"
    SYSTEM_PERFORMANCE = "system_performance"


@dataclass
class MetricResult:
    """A single metric evaluation result."""
    metric_type: MetricType
    metric_name: str
    value: float  # 0-1 normalized
    raw_value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "metric_type": self.metric_type.value,
            "metric_name": self.metric_name,
            "value": self.value,
            "raw_value": self.raw_value,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }


@dataclass
class EvaluationReport:
    """Complete evaluation report for a time period or experiment."""
    report_id: str
    brand_id: str
    period_start: datetime
    period_end: datetime
    metrics: List[MetricResult]
    summary: Dict[str, float]
    recommendations: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "report_id": self.report_id,
            "brand_id": self.brand_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "metrics": [m.to_dict() for m in self.metrics],
            "summary": self.summary,
            "recommendations": self.recommendations
        }
    
    def get_overall_score(self) -> float:
        """Calculate weighted overall score."""
        weights = {
            MetricType.BRAND_ALIGNMENT: 0.25,
            MetricType.CONSTRAINT_SATISFACTION: 0.20,
            MetricType.USER_SATISFACTION: 0.30,
            MetricType.LEARNING_EFFECTIVENESS: 0.15,
            MetricType.GENERATION_QUALITY: 0.10
        }
        
        type_scores = defaultdict(list)
        for metric in self.metrics:
            type_scores[metric.metric_type].append(metric.value)
        
        weighted_sum = 0
        total_weight = 0
        
        for metric_type, weight in weights.items():
            if metric_type in type_scores:
                avg_score = sum(type_scores[metric_type]) / len(type_scores[metric_type])
                weighted_sum += avg_score * weight
                total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0


class BrandAlignmentEvaluator:
    """Evaluates how well generated content aligns with brand guidelines."""
    
    @staticmethod
    def evaluate_color_alignment(
        generated_colors: List[str],
        brand_colors: List[str],
        tolerance: float = 0.2
    ) -> MetricResult:
        """
        Evaluate color alignment between generated and brand colors.
        
        Args:
            generated_colors: Hex colors from generated image
            brand_colors: Brand's defined colors
            tolerance: Color distance tolerance (0-1)
        """
        if not generated_colors or not brand_colors:
            return MetricResult(
                metric_type=MetricType.BRAND_ALIGNMENT,
                metric_name="color_alignment",
                value=0.5,
                raw_value={"generated": generated_colors, "brand": brand_colors},
                details={"message": "Insufficient color data"}
            )
        
        def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        def color_distance(c1: Tuple, c2: Tuple) -> float:
            return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2))) / 441.67  # Normalize by max distance
        
        # Calculate best match for each generated color
        matches = 0
        match_details = []
        
        brand_rgb = [hex_to_rgb(c) for c in brand_colors if len(c) >= 6]
        
        for gen_color in generated_colors:
            try:
                gen_rgb = hex_to_rgb(gen_color)
                min_distance = min(color_distance(gen_rgb, brand) for brand in brand_rgb)
                is_match = min_distance <= tolerance
                if is_match:
                    matches += 1
                match_details.append({
                    "color": gen_color,
                    "min_distance": min_distance,
                    "is_match": is_match
                })
            except:
                continue
        
        alignment_score = matches / len(generated_colors) if generated_colors else 0
        
        return MetricResult(
            metric_type=MetricType.BRAND_ALIGNMENT,
            metric_name="color_alignment",
            value=alignment_score,
            raw_value={"matches": matches, "total": len(generated_colors)},
            details={"match_details": match_details, "tolerance": tolerance}
        )
    
    @staticmethod
    def evaluate_style_consistency(
        generated_style: Dict[str, str],
        brand_style: Dict[str, str]
    ) -> MetricResult:
        """Evaluate style attribute consistency with brand guidelines."""
        if not generated_style or not brand_style:
            return MetricResult(
                metric_type=MetricType.BRAND_ALIGNMENT,
                metric_name="style_consistency",
                value=0.5,
                raw_value={},
                details={"message": "Insufficient style data"}
            )
        
        matches = 0
        total = 0
        comparison = []
        
        for key, brand_value in brand_style.items():
            if key in generated_style:
                total += 1
                gen_value = generated_style[key] or ""
                brand_value = brand_value or ""
                is_match = gen_value.lower() == brand_value.lower() or brand_value.lower() in gen_value.lower()
                if is_match:
                    matches += 1
                comparison.append({
                    "attribute": key,
                    "brand": brand_value,
                    "generated": gen_value,
                    "match": is_match
                })
        
        score = matches / total if total > 0 else 0.5
        
        return MetricResult(
            metric_type=MetricType.BRAND_ALIGNMENT,
            metric_name="style_consistency",
            value=score,
            raw_value={"matches": matches, "total": total},
            details={"comparison": comparison}
        )


class ConstraintSatisfactionEvaluator:
    """Evaluates how well constraints are satisfied in generations."""
    
    @staticmethod
    def evaluate_constraint_adherence(
        constraints_applied: List[Dict],
        generation_result: Dict
    ) -> MetricResult:
        """
        Evaluate constraint adherence in a generation.
        
        Checks:
        - MUST_INCLUDE constraints are present
        - MUST_AVOID constraints are absent
        - PREFER constraints are considered
        """
        if not constraints_applied:
            return MetricResult(
                metric_type=MetricType.CONSTRAINT_SATISFACTION,
                metric_name="constraint_adherence",
                value=1.0,
                raw_value={"constraints": 0},
                details={"message": "No constraints to evaluate"}
            )
        
        satisfied = 0
        violated = 0
        weighted_score = 0
        total_weight = 0
        violations = []
        
        prompt_used = generation_result.get("compiled_prompt", {}).get("positive_prompt", "").lower()
        negative_prompt = generation_result.get("compiled_prompt", {}).get("negative_prompt", "").lower()
        
        for constraint in constraints_applied:
            weight = constraint.get("strength", 0.5)
            total_weight += weight
            target = constraint.get("target_value", "").lower()
            
            if constraint.get("type") == "MUST_INCLUDE":
                if target in prompt_used:
                    satisfied += 1
                    weighted_score += weight
                else:
                    violated += 1
                    violations.append({
                        "constraint": constraint,
                        "reason": f"Required '{target}' not found in prompt"
                    })
            
            elif constraint.get("type") == "MUST_AVOID":
                if target not in prompt_used or target in negative_prompt:
                    satisfied += 1
                    weighted_score += weight
                else:
                    violated += 1
                    violations.append({
                        "constraint": constraint,
                        "reason": f"Avoided '{target}' present in prompt"
                    })
            
            elif constraint.get("type") in ["PREFER", "DISCOURAGE"]:
                # Soft constraints - partial credit
                satisfied += 0.5
                weighted_score += weight * 0.5
        
        score = weighted_score / total_weight if total_weight > 0 else 1.0
        
        return MetricResult(
            metric_type=MetricType.CONSTRAINT_SATISFACTION,
            metric_name="constraint_adherence",
            value=score,
            raw_value={"satisfied": satisfied, "violated": violated, "total": len(constraints_applied)},
            details={"violations": violations}
        )
    
    @staticmethod
    def evaluate_conflict_resolution(
        conflicts: List[Dict]
    ) -> MetricResult:
        """Evaluate how well conflicts were resolved."""
        if not conflicts:
            return MetricResult(
                metric_type=MetricType.CONSTRAINT_SATISFACTION,
                metric_name="conflict_resolution",
                value=1.0,
                raw_value={"conflicts": 0},
                details={"message": "No conflicts to resolve"}
            )
        
        # Check if each conflict has a clear winner and reason
        resolved_properly = sum(
            1 for c in conflicts 
            if c.get("winner") and c.get("reason")
        )
        
        score = resolved_properly / len(conflicts) if conflicts else 1.0
        
        return MetricResult(
            metric_type=MetricType.CONSTRAINT_SATISFACTION,
            metric_name="conflict_resolution",
            value=score,
            raw_value={"resolved": resolved_properly, "total": len(conflicts)},
            details={"conflicts": conflicts}
        )


class UserSatisfactionEvaluator:
    """Evaluates user satisfaction based on feedback data."""
    
    @staticmethod
    def evaluate_feedback_ratio(
        positive_count: int,
        negative_count: int
    ) -> MetricResult:
        """Calculate satisfaction based on feedback ratio."""
        total = positive_count + negative_count
        if total == 0:
            return MetricResult(
                metric_type=MetricType.USER_SATISFACTION,
                metric_name="feedback_ratio",
                value=0.5,
                raw_value={"positive": 0, "negative": 0},
                details={"message": "No feedback data"}
            )
        
        # Calculate ratio with smoothing
        score = (positive_count + 1) / (total + 2)  # Laplace smoothing
        
        return MetricResult(
            metric_type=MetricType.USER_SATISFACTION,
            metric_name="feedback_ratio",
            value=score,
            raw_value={"positive": positive_count, "negative": negative_count, "total": total}
        )
    
    @staticmethod
    def evaluate_acceptance_rate(
        accepted: int,
        regenerated: int,
        total_generations: int
    ) -> MetricResult:
        """Calculate rate of accepted vs regenerated content."""
        if total_generations == 0:
            return MetricResult(
                metric_type=MetricType.USER_SATISFACTION,
                metric_name="acceptance_rate",
                value=0.5,
                raw_value={}
            )
        
        acceptance_rate = accepted / total_generations
        rejection_rate = regenerated / total_generations
        
        # Score weighted towards acceptance
        score = acceptance_rate * 0.7 + (1 - rejection_rate) * 0.3
        
        return MetricResult(
            metric_type=MetricType.USER_SATISFACTION,
            metric_name="acceptance_rate",
            value=score,
            raw_value={
                "accepted": accepted,
                "regenerated": regenerated,
                "total": total_generations
            }
        )


class LearningEffectivenessEvaluator:
    """Evaluates how effectively the system learns from feedback."""
    
    @staticmethod
    def evaluate_preference_confidence_growth(
        preferences: List[Dict],
        min_samples: int = 3
    ) -> MetricResult:
        """Evaluate how preference confidence grows over time."""
        if not preferences:
            return MetricResult(
                metric_type=MetricType.LEARNING_EFFECTIVENESS,
                metric_name="confidence_growth",
                value=0.0,
                raw_value={}
            )
        
        high_confidence = sum(1 for p in preferences if p.get("confidence", 0) >= 0.7)
        medium_confidence = sum(1 for p in preferences if 0.5 <= p.get("confidence", 0) < 0.7)
        sufficient_samples = sum(1 for p in preferences if p.get("sample_count", 0) >= min_samples)
        
        # Score based on preference quality
        score = (
            (high_confidence * 1.0 + medium_confidence * 0.5) / len(preferences) * 0.7 +
            (sufficient_samples / len(preferences)) * 0.3
        ) if preferences else 0
        
        return MetricResult(
            metric_type=MetricType.LEARNING_EFFECTIVENESS,
            metric_name="confidence_growth",
            value=score,
            raw_value={
                "high_confidence": high_confidence,
                "medium_confidence": medium_confidence,
                "sufficient_samples": sufficient_samples,
                "total_preferences": len(preferences)
            }
        )
    
    @staticmethod
    def evaluate_pattern_detection(
        patterns_detected: int,
        actionable_patterns: int,
        total_negative_feedback: int
    ) -> MetricResult:
        """Evaluate effectiveness of negative pattern detection."""
        if total_negative_feedback == 0:
            return MetricResult(
                metric_type=MetricType.LEARNING_EFFECTIVENESS,
                metric_name="pattern_detection",
                value=1.0,
                raw_value={},
                details={"message": "No negative feedback to learn from"}
            )
        
        # Good if patterns are detected from negative feedback
        detection_rate = patterns_detected / max(1, total_negative_feedback / 2)
        actionable_rate = actionable_patterns / max(1, patterns_detected) if patterns_detected > 0 else 1
        
        score = min(1.0, detection_rate * 0.6 + actionable_rate * 0.4)
        
        return MetricResult(
            metric_type=MetricType.LEARNING_EFFECTIVENESS,
            metric_name="pattern_detection",
            value=score,
            raw_value={
                "patterns_detected": patterns_detected,
                "actionable_patterns": actionable_patterns,
                "negative_feedback": total_negative_feedback
            }
        )
    
    @staticmethod
    def evaluate_improvement_over_time(
        brand_scores: List[Tuple[datetime, float]]
    ) -> MetricResult:
        """Evaluate if generation quality improves over time."""
        if len(brand_scores) < 3:
            return MetricResult(
                metric_type=MetricType.LEARNING_EFFECTIVENESS,
                metric_name="improvement_over_time",
                value=0.5,
                raw_value={},
                details={"message": "Insufficient data points"}
            )
        
        # Sort by time
        sorted_scores = sorted(brand_scores, key=lambda x: x[0])
        
        # Split into early and recent
        midpoint = len(sorted_scores) // 2
        early_avg = sum(s[1] for s in sorted_scores[:midpoint]) / midpoint
        recent_avg = sum(s[1] for s in sorted_scores[midpoint:]) / (len(sorted_scores) - midpoint)
        
        # Calculate trend
        improvement = recent_avg - early_avg
        
        # Normalize to 0-1 (considering max possible improvement)
        max_improvement = 1.0 - early_avg
        if max_improvement > 0:
            score = 0.5 + (improvement / max_improvement) * 0.5
        else:
            score = 0.5 + improvement * 2  # Already near perfect
        
        score = max(0, min(1, score))
        
        return MetricResult(
            metric_type=MetricType.LEARNING_EFFECTIVENESS,
            metric_name="improvement_over_time",
            value=score,
            raw_value={
                "early_average": early_avg,
                "recent_average": recent_avg,
                "improvement": improvement
            },
            details={"data_points": len(brand_scores)}
        )


class SystemPerformanceEvaluator:
    """Evaluates system performance metrics."""
    
    @staticmethod
    def evaluate_generation_time(
        avg_time_ms: float,
        target_time_ms: float = 30000
    ) -> MetricResult:
        """Evaluate if generation time meets targets."""
        if avg_time_ms <= 0:
            return MetricResult(
                metric_type=MetricType.SYSTEM_PERFORMANCE,
                metric_name="generation_time",
                value=0.5,
                raw_value={}
            )
        
        # Score decreases as time exceeds target
        if avg_time_ms <= target_time_ms:
            score = 1.0
        else:
            score = max(0, 1.0 - (avg_time_ms - target_time_ms) / target_time_ms)
        
        return MetricResult(
            metric_type=MetricType.SYSTEM_PERFORMANCE,
            metric_name="generation_time",
            value=score,
            raw_value={"avg_time_ms": avg_time_ms, "target_ms": target_time_ms}
        )
    
    @staticmethod
    def evaluate_error_rate(
        successful: int,
        failed: int
    ) -> MetricResult:
        """Evaluate system error rate."""
        total = successful + failed
        if total == 0:
            return MetricResult(
                metric_type=MetricType.SYSTEM_PERFORMANCE,
                metric_name="error_rate",
                value=1.0,
                raw_value={}
            )
        
        success_rate = successful / total
        
        return MetricResult(
            metric_type=MetricType.SYSTEM_PERFORMANCE,
            metric_name="error_rate",
            value=success_rate,
            raw_value={"successful": successful, "failed": failed, "total": total}
        )


class EvaluationFramework:
    """
    Main evaluation framework that orchestrates all evaluators.
    
    Use this to generate comprehensive evaluation reports for:
    - Individual generations
    - Time periods
    - A/B experiments
    - System health checks
    """
    
    def __init__(self, neo4j_client=None):
        self.db = neo4j_client
        self.brand_evaluator = BrandAlignmentEvaluator()
        self.constraint_evaluator = ConstraintSatisfactionEvaluator()
        self.satisfaction_evaluator = UserSatisfactionEvaluator()
        self.learning_evaluator = LearningEffectivenessEvaluator()
        self.performance_evaluator = SystemPerformanceEvaluator()
    
    async def evaluate_generation(
        self,
        generation_result: Dict,
        brand_context: Dict,
        constraints_applied: List[Dict]
    ) -> List[MetricResult]:
        """Evaluate a single generation."""
        metrics = []
        
        # Brand alignment
        if generation_result.get("colors_used") and brand_context.get("colors"):
            brand_colors = [c.get("hex") for c in brand_context["colors"] if c.get("hex")]
            metrics.append(self.brand_evaluator.evaluate_color_alignment(
                generation_result["colors_used"],
                brand_colors
            ))
        
        # Constraint satisfaction
        if constraints_applied:
            metrics.append(self.constraint_evaluator.evaluate_constraint_adherence(
                constraints_applied,
                generation_result
            ))
        
        if generation_result.get("conflicts_resolved"):
            metrics.append(self.constraint_evaluator.evaluate_conflict_resolution(
                generation_result["conflicts_resolved"]
            ))
        
        # Performance
        if generation_result.get("generation_time_ms"):
            metrics.append(self.performance_evaluator.evaluate_generation_time(
                generation_result["generation_time_ms"]
            ))
        
        return metrics
    
    async def generate_report(
        self,
        brand_id: str,
        days: int = 7
    ) -> EvaluationReport:
        """Generate comprehensive evaluation report for a brand."""
        import uuid
        
        period_end = datetime.now()
        period_start = period_end - timedelta(days=days)
        
        metrics = []
        
        # Gather data from database
        if self.db:
            generation_data = await self._get_generation_data(brand_id, period_start)
            feedback_data = await self._get_feedback_data(brand_id, period_start)
            preference_data = await self._get_preference_data(brand_id)
        else:
            generation_data = {"count": 0, "avg_score": 0.5}
            feedback_data = {"positive": 0, "negative": 0, "accepted": 0, "regenerated": 0}
            preference_data = {"preferences": [], "patterns": 0}
        
        # User satisfaction metrics
        metrics.append(self.satisfaction_evaluator.evaluate_feedback_ratio(
            feedback_data.get("positive", 0),
            feedback_data.get("negative", 0)
        ))
        
        metrics.append(self.satisfaction_evaluator.evaluate_acceptance_rate(
            feedback_data.get("accepted", 0),
            feedback_data.get("regenerated", 0),
            generation_data.get("count", 0)
        ))
        
        # Learning effectiveness
        metrics.append(self.learning_evaluator.evaluate_preference_confidence_growth(
            preference_data.get("preferences", [])
        ))
        
        metrics.append(self.learning_evaluator.evaluate_pattern_detection(
            preference_data.get("patterns", 0),
            preference_data.get("actionable_patterns", 0),
            feedback_data.get("negative", 0)
        ))
        
        # Generate summary
        summary = self._calculate_summary(metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, summary)
        
        return EvaluationReport(
            report_id=f"eval_{uuid.uuid4().hex[:8]}",
            brand_id=brand_id,
            period_start=period_start,
            period_end=period_end,
            metrics=metrics,
            summary=summary,
            recommendations=recommendations
        )
    
    async def _get_generation_data(self, brand_id: str, since: datetime) -> Dict:
        """Get generation statistics from database."""
        query = """
        MATCH (b:Brand {id: $brand_id})-[:GENERATED]->(g:Generation)
        WHERE g.created_at >= $since
        RETURN count(g) as count, avg(g.brand_score) as avg_score,
               avg(g.generation_time_ms) as avg_time
        """
        try:
            results = await self.db.execute_query(query, {
                "brand_id": brand_id,
                "since": since.isoformat()
            })
            if results:
                return dict(results[0])
        except:
            pass
        return {"count": 0, "avg_score": 0.5}
    
    async def _get_feedback_data(self, brand_id: str, since: datetime) -> Dict:
        """Get feedback statistics from database."""
        # Simplified - would query actual feedback nodes
        return {"positive": 0, "negative": 0, "accepted": 0, "regenerated": 0}
    
    async def _get_preference_data(self, brand_id: str) -> Dict:
        """Get learned preference data."""
        # Simplified - would query actual preference nodes
        return {"preferences": [], "patterns": 0, "actionable_patterns": 0}
    
    def _calculate_summary(self, metrics: List[MetricResult]) -> Dict[str, float]:
        """Calculate summary statistics from metrics."""
        summary = {}
        
        for metric_type in MetricType:
            type_metrics = [m for m in metrics if m.metric_type == metric_type]
            if type_metrics:
                avg = sum(m.value for m in type_metrics) / len(type_metrics)
                summary[metric_type.value] = round(avg, 3)
        
        # Overall score
        if summary:
            summary["overall"] = round(sum(summary.values()) / len(summary), 3)
        
        return summary
    
    def _generate_recommendations(
        self,
        metrics: List[MetricResult],
        summary: Dict[str, float]
    ) -> List[str]:
        """Generate actionable recommendations based on metrics."""
        recommendations = []
        
        # Check each dimension
        brand_score = summary.get(MetricType.BRAND_ALIGNMENT.value, 1)
        if brand_score < 0.6:
            recommendations.append(
                "Brand alignment is low. Consider reviewing and strengthening brand constraints."
            )
        
        satisfaction_score = summary.get(MetricType.USER_SATISFACTION.value, 1)
        if satisfaction_score < 0.5:
            recommendations.append(
                "User satisfaction needs improvement. Review recent negative feedback for patterns."
            )
        
        learning_score = summary.get(MetricType.LEARNING_EFFECTIVENESS.value, 1)
        if learning_score < 0.5:
            recommendations.append(
                "Learning effectiveness is low. Need more user feedback to improve preferences."
            )
        
        # Positive recommendations
        overall = summary.get("overall", 0)
        if overall >= 0.8:
            recommendations.append(
                "System is performing well! Continue collecting feedback to maintain quality."
            )
        elif overall >= 0.6:
            recommendations.append(
                "System shows moderate performance. Focus on the lowest-scoring dimensions."
            )
        
        if not recommendations:
            recommendations.append("Continue monitoring system performance.")
        
        return recommendations


# Convenience function for quick evaluation
async def evaluate_generation(
    generation_result: Dict,
    brand_context: Dict,
    constraints: List[Dict] = None
) -> Dict[str, Any]:
    """
    Quick evaluation of a single generation.
    
    Returns:
        Dict with metric scores and overall assessment
    """
    framework = EvaluationFramework()
    metrics = await framework.evaluate_generation(
        generation_result,
        brand_context,
        constraints or []
    )
    
    scores = {m.metric_name: m.value for m in metrics}
    overall = sum(m.value for m in metrics) / len(metrics) if metrics else 0.5
    
    return {
        "scores": scores,
        "overall": overall,
        "grade": "A" if overall >= 0.9 else "B" if overall >= 0.7 else "C" if overall >= 0.5 else "D",
        "metrics_count": len(metrics)
    }
