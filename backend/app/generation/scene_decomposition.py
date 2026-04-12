"""
Scene Decomposition Engine for GraphRAG-Guided Image Generation
================================================================
This module handles the decomposition of user prompts into structured scene graphs
using LLM-based semantic parsing. It identifies:
- Scene elements (background, subject, accents, text areas)
- Spatial relationships between elements
- Style attributes for each element
- Composition requirements

Part of Capstone Research: GraphRAG-Guided Compositional Image Generation
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
import json
import uuid
from datetime import datetime
import httpx
import os
import re


class ElementType(str, Enum):
    """Taxonomy of scene element types for compositional generation."""
    BACKGROUND = "BACKGROUND"      # Scene backdrop, environment
    SUBJECT = "SUBJECT"            # Main focal point, product, person
    SECONDARY = "SECONDARY"        # Supporting elements
    TEXT_AREA = "TEXT_AREA"        # Designated text/copy regions
    ACCENT = "ACCENT"              # Decorative elements, highlights
    CHARACTER = "CHARACTER"        # Human figures requiring consistency
    LOGO = "LOGO"                  # Brand logo placement
    PRODUCT = "PRODUCT"            # Featured product


class SpatialPosition(str, Enum):
    """Predefined spatial positions for scene elements."""
    CENTER = "center"
    TOP_LEFT = "top-left"
    TOP_CENTER = "top-center"
    TOP_RIGHT = "top-right"
    MIDDLE_LEFT = "middle-left"
    MIDDLE_RIGHT = "middle-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_CENTER = "bottom-center"
    BOTTOM_RIGHT = "bottom-right"
    RULE_OF_THIRDS_LEFT = "rule-of-thirds-left"
    RULE_OF_THIRDS_RIGHT = "rule-of-thirds-right"
    FULL_BLEED = "full-bleed"


class LayoutType(str, Enum):
    """Composition layout patterns."""
    CENTERED = "centered"
    RULE_OF_THIRDS = "rule_of_thirds"
    ASYMMETRIC = "asymmetric"
    GRID = "grid"
    DIAGONAL = "diagonal"
    GOLDEN_RATIO = "golden_ratio"
    Z_PATTERN = "z_pattern"
    F_PATTERN = "f_pattern"


@dataclass
class BoundingBox:
    """Relative bounding box as percentages (0-1) of image dimensions."""
    x: float  # Left edge percentage
    y: float  # Top edge percentage
    width: float
    height: float
    
    def to_dict(self) -> Dict:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}
    
    @classmethod
    def from_dict(cls, data: Dict) -> "BoundingBox":
        return cls(x=data["x"], y=data["y"], width=data["width"], height=data["height"])
    
    def center(self) -> tuple:
        """Return center point of bounding box."""
        return (self.x + self.width / 2, self.y + self.height / 2)


@dataclass
class StyleAttributes:
    """Visual style attributes for a scene element."""
    lighting: Optional[str] = None  # 'natural', 'studio', 'dramatic', 'soft'
    material: Optional[str] = None  # 'matte', 'glossy', 'metallic', 'organic'
    texture: Optional[str] = None   # 'smooth', 'rough', 'gradient', 'pattern'
    color_scheme: Optional[str] = None  # 'warm', 'cool', 'neutral', 'vibrant'
    mood: Optional[str] = None      # 'energetic', 'calm', 'professional', 'playful'
    depth_of_field: Optional[str] = None  # 'shallow', 'deep', 'selective'
    shadow_style: Optional[str] = None  # 'soft', 'hard', 'none', 'ambient'
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in {
            "lighting": self.lighting,
            "material": self.material,
            "texture": self.texture,
            "color_scheme": self.color_scheme,
            "mood": self.mood,
            "depth_of_field": self.depth_of_field,
            "shadow_style": self.shadow_style
        }.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict) -> "StyleAttributes":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SceneElement:
    """A single element within the scene graph."""
    id: str
    type: ElementType
    semantic_label: str  # What this element represents
    spatial_position: SpatialPosition
    z_index: int  # Layer order (higher = front)
    bounding_box: BoundingBox
    style_attributes: StyleAttributes
    importance: float = 0.5  # 0-1, for constraint priority
    prompt_segment: str = ""  # The part of prompt this maps to
    relationships: List[Dict] = field(default_factory=list)  # Spatial relations
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "semantic_label": self.semantic_label,
            "spatial_position": self.spatial_position.value,
            "z_index": self.z_index,
            "bounding_box": self.bounding_box.to_dict(),
            "style_attributes": self.style_attributes.to_dict(),
            "importance": self.importance,
            "prompt_segment": self.prompt_segment,
            "relationships": self.relationships
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SceneElement":
        return cls(
            id=data["id"],
            type=ElementType(data["type"]),
            semantic_label=data["semantic_label"],
            spatial_position=SpatialPosition(data["spatial_position"]),
            z_index=data["z_index"],
            bounding_box=BoundingBox.from_dict(data["bounding_box"]),
            style_attributes=StyleAttributes.from_dict(data.get("style_attributes", {})),
            importance=data.get("importance", 0.5),
            prompt_segment=data.get("prompt_segment", ""),
            relationships=data.get("relationships", [])
        )


@dataclass
class SceneGraph:
    """Complete scene graph representing a decomposed prompt."""
    id: str
    original_prompt: str
    elements: List[SceneElement]
    layout_type: LayoutType
    aspect_ratio: str
    overall_mood: str
    focal_point: tuple  # (x, y) as percentages
    visual_flow: str  # 'left-to-right', 'center-out', 'z-pattern'
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "original_prompt": self.original_prompt,
            "elements": [e.to_dict() for e in self.elements],
            "layout_type": self.layout_type.value,
            "aspect_ratio": self.aspect_ratio,
            "overall_mood": self.overall_mood,
            "focal_point": {"x": self.focal_point[0], "y": self.focal_point[1]},
            "visual_flow": self.visual_flow,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SceneGraph":
        return cls(
            id=data["id"],
            original_prompt=data["original_prompt"],
            elements=[SceneElement.from_dict(e) for e in data["elements"]],
            layout_type=LayoutType(data["layout_type"]),
            aspect_ratio=data["aspect_ratio"],
            overall_mood=data["overall_mood"],
            focal_point=(data["focal_point"]["x"], data["focal_point"]["y"]),
            visual_flow=data["visual_flow"],
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            metadata=data.get("metadata", {})
        )
    
    def get_elements_by_type(self, element_type: ElementType) -> List[SceneElement]:
        """Get all elements of a specific type."""
        return [e for e in self.elements if e.type == element_type]
    
    def get_primary_subject(self) -> Optional[SceneElement]:
        """Get the main subject element with highest importance."""
        subjects = self.get_elements_by_type(ElementType.SUBJECT)
        if subjects:
            return max(subjects, key=lambda x: x.importance)
        return None


class SceneDecompositionEngine:
    """
    LLM-powered engine for decomposing text prompts into structured scene graphs.
    
    This is a core component of the GraphRAG system that enables:
    1. Element-level constraint application
    2. Compositional control over generation
    3. Targeted feedback at the element level
    """
    
    # System prompt for scene decomposition
    DECOMPOSITION_PROMPT = """You are a scene decomposition expert for AI image generation. 
