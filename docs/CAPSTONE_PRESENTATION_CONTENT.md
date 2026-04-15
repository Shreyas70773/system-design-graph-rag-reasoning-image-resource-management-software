# Capstone Project Presentation Content
## Brand-Aligned Content Generation Platform using GraphRAG
### 12-15 Minutes Presentation

---

## SLIDE 1: Title Slide

**Title:** Brand-Aligned Content Generation Platform using GraphRAG and AI-Powered Image Synthesis

**Subtitle:** Automated Marketing Content Generation with Brand Consistency

**Student Name:** [Your Name]  
**Guide:** [Guide Name]  
**Institution:** [Your Institution]  
**Date:** January 2026

*[Include screenshot of guide approval email]*

---

## SLIDE 2: Introduction (1/2)

### Background & Motivation

**The Challenge in Modern Marketing:**
- Businesses struggle to maintain **brand consistency** across marketing channels
- Creating professional marketing visuals requires expensive design tools and expertise
- Small and medium enterprises (SMEs) lack resources for dedicated design teams
- Manual content creation is **time-consuming** and **error-prone**

**Market Need:**
- Global digital marketing spend exceeded **$600 billion** in 2024
- 73% of companies struggle with brand consistency across platforms
- AI-generated content market projected to reach **$110 billion** by 2030

**Key Insight:**
> "Brand consistency can increase revenue by up to 23%" - Lucidpress Brand Consistency Report

---

## SLIDE 3: Introduction (2/2)

### Why AI-Powered Brand Content Generation?

**Current Limitations:**
| Traditional Approach | Our Solution |
|---------------------|--------------|
| Manual design work | Automated AI generation |
| Expensive software licenses | Web-based platform |
| Requires design expertise | No-code interface |
| Hours per asset | Seconds per asset |
| Inconsistent brand application | Graph-enforced consistency |

**Innovation Opportunity:**
- Combine **Graph Databases** (Neo4j) for brand knowledge storage
- Use **Large Language Models** for intelligent planning
- Leverage **AI Image Generation** for visual creation
- Implement **GraphRAG** (Graph Retrieval-Augmented Generation) for context-aware outputs

**Target Users:**
- Marketing teams at SMEs
- Social media managers
- Brand consultants
- E-commerce businesses

---

## SLIDE 4: Problem Statement

### Core Problem

**"How can we automatically generate marketing visuals that consistently reflect a brand's unique identity, colors, style, and messaging without requiring manual design intervention?"**

**Specific Challenges Addressed:**

1. **Brand Identity Fragmentation**
   - Brand elements scattered across multiple systems
   - No centralized source of truth for brand guidelines

2. **Manual Content Bottleneck**
   - Average 2-4 hours to create a single branded social media post
   - Design teams overwhelmed with repetitive tasks

3. **Inconsistent Brand Application**
   - Different team members interpret brand guidelines differently
   - Platform-specific adaptations lose brand coherence

4. **Limited AI Context Understanding**
   - Generic AI image generators don't understand brand context
   - Results require significant manual correction

**Gap in Existing Solutions:**
- Tools like Canva require manual template selection
- AI generators (Midjourney, DALL-E) lack brand awareness
- No integrated solution combining brand knowledge + AI generation

---

## SLIDE 5: Research Objectives

### Primary Objectives

1. **Design a GraphRAG-based Brand DNA Storage System**
   - Model brand identity as a knowledge graph
   - Store colors, styles, typography, products, and composition preferences
   - Enable semantic retrieval of brand attributes

2. **Develop an Intelligent Prompt Engineering Pipeline**
   - Use LLM reasoning to plan image compositions
   - Translate brand DNA into effective generation prompts
   - Apply learned preferences from user feedback

3. **Implement Multi-Provider AI Image Generation**
   - Integrate with OpenRouter API for model access
   - Support multiple AI providers (Gemini, Stability AI)
   - Build fallback mechanisms for reliability

4. **Create a Post-Processing Compositing System**
   - Add text overlays with brand fonts
   - Apply logo watermarks
   - Ensure consistent visual output

