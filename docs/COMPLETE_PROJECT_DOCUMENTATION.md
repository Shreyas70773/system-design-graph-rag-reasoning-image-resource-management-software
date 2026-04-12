# Complete Project Documentation
## Brand-Aligned Content Generation Platform with GraphRAG

**Version:** 1.0.0  
**Last Updated:** January 2026  
**Research Focus:** GraphRAG-Guided Compositional Image Generation

---

# Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Technology Stack](#3-technology-stack)
4. [Backend Deep Dive](#4-backend-deep-dive)
   - 4.1 [Application Entry Point](#41-application-entry-point)
   - 4.2 [Configuration Management](#42-configuration-management)
   - 4.3 [Database Layer (Neo4j)](#43-database-layer-neo4j)
   - 4.4 [GraphRAG Service Layer](#44-graphrag-service-layer)
   - 4.5 [LLM Reasoning Engine](#45-llm-reasoning-engine)
   - 4.6 [Image Generation Pipeline](#46-image-generation-pipeline)
   - 4.7 [Text Overlay System](#47-text-overlay-system)
   - 4.8 [Logo Layering System](#48-logo-layering-system)
   - 4.9 [API Routers](#49-api-routers)
   - 4.10 [Web Scraping Modules](#410-web-scraping-modules)
   - 4.11 [Feedback Learning System](#411-feedback-learning-system)
5. [Frontend Deep Dive](#5-frontend-deep-dive)
6. [GraphRAG Pipeline Explained](#6-graphrag-pipeline-explained)
7. [Data Flow Diagrams](#7-data-flow-diagrams)
8. [File-by-File Reference](#8-file-by-file-reference)

---

# 1. Executive Summary

The **Brand-Aligned Content Generation Platform** is a sophisticated system that leverages **GraphRAG (Graph Retrieval-Augmented Generation)** to create marketing visuals that are automatically aligned with a brand's identity. 

## Core Innovation

Traditional AI image generators don't understand brand context. They can create generic images but cannot enforce:
- Specific brand color palettes
- Consistent visual styles
- Product placement rules
- Typography preferences
- Logo placement standards

Our system solves this by:
1. **Storing brand identity as a knowledge graph** in Neo4j
2. **Using LLM reasoning** to plan each generation
3. **Conditioning AI image generation** with brand parameters
4. **Post-processing with PIL** to add text overlays and logos
5. **Learning from feedback** to improve future generations

---

# 2. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                               │
│                    React 18 + Vite + Tailwind CSS                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │   Home   │  │Onboarding│  │Dashboard │  │ Generate │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP/REST API
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    API ROUTERS LAYER                         │   │
│  │  brands.py │ brand_dna.py │ generation.py │ feedback.py     │   │
│  │  content_creator.py │ linkedin.py │ health.py               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                             │                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   SERVICE LAYER                              │   │
│  │            brand_dna_service.py (GraphRAG Orchestrator)      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                             │                                        │
│  ┌──────────────┬───────────┼───────────┬──────────────────────┐   │
│  │              │           │           │                      │   │
│  ▼              ▼           ▼           ▼                      │   │
│ ┌────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐│   │
│ │Database│ │   LLM   │ │  Image  │ │  Text   │ │   Logo      ││   │
│ │ Client │ │Reasoner │ │Generator│ │ Overlay │ │  Layering   ││   │
│ └────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────────┘│   │
│                                                                      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │  Neo4j   │        │  Groq    │        │OpenRouter│
    │  Aura    │        │   API    │        │   API    │
    │(Graph DB)│        │  (LLM)   │        │(Image AI)│
    └──────────┘        └──────────┘        └──────────┘
```

---

# 3. Technology Stack

## Backend
| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | FastAPI 0.104+ | Async Python web framework |
| Runtime | Python 3.10+ | Core runtime |
| Database | Neo4j Aura | Cloud graph database |
| LLM | Groq (Llama 3.3 70B) | Generation planning |
| Image AI | OpenRouter (Gemini 2.5 Flash) | Image generation |
| Image Processing | PIL/Pillow | Text overlay & compositing |
| HTTP Client | httpx | Async API calls |
| Validation | Pydantic | Request/response validation |

## Frontend
| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | React 18 | UI library |
| Build Tool | Vite 5 | Fast development server |
| Styling | Tailwind CSS | Utility-first CSS |
| Routing | React Router v6 | Client-side routing |
| HTTP Client | Axios | API communication |
| Icons | Lucide React | Icon library |

## External APIs
| API | Provider | Purpose |
|-----|----------|---------|
| Groq | Groq Inc. | LLM reasoning (free tier) |
| OpenRouter | OpenRouter | Multi-model image generation |
| Perplexity | Perplexity AI | Trending topics discovery |
| Neo4j Aura | Neo4j | Cloud graph database |

---

# 4. Backend Deep Dive

## 4.1 Application Entry Point

### File: `backend/app/main.py`

This is the FastAPI application bootstrap file. It:

1. **Creates the FastAPI app instance** with metadata
2. **Configures CORS middleware** for frontend communication
3. **Registers all API routers** with their prefixes
4. **Manages application lifecycle** (startup/shutdown)
5. **Handles global exceptions** with CORS headers

```python
# Key components:

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events"""
    # Startup: Verify Neo4j connection
    if neo4j_client.verify_connection():
        print("[OK] Neo4j connection verified")
    yield
    # Shutdown: Close database connections
    neo4j_client.close()

app = FastAPI(
    title="Brand-Aligned Content Generation API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware allows frontend on different port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Development setting
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router registration with prefixes
app.include_router(brand_dna.router, tags=["Brand DNA"])
app.include_router(brands.router, prefix="/api/brands")
app.include_router(generation.router, prefix="/api")
```

**Flow:**
1. Server starts → `lifespan` context manager runs startup code
2. Neo4j connection verified
3. Routes become available
4. On shutdown → cleanup runs

---

## 4.2 Configuration Management

### File: `backend/app/config.py`

Centralizes all environment variable loading using Pydantic Settings:

```python
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file immediately on import
load_dotenv(_env_path)

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "Brand-Aligned Content Generation Platform"
    
    # Neo4j Aura (Graph Database)
    neo4j_uri: str = ""
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    
    # AI APIs
    groq_api_key: str = ""      # LLM reasoning
    openai_api_key: str = ""    # Backup LLM
    perplexity_api_key: str = "" # Content discovery
    huggingface_token: str = "" # Image generation

@lru_cache()  # Singleton pattern
def get_settings() -> Settings:
    return Settings()
```

**Why This Design:**
- **Single Source of Truth**: All config in one place
- **Type Safety**: Pydantic validates types
- **Caching**: `@lru_cache` ensures settings loaded once
- **Early Loading**: `load_dotenv()` runs on import

---

## 4.3 Database Layer (Neo4j)

### File: `backend/app/database/neo4j_client.py`

The Neo4j client handles all graph database operations:

### Connection Management

```python
class Neo4jClient:
    def __init__(self):
        self._driver = None
        self._connection_attempted = False
    
    @property
    def driver(self):
        """Lazy initialization of Neo4j driver"""
        if self._driver is None and not self._connection_attempted:
            self._connection_attempted = True
            settings = get_settings()
            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
        return self._driver
```

### Brand Operations

```python
def create_brand(self, data: Dict[str, Any]) -> str:
    """Create a new brand node with related nodes"""
    brand_id = str(uuid.uuid4())[:8]
    
    query = """
    CREATE (b:Brand {
        id: $brand_id,
        name: $name,
        website: $website,
        tagline: $tagline,
        industry: $industry,
        created_at: datetime()
    })
    
    WITH b
    
    // Create logo node if provided
    FOREACH (logo IN CASE WHEN $logo_url IS NOT NULL THEN [1] ELSE [] END |
        CREATE (l:Logo {
            url: $logo_url,
            quality_score: $logo_quality_score,
            source: $logo_source
        })
        CREATE (b)-[:HAS_LOGO]->(l)
    )
    
    RETURN b.id as brand_id
    """
```

### Graph Schema

```cypher
# Node Types:
(:Brand {id, name, website, tagline, industry})
(:Logo {url, quality_score, source})
(:ColorNode {hex, name, usage_weight, contexts})
(:StyleNode {type, keywords, negative_keywords, weight})
(:CompositionNode {layout, text_density, text_position, overlay_opacity})
(:ProductNode {id, name, category, image_url, description})
(:CharacterNode {id, name, reference_image_url, body_type})
(:LearnedPreference {trigger, applies, aspect, confidence})
(:Generation {id, prompt, image_url, model_used, created_at})

# Relationships:
(Brand)-[:HAS_LOGO]->(Logo)
(Brand)-[:HAS_COLOR]->(ColorNode)
(Brand)-[:HAS_STYLE]->(StyleNode)
(Brand)-[:HAS_COMPOSITION]->(CompositionNode)
(Brand)-[:SELLS]->(ProductNode)
(Brand)-[:HAS_CHARACTER]->(CharacterNode)
(Brand)-[:LEARNED]->(LearnedPreference)
(Brand)-[:GENERATED]->(Generation)
```

**Why Graph Database:**
- **Natural Brand Modeling**: Brands have multiple related entities
- **Flexible Schema**: Easy to add new node types
- **Relationship Queries**: Efficient traversal for GraphRAG
- **Pattern Matching**: Find brands by color, style, etc.

---

## 4.4 GraphRAG Service Layer

### File: `backend/app/services/brand_dna_service.py`

This is the **BRAIN** of the system - orchestrating the entire GraphRAG pipeline.

### BrandDNA Data Class

```python
@dataclass
class BrandDNA:
    """Complete Brand DNA from Neo4j"""
    brand_id: str
    brand_name: str
    tagline: Optional[str] = None
    industry: Optional[str] = None
    logo_url: Optional[str] = None
    
    colors: List[Dict[str, Any]] = None      # Color palette
    styles: List[Dict[str, Any]] = None      # Visual styles
    composition: Optional[Dict] = None        # Layout preferences
    products: List[Dict[str, Any]] = None    # Product references
    characters: List[Dict[str, Any]] = None  # Face references
    learned_preferences: List[Dict] = None   # From feedback
    
    def to_brand_condition(self) -> BrandCondition:
        """Convert to BrandCondition for image generator"""
        return BrandCondition(
            primary_colors=[c["hex"] for c in self.colors if c.get("hex")],
            style_keywords=[kw for s in self.styles for kw in (s.get("keywords") or [])],
            negative_keywords=[kw for s in self.styles for kw in (s.get("negative_keywords") or [])],
            layout=self.composition.get("layout", "centered") if self.composition else "centered",
            # ... more mappings
        )
```

### Main Generation Pipeline

```python
async def generate_content(
    self,
    brand_id: str,
    user_prompt: str,
    headline: Optional[str] = None,
    body_copy: Optional[str] = None,
    product_id: Optional[str] = None,
    character_id: Optional[str] = None,
    aspect_ratio: str = "1:1",
    text_layout: str = "bottom_centered",
    include_logo: bool = False,
    use_reasoning: bool = True
) -> Dict[str, Any]:
    """
    Full GraphRAG generation pipeline:
    1. Retrieve Brand DNA
    2. LLM plans generation
    3. Apply learned preferences
    4. Generate image with conditioning
    5. Post-process (text + logo)
    6. Store generation in graph
    """
    
    pipeline_steps = []
    
    # STEP 1: RETRIEVE - Get Brand DNA from Neo4j
    brand_dna = await self.get_brand_dna(brand_id)
    
    # STEP 2: AUGMENT - LLM Planning
    if use_reasoning:
        plan = await self.reasoner.plan_generation(
            user_prompt=user_prompt,
            brand_context=brand_dna.to_dict(),
            learned_preferences=brand_dna.learned_preferences
        )
    
    # STEP 3: BUILD CONDITIONING - Convert to generation parameters
    brand_condition = brand_dna.to_brand_condition()
    brand_condition.aspect_ratio = aspect_ratio
    
    # Apply plan adjustments
    if plan:
        brand_condition.overlay_opacity = plan.suggested_overlay
        brand_condition.layout = plan.suggested_layout
        brand_condition.style_strength = plan.style_strength
    
    # STEP 4: COMPILE PROMPT
    positive_prompt, negative_prompt = await self.reasoner.compile_final_prompt(
        plan, brand_dna.to_dict()
    )
    
    # STEP 5: GENERATE IMAGE
    request = GenerationRequest(
        prompt=positive_prompt,
        brand_id=brand_id,
        brand_condition=brand_condition,
        headline=headline,
        body_copy=body_copy
    )
    result = await self.generator.generate(request)
    
    # STEP 6: POST-PROCESS (Text + Logo)
    if result.success and (headline or body_copy or include_logo):
        # ... text overlay and logo compositing
    
    # STEP 7: STORE IN GRAPH
    await self._store_generation(brand_id, generation_id, result, plan, brand_dna)
    
    return {
        "success": result.success,
        "image_url": result.image_url,
        "pipeline_steps": pipeline_steps,
        # ...
    }
```

### Brand DNA Retrieval Query

```python
async def get_brand_dna(self, brand_id: str) -> Optional[BrandDNA]:
    query = """
    MATCH (b:Brand {id: $brand_id})
    
    OPTIONAL MATCH (b)-[:HAS_LOGO]->(logo:Logo)
    OPTIONAL MATCH (b)-[cr:HAS_COLOR]->(c:ColorNode)
    OPTIONAL MATCH (b)-[sr:HAS_STYLE]->(s:StyleNode)
    OPTIONAL MATCH (b)-[:HAS_COMPOSITION]->(comp:CompositionNode)
    OPTIONAL MATCH (b)-[:SELLS]->(p:ProductNode)
    OPTIONAL MATCH (b)-[:HAS_CHARACTER]->(ch:CharacterNode)
    OPTIONAL MATCH (b)-[:LEARNED]->(lp:LearnedPreference)
    
    RETURN b,
           logo.url as logo_url,
           collect(DISTINCT {hex: c.hex, name: c.name, weight: cr.weight}) as colors,
           collect(DISTINCT {type: s.type, keywords: s.keywords}) as styles,
           comp as composition,
           collect(DISTINCT {id: p.id, name: p.name, image_url: p.image_url}) as products,
           collect(DISTINCT {id: ch.id, name: ch.name, reference_image_url: ch.reference_image_url}) as characters,
           collect(DISTINCT {trigger: lp.trigger, applies: lp.applies}) as learned_preferences
    """
```

**This single query retrieves the ENTIRE brand identity** in one database call, demonstrating the power of graph databases for connected data.

---

## 4.5 LLM Reasoning Engine

### File: `backend/app/generation/llm_reasoner.py`

The LLM Reasoner implements the "thinking first" approach before image generation.

### GenerationPlan Data Class

```python
@dataclass
class GenerationPlan:
    """The output of LLM planning - what to retrieve and how to condition"""
    
    # Parsed user intent
    subject: str
    scene_description: str
    mood: str
    
    # What to retrieve from Brand DNA
    needs_colors: bool = True
    needs_style: bool = True
    needs_products: List[str] = field(default_factory=list)
    needs_character: bool = False
    
    # Composition decisions
    suggested_layout: str = "centered"
    suggested_text_position: str = "bottom"
    suggested_overlay: float = 0.0
    
    # Conditioning strengths (0-1)
    color_strength: float = 0.8
    style_strength: float = 0.8
    product_strength: float = 0.6
    
    # Reasoning trace (for explainability)
    reasoning_steps: List[str] = field(default_factory=list)
```

### Planning Function

```python
async def plan_generation(
    self,
    user_prompt: str,
    brand_context: Dict[str, Any],
    learned_preferences: List[Dict[str, Any]]
) -> GenerationPlan:
    """
    Analyze user prompt and plan what to retrieve from Brand DNA.
    This is the "thinking" step before generation.
    """
    
    system_prompt = """You are an AI that plans brand-aligned image generation.
Given a user prompt and brand context, you must:
1. Analyze what the user wants to generate
2. Decide which brand elements (colors, style, products) are relevant
3. Plan composition and layout
4. Consider learned preferences from past feedback
5. Output a structured generation plan

Output valid JSON matching this schema:
{
    "subject": "main subject of the image",
    "scene_description": "detailed scene description",
    "mood": "emotional tone",
    "needs_colors": true/false,
    "needs_style": true/false,
    "needs_products": ["product names if relevant"],
    "suggested_layout": "centered|left-aligned|split|asymmetric",
    "color_strength": 0.0-1.0,
    "style_strength": 0.0-1.0,
    "reasoning_steps": ["step 1 reasoning", "step 2 reasoning", ...]
}"""

    user_content = f"""User Prompt: {user_prompt}
    
Brand Context:
- Name: {brand_context.get('brand_name')}
- Industry: {brand_context.get('industry')}
- Colors: {brand_context.get('colors')}
- Styles: {brand_context.get('styles')}
- Products: {brand_context.get('products')}
- Learned Preferences: {learned_preferences}
"""

    response = await self._call_llm(system_prompt, user_content)
    # Parse JSON and return GenerationPlan
```

**Why LLM Planning:**
- **Context Awareness**: LLM understands which brand elements are relevant
- **Dynamic Decisions**: Adjusts composition based on prompt
- **Explainability**: Reasoning steps show why decisions were made
- **Learning Integration**: Applies learned preferences from feedback

---

## 4.6 Image Generation Pipeline

### File: `backend/app/generation/image_generators.py`

This file implements an **abstracted interface** for multiple image generation backends.

### Core Data Structures

```python
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
    text_position: str = "bottom"
    overlay_opacity: float = 0.0
    aspect_ratio: str = "1:1"
    
    # Product reference (for IP-Adapter)
    product_image_url: Optional[str] = None
    product_strength: float = 0.6
    
    # Character reference (for PuLID/InstantID)
    face_image_url: Optional[str] = None
    face_strength: float = 0.7

@dataclass
class GenerationRequest:
    """Full generation request with all parameters"""
    prompt: str
    brand_id: str
    brand_condition: BrandCondition
    num_images: int = 1
    guidance_scale: float = 7.5
    num_inference_steps: int = 30
    headline: Optional[str] = None
    body_copy: Optional[str] = None

@dataclass
class GenerationResult:
    """Result from image generation"""
    success: bool
    image_url: Optional[str] = None
    compiled_prompt: Optional[str] = None
    model_used: str = ""
    generation_time_ms: float = 0
    cost_usd: float = 0
    conditioners_used: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
```

### Abstract Base Class

```python
class ImageGenerator(ABC):
    """Abstract base class for image generation backends"""
    
    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate image(s) based on request"""
        pass
    
    @abstractmethod
    async def generate_with_character(
        self, request: GenerationRequest,
        character_image_url: str,
        strength: float = 0.7
    ) -> GenerationResult:
        """Generate with character consistency (PuLID/InstantID)"""
        pass
    
    @abstractmethod
    async def generate_with_product(
        self, request: GenerationRequest,
        product_image_url: str,
        strength: float = 0.6
    ) -> GenerationResult:
        """Generate with product reference (IP-Adapter)"""
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
            parts.append(f"Color palette: {', '.join(cond.primary_colors[:3])}")
        
        # Add composition guidance
        if cond.layout:
            parts.append(f"Layout: {cond.layout}")
        
        # NO TEXT in image - text will be composited via PIL
        parts.append("photorealistic, no text, no words, no letters")
        
        return ". ".join(parts)
```

### OpenRouter Implementation

```python
class OpenRouterGenerator(ImageGenerator):
    """OpenRouter implementation - access to multiple models"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "google/gemini-2.5-flash-image"  # Default model
    
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        start_time = time.time()
        
        compiled_prompt = self.compile_prompt(request)
        negative_prompt = self.get_negative_prompt(request)
        
        payload = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": [{"type": "text", "text": compiled_prompt}]
            }]
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://brand-gen.com"
                },
                json=payload
            )
            result = response.json()
        
        # Extract image URL from response
        image_url = extract_image_from_response(result)
        
        return GenerationResult(
            success=True,
            image_url=image_url,
            compiled_prompt=compiled_prompt,
            model_used=self.model,
            generation_time_ms=(time.time() - start_time) * 1000,
            cost_usd=0.001
        )
```

**Architecture Note:** The system uses **prompt-level conditioning** with OpenRouter. For production with TRUE diffusion-level control, we would use:

1. **Self-Hosted ComfyUI** with custom workflows
2. **LoRAs** trained on brand assets at UNet level
3. **IP-Adapter** for product conditioning at cross-attention
4. **ControlNet** for composition (pose, depth, layout)
5. **PuLID/InstantID** for face embedding at attention layers

---

## 4.7 Text Overlay System

### File: `backend/app/generation/text_overlay.py`

The text overlay system uses **PIL (Pillow)** to composite text onto generated images after AI generation. This ensures text is crisp and readable, unlike AI-generated text which is often distorted.

### Available Fonts

```python
AVAILABLE_FONTS = {
    "montserrat": {"name": "Montserrat", "description": "Modern, clean sans-serif", "style": "modern"},
    "playfair": {"name": "Playfair Display", "description": "Elegant serif for luxury brands", "style": "elegant"},
    "roboto": {"name": "Roboto", "description": "Versatile, professional sans-serif", "style": "professional"},
    "poppins": {"name": "Poppins", "description": "Friendly, geometric sans-serif", "style": "friendly"},
    "oswald": {"name": "Oswald", "description": "Bold, impactful condensed", "style": "bold"},
    "bebas": {"name": "Bebas Neue", "description": "All-caps display font", "style": "display"},
}

TEXT_LAYOUTS = {
    "top_centered": {"headline_position": "top_center", "body_position": "below_headline"},
    "bottom_centered": {"headline_position": "bottom_center", "body_position": "above_headline"},
    "center_overlay": {"headline_position": "center", "body_position": "below_headline"},
    "bottom_left": {"headline_position": "bottom_left", "body_position": "below_headline"},
}
```

### Color Analysis for Text

```python
def get_dominant_color_region(image: Image.Image, region: str) -> Tuple[int, int, int]:
    """Get dominant color from a specific region of the image"""
    width, height = image.size
    
    if region == "top":
        box = (0, 0, width, height // 3)
    elif region == "bottom":
        box = (0, 2 * height // 3, width, height)
    elif region == "center":
        margin_x = width // 4
        margin_y = height // 4
        box = (margin_x, margin_y, width - margin_x, height - margin_y)
    
    region_image = image.crop(box).resize((50, 50))
    colors = region_image.getcolors(2500)
    most_common = max(colors, key=lambda x: x[0])[1]
    return most_common[:3]

def get_contrasting_color(bg_color: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Calculate contrasting text color (black or white)"""
    luminance = (0.299 * bg_color[0] + 0.587 * bg_color[1] + 0.114 * bg_color[2]) / 255
    return (255, 255, 255) if luminance < 0.5 else (0, 0, 0)
```

### Main Compositing Function

```python
def composite_text_on_image(
    image_bytes: bytes,
    headline: Optional[str],
    body_copy: Optional[str],
    brand_context: Dict[str, Any],
    layout: str = "bottom_centered"
) -> bytes:
    """
    Composite text overlay on the generated image.
    
    PROCESS:
    1. Open image and convert to RGBA
    2. Analyze background color in text region
    3. Determine text color (auto-contrast)
    4. Add gradient overlay for readability
    5. Render headline and body copy with shadows
    6. Return composited image bytes
    """
    
    # Open the image
    image = Image.open(io.BytesIO(image_bytes)).convert('RGBA')
    width, height = image.size
    
    # Get brand preferences
    font_id = brand_context.get('font_id', 'montserrat')
    brand_colors = brand_context.get('colors', [])
    
    # Determine text color based on layout position
    if layout in ["bottom_centered", "bottom_left"]:
        region = "bottom"
    elif layout == "top_centered":
        region = "top"
    else:
        region = "center"
    
    bg_color = get_dominant_color_region(image, region)
    
    # Use brand color if it contrasts well, otherwise black/white
    if brand_colors:
        primary_rgb = hex_to_rgb(brand_colors[0].get('hex', '#FFFFFF'))
        bg_luminance = calculate_luminance(bg_color)
        primary_luminance = calculate_luminance(primary_rgb)
        
        if abs(bg_luminance - primary_luminance) > 0.4:
            text_color = primary_rgb
        else:
            text_color = get_contrasting_color(bg_color)
    else:
        text_color = get_contrasting_color(bg_color)
    
    # Create text layer
    text_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)
    
    # Load fonts
    headline_font = load_font(font_id, int(height * 0.08))  # 8% of height
    body_font = load_font(font_id, int(height * 0.04))      # 4% of height
    
    # Add gradient overlay for readability
    if layout in ["bottom_centered", "bottom_left"]:
        gradient = create_gradient_overlay((width, height // 2), "bottom")
        gradient_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        gradient_layer.paste(gradient, (0, height // 2))
        image = Image.alpha_composite(image, gradient_layer)
    
    # Draw text with shadows
    if layout == "bottom_centered":
        # Draw from bottom up
        current_y = height - padding_vertical
        
        if body_copy:
            body_lines = wrap_text(body_copy, body_font, max_text_width, draw)
            for line in reversed(body_lines):
                x = (width - get_text_width(line, body_font)) // 2
                current_y -= line_height
                add_text_shadow(draw, (x, current_y), line, body_font)
                draw.text((x, current_y), line, font=body_font, fill=(*text_color, 255))
        
        if headline:
            headline_lines = wrap_text(headline.upper(), headline_font, max_text_width, draw)
            for line in reversed(headline_lines):
                x = (width - get_text_width(line, headline_font)) // 2
                current_y -= line_height
                add_text_shadow(draw, (x, current_y), line, headline_font, offset=4)
                draw.text((x, current_y), line, font=headline_font, fill=(*text_color, 255))
    
    # Composite and return
    result = Image.alpha_composite(image, text_layer)
    result = result.convert('RGB')
    
    output = io.BytesIO()
    result.save(output, format='PNG', quality=95)
    return output.getvalue()
```

### Gradient Overlay for Readability

```python
def create_gradient_overlay(
    size: Tuple[int, int],
    direction: str = "bottom",
    color: Tuple[int, int, int] = (0, 0, 0),
    opacity_start: int = 0,
    opacity_end: int = 180
) -> Image.Image:
    """Create a gradient overlay for better text readability"""
    width, height = size
    overlay = Image.new('RGBA', size, (0, 0, 0, 0))
    
    for y in range(height):
        if direction == "bottom":
            progress = y / height
        elif direction == "top":
            progress = 1 - (y / height)
        
        opacity = int(opacity_start + (opacity_end - opacity_start) * progress)
        
        for x in range(width):
            overlay.putpixel((x, y), (*color, opacity))
    
    return overlay
```

**Why PIL for Text:**
- **Crisp Text**: AI models generate blurry, distorted text
- **Font Control**: Use exact brand fonts
- **Positioning**: Precise layout control
- **Readability**: Gradient overlays ensure text is visible

---

## 4.8 Logo Layering System

### File: `backend/app/generation/text_overlay.py` (continued)

The logo layering system adds brand logos as watermarks to generated images.

### Logo Compositing Function

```python
def add_logo_to_image(
    image_bytes: bytes,
    logo_bytes: bytes,
    position: str = "bottom_right",
    scale: float = 0.12,          # 12% of image width
    padding: float = 0.03,         # 3% padding from edge
    opacity: float = 0.9           # 90% opacity
) -> bytes:
    """
    Add a logo watermark to an image.
    
    PROCESS:
    1. Open base image and logo (both as RGBA)
    2. Calculate logo size based on scale factor
    3. Resize logo maintaining aspect ratio
    4. Apply opacity to logo alpha channel
    5. Calculate position based on padding
    6. Create transparent layer and paste logo
    7. Composite onto base image
    8. Return final image bytes
    """
    
    # Open images
    image = Image.open(io.BytesIO(image_bytes)).convert('RGBA')
    logo = Image.open(io.BytesIO(logo_bytes)).convert('RGBA')
    
    img_width, img_height = image.size
    
    # Calculate logo size (scaled to image width)
    target_width = int(img_width * scale)
    aspect = logo.width / logo.height
    target_height = int(target_width / aspect)
    
    # Resize logo with high-quality resampling
    logo = logo.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    # Apply opacity to alpha channel
    if opacity < 1.0:
        alpha = logo.split()[3]  # Get alpha channel
        alpha = alpha.point(lambda p: int(p * opacity))  # Reduce opacity
        logo.putalpha(alpha)
    
    # Calculate position
    pad_x = int(img_width * padding)
    pad_y = int(img_height * padding)
    
    if position == "top_left":
        pos = (pad_x, pad_y)
    elif position == "top_right":
        pos = (img_width - target_width - pad_x, pad_y)
    elif position == "bottom_left":
        pos = (pad_x, img_height - target_height - pad_y)
    elif position == "bottom_right":
        pos = (img_width - target_width - pad_x, img_height - target_height - pad_y)
    elif position == "center":
        pos = ((img_width - target_width) // 2, (img_height - target_height) // 2)
    else:
        pos = (img_width - target_width - pad_x, img_height - target_height - pad_y)
    
    # Create transparent layer and paste logo
    logo_layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
    logo_layer.paste(logo, pos, logo)  # Use logo as mask for transparency
    
    # Composite
    result = Image.alpha_composite(image, logo_layer)
    result = result.convert('RGB')
    
    # Save to bytes
    output = io.BytesIO()
    result.save(output, format='PNG', quality=95)
    output.seek(0)
    
    return output.getvalue()
```

### Integration in Pipeline

The logo is added in `brand_dna_service.py` during post-processing:

```python
# In generate_content() method:

if include_logo and brand_dna.logo_url:
    try:
        # Fetch logo from URL
        async with httpx.AsyncClient(timeout=15.0) as client:
            logo_response = await client.get(brand_dna.logo_url)
            logo_response.raise_for_status()
            logo_bytes = logo_response.content
        
        # Add logo to image
        current_image_bytes = add_logo_to_image(
            image_bytes=current_image_bytes,
            logo_bytes=logo_bytes,
            position="bottom_right",
            scale=0.12,      # 12% of image width
            opacity=0.85     # 85% opacity
        )
        
        pipeline_steps[-1]["logo_added"] = True
    except Exception as e:
        pipeline_steps[-1]["logo_error"] = str(e)
        # Continue without logo if error
```

### Logo Storage in Neo4j

Logos are stored as separate nodes with relationship to Brand:

```cypher
# Create logo node
CREATE (l:Logo {
    url: $logo_url,
    source: 'manual_upload',
    created_at: datetime()
})

# Connect to brand
CREATE (b)-[:HAS_LOGO]->(l)
```

### Update Logo API

```python
@router.put("/{brand_id}/logo")
async def update_logo(brand_id: str, request: UpdateLogoRequest):
    """Update brand logo URL"""
    query = """
    MATCH (b:Brand {id: $brand_id})
    OPTIONAL MATCH (b)-[r:HAS_LOGO]->(old_logo:Logo)
    DELETE r, old_logo
    WITH b
    CREATE (l:Logo {
        url: $logo_url,
        source: 'manual_upload',
        created_at: datetime()
    })
    CREATE (b)-[:HAS_LOGO]->(l)
    RETURN l.url as logo_url
    """
    result = neo4j.execute_query(query, {"brand_id": brand_id, "logo_url": request.logo_url})
    return {"success": True, "logo_url": result[0]["logo_url"]}
```

**Logo Pipeline Summary:**
1. **Storage**: Logo URL stored in Neo4j Logo node
2. **Retrieval**: Fetched during Brand DNA query via `(b)-[:HAS_LOGO]->(logo:Logo)`
3. **Download**: Fetched from URL using httpx during post-processing
4. **Compositing**: Added to image using PIL with configurable position/scale/opacity
5. **Output**: Final image returned as base64 data URL

---

## 4.9 API Routers

### Router Architecture

```
backend/app/routers/
├── __init__.py
├── health.py           # Health check endpoint
├── brands.py           # Brand scraping and management
├── brand_dna.py        # GraphRAG Brand DNA endpoints
├── generation.py       # Basic generation endpoints
├── advanced_generation.py  # Advanced generation with decomposition
├── feedback.py         # Feedback collection
├── content_creator.py  # AI-powered content discovery
├── linkedin.py         # LinkedIn post generation
├── products.py         # Product management
└── search.py           # Search functionality
```

### Key Routers

#### `brand_dna.py` - GraphRAG Endpoints

```python
router = APIRouter(prefix="/api/brand-dna", tags=["Brand DNA"])

@router.get("/{brand_id}")
async def get_brand_dna(brand_id: str):
    """Get complete Brand DNA for a brand"""
    
@router.get("/{brand_id}/graph")
async def get_brand_graph(brand_id: str):
    """Get Brand DNA as graph visualization data"""

@router.post("/{brand_id}/generate")
async def generate_with_brand_dna(brand_id: str, request: GenerateRequest):
    """Generate image using full GraphRAG pipeline"""

@router.post("/{brand_id}/colors")
async def add_color(brand_id: str, request: AddColorRequest):
    """Add color to brand DNA"""

@router.post("/{brand_id}/styles")
async def add_style(brand_id: str, request: AddStyleRequest):
    """Add style to brand DNA"""

@router.post("/{brand_id}/products")
async def add_product(brand_id: str, request: AddProductRequest):
    """Add product reference"""

@router.post("/{brand_id}/characters")
async def add_character(brand_id: str, request: AddCharacterRequest):
    """Add character reference for face consistency"""

@router.put("/{brand_id}/logo")
async def update_logo(brand_id: str, request: UpdateLogoRequest):
    """Update brand logo URL"""

@router.post("/{brand_id}/feedback")
async def process_feedback(brand_id: str, request: FeedbackRequest):
    """Process semantic feedback and update graph"""
```

#### `content_creator.py` - AI Content Discovery

```python
router = APIRouter()

@router.post("/discover-topics")
async def discover_trending_topics(request: ContentDiscoveryRequest):
    """
    Search the internet for trending topics relevant to the brand
    Uses Perplexity API (sonar model)
    """

@router.post("/generate-ideas")
async def generate_content_ideas(request: GenerateIdeasRequest):
    """Generate content ideas based on profile and trends"""

@router.post("/generate-post")
async def generate_linkedin_post(request: GeneratePostRequest):
    """Generate a full LinkedIn post"""
```

---

## 4.10 Web Scraping Modules

### File Structure

```
backend/app/scraping/
├── __init__.py
├── website_scraper.py   # Main brand data extraction
├── logo_extractor.py    # Logo finding and downloading
└── color_extractor.py   # Color palette extraction
```

### `website_scraper.py` - Brand Extraction

```python
async def scrape_brand_data(url: str) -> Dict[str, Any]:
    """
    Main function to scrape brand data from a website.
    
    PROCESS:
    1. Fetch webpage HTML
    2. Extract company name from title/meta tags
    3. Extract tagline from meta description
    4. Find and download logo
    5. Extract colors from logo
    6. Save to Neo4j and return
    """
    
    # Ensure URL has scheme
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Fetch the webpage
    html = fetch_webpage(url)
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract company information
    company_info = extract_company_info(soup, url)
    meta_info = extract_meta_tags(soup)
    
    # Get company name (prioritize meta, then title)
    company_name = (
        meta_info.get('og:site_name') or
        meta_info.get('application-name') or
        company_info.get('title') or
        extract_domain_name(url)
    )
    
    # Get tagline from meta description
    tagline = meta_info.get('description') or meta_info.get('og:description')
    
    # Extract logo
    logo_result = await find_and_download_logo(soup, url)
    
    # Extract colors from logo
    colors = []
    if logo_result and logo_result.get('image_data'):
        colors = extract_colors_from_image(logo_result['image_data'])
    
    # Save to Neo4j
    brand_id = neo4j_client.create_brand(brand_data)
    
    return brand_data
```

### `logo_extractor.py` - Logo Finding

```python
async def find_and_download_logo(soup: BeautifulSoup, base_url: str) -> Optional[Dict]:
    """
    Find and download the best logo from a webpage.
    
    SEARCH ORDER:
    1. Schema.org Organization logo
    2. Open Graph image
    3. <link rel="icon"> or apple-touch-icon
    4. <img> with 'logo' in src/class/alt
    5. SVG with 'logo' in class
    """
    
    logo_candidates = []
    
    # 1. Schema.org Organization
    schema_data = extract_schema_org(soup)
    if schema_data and schema_data.get('logo'):
        logo_candidates.append(('schema', schema_data['logo']))
    
    # 2. Open Graph image
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        logo_candidates.append(('og', og_image['content']))
    
    # 3. Favicon / Apple touch icon
    for link in soup.find_all('link', rel=lambda x: x and 'icon' in x):
        if link.get('href'):
            logo_candidates.append(('favicon', link['href']))
    
    # 4. Images with 'logo' in attributes
    for img in soup.find_all('img'):
        src = img.get('src', '')
        cls = ' '.join(img.get('class', []))
        alt = img.get('alt', '')
        if 'logo' in src.lower() or 'logo' in cls.lower() or 'logo' in alt.lower():
            logo_candidates.append(('img', src))
    
    # Download and evaluate candidates
    best_logo = None
    best_score = 0
    
    for source, url in logo_candidates:
        logo = await download_and_evaluate_logo(url, base_url)
        if logo and logo['quality_score'] > best_score:
            best_logo = logo
            best_score = logo['quality_score']
    
    return best_logo
```

### `color_extractor.py` - Color Analysis

```python
def extract_colors_from_image(image_data: bytes, num_colors: int = 5) -> List[Dict]:
    """
    Extract dominant colors from an image using K-Means clustering.
    
    PROCESS:
    1. Load image and convert to RGB
    2. Resize for performance
    3. Run K-Means clustering
    4. Get cluster centers (dominant colors)
    5. Name colors using nearest named color
    6. Return sorted by dominance
    """
    
    image = Image.open(io.BytesIO(image_data)).convert('RGB')
    
    # Resize for performance
    image = image.resize((150, 150))
    
    # Convert to numpy array
    pixels = np.array(image).reshape(-1, 3)
    
    # K-Means clustering
    kmeans = KMeans(n_clusters=num_colors, random_state=42)
    kmeans.fit(pixels)
    
    # Get dominant colors
    colors = []
    for i, center in enumerate(kmeans.cluster_centers_):
        rgb = tuple(int(c) for c in center)
        hex_code = '#{:02x}{:02x}{:02x}'.format(*rgb)
        name = get_color_name(rgb)
        
        colors.append({
            'hex': hex_code,
            'name': name,
            'rgb': rgb
        })
    
    return colors
```

---

## 4.11 Feedback Learning System

### File: `backend/app/generation/feedback_learning.py`

The feedback learning system implements **continuous preference learning** from user feedback.

### Feedback Types

```python
class FeedbackType(str, Enum):
    LIKE = "like"              # Positive feedback on whole image
    DISLIKE = "dislike"        # Negative feedback on whole image
    ACCEPT = "accept"          # User accepted/downloaded
    REGENERATE = "regenerate"  # User requested regeneration
    EDIT = "edit"              # User made an edit
    ELEMENT_LIKE = "element_like"      # Positive on specific element
    ELEMENT_DISLIKE = "element_dislike"  # Negative on specific element

class FeedbackLevel(str, Enum):
    WHOLE = "whole"        # Entire image
    ELEMENT = "element"    # Specific element
    ATTRIBUTE = "attribute"  # Specific attribute
```

### Feedback Data Structure

```python
@dataclass
class Feedback:
    id: str
    type: FeedbackType
    level: FeedbackLevel
    generation_id: str
    brand_id: str
    element_type: Optional[str] = None  # For element-level
    attribute: Optional[str] = None      # For attribute-level
    old_value: Optional[str] = None      # For edit feedback
    new_value: Optional[str] = None
    comment: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
```

### Preference Aggregation

```python
@dataclass
class AggregatedPreference:
    """An aggregated preference learned from multiple feedback instances"""
    attribute: str  # e.g., 'SUBJECT_lighting', 'global_color_saturation'
    preferred_values: Dict[str, int]  # value -> positive count
    avoided_values: Dict[str, int]    # value -> negative count
    total_samples: int
    confidence: float
    
    def get_top_preference(self) -> Optional[str]:
        """Get the most preferred value."""
        if not self.preferred_values:
            return None
        return max(self.preferred_values, key=self.preferred_values.get)
```

### Learning Integration

Learned preferences are stored in Neo4j and applied during generation:

```cypher
# Create learned preference node
CREATE (lp:LearnedPreference {
    id: $id,
    trigger: $trigger,        # When to apply: "text_position = bottom"
    applies: $applies,        # What to apply: "overlay_opacity = 0.2"
    aspect: $aspect,          # Which aspect: "composition"
    confidence: $confidence,  # 0.0 - 1.0
    created_at: datetime()
})

# Connect to brand
CREATE (b)-[:LEARNED]->(lp)
```

---

# 5. Frontend Deep Dive

## File Structure

```
frontend/src/
├── main.jsx           # Application entry point
├── App.jsx            # Route configuration
├── index.css          # Global styles
├── components/
│   └── Layout.jsx     # Shared layout wrapper
├── pages/
│   ├── Home.jsx       # Landing page
│   ├── Onboarding.jsx # Brand setup wizard
│   ├── OnboardingEnhanced.jsx  # Enhanced onboarding
│   ├── Dashboard.jsx  # Brand dashboard
│   ├── Generate.jsx   # Image generation interface
│   ├── Results.jsx    # Generation results
│   ├── History.jsx    # Past generations
│   └── LinkedIn.jsx   # LinkedIn post generator
└── services/
    └── api.js         # API client
```

## Route Configuration

### File: `frontend/src/App.jsx`

```jsx
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import OnboardingEnhanced from './pages/OnboardingEnhanced'
import Dashboard from './pages/Dashboard'
import Generate from './pages/Generate'
import History from './pages/History'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="onboarding" element={<OnboardingEnhanced />} />
        <Route path="dashboard/:brandId" element={<Dashboard />} />
        <Route path="generate/:brandId" element={<Generate />} />
        <Route path="history/:brandId" element={<History />} />
      </Route>
    </Routes>
  )
}
```

## API Client

### File: `frontend/src/services/api.js`

```javascript
import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 120000, // 2 minutes for AI generation
});

// ============== Brands ==============

export const scrapeBrand = async (websiteUrl) => {
  const response = await api.post('/api/brands/scrape', { website_url: websiteUrl });
  return response.data;
};

export const getBrand = async (brandId) => {
  const response = await api.get(`/api/brands/${brandId}`);
  return response.data;
};

// ============== Brand DNA ==============

export const getBrandDNA = async (brandId) => {
  const response = await api.get(`/api/brand-dna/${brandId}`);
  return response.data;
};

export const generateWithBrandDNA = async (brandId, params) => {
  const response = await api.post(`/api/brand-dna/${brandId}/generate`, params);
  return response.data;
};

// ============== Content Creator ==============

export const discoverTrendingTopics = async (params) => {
  const response = await api.post('/api/content/discover-topics', params);
  return response.data;
};
```

## Generation Page

### File: `frontend/src/pages/Generate.jsx`

The main generation interface with:
- Prompt input
- Text overlay controls (headline, body copy)
- Product/character selection
- Layout preferences
- AI Content Creator integration

```jsx
export default function Generate() {
  const { brandId } = useParams()
  
  // Form state
  const [prompt, setPrompt] = useState('')
  const [headline, setHeadline] = useState('')
  const [bodyCopy, setBodyCopy] = useState('')
  const [textLayout, setTextLayout] = useState('bottom_centered')
  const [includeLogo, setIncludeLogo] = useState(true)
  const [aspectRatio, setAspectRatio] = useState('1:1')
  
  // Generation
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState(null)
  
  const handleGenerate = async () => {
    setGenerating(true)
    
    const data = await generateWithBrandDNA(brandId, {
      prompt,
      headline: headline.trim() || null,
      body_copy: bodyCopy.trim() || null,
      aspect_ratio: aspectRatio,
      text_layout: textLayout,
      include_logo: includeLogo,
      use_reasoning: true
    })
    
    setResult(data)
    setGenerating(false)
  }
  
  return (
    <div>
      <textarea 
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Describe the image you want to generate..."
      />
      
      <input
        value={headline}
        onChange={(e) => setHeadline(e.target.value)}
        placeholder="Headline text"
      />
      
      <input
        value={bodyCopy}
        onChange={(e) => setBodyCopy(e.target.value)}
        placeholder="Body copy text"
      />
      
      <select value={textLayout} onChange={(e) => setTextLayout(e.target.value)}>
        <option value="bottom_centered">Bottom Center</option>
        <option value="top_centered">Top Center</option>
        <option value="center_overlay">Center</option>
        <option value="bottom_left">Bottom Left</option>
      </select>
      
      <button onClick={handleGenerate} disabled={generating}>
        {generating ? 'Generating...' : 'Generate Image'}
      </button>
      
      {result && (
        <img src={result.image_url} alt="Generated" />
      )}
    </div>
  )
}
```

---

# 6. GraphRAG Pipeline Explained

## What is GraphRAG?

**GraphRAG (Graph Retrieval-Augmented Generation)** combines:
1. **Knowledge Graphs**: Structured storage of brand identity
2. **Retrieval**: Query graph for relevant context
3. **Augmentation**: Inject context into generation
4. **Generation**: Create content with full context

## Our Implementation

### Traditional RAG vs Our GraphRAG

| Traditional RAG | Our GraphRAG |
|-----------------|--------------|
| Vector embeddings | Graph structure |
| Document chunks | Entity relationships |
| Semantic similarity | Relationship traversal |
| Flat retrieval | Multi-hop queries |

### Pipeline Steps

```
User Prompt: "Create a social media post for our new product launch"
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: RETRIEVE                                                │
│                                                                 │
│  Query: MATCH (b:Brand {id: $id})                              │
│         OPTIONAL MATCH (b)-[:HAS_COLOR]->(c:ColorNode)         │
│         OPTIONAL MATCH (b)-[:HAS_STYLE]->(s:StyleNode)         │
│         OPTIONAL MATCH (b)-[:SELLS]->(p:ProductNode)           │
│         OPTIONAL MATCH (b)-[:LEARNED]->(lp:LearnedPreference)  │
│         RETURN b, collect(c) as colors, collect(s) as styles,  │
│                collect(p) as products, collect(lp) as prefs    │
│                                                                 │
│  Result: Complete Brand DNA with all relationships             │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: AUGMENT (LLM Planning)                                  │
│                                                                 │
│  Input to LLM:                                                  │
│  - User prompt: "social media post for new product launch"      │
│  - Brand context: colors, styles, products, preferences         │
│                                                                 │
│  LLM Output (GenerationPlan):                                   │
│  {                                                              │
│    "subject": "product showcase",                               │
│    "scene_description": "modern product display with brand...", │
│    "needs_colors": true,                                        │
│    "needs_products": ["New Product X"],                         │
│    "suggested_layout": "centered",                              │
│    "color_strength": 0.8,                                       │
│    "style_strength": 0.7                                        │
│  }                                                              │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: CONDITION                                               │
│                                                                 │
│  Build BrandCondition:                                          │
│  - primary_colors: ["#1a1a1a", "#f0f0f0", "#ff5733"]          │
│  - style_keywords: ["professional", "modern", "clean"]          │
│  - layout: "centered"                                           │
│  - overlay_opacity: 0.2                                         │
│  - product_image_url: "https://..."                            │
│                                                                 │
│  Compile Prompt:                                                │
│  "modern product display with brand colors #1a1a1a dominant,   │
│   professional photography, centered composition, no text..."   │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: GENERATE                                                │
│                                                                 │
│  Call OpenRouter API with:                                      │
│  - Compiled positive prompt                                     │
│  - Negative prompt (no text, no distortion)                    │
│  - Model: google/gemini-2.5-flash-image                        │
│                                                                 │
│  Result: Base64 image data                                      │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: POST-PROCESS                                            │
│                                                                 │
│  5a. Text Overlay (PIL):                                        │
│      - Analyze background color in text region                  │
│      - Calculate contrasting text color                         │
│      - Add gradient overlay for readability                     │
│      - Render headline with shadow                              │
│      - Render body copy                                         │
│                                                                 │
│  5b. Logo Layering (PIL):                                       │
│      - Fetch logo from brand.logo_url                          │
│      - Resize to 12% of image width                            │
│      - Apply 85% opacity                                        │
│      - Composite at bottom-right with padding                  │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: STORE                                                   │
│                                                                 │
│  Create Generation node in Neo4j:                               │
│  CREATE (g:Generation {                                         │
│    id: $generation_id,                                          │
│    prompt: $prompt,                                             │
│    image_url: $image_url,                                       │
│    model_used: $model,                                          │
│    created_at: datetime()                                       │
│  })                                                             │
│  CREATE (b)-[:GENERATED]->(g)                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

# 7. Data Flow Diagrams

## Complete System Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                     │
│                                                                          │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐  │
│  │   Home     │───▶│ Onboarding │───▶│ Dashboard  │───▶│  Generate  │  │
│  │            │    │            │    │            │    │            │  │
│  └────────────┘    └─────┬──────┘    └────────────┘    └─────┬──────┘  │
│                          │                                    │          │
└──────────────────────────┼────────────────────────────────────┼──────────┘
                           │                                    │
                           │ POST /api/brands/scrape            │ POST /api/brand-dna/{id}/generate
                           │                                    │
┌──────────────────────────┼────────────────────────────────────┼──────────┐
│                          ▼                                    ▼          │
│                   ┌──────────────┐                    ┌──────────────┐  │
│                   │ brands.py    │                    │ brand_dna.py │  │
│                   │   Router     │                    │    Router    │  │
│                   └──────┬───────┘                    └──────┬───────┘  │
│                          │                                   │          │
│                          ▼                                   ▼          │
│                   ┌──────────────────────────────────────────────┐      │
│                   │         BrandDNAService                       │      │
│                   │                                               │      │
│                   │  ┌─────────┐  ┌─────────┐  ┌─────────────┐  │      │
│                   │  │get_brand│  │plan_gen │  │generate_img │  │      │
│                   │  │_dna()   │  │_eration()│  │()           │  │      │
│                   │  └────┬────┘  └────┬────┘  └──────┬──────┘  │      │
│                   │       │            │              │          │      │
│                   └───────┼────────────┼──────────────┼──────────┘      │
│                           │            │              │                  │
│                           ▼            ▼              ▼                  │
│                   ┌────────────┐ ┌──────────┐ ┌──────────────┐          │
│                   │ Neo4j      │ │ Groq API │ │ OpenRouter   │          │
│                   │ Client     │ │ (LLM)    │ │ (Image Gen)  │          │
│                   └─────┬──────┘ └──────────┘ └──────────────┘          │
│                         │                                                │
│                    BACKEND                                               │
└─────────────────────────┼────────────────────────────────────────────────┘
                          │
                          ▼
               ┌────────────────────┐
               │    NEO4J AURA      │
               │                    │
               │  (:Brand)          │
               │    │               │
               │    ├─[:HAS_LOGO]─▶(:Logo)
               │    ├─[:HAS_COLOR]─▶(:ColorNode)
               │    ├─[:HAS_STYLE]─▶(:StyleNode)
               │    ├─[:SELLS]─▶(:ProductNode)
               │    └─[:GENERATED]─▶(:Generation)
               │                    │
               └────────────────────┘
```

---

# 8. File-by-File Reference

## Backend Files

| File | Purpose | Key Functions |
|------|---------|---------------|
| `main.py` | FastAPI app entry | `lifespan()`, route registration |
| `config.py` | Environment config | `Settings`, `get_settings()` |
| `neo4j_client.py` | Database client | `create_brand()`, `get_brand()`, `execute_query()` |
| `brand_dna_service.py` | GraphRAG orchestrator | `get_brand_dna()`, `generate_content()` |
| `llm_reasoner.py` | LLM planning | `plan_generation()`, `compile_final_prompt()` |
| `image_generators.py` | Image generation | `generate()`, `generate_with_character()` |
| `text_overlay.py` | Text compositing | `composite_text_on_image()`, `add_logo_to_image()` |
| `feedback_learning.py` | Preference learning | `process_feedback()`, `aggregate_preferences()` |
| `prompt_compiler.py` | Prompt building | `compile_prompt()`, `get_negative_prompt()` |
| `website_scraper.py` | Brand scraping | `scrape_brand_data()` |
| `logo_extractor.py` | Logo finding | `find_and_download_logo()` |
| `color_extractor.py` | Color analysis | `extract_colors_from_image()` |
| `brands.py` | Brand API router | `scrape_website()`, `get_brand()` |
| `brand_dna.py` | Brand DNA router | `get_brand_dna()`, `generate_with_brand_dna()` |
| `content_creator.py` | Content discovery | `discover_trending_topics()` |

## Frontend Files

| File | Purpose | Key Components |
|------|---------|----------------|
| `App.jsx` | Route config | Routes, Layout |
| `api.js` | API client | `scrapeBrand()`, `generateWithBrandDNA()` |
| `Home.jsx` | Landing page | URL input, start onboarding |
| `Onboarding.jsx` | Brand setup | Multi-step wizard |
| `Dashboard.jsx` | Brand overview | Stats, quick actions |
| `Generate.jsx` | Image generation | Prompt input, options, results |
| `History.jsx` | Past generations | Gallery, feedback |
| `Layout.jsx` | Shared layout | Navigation, footer |

---

# Conclusion

This documentation covers the complete architecture of the Brand-Aligned Content Generation Platform:

1. **GraphRAG Implementation**: How we use Neo4j to store brand identity and retrieve it for generation
2. **LLM Reasoning**: How the LLM plans each generation based on brand context
3. **Image Generation**: Multi-provider support with brand conditioning
4. **Text Overlay**: PIL-based compositing for crisp, readable text
5. **Logo Layering**: Configurable logo watermarking with opacity and positioning
6. **Feedback Learning**: Continuous preference learning from user feedback

The system demonstrates that combining **graph databases**, **LLM reasoning**, and **AI image generation** creates a powerful solution for automated, brand-consistent marketing content production.

---

*Document generated for Capstone Project - January 2026*