Your task is to analyze a text prompt and decompose it into a structured scene graph.

For each prompt, identify:
1. BACKGROUND: The scene backdrop/environment
2. SUBJECT: Main focal point (product, person, object)
3. SECONDARY: Supporting elements
4. TEXT_AREA: Where text/copy should go
5. ACCENT: Decorative elements
6. CHARACTER: Any human figures
7. LOGO: Brand logo placement
8. PRODUCT: Featured products

For each element provide:
- type: One of [BACKGROUND, SUBJECT, SECONDARY, TEXT_AREA, ACCENT, CHARACTER, LOGO, PRODUCT]
- semantic_label: Descriptive name (e.g., "coffee_cup", "outdoor_cafe")
- spatial_position: One of [center, top-left, top-center, top-right, middle-left, middle-right, bottom-left, bottom-center, bottom-right, rule-of-thirds-left, rule-of-thirds-right, full-bleed]
- z_index: Layer order (0=back, higher=front)
- bounding_box: {x, y, width, height} as percentages 0-1
- importance: 0-1 priority score
- style_attributes: {lighting, material, texture, color_scheme, mood}
- prompt_segment: The part of the original prompt this maps to

Also determine:
- layout_type: [centered, rule_of_thirds, asymmetric, grid, diagonal, golden_ratio, z_pattern, f_pattern]
- aspect_ratio: e.g., "1:1", "16:9", "4:3"
- overall_mood: Single word describing the feel
- focal_point: {x, y} where attention should focus (0-1)
- visual_flow: How the eye moves through the scene

