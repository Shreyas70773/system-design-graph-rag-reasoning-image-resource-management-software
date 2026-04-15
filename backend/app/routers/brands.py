"""
Brand management endpoints
- Scrape website for brand data
- Logo quality check and enhancement
"""
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, HttpUrl
from typing import Optional, List

router = APIRouter()


# === Request/Response Models ===

class ScrapeRequest(BaseModel):
    """Request to scrape a website for brand data"""
    website_url: HttpUrl


class ColorInfo(BaseModel):
    """Color information"""
    hex: str
    name: Optional[str] = None


class LogoInfo(BaseModel):
    """Logo information"""
    url: str
    quality_score: Optional[float] = None
    needs_enhancement: bool = False


class BrandData(BaseModel):
    """Scraped brand data"""
    id: Optional[str] = None
    company_name: str
    tagline: Optional[str] = None
    website: str
    logo: Optional[LogoInfo] = None
    colors: List[ColorInfo] = []


class QualityCheckResponse(BaseModel):
    """Logo quality check response"""
    quality_score: float
    resolution: dict
    is_blurry: bool
    format: str
    needs_enhancement: bool
    recommendations: List[str]


class GenerateLogoRequest(BaseModel):
    """Request to generate AI logo"""
    style: Optional[str] = "modern minimalist"
    include_text: bool = True


# === Endpoints ===

@router.post("/scrape", response_model=BrandData)
async def scrape_website(request: ScrapeRequest):
    """
    Scrape a website to extract brand information.
    
    Extracts:
    - Company name (from title, meta tags)
    - Tagline (from meta description, h1)
    - Logo (from img tags, favicon)
    - Brand colors (from logo, CSS)
    """
    from app.scraping.website_scraper import scrape_brand_data
    
    try:
        brand_data = await scrape_brand_data(str(request.website_url))
        return brand_data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{brand_id}")
async def get_brand(brand_id: str):
    """Get brand data by ID"""
    from app.database.neo4j_client import neo4j_client
    
    brand = neo4j_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


@router.post("/{brand_id}/logo/check-quality", response_model=QualityCheckResponse)
async def check_logo_quality(brand_id: str):
    """
    Assess the quality of a brand's logo.
    
    Checks:
    - Resolution (minimum 200x200)
    - Blur detection (Laplacian variance)
    - File format
    
    Returns score 0.0-1.0 and recommendations.
    """
    from app.quality.image_quality import check_logo_quality
    from app.database.neo4j_client import neo4j_client
    
    brand = neo4j_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    if not brand.get("logo_url"):
        raise HTTPException(status_code=400, detail="Brand has no logo")
    
    try:
        quality_result = await check_logo_quality(brand["logo_url"])
        return quality_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{brand_id}/logo/generate-ai")
async def generate_ai_logo(brand_id: str, request: GenerateLogoRequest):
    """
    Generate an AI logo for a brand using Hugging Face SDXL.
    
    Uses brand context (name, colors, industry) to create
    a prompt for logo generation.
    """
    from app.quality.enhancement import generate_ai_logo
    from app.database.neo4j_client import neo4j_client
    
    brand = neo4j_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    try:
        result = await generate_ai_logo(brand, request.style, request.include_text)
        
        # Update brand with new logo
        neo4j_client.update_brand_logo(brand_id, result["logo_url"], "ai_generated")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{brand_id}/logo/upload")
async def upload_logo(brand_id: str, file: UploadFile = File(...)):
    """
    Upload a custom logo for a brand and evaluate basic image quality.
    """
    from io import BytesIO

    from PIL import Image

    from app.database.neo4j_client import neo4j_client
    from app.quality.image_quality import calculate_blur_score, calculate_resolution_score, check_blur, check_resolution
    from app.services.storage_service import get_storage_service

    brand = neo4j_client.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are supported")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Logo file exceeds 10 MB limit")

    try:
        image = Image.open(BytesIO(data))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {exc}")

    storage = get_storage_service()
    stored = await storage.save_logo(
        brand_id=brand_id,
        filename=file.filename or "logo",
        content_type=file.content_type,
        data=data,
    )

    # Persist logo URL in graph.
    neo4j_client.update_brand_logo(brand_id, stored.url, "uploaded")

    width, height = image.size
    resolution_ok = check_resolution(image)
    resolution_score = calculate_resolution_score(width, height)
    is_blurry, blur_variance = check_blur(image)
    blur_score = calculate_blur_score(blur_variance)
    quality_score = round((resolution_score * 0.5) + (blur_score * 0.5), 2)

    recommendations = []
    if not resolution_ok:
        recommendations.append(f"Image resolution is low ({width}x{height}). Minimum recommended is 200x200.")
    if is_blurry:
        recommendations.append("Image appears blurry. Consider uploading a sharper file.")
    if not recommendations:
        recommendations.append("Logo uploaded successfully and quality checks passed.")

    return {
        "brand_id": brand_id,
        "logo_url": stored.url,
        "storage_backend": stored.storage_backend,
        "quality_score": quality_score,
        "resolution": {
            "width": width,
            "height": height,
            "meets_minimum": resolution_ok,
        },
        "is_blurry": is_blurry,
        "needs_enhancement": quality_score < 0.7,
        "recommendations": recommendations,
    }
