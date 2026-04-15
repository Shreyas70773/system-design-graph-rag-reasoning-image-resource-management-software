"""
Structured Prompt Compilation Engine
=====================================
This module compiles scene graphs, constraints, and learned preferences into
optimized prompts for image generation models. It translates the semantic
understanding from GraphRAG into effective generation instructions.

Key Features:
- Scene graph to prompt translation
- Constraint injection into prompts
- Negative prompt construction
- Element-specific guidance encoding
- Model-specific prompt formatting
- Prompt optimization and deduplication

Part of Capstone Research: GraphRAG-Guided Compositional Image Generation
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
import json
from enum import Enum

from .scene_decomposition import SceneGraph, SceneElement, ElementType, StyleAttributes
from .constraint_resolver import ResolvedConstraintSet, Constraint, ConstraintType


class PromptStyle(str, Enum):
    """Prompt formatting styles for different models."""
    SDXL = "sdxl"              # Stable Diffusion XL format
    DALLE = "dalle"            # DALL-E style prompting
    MIDJOURNEY = "midjourney"  # Midjourney-style formatting
    FLUX = "flux"              # Flux model format
    GENERIC = "generic"        # Generic format


@dataclass
class CompiledPrompt:
    """A fully compiled prompt ready for generation."""
    positive_prompt: str
    negative_prompt: str
    element_prompts: Dict[str, str]  # element_id -> specific guidance
    style_modifiers: List[str]
    quality_modifiers: List[str]
    composition_guidance: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "positive_prompt": self.positive_prompt,
            "negative_prompt": self.negative_prompt,
            "element_prompts": self.element_prompts,
            "style_modifiers": self.style_modifiers,
            "quality_modifiers": self.quality_modifiers,
            "composition_guidance": self.composition_guidance,
            "metadata": self.metadata
        }
    
    def get_full_positive(self) -> str:
        """Get the complete positive prompt with all modifiers."""
        parts = [self.positive_prompt]
        
        if self.composition_guidance:
            parts.append(self.composition_guidance)
        
        if self.style_modifiers:
            parts.extend(self.style_modifiers)
        
        if self.quality_modifiers:
            parts.extend(self.quality_modifiers)
        
        return ", ".join(filter(None, parts))
    
    def get_full_negative(self) -> str:
        """Get the complete negative prompt."""
        return self.negative_prompt


class PromptCompilationEngine:
    """
    Engine for compiling semantic scene understanding into generation prompts.
    
    This is the final step in the GraphRAG pipeline:
    1. Take scene graph (what to generate)
    2. Apply resolved constraints (how to generate)
    3. Incorporate learned preferences
    4. Output optimized prompts for the target model
    """
    
    # Quality boosters for better image generation
    QUALITY_BOOSTERS = {
        "high_quality": [
            "masterpiece",
            "best quality",
            "highly detailed",
            "professional photography"
        ],
        "medium_quality": [
            "high quality",
            "detailed",
            "well-composed"
        ],
        "commercial": [
            "commercial photography",
            "advertising quality",
            "professionally lit",
            "studio quality"
        ]
    }
    
    # Standard negative prompts by category
    NEGATIVE_STANDARDS = {
        "quality": [
            "low quality",
            "blurry",
            "pixelated",
            "jpeg artifacts",
            "compression artifacts",
            "noisy",
            "grainy"
        ],
        "anatomy": [
            "deformed",
            "disfigured",
            "bad anatomy",
            "extra limbs",
            "missing limbs",
            "mutated"
        ],
        "text": [
            "watermark",
            "signature",
            "text",
            "logo",
            "username"
        ],
        "composition": [
            "cropped",
            "out of frame",
            "cut off",
            "poorly framed"
        ]
    }
    
    # Element type to prompt keywords mapping
    ELEMENT_KEYWORDS = {
        ElementType.BACKGROUND: {
            "emphasis": "background featuring",
            "lighting": ["ambient lighting", "environmental lighting"],
            "depth": "establishing shot"
        },
        ElementType.SUBJECT: {
            "emphasis": "main focus on",
            "lighting": ["key light on subject", "subject lighting"],
            "depth": "shallow depth of field"
        },
        ElementType.PRODUCT: {
            "emphasis": "product photography of",
            "lighting": ["product lighting", "soft box lighting"],
            "depth": "product showcase"
        },
        ElementType.CHARACTER: {
            "emphasis": "portrait of",
            "lighting": ["portrait lighting", "rim lighting"],
            "depth": "character focus"
        },
        ElementType.TEXT_AREA: {
            "emphasis": "clean space for text",
            "lighting": ["even lighting for text area"],
            "depth": "text-friendly background"
        },
        ElementType.ACCENT: {
            "emphasis": "decorative elements",
            "lighting": ["accent lighting"],
            "depth": "complementary elements"
        }
    }
    
    def __init__(self, prompt_style: PromptStyle = PromptStyle.SDXL):
        """
        Initialize the prompt compilation engine.
        
        Args:
            prompt_style: Target model prompt format
        """
        self.prompt_style = prompt_style
    
    def compile(
        self,
        scene_graph: SceneGraph,
        constraint_set: ResolvedConstraintSet,
        brand_context: Optional[Dict] = None,
        character_guidance: Optional[Dict] = None,
        quality_level: str = "high_quality"
    ) -> CompiledPrompt:
        """
        Compile a complete prompt from scene graph and constraints.
        
        Args:
            scene_graph: Decomposed scene structure
            constraint_set: Resolved constraints
            brand_context: Optional brand information
            character_guidance: Optional character consistency guidance
            quality_level: Quality preset to use
            
        Returns:
            CompiledPrompt ready for generation
        """
        # Step 1: Build base prompt from scene graph
        base_prompt = self._compile_scene_to_prompt(scene_graph)
        
        # Step 2: Apply constraint additions
        constrained_prompt, constraint_negatives = self._apply_constraints(
            base_prompt, constraint_set
        )
        
        # Step 3: Add brand context
        if brand_context:
            constrained_prompt = self._inject_brand_context(
                constrained_prompt, brand_context
            )
        
        # Step 4: Add character consistency guidance
        if character_guidance:
            constrained_prompt, char_negatives = self._apply_character_guidance(
                constrained_prompt, character_guidance
            )
            constraint_negatives.extend(char_negatives)
        
        # Step 5: Build element-specific prompts
        element_prompts = self._build_element_prompts(
            scene_graph, constraint_set
        )
        
        # Step 6: Compile negative prompt
        negative_prompt = self._compile_negative_prompt(
            constraint_set.negative_prompts + constraint_negatives
        )
        
        # Step 7: Add quality boosters
        quality_mods = self.QUALITY_BOOSTERS.get(quality_level, [])
        
        # Step 8: Extract style modifiers
        style_mods = self._extract_style_modifiers(
            scene_graph, constraint_set.style_guidance
        )
        
        # Step 9: Build composition guidance
        composition = self._build_composition_guidance(scene_graph)
        
        # Step 10: Optimize and deduplicate
        final_prompt = self._optimize_prompt(constrained_prompt)
        final_negative = self._optimize_prompt(negative_prompt)
        
        return CompiledPrompt(
            positive_prompt=final_prompt,
            negative_prompt=final_negative,
            element_prompts=element_prompts,
            style_modifiers=style_mods,
            quality_modifiers=quality_mods,
            composition_guidance=composition,
            metadata={
                "scene_graph_id": scene_graph.id,
                "constraint_count": len(constraint_set.global_constraints),
                "element_count": len(scene_graph.elements),
                "prompt_style": self.prompt_style.value
            }
        )
    
    def _compile_scene_to_prompt(self, scene_graph: SceneGraph) -> str:
        """Convert scene graph to base prompt text."""
        parts = []
        
        # Start with original prompt essence
        parts.append(scene_graph.original_prompt)
        
        # Add mood/atmosphere
        if scene_graph.overall_mood:
            parts.append(f"{scene_graph.overall_mood} atmosphere")
        
        # Add layout guidance
        layout_descriptions = {
            "centered": "centered composition",
            "rule_of_thirds": "rule of thirds composition",
            "asymmetric": "dynamic asymmetric layout",
            "golden_ratio": "golden ratio composition",
            "diagonal": "diagonal composition",
            "z_pattern": "z-pattern layout"
        }
        
        layout_desc = layout_descriptions.get(scene_graph.layout_type.value)
        if layout_desc:
            parts.append(layout_desc)
        
        # Add key elements with importance weighting
        sorted_elements = sorted(
            scene_graph.elements,
            key=lambda e: e.importance,
            reverse=True
        )
        
        for elem in sorted_elements[:3]:  # Top 3 most important
            elem_desc = self._describe_element(elem)
            if elem_desc:
                parts.append(elem_desc)
        
        return ", ".join(filter(None, parts))
    
    def _describe_element(self, element: SceneElement) -> str:
        """Generate description for a scene element."""
        parts = []
        
        # Element type specific keywords
        keywords = self.ELEMENT_KEYWORDS.get(element.type, {})
        if "emphasis" in keywords:
            parts.append(f"{keywords['emphasis']} {element.semantic_label}")
        else:
            parts.append(element.semantic_label)
        
        # Add style attributes
        style = element.style_attributes
        if style.lighting:
            parts.append(f"{style.lighting} lighting")
        if style.mood:
            parts.append(f"{style.mood} mood")
        if style.material:
            parts.append(f"{style.material} material")
        
        # Position guidance for composition
        position_terms = {
            "center": "in the center",
            "rule-of-thirds-left": "positioned at left third",
            "rule-of-thirds-right": "positioned at right third",
            "top-center": "at the top",
            "bottom-center": "at the bottom"
        }
        
        pos_term = position_terms.get(element.spatial_position.value)
        if pos_term and element.importance >= 0.7:
            parts.append(pos_term)
        
        return ", ".join(parts)
    
    def _apply_constraints(
        self,
        base_prompt: str,
        constraint_set: ResolvedConstraintSet
    ) -> Tuple[str, List[str]]:
        """Apply constraints to prompt, return modified prompt and negatives."""
        additions = []
        negatives = []
        
        for constraint in constraint_set.global_constraints:
            if constraint.type == ConstraintType.MUST_INCLUDE:
                additions.append(constraint.target_value)
            elif constraint.type == ConstraintType.PREFER:
                if constraint.effective_strength >= 0.7:
                    additions.append(constraint.target_value)
            elif constraint.type == ConstraintType.MUST_AVOID:
                negatives.append(constraint.target_value)
            elif constraint.type == ConstraintType.DISCOURAGE:
                if constraint.effective_strength >= 0.7:
                    negatives.append(constraint.target_value)
        
        # Add positive constraints
        if additions:
            prompt_with_constraints = f"{base_prompt}, {', '.join(additions)}"
        else:
            prompt_with_constraints = base_prompt
        
        return prompt_with_constraints, negatives
    
    def _inject_brand_context(self, prompt: str, brand_context: Dict) -> str:
        """Inject brand-specific context into prompt."""
        additions = []
        
        # Color palette - handle both string and dict formats with None safety
        colors = brand_context.get("colors", [])
        if colors:
            color_strs = []
            for c in colors[:3]:
                if isinstance(c, dict):
                    color_val = c.get('hex') or c.get('name')
                    if color_val:
                        color_strs.append(str(color_val))
                elif c:
                    color_strs.append(str(c))
            if color_strs:
                color_str = " and ".join(color_strs)
                additions.append(f"color palette featuring {color_str}")
        
        # Industry-specific styling
        industry = (brand_context.get("industry") or "").lower()
        industry_styles = {
            "food & beverage": "appetizing, inviting presentation",
            "technology": "modern, sleek aesthetic",
            "fashion": "stylish, trendy look",
            "luxury": "elegant, premium quality",
            "health": "clean, fresh appearance",
            "entertainment": "dynamic, engaging visual"
        }
        
        for key, style in industry_styles.items():
            if key in industry:
                additions.append(style)
                break
        
        # Brand mood/tagline influence
        tagline = brand_context.get("tagline") or ""
        if tagline:
            # Extract mood words from tagline
            mood_words = ["warm", "fresh", "bold", "elegant", "vibrant", "calm", "energetic"]
            tagline_lower = tagline.lower()
            for word in mood_words:
                if word in tagline_lower:
                    additions.append(f"{word} feeling")
                    break
        
        if additions:
            return f"{prompt}, {', '.join(additions)}"
        return prompt
    
    def _apply_character_guidance(
        self,
        prompt: str,
        character_guidance: Dict
    ) -> Tuple[str, List[str]]:
        """Apply character consistency guidance."""
        positive_addition = character_guidance.get("positive", "")
        negative_parts = character_guidance.get("negative", "").split(", ")
        
        if positive_addition:
            prompt = f"{prompt}, {positive_addition}"
        
        return prompt, negative_parts
    
    def _build_element_prompts(
        self,
        scene_graph: SceneGraph,
        constraint_set: ResolvedConstraintSet
    ) -> Dict[str, str]:
        """Build element-specific prompt guidance."""
        element_prompts = {}
        
        for element in scene_graph.elements:
            elem_parts = [element.semantic_label]
            
            # Add element-specific constraints
            elem_type_key = element.type.value
            if elem_type_key in constraint_set.element_constraints:
                for constraint in constraint_set.element_constraints[elem_type_key]:
                    if constraint.type in [ConstraintType.MUST_INCLUDE, ConstraintType.PREFER]:
                        elem_parts.append(constraint.target_value)
            
            # Add style attributes
            style = element.style_attributes
            style_parts = []
            if style.lighting:
                style_parts.append(f"{style.lighting} lighting")
            if style.material:
                style_parts.append(f"{style.material}")
            if style.depth_of_field:
                style_parts.append(f"{style.depth_of_field} depth of field")
            
            if style_parts:
                elem_parts.extend(style_parts)
            
            element_prompts[element.id] = ", ".join(elem_parts)
        
        return element_prompts
    
    def _compile_negative_prompt(self, explicit_negatives: List[str]) -> str:
        """Compile the complete negative prompt."""
        all_negatives = []
        
        # Add explicit negatives from constraints
        all_negatives.extend(explicit_negatives)
        
        # Add standard quality negatives
        all_negatives.extend(self.NEGATIVE_STANDARDS["quality"])
        
        # Add composition negatives
        all_negatives.extend(self.NEGATIVE_STANDARDS["composition"])
        
        # Model-specific additions
        if self.prompt_style == PromptStyle.SDXL:
            all_negatives.extend([
                "ugly",
                "duplicate",
                "morbid",
                "mutilated"
            ])
        
        # Deduplicate while preserving order
        seen = set()
        unique_negatives = []
        for neg in all_negatives:
            if not neg:
                continue
            neg_lower = neg.lower().strip()
            if neg_lower and neg_lower not in seen:
                seen.add(neg_lower)
                unique_negatives.append(neg)
        
        return ", ".join(unique_negatives)
    
    def _extract_style_modifiers(
        self,
        scene_graph: SceneGraph,
        style_guidance: Dict[str, str]
    ) -> List[str]:
        """Extract style modifiers from scene and guidance."""
        modifiers = []
        
        # From style guidance
        for key, value in style_guidance.items():
            if not key or not value:
                continue
            key_lower = key.lower()
            if "lighting" in key_lower:
                modifiers.append(f"{value} lighting")
            elif "mood" in key_lower:
                modifiers.append(f"{value} mood")
            elif "style" in key_lower:
                modifiers.append(value)
        
        # From scene graph elements
        for element in scene_graph.elements:
            if element.importance >= 0.8:
                style = element.style_attributes
                if style.lighting and f"{style.lighting} lighting" not in modifiers:
                    modifiers.append(f"{style.lighting} lighting")
        
        return modifiers
    
    def _build_composition_guidance(self, scene_graph: SceneGraph) -> str:
        """Build composition-specific guidance string."""
        parts = []
        
        # Focal point
        fx, fy = scene_graph.focal_point
        if abs(fx - 0.5) < 0.1 and abs(fy - 0.5) < 0.1:
            parts.append("centered focal point")
        elif fx < 0.4:
            parts.append("left-weighted composition")
        elif fx > 0.6:
            parts.append("right-weighted composition")
        
        # Visual flow
        flow_descriptions = {
            "left-to-right": "eye flow from left to right",
            "center-out": "radial visual flow from center",
            "z-pattern": "z-pattern reading flow",
            "f-pattern": "f-pattern visual hierarchy"
        }
        
        flow_desc = flow_descriptions.get(scene_graph.visual_flow)
        if flow_desc:
            parts.append(flow_desc)
        
        # Aspect ratio considerations
        aspect = scene_graph.aspect_ratio
        if aspect == "16:9":
            parts.append("cinematic wide composition")
        elif aspect == "1:1":
            parts.append("square format balance")
        elif aspect == "9:16":
            parts.append("vertical portrait composition")
        
        return ", ".join(parts)
    
    def _optimize_prompt(self, prompt: str) -> str:
        """Optimize prompt by removing duplicates and improving structure."""
        if not prompt:
            return ""
        
        # Split into parts
        parts = [p.strip() for p in prompt.split(",")]
        
        # Remove empty parts
        parts = [p for p in parts if p]
        
        # Remove near-duplicates
        seen = set()
        unique_parts = []
        
        for part in parts:
            if not part:
                continue
            # Normalize for comparison
            normalized = part.lower().strip()
            
            # Check for semantic duplicates
            is_duplicate = False
            for seen_part in seen:
                if self._are_semantically_similar(normalized, seen_part):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen.add(normalized)
                unique_parts.append(part)
        
        # Limit length for model compatibility
        max_parts = 50  # Reasonable limit
        if len(unique_parts) > max_parts:
            unique_parts = unique_parts[:max_parts]
        
        return ", ".join(unique_parts)
    
    def _are_semantically_similar(self, a: str, b: str) -> bool:
        """Check if two prompt parts are semantically similar."""
        # Exact match
        if a == b:
            return True
        
        # One contains the other
        if a in b or b in a:
            return True
        
        # Word overlap
        words_a = set(a.split())
        words_b = set(b.split())
        
        if len(words_a) > 0 and len(words_b) > 0:
            overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
            if overlap > 0.7:
                return True
        
        return False


# Convenience function for quick prompt compilation
def compile_prompt(
    original_prompt: str,
    brand_context: Optional[Dict] = None,
    constraints: Optional[List[Dict]] = None,
    quality: str = "high_quality"
) -> CompiledPrompt:
    """
    Quick helper to compile a prompt with basic settings.
    
    Args:
        original_prompt: User's generation prompt
        brand_context: Optional brand information
        constraints: Optional list of constraint dicts
        quality: Quality preset
        
    Returns:
        CompiledPrompt object
    """
    from .scene_decomposition import SceneDecompositionEngine, SceneGraph
    from .constraint_resolver import ResolvedConstraintSet
    
    # Create a simple scene graph
    scene_graph = SceneGraph(
        id="quick_scene",
        original_prompt=original_prompt,
        elements=[],
        layout_type="centered",
        aspect_ratio="1:1",
        overall_mood="professional",
        focal_point=(0.5, 0.5),
        visual_flow="center-out"
    )
    
    # Create empty constraint set if none provided
    if constraints:
        # Convert dict constraints to proper format
        from .constraint_resolver import Constraint, ConstraintType, ConstraintTarget, ConstraintSource
        parsed_constraints = []
        for c in constraints:
            parsed_constraints.append(Constraint(
                id=c.get("id", "con_quick"),
                type=ConstraintType(c.get("type", "PREFER")),
                strength=c.get("strength", 0.7),
                scope="global",
                target_type=ConstraintTarget(c.get("target_type", "style")),
                target_value=c.get("target_value", ""),
                description=c.get("description", ""),
                reason=ConstraintSource.SYSTEM_DEFAULT,
                applies_to="all"
            ))
        
        constraint_set = ResolvedConstraintSet(
            global_constraints=parsed_constraints,
            element_constraints={},
            positive_prompts=[c.target_value for c in parsed_constraints if c.type == ConstraintType.MUST_INCLUDE],
            negative_prompts=[c.target_value for c in parsed_constraints if c.type == ConstraintType.MUST_AVOID],
            style_guidance={},
            conflict_resolutions=[]
        )
    else:
        constraint_set = ResolvedConstraintSet(
            global_constraints=[],
            element_constraints={},
            positive_prompts=[],
            negative_prompts=[],
            style_guidance={},
            conflict_resolutions=[]
        )
    
    engine = PromptCompilationEngine()
    return engine.compile(scene_graph, constraint_set, brand_context, quality_level=quality)
