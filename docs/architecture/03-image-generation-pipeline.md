# Reasoning-Augmented Image Generation Pipeline
## Brand-Consistent Visual Content Synthesis

**Version**: 1.0  
**Date**: January 2026  
**Component**: Reasoning Agent + Image Generation Agent

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Phase 1: Graph-Conditioned Reasoning](#phase-1-graph-conditioned-reasoning)
3. [Phase 2: Constraint-Guided Generation](#phase-2-constraint-guided-generation)
4. [Phase 3: Validation & Refinement](#phase-3-validation--refinement)
5. [Training Strategy](#training-strategy)
6. [Inference Optimization](#inference-optimization)
7. [Brand Consistency Mechanisms](#brand-consistency-mechanisms)

---

## Architecture Overview

### Core Insight: Reasoning Reduces Generation Entropy

From information theory, conditioning on explicit reasoning reduces uncertainty:

$$H(X \mid \tilde{S}, c) \leq H(X \mid c)$$

Where:
- $X$ = Generated image
- $\tilde{S}$ = Reasoning tokens (thought images, layout plans)
- $c$ = Text prompt + graph context

By generating **explicit planning tokens** before pixel synthesis, we:
1. Decompose complex brand constraints into spatial layouts
2. Bind graph entities to image regions deterministically
3. Enable human-interpretable generation traces

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                      REASONING-AUGMENTED IMAGE GENERATION PIPELINE                       │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                              INPUT ASSEMBLY                                       │   │
│  │                                                                                   │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │   │
│  │  │ User Prompt │    │   Graph     │    │  Reference  │    │   Brand     │       │   │
│  │  │             │    │  Context    │    │   Images    │    │ Constraints │       │   │
│  │  │ "Product    │    │ (from       │    │ (logo,      │    │ (colors,    │       │   │
│  │  │  launch     │    │  GraphRAG)  │    │  motifs)    │    │  rules)     │       │   │
│  │  │  image"     │    │             │    │             │    │             │       │   │
│  │  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘       │   │
│  │         │                  │                  │                  │              │   │
│  │         └──────────────────┴──────────────────┴──────────────────┘              │   │
│  │                                       │                                          │   │
│  │                                       ▼                                          │   │
│  │                            ┌─────────────────────┐                              │   │
│  │                            │   Input Encoder     │                              │   │
│  │                            │   (Multi-Modal)     │                              │   │
│  │                            │                     │                              │   │
│  │                            │ • Text: T5-XXL      │                              │   │
│  │                            │ • Image: SigLIP     │                              │   │
│  │                            │ • Graph: GNN        │                              │   │
│  │                            └──────────┬──────────┘                              │   │
│  │                                       │                                          │   │
│  └───────────────────────────────────────┼──────────────────────────────────────────┘   │
│                                          │                                               │
│                                          ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                         PHASE 1: REASONING (THINKER)                              │   │
│  │                                                                                   │   │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐  │   │
│  │  │                      Reasoning Transformer                                  │  │   │
│  │  │                                                                             │  │   │
│  │  │   Input: [TEXT_EMB | GRAPH_EMB | REF_IMG_EMB]                              │  │   │
│  │  │                                                                             │  │   │
│  │  │   Output:                                                                   │  │   │
│  │  │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │  │   │
│  │  │   │  Thought Image  │  │  Layout Tokens  │  │ Binding Tokens  │           │  │   │
│  │  │   │  (64x64 sketch) │  │  (region specs) │  │ (entity→region) │           │  │   │
│  │  │   │                 │  │                 │  │                 │           │  │   │
│  │  │   │  Low-res        │  │  [{region: A,   │  │  {logo: R1,     │           │  │   │
│  │  │   │  compositional  │  │    x: 0.1,      │  │   product: R2,  │           │  │   │
│  │  │   │  preview        │  │    y: 0.05,     │  │   palette: ALL} │           │  │   │
│  │  │   │                 │  │    w: 0.2,      │  │                 │           │  │   │
│  │  │   │  512 tokens     │  │    h: 0.15,     │  │  128 tokens     │           │  │   │
│  │  │   │  (VAE latent)   │  │    type: logo}] │  │                 │           │  │   │
│  │  │   │                 │  │                 │  │                 │           │  │   │
│  │  │   │                 │  │  256 tokens     │  │                 │           │  │   │
│  │  │   └─────────────────┘  └─────────────────┘  └─────────────────┘           │  │   │
│  │  │                                                                             │  │   │
│  │  └────────────────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                                   │   │
│  │  Mathematical Formulation:                                                       │   │
│  │  P(S | c, G) = ∏_{t=1}^{T_s} P(s_t | s_{<t}, c, G)                              │   │
│  │                                                                                   │   │
│  │  Where:                                                                          │   │
│  │  • S = reasoning tokens (thought image + layout + bindings)                     │   │
│  │  • c = text prompt                                                              │   │
│  │  • G = graph context (constraints, references)                                  │   │
│  │  • T_s = reasoning sequence length (~896 tokens)                                │   │
│  │                                                                                   │   │
│  └────────────────────────────────────────────────┬─────────────────────────────────┘   │
│                                                   │                                      │
│                                                   ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                      PHASE 2: GENERATION (EXECUTOR)                               │   │
│  │                                                                                   │   │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐  │   │
│  │  │                      Generation Transformer                                 │  │   │
│  │  │                                                                             │  │   │
│  │  │   Input: [REASONING_TOKENS | TEXT_EMB | GRAPH_CONSTRAINTS]                 │  │   │
│  │  │                                                                             │  │   │
│  │  │   ┌─────────────────────────────────────────────────────────────────────┐  │  │   │
│  │  │   │              Autoregressive Image Token Generation                   │  │  │   │
│  │  │   │                                                                      │  │  │   │
│  │  │   │   ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐       ┌─────┐            │  │  │   │
│  │  │   │   │ t_1 │→│ t_2 │→│ t_3 │→│ t_4 │→│ ... │→ ... →│t_4096│           │  │  │   │
│  │  │   │   └─────┘ └─────┘ └─────┘ └─────┘ └─────┘       └─────┘            │  │  │   │
│  │  │   │                                                                      │  │  │   │
│  │  │   │   Codebook: 16,384 visual tokens (SDXL VAE vocabulary)              │  │  │   │
│  │  │   │   Resolution: 1024x1024 → 64x64 latent → 4096 tokens               │  │  │   │
│  │  │   │   Generation order: Raster scan (top-left to bottom-right)          │  │  │   │
│  │  │   │                                                                      │  │  │   │
│  │  │   └─────────────────────────────────────────────────────────────────────┘  │  │   │
│  │  │                                                                             │  │   │
│  │  │   Cross-Attention Injection Points:                                        │  │   │
│  │  │   • Thought image → global composition guidance                            │  │   │
│  │  │   • Layout tokens → regional attention masks                               │  │   │
│  │  │   • Binding tokens → entity-specific constraints                           │  │   │
│  │  │                                                                             │  │   │
│  │  └────────────────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                                   │   │
│  │  Mathematical Formulation:                                                       │   │
│  │  P(X | S, c, G) = ∏_{t=1}^{T_x} P(x_t | x_{<t}, S, c, G)                        │   │
│  │                                                                                   │   │
│  │  Where:                                                                          │   │
│  │  • X = image tokens (4096 tokens for 1024x1024)                                 │   │
│  │  • S = reasoning tokens from Phase 1                                            │   │
│  │  • Attention mask M(t) = f(layout_tokens, current_position_t)                   │   │
│  │                                                                                   │   │
│  └────────────────────────────────────────────────┬─────────────────────────────────┘   │
│                                                   │                                      │
│                                                   ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                      PHASE 3: VALIDATION & REFINEMENT                             │   │
│  │                                                                                   │   │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐  │   │
│  │  │                      Constraint Validator                                   │  │   │
│  │  │                                                                             │  │   │
│  │  │   Checks:                                                                   │  │   │
│  │  │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │  │   │
│  │  │   │ Instance-Level  │  │ Attribute-Level │  │ Relational      │           │  │   │
│  │  │   │                 │  │                 │  │                 │           │  │   │
│  │  │   │ • Logo pixel    │  │ • Color within  │  │ • Required      │           │  │   │
│  │  │   │   match (SSIM)  │  │   ±5% of brand  │  │   elements      │           │  │   │
│  │  │   │ • Product       │  │   palette       │  │   present       │           │  │   │
│  │  │   │   recognition   │  │ • Typography    │  │ • Prohibited    │           │  │   │
│  │  │   │   (CLIP)        │  │   style match   │  │   combinations  │           │  │   │
│  │  │   │                 │  │ • Composition   │  │   absent        │           │  │   │
│  │  │   │ Threshold: 0.95 │  │   adherence     │  │                 │           │  │   │
│  │  │   │                 │  │                 │  │ Threshold: 1.0  │           │  │   │
│  │  │   │                 │  │ Threshold: 0.85 │  │ (binary)        │           │  │   │
│  │  │   └─────────────────┘  └─────────────────┘  └─────────────────┘           │  │   │
│  │  │                                                                             │  │   │
│  │  └────────────────────────────────────────────────────────────────────────────┘  │   │
│  │                                       │                                          │   │
│  │                                       ▼                                          │   │
│  │                              ┌─────────────────┐                                 │   │
│  │                              │ Pass/Fail?      │                                 │   │
│  │                              └────────┬────────┘                                 │   │
│  │                                       │                                          │   │
│  │                    ┌──────────────────┴──────────────────┐                      │   │
│  │                    │                                     │                      │   │
│  │                    ▼                                     ▼                      │   │
│  │           ┌─────────────────┐                   ┌─────────────────┐            │   │
│  │           │      PASS       │                   │      FAIL       │            │   │
│  │           │                 │                   │                 │            │   │
│  │           │ → Output image  │                   │ → Refinement    │            │   │
│  │           │ → Log lineage   │                   │   loop (max 3)  │            │   │
│  │           │ → Update perf   │                   │ → Regenerate    │            │   │
│  │           │   metrics       │                   │   failed region │            │   │
│  │           └─────────────────┘                   └─────────────────┘            │   │
│  │                                                                                   │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Graph-Conditioned Reasoning

### Reasoning Token Types

#### 1. Thought Images (Visual Planning)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        THOUGHT IMAGE GENERATION                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Purpose: Generate low-resolution compositional sketches that:              │
│  • Establish global layout and structure                                    │
│  • Pre-allocate regions for brand elements                                  │
│  • Reduce generation entropy by providing coarse guidance                   │
│                                                                              │
│  Format: 64x64 pixels → 512 VAE latent tokens                               │
│                                                                              │
│  Generation Process:                                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  Input: "Product launch image for eco-friendly water bottle"         │   │
│  │         + Graph context (brand colors, logo, sustainability motif)   │   │
│  │                                                                       │   │
│  │                         │                                             │   │
│  │                         ▼                                             │   │
│  │                                                                       │   │
│  │  Thought Image 1       Thought Image 2       Thought Image 3         │   │
│  │  (Centered Product)    (Hero Shot)          (Lifestyle Context)      │   │
│  │  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐        │   │
│  │  │  [LOGO]      │      │              │      │    ☀️         │        │   │
│  │  │              │      │   ┌──────┐   │      │  ┌──────┐     │        │   │
│  │  │   ┌──────┐   │      │   │      │   │      │  │      │ 🌿  │        │   │
│  │  │   │BOTTLE│   │      │   │BOTTLE│   │      │  │BOTTLE│     │        │   │
│  │  │   │      │   │      │   │      │   │      │  └──────┘     │        │   │
│  │  │   └──────┘   │      │   └──────┘   │      │       🌊      │        │   │
│  │  │              │      │  [TAGLINE]   │      │  [TAGLINE]    │        │   │
│  │  │  [TAGLINE]   │      │  [LOGO]      │      │    [LOGO]     │        │   │
│  │  └──────────────┘      └──────────────┘      └──────────────┘        │   │
│  │                                                                       │   │
│  │  Selection: Based on brand guidelines (prefer centered for products) │   │
│  │             → Select Thought Image 1                                  │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Token Representation:                                                       │
│  [THOUGHT_START] [v_1, v_2, ..., v_512] [THOUGHT_END]                       │
│                                                                              │
│  Where v_i ∈ {0, 1, ..., 8191} (8K codebook for low-res)                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 2. Layout Tokens (Spatial Planning)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LAYOUT TOKEN STRUCTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Purpose: Define precise spatial regions for each content element           │
│                                                                              │
│  Token Grammar:                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  [LAYOUT_START]                                                      │   │
│  │    [REGION_START]                                                    │   │
│  │      [TYPE: logo | product | text | background | decoration]         │   │
│  │      [X: 0.00-1.00]  // normalized x-coordinate                      │   │
│  │      [Y: 0.00-1.00]  // normalized y-coordinate                      │   │
│  │      [W: 0.00-1.00]  // normalized width                             │   │
│  │      [H: 0.00-1.00]  // normalized height                            │   │
│  │      [PRIORITY: 1-5] // rendering order (1 = front)                  │   │
│  │      [CONSTRAINT_REF: entity_id | null]                              │   │
│  │    [REGION_END]                                                      │   │
│  │    ... (repeat for each region)                                      │   │
│  │  [LAYOUT_END]                                                        │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Example (Product Launch Image):                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  [LAYOUT_START]                                                      │   │
│  │    [REGION: logo,     x=0.05, y=0.02, w=0.15, h=0.08, p=1, ref=L001]│   │
│  │    [REGION: product,  x=0.25, y=0.20, w=0.50, h=0.55, p=2, ref=P042]│   │
│  │    [REGION: tagline,  x=0.10, y=0.80, w=0.80, h=0.10, p=1, ref=T003]│   │
│  │    [REGION: bg_color, x=0.00, y=0.00, w=1.00, h=1.00, p=5, ref=C001]│   │
│  │    [REGION: accent,   x=0.70, y=0.15, w=0.25, h=0.25, p=3, ref=M002]│   │
│  │  [LAYOUT_END]                                                        │   │
│  │                                                                       │   │
│  │  Visual representation:                                               │   │
│  │  ┌────────────────────────────────────────────────────────────┐      │   │
│  │  │ [LOGO]                                        ┌─────────┐ │      │   │
│  │  │                                               │ ACCENT  │ │      │   │
│  │  │            ┌────────────────────┐             │ MOTIF   │ │      │   │
│  │  │            │                    │             └─────────┘ │      │   │
│  │  │            │                    │                         │      │   │
│  │  │            │     PRODUCT        │                         │      │   │
│  │  │            │                    │                         │      │   │
│  │  │            │                    │                         │      │   │
│  │  │            └────────────────────┘                         │      │   │
│  │  │                                                           │      │   │
│  │  │    [           TAGLINE TEXT GOES HERE            ]       │      │   │
│  │  └────────────────────────────────────────────────────────────┘      │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Token Count: ~256 tokens (variable based on complexity)                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 3. Binding Tokens (Entity-Region Mapping)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        BINDING TOKEN STRUCTURE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Purpose: Explicitly map graph entities to layout regions                   │
│           Enable constraint verification post-generation                     │
│                                                                              │
│  Token Grammar:                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  [BINDING_START]                                                     │   │
│  │    [ENTITY_ID] -> [REGION_ID] : [BINDING_TYPE] : [PARAMETERS]       │   │
│  │  [BINDING_END]                                                       │   │
│  │                                                                       │   │
│  │  Binding Types:                                                       │   │
│  │  • EXACT_MATCH: Pixel-perfect reproduction (logos, icons)            │   │
│  │  • STYLE_TRANSFER: Apply visual style (motifs, patterns)             │   │
│  │  • COLOR_FILL: Apply color from palette (backgrounds)                │   │
│  │  • SEMANTIC_GUIDE: Guide content semantically (products, text)       │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Example:                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  [BINDING_START]                                                     │   │
│  │    logo:L001 -> region:R1 : EXACT_MATCH : {                         │   │
│  │      source_uri: "s3://brand/logos/primary.png",                    │   │
│  │      min_size: 80px,                                                 │   │
│  │      clear_space: 10px,                                              │   │
│  │      verification: SSIM > 0.95                                       │   │
│  │    }                                                                  │   │
│  │                                                                       │   │
│  │    product:P042 -> region:R2 : SEMANTIC_GUIDE : {                   │   │
│  │      reference_images: ["s3://products/bottle_hero.png"],           │   │
│  │      description: "eco-friendly water bottle, matte green",         │   │
│  │      verification: CLIP_similarity > 0.80                            │   │
│  │    }                                                                  │   │
│  │                                                                       │   │
│  │    palette:C001 -> region:R4 : COLOR_FILL : {                       │   │
│  │      colors: ["#2E7D32", "#A5D6A7"],                                │   │
│  │      gradient_type: "radial",                                        │   │
│  │      verification: color_distance < 15 (CIEDE2000)                   │   │
│  │    }                                                                  │   │
│  │                                                                       │   │
│  │    motif:M002 -> region:R5 : STYLE_TRANSFER : {                     │   │
│  │      style_reference: "s3://brand/motifs/leaf_pattern.png",         │   │
│  │      intensity: 0.7,                                                 │   │
│  │      verification: style_similarity > 0.75                           │   │
│  │    }                                                                  │   │
│  │  [BINDING_END]                                                       │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Token Count: ~128 tokens (variable based on bindings)                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Reasoning Model Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     REASONING TRANSFORMER ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Model: Custom Transformer (1.3B parameters)                                │
│  Base: LLaMA architecture with visual token vocabulary extension            │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  Input Embedding Layer                                               │   │
│  │  ├── Text Embeddings: 32K vocab (LLaMA tokenizer)                   │   │
│  │  ├── Visual Embeddings: 8K vocab (thought image codebook)           │   │
│  │  ├── Layout Embeddings: 1K vocab (spatial tokens)                   │   │
│  │  ├── Binding Embeddings: 512 vocab (entity types + operators)       │   │
│  │  └── Graph Embeddings: Projected from GNN (256-dim → 4096-dim)      │   │
│  │                                                                       │   │
│  │  Total Vocabulary: ~42K tokens                                       │   │
│  │  Embedding Dimension: 4096                                           │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  Transformer Blocks (24 layers)                                      │   │
│  │                                                                       │   │
│  │  ┌────────────────────────────────────────────────────────────────┐  │   │
│  │  │  Layer N                                                        │  │   │
│  │  │  ┌──────────────────────────────────────────────────────────┐  │  │   │
│  │  │  │  Multi-Head Self-Attention (32 heads, 128 dim/head)      │  │  │   │
│  │  │  │  + RoPE positional encoding                               │  │  │   │
│  │  │  │  + Causal mask (autoregressive)                           │  │  │   │
│  │  │  └──────────────────────────────────────────────────────────┘  │  │   │
│  │  │                          │                                      │  │   │
│  │  │                          ▼                                      │  │   │
│  │  │  ┌──────────────────────────────────────────────────────────┐  │  │   │
│  │  │  │  Cross-Attention to Graph Context (8 heads)              │  │  │   │
│  │  │  │  Q: hidden states, K/V: graph node embeddings            │  │  │   │
│  │  │  │  (Only on layers 4, 8, 12, 16, 20, 24)                   │  │  │   │
│  │  │  └──────────────────────────────────────────────────────────┘  │  │   │
│  │  │                          │                                      │  │   │
│  │  │                          ▼                                      │  │   │
│  │  │  ┌──────────────────────────────────────────────────────────┐  │  │   │
│  │  │  │  Feed-Forward Network (SwiGLU activation)                │  │  │   │
│  │  │  │  Hidden: 4096 → 11008 → 4096                             │  │  │   │
│  │  │  └──────────────────────────────────────────────────────────┘  │  │   │
│  │  │                                                                 │  │   │
│  │  └────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  Output Heads (Multi-Task)                                           │   │
│  │  ├── Thought Image Head: Linear(4096 → 8K) + Softmax               │   │
│  │  ├── Layout Head: Linear(4096 → 1K) + Softmax                       │   │
│  │  └── Binding Head: Linear(4096 → 512) + Softmax                     │   │
│  │                                                                       │   │
│  │  Inference:                                                           │   │
│  │  Generate [THOUGHT_TOKENS] → [LAYOUT_TOKENS] → [BINDING_TOKENS]     │   │
│  │  Total output: ~896 tokens                                           │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 2: Constraint-Guided Generation

### Generator Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    IMAGE GENERATOR ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Base Model: Fine-tuned SDXL 1.0 with Autoregressive Head                  │
│  Parameters: 2.6B (SDXL) + 800M (AR Head) = 3.4B total                     │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    CONDITIONING INPUTS                                │   │
│  │                                                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │  From Reasoning Phase:                                       │     │   │
│  │  │  • Thought image tokens (512) → Upsampled guidance          │     │   │
│  │  │  • Layout tokens (256) → Regional attention masks           │     │   │
│  │  │  • Binding tokens (128) → Entity conditioning vectors       │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │  From Graph Context:                                         │     │   │
│  │  │  • Logo reference embedding (512-dim)                        │     │   │
│  │  │  • Color palette vectors (RGB → LAB → embedding)            │     │   │
│  │  │  • Style reference embedding (512-dim)                       │     │   │
│  │  │  • Negative prompts (prohibited elements)                    │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │  From Text Prompt:                                           │     │   │
│  │  │  • CLIP text embedding (768-dim)                             │     │   │
│  │  │  • T5-XXL encoding (4096-dim, pooled)                       │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    GENERATION PROCESS                                 │   │
│  │                                                                       │   │
│  │  Step 1: Condition Fusion                                            │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │                                                              │     │   │
│  │  │  condition = concat([                                        │     │   │
│  │  │      project(thought_image_embed, 1024),                    │     │   │
│  │  │      project(text_embed, 1024),                              │     │   │
│  │  │      project(graph_embed, 512),                              │     │   │
│  │  │      time_embed(t, 256)                                      │     │   │
│  │  │  ])  # Total: 2816-dim                                       │     │   │
│  │  │                                                              │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                       │   │
│  │  Step 2: Regional Attention Masks                                    │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │                                                              │     │   │
│  │  │  For each layout region R_i:                                 │     │   │
│  │  │    mask_i = create_soft_mask(R_i.bbox, feather=5px)         │     │   │
│  │  │    entity_cond_i = lookup(binding[R_i.entity_id])           │     │   │
│  │  │                                                              │     │   │
│  │  │  During attention:                                           │     │   │
│  │  │    attn_weights = softmax(Q @ K^T / sqrt(d))                │     │   │
│  │  │    regional_attn = attn_weights * mask_i + bias_i           │     │   │
│  │  │                                                              │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                       │   │
│  │  Step 3: Autoregressive Token Generation                             │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │                                                              │     │   │
│  │  │  for t in range(4096):  # 64x64 latent grid                 │     │   │
│  │  │      region_idx = get_region(t)  # Which layout region?     │     │   │
│  │  │      local_cond = concat([                                   │     │   │
│  │  │          condition,                                          │     │   │
│  │  │          entity_cond[region_idx],                            │     │   │
│  │  │          position_embed(t)                                   │     │   │
│  │  │      ])                                                      │     │   │
│  │  │                                                              │     │   │
│  │  │      logits = generator(x[<t], local_cond)                  │     │   │
│  │  │                                                              │     │   │
│  │  │      # Apply constraints                                     │     │   │
│  │  │      if region_idx in color_constrained_regions:            │     │   │
│  │  │          logits = apply_color_bias(logits, palette)         │     │   │
│  │  │                                                              │     │   │
│  │  │      x[t] = sample(logits, temperature=0.9, top_p=0.95)     │     │   │
│  │  │                                                              │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                       │   │
│  │  Step 4: VAE Decoding                                                │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │                                                              │     │   │
│  │  │  latent_grid = reshape(x, (64, 64, 4))                      │     │   │
│  │  │  image = sdxl_vae.decode(latent_grid)  # → 1024x1024 RGB   │     │   │
│  │  │                                                              │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### ControlNet Integration for Brand Elements

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONTROLNET BRAND ELEMENT INJECTION                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Purpose: Ensure pixel-perfect reproduction of brand elements (logos, etc.) │
│                                                                              │
│  Architecture:                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │                    ┌─────────────────┐                               │   │
│  │                    │   Logo Image    │                               │   │
│  │                    │   (Reference)   │                               │   │
│  │                    └────────┬────────┘                               │   │
│  │                             │                                         │   │
│  │                             ▼                                         │   │
│  │                    ┌─────────────────┐                               │   │
│  │                    │  Canny Edge     │                               │   │
│  │                    │  Detector       │                               │   │
│  │                    └────────┬────────┘                               │   │
│  │                             │                                         │   │
│  │                             ▼                                         │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │                    ControlNet Encoder                         │   │   │
│  │  │                                                               │   │   │
│  │  │  • Zero-convolution initialization                           │   │   │
│  │  │  • Feature injection at multiple scales                      │   │   │
│  │  │  • Region-masked application (only logo region)             │   │   │
│  │  │                                                               │   │   │
│  │  └────────────────────────────┬─────────────────────────────────┘   │   │
│  │                               │                                      │   │
│  │                               ▼                                      │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │                    SDXL UNet                                  │   │   │
│  │  │                                                               │   │   │
│  │  │  Residual injection:                                         │   │   │
│  │  │  h_out = h_base + controlnet_weight * controlnet_features   │   │   │
│  │  │                                                               │   │   │
│  │  │  Weight scheduling:                                          │   │   │
│  │  │  • Logo regions: 0.9-1.0 (strong control)                   │   │   │
│  │  │  • Product regions: 0.5-0.7 (moderate guidance)             │   │   │
│  │  │  • Background: 0.1-0.3 (light influence)                    │   │   │
│  │  │                                                               │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Brand Element Handling:                                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  1. LOGOS (Pixel-Perfect)                                            │   │
│  │     ├── Input: Pre-rendered logo at target size/position             │   │
│  │     ├── Control: Canny edges + semantic mask                         │   │
│  │     ├── Weight: 0.95 (near-deterministic)                            │   │
│  │     └── Verification: SSIM > 0.95                                    │   │
│  │                                                                       │   │
│  │  2. PRODUCT IMAGES (Style-Guided)                                    │   │
│  │     ├── Input: Reference product photo                               │   │
│  │     ├── Control: Depth map + semantic segmentation                   │   │
│  │     ├── Weight: 0.6 (allow creative variation)                       │   │
│  │     └── Verification: CLIP similarity > 0.80                         │   │
│  │                                                                       │   │
│  │  3. BRAND PATTERNS (Style Transfer)                                  │   │
│  │     ├── Input: Pattern tile reference                                │   │
│  │     ├── Control: None (purely style-based)                           │   │
│  │     ├── Method: LoRA adapter for pattern style                       │   │
│  │     └── Verification: Style loss < threshold                         │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 3: Validation & Refinement

### Constraint Validator Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BRAND CONSISTENCY VALIDATOR                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    VALIDATION PIPELINE                                │   │
│  │                                                                       │   │
│  │                         ┌─────────────┐                              │   │
│  │                         │  Generated  │                              │   │
│  │                         │   Image     │                              │   │
│  │                         └──────┬──────┘                              │   │
│  │                                │                                      │   │
│  │       ┌────────────────────────┼────────────────────────┐            │   │
│  │       │                        │                        │            │   │
│  │       ▼                        ▼                        ▼            │   │
│  │  ┌─────────────┐        ┌─────────────┐        ┌─────────────┐      │   │
│  │  │  Instance   │        │  Attribute  │        │  Relational │      │   │
│  │  │  Validator  │        │  Validator  │        │  Validator  │      │   │
│  │  └──────┬──────┘        └──────┬──────┘        └──────┬──────┘      │   │
│  │         │                      │                      │              │   │
│  │         ▼                      ▼                      ▼              │   │
│  │  ┌─────────────┐        ┌─────────────┐        ┌─────────────┐      │   │
│  │  │ • Logo SSIM │        │ • Color     │        │ • Required  │      │   │
│  │  │ • Product   │        │   Distance  │        │   Elements  │      │   │
│  │  │   CLIP      │        │ • Typography│        │ • Prohibited│      │   │
│  │  │ • Text OCR  │        │   Match     │        │   Combos    │      │   │
│  │  └─────────────┘        └─────────────┘        └─────────────┘      │   │
│  │         │                      │                      │              │   │
│  │         └──────────────────────┼──────────────────────┘              │   │
│  │                                │                                      │   │
│  │                                ▼                                      │   │
│  │                    ┌──────────────────────┐                          │   │
│  │                    │   Score Aggregator   │                          │   │
│  │                    │                      │                          │   │
│  │                    │ brand_score =        │                          │   │
│  │                    │   w1*instance +      │                          │   │
│  │                    │   w2*attribute +     │                          │   │
│  │                    │   w3*relational      │                          │   │
│  │                    │                      │                          │   │
│  │                    │ Default weights:     │                          │   │
│  │                    │ w1=0.4, w2=0.35,    │                          │   │
│  │                    │ w3=0.25             │                          │   │
│  │                    └──────────┬───────────┘                          │   │
│  │                               │                                       │   │
│  │                               ▼                                       │   │
│  │                    ┌──────────────────────┐                          │   │
│  │                    │   Decision Engine    │                          │   │
│  │                    │                      │                          │   │
│  │                    │ if brand_score >=    │                          │   │
│  │                    │    0.90: PASS       │                          │   │
│  │                    │ elif brand_score >=  │                          │   │
│  │                    │    0.75: REFINE     │                          │   │
│  │                    │ else: REJECT        │                          │   │
│  │                    └──────────────────────┘                          │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Validation Metrics Detail

```python
# Validation metric implementations (pseudocode)

class BrandConsistencyValidator:
    
    def validate_instance(self, image: np.ndarray, bindings: List[Binding]) -> InstanceScore:
        """
        Verify pixel-level accuracy of brand elements.
        """
        scores = {}
        
        for binding in bindings:
            if binding.type == BindingType.EXACT_MATCH:
                # Logo verification
                region = self.extract_region(image, binding.bbox)
                reference = self.load_reference(binding.entity_id)
                
                # SSIM for structural similarity
                ssim_score = structural_similarity(region, reference, multichannel=True)
                
                # Perceptual hash for robustness
                phash_distance = imagehash.phash(region) - imagehash.phash(reference)
                
                scores[binding.entity_id] = {
                    'ssim': ssim_score,
                    'phash_distance': phash_distance,
                    'pass': ssim_score > 0.95 and phash_distance < 5
                }
                
            elif binding.type == BindingType.SEMANTIC_GUIDE:
                # Product/content verification via CLIP
                region = self.extract_region(image, binding.bbox)
                region_embed = self.clip_model.encode_image(region)
                reference_embed = self.get_entity_embedding(binding.entity_id)
                
                similarity = cosine_similarity(region_embed, reference_embed)
                
                scores[binding.entity_id] = {
                    'clip_similarity': similarity,
                    'pass': similarity > 0.80
                }
        
        return InstanceScore(
            details=scores,
            aggregate=np.mean([s['pass'] for s in scores.values()])
        )
    
    def validate_attributes(self, image: np.ndarray, constraints: GraphConstraints) -> AttributeScore:
        """
        Verify color palette, typography, and style adherence.
        """
        scores = {}
        
        # Color validation
        dominant_colors = self.extract_dominant_colors(image, n=5)
        brand_colors = constraints.color_palette
        
        color_distances = []
        for dom_color in dominant_colors:
            min_dist = min([
                ciede2000(dom_color, brand_color) 
                for brand_color in brand_colors
            ])
            color_distances.append(min_dist)
        
        scores['color'] = {
            'distances': color_distances,
            'mean_distance': np.mean(color_distances),
            'pass': np.mean(color_distances) < 15  # CIEDE2000 threshold
        }
        
        # Typography validation (if text detected)
        detected_text = self.ocr_model.detect(image)
        if detected_text:
            for text_region in detected_text:
                font_match = self.font_classifier.classify(text_region.image)
                scores['typography'] = {
                    'detected_font': font_match.font_family,
                    'expected_font': constraints.typography.font_family,
                    'confidence': font_match.confidence,
                    'pass': font_match.font_family == constraints.typography.font_family
                }
        
        # Composition validation
        composition_features = self.composition_analyzer.analyze(image)
        expected_composition = constraints.visual_motif.style_attributes.composition
        
        scores['composition'] = {
            'detected': composition_features.primary_composition,
            'expected': expected_composition,
            'pass': composition_features.matches(expected_composition)
        }
        
        return AttributeScore(
            details=scores,
            aggregate=np.mean([s['pass'] for s in scores.values()])
        )
    
    def validate_relational(self, image: np.ndarray, graph_constraints: List[Constraint]) -> RelationalScore:
        """
        Verify graph-defined relationships are respected.
        """
        scores = {}
        
        # Detect all entities in image
        detected_entities = self.entity_detector.detect(image)
        detected_ids = set([e.entity_id for e in detected_entities])
        
        for constraint in graph_constraints:
            if constraint.type == ConstraintType.REQUIRED:
                # Check if required element is present
                source_present = constraint.source_id in detected_ids
                target_present = constraint.target_id in detected_ids
                
                if source_present:
                    scores[f"required_{constraint.id}"] = {
                        'source': constraint.source_id,
                        'target': constraint.target_id,
                        'target_present': target_present,
                        'pass': target_present
                    }
                    
            elif constraint.type == ConstraintType.PROHIBITED:
                # Check if prohibited combination is absent
                source_present = constraint.source_id in detected_ids
                target_present = constraint.target_id in detected_ids
                
                violation = source_present and target_present
                
                scores[f"prohibited_{constraint.id}"] = {
                    'source': constraint.source_id,
                    'target': constraint.target_id,
                    'violation': violation,
                    'pass': not violation
                }
        
        return RelationalScore(
            details=scores,
            aggregate=np.mean([s['pass'] for s in scores.values()]) if scores else 1.0
        )
```

### Iterative Refinement Loop

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ITERATIVE REFINEMENT PROCESS                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Purpose: Fix specific regions without full regeneration                    │
│  Max iterations: 3                                                           │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  Iteration 1 (Full Generation)                                       │   │
│  │  ├── Generate complete image                                          │   │
│  │  ├── Validate all constraints                                         │   │
│  │  └── Result: brand_score = 0.82 (REFINE)                             │   │
│  │                                                                       │   │
│  │  Failed checks:                                                       │   │
│  │  • Logo SSIM = 0.91 (< 0.95 threshold)                               │   │
│  │  • Color distance = 18 (> 15 threshold)                              │   │
│  │                                                                       │   │
│  │  ──────────────────────────────────────────────────────────────────  │   │
│  │                                                                       │   │
│  │  Iteration 2 (Region Refinement)                                     │   │
│  │  ├── Identify failed regions: [logo_region, background_region]       │   │
│  │  ├── Mask non-failed regions (preserve)                              │   │
│  │  ├── Re-generate only failed regions with:                           │   │
│  │  │   ├── Stronger ControlNet weight (0.95 → 0.98 for logo)          │   │
│  │  │   └── Color-constrained sampling for background                   │   │
│  │  └── Composite: blend refined regions into original                  │   │
│  │                                                                       │   │
│  │  Result: brand_score = 0.94 (PASS)                                   │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Refinement Strategies by Failure Type:                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  LOGO_MISMATCH:                                                      │   │
│  │  ├── Increase ControlNet weight                                       │   │
│  │  ├── Reduce region size (zoom in)                                     │   │
│  │  └── Use inpainting with reference as init                           │   │
│  │                                                                       │   │
│  │  COLOR_DEVIATION:                                                     │   │
│  │  ├── Apply color transfer post-processing                            │   │
│  │  ├── Re-sample with color-biased logits                              │   │
│  │  └── Use LoRA adapter for brand color style                          │   │
│  │                                                                       │   │
│  │  MISSING_ELEMENT:                                                     │   │
│  │  ├── Regenerate with explicit prompt addition                        │   │
│  │  ├── Use inpainting to add missing element                           │   │
│  │  └── Adjust layout tokens and retry                                  │   │
│  │                                                                       │   │
│  │  PROHIBITED_ELEMENT:                                                  │   │
│  │  ├── Add to negative prompt                                          │   │
│  │  ├── Use inpainting to remove                                        │   │
│  │  └── Mask region and regenerate                                      │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Training Strategy

### Dual-Phase Reinforcement Learning

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DUAL-PHASE RL TRAINING                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    PHASE A: THINKER RL                                │   │
│  │                                                                       │   │
│  │  Objective: Train reasoning model to produce high-quality plans      │   │
│  │                                                                       │   │
│  │  Reward Function:                                                     │   │
│  │  R_think(S) = α·R_constraint(S) + β·R_coherence(S) + γ·R_efficiency(S)│   │
│  │                                                                       │   │
│  │  Where:                                                               │   │
│  │  • R_constraint: % of graph constraints satisfiable by layout        │   │
│  │  • R_coherence: Spatial coherence score (no overlapping regions)     │   │
│  │  • R_efficiency: Token efficiency (shorter reasoning = better)       │   │
│  │                                                                       │   │
│  │  Training:                                                            │   │
│  │  • Algorithm: PPO with KL penalty                                    │   │
│  │  • Base policy: Pre-trained reasoning model                          │   │
│  │  • Reward model: Trained on human layout preferences                 │   │
│  │  • Data: 100K (prompt, graph) → reasoning pairs                     │   │
│  │                                                                       │   │
│  │  Loss:                                                                │   │
│  │  L_think = -E[min(r(θ)A, clip(r(θ), 1-ε, 1+ε)A)] + β·KL(π||π_ref)  │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    PHASE B: GENERATOR RL                              │   │
│  │                                                                       │   │
│  │  Objective: Train image generator for brand consistency              │   │
│  │                                                                       │   │
│  │  Reward Function:                                                     │   │
│  │  R_gen(X|S) = α·R_brand(X) + β·R_quality(X) + γ·R_prompt(X)         │   │
│  │                                                                       │   │
│  │  Where:                                                               │   │
│  │  • R_brand: Brand consistency score from validator                   │   │
│  │  • R_quality: Aesthetic quality (LAION aesthetic predictor)          │   │
│  │  • R_prompt: CLIP alignment with text prompt                         │   │
│  │                                                                       │   │
│  │  Training:                                                            │   │
│  │  • Algorithm: DPO (Direct Preference Optimization)                   │   │
│  │  • Preference data: Human ratings of (image_A, image_B) pairs       │   │
│  │  • Data: 50K preference pairs per brand                              │   │
│  │                                                                       │   │
│  │  Loss:                                                                │   │
│  │  L_gen = -E[log σ(β·(log π(y_w)/π_ref(y_w) - log π(y_l)/π_ref(y_l)))]│   │
│  │                                                                       │   │
│  │  Where y_w = preferred image, y_l = rejected image                   │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Training Schedule:                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  Week 1-2: Pre-train reasoning model (supervised)                    │   │
│  │            Dataset: 500K (prompt, layout) pairs                       │   │
│  │                                                                       │   │
│  │  Week 3-4: Fine-tune generator (supervised)                          │   │
│  │            Dataset: 1M (prompt, reasoning, image) tuples             │   │
│  │                                                                       │   │
│  │  Week 5-6: Thinker RL (Phase A)                                      │   │
│  │            Freeze generator, train reasoning with RL                  │   │
│  │                                                                       │   │
│  │  Week 7-8: Generator RL (Phase B)                                    │   │
│  │            Freeze reasoning, train generator with DPO                 │   │
│  │                                                                       │   │
│  │  Week 9+:  Joint fine-tuning                                         │   │
│  │            Alternate between phases, reduce LR                        │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Per-Brand Adaptation (LoRA)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PER-BRAND LORA ADAPTATION                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Strategy: Train lightweight LoRA adapters for each brand                   │
│  Base model: Shared across all tenants                                       │
│  LoRA rank: 64 (balance between capacity and efficiency)                    │
│  Parameters: ~10M per adapter (0.3% of base model)                          │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  Training Pipeline:                                                   │   │
│  │                                                                       │   │
│  │  1. Brand Onboarding (Day 1-3)                                       │   │
│  │     ├── Ingest brand assets (logos, colors, examples)                │   │
│  │     ├── Extract style embeddings                                      │   │
│  │     └── Generate synthetic training pairs                            │   │
│  │                                                                       │   │
│  │  2. Initial Training (Day 4-7)                                       │   │
│  │     ├── Fine-tune LoRA on brand examples                             │   │
│  │     ├── Validate on held-out set                                      │   │
│  │     └── Human review of 20 samples                                   │   │
│  │                                                                       │   │
│  │  3. Continuous Learning (Ongoing)                                    │   │
│  │     ├── Collect user feedback                                        │   │
│  │     ├── Retrain LoRA weekly (if feedback threshold met)             │   │
│  │     └── A/B test new adapter vs. current                            │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Adapter Storage:                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  s3://models/lora-adapters/                                          │   │
│  │  ├── brand_001/                                                      │   │
│  │  │   ├── v1.0/adapter.safetensors (40MB)                            │   │
│  │  │   ├── v1.1/adapter.safetensors                                   │   │
│  │  │   └── metadata.json                                               │   │
│  │  ├── brand_002/                                                      │   │
│  │  │   └── ...                                                         │   │
│  │  └── ...                                                              │   │
│  │                                                                       │   │
│  │  Total storage: ~40MB per brand                                      │   │
│  │  100 brands = 4GB (negligible)                                       │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Inference:                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  # Load base model once at startup                                   │   │
│  │  base_model = load_sdxl_base()                                       │   │
│  │                                                                       │   │
│  │  # Load LoRA adapter on-demand (cached in memory)                    │   │
│  │  adapter = lora_cache.get(brand_id)                                  │   │
│  │  if not adapter:                                                      │   │
│  │      adapter = load_lora(f"s3://models/lora/{brand_id}/latest")     │   │
│  │      lora_cache.put(brand_id, adapter)                               │   │
│  │                                                                       │   │
│  │  # Merge for inference                                               │   │
│  │  merged_model = merge_lora(base_model, adapter, alpha=0.8)          │   │
│  │  image = merged_model.generate(prompt, reasoning_tokens)             │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Inference Optimization

### Latency Breakdown & Optimization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    INFERENCE LATENCY OPTIMIZATION                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Target: <30 seconds end-to-end (P95)                                       │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    LATENCY BREAKDOWN (Before Optimization)            │   │
│  │                                                                       │   │
│  │  Stage                          Time (s)    % of Total                │   │
│  │  ─────────────────────────────────────────────────────────────────   │   │
│  │  GraphRAG retrieval             2.5         5%                        │   │
│  │  Context assembly               0.5         1%                        │   │
│  │  Reasoning generation           8.0         16%                       │   │
│  │  Image generation              35.0         70%                       │   │
│  │  Validation                     3.0         6%                        │   │
│  │  Post-processing                1.0         2%                        │   │
│  │  ─────────────────────────────────────────────────────────────────   │   │
│  │  TOTAL                         50.0s       100%                       │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    OPTIMIZATION STRATEGIES                            │   │
│  │                                                                       │   │
│  │  1. GraphRAG (2.5s → 0.8s)                                           │   │
│  │     ├── Redis cache for hot brand subgraphs                          │   │
│  │     ├── Pre-computed constraint sets                                  │   │
│  │     └── Parallel vector + graph queries                              │   │
│  │                                                                       │   │
│  │  2. Reasoning (8.0s → 4.0s)                                          │   │
│  │     ├── Model quantization (INT8)                                    │   │
│  │     ├── Speculative decoding                                          │   │
│  │     ├── KV-cache optimization                                         │   │
│  │     └── Batch similar requests                                        │   │
│  │                                                                       │   │
│  │  3. Image Generation (35.0s → 18.0s)                                 │   │
│  │     ├── Model distillation (50% fewer steps)                         │   │
│  │     ├── TensorRT optimization                                         │   │
│  │     ├── Flash attention                                               │   │
│  │     └── Progressive generation (show preview at 50%)                 │   │
│  │                                                                       │   │
│  │  4. Validation (3.0s → 1.5s)                                         │   │
│  │     ├── Parallel validator execution                                  │   │
│  │     ├── Early exit on critical failures                              │   │
│  │     └── GPU-accelerated CLIP/SSIM                                    │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    LATENCY BREAKDOWN (After Optimization)             │   │
│  │                                                                       │   │
│  │  Stage                          Time (s)    % of Total                │   │
│  │  ─────────────────────────────────────────────────────────────────   │   │
│  │  GraphRAG retrieval             0.8         3%                        │   │
│  │  Context assembly               0.3         1%                        │   │
│  │  Reasoning generation           4.0         16%                       │   │
│  │  Image generation              18.0         72%                       │   │
│  │  Validation                     1.5         6%                        │   │
│  │  Post-processing                0.4         2%                        │   │
│  │  ─────────────────────────────────────────────────────────────────   │   │
│  │  TOTAL                         25.0s       100%                       │   │
│  │                                                                       │   │
│  │  ✓ Within 30s P95 target                                             │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Hardware Configuration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GPU CLUSTER CONFIGURATION                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    INFERENCE NODES                                    │   │
│  │                                                                       │   │
│  │  Node Type: AWS p4d.24xlarge (8x A100 40GB)                          │   │
│  │                                                                       │   │
│  │  GPU Allocation per Node:                                            │   │
│  │  ┌────────────────────────────────────────────────────────────────┐  │   │
│  │  │                                                                 │  │   │
│  │  │  GPU 0-1: Reasoning Model (1.3B params)                        │  │   │
│  │  │           • Tensor parallel across 2 GPUs                      │  │   │
│  │  │           • 8GB VRAM each                                       │  │   │
│  │  │                                                                 │  │   │
│  │  │  GPU 2-5: Image Generator (3.4B params)                        │  │   │
│  │  │           • Tensor parallel across 4 GPUs                      │  │   │
│  │  │           • 32GB VRAM each                                      │  │   │
│  │  │                                                                 │  │   │
│  │  │  GPU 6-7: Validators + Misc                                    │  │   │
│  │  │           • CLIP, OCR, aesthetic models                        │  │   │
│  │  │           • LoRA adapter cache                                 │  │   │
│  │  │                                                                 │  │   │
│  │  └────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                       │   │
│  │  Throughput per Node: ~10 images/minute                              │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    SCALING STRATEGY                                   │   │
│  │                                                                       │   │
│  │  Requirement: 10,000 images/day = 7 images/minute sustained          │   │
│  │  Peak: 3x sustained = 21 images/minute                               │   │
│  │                                                                       │   │
│  │  Configuration:                                                       │   │
│  │  • Baseline: 2 nodes (20 img/min capacity)                          │   │
│  │  • Auto-scale: Up to 5 nodes (50 img/min capacity)                  │   │
│  │  • Scale trigger: Queue depth > 50 requests                         │   │
│  │                                                                       │   │
│  │  Cost (AWS us-east-1):                                               │   │
│  │  • p4d.24xlarge: $32.77/hour                                        │   │
│  │  • Baseline (2 nodes): $1,573/day                                   │   │
│  │  • Per-image cost: $0.16 (at 10K/day)                               │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Brand Consistency Mechanisms

### Deterministic Mode

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DETERMINISTIC GENERATION MODE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Use Case: Legal/compliance requirements for reproducible outputs           │
│                                                                              │
│  Mechanism:                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  1. Seed Management                                                  │   │
│  │     ├── Store seed with each generation request                      │   │
│  │     ├── Seed = hash(prompt + graph_version + timestamp)             │   │
│  │     └── Retrieve seed for exact reproduction                         │   │
│  │                                                                       │   │
│  │  2. Floating Point Determinism                                       │   │
│  │     ├── torch.use_deterministic_algorithms(True)                    │   │
│  │     ├── CUBLAS_WORKSPACE_CONFIG=:16:8                               │   │
│  │     └── Fixed CUDA version across cluster                           │   │
│  │                                                                       │   │
│  │  3. Graph Snapshot                                                   │   │
│  │     ├── Store graph_version_id with generation                       │   │
│  │     ├── Reproduce with same graph state                              │   │
│  │     └── Immutable graph snapshots for compliance                     │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Reproduction Request:                                                       │
│  {                                                                           │
│    "action": "reproduce",                                                   │
│    "original_generation_id": "gen_abc123",                                  │
│    "verify_exact_match": true                                               │
│  }                                                                           │
│                                                                              │
│  Response includes: SHA-256 hash of output for verification                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Explainability

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GENERATION EXPLAINABILITY                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Every generation produces an explanation artifact:                         │
│                                                                              │
│  {                                                                           │
│    "generation_id": "gen_abc123",                                           │
│    "timestamp": "2026-01-19T10:30:00Z",                                     │
│                                                                              │
│    "graph_influence": {                                                      │
│      "nodes_retrieved": [                                                   │
│        {"id": "logo_001", "type": "Logo", "influence": 0.95},              │
│        {"id": "palette_001", "type": "ColorPalette", "influence": 0.88},   │
│        {"id": "motif_003", "type": "VisualMotif", "influence": 0.72}       │
│      ],                                                                      │
│      "constraints_applied": [                                               │
│        {"id": "c_001", "type": "REQUIRES", "satisfied": true},             │
│        {"id": "c_002", "type": "PROHIBITS", "satisfied": true}             │
│      ]                                                                       │
│    },                                                                        │
│                                                                              │
│    "reasoning_trace": {                                                      │
│      "thought_image": "s3://traces/gen_abc123/thought.png",                │
│      "layout_plan": [                                                       │
│        {"region": "logo", "bbox": [0.05, 0.02, 0.15, 0.08]},              │
│        {"region": "product", "bbox": [0.25, 0.20, 0.50, 0.55]}            │
│      ],                                                                      │
│      "bindings": [                                                          │
│        {"entity": "logo_001", "region": "logo", "method": "EXACT_MATCH"}  │
│      ]                                                                       │
│    },                                                                        │
│                                                                              │
│    "validation_results": {                                                   │
│      "instance_score": 0.97,                                                │
│      "attribute_score": 0.92,                                               │
│      "relational_score": 1.00,                                              │
│      "overall_brand_score": 0.95,                                           │
│      "details": {                                                            │
│        "logo_ssim": 0.98,                                                   │
│        "color_distance_mean": 8.2,                                          │
│        "required_elements_present": ["logo", "tagline", "product"]         │
│      }                                                                       │
│    }                                                                         │
│  }                                                                           │
│                                                                              │
│  Dashboard UI shows:                                                         │
│  • Visual overlay highlighting graph-influenced regions                     │
│  • Side-by-side: thought image vs. final output                            │
│  • Constraint satisfaction checklist                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Cost Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COST PER GENERATION                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Target: $0.50 per content piece (image + text)                             │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    COST BREAKDOWN                                     │   │
│  │                                                                       │   │
│  │  Component                      Cost/Generation    % of Total         │   │
│  │  ─────────────────────────────────────────────────────────────────   │   │
│  │  GPU Compute (image)            $0.16              32%                │   │
│  │  GPU Compute (reasoning)        $0.05              10%                │   │
│  │  GPU Compute (validation)       $0.02               4%                │   │
│  │  LLM API (text generation)      $0.08              16%                │   │
│  │  Graph DB queries               $0.01               2%                │   │
│  │  Vector search                  $0.01               2%                │   │
│  │  Storage (30-day retention)     $0.02               4%                │   │
│  │  Network/data transfer          $0.01               2%                │   │
│  │  Overhead (infra, monitoring)   $0.14              28%                │   │
│  │  ─────────────────────────────────────────────────────────────────   │   │
│  │  TOTAL                          $0.50             100%                │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Cost Optimization Levers:                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                                                                       │   │
│  │  1. Caching (saves ~15% on repeat requests)                          │   │
│  │     ├── Cache brand constraint sets                                   │   │
│  │     ├── Cache reasoning for similar prompts                          │   │
│  │     └── Cache validation results                                      │   │
│  │                                                                       │   │
│  │  2. Batching (saves ~20% on GPU utilization)                         │   │
│  │     ├── Batch similar brand requests                                  │   │
│  │     ├── Share LoRA adapter loads                                      │   │
│  │     └── Batch validation runs                                         │   │
│  │                                                                       │   │
│  │  3. Model Optimization (saves ~30% on inference)                     │   │
│  │     ├── INT8 quantization                                            │   │
│  │     ├── Model distillation                                           │   │
│  │     └── Speculative decoding                                          │   │
│  │                                                                       │   │
│  │  4. Spot Instances (saves ~60% on GPU cost)                          │   │
│  │     ├── Use for batch/async workloads                                │   │
│  │     ├── Fallback to on-demand for real-time                          │   │
│  │     └── Multi-AZ for availability                                    │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Next Document

Continue to **[04-agent-orchestration.md](./04-agent-orchestration.md)** for the multi-agent coordination blueprint.
