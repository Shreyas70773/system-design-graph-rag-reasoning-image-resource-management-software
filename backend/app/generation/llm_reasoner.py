"""
LLM Reasoning Layer for GraphRAG Generation
============================================
This module implements the "thinking first" approach:
1. Analyzes user prompt
2. Plans which Brand DNA nodes to retrieve
3. Compiles conditioned prompt for diffusion model
4. Maps feedback to specific graph nodes

Uses Groq (fast, free tier) or Claude (better reasoning)
"""

import os
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import httpx
from datetime import datetime


class ReasoningProvider(Enum):
    GROQ = "groq"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass
class GenerationPlan:
    """The output of LLM planning - what to retrieve and how to condition"""
    # Parsed user intent
    subject: str
    scene_description: str
    mood: str
    
    # What to retrieve from Brand DNA
    needs_colors: bool = True
    needs_style: bool = True
    needs_products: List[str] = field(default_factory=list)  # Product names/categories
    needs_character: bool = False
    character_description: Optional[str] = None
    
    # Composition decisions
    suggested_layout: str = "centered"
    suggested_text_position: str = "bottom"
    suggested_overlay: float = 0.0
    
    # Conditioning strengths (0-1)
    color_strength: float = 0.8
    style_strength: float = 0.8
    product_strength: float = 0.6
    character_strength: float = 0.7
    
    # Learned preferences to apply
    applicable_preferences: List[str] = field(default_factory=list)
    
    # Compiled prompt parts
    positive_prompt_additions: List[str] = field(default_factory=list)
    negative_prompt_additions: List[str] = field(default_factory=list)
    
    # Reasoning trace (for explainability)
    reasoning_steps: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "scene_description": self.scene_description,
            "mood": self.mood,
            "needs_colors": self.needs_colors,
            "needs_style": self.needs_style,
            "needs_products": self.needs_products,
            "needs_character": self.needs_character,
            "character_description": self.character_description,
            "suggested_layout": self.suggested_layout,
            "suggested_text_position": self.suggested_text_position,
            "suggested_overlay": self.suggested_overlay,
            "color_strength": self.color_strength,
            "style_strength": self.style_strength,
            "product_strength": self.product_strength,
            "character_strength": self.character_strength,
            "applicable_preferences": self.applicable_preferences,
            "positive_prompt_additions": self.positive_prompt_additions,
            "negative_prompt_additions": self.negative_prompt_additions,
            "reasoning_steps": self.reasoning_steps
        }


@dataclass
class FeedbackAnalysis:
    """Analysis of user feedback mapped to graph nodes"""
    # What aspects had issues
    affected_aspects: List[str]  # color, style, composition, product, character
    
    # Specific node updates
    node_updates: List[Dict[str, Any]]  # {node_type, node_id, property, old_value, new_value}
    
    # New preferences to create
    new_preferences: List[Dict[str, Any]]  # {trigger, applies, aspect, confidence}
    
    # Reasoning
    analysis_reasoning: str
    
    # Suggested actions
    suggested_actions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "affected_aspects": self.affected_aspects,
            "node_updates": self.node_updates,
            "new_preferences": self.new_preferences,
            "analysis_reasoning": self.analysis_reasoning,
            "suggested_actions": self.suggested_actions
        }


