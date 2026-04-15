"""
GraphRAG Constraint Resolution System
======================================
This module implements multi-hop graph traversal for constraint gathering and
conflict resolution. It queries the Neo4j knowledge graph to:
- Retrieve brand-specific constraints
- Gather learned preferences with confidence scores
- Identify negative patterns to avoid
- Resolve conflicts between competing constraints
- Build element-specific constraint sets

Part of Capstone Research: GraphRAG-Guided Compositional Image Generation
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
import json
from datetime import datetime

from .scene_decomposition import ElementType, SceneElement, SceneGraph


class ConstraintType(str, Enum):
    """Types of constraints in the system."""
    MUST_INCLUDE = "MUST_INCLUDE"      # Hard requirement to include
    MUST_AVOID = "MUST_AVOID"          # Hard requirement to avoid
    PREFER = "PREFER"                  # Soft preference to include
    DISCOURAGE = "DISCOURAGE"          # Soft preference to avoid


class ConstraintTarget(str, Enum):
    """What aspect the constraint targets."""
    COLOR = "color"
    STYLE = "style"
    COMPOSITION = "composition"
    CONTENT = "content"
    TEXT = "text"
    LIGHTING = "lighting"
    MOOD = "mood"
    MATERIAL = "material"


class ConstraintSource(str, Enum):
    """Origin of the constraint."""
    BRAND_GUIDELINE = "brand_guideline"
    LEGAL = "legal"
    USER_FEEDBACK = "user_feedback"
    LEARNED = "learned"
    SYSTEM_DEFAULT = "system_default"


@dataclass
class Constraint:
    """A single constraint that affects generation."""
    id: str
    type: ConstraintType
    strength: float  # 0-1, soft to hard
    scope: str  # 'global', 'element_type', 'specific_element'
    target_type: ConstraintTarget
    target_value: str
    description: str
    reason: ConstraintSource
    applies_to: str  # Element type or 'all'
    confidence: float = 1.0  # For learned constraints
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "strength": self.strength,
            "scope": self.scope,
            "target_type": self.target_type.value,
            "target_value": self.target_value,
            "description": self.description,
            "reason": self.reason.value,
            "applies_to": self.applies_to,
            "confidence": self.confidence
        }
    
    @classmethod
    def from_neo4j(cls, record: Dict) -> "Constraint":
        """Create Constraint from Neo4j record."""
        return cls(
            id=record.get("id", "unknown"),
            type=ConstraintType(record.get("type", "PREFER")),
            strength=record.get("strength", 0.5),
            scope=record.get("scope", "global"),
            target_type=ConstraintTarget(record.get("target_type", "style")),
            target_value=record.get("target_value", ""),
            description=record.get("description", ""),
            reason=ConstraintSource(record.get("reason", "system_default")),
            applies_to=record.get("applies_to", "all"),
            confidence=record.get("confidence", 1.0)
        )
    
    @property
    def effective_strength(self) -> float:
        """Strength weighted by confidence for learned constraints."""
        return self.strength * self.confidence


@dataclass
class LearnedPreference:
    """A preference learned from user feedback."""
    id: str
    attribute: str  # e.g., 'SUBJECT_lighting', 'color_saturation'
    preferred_value: str
    anti_preferred_value: Optional[str] = None
    confidence: float = 0.5
    sample_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "attribute": self.attribute,
            "preferred_value": self.preferred_value,
            "anti_preferred_value": self.anti_preferred_value,
            "confidence": self.confidence,
            "sample_count": self.sample_count
        }
    
    @classmethod
    def from_neo4j(cls, record: Dict) -> "LearnedPreference":
        return cls(
            id=record.get("id", "unknown"),
            attribute=record.get("attribute", ""),
            preferred_value=record.get("preferred_value", ""),
            anti_preferred_value=record.get("anti_preferred_value"),
            confidence=record.get("confidence", 0.5),
            sample_count=record.get("sample_count", 0),
            positive_count=record.get("positive_count", 0),
            negative_count=record.get("negative_count", 0)
        )
    
    def to_constraint(self) -> Constraint:
        """Convert learned preference to a constraint."""
        return Constraint(
            id=f"learned_{self.id}",
            type=ConstraintType.PREFER,
            strength=min(0.8, self.confidence),  # Cap learned constraint strength
            scope="element_type" if "_" in self.attribute else "global",
            target_type=ConstraintTarget.STYLE,
            target_value=self.preferred_value,
            description=f"Learned preference: {self.attribute} should be {self.preferred_value}",
            reason=ConstraintSource.LEARNED,
            applies_to=self.attribute.split("_")[0] if "_" in self.attribute else "all",
            confidence=self.confidence
        )


@dataclass
class NegativePattern:
    """A pattern to avoid based on past negative feedback."""
    id: str
    element_type: str
    pattern_description: str
    severity: str  # 'minor', 'major', 'critical'
    occurrence_count: int = 1
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "element_type": self.element_type,
            "pattern_description": self.pattern_description,
            "severity": self.severity,
            "occurrence_count": self.occurrence_count
        }
    
    def to_constraint(self) -> Constraint:
        """Convert negative pattern to an avoidance constraint."""
        strength_map = {"minor": 0.5, "major": 0.8, "critical": 1.0}
        return Constraint(
            id=f"avoid_{self.id}",
            type=ConstraintType.MUST_AVOID,
            strength=strength_map.get(self.severity, 0.7),
            scope="element_type",
            target_type=ConstraintTarget.CONTENT,
            target_value=self.pattern_description,
            description=f"Avoid: {self.pattern_description} (negative feedback x{self.occurrence_count})",
            reason=ConstraintSource.USER_FEEDBACK,
            applies_to=self.element_type,
            confidence=min(1.0, 0.5 + 0.1 * self.occurrence_count)  # Confidence grows with occurrences
        )


@dataclass
class ResolvedConstraintSet:
    """A resolved set of constraints for generation."""
    global_constraints: List[Constraint]
    element_constraints: Dict[str, List[Constraint]]  # element_type -> constraints
    positive_prompts: List[str]  # Things to include
    negative_prompts: List[str]  # Things to avoid
    style_guidance: Dict[str, str]  # Attribute -> value
    conflict_resolutions: List[Dict]  # Record of resolved conflicts
    
    def to_dict(self) -> Dict:
        return {
            "global_constraints": [c.to_dict() for c in self.global_constraints],
            "element_constraints": {
                k: [c.to_dict() for c in v] for k, v in self.element_constraints.items()
            },
            "positive_prompts": self.positive_prompts,
            "negative_prompts": self.negative_prompts,
            "style_guidance": self.style_guidance,
            "conflict_resolutions": self.conflict_resolutions
        }


class ConstraintResolutionEngine:
    """
    Engine for querying and resolving constraints from the knowledge graph.
    
    This implements the multi-hop reasoning component of GraphRAG:
    1. Query brand constraints from Neo4j
    2. Retrieve learned preferences
    3. Identify negative patterns
    4. Resolve conflicts based on strength/confidence
    5. Compile into generation-ready constraint set
    """
    
    def __init__(self, neo4j_client):
        """
        Initialize the constraint resolution engine.
        
        Args:
            neo4j_client: Neo4j database client for graph queries
        """
        self.db = neo4j_client
    
    async def gather_constraints(
        self,
        brand_id: str,
        scene_graph: Optional[SceneGraph] = None
    ) -> ResolvedConstraintSet:
        """
        Gather and resolve all constraints for a generation request.
        
        Args:
            brand_id: The brand identifier
            scene_graph: Optional scene graph for element-specific constraints
            
        Returns:
            ResolvedConstraintSet ready for prompt compilation
        """
        # Step 1: Get brand constraints from graph
        brand_constraints = await self._query_brand_constraints(brand_id)
        
        # Step 2: Get learned preferences
        learned_preferences = await self._query_learned_preferences(brand_id)
        
        # Step 3: Get negative patterns to avoid
        negative_patterns = await self._query_negative_patterns(brand_id)
        
        # Step 4: Get color harmonies and relationships
        color_guidance = await self._query_color_relationships(brand_id)
        
        # Step 5: Convert learned data to constraints
        all_constraints = brand_constraints.copy()
        for pref in learned_preferences:
            if pref.confidence >= 0.6:  # Only use confident preferences
                all_constraints.append(pref.to_constraint())
        
        for pattern in negative_patterns:
            all_constraints.append(pattern.to_constraint())
        
        # Step 6: Resolve conflicts
        resolved_global, resolved_element, conflicts = self._resolve_conflicts(
            all_constraints, scene_graph
        )
        
        # Step 7: Compile into prompt components
        positive_prompts, negative_prompts = self._compile_prompts(
            resolved_global, resolved_element, color_guidance
        )
        
        # Step 8: Extract style guidance
        style_guidance = self._extract_style_guidance(resolved_global, resolved_element)
        
        return ResolvedConstraintSet(
            global_constraints=resolved_global,
            element_constraints=resolved_element,
            positive_prompts=positive_prompts,
            negative_prompts=negative_prompts,
            style_guidance=style_guidance,
            conflict_resolutions=conflicts
        )
    
    async def _query_brand_constraints(self, brand_id: str) -> List[Constraint]:
        """Query explicit brand constraints from Neo4j."""
        query = """
        MATCH (b:Brand {id: $brand_id})-[:HAS_CONSTRAINT]->(c:Constraint)
        WHERE c.expires_at IS NULL OR c.expires_at > datetime()
        RETURN c.id as id, c.type as type, c.strength as strength,
               c.scope as scope, c.target_type as target_type,
               c.target_value as target_value, c.description as description,
               c.reason as reason, c.applies_to as applies_to
        ORDER BY c.strength DESC
        """
        
        constraints = []
        try:
            results = await self.db.execute_query(query, {"brand_id": brand_id})
            for record in results:
                try:
                    constraints.append(Constraint.from_neo4j(record))
                except (ValueError, KeyError) as e:
                    print(f"Warning: Could not parse constraint: {e}")
        except Exception as e:
            print(f"Error querying brand constraints: {e}")
        
        return constraints
    
    async def _query_learned_preferences(self, brand_id: str) -> List[LearnedPreference]:
        """Query learned preferences from feedback aggregation."""
        query = """
        MATCH (b:Brand {id: $brand_id})-[:HAS_LEARNED_PREFERENCE]->(lp:LearnedPreference)
        WHERE lp.confidence >= 0.5 AND lp.sample_count >= 3
        RETURN lp.id as id, lp.attribute as attribute,
               lp.preferred_value as preferred_value,
               lp.anti_preferred_value as anti_preferred_value,
               lp.confidence as confidence, lp.sample_count as sample_count,
               lp.positive_count as positive_count, lp.negative_count as negative_count
        ORDER BY lp.confidence DESC
        LIMIT 20
        """
        
        preferences = []
        try:
            results = await self.db.execute_query(query, {"brand_id": brand_id})
            for record in results:
                try:
                    preferences.append(LearnedPreference.from_neo4j(record))
                except (ValueError, KeyError) as e:
                    print(f"Warning: Could not parse preference: {e}")
        except Exception as e:
            print(f"Error querying learned preferences: {e}")
        
        return preferences
    
    async def _query_negative_patterns(self, brand_id: str) -> List[NegativePattern]:
        """Query negative patterns to avoid."""
        query = """
        MATCH (b:Brand {id: $brand_id})-[:AVOID_PATTERN]->(np:NegativePattern)
        RETURN np.id as id, np.element_type as element_type,
               np.pattern_description as pattern_description,
               np.severity as severity, np.occurrence_count as occurrence_count
        ORDER BY np.occurrence_count DESC
        LIMIT 15
        """
        
        patterns = []
        try:
            results = await self.db.execute_query(query, {"brand_id": brand_id})
            for record in results:
                patterns.append(NegativePattern(
                    id=record.get("id", "unknown"),
                    element_type=record.get("element_type", "all"),
                    pattern_description=record.get("pattern_description", ""),
                    severity=record.get("severity", "minor"),
                    occurrence_count=record.get("occurrence_count", 1)
                ))
        except Exception as e:
            print(f"Error querying negative patterns: {e}")
        
        return patterns
    
    async def _query_color_relationships(self, brand_id: str) -> Dict[str, Any]:
        """Query color harmonies and brand color relationships."""
        query = """
        MATCH (b:Brand {id: $brand_id})-[r:USES_COLOR]->(c:Color)
        OPTIONAL MATCH (c)-[h:HARMONIZES_WITH]->(c2:Color)
        OPTIONAL MATCH (c)-[:CONTRASTS_WITH]->(c3:Color)
        RETURN c.hex as hex, c.name as name, r.role as role,
               collect(DISTINCT {harmony_color: c2.hex, harmony_type: h.harmony_type}) as harmonies,
               collect(DISTINCT c3.hex) as contrasts
        """
        
        color_guidance = {
            "primary_colors": [],
            "secondary_colors": [],
            "accent_colors": [],
            "harmonies": [],
            "avoid_colors": []
        }
        
        try:
            results = await self.db.execute_query(query, {"brand_id": brand_id})
            for record in results:
                hex_val = record.get("hex")
                role = record.get("role", "secondary")
                
                if role == "primary":
                    color_guidance["primary_colors"].append(hex_val)
                elif role == "secondary":
                    color_guidance["secondary_colors"].append(hex_val)
                elif role == "accent":
                    color_guidance["accent_colors"].append(hex_val)
                
                # Add harmonies
                for harmony in record.get("harmonies", []):
                    if harmony.get("harmony_color"):
                        color_guidance["harmonies"].append(harmony)
        except Exception as e:
            print(f"Error querying color relationships: {e}")
        
        return color_guidance
    
    def _resolve_conflicts(
        self,
        constraints: List[Constraint],
        scene_graph: Optional[SceneGraph]
    ) -> Tuple[List[Constraint], Dict[str, List[Constraint]], List[Dict]]:
        """
        Resolve conflicts between constraints.
        
        Priority order:
        1. Hard constraints (strength >= 0.9) always win
        2. Brand guidelines over learned preferences
        3. Higher confidence wins for learned preferences
        4. More specific scope wins over general
        
        Returns:
            Tuple of (global_constraints, element_constraints, conflict_records)
        """
        global_constraints = []
        element_constraints: Dict[str, List[Constraint]] = {}
        conflict_records = []
        
        # Separate by scope
        global_pool = [c for c in constraints if c.scope == "global" or c.applies_to == "all"]
        element_pool = [c for c in constraints if c.scope == "element_type" and c.applies_to != "all"]
        
        # Resolve global constraints
        global_constraints = self._resolve_constraint_pool(global_pool, conflict_records)
        
        # Resolve element-specific constraints
        element_types = set(c.applies_to for c in element_pool)
        if scene_graph:
            element_types.update(e.type.value for e in scene_graph.elements)
        
        for elem_type in element_types:
            pool = [c for c in element_pool if c.applies_to == elem_type]
            # Also include global constraints that might apply
            applicable_global = [c for c in global_constraints if self._constraint_applies_to_element(c, elem_type)]
            combined_pool = pool + applicable_global
            element_constraints[elem_type] = self._resolve_constraint_pool(combined_pool, conflict_records)
        
        return global_constraints, element_constraints, conflict_records
    
    def _resolve_constraint_pool(
        self,
        constraints: List[Constraint],
        conflict_records: List[Dict]
    ) -> List[Constraint]:
        """Resolve conflicts within a constraint pool."""
        if not constraints:
            return []
        
        resolved = []
        
        # Group by target
        by_target: Dict[str, List[Constraint]] = {}
        for c in constraints:
            key = f"{c.target_type.value}:{c.target_value}"
            if key not in by_target:
                by_target[key] = []
            by_target[key].append(c)
        
        for target_key, group in by_target.items():
            if len(group) == 1:
                resolved.append(group[0])
            else:
                # Conflict - resolve by priority
                winner = self._pick_winner(group)
                resolved.append(winner)
                
                # Record conflict
                conflict_records.append({
                    "target": target_key,
                    "constraints": [c.id for c in group],
                    "winner": winner.id,
                    "reason": self._explain_resolution(winner, group)
                })
        
        # Check for include/avoid conflicts
        include_targets = {c.target_value for c in resolved if c.type == ConstraintType.MUST_INCLUDE}
        avoid_targets = {c.target_value for c in resolved if c.type == ConstraintType.MUST_AVOID}
        
        conflicts = include_targets & avoid_targets
        if conflicts:
            for conflict_value in conflicts:
                include_c = next(c for c in resolved if c.type == ConstraintType.MUST_INCLUDE and c.target_value == conflict_value)
                avoid_c = next(c for c in resolved if c.type == ConstraintType.MUST_AVOID and c.target_value == conflict_value)
                
                # Hard avoid always wins
                if avoid_c.strength >= 0.9:
                    resolved.remove(include_c)
                    conflict_records.append({
                        "target": conflict_value,
                        "type": "include_avoid_conflict",
                        "winner": avoid_c.id,
                        "reason": "Hard avoidance constraint takes precedence"
                    })
                else:
                    # Strongest wins
                    if include_c.effective_strength > avoid_c.effective_strength:
                        resolved.remove(avoid_c)
                        conflict_records.append({
                            "target": conflict_value,
                            "winner": include_c.id,
                            "reason": "Stronger inclusion constraint"
                        })
                    else:
                        resolved.remove(include_c)
                        conflict_records.append({
                            "target": conflict_value,
                            "winner": avoid_c.id,
                            "reason": "Stronger avoidance constraint"
                        })
        
        return resolved
    
    def _pick_winner(self, constraints: List[Constraint]) -> Constraint:
        """Pick the winning constraint from a conflicting set."""
        # Sort by priority
        def priority_key(c: Constraint) -> Tuple:
            source_priority = {
                ConstraintSource.LEGAL: 4,
                ConstraintSource.BRAND_GUIDELINE: 3,
                ConstraintSource.USER_FEEDBACK: 2,
                ConstraintSource.LEARNED: 1,
                ConstraintSource.SYSTEM_DEFAULT: 0
            }
            return (
                c.strength >= 0.9,  # Hard constraints first
                source_priority.get(c.reason, 0),
                c.effective_strength,
                c.confidence
            )
        
        return max(constraints, key=priority_key)
    
    def _explain_resolution(self, winner: Constraint, competitors: List[Constraint]) -> str:
        """Explain why a constraint won."""
        if winner.strength >= 0.9:
            return "Hard constraint (strength >= 0.9)"
        if winner.reason == ConstraintSource.BRAND_GUIDELINE:
            return "Brand guideline takes precedence"
        if winner.reason == ConstraintSource.LEGAL:
            return "Legal requirement takes precedence"
        return f"Highest effective strength ({winner.effective_strength:.2f})"
    
    def _constraint_applies_to_element(self, constraint: Constraint, element_type: str) -> bool:
        """Check if a constraint applies to a specific element type."""
        if constraint.applies_to == "all":
            return True
        return constraint.applies_to.upper() == element_type.upper()
    
    def _compile_prompts(
        self,
        global_constraints: List[Constraint],
        element_constraints: Dict[str, List[Constraint]],
        color_guidance: Dict[str, Any]
    ) -> Tuple[List[str], List[str]]:
        """Compile constraints into positive and negative prompt components."""
        positive = []
        negative = []
        
        # Process global constraints
        for c in global_constraints:
            if c.type == ConstraintType.MUST_INCLUDE:
                positive.append(c.target_value)
            elif c.type == ConstraintType.MUST_AVOID:
                negative.append(c.target_value)
            elif c.type == ConstraintType.PREFER:
                positive.append(c.target_value)
            elif c.type == ConstraintType.DISCOURAGE:
                negative.append(c.target_value)
        
        # Add color guidance
        if color_guidance.get("primary_colors"):
            primary = color_guidance["primary_colors"][0]
            positive.append(f"color palette featuring {primary}")
        
        # Add avoid colors
        for color in color_guidance.get("avoid_colors", []):
            negative.append(f"{color} color")
        
        return positive, negative
    
    def _extract_style_guidance(
        self,
        global_constraints: List[Constraint],
        element_constraints: Dict[str, List[Constraint]]
    ) -> Dict[str, str]:
        """Extract specific style guidance from constraints."""
        guidance = {}
        
        style_targets = [ConstraintTarget.LIGHTING, ConstraintTarget.MOOD, ConstraintTarget.STYLE]
        
        for c in global_constraints:
            if c.target_type in style_targets and c.type in [ConstraintType.MUST_INCLUDE, ConstraintType.PREFER]:
                guidance[c.target_type.value] = c.target_value
        
        # Element-specific styles
        for elem_type, constraints in element_constraints.items():
            for c in constraints:
                if c.target_type in style_targets and c.type in [ConstraintType.MUST_INCLUDE, ConstraintType.PREFER]:
                    guidance[f"{elem_type}_{c.target_type.value}"] = c.target_value
        
        return guidance


# Utility function for quick constraint creation
def create_constraint(
    constraint_type: str,
    target_type: str,
    target_value: str,
    strength: float = 0.7,
    description: str = "",
    applies_to: str = "all"
) -> Constraint:
    """Quick helper to create a constraint."""
    import uuid
    return Constraint(
        id=f"con_{uuid.uuid4().hex[:8]}",
        type=ConstraintType(constraint_type),
        strength=strength,
        scope="element_type" if applies_to != "all" else "global",
        target_type=ConstraintTarget(target_type),
        target_value=target_value,
        description=description or f"{constraint_type}: {target_value}",
        reason=ConstraintSource.SYSTEM_DEFAULT,
        applies_to=applies_to
    )
