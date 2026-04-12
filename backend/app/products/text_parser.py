"""
Product Text Parser Module
Uses Groq LLM to extract structured product data from text.
"""
import httpx
import json
from typing import List, Dict, Any

from app.config import get_settings


async def parse_products_with_llm(text: str) -> List[Dict[str, Any]]:
    """
    Parse products from a text description using Groq Llama 3.
    
    Examples:
        Input: "We sell coffee ($15), cold brew ($5), and pastries ($3-8)"
        Output: [
            {"name": "coffee", "price": "$15", "category": "beverages"},
            {"name": "cold brew", "price": "$5", "category": "beverages"},
            {"name": "pastries", "price": "$3-8", "category": "food"}
        ]
    
    Args:
        text: Raw text containing product information
        
    Returns:
        List of product dictionaries
    """
    settings = get_settings()
    
    if not settings.groq_api_key:
        raise Exception("Groq API key not configured")
    
    # Build the prompt
    prompt = build_extraction_prompt(text)
    
    # Call Groq API
    response_text = await call_groq_api(prompt, settings.groq_api_key)
    
    # Parse the JSON response
    products = parse_llm_response(response_text)
    
    return products


def build_extraction_prompt(text: str) -> str:
    """
    Build a prompt for product extraction.
    
    Args:
        text: The text to extract products from
        
    Returns:
        Formatted prompt string
    """
    return f"""Extract products/services from the following text and return them as a JSON array.

For each product, extract:
- name: The product name
- price: The price if mentioned (keep original format like "$15" or "$10-20")
- price_range: A category like "budget", "mid-range", or "premium" based on price
- category: A general category for the product
- description: A brief description if available

Text to analyze:
"{text}"

Return ONLY a valid JSON array with the products. No explanation or other text.
Example format:
[
  {{"name": "Product Name", "price": "$XX", "price_range": "mid-range", "category": "category", "description": "brief description"}}
]

If no products are found, return an empty array: []

JSON response:"""


async def call_groq_api(prompt: str, api_key: str) -> str:
    """
    Call Groq API with Llama 3 model.
    
    Args:
        prompt: The prompt to send
        api_key: Groq API key
        
    Returns:
        Response text from the model
    """
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant that extracts structured product data from text. Always respond with valid JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,  # Low temperature for consistent extraction
        "max_tokens": 2000
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(API_URL, headers=headers, json=payload)
        
        if response.status_code != 200:
            error_detail = response.text
            raise Exception(f"Groq API error: {response.status_code} - {error_detail}")
        
        result = response.json()
        return result["choices"][0]["message"]["content"]


def parse_llm_response(response_text: str) -> List[Dict[str, Any]]:
    """
    Parse the LLM response to extract product data.
    
    Handles various response formats and cleans up the JSON.
    
    Args:
        response_text: Raw response from LLM
        
    Returns:
        List of product dictionaries
    """
    # Clean up the response
    text = response_text.strip()
    
    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    
    text = text.strip()
    
    # Try to parse as JSON
    try:
        products = json.loads(text)
        
        # Ensure it's a list
        if isinstance(products, dict):
            products = [products]
        
        # Validate and clean each product
        cleaned_products = []
        for p in products:
            if isinstance(p, dict) and p.get('name'):
                cleaned_products.append({
                    "name": str(p.get('name', '')),
                    "price": str(p.get('price', '')) if p.get('price') else None,
                    "price_range": str(p.get('price_range', '')) if p.get('price_range') else None,
                    "category": str(p.get('category', '')) if p.get('category') else None,
                    "description": str(p.get('description', '')) if p.get('description') else None
                })
        
        return cleaned_products
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM response as JSON: {e}")
        print(f"Response was: {text}")
        return []