Respond ONLY with valid JSON in this exact format:
{
    "elements": [...],
    "layout_type": "...",
    "aspect_ratio": "...",
    "overall_mood": "...",
    "focal_point": {"x": 0.5, "y": 0.5},
    "visual_flow": "..."
}"""

    def __init__(self, llm_client=None):
        """
        Initialize the Scene Decomposition Engine.
        
        Args:
            llm_client: Optional pre-configured LLM client. If None, uses Groq.
        """
        self.llm_client = llm_client
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_model = "llama-3.3-70b-versatile"
    
    async def decompose_prompt(
        self, 
        prompt: str, 
        brand_context: Optional[Dict] = None,
        aspect_ratio: str = "1:1",
        include_text_area: bool = True
    ) -> SceneGraph:
        """
        Decompose a text prompt into a structured scene graph.
        
        Args:
            prompt: The user's generation prompt
            brand_context: Optional brand information for context
            aspect_ratio: Desired output aspect ratio
            include_text_area: Whether to include text overlay area
            
        Returns:
            SceneGraph object with all identified elements
        """
        # Build the analysis request
        analysis_prompt = self._build_analysis_prompt(prompt, brand_context, aspect_ratio, include_text_area)
        
        # Get LLM response
        llm_response = await self._call_llm(analysis_prompt)
        
        # Parse the response
        scene_data = self._parse_llm_response(llm_response)
        
        # Build the scene graph
        scene_graph = self._build_scene_graph(prompt, scene_data, aspect_ratio)
        
        return scene_graph
    
    def _build_analysis_prompt(
        self, 
        prompt: str, 
        brand_context: Optional[Dict],
        aspect_ratio: str,
        include_text_area: bool
    ) -> str:
        """Build the complete prompt for LLM analysis."""
        context_str = ""
        if brand_context:
            # Extract color values - handle both string and dict formats
            colors = brand_context.get('colors', [])
            color_strs = []
            if colors:
                for c in colors:
                    if isinstance(c, dict):
                        color_val = c.get('hex') or c.get('name')
                        if color_val:
                            color_strs.append(str(color_val))
                    elif c:
                        color_strs.append(str(c))
            
            context_str = f"""
Brand Context:
- Name: {brand_context.get('name', 'Unknown') or 'Unknown'}
- Industry: {brand_context.get('industry', 'General') or 'General'}
- Colors: {', '.join(color_strs) if color_strs else 'Not specified'}
- Tagline: {brand_context.get('tagline', '') or ''}
"""
        
        text_instruction = ""
        if include_text_area:
            text_instruction = "\nIMPORTANT: Include a TEXT_AREA element for text overlay placement."
        
        return f"""{self.DECOMPOSITION_PROMPT}

{context_str}

Target Aspect Ratio: {aspect_ratio}
{text_instruction}

User Prompt to Decompose:
"{prompt}"

