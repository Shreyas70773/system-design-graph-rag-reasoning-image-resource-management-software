# Capstone Presentation Slide Content
## Brand-Aligned Content Generation Platform with GraphRAG

> **NOTE**: One slide per module with key technical points.

---

# MODULE 1: Brand DNA Management

**Title**: Automated Brand Identity Extraction & Storage

**Key Points**:
- **Web Scraping**: BeautifulSoup parses HTML DOM; multi-strategy logo detection (schema.org → og:image → favicon → img tags)
- **Color Extraction**: ColorThief uses Modified Median Cut quantization; color naming via Euclidean distance in RGB space: `√[(R₁-R₂)² + (G₁-G₂)² + (B₁-B₂)²]`
- **Logo Quality Scoring**: `Score = (Resolution × 0.6) + (Size × 0.4)` where 200px+ = 1.0
- **Neo4j Schema**: Brand → [:HAS_LOGO] → Logo, [:HAS_COLOR] → ColorNode, [:HAS_STYLE] → StyleNode, [:LEARNED] → LearnedPreference
- **Learning**: Feedback → LLM analysis → CREATE LearnedPreference node; Confidence = `(sample_factor × 0.4) + (consistency × 0.6)`

---

# MODULE 2: GraphRAG Pipeline & LLM Reasoning

**Title**: 6-Step Generation Pipeline

**Key Points**:
1. **RETRIEVE**: Single Cypher query traverses ALL relationships (colors, styles, preferences) - O(1) vs 6+ JOINs in SQL
2. **PLAN (LLM)**: Groq Llama 3.3 70B analyzes prompt → outputs GenerationPlan with reasoning steps
3. **BUILD CONDITIONING**: BrandDNA.to_brand_condition() maps graph data to generation parameters
4. **COMPILE PROMPT**: Merge user_prompt + brand_context + quality boosters + "no text" directive
5. **GENERATE**: OpenRouter API (Gemini 2.5 Flash)
6. **POST-PROCESS**: PIL text overlay + logo composite → Store Generation node

**Why LLM Planning**: Context-aware decisions, dynamic composition, explainable reasoning traces

---

# MODULE 3: AI Image Generation

**Title**: Prompt Compilation & Future Architecture

**Key Points**:
- **4-Layer Prompt**: Base (user intent) + Brand (style/colors) + Quality (8k, sharp) + Control ("no text, no letters")
- **Negative Prompts**: Quality (blurry, pixelated), Anatomy (deformed), Text (watermark), Composition (cropped)
- **Current (v1)**: OpenRouter API - prompt-level conditioning only (model interprets loosely)
- **Future (v2)**: Self-hosted ComfyUI with diffusion-level control:
  - UNet: Brand LoRAs, Color ControlNet
  - Cross-Attention: IP-Adapter (product reference)
  - Face Embedding: PuLID/InstantID (character consistency)

---

# MODULE 4: Post-Processing & Compositing

**Title**: PIL-Based Text & Logo Layering

**Key Points**:
- **Text Overlay Pipeline**:
  1. Analyze dominant color in text region (crop → resize 50×50 → getcolors())
  2. Luminance contrast: `L = (0.299R + 0.587G + 0.114B)/255` → WHITE if L<0.5, else BLACK
  3. Gradient overlay: 0→180 alpha for readability
  4. Shadow offset 3-4px, font size 8% (headline) / 4% (body) of image height
- **Logo Compositing**:
  - Scale: 12% of image width, maintain aspect ratio
  - Resize with LANCZOS resampling
  - Apply opacity via alpha channel: `alpha.point(lambda p: int(p * 0.9))`
  - Position: `pos_x = width - logo_w - (width × 0.03)`

---

# MODULE 5: AI Content Discovery

**Title**: Perplexity-Powered Trend Intelligence

**Key Points**:
- **API**: Perplexity Sonar model (optimized for real-time web search with citations)
- **3-Phase Pipeline**:
  1. **Discover**: Search trending topics by industry/focus areas → TrendingTopic[]
  2. **Ideate**: Generate content ideas with hooks, key points, CTAs
  3. **Generate**: Full content with hashtags and variations
- **System Prompt**: Brand profile (industry, values, products) + target audience + content goal → structured JSON output with engagement potential scoring

---

# MODULE 6: Future Roadmap

**Title**: Planned Enhancements

**Key Points**:
- **Product Relationships**:
  - Current: `(Brand)-[:SELLS]->(Product)`
  - Planned: `(Product)-[:BELONGS_TO]->(Category)`, `(Product)-[:RELATED_TO]->(Product)`
- **Feedback Traceability**:
  - Planned: `(LearnedPreference)-[:AFFECTS]->(ColorNode)`, `(LearnedPreference)-[:DERIVED_FROM]->(Generation)`
- **Diffusion Control**: ComfyUI with Brand LoRAs (UNet) + IP-Adapter (cross-attention) + ControlNet (colors) + PuLID (faces)

---

# CONCLUSION

**Title**: Key Achievements & Contributions

**What We Built**:
- GraphRAG architecture with Neo4j knowledge graph for brand identity
- LLM reasoning layer (Groq) for context-aware generation planning
- Multi-model integration: OpenRouter (images), Perplexity (content), Groq (reasoning)
- PIL-based post-processing for crisp text and logo compositing
- Continuous learning via feedback → preference pipeline

**Research Contributions**:
1. Graph-native brand modeling with relationship traversal
2. "Think first" LLM planning with explainable reasoning
3. Hybrid pipeline: AI generation + pixel-perfect PIL compositing
4. Confidence-scored graph learning with negative pattern detection

**Metrics**: Brand onboarding ~5s | Generation ~15-30s | Graph query <50ms

---

*Document prepared for Capstone Presentation - January 2026*