class LLMReasoner:
    """LLM-based reasoning for generation planning and feedback analysis"""
    
    def __init__(
        self,
        provider: ReasoningProvider = ReasoningProvider.OPENAI,
        api_key: Optional[str] = None
    ):
        self.provider = provider
        
        if provider == ReasoningProvider.GROQ:
            self.api_key = api_key or os.getenv("GROQ_API_KEY")
            self.base_url = "https://api.groq.com/openai/v1"
            self.model = "llama-3.3-70b-versatile"
        elif provider == ReasoningProvider.ANTHROPIC:
            self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            self.base_url = "https://api.anthropic.com/v1"
            self.model = "claude-3-5-sonnet-20241022"
        else:  # OPENAI (default)
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            self.base_url = "https://api.openai.com/v1"
            self.model = "gpt-4o-mini"
    
    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Make LLM API call"""
        
        if self.provider == ReasoningProvider.ANTHROPIC:
            return await self._call_anthropic(system_prompt, user_prompt)
        else:
            return await self._call_openai_compatible(system_prompt, user_prompt)
    
    async def _call_openai_compatible(self, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI-compatible API (Groq, OpenAI)"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"LLM API error: {response.text}")
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
    
    async def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        """Call Anthropic Claude API"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "max_tokens": 2000,
                    "system": system_prompt,
                    "messages": [
                        {"role": "user", "content": user_prompt}
                    ]
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Anthropic API error: {response.text}")
            
            result = response.json()
            return result["content"][0]["text"]
    
    async def plan_generation(
        self,
        user_prompt: str,
        brand_context: Dict[str, Any],
        learned_preferences: List[Dict[str, Any]]
    ) -> GenerationPlan:
        """
        Analyze user prompt and plan what to retrieve from Brand DNA.
        This is the "thinking" step before generation.
        """
        
        system_prompt = """You are an AI that plans brand-aligned image generation.
Given a user prompt and brand context, you must:
1. Analyze what the user wants to generate
2. Decide which brand elements (colors, style, products, characters) are relevant
3. Plan composition and layout
4. Consider learned preferences from past feedback
5. Output a structured generation plan

Brand Context provided:
- Colors: brand color palette with roles (primary, secondary, accent)
- Style: brand aesthetic keywords
- Products: available product references
- Characters: available face references for consistency
- Learned Preferences: rules learned from past feedback

Output valid JSON matching this schema:
{
    "subject": "main subject of the image",
    "scene_description": "detailed scene description",
    "mood": "emotional tone",
    "needs_colors": true/false,
    "needs_style": true/false,
    "needs_products": ["product names if relevant"],
    "needs_character": true/false,
    "character_description": "if character needed, describe",
    "suggested_layout": "centered|left-aligned|split|asymmetric",
    "suggested_text_position": "top|center|bottom|none",
    "suggested_overlay": 0.0-1.0,
    "color_strength": 0.0-1.0,
    "style_strength": 0.0-1.0,
    "product_strength": 0.0-1.0,
    "character_strength": 0.0-1.0,
    "applicable_preferences": ["preference IDs that apply"],
    "positive_prompt_additions": ["extra positive prompt terms"],
    "negative_prompt_additions": ["extra negative prompt terms"],
    "reasoning_steps": ["step 1 reasoning", "step 2 reasoning", ...]
}"""
        
        user_content = f"""User Prompt: {user_prompt}

Brand Context:
{json.dumps(brand_context, indent=2)}

Learned Preferences:
{json.dumps(learned_preferences, indent=2)}

Analyze this and create a generation plan. Output only valid JSON."""
        
        try:
            response = await self._call_llm(system_prompt, user_content)
            
            # Parse JSON from response
            # Handle potential markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            plan_data = json.loads(response.strip())
            
            return GenerationPlan(
                subject=plan_data.get("subject", ""),
                scene_description=plan_data.get("scene_description", user_prompt),
                mood=plan_data.get("mood", "neutral"),
                needs_colors=plan_data.get("needs_colors", True),
                needs_style=plan_data.get("needs_style", True),
                needs_products=plan_data.get("needs_products", []),
                needs_character=plan_data.get("needs_character", False),
                character_description=plan_data.get("character_description"),
                suggested_layout=plan_data.get("suggested_layout", "centered"),
                suggested_text_position=plan_data.get("suggested_text_position", "bottom"),
                suggested_overlay=plan_data.get("suggested_overlay", 0.0),
                color_strength=plan_data.get("color_strength", 0.8),
                style_strength=plan_data.get("style_strength", 0.8),
                product_strength=plan_data.get("product_strength", 0.6),
                character_strength=plan_data.get("character_strength", 0.7),
                applicable_preferences=plan_data.get("applicable_preferences", []),
                positive_prompt_additions=plan_data.get("positive_prompt_additions", []),
                negative_prompt_additions=plan_data.get("negative_prompt_additions", []),
                reasoning_steps=plan_data.get("reasoning_steps", [])
            )
            
        except json.JSONDecodeError as e:
            # Fallback to basic plan
            return GenerationPlan(
                subject=user_prompt,
                scene_description=user_prompt,
                mood="neutral",
                reasoning_steps=[f"JSON parse error, using defaults: {str(e)}"]
            )
    
    async def analyze_feedback(
        self,
        generation_context: Dict[str, Any],
        user_feedback: Dict[str, Any],
        brand_dna: Dict[str, Any]
    ) -> FeedbackAnalysis:
        """
        Analyze user feedback and map to specific Brand DNA node updates.
        This is the key to GraphRAG learning.
        
        user_feedback contains:
        - selected_aspects: List of aspects user marked as issues
        - feedback_text: Free text description of issues
        - rating: positive/negative
        """
        
        system_prompt = """You are an AI that analyzes feedback on generated brand content.
Your job is to:
1. Understand what went wrong based on user feedback
2. Map issues to specific Brand DNA graph nodes
3. Suggest node property updates
4. Identify patterns that should become learned preferences

Brand DNA Node Types:
- ColorNode: hex, name, role, usage_weight, contexts
- StyleNode: type, keywords, weight, negative_keywords  
- CompositionNode: layout, text_density, text_position, overlay_opacity, padding_preference
- ProductNode: name, category, usage_count, avg_rating
- CharacterNode: name, usage_count
- LearnedPreference: trigger (condition), applies (what to do), aspect, confidence

Output valid JSON:
{
    "affected_aspects": ["color", "style", "composition", etc],
    "node_updates": [
        {
            "node_type": "CompositionNode",
            "node_id": "composition id or null for default",
            "property": "overlay_opacity",
            "old_value": 0.0,
            "new_value": 0.3,
            "reason": "User requested dark overlay for text visibility"
        }
    ],
    "new_preferences": [
        {
            "trigger": "text_position = centered",
            "applies": "overlay_opacity = 0.3",
            "aspect": "composition",
            "confidence": 1.0,
            "reason": "User consistently wants overlay when text is centered"
        }
    ],
    "analysis_reasoning": "Detailed explanation of analysis",
    "suggested_actions": ["Apply overlay", "Reduce text density", etc]
}"""
        
        user_content = f"""Generation Context:
{json.dumps(generation_context, indent=2)}

User Feedback:
- Selected Issues: {user_feedback.get('selected_aspects', [])}
- Feedback Text: {user_feedback.get('feedback_text', '')}
- Rating: {user_feedback.get('rating', 'neutral')}

Current Brand DNA:
{json.dumps(brand_dna, indent=2)}

Analyze this feedback and map to graph node updates. Output only valid JSON."""
        
        try:
            response = await self._call_llm(system_prompt, user_content)
            
            # Parse JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            analysis_data = json.loads(response.strip())
            
            return FeedbackAnalysis(
                affected_aspects=analysis_data.get("affected_aspects", []),
                node_updates=analysis_data.get("node_updates", []),
                new_preferences=analysis_data.get("new_preferences", []),
                analysis_reasoning=analysis_data.get("analysis_reasoning", ""),
                suggested_actions=analysis_data.get("suggested_actions", [])
            )
            
        except json.JSONDecodeError:
            return FeedbackAnalysis(
                affected_aspects=user_feedback.get("selected_aspects", []),
                node_updates=[],
                new_preferences=[],
                analysis_reasoning="Failed to parse LLM response",
                suggested_actions=[]
            )
    
    async def compile_final_prompt(
        self,
        plan: GenerationPlan,
        brand_dna: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Compile the final positive and negative prompts for diffusion.
        Combines user intent with brand conditioning.
        """
        
        positive_parts = [plan.scene_description]
        negative_parts = []
        
        # Add colors
        if plan.needs_colors and brand_dna.get("colors"):
            colors = brand_dna["colors"]
            primary = next((c for c in colors if c.get("role") == "primary"), colors[0] if colors else None)
            if primary:
                positive_parts.append(f"color palette featuring {primary.get('name', primary.get('hex'))}")
        
        # Add style
        if plan.needs_style and brand_dna.get("styles"):
            styles = brand_dna["styles"]
            for style in styles[:2]:  # Top 2 styles
                keywords = style.get("keywords", [])
                if keywords:
                    positive_parts.append(f"{', '.join(keywords[:3])} aesthetic")
                negative_kw = style.get("negative_keywords", [])
                negative_parts.extend(negative_kw)
        
        # Add composition hints
        if plan.suggested_overlay > 0:
            positive_parts.append(f"with subtle dark overlay (opacity {plan.suggested_overlay})")
        
        if plan.suggested_layout:
            positive_parts.append(f"{plan.suggested_layout} composition")
        
        # Add LLM-suggested additions
        positive_parts.extend(plan.positive_prompt_additions)
        negative_parts.extend(plan.negative_prompt_additions)
        
        # Standard quality boosters
        positive_parts.extend([
            "professional photography",
            "high resolution",
            "sharp focus",
            "brand marketing quality"
        ])
        
        # Standard negatives
        negative_parts.extend([
            "blurry",
            "low quality",
            "distorted",
            "watermark",
            "amateur",
            "poorly lit"
        ])
        
        positive_prompt = ", ".join(positive_parts)
        negative_prompt = ", ".join(list(set(negative_parts)))  # Dedupe
        
        return positive_prompt, negative_prompt


# Singleton for easy access
_reasoner_instance: Optional[LLMReasoner] = None

def get_reasoner(provider: str = "groq") -> LLMReasoner:
    """Get or create LLM reasoner instance"""
    global _reasoner_instance
    
    if _reasoner_instance is None:
        provider_enum = ReasoningProvider(provider.lower())
        _reasoner_instance = LLMReasoner(provider=provider_enum)
    
    return _reasoner_instance
