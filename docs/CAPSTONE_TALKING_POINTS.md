# Capstone Talking Points
## Brand-Aligned Content Generation with GraphRAG

---

## 1. Problem Statement

**The Challenge:** Marketing teams need to generate brand-consistent visual content at scale, but:
- Generic AI image generators ignore brand guidelines
- Manual brand enforcement is slow and expensive
- No memory of what worked/didn't work in the past
- Inconsistent character/product representation across campaigns

**Our Solution:** A GraphRAG-powered system that learns and enforces brand identity automatically.

---

## 2. Technical Architecture (Key Innovation)

### 2.1 Knowledge Graph Schema (Neo4j)
```
(Brand)──[:HAS_COLOR]──>(Color {hex, name, role})
       ──[:HAS_STYLE]──>(Style {type, keywords})
       ──[:HAS_COMPOSITION]──>(Composition {layout, text_position})
       ──[:SELLS]──>(Product {name, image_url, category})
       ──[:HAS_CHARACTER]──>(Character {name, reference_image})
       ──[:LEARNED]──>(LearnedPreference {trigger, action, confidence})
       ──[:GENERATED]──>(Generation {prompt, result, feedback})
```

### 2.2 The GraphRAG Pipeline
```
User Prompt → Graph Retrieval → LLM Planning → Prompt Conditioning → Image Generation
                    ↑                                                        ↓
                    └──────────────── Semantic Feedback ←────────────────────┘
```

### 2.3 Semantic Feedback Loop
- Users provide structured feedback (rating + aspects)
- LLM analyzes feedback to extract patterns
- Patterns stored as LearnedPreference nodes
- Future generations query applicable preferences
- **The system improves with use**

---

## 3. Research Contributions

### 3.1 Novel Aspects
1. **Brand DNA as Knowledge Graph**: First system to model brand identity as queryable graph relationships
2. **Semantic Feedback → Graph Updates**: Feedback isn't just stored, it's transformed into actionable graph patterns
3. **Multi-modal Conditioning Pipeline**: Text + Color + Style + Product Image + Character Face → Unified Generation

### 3.2 Literature Connections
- **GraphRAG** (Microsoft 2024): We extend retrieval to multi-modal generation
- **IP-Adapter** (Ye et al.): Product image conditioning approach
- **PuLID**: Character face consistency technique
- **ControlNet**: Composition guidance methodology

---

## 4. Implementation Scope

### 4.1 Completed (Current Prototype - ~60%)
| Component | Status | Description |
|-----------|--------|-------------|
| Neo4j Knowledge Graph | ✅ Complete | Full schema with all node types |
| Brand Scraping | ✅ Complete | Extracts logo, colors, name from websites |
| GraphRAG Retrieval | ✅ Complete | Queries graph for generation context |
| LLM Planning Stage | ✅ Complete | GPT-4o-mini plans generation parameters |
| Prompt Conditioning | ✅ Complete | Compiles brand DNA into prompts |
| Multi-Provider Generation | ✅ Complete | Gemini, Replicate, fal.ai with fallback |
| Semantic Feedback API | ✅ Complete | Structured feedback collection |
| Live Graph Visualization | ✅ Complete | Real-time knowledge graph UI |
| Product/Character Selection | ✅ Complete | Reference images for conditioning |

### 4.2 Future Work (Documented Architecture - 40%)
| Component | Status | Description |
|-----------|--------|-------------|
| LoRA Fine-tuning | 📋 Designed | Brand-specific model weights |
| IP-Adapter Integration | 📋 Designed | Product embedding at cross-attention |
| PuLID Face Consistency | 📋 Designed | Character face embedding injection |
| ControlNet Composition | 📋 Designed | Layout and pose guidance |
| ComfyUI Pipeline | 📋 Designed | Self-hosted diffusion control |

---

## 5. Evaluation Metrics (For Presentation)

