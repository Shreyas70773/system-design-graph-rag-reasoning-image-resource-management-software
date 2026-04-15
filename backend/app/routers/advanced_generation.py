"""
Enhanced Generation API with GraphRAG Integration
==================================================
This router provides the advanced generation endpoints that leverage:
- Scene decomposition
- Constraint resolution
- Character consistency
- Feedback learning
- Structured prompt compilation

Part of Capstone Research: GraphRAG-Guided Compositional Image Generation
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
import uuid
import base64

from app.generation.evaluation_framework import (
    EvaluationFramework,
    evaluate_generation as quick_evaluate
)
from app.generation.pipeline_logger import (
    PipelineLogger, 
    PipelineStage,
    store_execution,
    get_recent_executions,
    get_execution_by_id
)

router = APIRouter(tags=["Advanced Generation"])


# === Request/Response Models ===

class SceneElementRequest(BaseModel):
    """Request model for a scene element."""
    type: str  # BACKGROUND, SUBJECT, TEXT_AREA, etc.
    semantic_label: str
    spatial_position: str = "center"
    importance: float = 0.5
    style_attributes: Optional[Dict[str, str]] = None


class AdvancedGenerateRequest(BaseModel):
    """Enhanced generation request with full GraphRAG support."""
    brand_id: str
    prompt: str
    type: Literal["image", "text", "both"] = "both"
    
    # Scene configuration
    aspect_ratio: str = "1:1"
    layout_type: Optional[str] = None  # Auto-detected if not provided
    scene_elements: Optional[List[SceneElementRequest]] = None
    
    # Text overlay
    text_layout: Optional[str] = "bottom_centered"
    include_text_overlay: bool = True
    font_id: Optional[str] = None
    
    # Product context
    product_ids: Optional[List[str]] = None
    
    # Character consistency
    character_id: Optional[str] = None  # For consistent character rendering
    preserve_identity: bool = False     # Enable identity preservation mode
    
    # Advanced options
    use_scene_decomposition: bool = True
    use_constraint_resolution: bool = True
    use_learned_preferences: bool = True
    quality_level: str = "high_quality"
    
    # For edits/variations
    source_generation_id: Optional[str] = None
    edit_type: Optional[Literal["variation", "edit", "upscale"]] = None


class SceneElementResponse(BaseModel):
    """Response model for a scene element."""
    id: str
    type: str
    semantic_label: str
    spatial_position: str
    z_index: int
    bounding_box: Dict[str, float]
    importance: float


class SceneGraphResponse(BaseModel):
    """Response model for scene graph."""
    id: str
    original_prompt: str
    elements: List[SceneElementResponse]
    layout_type: str
    aspect_ratio: str
    overall_mood: str
    focal_point: Dict[str, float]


class ConstraintResponse(BaseModel):
    """Response model for constraint."""
    id: str
    type: str
    strength: float
    target_type: str
    target_value: str
    description: str


class CompiledPromptResponse(BaseModel):
    """Response model for compiled prompt."""
    positive_prompt: str
    negative_prompt: str
    style_modifiers: List[str]
    quality_modifiers: List[str]


class AdvancedGeneratedContent(BaseModel):
    """Enhanced generation response with full context."""
    generation_id: str
    image_url: Optional[str] = None
    image_without_text_url: Optional[str] = None
    headline: Optional[str] = None
    body_copy: Optional[str] = None
    brand_score: float
    constraint_satisfaction_score: float = 0.0
    colors_used: List[str] = []
    
    # Scene analysis
    scene_graph: Optional[SceneGraphResponse] = None
    
    # Constraint context
    constraints_applied: List[ConstraintResponse] = []
    conflicts_resolved: List[Dict] = []
    
    # Compiled prompts (for debugging/transparency)
    compiled_prompt: Optional[CompiledPromptResponse] = None
    
    # Character consistency
    character_id: Optional[str] = None
    identity_preserved: bool = False
    
    # Metadata
    generation_time_ms: int = 0
    model_used: str = "sdxl"
    pipeline_execution_id: Optional[str] = None  # For viewing pipeline logs


class FeedbackRequest(BaseModel):
    """Request to submit feedback on a generation."""
    generation_id: str
    brand_id: str
    feedback_type: Literal["like", "dislike", "accept", "regenerate", "edit", "element_like", "element_dislike"]
    level: Literal["whole", "element", "attribute"] = "whole"
    element_type: Optional[str] = None
    element_id: Optional[str] = None
    attribute: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    comment: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""
    feedback_id: str
    recorded: bool
    preference_updated: bool
    pattern_detected: bool = False
    message: str


class PreferenceResponse(BaseModel):
    """Response model for learned preference."""
    attribute: str
    preferred_value: str
    avoided_value: Optional[str] = None
    confidence: float
    sample_count: int


class LearningSummaryResponse(BaseModel):
    """Summary of what has been learned for a brand."""
    total_feedback: int
    positive_feedback: int
    negative_feedback: int
    learned_preferences: int
    high_confidence_preferences: int
    negative_patterns: int
    top_preferences: List[Dict]
    key_avoidances: List[Dict]


class CharacterRequest(BaseModel):
    """Request to create a character for consistency."""
    name: str
    description: str
    reference_image_urls: List[str] = []
    style_notes: Optional[str] = None


class CharacterResponse(BaseModel):
    """Response model for character."""
    id: str
    name: str
    description: str
    reference_count: int
    quality_score: float


# === Advanced Generation Endpoint ===

@router.post("/advanced/generate", response_model=AdvancedGeneratedContent)
async def generate_with_graphrag(request: AdvancedGenerateRequest):
    """
    Generate brand-aligned content using the full GraphRAG pipeline.
    
    This endpoint leverages:
    1. Scene Decomposition - Parse prompt into structured scene graph
    2. Constraint Resolution - Gather and resolve constraints from knowledge graph
    3. Preference Application - Apply learned user preferences
    4. Prompt Compilation - Build optimized prompts for generation
    5. Character Consistency - Maintain identity across edits (optional)
    6. Quality Validation - Score against brand guidelines
    
    Use this for high-quality, intelligent generation that learns and improves.
    """
    import time
    start_time = time.time()
    
    # Initialize pipeline logger for visualization
    logger = PipelineLogger(request.brand_id, request.prompt)
    
    from app.database.neo4j_client import neo4j_client
    from app.generation.scene_decomposition import SceneDecompositionEngine
    from app.generation.constraint_resolver import ConstraintResolutionEngine
    from app.generation.prompt_compiler import PromptCompilationEngine
    from app.generation.image_generator import generate_marketing_image
    from app.generation.text_generator import generate_marketing_text
    from app.generation.validator import calculate_brand_score
    from app.generation.text_overlay import composite_text_on_image
    
    # Log: Request Received
    logger.start_stage(PipelineStage.RECEIVED, {
        "brand_id": request.brand_id,
        "prompt": request.prompt,
        "type": request.type,
        "use_scene_decomposition": request.use_scene_decomposition,
        "use_constraint_resolution": request.use_constraint_resolution,
        "use_learned_preferences": request.use_learned_preferences
    })
    
    # Get brand context
    brand_context = neo4j_client.get_brand_context(request.brand_id)
    if not brand_context:
        logger.log_error("Brand not found")
        store_execution(logger.get_execution())
        raise HTTPException(status_code=404, detail="Brand not found")
    
    logger.add_neo4j_query("MATCH (b:Brand {id: $brand_id}) RETURN b", {"brand_id": request.brand_id})
    logger.add_relationship_read("Brand", "HAS_COLORS", "ColorPalette")
    logger.add_relationship_read("Brand", "HAS_LOGO", "Logo")
    
    # Add product context if provided
    if request.product_ids:
        products = neo4j_client.get_products_by_ids(request.product_ids)
        if products:
            brand_context["selected_products"] = products
            product_summaries = []
            for p in products:
                summary = f"- {p.get('name', 'Product')}"
                if p.get('description'):
                    summary += f": {p.get('description')[:100]}"
                product_summaries.append(summary)
            brand_context["product_context"] = "\n".join(product_summaries)
            logger.add_neo4j_query("MATCH (p:Product) WHERE p.id IN $ids RETURN p", {"ids": request.product_ids})
            for p in products:
                logger.add_relationship_read("Brand", "HAS_PRODUCT", f"Product:{p.get('name', 'Unknown')}")
    
    logger.end_stage(
        {"brand_name": brand_context.get("name"), "colors_count": len(brand_context.get("colors", []))},
        f"Loaded brand '{brand_context.get('name')}' with {len(brand_context.get('colors', []))} colors"
    )
    
    generation_id = f"gen_{uuid.uuid4().hex[:12]}"
    result = AdvancedGeneratedContent(
        generation_id=generation_id,
        brand_score=0.0
    )
    
    try:
        scene_graph = None
        constraint_set = None
        compiled_prompt = None
        
        # Step 1: Scene Decomposition
        if request.use_scene_decomposition:
            logger.start_stage(PipelineStage.SCENE_DECOMPOSITION, {"prompt": request.prompt})
            
            decomposer = SceneDecompositionEngine()
            scene_graph = await decomposer.decompose_prompt(
                prompt=request.prompt,
                brand_context=brand_context,
                aspect_ratio=request.aspect_ratio,
                include_text_area=request.include_text_overlay
            )
            
            # Convert to response model
            result.scene_graph = SceneGraphResponse(
                id=scene_graph.id,
                original_prompt=scene_graph.original_prompt,
                elements=[
                    SceneElementResponse(
                        id=e.id,
                        type=e.type.value,
                        semantic_label=e.semantic_label,
                        spatial_position=e.spatial_position.value,
                        z_index=e.z_index,
                        bounding_box=e.bounding_box.to_dict(),
                        importance=e.importance
                    ) for e in scene_graph.elements
                ],
                layout_type=scene_graph.layout_type.value,
                aspect_ratio=scene_graph.aspect_ratio,
                overall_mood=scene_graph.overall_mood,
                focal_point={"x": scene_graph.focal_point[0], "y": scene_graph.focal_point[1]}
            )
            
            element_types = [e.type.value for e in scene_graph.elements]
            logger.end_stage(
                {"elements": element_types, "layout": scene_graph.layout_type.value},
                f"Decomposed into {len(scene_graph.elements)} elements: {', '.join(element_types)}"
            )
        
        # Step 2: Constraint Resolution
        if request.use_constraint_resolution:
            logger.start_stage(PipelineStage.CONSTRAINT_QUERY, {"brand_id": request.brand_id})
            
            resolver = ConstraintResolutionEngine(neo4j_client)
            constraint_set = await resolver.gather_constraints(
                brand_id=request.brand_id,
                scene_graph=scene_graph
            )
            
            # Log Neo4j queries for constraints
            logger.add_neo4j_query(
                "MATCH (b:Brand {id: $brand_id})-[:HAS_CONSTRAINT]->(c:Constraint) RETURN c",
                {"brand_id": request.brand_id}
            )
            logger.add_relationship_read("Brand", "HAS_CONSTRAINT", "Constraint")
            
            # Convert constraints to response
            result.constraints_applied = [
                ConstraintResponse(
                    id=c.id,
                    type=c.type.value,
                    strength=c.strength,
                    target_type=c.target_type.value,
                    target_value=c.target_value,
                    description=c.description
                ) for c in constraint_set.global_constraints
            ]
            result.conflicts_resolved = constraint_set.conflict_resolutions
            
            logger.end_stage(
                {"constraints_found": len(constraint_set.global_constraints)},
                f"Found {len(constraint_set.global_constraints)} constraints"
            )
            
            # Step 2b: Preference Retrieval
            if request.use_learned_preferences:
                logger.start_stage(PipelineStage.PREFERENCE_RETRIEVAL, {"brand_id": request.brand_id})
                
                logger.add_neo4j_query(
                    "MATCH (b:Brand {id: $id})-[:HAS_LEARNED_PREFERENCE]->(p:LearnedPreference) WHERE p.confidence >= 0.5 RETURN p",
                    {"id": request.brand_id}
                )
                logger.add_relationship_read("Brand", "HAS_LEARNED_PREFERENCE", "LearnedPreference")
                logger.add_neo4j_query(
                    "MATCH (b:Brand {id: $id})-[:AVOID_PATTERN]->(n:NegativePattern) RETURN n",
                    {"id": request.brand_id}
                )
                logger.add_relationship_read("Brand", "AVOID_PATTERN", "NegativePattern")
                
                prefs_count = len(constraint_set.learned_preferences) if hasattr(constraint_set, 'learned_preferences') else 0
                patterns_count = len(constraint_set.negative_patterns) if hasattr(constraint_set, 'negative_patterns') else 0
                
                logger.end_stage(
                    {"preferences": prefs_count, "negative_patterns": patterns_count},
                    f"Retrieved {prefs_count} learned preferences, {patterns_count} negative patterns"
                )
            
            # Step 2c: Conflict Resolution (if any)
            if constraint_set.conflict_resolutions:
                logger.start_stage(PipelineStage.CONFLICT_RESOLUTION, {
                    "conflicts": len(constraint_set.conflict_resolutions)
                })
                logger.end_stage(
                    {"resolved": len(constraint_set.conflict_resolutions)},
                    f"Resolved {len(constraint_set.conflict_resolutions)} constraint conflicts"
                )
        
        # Step 3: Character Consistency (if requested)
        character_guidance = None
        if request.preserve_identity and request.character_id:
            from app.generation.character_consistency import CharacterConsistencyEngine
            char_engine = CharacterConsistencyEngine(neo4j_client)
            characters = await char_engine.get_character_for_brand(request.brand_id)
            
            matching_char = next((c for c in characters if c.id == request.character_id), None)
            if matching_char:
                character_guidance = char_engine.generate_consistency_prompt(matching_char)
                result.character_id = request.character_id
                result.identity_preserved = True
                logger.add_relationship_read("Brand", "HAS_CHARACTER", f"Character:{matching_char.name}")
        
        # Step 4: Prompt Compilation
        if scene_graph and constraint_set:
            logger.start_stage(PipelineStage.PROMPT_COMPILATION, {
                "scene_elements": len(scene_graph.elements),
                "constraints": len(constraint_set.global_constraints)
            })
            
            compiler = PromptCompilationEngine()
            compiled_prompt = compiler.compile(
                scene_graph=scene_graph,
                constraint_set=constraint_set,
                brand_context=brand_context,
                character_guidance=character_guidance,
                quality_level=request.quality_level
            )
            
            result.compiled_prompt = CompiledPromptResponse(
                positive_prompt=compiled_prompt.get_full_positive(),
                negative_prompt=compiled_prompt.get_full_negative(),
                style_modifiers=compiled_prompt.style_modifiers,
                quality_modifiers=compiled_prompt.quality_modifiers
            )
            
            logger.end_stage(
                {
                    "positive_prompt_length": len(compiled_prompt.get_full_positive()),
                    "negative_prompt_length": len(compiled_prompt.get_full_negative()),
                    "style_modifiers": compiled_prompt.style_modifiers
                },
                f"Compiled prompt with {len(compiled_prompt.style_modifiers)} style modifiers"
            )
        
        # Step 5: Generate Image
        image_bytes = None
        if request.type in ["image", "both"]:
            logger.start_stage(PipelineStage.IMAGE_GENERATION, {
                "model": "comfyui FLUX (primary) -> huggingface SDXL (fallback)"
            })
            
            # Use compiled prompt if available
            generation_prompt = compiled_prompt.get_full_positive() if compiled_prompt else request.prompt
            negative_prompt = compiled_prompt.get_full_negative() if compiled_prompt else None
            
            image_result = await generate_marketing_image(
                brand_context,
                generation_prompt,
                style=None,
                negative_prompt=negative_prompt,
                aspect_ratio=request.aspect_ratio,
            )
            
            result.image_without_text_url = image_result["url"]
            result.colors_used = image_result.get("colors_extracted", [])
            
            if image_result["url"].startswith("data:image"):
                base64_data = image_result["url"].split(",")[1]
                image_bytes = base64.b64decode(base64_data)
            
            logger.end_stage(
                {
                    "provider": image_result.get("provider"),
                    "model_used": image_result.get("model_used"),
                    "fallback_used": image_result.get("fallback_used"),
                    "colors_extracted": result.colors_used[:5],
                },
                f"Generated image, extracted {len(result.colors_used)} colors"
            )
        
        # Step 6: Generate Text
        if request.type in ["text", "both"]:
            logger.start_stage(PipelineStage.TEXT_GENERATION, {
                "model": "llama-3.3-70b-versatile"
            })
            
            text_result = await generate_marketing_text(
                brand_context,
                request.prompt
            )
            result.headline = text_result["headline"]
            result.body_copy = text_result["body_copy"]
            
            logger.end_stage(
                {"headline_length": len(result.headline or ""), "body_length": len(result.body_copy or "")},
                f"Generated headline: '{result.headline[:50]}...'" if result.headline else "No headline"
            )
        
        # Step 7: Composite Text Overlay
        if image_bytes and request.include_text_overlay and request.type == "both":
            logger.start_stage(PipelineStage.POST_PROCESSING, {"operation": "text_overlay"})
            
            try:
                composited_bytes = composite_text_on_image(
                    image_bytes=image_bytes,
                    headline=result.headline,
                    body_copy=result.body_copy,
                    brand_context=brand_context,
                    layout=request.text_layout or "bottom_centered"
                )
                composited_base64 = base64.b64encode(composited_bytes).decode('utf-8')
                result.image_url = f"data:image/png;base64,{composited_base64}"
                logger.end_stage({"layout": request.text_layout}, "Applied text overlay successfully")
            except Exception as overlay_error:
                print(f"Text overlay failed: {overlay_error}")
                result.image_url = result.image_without_text_url
                logger.end_stage({"error": str(overlay_error)}, f"Text overlay failed: {overlay_error}")
        else:
            result.image_url = result.image_without_text_url
        
        # Step 8: Calculate Scores
        result.brand_score = await calculate_brand_score(
            brand_context,
            result.image_url,
            result.colors_used
        )
        
        # Calculate constraint satisfaction
        if constraint_set:
            satisfied = len([c for c in constraint_set.global_constraints if c.strength <= 0.7])
            total = len(constraint_set.global_constraints)
            result.constraint_satisfaction_score = satisfied / total if total > 0 else 1.0
        
        # Record timing
        result.generation_time_ms = int((time.time() - start_time) * 1000)
        if request.type in ["image", "both"]:
            provider = image_result.get("provider") if "image_result" in locals() else None
            model_used = image_result.get("model_used") if "image_result" in locals() else None
            if provider and model_used:
                result.model_used = f"{provider}:{model_used}"
            elif model_used:
                result.model_used = str(model_used)
        
        # Save enhanced generation to Neo4j
        save_advanced_generation(neo4j_client, request, result)
        
        # Log relationship created
        logger.add_neo4j_query(
            "MATCH (b:Brand {id: $brand_id}) CREATE (g:Generation {...}) CREATE (b)-[:GENERATED]->(g)",
            {"brand_id": request.brand_id}
        )
        logger.add_relationship_created("Brand", "GENERATED", f"Generation:{result.generation_id}")
        
        # Complete pipeline logging
        logger.start_stage(PipelineStage.COMPLETED, {})
        logger.end_stage(
            {
                "generation_id": result.generation_id,
                "brand_score": result.brand_score,
                "total_time_ms": result.generation_time_ms
            },
            f"Generation complete! Brand score: {result.brand_score:.2%}"
        )
        logger.complete()
        
        # Store execution for visualization
        store_execution(logger.get_execution())
        
        # Print summary to console for debugging
        logger.print_summary()
        
        # Add pipeline execution ID to result for frontend
        result.pipeline_execution_id = logger.execution.execution_id
        
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.log_error(str(e))
        store_execution(logger.get_execution())
        raise HTTPException(status_code=500, detail=str(e))


# === Feedback Endpoints ===

@router.post("/advanced/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback on a generation.
    
    Feedback is used to:
    - Learn user preferences
    - Detect negative patterns
    - Update constraints
    - Improve future generations
    
    Supports multiple feedback levels:
    - whole: Feedback on entire image
    - element: Feedback on specific scene element
    - attribute: Feedback on specific attribute (lighting, color, etc.)
    """
    from app.database.neo4j_client import neo4j_client
    from app.generation.feedback_learning import FeedbackLearningEngine
    
    try:
        learning_engine = FeedbackLearningEngine(neo4j_client)
        
        feedback = await learning_engine.record_feedback(
            feedback_type=request.feedback_type,
            generation_id=request.generation_id,
            brand_id=request.brand_id,
            level=request.level,
            element_type=request.element_type,
            element_id=request.element_id,
            attribute=request.attribute,
            old_value=request.old_value,
            new_value=request.new_value,
            comment=request.comment,
            context=request.context
        )
        
        # Check if any preferences were updated or patterns detected
        summary = learning_engine.get_learning_summary(request.brand_id)
        
        return FeedbackResponse(
            feedback_id=feedback.id,
            recorded=True,
            preference_updated=summary["learned_preferences"] > 0,
            pattern_detected=summary["negative_patterns"] > 0,
            message="Feedback recorded successfully. Your preferences are being learned."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced/preferences/{brand_id}", response_model=List[PreferenceResponse])
async def get_learned_preferences(brand_id: str, min_confidence: float = 0.5):
    """
    Get learned preferences for a brand.
    
    Returns preferences that have been learned from user feedback,
    filtered by minimum confidence threshold.
    """
    from app.database.neo4j_client import neo4j_client
    from app.generation.feedback_learning import FeedbackLearningEngine
    
    learning_engine = FeedbackLearningEngine(neo4j_client)
    preferences = await learning_engine.get_preferences_for_brand(brand_id, min_confidence)
    
    return [
        PreferenceResponse(
            attribute=p.attribute,
            preferred_value=p.get_top_preference() or "",
            avoided_value=p.get_top_avoidance(),
            confidence=p.confidence,
            sample_count=p.total_samples
        ) for p in preferences
    ]


@router.get("/advanced/learning-summary/{brand_id}", response_model=LearningSummaryResponse)
async def get_learning_summary(brand_id: str):
    """
    Get summary of what has been learned for a brand.
    
    Useful for displaying learning progress and
    showing users how their feedback improves generation.
    """
    from app.database.neo4j_client import neo4j_client
    from app.generation.feedback_learning import FeedbackLearningEngine
    
    learning_engine = FeedbackLearningEngine(neo4j_client)
    summary = learning_engine.get_learning_summary(brand_id)
    
    return LearningSummaryResponse(**summary)


# === Character Consistency Endpoints ===

@router.post("/advanced/characters", response_model=CharacterResponse)
async def create_character(brand_id: str, request: CharacterRequest):
    """
    Create a character for identity consistency.
    
    Upload reference images to establish a character identity
    that will be preserved across generations and edits.
    """
    from app.database.neo4j_client import neo4j_client
    from app.generation.character_consistency import CharacterConsistencyEngine
    import httpx
    
    char_engine = CharacterConsistencyEngine(neo4j_client)
    
    # Download reference images
    reference_images = []
    async with httpx.AsyncClient() as client:
        for url in request.reference_image_urls[:5]:  # Limit to 5 references
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    reference_images.append(response.content)
            except:
                continue
    
    if not reference_images:
        raise HTTPException(status_code=400, detail="No valid reference images provided")
    
    character = await char_engine.create_character(
        name=request.name,
        description=request.description,
        reference_images=reference_images,
        brand_id=brand_id
    )
    
    # Calculate average quality
    avg_quality = sum(e.quality_score for e in character.reference_embeddings) / len(character.reference_embeddings) if character.reference_embeddings else 0
    
    return CharacterResponse(
        id=character.id,
        name=character.name,
        description=character.description,
        reference_count=len(character.reference_embeddings),
        quality_score=avg_quality
    )


@router.get("/advanced/characters/{brand_id}", response_model=List[CharacterResponse])
async def get_brand_characters(brand_id: str):
    """Get all characters associated with a brand."""
    from app.database.neo4j_client import neo4j_client
    from app.generation.character_consistency import CharacterConsistencyEngine
    
    char_engine = CharacterConsistencyEngine(neo4j_client)
    characters = await char_engine.get_character_for_brand(brand_id)
    
    return [
        CharacterResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            reference_count=len(c.reference_embeddings),
            quality_score=sum(e.quality_score for e in c.reference_embeddings) / len(c.reference_embeddings) if c.reference_embeddings else 0
        ) for c in characters
    ]


