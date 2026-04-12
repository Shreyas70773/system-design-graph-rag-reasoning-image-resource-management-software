"""
Search Router - Perplexity-powered search for marketing content research
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import httpx
import os

from app.config import get_settings

router = APIRouter()


class SearchRequest(BaseModel):
    """Request for Perplexity search"""
    query: str = Field(..., description="Search query for marketing research")
    brand_context: Optional[str] = Field(None, description="Optional brand context to inform search")
    search_type: str = Field("general", description="general, competitor, trends, ideas")


class SearchResult(BaseModel):
    """A single search result"""
    title: str
    content: str
    source: Optional[str] = None


class SearchResponse(BaseModel):
    """Response from search"""
    success: bool
    query: str
    results: List[SearchResult]
    summary: str
    sources: List[str]


@router.post("/search", response_model=SearchResponse)
async def search_content(request: SearchRequest):
    """
    Search for marketing content ideas using Perplexity AI.
    
    Great for:
    - Competitor research
    - Trending topics in your industry
    - Content inspiration
    - Marketing best practices
    """
    settings = get_settings()
    api_key = settings.perplexity_api_key
    
    if not api_key:
        raise HTTPException(
            status_code=503, 
            detail="Perplexity API key not configured. Please add PERPLEXITY_API_KEY to your environment."
        )
    
    # Build the search prompt based on type
    if request.search_type == "competitor":
        system_prompt = """You are a marketing research assistant. Search for competitor marketing strategies 
        and content examples. Format findings in a clear, actionable way for content creators."""
    elif request.search_type == "trends":
        system_prompt = """You are a marketing trends analyst. Find the latest trends and viral content formats 
        relevant to the query. Focus on what's working now in social media marketing."""
    elif request.search_type == "ideas":
        system_prompt = """You are a creative content strategist. Generate content ideas inspired by 
        successful examples found online. Be specific and actionable."""
    else:
        system_prompt = """You are a marketing research assistant. Provide helpful information for 
        creating marketing content. Include relevant examples and best practices."""
    
    # Add brand context if provided
    user_message = request.query
    if request.brand_context:
        user_message = f"Brand Context: {request.brand_context}\n\nQuery: {request.query}"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-sonar-large-128k-online",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "return_citations": True,
                    "search_recency_filter": "month"  # Focus on recent content
                }
            )
            
            if response.status_code != 200:
                error_text = response.text
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Perplexity API error: {error_text}"
                )
            
            data = response.json()
            
            # Extract the response
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            citations = data.get("citations", [])
            
            # Parse into structured results
            # Split by sections or paragraphs
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            
            results = []
            for i, para in enumerate(paragraphs[:5]):  # Limit to 5 results
                results.append(SearchResult(
                    title=f"Finding {i+1}",
                    content=para,
                    source=citations[i] if i < len(citations) else None
                ))
            
            return SearchResponse(
                success=True,
                query=request.query,
                results=results,
                summary=content[:500] + "..." if len(content) > 500 else content,
                sources=citations[:10]
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Search request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/quick")
async def quick_search(query: str, brand_id: Optional[str] = None):
    """
    Quick search endpoint for simple queries.
    Returns just the summary text for easy integration.
    """
    settings = get_settings()
    api_key = settings.perplexity_api_key
    
    if not api_key:
        return {
            "success": False,
            "error": "Perplexity API not configured",
            "fallback": f"Search results for: {query} (API not available)"
        }
    
    # Get brand context if brand_id provided
    brand_context = None
    if brand_id:
        try:
            from app.database.neo4j_client import neo4j_client
            brand = neo4j_client.get_brand(brand_id)
            if brand:
                brand_context = f"Brand: {brand.get('name', '')} - {brand.get('tagline', '')}"
        except:
            pass
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-sonar-small-128k-online",  # Faster model for quick search
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are a marketing assistant. Provide brief, actionable insights. Be concise."
                        },
                        {
                            "role": "user", 
                            "content": f"{brand_context + '. ' if brand_context else ''}{query}"
                        }
                    ],
                    "return_citations": True
                }
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}",
                    "fallback": f"Could not search for: {query}"
                }
            
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            citations = data.get("citations", [])
            
            return {
                "success": True,
                "result": content,
                "sources": citations[:5]
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "fallback": f"Search failed for: {query}"
        }