### 5.1 Quantitative
- **Brand Consistency Score**: % of generations matching brand colors/style
- **Feedback Loop Improvement**: Positive rating % over time
- **Generation Latency**: Time from prompt to image
- **Cost per Generation**: API costs across providers

### 5.2 Qualitative
- User study: "Does this look like [Brand]'s marketing?"
- A/B test: GraphRAG-conditioned vs baseline prompts
- Expert review: Marketing professionals assess outputs

---

## 6. Key Talking Points for Defense

### "Why a Knowledge Graph instead of Vector DB?"
> "Vector databases excel at semantic similarity, but brand identity has **explicit relationships**. A color isn't just 'similar' to a brand—it IS the primary color, WITH a specific role. Graph relationships capture this structure naturally and allow complex queries like 'get all learned preferences that apply when text_position=centered'."

### "How is this different from just prompting?"
> "Pure prompting has no memory and no enforcement. Our system:
> 1. **Retrieves** brand context from the graph
> 2. **Plans** generation with an LLM reasoning stage  
> 3. **Conditions** the prompt with structured brand DNA
> 4. **Learns** from feedback to improve future generations
> This creates a closed loop that traditional prompting cannot achieve."

### "What about diffusion-level control?"
> "The current prototype demonstrates the **retrieval and planning** stages of GraphRAG. The architecture is designed to extend to diffusion-level control via IP-Adapter (product embeddings), PuLID (face embeddings), and ControlNet (composition). These would inject conditioning at the UNet cross-attention layers rather than just text. We've documented this architecture for future implementation."

### "What's the research contribution?"
> "Three contributions:
> 1. A novel graph schema for brand identity representation
> 2. A semantic feedback mechanism that updates the knowledge graph
> 3. A multi-stage pipeline connecting GraphRAG to multi-modal generation"

---

## 7. Demo Flow

1. **Onboarding**: Scrape website → Show live graph building
2. **Brand DNA Review**: Display extracted colors, logo, add products
3. **Generation**: Enter prompt → Show LLM planning → Generate image
4. **Feedback**: Rate the image → Show graph update with learned preference
5. **Improved Generation**: Generate again → Show how learned preference affects output

---

## 8. Technology Stack

| Layer | Technology | Justification |
|-------|------------|---------------|
| Frontend | React + Vite | Fast development, component-based |
| Backend | FastAPI (Python) | Async support, Pydantic validation |
| Database | Neo4j Aura | Native graph queries, cloud-managed |
| LLM | OpenAI GPT-4o-mini | Cost-effective reasoning |
| Image Gen | Gemini / Replicate | Multi-provider resilience |
| Visualization | Custom SVG | Real-time graph animation |

---

## 9. Limitations & Honest Assessment

### Current Limitations
1. **Prompt-level conditioning only**: True diffusion control requires self-hosting
2. **Text rendering**: AI models struggle with legible text in images
3. **Face consistency**: Without PuLID, character faces vary between generations
4. **Product accuracy**: Without IP-Adapter, products may not match exactly

### Why This is Still Valuable
> "The architecture demonstrates the **full GraphRAG pipeline**. The limitation is in the image generation backend (API-based), not the retrieval, planning, or feedback systems. Swapping to a self-hosted ComfyUI pipeline would enable diffusion-level control with the same GraphRAG front-end."

---

## 10. Conclusion

This capstone demonstrates:
1. ✅ **Systems Design**: Multi-service architecture with fallback
2. ✅ **Database Design**: Novel graph schema for brand identity
3. ✅ **ML Pipeline**: GraphRAG retrieval → LLM planning → Generation
4. ✅ **Feedback Systems**: Semantic analysis → Graph updates
5. ✅ **Full-Stack Development**: React frontend, FastAPI backend
6. ✅ **Research Awareness**: Grounded in current literature (GraphRAG, IP-Adapter, etc.)

**The 60/40 split is intentional**: Fully implementing diffusion-level control requires GPU infrastructure and extensive training. The documented architecture shows understanding while the prototype demonstrates the GraphRAG core.