# === Scene Analysis Endpoint ===

@router.post("/advanced/analyze-scene", response_model=SceneGraphResponse)
async def analyze_scene(prompt: str, brand_id: Optional[str] = None, aspect_ratio: str = "1:1"):
    """
    Analyze a prompt and return its scene decomposition.
    
    Useful for previewing how a prompt will be interpreted
    before running full generation.
    """
    from app.database.neo4j_client import neo4j_client
    from app.generation.scene_decomposition import SceneDecompositionEngine
    
    brand_context = None
    if brand_id:
        brand_context = neo4j_client.get_brand_context(brand_id)
    
    decomposer = SceneDecompositionEngine()
    scene_graph = await decomposer.decompose_prompt(
        prompt=prompt,
        brand_context=brand_context,
        aspect_ratio=aspect_ratio
    )
    
    return SceneGraphResponse(
        id=scene_graph.id,
        original_prompt=scene_graph.original_prompt,
        elements=[
            SceneElementResponse(
                id=e.id,
                type=e.type.value,
                semantic_label=e.semantic_label,
                spatial_position=e.spatial_position.value,
                z_index=e.z_index,
                bounding_box=e.bounding_box.to_dict(),
                importance=e.importance
            ) for e in scene_graph.elements
        ],
        layout_type=scene_graph.layout_type.value,
        aspect_ratio=scene_graph.aspect_ratio,
        overall_mood=scene_graph.overall_mood,
        focal_point={"x": scene_graph.focal_point[0], "y": scene_graph.focal_point[1]}
    )