### Secondary Objectives

5. Build an intuitive web-based user interface
6. Implement feedback loop for continuous improvement
7. Support AI-powered content ideation (trending topics)

---

## SLIDE 6: Proposed System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE (React)                    │
│         Dashboard │ Generate │ History │ Onboarding         │
└─────────────────────────────┬───────────────────────────────┘
                              │ REST API
┌─────────────────────────────▼───────────────────────────────┐
│                  FASTAPI BACKEND                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐    │
│  │ Brand DNA   │  │ LLM Reasoner │  │ Image Generator │    │
│  │ Service     │  │ (Groq)       │  │ (OpenRouter)    │    │
│  └──────┬──────┘  └──────┬───────┘  └────────┬────────┘    │
│         │                │                    │              │
│  ┌──────▼────────────────▼────────────────────▼──────┐     │
│  │              GraphRAG Pipeline                      │     │
│  │  Retrieve → Plan → Condition → Generate → Store    │     │
│  └──────────────────────┬─────────────────────────────┘     │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    NEO4J GRAPH DATABASE                      │
│     Brand ──→ Colors, Styles, Products, Preferences          │
│       ↓                                                      │
│   Generations ──→ Feedback ──→ Learned Patterns             │
└─────────────────────────────────────────────────────────────┘
```

**Key Technology Stack:**
- **Frontend:** React 18, Tailwind CSS, Vite
- **Backend:** Python FastAPI, Pydantic
- **Database:** Neo4j Aura (Graph Database)
- **AI Services:** Groq (LLM), OpenRouter (Image Gen), Perplexity (Content Ideas)
- **Image Processing:** PIL/Pillow for compositing

---

## SLIDE 7: System Diagram

### Detailed Data Flow Diagram

```
                              ┌──────────────┐
                              │    User      │
                              └──────┬───────┘
                                     │ 1. Enter Prompt
                                     ▼
┌────────────────────────────────────────────────────────────────┐
│                        GENERATION PIPELINE                      │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐    │
│  │ 1. RETRIEVE │───▶│ 2. PLAN     │───▶│ 3. CONDITION    │    │
│  │ Brand DNA   │    │ LLM Reasoning│   │ Build Prompt    │    │
│  │ from Neo4j  │    │ via Groq    │    │ with Brand DNA  │    │
│  └─────────────┘    └─────────────┘    └────────┬────────┘    │
│                                                  │              │
│  ┌─────────────┐    ┌─────────────┐    ┌────────▼────────┐    │
│  │ 6. STORE    │◀───│ 5. POST-    │◀───│ 4. GENERATE     │    │
│  │ Generation  │    │ PROCESS     │    │ AI Image via    │    │
│  │ + Feedback  │    │ Text+Logo   │    │ OpenRouter      │    │
│  └─────────────┘    └─────────────┘    └─────────────────┘    │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼ 7. Return Result
                              ┌──────────────┐
                              │ Branded Image│
                              │ with Text &  │
                              │ Logo Overlay │
                              └──────────────┘
```

### Graph Database Schema

```
(:Brand {id, name, tagline, logo_url})
    │
    ├──[:HAS_COLOR]──▶ (:Color {hex, name, usage_weight})
    │
    ├──[:HAS_STYLE]──▶ (:Style {type, keywords, negative_keywords})
    │
    ├──[:HAS_PRODUCT]──▶ (:Product {name, description, image_url})
    │
    ├──[:HAS_COMPOSITION]──▶ (:Composition {layout, text_density, overlay})
    │
    └──[:GENERATED]──▶ (:Generation {prompt, image_url, timestamp})
                            │
                            └──[:HAS_FEEDBACK]──▶ (:Feedback {rating, type})