Respond with the scene graph JSON:"""
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM API for scene decomposition."""
        if not self.groq_api_key:
            # Fallback to simple parsing if no API key
            return self._simple_decomposition_fallback(prompt)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.groq_model,
                    "messages": [
                        {"role": "system", "content": "You are a scene decomposition expert. Always respond with valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
            )
            
            if response.status_code != 200:
                print(f"LLM API error: {response.text}")
                return self._simple_decomposition_fallback(prompt)
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    def _simple_decomposition_fallback(self, prompt: str) -> str:
        """Fallback decomposition when LLM is unavailable."""
        # Simple keyword-based decomposition
        prompt_lower = (prompt or "").lower()
        has_person = any(word in prompt_lower for word in ["person", "people", "man", "woman", "model", "face"])
        has_product = any(word in prompt_lower for word in ["product", "item", "coffee", "drink", "food"])
        
        elements = [
            {
                "type": "BACKGROUND",
                "semantic_label": "scene_background",
                "spatial_position": "full-bleed",
                "z_index": 0,
                "bounding_box": {"x": 0, "y": 0, "width": 1, "height": 1},
                "importance": 0.3,
                "style_attributes": {"lighting": "natural", "mood": "warm"},
                "prompt_segment": prompt
            },
            {
                "type": "SUBJECT",
                "semantic_label": "main_subject",
                "spatial_position": "center",
                "z_index": 2,
                "bounding_box": {"x": 0.2, "y": 0.2, "width": 0.6, "height": 0.6},
                "importance": 1.0,
                "style_attributes": {"lighting": "studio", "depth_of_field": "shallow"},
                "prompt_segment": prompt
            },
            {
                "type": "TEXT_AREA",
                "semantic_label": "text_overlay_area",
                "spatial_position": "bottom-center",
                "z_index": 10,
                "bounding_box": {"x": 0.1, "y": 0.75, "width": 0.8, "height": 0.2},
                "importance": 0.7,
                "style_attributes": {},
                "prompt_segment": ""
            }
        ]
        
        if has_person:
            elements.append({
                "type": "CHARACTER",
                "semantic_label": "human_figure",
                "spatial_position": "rule-of-thirds-left",
                "z_index": 3,
                "bounding_box": {"x": 0.1, "y": 0.1, "width": 0.4, "height": 0.8},
                "importance": 0.9,
                "style_attributes": {"lighting": "natural"},
                "prompt_segment": prompt
            })
        
        if has_product:
            elements.append({
                "type": "PRODUCT",
                "semantic_label": "featured_product",
                "spatial_position": "center",
                "z_index": 4,
                "bounding_box": {"x": 0.3, "y": 0.3, "width": 0.4, "height": 0.4},
                "importance": 0.95,
                "style_attributes": {"lighting": "studio", "material": "glossy"},
                "prompt_segment": prompt
            })
        
        return json.dumps({
            "elements": elements,
            "layout_type": "centered",
            "aspect_ratio": "1:1",
            "overall_mood": "professional",
            "focal_point": {"x": 0.5, "y": 0.5},
            "visual_flow": "center-out"
        })
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse the LLM response into structured data."""
        # Try to extract JSON from the response
        try:
            # First, try direct JSON parsing
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in the response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Return default structure if parsing fails
        print(f"Warning: Could not parse LLM response, using fallback")
        return json.loads(self._simple_decomposition_fallback(""))
    
    def _build_scene_graph(self, prompt: str, scene_data: Dict, aspect_ratio: str) -> SceneGraph:
        """Build a SceneGraph object from parsed data."""
        elements = []
        
        for i, elem_data in enumerate(scene_data.get("elements", [])):
            try:
                element = SceneElement(
                    id=f"elem_{uuid.uuid4().hex[:8]}",
                    type=ElementType(elem_data.get("type", "SECONDARY")),
                    semantic_label=elem_data.get("semantic_label", f"element_{i}"),
                    spatial_position=SpatialPosition(elem_data.get("spatial_position", "center")),
                    z_index=elem_data.get("z_index", i),
                    bounding_box=BoundingBox.from_dict(elem_data.get("bounding_box", {
                        "x": 0.2, "y": 0.2, "width": 0.6, "height": 0.6
                    })),
                    style_attributes=StyleAttributes.from_dict(elem_data.get("style_attributes", {})),
                    importance=elem_data.get("importance", 0.5),
                    prompt_segment=elem_data.get("prompt_segment", "")
                )
                elements.append(element)
            except (ValueError, KeyError) as e:
                print(f"Warning: Could not parse element {i}: {e}")
                continue
        
        focal_point_data = scene_data.get("focal_point", {"x": 0.5, "y": 0.5})
        
        return SceneGraph(
            id=f"scene_{uuid.uuid4().hex[:8]}",
            original_prompt=prompt,
            elements=elements,
            layout_type=LayoutType(scene_data.get("layout_type", "centered")),
            aspect_ratio=scene_data.get("aspect_ratio", aspect_ratio),
            overall_mood=scene_data.get("overall_mood", "neutral"),
            focal_point=(focal_point_data.get("x", 0.5), focal_point_data.get("y", 0.5)),
            visual_flow=scene_data.get("visual_flow", "center-out")
        )
    
    def infer_element_type(self, description: str) -> ElementType:
        """Infer element type from a text description."""
        if not description:
            return ElementType.SUBJECT  # Default fallback
        description_lower = description.lower()
        
        # Background indicators
        if any(word in description_lower for word in ["background", "backdrop", "environment", "scene", "sky", "wall"]):
            return ElementType.BACKGROUND
        
        # Character indicators
        if any(word in description_lower for word in ["person", "people", "man", "woman", "face", "model", "human"]):
            return ElementType.CHARACTER
        
        # Product indicators
        if any(word in description_lower for word in ["product", "item", "package", "bottle", "box"]):
            return ElementType.PRODUCT
        
        # Logo indicators
        if any(word in description_lower for word in ["logo", "brand", "emblem", "icon"]):
            return ElementType.LOGO
        
        # Text indicators
        if any(word in description_lower for word in ["text", "headline", "title", "copy", "words"]):
            return ElementType.TEXT_AREA
        
        # Default to subject for main items
        return ElementType.SUBJECT


# Utility functions
def merge_scene_elements(base_scene: SceneGraph, additional_elements: List[SceneElement]) -> SceneGraph:
    """Merge additional elements into an existing scene graph."""
    merged_elements = base_scene.elements.copy()
    max_z = max((e.z_index for e in merged_elements), default=0)
    
    for elem in additional_elements:
        elem.z_index = max_z + 1
        max_z += 1
        merged_elements.append(elem)
    
    return SceneGraph(
        id=base_scene.id,
        original_prompt=base_scene.original_prompt,
        elements=merged_elements,
        layout_type=base_scene.layout_type,
        aspect_ratio=base_scene.aspect_ratio,
        overall_mood=base_scene.overall_mood,
        focal_point=base_scene.focal_point,
        visual_flow=base_scene.visual_flow,
        created_at=base_scene.created_at,
        metadata=base_scene.metadata
    )


def calculate_element_overlap(elem1: SceneElement, elem2: SceneElement) -> float:
    """Calculate overlap percentage between two elements."""
    box1, box2 = elem1.bounding_box, elem2.bounding_box
    
    # Calculate intersection
    x_left = max(box1.x, box2.x)
    y_top = max(box1.y, box2.y)
    x_right = min(box1.x + box1.width, box2.x + box2.width)
    y_bottom = min(box1.y + box1.height, box2.y + box2.height)
    
    if x_right < x_left or y_bottom < y_top:
        return 0.0
    
    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    elem1_area = box1.width * box1.height
    
    return intersection_area / elem1_area if elem1_area > 0 else 0.0
