"""
Marketing Text Generation Module
Generates headlines and body copy using Groq Llama 3.
"""
import httpx
from typing import Dict, Any, Optional

from app.config import get_settings


async def generate_marketing_text(
    brand_context: Dict[str, Any],
    prompt: str
) -> Dict[str, str]:
    """
    Generate marketing text (headline + body copy) for a brand.
    
    Args:
        brand_context: Full brand context from Neo4j
        prompt: User's content request
        
    Returns:
        Dict with headline and body_copy
    """
    settings = get_settings()
    
    if not settings.groq_api_key:
        raise Exception("Groq API key not configured")
    
    # Build the text generation prompt
    full_prompt = build_text_prompt(brand_context, prompt)
    
    # Generate with Groq
    response_text = await call_groq_api(full_prompt, settings.groq_api_key)
    
    # Parse the response
    result = parse_marketing_text(response_text)
    
    return result


def build_text_prompt(
    brand_context: Dict[str, Any],
    user_prompt: str
) -> str:
    """
    Build a prompt for marketing text generation.
    
    Args:
        brand_context: Brand data from Neo4j
        user_prompt: User's content request
        
    Returns:
        Formatted prompt for the LLM
    """
    brand_name = brand_context.get('name', 'Company')
    tagline = brand_context.get('tagline', '')
    
    # Prefer selected products over general products
    product_info = ""
    if brand_context.get('product_context'):
        # User-selected products with detailed context
        product_info = f"Featured Products (include these in the content):\n{brand_context['product_context']}"
    elif brand_context.get('selected_products'):
        # Selected products without pre-built context
        products = brand_context['selected_products']
        product_details = []
        for p in products:
            detail = p.get('name', '')
            if p.get('description'):
                detail += f": {p.get('description', '')[:100]}"
            if p.get('price'):
                detail += f" ({p['price']})"
            if detail:
                product_details.append(f"- {detail}")
        if product_details:
            product_info = f"Featured Products (include these in the content):\n" + "\n".join(product_details)
    else:
        # Fall back to general products
        products = brand_context.get('products', [])
        if products:
            product_details = []
            for p in products[:5]:
                detail = p.get('name', '')
                if p.get('price'):
                    detail += f" ({p['price']})"
                if detail:
                    product_details.append(detail)
            if product_details:
                product_info = f"Products/Services: {', '.join(product_details)}"
    
    return f"""You are an expert marketing copywriter. Create compelling marketing content for the following brand:

Brand Name: {brand_name}
{f'Brand Tagline: {tagline}' if tagline else ''}
{product_info}

User Request: {user_prompt}

Generate a catchy HEADLINE (max 10 words) and persuasive BODY COPY (2-3 sentences, max 50 words).

The tone should be professional yet engaging. Focus on benefits and value proposition.

Respond in this exact format:
HEADLINE: [Your headline here]
BODY: [Your body copy here]"""


async def call_groq_api(prompt: str, api_key: str) -> str:
    """
    Call Groq API for text generation.
    
    Args:
        prompt: The generation prompt
        api_key: Groq API key
        
    Returns:
        Generated text
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
                "content": "You are an expert marketing copywriter who creates compelling, concise marketing content."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,  # Some creativity but not too wild
        "max_tokens": 500
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(API_URL, headers=headers, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Groq API error: {response.status_code} - {response.text}")
        
        result = response.json()
        return result["choices"][0]["message"]["content"]


def parse_marketing_text(response_text: str) -> Dict[str, str]:
    """
    Parse the LLM response to extract headline and body copy.
    
    Args:
        response_text: Raw response from LLM
        
    Returns:
        Dict with headline and body_copy
    """
    result = {
        "headline": "",
        "body_copy": ""
    }
    
    lines = response_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        
        if line.upper().startswith('HEADLINE:'):
            result['headline'] = line[9:].strip()
        elif line.upper().startswith('BODY:'):
            result['body_copy'] = line[5:].strip()
    
    # Fallback: if parsing failed, use the whole response
    if not result['headline'] and not result['body_copy']:
        # Try to split intelligently
        parts = response_text.strip().split('\n\n')
        if len(parts) >= 2:
            result['headline'] = parts[0].strip()[:100]
            result['body_copy'] = parts[1].strip()[:300]
        else:
            result['headline'] = response_text[:50]
            result['body_copy'] = response_text
    
    return result
