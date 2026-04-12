"""
LinkedIn Post Generation API Routes

Endpoints for generating brand-voiced LinkedIn posts with industry news integration.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os

from ..linkedin.news_retriever import IndustryNewsRetriever, NewsItem
from ..linkedin.post_generator import LinkedInPostGenerator, BrandVoice, LinkedInPost

router = APIRouter(prefix="/linkedin", tags=["linkedin"])


class NewsRequest(BaseModel):
    """Request model for news retrieval."""
    industry: str
    brand_name: Optional[str] = None
    max_items: int = 5


class PostGenerationRequest(BaseModel):
    """Request model for post generation."""
    brand_name: str
    industry: str
    topic: Optional[str] = None
    news_title: Optional[str] = None
    news_summary: Optional[str] = None
    tone: str = "professional"
    values: List[str] = []
    tagline: Optional[str] = None
    post_type: str = "news_commentary"


class BatchPostRequest(BaseModel):
    """Request model for batch post generation."""
    brand_name: str
    industry: str
    tone: str = "professional"
    values: List[str] = []
    tagline: Optional[str] = None
    max_news_items: int = 3


@router.get("/health")
async def health_check():
    """Check LinkedIn module availability."""
    perplexity_configured = bool(os.getenv("PERPLEXITY_API_KEY"))
    openai_configured = bool(os.getenv("OPENAI_API_KEY"))
    
    return {
        "status": "ok",
        "perplexity_api": "configured" if perplexity_configured else "missing",
        "openai_api": "configured" if openai_configured else "missing",
        "ready": perplexity_configured and openai_configured
    }


@router.post("/news", response_model=List[NewsItem])
async def get_industry_news(request: NewsRequest):
    """
    Retrieve relevant industry news for LinkedIn post creation.
    
    Uses Perplexity API to search for recent developments in the specified industry.
    """
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Perplexity API key not configured. Set PERPLEXITY_API_KEY environment variable."
        )
    
    try:
        retriever = IndustryNewsRetriever(api_key=api_key)
        news_items = await retriever.retrieve_news(
            industry=request.industry,
            brand_name=request.brand_name,
            max_items=request.max_items
        )
        return news_items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve news: {str(e)}")


@router.post("/generate", response_model=LinkedInPost)
async def generate_post(request: PostGenerationRequest):
    """
    Generate a brand-voiced LinkedIn post.
    
    Can generate from:
    - A custom topic
    - A news item (provide news_title and news_summary)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key not configured."
        )
    
    if not request.topic and not request.news_summary:
        raise HTTPException(
            status_code=400,
            detail="Either 'topic' or 'news_summary' must be provided."
        )
    
    try:
        generator = LinkedInPostGenerator(openai_api_key=api_key)
        brand_voice = BrandVoice(
            brand_name=request.brand_name,
            industry=request.industry,
            tone=request.tone,
            values=request.values,
            tagline=request.tagline
        )
        
        # Create news item if news data provided
        news_item = None
        if request.news_title and request.news_summary:
            news_item = NewsItem(
                title=request.news_title,
                summary=request.news_summary
            )
        
        post = generator.generate_post(
            brand_voice=brand_voice,
            news_item=news_item,
            topic=request.topic,
            post_type=request.post_type
        )
        return post
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate post: {str(e)}")


@router.post("/generate-batch")
async def generate_batch_posts(request: BatchPostRequest):
    """
    Generate multiple LinkedIn posts from industry news.
    
    Combines news retrieval and post generation:
    1. Fetches relevant news for the industry
    2. Generates a post for each news item
    
    Returns both the news items and generated posts.
    """
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not perplexity_key:
        raise HTTPException(status_code=503, detail="Perplexity API key not configured.")
    if not openai_key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured.")
    
    try:
        # Step 1: Retrieve news
        retriever = IndustryNewsRetriever(api_key=perplexity_key)
        news_items = await retriever.retrieve_news(
            industry=request.industry,
            brand_name=request.brand_name,
            max_items=request.max_news_items
        )
        
        # Step 2: Generate posts
        generator = LinkedInPostGenerator(openai_api_key=openai_key)
        brand_voice = BrandVoice(
            brand_name=request.brand_name,
            industry=request.industry,
            tone=request.tone,
            values=request.values,
            tagline=request.tagline
        )
        
        posts = generator.generate_batch(brand_voice, news_items)
        
        return {
            "success": True,
            "news_retrieved": len(news_items),
            "posts_generated": len(posts),
            "news_items": [item.model_dump() for item in news_items],
            "posts": [post.model_dump() for post in posts]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch generation failed: {str(e)}")


@router.get("/post-types")
async def get_post_types():
    """Get available LinkedIn post types and their descriptions."""
    return {
        "post_types": {
            "news_commentary": "Share insights on industry news with your perspective",
            "thought_leadership": "Establish expertise with original insights", 
            "company_update": "Share brand news and achievements",
            "educational": "Teach your audience something valuable",
            "engagement": "Ask questions and spark discussion"
        }
    }


@router.get("/industries")
async def get_supported_industries():
    """Get list of industries with optimized news retrieval."""
    return {
        "industries": [
            "Technology",
            "Finance",
            "Healthcare",
            "Retail",
            "Manufacturing",
            "Education",
            "Marketing",
            "Real Estate",
            "Hospitality",
            "Energy"
        ],
        "note": "Custom industries are also supported."
    }
