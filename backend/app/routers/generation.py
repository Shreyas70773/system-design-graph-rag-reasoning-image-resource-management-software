"""
Content generation endpoints
- Generate marketing images
- Generate marketing copy
- Validate brand consistency
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Literal

router = APIRouter()


# === Request/Response Models ===

class GenerateRequest(BaseModel):
    """Request to generate marketing content"""
    brand_id: str
    prompt: str
    type: Literal["image", "text", "both"] = "both"
    style: Optional[str] = None
    product_ids: Optional[List[str]] = None  # Products to use as context
    text_layout: Optional[str] = "bottom_centered"  # Text overlay layout
    include_text_overlay: bool = True  # Whether to overlay text on image


class GeneratedContent(BaseModel):
    """Generated marketing content"""
    generation_id: Optional[str] = None
    image_url: Optional[str] = None
    image_without_text_url: Optional[str] = None  # Original image without text
    headline: Optional[str] = None
    body_copy: Optional[str] = None
    brand_score: float  # 0.0-1.0 how well it matches brand
    colors_used: List[str] = []


class FontOption(BaseModel):
    """Available font option"""
    id: str
    name: str
    description: str
    style: str


class TextLayoutOption(BaseModel):
    """Available text layout option"""
    id: str
    name: str
    description: str


class GenerationHistoryItem(BaseModel):
    """A past generation"""
    id: str
    brand_id: str
    prompt: str
    image_url: Optional[str] = None
    headline: Optional[str] = None
    body_copy: Optional[str] = None
    brand_score: float
    created_at: str


# === Endpoints ===

@router.post("/generate", response_model=GeneratedContent)
async def generate_content(request: GenerateRequest):
    """
    Generate brand-aligned marketing content.
    
    Uses brand context from Neo4j to build prompts for:
    - Hugging Face SDXL (images)
    - Groq Llama 3 (text)
    
    Validates generated content against brand colors.
    Optionally overlays generated text on the image.
    """
    from app.generation.image_generator import generate_marketing_image
    from app.generation.text_generator import generate_marketing_text
    from app.generation.validator import calculate_brand_score
    from app.generation.text_overlay import composite_text_on_image
    from app.database.neo4j_client import neo4j_client
    import base64
    
    # Get full brand context
    brand_context = neo4j_client.get_brand_context(request.brand_id)
    if not brand_context:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Add product context if product_ids provided
    if request.product_ids:
        products = neo4j_client.get_products_by_ids(request.product_ids)
        if products:
            brand_context["selected_products"] = products
            # Also build a product summary for prompts
            product_summaries = []
            for p in products:
                summary = f"- {p.get('name', 'Product')}"
                if p.get('description'):
                    summary += f": {p.get('description')[:100]}"
                if p.get('price'):
                    summary += f" ({p.get('price')})"
                product_summaries.append(summary)
            brand_context["product_context"] = "\n".join(product_summaries)
    
    result = GeneratedContent(brand_score=0.0)
    
    try:
        image_bytes = None
        
        # Generate image if requested
        if request.type in ["image", "both"]:
            image_result = await generate_marketing_image(
                brand_context, 
                request.prompt, 
                request.style
            )
            # Store original image URL (without text)
            result.image_without_text_url = image_result["url"]
            result.colors_used = image_result.get("colors_extracted", [])
            
            # Decode image bytes for potential overlay
            if image_result["url"].startswith("data:image"):
                base64_data = image_result["url"].split(",")[1]
                image_bytes = base64.b64decode(base64_data)
        
        # Generate text if requested
        if request.type in ["text", "both"]:
            text_result = await generate_marketing_text(
                brand_context, 
                request.prompt
            )
            result.headline = text_result["headline"]
            result.body_copy = text_result["body_copy"]
        
        # Composite text on image if both are generated and overlay is requested
        if image_bytes and request.include_text_overlay and request.type == "both":
            try:
                composited_bytes = composite_text_on_image(
                    image_bytes=image_bytes,
                    headline=result.headline,
                    body_copy=result.body_copy,
                    brand_context=brand_context,
                    layout=request.text_layout or "bottom_centered"
                )
                # Convert composited image to data URL
                composited_base64 = base64.b64encode(composited_bytes).decode('utf-8')
                result.image_url = f"data:image/png;base64,{composited_base64}"
            except Exception as overlay_error:
                print(f"Text overlay failed: {overlay_error}, using original image")
                result.image_url = result.image_without_text_url
        else:
            # No overlay, use original image
            result.image_url = result.image_without_text_url
        
        # Calculate brand consistency score
        result.brand_score = await calculate_brand_score(
            brand_context,
            result.image_url,
            result.colors_used
        )
        
        # Save generation to Neo4j
        generation_id = neo4j_client.save_generation(
            brand_id=request.brand_id,
            prompt=request.prompt,
            image_url=result.image_url,
            headline=result.headline,
            body_copy=result.body_copy,
            brand_score=result.brand_score
        )
        
        result.generation_id = generation_id
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generations/{brand_id}", response_model=List[GenerationHistoryItem])
async def get_generation_history(brand_id: str, limit: int = 10):
    """Get generation history for a brand"""
    from app.database.neo4j_client import neo4j_client
    
    brand = neo4j_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    generations = neo4j_client.get_brand_generations(brand_id, limit)
    return generations


@router.get("/fonts", response_model=List[FontOption])
async def get_available_fonts():
    """Get list of available fonts for text overlay"""
    from app.generation.text_overlay import get_available_fonts
    return get_available_fonts()


@router.get("/text-layouts", response_model=List[TextLayoutOption])
async def get_text_layouts():
    """Get available text layout options"""
    from app.generation.text_overlay import get_text_layouts
    return get_text_layouts()
