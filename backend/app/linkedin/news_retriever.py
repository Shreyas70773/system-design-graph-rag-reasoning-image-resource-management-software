"""
Industry News Retriever using Perplexity API

This module retrieves relevant industry news for LinkedIn post generation.
The Perplexity API provides search-augmented responses that include real-time
web information, making it ideal for gathering current industry developments.
"""

import os
import httpx
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class NewsItem(BaseModel):
    """Structured representation of a news item."""
    title: str
    summary: str
    source: Optional[str] = None
    relevance_score: float = 0.0
    retrieved_at: datetime = datetime.now()


class IndustryNewsRetriever:
    """
    Retrieves industry-relevant news using Perplexity API.
    
    The Perplexity API combines search capabilities with LLM reasoning,
    providing summaries of recent developments in specified industries.
    """
    
    PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
    
    # Industry-specific search prompts for better results
    INDUSTRY_CONTEXTS = {
        "technology": "software, AI, cloud computing, cybersecurity, startups",
        "finance": "banking, fintech, investments, markets, cryptocurrency",
        "healthcare": "medical devices, pharmaceuticals, digital health, biotech",
        "retail": "e-commerce, consumer trends, supply chain, omnichannel",
        "manufacturing": "automation, Industry 4.0, supply chain, sustainability",
        "education": "edtech, online learning, higher education, training",
        "marketing": "digital marketing, advertising, brand strategy, social media",
        "real_estate": "property tech, commercial real estate, housing market",
        "hospitality": "travel tech, tourism, hotels, restaurants",
        "energy": "renewable energy, oil and gas, utilities, cleantech",
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the news retriever.
        
        Args:
            api_key: Perplexity API key. Falls back to PERPLEXITY_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Perplexity API key required. Set PERPLEXITY_API_KEY environment variable "
                "or pass api_key parameter."
            )
    
    def _get_industry_context(self, industry: str) -> str:
        """Get additional context keywords for the industry."""
        industry_lower = industry.lower().replace(" ", "_")
        return self.INDUSTRY_CONTEXTS.get(industry_lower, industry)
    
    async def retrieve_news(
        self, 
        industry: str, 
        brand_name: Optional[str] = None,
        max_items: int = 5
    ) -> List[NewsItem]:
        """
        Retrieve recent industry news relevant for LinkedIn posts.
        
        Args:
            industry: The industry to search for news
            brand_name: Optional brand name for more targeted results
            max_items: Maximum number of news items to return
            
        Returns:
            List of NewsItem objects with titles and summaries
        """
        industry_context = self._get_industry_context(industry)
        
        # Construct search query
        brand_context = f" relevant to companies like {brand_name}" if brand_name else ""
        
        prompt = f"""Search for the latest news and developments in the {industry} industry{brand_context}.
Focus on topics related to: {industry_context}

Return {max_items} recent, significant news items that would be relevant for a LinkedIn post.
For each news item, provide:
1. A concise title
2. A brief summary (2-3 sentences)
3. Why this matters for professionals in this industry

Format each item clearly with "TITLE:", "SUMMARY:", and "RELEVANCE:" labels."""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.PERPLEXITY_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "sonar",  # Online model for real-time search
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a professional news aggregator for business professionals. Provide accurate, recent news with proper context."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.2,
                        "max_tokens": 2000
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    raise Exception(f"Perplexity API error: {response.status_code} - {response.text}")
                
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                return self._parse_news_response(content)
                
        except httpx.TimeoutException:
            raise Exception("Perplexity API request timed out")
        except Exception as e:
            raise Exception(f"Failed to retrieve news: {str(e)}")
    
    def _parse_news_response(self, content: str) -> List[NewsItem]:
        """Parse the Perplexity response into structured NewsItem objects."""
        news_items = []
        
        # Split by common delimiters between news items
        sections = content.split("\n\n")
        
        current_item = {"title": "", "summary": "", "relevance": ""}
        
        for section in sections:
            lines = section.strip().split("\n")
            
            for line in lines:
                line = line.strip()
                if line.startswith("TITLE:") or line.startswith("**TITLE"):
                    # Save previous item if exists
                    if current_item["title"] and current_item["summary"]:
                        news_items.append(NewsItem(
                            title=current_item["title"],
                            summary=current_item["summary"],
                            relevance_score=0.8
                        ))
                    current_item = {"title": line.replace("TITLE:", "").replace("**", "").strip(), "summary": "", "relevance": ""}
                elif line.startswith("SUMMARY:") or line.startswith("**SUMMARY"):
                    current_item["summary"] = line.replace("SUMMARY:", "").replace("**", "").strip()
                elif line.startswith("RELEVANCE:") or line.startswith("**RELEVANCE"):
                    current_item["relevance"] = line.replace("RELEVANCE:", "").replace("**", "").strip()
                elif current_item["title"] and not current_item["summary"]:
                    # Continuation of title
                    current_item["summary"] = line
        
        # Add last item
        if current_item["title"] and current_item["summary"]:
            news_items.append(NewsItem(
                title=current_item["title"],
                summary=current_item["summary"],
                relevance_score=0.8
            ))
        
        # Fallback: if parsing failed, create a single item from the whole response
        if not news_items and content.strip():
            news_items.append(NewsItem(
                title="Industry Update",
                summary=content[:500] + "..." if len(content) > 500 else content,
                relevance_score=0.5
            ))
        
        return news_items


# Synchronous wrapper for non-async contexts
def retrieve_industry_news(
    industry: str,
    brand_name: Optional[str] = None,
    max_items: int = 5,
    api_key: Optional[str] = None
) -> List[NewsItem]:
    """
    Synchronous wrapper for news retrieval.
    
    Args:
        industry: The industry to search for news
        brand_name: Optional brand name for targeted results
        max_items: Maximum number of news items
        api_key: Optional Perplexity API key
        
    Returns:
        List of NewsItem objects
    """
    import asyncio
    retriever = IndustryNewsRetriever(api_key=api_key)
    return asyncio.run(retriever.retrieve_news(industry, brand_name, max_items))
