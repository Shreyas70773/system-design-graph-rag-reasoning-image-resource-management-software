"""
Marketing Image Generation Module
Generates brand-aligned marketing images using multiple providers (Gemini, OpenRouter, fal.ai).
"""
import httpx
import base64
from typing import Dict, Any, Optional, List
from io import BytesIO

from app.config import get_settings
from app.scraping.color_extractor import extract_colors_from_image


async def generate_marketing_image(
    brand_context: Dict[str, Any],
    prompt: str,
    style: Optional[str] = None,
    negative_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a marketing image aligned with brand guidelines.
    
    Uses FallbackGenerator to try multiple providers:
    1. Gemini (Google's native image generation)
    2. fal.ai (Flux models)
    3. Hugging Face SDXL (fallback)
    
    Args:
        brand_context: Full brand context from Neo4j
        prompt: User's content request
        style: Optional style override
        negative_prompt: Optional custom negative prompt from constraint system
        
    Returns:
        Dict with url, colors_extracted
    """
    from app.generation.image_generators import (
        get_generator, GenerationRequest, BrandCondition
    )
    
    # Build the image generation prompt
    full_prompt = build_image_prompt(brand_context, prompt, style)
    
    # Build brand colors for the request
    brand_colors = []
    colors = brand_context.get('colors', [])
    if colors:
        brand_colors = [c.get('hex', '') for c in colors[:5] if c.get('hex')]
    
    # Build style keywords from brand context
    style_keywords = []
    if style:
        style_keywords.append(style)
    if brand_context.get('tone'):
        style_keywords.append(brand_context.get('tone'))
    if brand_context.get('visual_style'):
        style_keywords.append(brand_context.get('visual_style'))
    
    # Build negative keywords including any custom negative prompt
    negative_keywords = []
    if negative_prompt:
        negative_keywords.extend(negative_prompt.split(','))
    
    # Create brand condition with proper fields
    brand_condition = BrandCondition(
        primary_colors=brand_colors,
        style_keywords=style_keywords,
        negative_keywords=negative_keywords,
        layout="centered",
        text_density="none",
        text_position="none"
    )
    
    # Create generation request with correct dataclass fields
    brand_id = brand_context.get('brand', {}).get('id', 'unknown')
    request = GenerationRequest(
        prompt=full_prompt,
        brand_id=brand_id,
        brand_condition=brand_condition,
        num_images=1
    )
    
    # Use FallbackGenerator for resilience
    generator = get_generator("fallback")
    result = await generator.generate(request)
    
    if not result.success:
        # If all providers fail, try old SDXL as last resort
        settings = get_settings()
        if settings.huggingface_token:
            try:
                image_bytes = await call_sdxl_api(full_prompt, settings.huggingface_token, negative_prompt)
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                return {
                    "url": f"data:image/png;base64,{image_base64}",
                    "colors_extracted": [],
                    "prompt_used": full_prompt
                }
            except Exception as sdxl_error:
                raise Exception(f"All image providers failed. Last error: {result.error_message}. SDXL error: {sdxl_error}")
        raise Exception(f"Image generation failed: {result.error_message}")
    
    # Extract colors from generated image for validation
    colors_extracted = []
    if result.image_url:
        try:
            # Only extract if we have base64 data
            if result.image_url.startswith("data:image"):
                base64_data = result.image_url.split(",")[1]
                image_bytes = base64.b64decode(base64_data)
                colors = extract_colors_from_image(image_bytes, color_count=5)
                colors_extracted = [c['hex'] for c in colors]
        except:
            pass
    
    return {
        "url": result.image_url,
        "colors_extracted": colors_extracted,
        "prompt_used": full_prompt,
        "provider": result.provider,
        "model_used": result.model_used
    }


def build_image_prompt(
    brand_context: Dict[str, Any],
    user_prompt: str,
    style: Optional[str] = None
) -> str:
    """
    Build a detailed prompt for marketing image generation.
    
    Incorporates brand colors, products, and style.
    Uses advanced prompt engineering for better SDXL output.
    
    Args:
        brand_context: Brand data from Neo4j
        user_prompt: User's content request
        style: Optional style preference
        
    Returns:
        Complete prompt for SDXL
    """
    brand_name = brand_context.get('name', 'Company')
    
    # Get brand colors - be more specific about how to use them
    colors = brand_context.get('colors', [])
    color_string = ""
    if colors:
        # Get hex codes for precise color matching
        hex_codes = [c.get('hex', '') for c in colors[:3] if c.get('hex')]
        color_names = [c.get('name', '') for c in colors[:3] if c.get('name')]
        if hex_codes:
            color_string = f"using brand colors {', '.join(hex_codes)}."
        elif color_names:
            color_string = f"Color scheme: {', '.join(color_names)}."
    
    # Get products for context - prioritize selected products
    product_string = ""
    if brand_context.get('selected_products'):
        products = brand_context['selected_products']
        product_names = [p.get('name', '') for p in products[:3] if p.get('name')]
        if product_names:
            product_string = f"Showcasing: {', '.join(product_names)}."
    elif brand_context.get('products'):
        products = brand_context['products']
        product_names = [p.get('name', '') for p in products[:3] if p.get('name')]
        if product_names:
            product_string = f"Related to: {', '.join(product_names)}."
    
    # Map style to detailed visual descriptions for SDXL
    style_mappings = {
        "modern minimalist": "clean modern minimalist design, simple geometric shapes, lots of whitespace, subtle gradients, professional",
        "bold and vibrant": "bold vibrant colors, dynamic composition, high contrast, energetic, eye-catching",
        "warm and cozy": "warm color tones, soft lighting, inviting atmosphere, comfortable, homey feeling",
        "professional corporate": "corporate professional aesthetic, clean lines, business appropriate, trustworthy, polished",
        "playful and fun": "playful colorful design, fun elements, cheerful mood, engaging, lively",
        "elegant luxury": "luxurious elegant design, sophisticated, premium quality, high-end aesthetic, refined",
    }
    
    style_description = style_mappings.get(style, style) if style else "modern professional commercial"
    
    # Build comprehensive prompt with SDXL-optimized structure
    # Quality boosters first, then context, then specifics
    prompt_parts = [
        # Quality boosters (what SDXL responds well to)
        "masterpiece, best quality, highly detailed,",
        "professional commercial photography,",
        "4K, sharp focus, studio lighting,",
        
        # Main subject/context
        f"marketing advertisement for {brand_name},",
        user_prompt + ",",
        
        # Style
        f"aesthetic style: {style_description},",
        
        # Brand elements
        color_string,
        product_string,
        
        # Additional quality descriptors
        "clean composition, well-balanced layout,",
        "suitable for social media marketing,",
        "trending on artstation, award-winning design"
    ]
    
    # Filter empty parts and join
    prompt = " ".join([p for p in prompt_parts if p])
    
    # Note: We don't add "no text" because we'll overlay text ourselves
    # The image should be clean for text overlay
    prompt += " No text, no watermarks, no logos, no words, no letters."
    
    return prompt


async def call_sdxl_api(prompt: str, token: str, custom_negative_prompt: Optional[str] = None) -> bytes:
    """
    Call Hugging Face SDXL API for image generation.
    
    Args:
        prompt: The generation prompt
        token: Hugging Face token
        custom_negative_prompt: Optional custom negative prompt from constraint system
        
    Returns:
        Generated image bytes
    """
    # Updated to use new router endpoint (api-inference.huggingface.co is deprecated)
    API_URL = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Base negative prompt to avoid common issues
    base_negative = (
        "text, watermark, logo, words, letters, numbers, signature, "
        "low quality, blurry, distorted, deformed, ugly, bad anatomy, "
        "amateur, poorly drawn, sketch, cartoon, anime, "
        "oversaturated, underexposed, overexposed"
    )
    
    # Combine with custom negative prompt if provided
    if custom_negative_prompt:
        negative_prompt = f"{custom_negative_prompt}, {base_negative}"
    else:
        negative_prompt = base_negative
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": 1024,
            "height": 1024,
            "num_inference_steps": 40,  # More steps for better quality
            "guidance_scale": 8.0,  # Slightly higher for more prompt adherence
            "negative_prompt": negative_prompt
        }
    }
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(API_URL, headers=headers, json=payload)
        
        # Handle model loading
        if response.status_code == 503:
            import asyncio
            await asyncio.sleep(30)
            response = await client.post(API_URL, headers=headers, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"SDXL API error: {response.status_code} - {response.text}")
        
        return response.content