```

---

## SLIDE 8: Modules List (1/4)

### Module 1: Brand DNA Management

**Purpose:** Store and manage brand identity as a knowledge graph

**Components:**
- `neo4j_client.py` - Database connection and queries
- `brand_dna.py` - API routes for brand operations
- `website_scraper.py` - Automatic brand extraction from websites

**Key Features:**
| Feature | Description |
|---------|-------------|
| Brand Onboarding | Scrape website to auto-extract brand elements |
| Color Management | Store hex codes with usage weights |
| Style Profiles | Define visual style keywords and negatives |
| Product Catalog | Link products with images and descriptions |
| Composition Rules | Define layout, text density, overlay preferences |

**API Endpoints:**
```
POST /api/brands/scrape          - Scrape brand from URL
GET  /api/brand-dna/{brand_id}   - Retrieve complete Brand DNA
PUT  /api/brand-dna/{brand_id}   - Update brand attributes
```

**Implementation Status:** ✅ 100% Complete

---

## SLIDE 9: Modules List (2/4)

### Module 2: GraphRAG Pipeline & LLM Reasoning

**Purpose:** Intelligent planning of image generation using brand context

**Components:**
- `llm_reasoner.py` - LLM-based generation planning
- `brand_dna_service.py` - Orchestration of full pipeline
- `prompt_compiler.py` - Dynamic prompt construction

**GraphRAG Process:**
```
1. RETRIEVE: Query Neo4j for relevant brand nodes
   └── Colors, styles, products, past preferences

2. AUGMENT: Inject brand context into LLM prompt
   └── "Given brand colors #1a1a1a, #f0f0f0 and style 'professional'..."

3. GENERATE: LLM creates structured generation plan
   └── {subject, scene, mood, layout, overlay_opacity}
