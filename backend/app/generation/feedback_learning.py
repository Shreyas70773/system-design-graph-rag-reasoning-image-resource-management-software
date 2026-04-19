"""
Feedback Learning System
=========================
This module implements continuous preference learning from user feedback.
It aggregates feedback at multiple levels (whole image, element, attribute)
to learn and update preferences in the knowledge graph.

Key Features:
- Multi-level feedback collection (image/element/attribute)
- Preference aggregation and confidence scoring
- Negative pattern detection
- Automatic constraint generation from feedback
- Feedback history tracking

Part of Capstone Research: GraphRAG-Guided Compositional Image Generation
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
import json
import uuid
from datetime import datetime, timedelta
from collections import defaultdict
import math


class FeedbackType(str, Enum):
    """Types of user feedback."""
    LIKE = "like"              # Positive feedback on whole image
    DISLIKE = "dislike"        # Negative feedback on whole image
    ACCEPT = "accept"          # User accepted/downloaded the image
    REGENERATE = "regenerate"  # User requested regeneration
    EDIT = "edit"              # User made an edit
    ELEMENT_LIKE = "element_like"      # Positive on specific element
    ELEMENT_DISLIKE = "element_dislike"  # Negative on specific element


class FeedbackLevel(str, Enum):
    """Granularity level of feedback."""
    WHOLE = "whole"        # Entire image
    ELEMENT = "element"    # Specific element (background, subject, etc.)
    ATTRIBUTE = "attribute"  # Specific attribute (lighting, color, etc.)


@dataclass
class Feedback:
    """A single feedback instance."""
    id: str
    type: FeedbackType
    level: FeedbackLevel
    generation_id: str
    brand_id: str
    element_type: Optional[str] = None  # For element-level
    element_id: Optional[str] = None    # Specific element
    attribute: Optional[str] = None      # For attribute-level
    old_value: Optional[str] = None      # For edit feedback
    new_value: Optional[str] = None      # For edit feedback
    comment: Optional[str] = None        # User explanation
    context: Dict[str, Any] = field(default_factory=dict)  # Generation context
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "level": self.level.value,
            "generation_id": self.generation_id,
            "brand_id": self.brand_id,
            "element_type": self.element_type,
            "element_id": self.element_id,
            "attribute": self.attribute,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "comment": self.comment,
            "context": self.context,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Feedback":
        return cls(
            id=data.get("id", f"fb_{uuid.uuid4().hex[:8]}"),
            type=FeedbackType(data["type"]),
            level=FeedbackLevel(data.get("level", "whole")),
            generation_id=data.get("generation_id", ""),
            brand_id=data.get("brand_id", ""),
            element_type=data.get("element_type"),
            element_id=data.get("element_id"),
            attribute=data.get("attribute"),
            old_value=data.get("old_value"),
            new_value=data.get("new_value"),
            comment=data.get("comment"),
            context=data.get("context", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now()
        )
    
    @property
    def is_positive(self) -> bool:
        """Check if this is positive feedback."""
        return self.type in [FeedbackType.LIKE, FeedbackType.ACCEPT, FeedbackType.ELEMENT_LIKE]
    
    @property
    def is_negative(self) -> bool:
        """Check if this is negative feedback."""
        return self.type in [FeedbackType.DISLIKE, FeedbackType.REGENERATE, FeedbackType.ELEMENT_DISLIKE]


@dataclass
class AggregatedPreference:
    """An aggregated preference learned from multiple feedback instances."""
    attribute: str  # e.g., 'SUBJECT_lighting', 'global_color_saturation'
    preferred_values: Dict[str, int]  # value -> positive count
    avoided_values: Dict[str, int]    # value -> negative count
    total_samples: int
    confidence: float
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "attribute": self.attribute,
            "preferred_values": self.preferred_values,
            "avoided_values": self.avoided_values,
            "total_samples": self.total_samples,
            "confidence": self.confidence,
            "last_updated": self.last_updated.isoformat()
        }
    
    def get_top_preference(self) -> Optional[str]:
        """Get the most preferred value."""
        if not self.preferred_values:
            return None
        return max(self.preferred_values, key=self.preferred_values.get)
    
    def get_top_avoidance(self) -> Optional[str]:
        """Get the most avoided value."""
        if not self.avoided_values:
            return None
        return max(self.avoided_values, key=self.avoided_values.get)


@dataclass
class NegativePatternLearned:
    """A negative pattern learned from repeated negative feedback."""
    pattern_key: str  # Unique identifier
    element_type: str
    attribute: Optional[str]
    value: str
    occurrence_count: int
    severity: str  # 'minor', 'major', 'critical'
    first_seen: datetime
    last_seen: datetime
    example_generations: List[str]  # Generation IDs where this occurred
    
    def to_dict(self) -> Dict:
        return {
            "pattern_key": self.pattern_key,
            "element_type": self.element_type,
            "attribute": self.attribute,
            "value": self.value,
            "occurrence_count": self.occurrence_count,
            "severity": self.severity,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "example_generations": self.example_generations
        }
    
    @property
    def is_significant(self) -> bool:
        """Check if pattern is significant enough to act on."""
        return self.occurrence_count >= 2 or self.severity == "critical"


class FeedbackLearningEngine:
    """
    Engine for learning preferences from user feedback.
    
    This implements the continuous learning component:
    1. Collect feedback at multiple granularities
    2. Aggregate feedback into preferences
    3. Detect negative patterns
    4. Update knowledge graph with learned constraints
    5. Apply decay to old feedback
    """
    
    # Configuration
    MIN_SAMPLES_FOR_CONFIDENCE = 3
    CONFIDENCE_DECAY_DAYS = 30
    PATTERN_THRESHOLD = 2  # Minimum occurrences to flag pattern
    
    def __init__(self, neo4j_client=None):
        """
        Initialize the feedback learning engine.
        
        Args:
            neo4j_client: Neo4j client for storing learned preferences
        """
        self.db = neo4j_client
        
        # In-memory caches for fast aggregation
        self._feedback_cache: Dict[str, List[Feedback]] = defaultdict(list)
        self._preference_cache: Dict[str, AggregatedPreference] = {}
        self._pattern_cache: Dict[str, NegativePatternLearned] = {}
    
    async def record_feedback(
        self,
        feedback_type: str,
        generation_id: str,
        brand_id: str,
        level: str = "whole",
        element_type: Optional[str] = None,
        element_id: Optional[str] = None,
        attribute: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        comment: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Feedback:
        """
        Record a new feedback instance.
        
        Args:
            feedback_type: Type of feedback (like, dislike, edit, etc.)
            generation_id: ID of the generation being rated
            brand_id: Brand identifier
            level: Feedback granularity (whole, element, attribute)
            element_type: For element-level feedback
            element_id: Specific element ID
            attribute: For attribute-level feedback
            old_value: For edit feedback
            new_value: For edit feedback
            comment: Optional user comment
            context: Optional generation context
            
        Returns:
            Created Feedback object
        """
        feedback = Feedback(
            id=f"fb_{uuid.uuid4().hex[:8]}",
            type=FeedbackType(feedback_type),
            level=FeedbackLevel(level),
            generation_id=generation_id,
            brand_id=brand_id,
            element_type=element_type,
            element_id=element_id,
            attribute=attribute,
            old_value=old_value,
            new_value=new_value,
            comment=comment,
            context=context or {}
        )
        
        # Add to cache
        cache_key = f"{brand_id}:{element_type or 'global'}"
        self._feedback_cache[cache_key].append(feedback)
        
        # Store in Neo4j
        if self.db:
            await self._store_feedback(feedback)
        
        # Update aggregations
        await self._update_aggregations(feedback)
        
        # Check for negative patterns
        if feedback.is_negative:
            await self._check_negative_patterns(feedback)
        
        return feedback
    
    async def _store_feedback(self, feedback: Feedback):
        """Store feedback in Neo4j."""
        query = """
        MATCH (g:Generation {id: $gen_id})
        CREATE (f:Feedback {
            id: $fb_id,
            type: $type,
            level: $level,
            element_type: $element_type,
            element_id: $element_id,
            attribute: $attribute,
            old_value: $old_value,
            new_value: $new_value,
            comment: $comment,
            context: $context,
            created_at: datetime()
        })
        CREATE (f)-[:ABOUT_GENERATION]->(g)
        """
        
        try:
            await self.db.execute_query(query, {
                "gen_id": feedback.generation_id,
                "fb_id": feedback.id,
                "type": feedback.type.value,
                "level": feedback.level.value,
                "element_type": feedback.element_type,
                "element_id": feedback.element_id,
                "attribute": feedback.attribute,
                "old_value": feedback.old_value,
                "new_value": feedback.new_value,
                "comment": feedback.comment,
                "context": json.dumps(feedback.context)
            })
        except Exception as e:
            print(f"Error storing feedback: {e}")
    
    async def _update_aggregations(self, feedback: Feedback):
        """Update preference aggregations based on new feedback."""
        # Determine the attribute key
        if feedback.level == FeedbackLevel.ATTRIBUTE and feedback.attribute:
            attr_key = f"{feedback.element_type}_{feedback.attribute}" if feedback.element_type else feedback.attribute
        elif feedback.level == FeedbackLevel.ELEMENT and feedback.element_type:
            attr_key = f"{feedback.element_type}_general"
        else:
            attr_key = "global_general"
        
        # Get or create aggregation
        if attr_key not in self._preference_cache:
            self._preference_cache[attr_key] = AggregatedPreference(
                attribute=attr_key,
                preferred_values={},
                avoided_values={},
                total_samples=0,
                confidence=0.0
            )
        
        pref = self._preference_cache[attr_key]
        pref.total_samples += 1
        pref.last_updated = datetime.now()
        
        # Update value counts based on feedback
        value = None
        if feedback.type == FeedbackType.EDIT and feedback.new_value:
            # Edit implies preference for new value, avoidance of old
            if feedback.old_value:
                pref.avoided_values[feedback.old_value] = pref.avoided_values.get(feedback.old_value, 0) + 1
            pref.preferred_values[feedback.new_value] = pref.preferred_values.get(feedback.new_value, 0) + 1
        elif feedback.context:
            # Extract value from context
            value = feedback.context.get(feedback.attribute) if feedback.attribute else None
            if value:
                if feedback.is_positive:
                    pref.preferred_values[value] = pref.preferred_values.get(value, 0) + 1
                elif feedback.is_negative:
                    pref.avoided_values[value] = pref.avoided_values.get(value, 0) + 1
        
        # Recalculate confidence
        pref.confidence = self._calculate_confidence(pref)
        
        # Persist if confidence is high enough
        if pref.confidence >= 0.6 and pref.total_samples >= self.MIN_SAMPLES_FOR_CONFIDENCE:
            await self._persist_preference(pref, feedback.brand_id)
    
    def _calculate_confidence(self, pref: AggregatedPreference) -> float:
        """
        Calculate confidence score for a preference.
        
        Factors:
        - Number of samples
        - Consistency of feedback
        - Recency of feedback
        """
        if pref.total_samples == 0:
            return 0.0
        
        # Sample count factor (sigmoid curve, plateaus around 10 samples)
        sample_factor = 1 - math.exp(-pref.total_samples / 5)
        
        # Consistency factor (how consistently the preference points one direction)
        total_positive = sum(pref.preferred_values.values())
        total_negative = sum(pref.avoided_values.values())
        total_votes = total_positive + total_negative
        
        if total_votes == 0:
            consistency = 0.5
        else:
            # How much does the dominant direction dominate?
            dominant = max(total_positive, total_negative)
            consistency = dominant / total_votes
        
        # Combine factors
        confidence = sample_factor * 0.4 + consistency * 0.6
        
        return round(min(1.0, confidence), 3)
    
    async def _persist_preference(self, pref: AggregatedPreference, brand_id: str):
        """Persist a learned preference to Neo4j."""
        if not self.db:
            return
        
        top_preferred = pref.get_top_preference()
        top_avoided = pref.get_top_avoidance()
        
        if not top_preferred:
            return
        
        query = """
        MATCH (b:Brand {id: $brand_id})
        MERGE (lp:LearnedPreference {attribute: $attribute})
        ON CREATE SET
            lp.id = $pref_id,
            lp.preferred_value = $preferred,
            lp.anti_preferred_value = $avoided,
            lp.confidence = $confidence,
            lp.sample_count = $samples,
            lp.positive_count = $positive_count,
            lp.negative_count = $negative_count,
            lp.created_at = datetime()
        ON MATCH SET
            lp.preferred_value = $preferred,
            lp.anti_preferred_value = $avoided,
            lp.confidence = $confidence,
            lp.sample_count = $samples,
            lp.positive_count = $positive_count,
            lp.negative_count = $negative_count,
            lp.last_updated = datetime()
        MERGE (b)-[:HAS_LEARNED_PREFERENCE]->(lp)
        """
        
        try:
            await self.db.execute_query(query, {
                "brand_id": brand_id,
                "pref_id": f"lp_{uuid.uuid4().hex[:8]}",
                "attribute": pref.attribute,
                "preferred": top_preferred,
                "avoided": top_avoided,
                "confidence": pref.confidence,
                "samples": pref.total_samples,
                "positive_count": sum(pref.preferred_values.values()),
                "negative_count": sum(pref.avoided_values.values())
            })
        except Exception as e:
            print(f"Error persisting preference: {e}")
    
    async def _check_negative_patterns(self, feedback: Feedback):
        """Check if feedback indicates a recurring negative pattern."""
        # Build pattern key
        pattern_key = f"{feedback.brand_id}:{feedback.element_type or 'global'}"
        if feedback.attribute:
            pattern_key += f":{feedback.attribute}"
        
        value = feedback.old_value or feedback.context.get(feedback.attribute, "") if feedback.context else ""
        
        if not value:
            return
        
        pattern_key += f":{value}"
        
        if pattern_key not in self._pattern_cache:
            self._pattern_cache[pattern_key] = NegativePatternLearned(
                pattern_key=pattern_key,
                element_type=feedback.element_type or "global",
                attribute=feedback.attribute,
                value=value,
                occurrence_count=0,
                severity="minor",
                first_seen=datetime.now(),
                last_seen=datetime.now(),
                example_generations=[]
            )
        
        pattern = self._pattern_cache[pattern_key]
        pattern.occurrence_count += 1
        pattern.last_seen = datetime.now()
        
        if feedback.generation_id not in pattern.example_generations:
            pattern.example_generations.append(feedback.generation_id)
        
        # Update severity based on occurrences
        if pattern.occurrence_count >= 5:
            pattern.severity = "critical"
        elif pattern.occurrence_count >= 3:
            pattern.severity = "major"
        
        # Persist if significant
        if pattern.is_significant:
            await self._persist_negative_pattern(pattern, feedback.brand_id)
    
    async def _persist_negative_pattern(self, pattern: NegativePatternLearned, brand_id: str):
        """Persist a negative pattern to Neo4j."""
        if not self.db:
            return
        
        query = """
        MATCH (b:Brand {id: $brand_id})
        MERGE (np:NegativePattern {pattern_key: $pattern_key})
        ON CREATE SET
            np.id = $pattern_id,
            np.element_type = $element_type,
            np.attribute = $attribute,
            np.pattern_description = $value,
            np.severity = $severity,
            np.occurrence_count = $count,
            np.example_generations = $examples,
            np.created_at = datetime()
        ON MATCH SET
            np.severity = $severity,
            np.occurrence_count = $count,
            np.example_generations = $examples,
            np.updated_at = datetime()
        MERGE (b)-[:AVOID_PATTERN]->(np)
        """
        
        try:
            await self.db.execute_query(query, {
                "brand_id": brand_id,
                "pattern_key": pattern.pattern_key,
                "pattern_id": f"np_{uuid.uuid4().hex[:8]}",
                "element_type": pattern.element_type,
                "attribute": pattern.attribute,
                "value": pattern.value,
                "severity": pattern.severity,
                "count": pattern.occurrence_count,
                "examples": json.dumps(pattern.example_generations[:5])  # Keep last 5
            })
        except Exception as e:
            print(f"Error persisting negative pattern: {e}")
    
    async def get_preferences_for_brand(
        self,
        brand_id: str,
        min_confidence: float = 0.5
    ) -> List[AggregatedPreference]:
        """Get all learned preferences for a brand."""
        if not self.db:
            # Return from cache
            return [p for p in self._preference_cache.values() if p.confidence >= min_confidence]
        
        query = """
        MATCH (b:Brand {id: $brand_id})-[:HAS_LEARNED_PREFERENCE]->(lp:LearnedPreference)
        WHERE lp.confidence >= $min_conf
        RETURN lp.attribute as attribute, lp.preferred_value as preferred,
               lp.anti_preferred_value as avoided, lp.confidence as confidence,
               lp.sample_count as samples, lp.positive_count as positive,
               lp.negative_count as negative
        ORDER BY lp.confidence DESC
        """
        
        preferences = []
        try:
            results = self.db.execute_query(query, {
                "brand_id": brand_id,
                "min_conf": min_confidence
            })
            
            for record in results:
                preferences.append(AggregatedPreference(
                    attribute=record["attribute"],
                    preferred_values={record["preferred"]: record.get("positive", 1)} if record.get("preferred") else {},
                    avoided_values={record["avoided"]: record.get("negative", 1)} if record.get("avoided") else {},
                    total_samples=record.get("samples", 1),
                    confidence=record["confidence"]
                ))
        except Exception as e:
            print(f"Error getting preferences: {e}")
        
        return preferences
    
    async def get_negative_patterns_for_brand(
        self,
        brand_id: str,
        min_severity: str = "minor"
    ) -> List[NegativePatternLearned]:
        """Get all negative patterns for a brand."""
        severity_order = {"minor": 1, "major": 2, "critical": 3}
        min_severity_num = severity_order.get(min_severity, 1)
        
        if not self.db:
            return [p for p in self._pattern_cache.values()
                    if severity_order.get(p.severity, 1) >= min_severity_num]
        
        query = """
        MATCH (b:Brand {id: $brand_id})-[:AVOID_PATTERN]->(np:NegativePattern)
        RETURN np.pattern_key as pattern_key, np.element_type as element_type,
               np.attribute as attribute, np.pattern_description as value,
               np.severity as severity, np.occurrence_count as count,
               np.example_generations as examples
        """
        
        patterns = []
        try:
            results = await self.db.execute_query(query, {"brand_id": brand_id})
            
            for record in results:
                if severity_order.get(record["severity"], 1) >= min_severity_num:
                    patterns.append(NegativePatternLearned(
                        pattern_key=record["pattern_key"],
                        element_type=record["element_type"],
                        attribute=record.get("attribute"),
                        value=record["value"],
                        occurrence_count=record["count"],
                        severity=record["severity"],
                        first_seen=datetime.now(),  # Not stored, approximating
                        last_seen=datetime.now(),
                        example_generations=json.loads(record.get("examples", "[]"))
                    ))
        except Exception as e:
            print(f"Error getting patterns: {e}")
        
        return patterns
    
    async def get_feedback_history(
        self,
        brand_id: str,
        generation_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Feedback]:
        """Get feedback history for a brand or specific generation."""
        if not self.db:
            # Return from cache
            feedbacks = []
            for key, fb_list in self._feedback_cache.items():
                if key.startswith(brand_id):
                    feedbacks.extend(fb_list)
            return sorted(feedbacks, key=lambda x: x.created_at, reverse=True)[:limit]
        
        query = """
        MATCH (f:Feedback)-[:ABOUT_GENERATION]->(g:Generation)
        WHERE g.brand_id = $brand_id
        """ + ("AND g.id = $gen_id" if generation_id else "") + """
        RETURN f.id as id, f.type as type, f.level as level,
               g.id as generation_id, g.brand_id as brand_id,
               f.element_type as element_type, f.element_id as element_id,
               f.attribute as attribute, f.old_value as old_value,
               f.new_value as new_value, f.comment as comment,
               f.context as context, f.created_at as created_at
        ORDER BY f.created_at DESC
        LIMIT $limit
        """
        
        params = {"brand_id": brand_id, "limit": limit}
        if generation_id:
            params["gen_id"] = generation_id
        
        feedbacks = []
        try:
            results = await self.db.execute_query(query, params)
            
            for record in results:
                feedbacks.append(Feedback(
                    id=record["id"],
                    type=FeedbackType(record["type"]),
                    level=FeedbackLevel(record.get("level", "whole")),
                    generation_id=record["generation_id"],
                    brand_id=record["brand_id"],
                    element_type=record.get("element_type"),
                    element_id=record.get("element_id"),
                    attribute=record.get("attribute"),
                    old_value=record.get("old_value"),
                    new_value=record.get("new_value"),
                    comment=record.get("comment"),
                    context=json.loads(record.get("context", "{}")) if record.get("context") else {}
                ))
        except Exception as e:
            print(f"Error getting feedback history: {e}")
        
        return feedbacks
    
    def get_learning_summary(self, brand_id: str) -> Dict[str, Any]:
        """Get a summary of what has been learned for a brand."""
        preferences = [p for p in self._preference_cache.values()]
        patterns = [p for p in self._pattern_cache.values() if p.is_significant]
        
        # Aggregate feedback counts
        total_feedback = sum(len(fb_list) for fb_list in self._feedback_cache.values())
        positive_count = sum(
            1 for fb_list in self._feedback_cache.values()
            for fb in fb_list if fb.is_positive
        )
        negative_count = sum(
            1 for fb_list in self._feedback_cache.values()
            for fb in fb_list if fb.is_negative
        )
        
        return {
            "total_feedback": total_feedback,
            "positive_feedback": positive_count,
            "negative_feedback": negative_count,
            "learned_preferences": len(preferences),
            "high_confidence_preferences": len([p for p in preferences if p.confidence >= 0.7]),
            "negative_patterns": len(patterns),
            "critical_patterns": len([p for p in patterns if p.severity == "critical"]),
            "top_preferences": [
                {"attribute": p.attribute, "value": p.get_top_preference(), "confidence": p.confidence}
                for p in sorted(preferences, key=lambda x: x.confidence, reverse=True)[:5]
            ],
            "key_avoidances": [
                {"element": p.element_type, "pattern": p.value, "severity": p.severity}
                for p in patterns if p.severity in ["major", "critical"]
            ][:5]
        }