# === Evaluation Endpoints ===

class EvaluationRequest(BaseModel):
    """Request for evaluating a generation."""
    generation_id: str
    brand_id: str
    generation_result: Dict[str, Any]
    brand_context: Dict[str, Any]
    constraints_applied: List[Dict[str, Any]] = []


class EvaluationReportRequest(BaseModel):
    """Request for generating an evaluation report."""
    brand_id: str
    days: int = 7


@router.post("/advanced/evaluate")
async def evaluate_generation_endpoint(request: EvaluationRequest):
    """
    Evaluate a single generation against brand guidelines and constraints.
    
    Returns scores for:
    - Brand alignment
    - Constraint satisfaction
    - Overall quality assessment
    """
    try:
        result = await quick_evaluate(
            generation_result=request.generation_result,
            brand_context=request.brand_context,
            constraints=request.constraints_applied
        )
        
        return {
            "generation_id": request.generation_id,
            "evaluation": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.get("/advanced/evaluation-report/{brand_id}")
async def get_evaluation_report(brand_id: str, days: int = 7):
    """
    Generate comprehensive evaluation report for a brand.
    
    Returns:
    - Multi-dimensional metrics (brand alignment, satisfaction, learning effectiveness)
    - Overall scores and trends
    - Actionable recommendations
    """
    try:
        from app.database.neo4j_client import get_neo4j_client
        
        try:
            neo4j_client = get_neo4j_client()
        except:
            neo4j_client = None
        
        framework = EvaluationFramework(neo4j_client)
        report = await framework.generate_report(brand_id, days)
        
        return report.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("/advanced/metrics-summary/{brand_id}")
async def get_metrics_summary(brand_id: str):
    """
    Get a quick summary of key metrics for a brand.
    
    Useful for dashboard displays and monitoring.
    """
    try:
        from app.database.neo4j_client import get_neo4j_client
        
        try:
            neo4j_client = get_neo4j_client()
        except:
            neo4j_client = None
        
        framework = EvaluationFramework(neo4j_client)
        report = await framework.generate_report(brand_id, days=30)
        
        return {
            "brand_id": brand_id,
            "summary": report.summary,
            "overall_score": report.get_overall_score(),
            "recommendations_count": len(report.recommendations),
            "period_days": 30
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics summary failed: {str(e)}")


# === Pipeline Visualization Endpoints ===

@router.get("/advanced/pipeline-logs")
async def get_pipeline_logs(limit: int = 10):
    """
    Get recent pipeline execution logs.
    
    Shows the detailed steps of each generation for:
    - Debugging
    - Demonstrations
    - Understanding the GraphRAG process
    
    Each log includes:
    - All pipeline stages executed
    - Neo4j queries run
    - Relationships read and created
    - Timing information
    """
    return {
        "executions": get_recent_executions(limit),
        "total_stored": len(get_recent_executions(50))
    }


@router.get("/advanced/pipeline-logs/{execution_id}")
async def get_pipeline_log(execution_id: str):
    """
    Get a specific pipeline execution log by ID.
    
    Returns detailed information about every step in the generation pipeline.
    """
    execution = get_execution_by_id(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution log not found")
    return execution


@router.get("/advanced/pipeline-logs/{execution_id}/neo4j-queries")
async def get_execution_neo4j_queries(execution_id: str):
    """
    Get all Neo4j queries from a specific pipeline execution.
    
    Useful for understanding how the GraphRAG system queries the knowledge graph.
    """
    execution = get_execution_by_id(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution log not found")
    
    queries = []
    for step in execution.get("steps", []):
        for query in step.get("neo4j_queries", []):
            queries.append({
                "stage": step["stage"],
                "query": query
            })
    
    return {"execution_id": execution_id, "queries": queries, "total": len(queries)}


@router.get("/advanced/pipeline-logs/{execution_id}/graph-operations")
async def get_execution_graph_operations(execution_id: str):
    """
    Get all graph relationships read and created during a pipeline execution.
    
    Shows exactly how the GraphRAG system interacts with the knowledge graph.
    """
    execution = get_execution_by_id(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution log not found")
    
    read_operations = []
    create_operations = []
    
    for step in execution.get("steps", []):
        for rel in step.get("relationships_read", []):
            read_operations.append({
                "stage": step["stage"],
                **rel
            })
        for rel in step.get("relationships_created", []):
            create_operations.append({
                "stage": step["stage"],
                **rel
            })
    
    return {
        "execution_id": execution_id,
        "relationships_read": read_operations,
        "relationships_created": create_operations,
        "summary": {
            "total_reads": len(read_operations),
            "total_creates": len(create_operations)
        }
    }


# === Helper Functions ===

def save_advanced_generation(neo4j_client, request: AdvancedGenerateRequest, result: AdvancedGeneratedContent):
    """Save enhanced generation data to Neo4j."""
    try:
        query = """
        MATCH (b:Brand {id: $brand_id})
        CREATE (g:Generation {
            id: $gen_id,
            brand_id: $brand_id,
            prompt: $prompt,
            compiled_prompt: $compiled_prompt,
            negative_prompt: $negative_prompt,
            image_url: $image_url,
            image_without_text_url: $image_without_text_url,
            headline: $headline,
            body_copy: $body_copy,
            brand_score: $brand_score,
            constraint_satisfaction_score: $constraint_score,
            generation_time_ms: $time_ms,
            model_used: $model,
            created_at: datetime()
        })
        CREATE (b)-[:GENERATED]->(g)
        """
        
        neo4j_client.execute_query(query, {
            "brand_id": request.brand_id,
            "gen_id": result.generation_id,
            "prompt": request.prompt,
            "compiled_prompt": result.compiled_prompt.positive_prompt if result.compiled_prompt else None,
            "negative_prompt": result.compiled_prompt.negative_prompt if result.compiled_prompt else None,
            "image_url": result.image_url,
            "image_without_text_url": result.image_without_text_url,
            "headline": result.headline,
            "body_copy": result.body_copy,
            "brand_score": result.brand_score,
            "constraint_score": result.constraint_satisfaction_score,
            "time_ms": result.generation_time_ms,
            "model": result.model_used
        })
    except Exception as e:
        print(f"Error saving generation: {e}")
