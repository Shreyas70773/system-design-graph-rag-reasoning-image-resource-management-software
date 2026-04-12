"""
Brand DNA API Router
====================
Exposes the GraphRAG Brand DNA system via REST API.
Includes endpoints for:
- Brand DNA retrieval and updates
- Graph-conditioned generation
- Semantic feedback processing
- Live graph visualization data
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import json
from datetime import datetime

from app.services.brand_dna_service import get_brand_dna_service, BrandDNA


router = APIRouter(prefix="/api/brand-dna", tags=["Brand DNA"])


# ===================
# REQUEST/RESPONSE MODELS
# ===================

class GenerateRequest(BaseModel):
    """Request for graph-conditioned generation"""
    prompt: str = Field(..., description="User's generation prompt")
    headline: Optional[str] = Field(None, description="Optional headline text")
    body_copy: Optional[str] = Field(None, description="Optional body copy text")
    product_id: Optional[str] = Field(None, description="Product reference for IP-Adapter")
    character_id: Optional[str] = Field(None, description="Character reference for face consistency")
    aspect_ratio: str = Field("1:1", description="1:1, 16:9, 9:16, 4:3")
    text_layout: str = Field("bottom_centered", description="Text placement: bottom_centered, top_centered, center_overlay, bottom_left")
    include_logo: bool = Field(False, description="Whether to add brand logo to image")
    use_reasoning: bool = Field(True, description="Enable LLM planning stage")


class FeedbackRequest(BaseModel):
    """Request for processing semantic feedback"""
    generation_id: str
    rating: str = Field(..., description="positive, negative, or neutral")
    selected_aspects: List[str] = Field(default_factory=list, description="color, style, composition, product, character")
    feedback_text: str = Field("", description="Free-form feedback description")


class AddColorRequest(BaseModel):
    """Add color to brand DNA"""
    hex: str = Field(..., description="Hex color code (e.g., #FF5733)", alias="hex_code")
    name: str = Field(..., description="Color name (e.g., 'Brand Orange')")
    role: str = Field("accent", description="primary, secondary, accent, background")
    
    class Config:
        populate_by_name = True


class AddProductRequest(BaseModel):
    """Add product reference"""
    name: str
    category: str
    image_url: str
    description: str = ""


class AddCharacterRequest(BaseModel):
    """Add character reference for consistency"""
    name: str
    reference_image_url: str
    body_type: str = "average"


class UpdateCompositionRequest(BaseModel):
    """Update composition preferences"""
    layout: Optional[str] = None
    text_density: Optional[str] = None
    text_position: Optional[str] = None
    overlay_opacity: Optional[float] = None
    padding_preference: Optional[str] = None
    aspect_ratio_preference: Optional[str] = None


class AddStyleRequest(BaseModel):
    """Add style to brand DNA"""
    type: str = Field(..., description="Style type: bold, minimalist, playful, luxury, professional")
    keywords: List[str] = Field(default_factory=list, description="Style keywords")
    negative_keywords: List[str] = Field(default_factory=list, description="What to avoid")


# ===================
# BRAND DNA ENDPOINTS
# ===================

@router.get("/{brand_id}")
async def get_brand_dna(brand_id: str):
    """
    Get complete Brand DNA for a brand.
    Returns all nodes: colors, styles, composition, products, characters, learned preferences.
    """
    service = get_brand_dna_service()
    dna = await service.get_brand_dna(brand_id)
    
    if not dna:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    return {
        "success": True,
        "brand_dna": dna.to_dict()
    }


@router.get("/{brand_id}/graph")
async def get_brand_graph(brand_id: str):
    """
    Get Brand DNA as graph visualization data.
    Returns nodes and edges for frontend visualization.
    """
    try:
        service = get_brand_dna_service()
        dna = await service.get_brand_dna(brand_id)
        
        if not dna:
            # Return empty graph for brands not yet in new schema
            return {
                "success": True,
                "graph": {
                    "nodes": [{"id": f"brand_{brand_id}", "type": "brand", "label": "Brand", "data": {}}],
                    "edges": [],
                    "stats": {"total_nodes": 1, "total_edges": 0, "colors": 0, "styles": 0, "products": 0, "characters": 0, "learned_preferences": 0}
                }
            }
        
        nodes = []
        edges = []
        
        # Brand node (center)
        nodes.append({
            "id": f"brand_{brand_id}",
            "type": "brand",
            "label": dna.brand_name,
            "data": {
                "tagline": dna.tagline,
                "industry": dna.industry,
                "logo_url": dna.logo_url
            }
        })
        
        # Color nodes - use index to ensure unique IDs
        for i, color in enumerate(dna.colors):
            hex_code = color.get('hex', '').replace('#', '')
            node_id = f"color_{hex_code}_{i}"
            nodes.append({
                "id": node_id,
                "type": "color",
                "label": color.get("name", color.get("hex")),
                "data": color
            })
            edges.append({
                "source": f"brand_{brand_id}",
                "target": node_id,
                "type": "HAS_COLOR",
                "data": {"role": color.get("role"), "weight": color.get("weight", 0.5)}
            })
        
        # Style nodes
        for i, style in enumerate(dna.styles):
            node_id = f"style_{style.get('id', i)}"
            nodes.append({
                "id": node_id,
                "type": "style",
                "label": style.get("type", "Style"),
                "data": style
            })
            edges.append({
                "source": f"brand_{brand_id}",
                "target": node_id,
                "type": "HAS_STYLE",
                "data": {"weight": style.get("weight", 0.5)}
            })
        
        # Composition node
        if dna.composition:
            nodes.append({
                "id": f"composition_{brand_id}",
                "type": "composition",
                "label": "Composition",
                "data": dna.composition
            })
            edges.append({
                "source": f"brand_{brand_id}",
                "target": f"composition_{brand_id}",
                "type": "HAS_COMPOSITION"
            })
        
        # Product nodes
        for product in dna.products:
            node_id = f"product_{product.get('id')}"
            nodes.append({
                "id": node_id,
                "type": "product",
                "label": product.get("name"),
                "data": product
            })
            edges.append({
                "source": f"brand_{brand_id}",
                "target": node_id,
                "type": "SELLS"
            })
        
        # Character nodes
        for character in dna.characters:
            node_id = f"character_{character.get('id')}"
            nodes.append({
                "id": node_id,
                "type": "character",
                "label": character.get("name"),
                "data": character
            })
            edges.append({
                "source": f"brand_{brand_id}",
                "target": node_id,
                "type": "HAS_CHARACTER"
            })
        
        # Learned preference nodes
        for pref in dna.learned_preferences:
            node_id = f"pref_{pref.get('id')}"
            nodes.append({
                "id": node_id,
                "type": "learned_preference",
                "label": f"When {pref.get('trigger', '?')[:20]}...",
                "data": pref
            })
            edges.append({
                "source": f"brand_{brand_id}",
                "target": node_id,
                "type": "LEARNED",
                "data": {"confidence": pref.get("confidence", 0.5)}
            })
        
        return {
            "success": True,
            "graph": {
                "nodes": nodes,
                "edges": edges,
                "stats": {
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                    "colors": len(dna.colors),
                    "styles": len(dna.styles),
                    "products": len(dna.products),
                    "characters": len(dna.characters),
                    "learned_preferences": len(dna.learned_preferences)
                }
            }
        }
    except Exception as e:
        # Return empty graph on error
        return {
            "success": False,
            "error": str(e),
            "graph": {
                "nodes": [{"id": f"brand_{brand_id}", "type": "brand", "label": "Brand", "data": {}}],
                "edges": [],
                "stats": {"total_nodes": 1, "total_edges": 0, "colors": 0, "styles": 0, "products": 0, "characters": 0, "learned_preferences": 0}
            }
        }


# ===================
# GENERATION ENDPOINTS
# ===================

@router.post("/{brand_id}/generate")
async def generate_content(brand_id: str, request: GenerateRequest):
    """
    Full GraphRAG generation pipeline:
    1. Retrieve Brand DNA from Neo4j
    2. LLM plans generation (if use_reasoning=True)
    3. Apply learned preferences
    4. Condition diffusion model
    5. Generate image
    6. Store generation in graph
    
    Returns image URL + full pipeline trace for visualization.
    """
    service = get_brand_dna_service()
    
    result = await service.generate_content(
        brand_id=brand_id,
        user_prompt=request.prompt,
        headline=request.headline,
        body_copy=request.body_copy,
        product_id=request.product_id,
        character_id=request.character_id,
        aspect_ratio=request.aspect_ratio,
        text_layout=request.text_layout,
        include_logo=request.include_logo,
        use_reasoning=request.use_reasoning
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=500, 
            detail=result.get("error_message", "Generation failed")
        )
    
    return result


@router.post("/{brand_id}/generate/stream")
async def generate_content_stream(brand_id: str, request: GenerateRequest):
    """
    Streaming version of generate - sends pipeline steps as they complete.
    Use for live visualization of the generation process.
    """
    service = get_brand_dna_service()
    
    async def stream_generator():
        # Step 1: Brand DNA
        yield json.dumps({
            "step": "retrieve_brand_dna",
            "status": "started",
            "message": "Retrieving Brand DNA from knowledge graph..."
        }) + "\n"
        
        dna = await service.get_brand_dna(brand_id)
        if not dna:
            yield json.dumps({
                "step": "retrieve_brand_dna",
                "status": "failed",
                "error": "Brand not found"
            }) + "\n"
            return
        
        yield json.dumps({
            "step": "retrieve_brand_dna",
            "status": "completed",
            "data": {
                "colors": len(dna.colors),
                "styles": len(dna.styles),
                "products": len(dna.products),
                "learned_preferences": len(dna.learned_preferences)
            }
        }) + "\n"
        
        # Step 2: LLM Planning
        if request.use_reasoning:
            yield json.dumps({
                "step": "llm_planning",
                "status": "started",
                "message": "LLM analyzing prompt and planning generation..."
            }) + "\n"
            
            await asyncio.sleep(0.1)  # Allow client to process
        
        # Continue with full generation
        result = await service.generate_content(
            brand_id=brand_id,
            user_prompt=request.prompt,
            headline=request.headline,
            body_copy=request.body_copy,
            product_id=request.product_id,
            character_id=request.character_id,
            aspect_ratio=request.aspect_ratio,
            use_reasoning=request.use_reasoning
        )
        
        # Stream remaining steps from result
        for step in result.get("pipeline_steps", []):
            yield json.dumps(step) + "\n"
        
        # Final result
        yield json.dumps({
            "step": "complete",
            "status": "completed" if result.get("success") else "failed",
            "result": result
        }) + "\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="application/x-ndjson"
    )


# ===================
# FEEDBACK ENDPOINTS
# ===================

@router.post("/{brand_id}/feedback")
async def submit_feedback(brand_id: str, request: FeedbackRequest):
    """
    Submit semantic feedback for a generation.
    
    The feedback is analyzed by LLM to:
    1. Identify which Brand DNA nodes need updates
    2. Create new LearnedPreference nodes
    3. Update the knowledge graph
    
    Returns the analysis and all graph updates made.
    """
    service = get_brand_dna_service()
    
    result = await service.process_feedback(
        generation_id=request.generation_id,
        rating=request.rating,
        selected_aspects=request.selected_aspects,
        feedback_text=request.feedback_text
    )
    
    return result


# ===================
# BRAND DNA UPDATE ENDPOINTS
# ===================

@router.post("/{brand_id}/colors")
async def add_color(brand_id: str, request: AddColorRequest):
    """Add a color to the brand's DNA"""
    try:
        service = get_brand_dna_service()
        return await service.add_color(
            brand_id=brand_id,
            hex_code=request.hex,
            name=request.name,
            role=request.role
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/{brand_id}/products")
async def add_product(brand_id: str, request: AddProductRequest):
    """Add a product reference (for IP-Adapter conditioning)"""
    try:
        service = get_brand_dna_service()
        return await service.add_product(
            brand_id=brand_id,
            name=request.name,
            category=request.category,
            image_url=request.image_url,
            description=request.description
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/{brand_id}/characters")
async def add_character(brand_id: str, request: AddCharacterRequest):
    """Add a character reference (for PuLID face consistency)"""
    service = get_brand_dna_service()
    return await service.add_character(
        brand_id=brand_id,
        name=request.name,
        reference_image_url=request.reference_image_url,
        body_type=request.body_type
    )


@router.put("/{brand_id}/composition")
async def update_composition(brand_id: str, request: UpdateCompositionRequest):
    """Update composition preferences"""
    service = get_brand_dna_service()
    
    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    return await service.update_composition(brand_id, updates)


class UpdateLogoRequest(BaseModel):
    """Request for updating brand logo"""
    logo_url: str = Field(..., description="URL of the brand logo image")


@router.put("/{brand_id}/logo")
async def update_logo(brand_id: str, request: UpdateLogoRequest):
    """Update brand logo URL"""
    try:
        from app.database.neo4j_client import get_neo4j_client
        
        neo4j = get_neo4j_client()
        
        # Check if brand exists
        brand_check = neo4j.execute_query(
            "MATCH (b:Brand {id: $brand_id}) RETURN b",
            {"brand_id": brand_id}
        )
        
        if not brand_check:
            raise HTTPException(status_code=404, detail="Brand not found")
        
        # Update or create logo node
        query = """
        MATCH (b:Brand {id: $brand_id})
        OPTIONAL MATCH (b)-[r:HAS_LOGO]->(old_logo:Logo)
        DELETE r, old_logo
        WITH b
        CREATE (l:Logo {
            url: $logo_url,
            source: 'manual_upload',
            created_at: datetime()
        })
        CREATE (b)-[:HAS_LOGO]->(l)
        RETURN l.url as logo_url
        """
        
        result = neo4j.execute_query(query, {
            "brand_id": brand_id,
            "logo_url": request.logo_url
        })
        
        return {
            "success": True, 
            "logo_url": result[0]["logo_url"] if result else request.logo_url,
            "message": "Logo updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/{brand_id}/styles")
async def add_style(brand_id: str, request: AddStyleRequest):
    """Add a style to the brand's DNA"""
    try:
        from app.database.neo4j_client import get_neo4j_client
        import uuid
        
        neo4j = get_neo4j_client()
        style_id = str(uuid.uuid4())
        
        query = """
        MATCH (b:Brand {id: $brand_id})
        CREATE (s:StyleNode {
            id: $style_id,
            type: $type,
            keywords: $keywords,
            negative_keywords: $negative_keywords,
            weight: 0.8,
            created_at: datetime()
        })
        CREATE (b)-[:HAS_STYLE]->(s)
        RETURN s
        """
        
        result = neo4j.execute_query(query, {
            "brand_id": brand_id,
            "style_id": style_id,
            "type": request.type,
            "keywords": request.keywords,
            "negative_keywords": request.negative_keywords
        })
        
        return {"success": True, "style": dict(result[0]["s"]) if result else None}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ===================
# LEARNING ENDPOINTS
# ===================

@router.get("/{brand_id}/learning-summary")
async def get_learning_summary(brand_id: str):
    """
    Get summary of what the system has learned for this brand.
    Shows all learned preferences and their confidence levels.
    """
    service = get_brand_dna_service()
    dna = await service.get_brand_dna(brand_id)
    
    if not dna:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Group preferences by aspect
    by_aspect = {}
    for pref in dna.learned_preferences:
        aspect = pref.get("aspect", "unknown")
        if aspect not in by_aspect:
            by_aspect[aspect] = []
        by_aspect[aspect].append(pref)
    
    # Get generation stats
    from app.database.neo4j_client import get_neo4j_client
    neo4j = get_neo4j_client()
    
    stats_query = """
    MATCH (b:Brand {id: $brand_id})-[:GENERATED]->(g:Generation)
    RETURN 
        count(g) as total_generations,
        count(CASE WHEN g.user_rating = 'positive' THEN 1 END) as positive_count,
        count(CASE WHEN g.user_rating = 'negative' THEN 1 END) as negative_count,
        count(CASE WHEN g.user_rating IS NOT NULL THEN 1 END) as feedback_count
    """
    stats_result = neo4j.execute_query(stats_query, {"brand_id": brand_id})
    stats = stats_result[0] if stats_result else {}
    
    return {
        "success": True,
        "brand_id": brand_id,
        "brand_name": dna.brand_name,
        "statistics": {
            "total_generations": stats.get("total_generations", 0),
            "total_feedback": stats.get("feedback_count", 0),
            "positive_feedback": stats.get("positive_count", 0),
            "negative_feedback": stats.get("negative_count", 0),
            "learned_preferences": len(dna.learned_preferences)
        },
        "learned_preferences_by_aspect": by_aspect,
        "all_preferences": dna.learned_preferences
    }


@router.get("/{brand_id}/generation-history")
async def get_generation_history(brand_id: str, limit: int = 10):
    """Get recent generations with their feedback"""
    from app.database.neo4j_client import get_neo4j_client
    neo4j = get_neo4j_client()
    
    query = """
    MATCH (b:Brand {id: $brand_id})-[:GENERATED]->(g:Generation)
    RETURN g
    ORDER BY g.created_at DESC
    LIMIT $limit
    """
    
    results = neo4j.execute_query(query, {"brand_id": brand_id, "limit": limit})
    
    generations = []
    for record in results:
        gen = dict(record["g"])
        # Convert datetime if needed
        if gen.get("created_at"):
            gen["created_at"] = str(gen["created_at"])
        generations.append(gen)
    
    return {
        "success": True,
        "generations": generations,
        "count": len(generations)
    }


class InitializeRequest(BaseModel):
    """Request to initialize Brand DNA from website"""
    website_url: str = Field(..., description="Brand website URL to scan")


@router.post("/{brand_id}/initialize")
async def initialize_brand_dna(brand_id: str, request: InitializeRequest):
    """
    Initialize Brand DNA from website scan.
    Extracts colors, logo, and basic brand info to create initial graph.
    """
    from app.database.neo4j_client import get_neo4j_client
    from app.scraping.website_scraper import extract_brand_data_sync
    from app.scraping.color_extractor import extract_colors_from_url
    
    neo4j = get_neo4j_client()
    
    try:
        # Check if brand already exists
        check_query = "MATCH (b:Brand {id: $brand_id}) RETURN b"
        existing = neo4j.execute_query(check_query, {"brand_id": brand_id})
        
        if existing:
            return {
                "success": False,
                "error": "Brand DNA already exists",
                "brand_id": brand_id
            }
        
        # Scrape website for brand data
        brand_data = extract_brand_data_sync(request.website_url)
        
        # Extract colors from website
        colors = extract_colors_from_url(request.website_url) if hasattr(extract_colors_from_url, '__call__') else []
        
        # Create Brand node
        create_brand_query = """
        CREATE (b:Brand {
            id: $brand_id,
            name: $name,
            website_url: $url,
            logo_url: $logo_url,
            description: $description,
            industry: $industry,
            created_at: datetime()
        })
        RETURN b
        """
        
        neo4j.execute_query(create_brand_query, {
            "brand_id": brand_id,
            "name": brand_data.get("brand_name", "Unknown Brand"),
            "url": request.website_url,
            "logo_url": brand_data.get("logo_url", ""),
            "description": brand_data.get("tagline", ""),
            "industry": brand_data.get("industry", "general")
        })
        
        # Create initial CompositionNode with defaults
        create_composition_query = """
        MATCH (b:Brand {id: $brand_id})
        CREATE (c:CompositionNode {
            id: $comp_id,
            layout: 'balanced',
            text_density: 'moderate',
            text_position: 'center',
            overlay_opacity: 0.3,
            padding_preference: 'standard',
            aspect_ratio_preference: '1:1',
            updated_at: datetime()
        })
        CREATE (b)-[:HAS_COMPOSITION]->(c)
        RETURN c
        """
        
        neo4j.execute_query(create_composition_query, {
            "brand_id": brand_id,
            "comp_id": f"comp_{brand_id}"
        })
        
        # Add extracted colors
        created_colors = []
        roles = ["primary", "secondary", "accent", "background"]
        for i, color in enumerate(colors[:4]):  # Max 4 initial colors
            color_hex = color.get("hex", color) if isinstance(color, dict) else color
            color_name = color.get("name", f"Color {i+1}") if isinstance(color, dict) else f"Brand Color {i+1}"
            role = roles[i] if i < len(roles) else "accent"
            
            add_color_query = """
            MATCH (b:Brand {id: $brand_id})
            CREATE (c:ColorNode {
                id: $color_id,
                hex_code: $hex,
                name: $name,
                role: $role,
                weight: $weight
            })
            CREATE (b)-[:HAS_COLOR {role: $role}]->(c)
            RETURN c
            """
            
            neo4j.execute_query(add_color_query, {
                "brand_id": brand_id,
                "color_id": f"color_{brand_id}_{color_hex.replace('#', '')}",
                "hex": color_hex,
                "name": color_name,
                "role": role,
                "weight": 1.0 - (i * 0.2)
            })
            
            created_colors.append({
                "hex": color_hex,
                "name": color_name,
                "role": role
            })
        
        # Create initial StyleNode from scraped data
        style_keywords = brand_data.get("style_keywords", ["professional", "modern"])
        create_style_query = """
        MATCH (b:Brand {id: $brand_id})
        CREATE (s:StyleNode {
            id: $style_id,
            name: 'primary_style',
            style_type: $style_type,
            keywords: $keywords,
            weight: 1.0
        })
        CREATE (b)-[:HAS_STYLE]->(s)
        RETURN s
        """
        
        neo4j.execute_query(create_style_query, {
            "brand_id": brand_id,
            "style_id": f"style_{brand_id}_primary",
            "style_type": brand_data.get("detected_style", "professional"),
            "keywords": style_keywords
        })
        
        return {
            "success": True,
            "brand_id": brand_id,
            "brand_name": brand_data.get("brand_name", "Unknown Brand"),
            "logo_url": brand_data.get("logo_url", ""),
            "colors_created": created_colors,
            "style_created": {
                "type": brand_data.get("detected_style", "professional"),
                "keywords": style_keywords
            },
            "message": "Brand DNA initialized successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "brand_id": brand_id
        }
