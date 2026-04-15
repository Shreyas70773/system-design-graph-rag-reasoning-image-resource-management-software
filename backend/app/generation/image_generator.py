"""
Marketing Image Generation Module
Generates brand-aligned marketing images using diffusion-first providers.
"""
import httpx
import base64
import random
from typing import Dict, Any, Optional, List

from app.config import get_settings
from app.scraping.color_extractor import extract_colors_from_image
from app.services.comfy_client import ComfyClient


def _aspect_ratio_to_dimensions(aspect_ratio: str) -> tuple[int, int]:
    """Map aspect ratio string to practical generation dimensions."""
    ratio = str(aspect_ratio or "1:1").strip()
    mapping = {
        "1:1": (1024, 1024),
        "16:9": (1216, 704),
        "9:16": (704, 1216),
        "4:3": (1152, 896),
        "3:4": (896, 1152),
        "3:2": (1152, 768),
        "2:3": (768, 1152),
    }
    return mapping.get(ratio, (1024, 1024))


def _pick_flux_checkpoint(checkpoints: List[str]) -> Optional[str]:
    """Pick the best FLUX checkpoint candidate from Comfy checkpoint list."""
    if not checkpoints:
        return None

    normalized = [str(name) for name in checkpoints if name]
    flux_candidates = [name for name in normalized if "flux" in name.lower()]
    if not flux_candidates:
        return None

    # Prefer FLUX.1-dev naming variants first.
    preference_order = ["flux.1-dev", "flux1-dev", "flux-dev", "dev", "flux"]
    for needle in preference_order:
        for candidate in flux_candidates:
            if needle in candidate.lower():
                return candidate

    return flux_candidates[0]