```

**LLM Reasoning Output:**
```json
{
  "subject": "modern office workspace",
  "scene_description": "minimalist desk with laptop",
  "mood": "professional and clean",
  "suggested_layout": "centered",
  "suggested_overlay": 0.2,
  "color_strength": 0.7,
  "style_strength": 0.8
}
```

**Implementation Status:** ✅ 100% Complete

---

## SLIDE 10: Modules List (3/4)

### Module 3: AI Image Generation

**Purpose:** Generate brand-aligned images using AI models

**Components:**
- `image_generators.py` - Multi-provider generation system
- `openrouter_generator.py` - OpenRouter API integration
- `fallback_generator.py` - Reliability with provider fallback

**Supported Providers:**
| Provider | Model | Use Case |
|----------|-------|----------|
| Google | Gemini 2.5 Flash | Fast, cost-effective |
| Stability AI | SDXL | High quality |
| OpenAI | DALL-E 3 | Creative compositions |

**Key Features:**
- **Dynamic Prompt Compilation:** Brand DNA → optimized prompt
- **Negative Prompts:** Exclude unwanted elements (text, watermarks)
- **Fallback System:** Automatic retry with alternate providers
- **Cost Tracking:** Monitor API usage and expenses

**Sample Compiled Prompt:**
```
"a modern office with stainless steel equipment, 
professional photography, high resolution, sharp focus,
brand colors #1a1a1a dominant, centered composition,
photorealistic, no text, no watermarks"
```

**Implementation Status:** ✅ 100% Complete

---

## SLIDE 11: Modules List (4/4)

### Module 4: Post-Processing & Text Overlay

**Purpose:** Apply brand elements to generated images

**Components:**
- `text_overlay.py` - PIL-based text compositing
- `add_logo_to_image()` - Logo watermark placement

**Text Overlay Features:**
- **Dynamic Font Loading:** Support for brand fonts (Montserrat, Playfair, etc.)
- **Auto-Contrast:** Calculate optimal text color based on background
- **Layout Options:** top_centered, bottom_centered, center_overlay
- **Shadow Effects:** Improve readability on complex backgrounds

**Logo Watermark:**
- Configurable position (bottom_right, bottom_left, etc.)
- Adjustable scale (default: 12% of image width)
- Opacity control (default: 85%)

### Module 5: AI Content Creator

**Purpose:** Discover trending topics for content ideation

**Components:**
- `content_creator.py` - Perplexity API integration

**Features:**
- Industry-specific trending topics
- Hashtag suggestions
- Content angle recommendations

**Implementation Status:** ✅ 90% Complete (Logo requires URL in database)

---

## SLIDE 12: Implementation Results (1/2)

### Working Features Demonstration

**1. Brand Onboarding Flow**
- ✅ Website URL scraping
- ✅ Automatic color extraction
- ✅ Logo detection
- ✅ Style profile creation

**2. Image Generation Pipeline**
- ✅ GraphRAG retrieval from Neo4j
- ✅ LLM-based generation planning
- ✅ OpenRouter image generation
- ✅ Sub-10 second generation time

**3. Text Overlay System**
- ✅ Headline text rendering
- ✅ Body copy placement
- ✅ Auto-contrast text colors
- ✅ Multiple layout options

**4. User Interface**
- ✅ Dashboard with brand overview
- ✅ Generate page with prompt input
- ✅ History view for past generations
- ✅ Real-time generation status

### Sample Generated Outputs
*[Include 2-3 screenshots of generated images with text overlays]*

---

## SLIDE 13: Implementation Results (2/2)

### Technical Metrics

| Metric | Value |
|--------|-------|
| Average Generation Time | 8-12 seconds |
| API Success Rate | 95%+ |
| Image Resolution | 1024x1024 |
| Supported Brands | Unlimited |
| Database Response Time | <100ms |

### Code Statistics

| Component | Lines of Code | Files |
|-----------|---------------|-------|
| Backend (Python) | ~5,000 | 25+ |
| Frontend (React) | ~2,500 | 15+ |
| Database Schema | ~200 | 1 |
| **Total** | **~7,700** | **41+** |

### API Endpoints Implemented

| Category | Count |
|----------|-------|
| Brand Management | 6 |
| Generation | 4 |
| Feedback | 3 |
| Content Creator | 2 |
| Health/Utility | 2 |
| **Total** | **17** |

### Technologies Successfully Integrated
- Neo4j Aura (Cloud Graph Database)
- Groq API (LLM Reasoning)
- OpenRouter API (Multi-model Image Generation)
- Perplexity API (Content Discovery)
- FastAPI + React Full-Stack

---

## SLIDE 14: Conclusion & Future Work

### Key Achievements

1. ✅ Successfully implemented GraphRAG pipeline for brand-aware generation
2. ✅ Integrated multiple AI providers with fallback reliability
3. ✅ Built complete full-stack application with modern technologies
4. ✅ Achieved sub-15 second end-to-end generation time

### Limitations

- Logo requires manual URL entry (auto-upload planned)
- Limited to single image generation (batch planned)
- Font selection limited to pre-defined options

### Future Enhancements

1. **Multi-Image Campaigns:** Generate coordinated sets
2. **A/B Testing:** Compare generation variations
3. **Analytics Dashboard:** Track brand consistency metrics
4. **Video Generation:** Extend to short-form video content
5. **API Access:** Enable third-party integrations

### Conclusion

> The Brand-Aligned Content Generation Platform demonstrates that combining Graph Databases with AI Generation creates a powerful solution for automated, brand-consistent marketing content production.

---

## SLIDE 15: Q&A

### Thank You

**Questions?**

**Project Repository:** [GitHub Link]

**Contact:** [Your Email]

**Technologies Used:**
`Python` `FastAPI` `React` `Neo4j` `Groq` `OpenRouter` `Tailwind CSS`

---

## Appendix: Demo Script (for presentation)

1. **Show Dashboard** (30 sec) - Explain brand overview
2. **Navigate to Generate** (30 sec) - Show prompt input
3. **Enter Sample Prompt** (30 sec) - "A modern product showcase"
4. **Add Text Overlay** (30 sec) - Fill headline and body copy
5. **Generate Image** (60 sec) - Show real-time progress
6. **Review Result** (60 sec) - Explain how brand DNA influenced output
7. **Show History** (30 sec) - Demonstrate past generations

**Total Demo Time: ~5 minutes**

---

*Document prepared for Capstone Presentation - January 2026*
