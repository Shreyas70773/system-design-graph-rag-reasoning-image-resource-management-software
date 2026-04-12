"""
Abstracted Image Generation Interface
=====================================
Allows swapping between different image generation backends:
- fal.ai (Flux.1 Kontext, Flux.1 Dev)
- Replicate (Flux, SDXL, PuLID)
- HuggingFace (fallback)

The interface accepts graph-derived conditioning parameters and
translates them to model-specific inputs.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import asyncio
import httpx
import os
import json
import time
from datetime import datetime


class ModelProvider(Enum):
    FAL_AI = "fal.ai"
    REPLICATE = "replicate"
    HUGGINGFACE = "huggingface"


class ModelType(Enum):
    FLUX_KONTEXT = "flux-kontext"
    FLUX_DEV = "flux-dev"
    FLUX_SCHNELL = "flux-schnell"
    FLUX_PRO = "flux-pro"
    SDXL = "sdxl"
    SDXL_LIGHTNING = "sdxl-lightning"


@dataclass
class BrandCondition:
    """Conditioning parameters derived from Brand DNA graph"""
    # Color conditioning
    primary_colors: List[str] = field(default_factory=list)  # Hex codes
    color_weights: Dict[str, float] = field(default_factory=dict)
    
    # Style conditioning
    style_keywords: List[str] = field(default_factory=list)
    negative_keywords: List[str] = field(default_factory=list)
    style_strength: float = 0.8
    
    # Composition conditioning
    layout: str = "centered"
    text_density: str = "moderate"
    text_position: str = "bottom"
    overlay_opacity: float = 0.0
    aspect_ratio: str = "1:1"
    
    # Product reference (for IP-Adapter)
    product_image_url: Optional[str] = None
    product_embedding: Optional[List[float]] = None
    product_strength: float = 0.6
    
    # Character reference (for PuLID)
    face_image_url: Optional[str] = None
    face_embedding: Optional[List[float]] = None
    face_strength: float = 0.7
    
    # Learned preferences
    learned_modifiers: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationRequest:
    """Full generation request with all parameters"""
    prompt: str
    brand_id: str
    brand_condition: BrandCondition
    
    # Generation settings
    num_images: int = 1
    guidance_scale: float = 7.5
    num_inference_steps: int = 30
    seed: Optional[int] = None
    
    # Optional text overlay
    headline: Optional[str] = None
    body_copy: Optional[str] = None
    
    # Metadata
    request_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GenerationResult:
    """Result from image generation"""
    success: bool
    image_url: Optional[str] = None
    image_urls: List[str] = field(default_factory=list)
    
    # Generated text (if LLM enhanced)
    headline: Optional[str] = None
    body_copy: Optional[str] = None
    compiled_prompt: Optional[str] = None
    
    # Metadata
    model_used: str = ""
    provider: str = ""
    generation_time_ms: float = 0
    cost_usd: float = 0
    
    # For tracking
    generation_id: Optional[str] = None
    conditioners_used: List[str] = field(default_factory=list)
    
    # Errors
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "image_url": self.image_url,
            "image_urls": self.image_urls,
            "headline": self.headline,
            "body_copy": self.body_copy,
            "compiled_prompt": self.compiled_prompt,
            "model_used": self.model_used,
            "provider": self.provider,
            "generation_time_ms": self.generation_time_ms,
            "cost_usd": self.cost_usd,
            "generation_id": self.generation_id,
            "conditioners_used": self.conditioners_used,
            "error_message": self.error_message
        }


class ImageGenerator(ABC):
    """Abstract base class for image generation backends"""
    
    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate image(s) based on request"""
        pass
    
    @abstractmethod
    async def generate_with_character(
        self, 
        request: GenerationRequest,
        character_image_url: str,
        strength: float = 0.7
    ) -> GenerationResult:
        """Generate with character consistency (PuLID/InstantID)"""
        pass
    
    @abstractmethod
    async def generate_with_product(
        self,
        request: GenerationRequest,
        product_image_url: str,
        strength: float = 0.6
    ) -> GenerationResult:
        """Generate with product reference (IP-Adapter)"""
        pass
    
    @abstractmethod
    def estimate_cost(self, request: GenerationRequest) -> float:
        """Estimate cost for this generation"""
        pass
    
    def compile_prompt(self, request: GenerationRequest) -> str:
        """Compile final prompt with brand conditioning"""
        parts = [request.prompt]
        cond = request.brand_condition
        
        # Add style keywords
        if cond.style_keywords:
            parts.append(f"Style: {', '.join(cond.style_keywords)}")
        
        # Add color guidance
        if cond.primary_colors:
            color_desc = ', '.join(cond.primary_colors[:3])
            parts.append(f"Color palette: {color_desc}")
        
        # Add composition guidance
        if cond.layout:
            parts.append(f"Layout: {cond.layout}")
        
        # NO TEXT in image - text will be composited via PIL after generation
        parts.append("photorealistic, no text, no words, no letters, no writing, no captions")
        
        if cond.overlay_opacity > 0:
            parts.append(f"Dark overlay opacity: {cond.overlay_opacity}")
        
        # Add learned modifiers
        for key, value in cond.learned_modifiers.items():
            parts.append(f"{key}: {value}")
        
        # Add quality boosters
        parts.append("high quality, professional photography, sharp focus, detailed, 8k resolution")
        
        compiled = ". ".join(parts)
        return compiled
    
    def get_negative_prompt(self, request: GenerationRequest) -> str:
        """Build negative prompt to avoid unwanted elements"""
        negative = []
        cond = request.brand_condition
        
        if cond.negative_keywords:
            negative.extend(cond.negative_keywords)
        
        # Standard quality negative prompts (avoid "watermark" which triggers content policy)
        negative.extend([
            "blurry", "low quality", "distorted", 
            "jpeg artifacts", "ugly", "deformed", "disfigured",
            "mutation", "extra limbs", "bad anatomy"
        ])
        
        # Always suppress text generation - text will be composited via PIL
        negative.extend([
            "text", "words", "letters", "writing", "caption", 
            "title", "subtitle", "label", "gibberish text", 
            "random letters", "inscriptions"
        ])
        
        return ", ".join(negative)