def _build_comfy_checkpoint_workflow(
    prompt: str,
    negative_prompt: str,
    checkpoint_name: str,
    aspect_ratio: str,
    steps: int = 30,
    cfg: float = 6.0,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a basic Comfy workflow around CheckpointLoaderSimple."""
    width, height = _aspect_ratio_to_dimensions(aspect_ratio)
    safe_steps = max(8, min(int(steps), 60))
    safe_cfg = max(1.0, min(float(cfg), 12.0))
    safe_seed = int(seed if seed is not None else random.randint(1, 2_147_483_647))

    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint_name},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt,
                "clip": ["1", 1],
            },
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative_prompt,
                "clip": ["1", 1],
            },
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1,
            },
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "seed": safe_seed,
                "steps": safe_steps,
                "cfg": safe_cfg,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["5", 0],
                "vae": ["1", 2],
            },
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "marketing_flux",
                "images": ["6", 0],
            },
        },
    }


async def _try_comfy_flux_generation(
    full_prompt: str,
    negative_prompt: str,
    aspect_ratio: str,
) -> Dict[str, Any]:
    """Try local Comfy first, preferring FLUX.1-dev checkpoints if present."""
    comfy_client = ComfyClient()
    health = await comfy_client.health(auto_start=True)
    if not health.get("ok"):
        raise RuntimeError(f"ComfyUI unavailable: {health.get('error', 'unknown error')}")

    checkpoints_result = await comfy_client.list_models("checkpoints", auto_start=False)
    if not checkpoints_result.get("ok"):
        raise RuntimeError(
            f"ComfyUI checkpoint listing failed: {checkpoints_result.get('error', 'unknown error')}"
        )

    checkpoints = checkpoints_result.get("models") or []
    selected_checkpoint = _pick_flux_checkpoint(checkpoints)
    if not selected_checkpoint:
        raise RuntimeError(
            "No FLUX checkpoint found in ComfyUI models/checkpoints. "
            "Install FLUX.1-dev (or another FLUX checkpoint) and retry."
        )

    workflow = _build_comfy_checkpoint_workflow(
        prompt=full_prompt,
        negative_prompt=negative_prompt,
        checkpoint_name=selected_checkpoint,
        aspect_ratio=aspect_ratio,
    )

    submitted = await comfy_client.submit_workflow(workflow, client_id="marketing-generate")
    prompt_id = submitted.get("prompt_id")
    if not prompt_id:
        raise RuntimeError("ComfyUI submission returned no prompt_id")

    completion = await comfy_client.wait_for_completion(prompt_id, max_polls=180, poll_interval_seconds=1.5)
    if not completion.get("completed"):
        raise RuntimeError(f"ComfyUI did not complete prompt {prompt_id}: {completion.get('error', 'unknown error')}")

    image_urls = comfy_client.extract_image_urls(completion.get("history", {}))
    if not image_urls:
        raise RuntimeError(f"ComfyUI completed prompt {prompt_id} but returned no images")

    image_url = image_urls[0]
    async with httpx.AsyncClient(timeout=60.0) as client:
        image_response = await client.get(image_url)
        image_response.raise_for_status()
        image_bytes = image_response.content
        content_type = (image_response.headers.get("content-type") or "image/png").split(";")[0].strip()

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    return {
        "url": f"data:{content_type};base64,{image_base64}",
        "provider": "comfyui",
        "model_used": selected_checkpoint,
    }


async def generate_marketing_image(
    brand_context: Dict[str, Any],
    prompt: str,
    style: Optional[str] = None,
    negative_prompt: Optional[str] = None,
    aspect_ratio: str = "1:1",
) -> Dict[str, Any]:
    """
    Generate a marketing image aligned with brand guidelines.
    
    Primary path:
    1. Local ComfyUI with FLUX checkpoint preference (FLUX.1-dev if present)

    Fallback path:
    2. Hugging Face Inference API (SDXL)
    
    Args:
        brand_context: Full brand context from Neo4j
        prompt: User's content request
        style: Optional style override
        negative_prompt: Optional custom negative prompt from constraint system
        
    Returns:
        Dict with url, colors_extracted
    """
    # Build the image generation prompt
    full_prompt = build_image_prompt(brand_context, prompt, style)
    
    # Build robust negative prompt once (used for both Comfy and SDXL fallback).
    base_negative = (
        "text, watermark, logo, words, letters, numbers, signature, "
        "low quality, blurry, distorted, deformed, ugly, bad anatomy, "
        "amateur, poorly drawn, sketch, cartoon, anime, "
        "oversaturated, underexposed, overexposed"
    )
    effective_negative = f"{negative_prompt}, {base_negative}" if negative_prompt else base_negative

    result: Dict[str, Any]
    comfy_error: Optional[Exception] = None

    # Primary: local ComfyUI (FLUX-first model selection).
    try:
        result = await _try_comfy_flux_generation(
            full_prompt=full_prompt,
            negative_prompt=effective_negative,
            aspect_ratio=aspect_ratio,
        )
    except Exception as exc:
        comfy_error = exc
        # Fallback: Hugging Face SDXL (no local VRAM cost).
        settings = get_settings()
        if not settings.huggingface_token:
            raise Exception(
                f"ComfyUI FLUX generation failed: {exc}. "
                "HuggingFace fallback is unavailable because HUGGINGFACE_TOKEN is not configured."
            )

        try:
            image_bytes = await call_sdxl_api(
                prompt=full_prompt,
                token=settings.huggingface_token,
                custom_negative_prompt=negative_prompt,
                aspect_ratio=aspect_ratio,
            )
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            result = {
                "url": f"data:image/png;base64,{image_base64}",
                "provider": "huggingface",
                "model_used": "stabilityai/stable-diffusion-xl-base-1.0",
            }
        except Exception as sdxl_error:
            raise Exception(
                f"ComfyUI FLUX failed: {exc}. Hugging Face SDXL fallback failed: {sdxl_error}"
            )
    
    # Extract colors from generated image for validation
    colors_extracted = []
    image_url = result.get("url")
    if image_url:
        try:
            # Only extract if we have base64 data
            if image_url.startswith("data:image"):
                base64_data = image_url.split(",")[1]
                image_bytes = base64.b64decode(base64_data)
                colors = extract_colors_from_image(image_bytes, color_count=5)
                colors_extracted = [c['hex'] for c in colors]
        except:
            pass
    
    return {
        "url": image_url,
        "colors_extracted": colors_extracted,
        "prompt_used": full_prompt,
        "provider": result.get("provider"),
        "model_used": result.get("model_used"),
        "fallback_used": comfy_error is not None,
        "comfy_error": str(comfy_error) if comfy_error is not None else None,
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


async def call_sdxl_api(
    prompt: str,
    token: str,
    custom_negative_prompt: Optional[str] = None,
    aspect_ratio: str = "1:1",
) -> bytes:
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
    
    width, height = _aspect_ratio_to_dimensions(aspect_ratio)

    payload = {
        "inputs": prompt,
        "parameters": {
            "width": width,
            "height": height,
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
