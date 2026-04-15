"""
Logo Enhancement Module
Generates AI logos using Hugging Face SDXL.
"""
import httpx
from typing import Dict, Any, Optional
import base64
from io import BytesIO

from app.config import get_settings


async def generate_ai_logo(
    brand: Dict[str, Any],
    style: str = "modern minimalist",
    include_text: bool = True
) -> Dict[str, Any]:
    """
    Generate an AI logo for a brand using Hugging Face SDXL.
    
    Args:
        brand: Brand data including name, colors, industry
        style: Logo style (e.g., "modern minimalist", "vintage", "corporate")
        include_text: Whether to include company name in the logo
        
    Returns:
        Dict with logo_url, prompt_used
    """
    settings = get_settings()
    
    if not settings.huggingface_token:
        raise Exception("Hugging Face token not configured")
    
    # Build the prompt
    prompt = build_logo_prompt(brand, style, include_text)
    
    # Call Hugging Face API
    image_bytes = await call_huggingface_sdxl(prompt, settings.huggingface_token)
    
    # For now, return base64 encoded image
    # In production, this would upload to Cloudflare R2 and return URL
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    data_url = f"data:image/png;base64,{image_base64}"
    
    return {
        "logo_url": data_url,
        "prompt_used": prompt
    }


def build_logo_prompt(
    brand: Dict[str, Any],
    style: str,
    include_text: bool
) -> str:
    """
    Build a prompt for logo generation based on brand context.
    
    Args:
        brand: Brand data
        style: Desired logo style
        include_text: Include company name in logo
        
    Returns:
        Prompt string for SDXL
    """
    company_name = brand.get('name', 'Company')
    industry = brand.get('industry', '')
    
    # Get brand colors for the prompt
    colors = brand.get('colors', [])
    color_string = ""
    if colors:
        color_names = [c.get('name', c.get('hex', '')) for c in colors[:3]]
        color_string = f", using {', '.join(color_names)} colors"
    
    # Build the prompt
    prompt_parts = [
        f"Professional logo design for {company_name}",
        f"{style} style",
        "clean vector graphics",
        "high quality",
        "centered composition",
        "white or transparent background",
        "suitable for business use"
    ]
    
    if industry:
        prompt_parts.insert(1, f"in the {industry} industry")
    
    if color_string:
        prompt_parts.append(color_string)
    
    if include_text:
        prompt_parts.append(f"with the text '{company_name}'")
    else:
        prompt_parts.append("icon only, no text")
    
    return ", ".join(prompt_parts)


async def call_huggingface_sdxl(prompt: str, token: str) -> bytes:
    """
    Call Hugging Face Inference API for SDXL image generation.
    
    Args:
        prompt: The image generation prompt
        token: Hugging Face API token
        
    Returns:
        Generated image as bytes
    """
    # Using SDXL model for high quality images
    API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": 512,
            "height": 512,
            "num_inference_steps": 30,
            "guidance_scale": 7.5
        }
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(API_URL, headers=headers, json=payload)
        
        if response.status_code == 503:
            # Model is loading, wait and retry
            import asyncio
            await asyncio.sleep(20)
            response = await client.post(API_URL, headers=headers, json=payload)
        
        if response.status_code != 200:
            error_detail = response.text
            raise Exception(f"Hugging Face API error: {response.status_code} - {error_detail}")
        
        return response.content