class FalAIGenerator(ImageGenerator):
    """fal.ai implementation - fastest, supports Flux.1 Kontext"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FAL_KEY")
        self.base_url = "https://fal.run"
        self.provider = ModelProvider.FAL_AI.value
        
        # Model endpoints
        self.models = {
            ModelType.FLUX_KONTEXT: "fal-ai/flux-kontext",
            ModelType.FLUX_DEV: "fal-ai/flux/dev",
            ModelType.FLUX_SCHNELL: "fal-ai/flux/schnell",
            ModelType.FLUX_PRO: "fal-ai/flux-pro",
        }
        
        # Pricing per image (approximate)
        self.pricing = {
            ModelType.FLUX_KONTEXT: 0.04,
            ModelType.FLUX_DEV: 0.025,
            ModelType.FLUX_SCHNELL: 0.003,
            ModelType.FLUX_PRO: 0.05,
        }
    
    async def generate(
        self, 
        request: GenerationRequest,
        model: ModelType = ModelType.FLUX_DEV
    ) -> GenerationResult:
        start_time = time.time()
        
        try:
            compiled_prompt = self.compile_prompt(request)
            negative_prompt = self.get_negative_prompt(request)
            
            # Prepare aspect ratio
            aspect_map = {
                "1:1": "square",
                "16:9": "landscape_16_9",
                "9:16": "portrait_16_9",
                "4:3": "landscape_4_3",
                "3:4": "portrait_4_3"
            }
            image_size = aspect_map.get(
                request.brand_condition.aspect_ratio, 
                "square"
            )
            
            # Build request payload
            payload = {
                "prompt": compiled_prompt,
                "negative_prompt": negative_prompt,  # Add negative prompt!
                "image_size": image_size,
                "num_inference_steps": request.num_inference_steps,
                "guidance_scale": request.guidance_scale,
                "num_images": request.num_images,
                "enable_safety_checker": True
            }
            
            if request.seed:
                payload["seed"] = request.seed
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/{self.models[model]}",
                    headers={
                        "Authorization": f"Key {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                
                if response.status_code != 200:
                    return GenerationResult(
                        success=False,
                        error_message=f"fal.ai error: {response.text}",
                        model_used=model.value,
                        provider=self.provider
                    )
                
                result = response.json()
            
            generation_time = (time.time() - start_time) * 1000
            
            # Extract image URLs
            images = result.get("images", [])
            image_urls = [img.get("url") for img in images if img.get("url")]
            
            return GenerationResult(
                success=True,
                image_url=image_urls[0] if image_urls else None,
                image_urls=image_urls,
                compiled_prompt=compiled_prompt,
                model_used=model.value,
                provider=self.provider,
                generation_time_ms=generation_time,
                cost_usd=self.pricing.get(model, 0.03) * request.num_images,
                conditioners_used=["text"]
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error_message=str(e),
                model_used=model.value,
                provider=self.provider,
                generation_time_ms=(time.time() - start_time) * 1000
            )
    
    async def generate_with_character(
        self,
        request: GenerationRequest,
        character_image_url: str,
        strength: float = 0.7
    ) -> GenerationResult:
        """Generate with PuLID face consistency via fal.ai"""
        start_time = time.time()
        
        try:
            compiled_prompt = self.compile_prompt(request)
            
            # PuLID endpoint on fal.ai
            pulid_endpoint = "fal-ai/pulid"
            
            payload = {
                "prompt": compiled_prompt,
                "reference_images": [character_image_url],
                "id_strength": strength,
                "num_inference_steps": request.num_inference_steps,
                "guidance_scale": request.guidance_scale,
            }
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{self.base_url}/{pulid_endpoint}",
                    headers={
                        "Authorization": f"Key {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                
                if response.status_code != 200:
                    return GenerationResult(
                        success=False,
                        error_message=f"PuLID error: {response.text}",
                        model_used="pulid",
                        provider=self.provider
                    )
                
                result = response.json()
            
            generation_time = (time.time() - start_time) * 1000
            images = result.get("images", [])
            image_urls = [img.get("url") for img in images if img.get("url")]
            
            return GenerationResult(
                success=True,
                image_url=image_urls[0] if image_urls else None,
                image_urls=image_urls,
                compiled_prompt=compiled_prompt,
                model_used="pulid",
                provider=self.provider,
                generation_time_ms=generation_time,
                cost_usd=0.06,  # PuLID is more expensive
                conditioners_used=["text", "pulid_face"]
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error_message=str(e),
                model_used="pulid",
                provider=self.provider
            )
    
    async def generate_with_product(
        self,
        request: GenerationRequest,
        product_image_url: str,
        strength: float = 0.6
    ) -> GenerationResult:
        """Generate with IP-Adapter product reference"""
        start_time = time.time()
        
        try:
            compiled_prompt = self.compile_prompt(request)
            
            # Flux Kontext supports multi-image natively
            payload = {
                "prompt": compiled_prompt,
                "image_url": product_image_url,  # Product as reference
                "strength": strength,
                "num_inference_steps": request.num_inference_steps,
                "guidance_scale": request.guidance_scale,
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/{self.models[ModelType.FLUX_KONTEXT]}",
                    headers={
                        "Authorization": f"Key {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                
                if response.status_code != 200:
                    return GenerationResult(
                        success=False,
                        error_message=f"Flux Kontext error: {response.text}",
                        model_used="flux-kontext",
                        provider=self.provider
                    )
                
                result = response.json()
            
            generation_time = (time.time() - start_time) * 1000
            images = result.get("images", [])
            image_urls = [img.get("url") for img in images if img.get("url")]
            
            return GenerationResult(
                success=True,
                image_url=image_urls[0] if image_urls else None,
                image_urls=image_urls,
                compiled_prompt=compiled_prompt,
                model_used="flux-kontext",
                provider=self.provider,
                generation_time_ms=generation_time,
                cost_usd=0.04,
                conditioners_used=["text", "product_reference"]
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error_message=str(e),
                model_used="flux-kontext",
                provider=self.provider
            )
    
    def estimate_cost(self, request: GenerationRequest) -> float:
        base_cost = 0.025  # Flux Dev base
        
        if request.brand_condition.face_image_url:
            base_cost += 0.03  # PuLID surcharge
        
        if request.brand_condition.product_image_url:
            base_cost += 0.015  # IP-Adapter surcharge
        
        return base_cost * request.num_images


class ReplicateGenerator(ImageGenerator):
    """Replicate implementation - good free tier, many models"""
    
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv("REPLICATE_API_TOKEN")
        self.base_url = "https://api.replicate.com/v1"
        self.provider = ModelProvider.REPLICATE.value
        
        # Model versions (these change, check replicate.com)
        self.models = {
            ModelType.FLUX_DEV: "black-forest-labs/flux-dev",
            ModelType.FLUX_SCHNELL: "black-forest-labs/flux-schnell",
            ModelType.SDXL: "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            ModelType.SDXL_LIGHTNING: "bytedance/sdxl-lightning-4step:727e49a643e999d602a896c774a0658ffefea21465756a6ce24b7ea4165ber0a"
        }
        
        self.pricing = {
            ModelType.FLUX_DEV: 0.025,
            ModelType.FLUX_SCHNELL: 0.003,
            ModelType.SDXL: 0.02,
            ModelType.SDXL_LIGHTNING: 0.008,
        }
    
    async def _run_prediction(self, model: str, input_data: dict) -> dict:
        """Run a prediction on Replicate and wait for result"""
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Create prediction
            response = await client.post(
                f"{self.base_url}/predictions",
                headers={
                    "Authorization": f"Token {self.api_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "version": model if ":" in model else None,
                    "model": model if ":" not in model else None,
                    "input": input_data
                }
            )
            
            if response.status_code != 201:
                raise Exception(f"Failed to create prediction: {response.text}")
            
            prediction = response.json()
            prediction_id = prediction["id"]
            
            # Poll for completion
            while True:
                response = await client.get(
                    f"{self.base_url}/predictions/{prediction_id}",
                    headers={"Authorization": f"Token {self.api_token}"}
                )
                prediction = response.json()
                
                if prediction["status"] == "succeeded":
                    return prediction
                elif prediction["status"] == "failed":
                    raise Exception(f"Prediction failed: {prediction.get('error')}")
                
                await asyncio.sleep(1)
    
    async def generate(
        self,
        request: GenerationRequest,
        model: ModelType = ModelType.FLUX_SCHNELL
    ) -> GenerationResult:
        start_time = time.time()
        
        try:
            compiled_prompt = self.compile_prompt(request)
            negative_prompt = self.get_negative_prompt(request)
            
            # Build input based on model
            input_data = {
                "prompt": compiled_prompt,
                "num_outputs": request.num_images,
                "guidance_scale": request.guidance_scale,
            }
            
            if model in [ModelType.FLUX_DEV, ModelType.FLUX_SCHNELL]:
                input_data["num_inference_steps"] = request.num_inference_steps
                input_data["go_fast"] = True
                # Flux models on Replicate also support negative prompt
                input_data["negative_prompt"] = negative_prompt
            else:  # SDXL
                input_data["num_inference_steps"] = request.num_inference_steps
                input_data["width"] = 1024
                input_data["height"] = 1024
                input_data["negative_prompt"] = negative_prompt
            
            if request.seed:
                input_data["seed"] = request.seed
            
            result = await self._run_prediction(
                self.models[model],
                input_data
            )
            
            generation_time = (time.time() - start_time) * 1000
            
            # Extract URLs
            output = result.get("output", [])
            if isinstance(output, str):
                output = [output]
            
            return GenerationResult(
                success=True,
                image_url=output[0] if output else None,
                image_urls=output,
                compiled_prompt=compiled_prompt,
                model_used=model.value,
                provider=self.provider,
                generation_time_ms=generation_time,
                cost_usd=self.pricing.get(model, 0.02) * request.num_images,
                conditioners_used=["text"]
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error_message=str(e),
                model_used=model.value,
                provider=self.provider,
                generation_time_ms=(time.time() - start_time) * 1000
            )
    
    async def generate_with_character(
        self,
        request: GenerationRequest,
        character_image_url: str,
        strength: float = 0.7
    ) -> GenerationResult:
        """Generate with InstantID on Replicate"""
        start_time = time.time()
        
        try:
            compiled_prompt = self.compile_prompt(request)
            
            # InstantID model on Replicate
            instantid_model = "zsxkib/instant-id:6af8583c541261472e92155d87bba80d5ad98b8e0f57bbef40ef8c6a01f03f90"
            
            input_data = {
                "prompt": compiled_prompt,
                "image": character_image_url,
                "ip_adapter_scale": strength,
                "controlnet_conditioning_scale": 0.8,
                "num_inference_steps": request.num_inference_steps,
            }
            
            result = await self._run_prediction(instantid_model, input_data)
            
            generation_time = (time.time() - start_time) * 1000
            output = result.get("output", [])
            if isinstance(output, str):
                output = [output]
            
            return GenerationResult(
                success=True,
                image_url=output[0] if output else None,
                image_urls=output,
                compiled_prompt=compiled_prompt,
                model_used="instantid",
                provider=self.provider,
                generation_time_ms=generation_time,
                cost_usd=0.05,
                conditioners_used=["text", "instantid_face"]
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error_message=str(e),
                model_used="instantid",
                provider=self.provider
            )
    
    async def generate_with_product(
        self,
        request: GenerationRequest,
        product_image_url: str,
        strength: float = 0.6
    ) -> GenerationResult:
        """Generate with IP-Adapter on Replicate"""
        start_time = time.time()
        
        try:
            compiled_prompt = self.compile_prompt(request)
            
            # IP-Adapter SDXL on Replicate
            ip_adapter_model = "lucataco/ip-adapter-sdxl:8bf5c083-7dbe-45f6-a42f-b0c5e5d9a4b0"
            
            input_data = {
                "prompt": compiled_prompt,
                "image": product_image_url,
                "scale": strength,
                "num_inference_steps": request.num_inference_steps,
            }
            
            result = await self._run_prediction(ip_adapter_model, input_data)
            
            generation_time = (time.time() - start_time) * 1000
            output = result.get("output", [])
            if isinstance(output, str):
                output = [output]
            
            return GenerationResult(
                success=True,
                image_url=output[0] if output else None,
                image_urls=output,
                compiled_prompt=compiled_prompt,
                model_used="ip-adapter-sdxl",
                provider=self.provider,
                generation_time_ms=generation_time,
                cost_usd=0.03,
                conditioners_used=["text", "ip_adapter_product"]
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error_message=str(e),
                model_used="ip-adapter-sdxl",
                provider=self.provider
            )
    
    async def generate_with_product_and_character(
        self,
        request: GenerationRequest,
        product_image_url: str,
        character_image_url: str,
        product_strength: float = 0.5,
        character_strength: float = 0.6
    ) -> GenerationResult:
        """Generate with both product and character reference"""
        start_time = time.time()
        
        try:
            compiled_prompt = self.compile_prompt(request)
            negative_prompt = self.get_negative_prompt(request)
            
            # Use IP-Adapter with multiple images
            # Many models support this via multiple image inputs
            ip_adapter_model = "zsxkib/ip-adapter-sdxl:f85b5f96461bf42aba98afe4e3d9c9ed38fee45a7c0e4c96fa42ee3bb39dc2b4"
            
            input_data = {
                "prompt": compiled_prompt,
                "negative_prompt": negative_prompt,
                "image": product_image_url,  # Product reference
                "face_image": character_image_url,  # Character reference
                "ip_adapter_scale": product_strength,
                "face_weight": character_strength,
                "num_inference_steps": request.num_inference_steps,
                "guidance_scale": request.guidance_scale,
            }
            
            result = await self._run_prediction(ip_adapter_model, input_data)
            
            generation_time = (time.time() - start_time) * 1000
            output = result.get("output", [])
            if isinstance(output, str):
                output = [output]
            
            return GenerationResult(
                success=True,
                image_url=output[0] if output else None,
                image_urls=output,
                compiled_prompt=compiled_prompt,
                model_used="ip-adapter-combo",
                provider=self.provider,
                generation_time_ms=generation_time,
                cost_usd=0.05,  # More expensive for combined
                conditioners_used=["text", "ip_adapter_product", "face_reference"]
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error_message=str(e),
                model_used="ip-adapter-combo",
                provider=self.provider
            )
    
    def estimate_cost(self, request: GenerationRequest) -> float:
        base_cost = 0.02
        
        if request.brand_condition.face_image_url:
            base_cost += 0.03
        
        if request.brand_condition.product_image_url:
            base_cost += 0.01
        
        return base_cost * request.num_images


class GeminiGenerator(ImageGenerator):
    """
    Google Gemini Nano Banana Implementation
    =========================================
    Uses Gemini's native image generation for high-quality outputs.
    
    ARCHITECTURE NOTE FOR CAPSTONE:
    --------------------------------
    This is a PROMPT-LEVEL implementation using Gemini's API.
    For production with TRUE diffusion-level control, we would:
    
    1. SELF-HOSTED APPROACH (ComfyUI):
       - Run ComfyUI with custom workflows
       - Inject LoRAs trained on brand assets at UNet level
       - Use IP-Adapter for product conditioning at cross-attention
       - Use ControlNet for composition (pose, depth, layout)
       - PuLID/InstantID for face embedding at attention layers
       - Direct latent manipulation for color palette enforcement
    
    2. FINE-TUNED APPROACH:
       - Train brand-specific LoRAs on logo, products, style
       - Merge multiple LoRAs at inference time
       - Use textual inversion for brand concepts
    
    3. EMBEDDING-LEVEL CONTROL:
       - Pre-compute product embeddings via CLIP/DINO
       - Inject embeddings directly into cross-attention
       - Control color via latent space manipulation
    
    Current implementation demonstrates the RETRIEVAL and PLANNING
    stages of GraphRAG - the generation is delegated to Gemini's API.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.provider = "gemini"
        
        # Model options - use actual image generation models
        self.models = {
            "flash": "gemini-2.5-flash-image",           # Nano Banana (fast image gen)
            "pro": "nano-banana-pro-preview",            # Nano Banana Pro (higher quality)
            "experimental": "gemini-2.0-flash-exp-image-generation",  # Experimental
        }
        
        # Pricing (approximate)
        self.pricing = {
            "flash": 0.002,  # Very cheap
            "pro": 0.01,
            "experimental": 0.005,
        }
    
    async def generate(
        self, 
        request: GenerationRequest,
        model: str = "flash"
    ) -> GenerationResult:
        """Generate image using Gemini's native image generation"""
        import base64
        start_time = time.time()
        
        try:
            compiled_prompt = self.compile_prompt(request)
            
            # Build the Gemini request
            # Gemini uses a different API structure
            payload = {
                "contents": [{
                    "parts": [{
                        "text": compiled_prompt
                    }]
                }],
                "generationConfig": {
                    "responseModalities": ["TEXT", "IMAGE"],
                    "temperature": 1.0,
                }
            }
            
            model_name = self.models.get(model, self.models["flash"])
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json=payload
                )
                
                if response.status_code != 200:
                    return GenerationResult(
                        success=False,
                        error_message=f"Gemini error ({response.status_code}): {response.text}",
                        model_used=model_name,
                        provider=self.provider
                    )
                
                result = response.json()
            
            generation_time = (time.time() - start_time) * 1000
            
            # Parse Gemini response - look for image data
            image_url = None
            image_data = None
            text_response = None
            
            candidates = result.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                
                for part in parts:
                    if "text" in part:
                        text_response = part["text"]
                    elif "inlineData" in part:
                        # Base64 image data
                        image_data = part["inlineData"].get("data")
                        mime_type = part["inlineData"].get("mimeType", "image/png")
                        if image_data:
                            # Convert to data URL for frontend display
                            image_url = f"data:{mime_type};base64,{image_data}"
            
            if not image_url:
                return GenerationResult(
                    success=False,
                    error_message=f"No image generated. Response: {text_response or 'No response'}",
                    model_used=model_name,
                    provider=self.provider,
                    generation_time_ms=generation_time
                )
            
            return GenerationResult(
                success=True,
                image_url=image_url,
                image_urls=[image_url] if image_url else [],
                compiled_prompt=compiled_prompt,
                model_used=model_name,
                provider=self.provider,
                generation_time_ms=generation_time,
                cost_usd=self.pricing.get(model, 0.002),
                conditioners_used=["text", "gemini_native"]
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error_message=str(e),
                model_used=model,
                provider=self.provider,
                generation_time_ms=(time.time() - start_time) * 1000
            )
    
    async def generate_with_character(
        self,
        request: GenerationRequest,
        character_image_url: str,
        strength: float = 0.7
    ) -> GenerationResult:
        """
        Generate with character reference using Gemini's image understanding.
        
        ARCHITECTURE NOTE:
        For true face consistency, production would use:
        - PuLID: Injects face embedding at cross-attention layers
        - InstantID: Similar but with ControlNet for pose
        - IP-Adapter Face: Product-level face conditioning
        
        Current: We download the reference and ask Gemini to match the face.
        """
        start_time = time.time()
        
        try:
            # Download reference image
            async with httpx.AsyncClient() as client:
                img_response = await client.get(character_image_url)
                if img_response.status_code == 200:
                    import base64
                    image_base64 = base64.b64encode(img_response.content).decode()
                else:
                    # Fallback to text-only
                    return await self.generate(request)
            
            compiled_prompt = self.compile_prompt(request)
            enhanced_prompt = f"""Generate an image that includes a person who looks EXACTLY like the person in the reference image I'm providing.

Reference person characteristics should be preserved: face shape, features, skin tone, general appearance.

Scene to generate: {compiled_prompt}

IMPORTANT: The person in the generated image must closely resemble the reference photo."""

            payload = {
                "contents": [{
                    "parts": [
                        {"text": enhanced_prompt},
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": image_base64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "responseModalities": ["TEXT", "IMAGE"],
                    "temperature": 1.0,
                }
            }
            
            model_name = self.models["flash"]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json=payload
                )
                
                if response.status_code != 200:
                    return GenerationResult(
                        success=False,
                        error_message=f"Gemini error: {response.text}",
                        model_used=model_name,
                        provider=self.provider
                    )
                
                result = response.json()
            
            generation_time = (time.time() - start_time) * 1000
            
            # Parse response
            image_url = None
            candidates = result.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                
                for part in parts:
                    if "inlineData" in part:
                        image_data = part["inlineData"].get("data")
                        mime_type = part["inlineData"].get("mimeType", "image/png")
                        if image_data:
                            image_url = f"data:{mime_type};base64,{image_data}"
            
            return GenerationResult(
                success=True,
                image_url=image_url,
                image_urls=[image_url] if image_url else [],
                compiled_prompt=compiled_prompt,
                model_used=model_name,
                provider=self.provider,
                generation_time_ms=generation_time,
                cost_usd=0.005,
                conditioners_used=["text", "character_reference"]
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error_message=str(e),
                model_used="gemini",
                provider=self.provider
            )
    
    async def generate_with_product(
        self,
        request: GenerationRequest,
        product_image_url: str,
        strength: float = 0.6
    ) -> GenerationResult:
        """
        Generate with product reference using Gemini's image understanding.
        
        ARCHITECTURE NOTE:
        For true product conditioning, production would use:
        - IP-Adapter: Injects product CLIP embedding at cross-attention
        - ControlNet: For product shape/pose guidance
        - Product LoRA: Fine-tuned on specific products
        
        Current: We provide the product image and ask Gemini to incorporate it.
        """
        start_time = time.time()
        
        try:
            # Download product image
            async with httpx.AsyncClient() as client:
                img_response = await client.get(product_image_url)
                if img_response.status_code == 200:
                    import base64
                    image_base64 = base64.b64encode(img_response.content).decode()
                else:
                    return await self.generate(request)
            
            compiled_prompt = self.compile_prompt(request)
            enhanced_prompt = f"""Generate a marketing image that prominently features the EXACT product shown in the reference image.

The product should be:
- Clearly visible and recognizable
- Integrated naturally into the scene
- Matching the exact design, colors, and branding of the reference

Scene description: {compiled_prompt}

IMPORTANT: The product must look exactly like the reference - same colors, design, branding."""

            payload = {
                "contents": [{
                    "parts": [
                        {"text": enhanced_prompt},
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg", 
                                "data": image_base64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "responseModalities": ["TEXT", "IMAGE"],
                    "temperature": 1.0,
                }
            }
            
            model_name = self.models["flash"]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json=payload
                )
                
                if response.status_code != 200:
                    return GenerationResult(
                        success=False,
                        error_message=f"Gemini error: {response.text}",
                        model_used=model_name,
                        provider=self.provider
                    )
                
                result = response.json()
            
            generation_time = (time.time() - start_time) * 1000
            
            # Parse response
            image_url = None
            candidates = result.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                
                for part in parts:
                    if "inlineData" in part:
                        image_data = part["inlineData"].get("data")
                        mime_type = part["inlineData"].get("mimeType", "image/png")
                        if image_data:
                            image_url = f"data:{mime_type};base64,{image_data}"
            
            return GenerationResult(
                success=True,
                image_url=image_url,
                image_urls=[image_url] if image_url else [],
                compiled_prompt=compiled_prompt,
                model_used=model_name,
                provider=self.provider,
                generation_time_ms=generation_time,
                cost_usd=0.005,
                conditioners_used=["text", "product_reference"]
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error_message=str(e),
                model_used="gemini",
                provider=self.provider
            )
    
    async def generate_with_product_and_character(
        self,
        request: GenerationRequest,
        product_image_url: str,
        character_image_url: str,
        product_strength: float = 0.6,
        character_strength: float = 0.7
    ) -> GenerationResult:
        """
        Generate with both product and character references.
        
        ARCHITECTURE NOTE:
        For true multi-conditioning, production would use:
        - Combined IP-Adapter + PuLID pipeline in ComfyUI
        - Separate ControlNets for product and pose
        - Weighted embedding injection at different layers
        """
        start_time = time.time()
        
        try:
            import base64
            
            # Download both images
            async with httpx.AsyncClient() as client:
                product_resp = await client.get(product_image_url)
                character_resp = await client.get(character_image_url)
                
                product_b64 = base64.b64encode(product_resp.content).decode() if product_resp.status_code == 200 else None
                character_b64 = base64.b64encode(character_resp.content).decode() if character_resp.status_code == 200 else None
            
            compiled_prompt = self.compile_prompt(request)
            enhanced_prompt = f"""Generate a marketing image with these requirements:

1. PERSON: Include a person who looks EXACTLY like the person in the FIRST reference image (face, features, appearance)
2. PRODUCT: Prominently feature the EXACT product from the SECOND reference image (design, colors, branding)

Scene: {compiled_prompt}

The person should be naturally interacting with or showcasing the product."""

            parts = [{"text": enhanced_prompt}]
            
            if character_b64:
                parts.append({
                    "inlineData": {
                        "mimeType": "image/jpeg",
                        "data": character_b64
                    }
                })
            
            if product_b64:
                parts.append({
                    "inlineData": {
                        "mimeType": "image/jpeg",
                        "data": product_b64
                    }
                })
            
            payload = {
                "contents": [{"parts": parts}],
                "generationConfig": {
                    "responseModalities": ["TEXT", "IMAGE"],
                    "temperature": 1.0,
                }
            }
            
            model_name = self.models["flash"]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json=payload
                )
                
                if response.status_code != 200:
                    return GenerationResult(
                        success=False,
                        error_message=f"Gemini error: {response.text}",
                        model_used=model_name,
                        provider=self.provider
                    )
                
                result = response.json()
            
            generation_time = (time.time() - start_time) * 1000
            
            # Parse response
            image_url = None
            candidates = result.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                
                for part in parts:
                    if "inlineData" in part:
                        image_data = part["inlineData"].get("data")
                        mime_type = part["inlineData"].get("mimeType", "image/png")
                        if image_data:
                            image_url = f"data:{mime_type};base64,{image_data}"
            
            return GenerationResult(
                success=True,
                image_url=image_url,
                image_urls=[image_url] if image_url else [],
                compiled_prompt=compiled_prompt,
                model_used=model_name,
                provider=self.provider,
                generation_time_ms=generation_time,
                cost_usd=0.008,
                conditioners_used=["text", "product_reference", "character_reference"]
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error_message=str(e),
                model_used="gemini",
                provider=self.provider
            )
    
    def estimate_cost(self, request: GenerationRequest) -> float:
        """Estimate cost - Gemini is very cheap"""
        return 0.002 * request.num_images


class OpenRouterGenerator(ImageGenerator):
    """
    OpenRouter Implementation for Image Generation
    ===============================================
    Uses OpenRouter's unified API to access various image generation models
    including nano-banana-2.5-flash-preview and other multimodal models.
    
    OpenRouter provides access to many providers through a single API,
    making it ideal for fallback and model experimentation.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.provider = "openrouter"
        
        # Models that support image generation
        # Use GA version which is verified to work with modalities: ["image", "text"]
        self.models = {
            "nano-banana": "google/gemini-2.5-flash-image",  # GA version - verified working
            "nano-banana-preview": "google/gemini-2.5-flash-image-preview",  # Preview version
            "gemini-flash": "google/gemini-flash-1.5",  # Text only
        }
        
        self.default_model = "nano-banana"
    
    async def generate(
        self, 
        request: GenerationRequest,
        model: str = None
    ) -> GenerationResult:
        """Generate image using OpenRouter's API"""
        start_time = time.time()
        
        if not self.api_key:
            return GenerationResult(
                success=False,
                error_message="OpenRouter API key not configured",
                provider=self.provider
            )
        
        try:
            compiled_prompt = self.compile_prompt(request)
            model_id = self.models.get(model or self.default_model, self.models["nano-banana"])
            
            # OpenRouter requires modalities parameter for image generation
            # According to docs: https://openrouter.ai/docs/guides/overview/multimodal/image-generation
            payload = {
                "model": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": compiled_prompt
                    }
                ],
                "modalities": ["image", "text"],  # Required for image generation!
                "max_tokens": 8192,
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://brand-content-generator.app",
                "X-Title": "Brand Content Generator"
            }
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    # Check for rate limit
                    if response.status_code == 429:
                        return GenerationResult(
                            success=False,
                            error_message=f"Rate limited (429): {error_text}",
                            model_used=model_id,
                            provider=self.provider
                        )
                    return GenerationResult(
                        success=False,
                        error_message=f"OpenRouter error ({response.status_code}): {error_text}",
                        model_used=model_id,
                        provider=self.provider
                    )
                
                result = response.json()
            
            generation_time = (time.time() - start_time) * 1000
            
            # Parse response - OpenRouter returns images in message.images array
            # Format: { "choices": [{ "message": { "content": "...", "images": [{ "type": "image_url", "image_url": { "url": "data:image/png;base64,..." } }] } }] }
            message = result.get("choices", [{}])[0].get("message", {})
            
            # Check for images array (the correct OpenRouter format)
            images = message.get("images", [])
            image_url = None
            
            if images:
                # Get the first image from the images array
                for img in images:
                    if isinstance(img, dict):
                        img_url_obj = img.get("image_url", {})
                        if isinstance(img_url_obj, dict):
                            image_url = img_url_obj.get("url")
                        elif isinstance(img_url_obj, str):
                            image_url = img_url_obj
                        if image_url:
                            break
            
            # Fallback: Check content for images (older format)
            if not image_url:
                content = message.get("content", "")
                
                # Format 1: Content is a list with image parts
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            # Check for inline_data (base64 image)
                            if item.get("type") == "image" or "inline_data" in item:
                                inline_data = item.get("inline_data", item)
                                if "data" in inline_data:
                                    mime = inline_data.get("mimeType", inline_data.get("mime_type", "image/png"))
                                    image_url = f"data:{mime};base64,{inline_data['data']}"
                                    break
                            # Check for image_url format
                            if item.get("type") == "image_url":
                                image_url = item.get("image_url", {}).get("url")
                                if image_url:
                                    break
                
                # Format 2: Content is a string
                elif isinstance(content, str):
                    import re
                    if content.startswith("data:image"):
                        image_url = content
                    else:
                        img_match = re.search(r'!\[.*?\]\((data:image[^)]+|https?://[^)]+)\)', content)
                        if img_match:
                            image_url = img_match.group(1)
            
            # If no image found, log full response for debugging
            if not image_url:
                import json
                debug_info = json.dumps(result, default=str)[:1500]
                return GenerationResult(
                    success=False,
                    error_message=f"No image in response. Debug: {debug_info}",
                    model_used=model_id,
                    provider=self.provider,
                    generation_time_ms=generation_time
                )
            
            return GenerationResult(
                success=True,
                image_url=image_url,
                image_urls=[image_url],
                compiled_prompt=compiled_prompt,
                model_used=model_id,
                provider=self.provider,
                generation_time_ms=generation_time,
                cost_usd=0.001,  # Very cheap on free tier
                conditioners_used=["text"]
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error_message=str(e),
                model_used=model or self.default_model,
                provider=self.provider,
                generation_time_ms=(time.time() - start_time) * 1000
            )
    
    async def generate_with_character(
        self,
        request: GenerationRequest,
        character_image_url: str,
        strength: float = 0.7
    ) -> GenerationResult:
        """Generate with character reference - enhanced prompt approach"""
        # Enhance prompt with character description request
        enhanced_request = GenerationRequest(
            prompt=f"{request.prompt} featuring a person that matches this reference image: {character_image_url}",
            brand_id=request.brand_id,
            brand_condition=request.brand_condition,
            num_images=request.num_images,
            guidance_scale=request.guidance_scale,
            num_inference_steps=request.num_inference_steps,
            seed=request.seed,
            headline=request.headline,
            body_copy=request.body_copy
        )
        return await self.generate(enhanced_request)
    
    async def generate_with_product(
        self,
        request: GenerationRequest,
        product_image_url: str,
        strength: float = 0.6
    ) -> GenerationResult:
        """Generate with product reference - enhanced prompt approach"""
        enhanced_request = GenerationRequest(
            prompt=f"{request.prompt} prominently featuring this product: {product_image_url}",
            brand_id=request.brand_id,
            brand_condition=request.brand_condition,
            num_images=request.num_images,
            guidance_scale=request.guidance_scale,
            num_inference_steps=request.num_inference_steps,
            seed=request.seed,
            headline=request.headline,
            body_copy=request.body_copy
        )
        return await self.generate(enhanced_request)
    
    def estimate_cost(self, request: GenerationRequest) -> float:
        return 0.001 * request.num_images  # Very cheap


class FallbackGenerator(ImageGenerator):
    """
    Fallback generator that tries multiple providers in order.
    Useful when one provider is rate-limited or down.
    
    Priority order:
    1. OpenRouter (Nano Banana - gemini-2.5-flash-image-preview)
    2. Gemini (Google's native image generation)
    3. fal.ai (Flux models - high quality)
    4. Replicate (many models - flexible)
    """
    
    def __init__(self):
        self.generators = []
        self.provider = "fallback"
        
        # Build list of available generators - ORDER MATTERS (first = tried first)
        # OpenRouter with Nano Banana is the primary choice
        if os.getenv("OPENROUTER_API_KEY"):
            self.generators.append(("openrouter", OpenRouterGenerator()))
        if os.getenv("GOOGLE_API_KEY"):
            self.generators.append(("gemini", GeminiGenerator()))
        if os.getenv("FAL_KEY"):
            self.generators.append(("fal.ai", FalAIGenerator()))
        if os.getenv("REPLICATE_API_TOKEN"):
            self.generators.append(("replicate", ReplicateGenerator()))
        
        if not self.generators:
            print("WARNING: No image generation API keys configured!")
    
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        last_error = None
        errors_by_provider = []
        for name, gen in self.generators:
            try:
                print(f"[FallbackGenerator] Trying provider: {name}")
                result = await gen.generate(request)
                if result.success:
                    print(f"[FallbackGenerator] Success with {name}")
                    return result
                # Check for rate limit error
                error_msg = result.error_message or "Unknown error"
                print(f"[FallbackGenerator] {name} failed: {error_msg}")
                errors_by_provider.append(f"{name}: {error_msg}")
                if "429" in error_msg or "quota" in error_msg.lower():
                    print(f"Rate limited on {name}, trying next provider...")
                    last_error = error_msg
                    continue
                # For non-rate-limit errors, still try next provider
                last_error = error_msg
            except Exception as e:
                error_msg = str(e)
                print(f"[FallbackGenerator] Exception with {name}: {error_msg}")
                errors_by_provider.append(f"{name}: {error_msg}")
                last_error = error_msg
                continue
        
        # Build detailed error message
        detailed_errors = "; ".join(errors_by_provider[-3:]) if errors_by_provider else "No providers configured"
        return GenerationResult(
            success=False,
            error_message=f"All providers failed. Errors: {detailed_errors}",
            provider="fallback"
        )
    
    async def generate_with_character(self, request, character_image_url, strength=0.7):
        for name, gen in self.generators:
            try:
                result = await gen.generate_with_character(request, character_image_url, strength)
                if result.success:
                    return result
                if result.error_message and ("429" in result.error_message or "quota" in result.error_message.lower()):
                    continue
                return result
            except:
                continue
        return GenerationResult(success=False, error_message="All providers failed", provider="fallback")
    
    async def generate_with_product(self, request, product_image_url, strength=0.6):
        for name, gen in self.generators:
            try:
                result = await gen.generate_with_product(request, product_image_url, strength)
                if result.success:
                    return result
                if result.error_message and ("429" in result.error_message or "quota" in result.error_message.lower()):
                    continue
                return result
            except:
                continue
        return GenerationResult(success=False, error_message="All providers failed", provider="fallback")
    
    async def generate_with_product_and_character(self, request, product_url, char_url, p_str=0.6, c_str=0.7):
        for name, gen in self.generators:
            if hasattr(gen, 'generate_with_product_and_character'):
                try:
                    result = await gen.generate_with_product_and_character(request, product_url, char_url, p_str, c_str)
                    if result.success:
                        return result
                    if result.error_message and ("429" in result.error_message or "quota" in result.error_message.lower()):
                        continue
                    return result
                except:
                    continue
        # Fallback to just product or character
        return await self.generate_with_product(request, product_url, p_str)
    
    def estimate_cost(self, request: GenerationRequest) -> float:
        return 0.02  # Average estimate


# Factory function to get the right generator
def get_generator(provider: str = None) -> ImageGenerator:
    """Get image generator for specified provider"""
    # Use fallback by default for resilience
    if provider is None:
        return FallbackGenerator()
    
    if provider == "openrouter":
        return OpenRouterGenerator()
    elif provider == "gemini":
        return GeminiGenerator()
    elif provider == "fal.ai":
        return FalAIGenerator()
    elif provider == "replicate":
        return ReplicateGenerator()
    elif provider == "fallback":
        return FallbackGenerator()
    else:
        return FallbackGenerator()
