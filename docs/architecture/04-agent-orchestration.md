# Multi-Agent Orchestration Blueprint
## MCP + A2A Protocol Implementation

**Version**: 1.0  
**Date**: January 2026  
**Component**: Agent Framework + Workflow Orchestration

---

## Table of Contents
1. [Agent Architecture Overview](#agent-architecture-overview)
2. [Agent Specifications](#agent-specifications)
3. [MCP Tool Definitions](#mcp-tool-definitions)
4. [A2A Communication Protocol](#a2a-communication-protocol)
5. [Workflow Orchestration](#workflow-orchestration)
6. [Failure Handling](#failure-handling)
7. [Observability](#observability)

---

## Agent Architecture Overview

### Design Principles

1. **Single Responsibility**: Each agent has one primary function
2. **Loose Coupling**: Agents communicate via message passing, not direct calls
3. **Stateless Execution**: Agent state stored externally (Redis/DB)
4. **Idempotent Operations**: Safe to retry any agent action
5. **Observable**: Every action logged and traced

### Agent Topology

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              AGENT ORCHESTRATION TOPOLOGY                                │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│                                  ┌────────────────────┐                                 │
│                                  │    USER REQUEST    │                                 │
│                                  │    (API Gateway)   │                                 │
│                                  └──────────┬─────────┘                                 │
│                                             │                                            │
│                                             ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                         ORCHESTRATION LAYER (Temporal.io)                         │   │
│  │                                                                                   │   │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐     │   │
│  │  │                    Content Generation Workflow                           │     │   │
│  │  │                                                                          │     │   │
│  │  │  start() → plan() → retrieve() → reason() → generate() → validate()    │     │   │
│  │  │                                                      ↓                   │     │   │
│  │  │                                               [PASS] → complete()       │     │   │
│  │  │                                               [FAIL] → refine() ──┐     │     │   │
│  │  │                                                      ↑            │     │     │   │
│  │  │                                                      └────────────┘     │     │   │
│  │  └─────────────────────────────────────────────────────────────────────────┘     │   │
│  │                                                                                   │   │
│  └──────────────────────────────────────────────┬────────────────────────────────────┘   │
│                                                 │                                        │
│                                                 ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                              MESSAGE BUS (Kafka)                                  │   │
│  │                                                                                   │   │
│  │  Topics:                                                                         │   │
│  │  ├── agent.tasks.content-strategy                                               │   │
│  │  ├── agent.tasks.graph-query                                                    │   │
│  │  ├── agent.tasks.reasoning                                                      │   │
│  │  ├── agent.tasks.image-generation                                               │   │
│  │  ├── agent.tasks.text-generation                                                │   │
│  │  ├── agent.tasks.validation                                                     │   │
│  │  ├── agent.tasks.feedback-learning                                              │   │
│  │  └── agent.results.*                                                            │   │
│  │                                                                                   │   │
│  └──────────────────────────────────────────────┬────────────────────────────────────┘   │
│                                                 │                                        │
│          ┌──────────────────────────────────────┼──────────────────────────────────┐    │
│          │                                      │                                  │    │
│          ▼                                      ▼                                  ▼    │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
│  │    BRAND      │  │   CONTENT     │  │    GRAPH      │  │   REASONING   │           │
│  │ INTELLIGENCE  │  │   STRATEGY    │  │    QUERY      │  │    AGENT      │           │
│  │    AGENT      │  │    AGENT      │  │    AGENT      │  │               │           │
│  │               │  │               │  │               │  │               │           │
│  │ ┌───────────┐ │  │ ┌───────────┐ │  │ ┌───────────┐ │  │ ┌───────────┐ │           │
│  │ │MCP Tools: │ │  │ │MCP Tools: │ │  │ │MCP Tools: │ │  │ │MCP Tools: │ │           │
│  │ │• scrape   │ │  │ │• llm_call │ │  │ │• neo4j    │ │  │ │• reasoning│ │           │
│  │ │• extract  │ │  │ │• plan     │ │  │ │• pgvector │ │  │ │  _model   │ │           │
│  │ │• graph_wr │ │  │ │• schedule │ │  │ │• cache    │ │  │ │• layout   │ │           │
│  │ └───────────┘ │  │ └───────────┘ │  │ └───────────┘ │  │ └───────────┘ │           │
│  └───────────────┘  └───────────────┘  └───────────────┘  └───────────────┘           │
│          │                  │                  │                  │                    │
│          │                  │                  │                  │                    │
│          ▼                  ▼                  ▼                  ▼                    │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
│  │    IMAGE      │  │     TEXT      │  │  VALIDATION   │  │   FEEDBACK    │           │
│  │  GENERATION   │  │  GENERATION   │  │    AGENT      │  │   LEARNING    │           │
│  │    AGENT      │  │    AGENT      │  │               │  │    AGENT      │           │
│  │               │  │               │  │               │  │               │           │
│  │ ┌───────────┐ │  │ ┌───────────┐ │  │ ┌───────────┐ │  │ ┌───────────┐ │           │
│  │ │MCP Tools: │ │  │ │MCP Tools: │ │  │ │MCP Tools: │ │  │ │MCP Tools: │ │           │
│  │ │• sdxl     │ │  │ │• gpt4     │ │  │ │• clip     │ │  │ │• classify │ │           │
│  │ │• controlnt│ │  │ │• claude   │ │  │ │• ssim     │ │  │ │• mutate   │ │           │
│  │ │• lora     │ │  │ │• voice    │ │  │ │• ocr      │ │  │ │• version  │ │           │
│  │ └───────────┘ │  │ └───────────┘ │  │ └───────────┘ │  │ └───────────┘ │           │
│  └───────────────┘  └───────────────┘  └───────────────┘  └───────────────┘           │
│                                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                              SHARED SERVICES (MCP)                                │   │
│  │                                                                                   │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │   │
│  │  │  Neo4j  │  │pgvector │  │  Redis  │  │   S3    │  │ Triton  │  │External │   │   │
│  │  │ Service │  │ Service │  │ Service │  │ Service │  │ Service │  │  APIs   │   │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘   │   │
│  │                                                                                   │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Specifications

### 1. Brand Intelligence Agent

```yaml
name: brand-intelligence-agent
version: 1.0.0
description: Manages brand knowledge graph construction and maintenance

responsibilities:
  - Website scraping and content extraction
  - Brand DNA analysis (colors, typography, voice)
  - Knowledge graph construction
  - Schema versioning and migration

mcp_tools:
  - web_scraper
  - pdf_extractor
  - image_analyzer
  - graph_writer
  - schema_validator

input_channels:
  - agent.tasks.brand-intelligence

output_channels:
  - agent.results.brand-intelligence
  - graph.updates

state_store: redis
  key_pattern: "agent:brand-intelligence:{task_id}:state"

scaling:
  min_replicas: 2
  max_replicas: 10
  scaling_metric: kafka_consumer_lag
  target_lag: 100

resource_limits:
  cpu: 2
  memory: 4Gi
```

**API Contract:**

```typescript
// Input: Brand Ingestion Request
interface BrandIngestionTask {
  task_id: string;
  tenant_id: string;
  brand_id: string;
  sources: {
    website_urls: string[];
    document_urls: string[];
    existing_assets: string[];
  };
  options: {
    extract_colors: boolean;
    extract_typography: boolean;
    extract_voice: boolean;
    create_embeddings: boolean;
  };
}

// Output: Ingestion Result
interface BrandIngestionResult {
  task_id: string;
  status: 'success' | 'partial' | 'failed';
  graph_version: string;
  extracted_entities: {
    colors: ColorPalette[];
    typography: Typography[];
    logos: Logo[];
    voice_profile: VoiceProfile;
    key_messages: KeyMessage[];
  };
  errors: Error[];
  duration_ms: number;
}
```

---

### 2. Content Strategy Agent

```yaml
name: content-strategy-agent
version: 1.0.0
description: Orchestrates content generation workflows

responsibilities:
  - Parse user content requests
  - Create generation plans
  - Coordinate multi-agent workflows
  - Handle user preferences and overrides

mcp_tools:
  - llm_call (GPT-4)
  - intent_classifier
  - plan_generator
  - scheduler

input_channels:
  - agent.tasks.content-strategy
  - api.content-requests

output_channels:
  - agent.tasks.graph-query
  - agent.tasks.reasoning
  - agent.tasks.image-generation
  - agent.tasks.text-generation
  - agent.results.content-strategy

a2a_connections:
  - graph-query-agent (sync)
  - reasoning-agent (async)
  - image-generation-agent (async)
  - text-generation-agent (async)
  - validation-agent (sync)

state_store: redis
  key_pattern: "agent:content-strategy:{workflow_id}:state"

scaling:
  min_replicas: 3
  max_replicas: 20
  scaling_metric: request_rate
  target_rps: 50
```

**API Contract:**

```typescript
// Input: Content Generation Request
interface ContentGenerationRequest {
  request_id: string;
  tenant_id: string;
  brand_id: string;
  
  prompt: string;
  content_type: 'social_post' | 'ad' | 'email' | 'blog' | 'product_page';
  
  constraints: {
    target_persona?: string;
    visual_style?: string;
    tone?: string;
    required_elements?: string[];
    excluded_elements?: string[];
  };
  
  output_specs: {
    image_dimensions?: { width: number; height: number };
    text_length?: 'short' | 'medium' | 'long';
    variations?: number;
  };
  
  priority: 'low' | 'normal' | 'high';
}

// Output: Generation Plan
interface GenerationPlan {
  request_id: string;
  plan_id: string;
  
  steps: PlanStep[];
  
  estimated_duration_ms: number;
  estimated_cost_usd: number;
  
  parallel_groups: string[][];  // Steps that can run in parallel
}

interface PlanStep {
  step_id: string;
  agent: string;
  action: string;
  input_refs: string[];  // References to previous step outputs
  timeout_ms: number;
  retry_policy: RetryPolicy;
}
```

---

### 3. Graph Query Agent (GraphRAG)

```yaml
name: graph-query-agent
version: 1.0.0
description: Executes GraphRAG queries for context retrieval

responsibilities:
  - Multi-hop graph traversal
  - Hybrid search (vector + graph)
  - Constraint extraction
  - Context assembly with token budgeting

mcp_tools:
  - neo4j_query
  - pgvector_search
  - redis_cache
  - embedding_generator

input_channels:
  - agent.tasks.graph-query

output_channels:
  - agent.results.graph-query

performance_targets:
  p50_latency_ms: 50
  p95_latency_ms: 100
  p99_latency_ms: 200

caching:
  strategy: write-through
  ttl_seconds: 3600
  invalidation: graph.updates topic

scaling:
  min_replicas: 5
  max_replicas: 30
  scaling_metric: latency_p95
  target_latency_ms: 100
```

**API Contract:**

```typescript
// Input: Graph Query Request
interface GraphQueryRequest {
  query_id: string;
  tenant_id: string;
  brand_id: string;
  
  query_type: 'context_retrieval' | 'constraint_check' | 'similarity_search';
  
  parameters: {
    text_query?: string;
    entity_ids?: string[];
    traversal_depth?: number;
    include_embeddings?: boolean;
  };
  
  token_budget: number;  // Max tokens for context assembly
}

// Output: Graph Query Result
interface GraphQueryResult {
  query_id: string;
  
  context: {
    brand_constraints: Constraint[];
    visual_references: VisualReference[];
    tonal_guidelines: TonalGuideline;
    key_messages: KeyMessage[];
    negative_constraints: Constraint[];
    high_performers: Asset[];
  };
  
  metadata: {
    nodes_traversed: number;
    edges_traversed: number;
    cache_hit: boolean;
    execution_time_ms: number;
    tokens_used: number;
  };
}
```

---

### 4. Reasoning Agent

```yaml
name: reasoning-agent
version: 1.0.0
description: Generates reasoning tokens for image planning

responsibilities:
  - Thought image generation
  - Layout planning
  - Entity-region binding
  - Constraint satisfaction planning

mcp_tools:
  - reasoning_model_inference
  - layout_validator
  - binding_generator

input_channels:
  - agent.tasks.reasoning

output_channels:
  - agent.results.reasoning

gpu_requirements:
  type: A100
  count: 2
  memory_gb: 80

performance_targets:
  p50_latency_ms: 3000
  p95_latency_ms: 5000

scaling:
  min_replicas: 2
  max_replicas: 8
  scaling_metric: gpu_utilization
  target_utilization: 0.8
```

**API Contract:**

```typescript
// Input: Reasoning Request
interface ReasoningRequest {
  reasoning_id: string;
  
  prompt: string;
  graph_context: GraphQueryResult['context'];
  reference_images: string[];  // S3 URIs
  
  output_specs: {
    thought_image_resolution: number;  // 64 or 128
    num_thought_images: number;  // 1-3
    layout_precision: 'coarse' | 'fine';
  };
}

// Output: Reasoning Result
interface ReasoningResult {
  reasoning_id: string;
  
  thought_images: {
    image_uri: string;
    tokens: number[];
    selection_score: number;
  }[];
  
  selected_thought_image_idx: number;
  
  layout_tokens: LayoutToken[];
  binding_tokens: BindingToken[];
  
  constraint_satisfaction: {
    constraint_id: string;
    satisfiable: boolean;
    confidence: number;
  }[];
  
  inference_time_ms: number;
}

interface LayoutToken {
  region_id: string;
  type: 'logo' | 'product' | 'text' | 'background' | 'decoration';
  bbox: { x: number; y: number; w: number; h: number };
  priority: number;
  constraint_ref?: string;
}

interface BindingToken {
  entity_id: string;
  region_id: string;
  binding_type: 'EXACT_MATCH' | 'STYLE_TRANSFER' | 'COLOR_FILL' | 'SEMANTIC_GUIDE';
  parameters: Record<string, any>;
}
```

---

### 5. Image Generation Agent

```yaml
name: image-generation-agent
version: 1.0.0
description: Generates high-resolution images from reasoning outputs

responsibilities:
  - Autoregressive image token generation
  - ControlNet conditioning
  - LoRA adapter loading
  - Iterative refinement

mcp_tools:
  - sdxl_inference
  - controlnet_apply
  - lora_loader
  - vae_decode
  - inpainting

input_channels:
  - agent.tasks.image-generation

output_channels:
  - agent.results.image-generation

gpu_requirements:
  type: A100
  count: 4
  memory_gb: 160

performance_targets:
  p50_latency_ms: 15000
  p95_latency_ms: 25000

scaling:
  min_replicas: 2
  max_replicas: 10
  scaling_metric: queue_depth
  target_queue_depth: 20
```

**API Contract:**

```typescript
// Input: Image Generation Request
interface ImageGenerationRequest {
  generation_id: string;
  tenant_id: string;
  brand_id: string;
  
  reasoning_result: ReasoningResult;
  
  conditioning: {
    text_prompt: string;
    negative_prompt: string;
    graph_constraints: Constraint[];
    reference_images: { uri: string; weight: number }[];
  };
  
  generation_params: {
    width: number;
    height: number;
    guidance_scale: number;
    num_inference_steps: number;
    seed?: number;  // For deterministic mode
  };
  
  lora_adapters: {
    adapter_id: string;
    weight: number;
  }[];
  
  controlnet_inputs?: {
    type: 'canny' | 'depth' | 'pose' | 'semantic';
    image_uri: string;
    weight: number;
    region_mask?: string;  // S3 URI to mask
  }[];
}

// Output: Image Generation Result
interface ImageGenerationResult {
  generation_id: string;
  
  image_uri: string;  // S3 URI
  thumbnail_uri: string;
  
  metadata: {
    seed: number;
    actual_steps: number;
    generation_time_ms: number;
    gpu_memory_peak_gb: number;
  };
  
  intermediate_outputs?: {
    step: number;
    image_uri: string;
  }[];  // For progressive preview
}
```

---

### 6. Text Generation Agent

```yaml
name: text-generation-agent
version: 1.0.0
description: Generates brand-aligned marketing copy

responsibilities:
  - Multi-format copywriting
  - Brand voice enforcement
  - Multi-language support
  - A/B variant generation

mcp_tools:
  - gpt4_call
  - claude_call
  - voice_analyzer
  - translation

input_channels:
  - agent.tasks.text-generation

output_channels:
  - agent.results.text-generation

performance_targets:
  p50_latency_ms: 2000
  p95_latency_ms: 5000

scaling:
  min_replicas: 3
  max_replicas: 15
  scaling_metric: request_rate
  target_rps: 100
```

**API Contract:**

```typescript
// Input: Text Generation Request
interface TextGenerationRequest {
  text_id: string;
  tenant_id: string;
  brand_id: string;
  
  prompt: string;
  content_type: 'headline' | 'body' | 'cta' | 'tagline' | 'description';
  
  voice_profile: VoiceProfile;
  vocabulary: Vocabulary;
  
  constraints: {
    max_length?: number;
    min_length?: number;
    required_keywords?: string[];
    excluded_words?: string[];
    tone_override?: string;
  };
  
  variants: number;  // Number of alternatives to generate
  language: string;  // ISO 639-1
}

// Output: Text Generation Result
interface TextGenerationResult {
  text_id: string;
  
  variants: {
    text: string;
    voice_alignment_score: number;
    constraint_violations: string[];
  }[];
  
  selected_variant_idx: number;
  
  metadata: {
    model_used: string;
    tokens_used: number;
    generation_time_ms: number;
  };
}
```

---

### 7. Validation Agent

```yaml
name: validation-agent
version: 1.0.0
description: Validates generated content against brand constraints

responsibilities:
  - Instance-level verification (logos, products)
  - Attribute validation (colors, typography)
  - Relational constraint checking
  - Brand score computation

mcp_tools:
  - clip_inference
  - ssim_calculator
  - ocr_detector
  - color_analyzer
  - composition_analyzer

input_channels:
  - agent.tasks.validation

output_channels:
  - agent.results.validation

gpu_requirements:
  type: A100
  count: 1
  memory_gb: 40

performance_targets:
  p50_latency_ms: 1000
  p95_latency_ms: 2000

scaling:
  min_replicas: 3
  max_replicas: 12
  scaling_metric: queue_depth
  target_queue_depth: 50
```

---

### 8. Feedback Learning Agent

```yaml
name: feedback-learning-agent
version: 1.0.0
description: Processes user feedback and updates knowledge graph

responsibilities:
  - Feedback signal classification
  - Graph mutation proposal
  - Conflict resolution
  - Retrain signal emission

mcp_tools:
  - feedback_classifier
  - graph_mutator
  - conflict_resolver
  - version_manager

input_channels:
  - agent.tasks.feedback-learning
  - feedback.events

output_channels:
  - graph.updates
  - training.signals

scaling:
  min_replicas: 2
  max_replicas: 8
  scaling_metric: feedback_queue_depth
  target_queue_depth: 100
```

---

## MCP Tool Definitions

### Tool Schema Format

```typescript
interface MCPTool {
  name: string;
  description: string;
  input_schema: JSONSchema;
  output_schema: JSONSchema;
  timeout_ms: number;
  retry_policy: RetryPolicy;
  rate_limit?: RateLimit;
}
```

### Core MCP Tools

```yaml
# ═══════════════════════════════════════════════════════════════════════════
# GRAPH TOOLS
# ═══════════════════════════════════════════════════════════════════════════

neo4j_query:
  name: neo4j_query
  description: Execute Cypher query against Neo4j graph database
  input_schema:
    type: object
    properties:
      cypher:
        type: string
        description: Cypher query (tenant-scoped automatically)
      parameters:
        type: object
        description: Query parameters
      timeout_ms:
        type: integer
        default: 5000
    required: [cypher]
  output_schema:
    type: object
    properties:
      records:
        type: array
      summary:
        type: object
  timeout_ms: 10000
  retry_policy:
    max_attempts: 3
    backoff_ms: [100, 500, 2000]

graph_write:
  name: graph_write
  description: Write nodes/edges to graph with version control
  input_schema:
    type: object
    properties:
      mutations:
        type: array
        items:
          type: object
          properties:
            operation: { enum: [CREATE, UPDATE, DELETE] }
            entity_type: { type: string }
            entity_id: { type: string }
            properties: { type: object }
      version_comment:
        type: string
    required: [mutations]
  output_schema:
    type: object
    properties:
      version_id: { type: string }
      mutations_applied: { type: integer }
  timeout_ms: 30000

# ═══════════════════════════════════════════════════════════════════════════
# VECTOR TOOLS
# ═══════════════════════════════════════════════════════════════════════════

pgvector_search:
  name: pgvector_search
  description: Similarity search in vector database
  input_schema:
    type: object
    properties:
      query_embedding:
        type: array
        items: { type: number }
      entity_type:
        type: string
      top_k:
        type: integer
        default: 10
      filters:
        type: object
    required: [query_embedding]
  output_schema:
    type: object
    properties:
      results:
        type: array
        items:
          type: object
          properties:
            entity_id: { type: string }
            similarity: { type: number }
            metadata: { type: object }
  timeout_ms: 5000

embedding_generate:
  name: embedding_generate
  description: Generate embeddings for text or images
  input_schema:
    type: object
    properties:
      input_type: { enum: [text, image] }
      content:
        type: string
        description: Text content or image URI
      model:
        type: string
        default: text-embedding-3-large
    required: [input_type, content]
  output_schema:
    type: object
    properties:
      embedding:
        type: array
        items: { type: number }
      dimensions: { type: integer }
  timeout_ms: 10000

# ═══════════════════════════════════════════════════════════════════════════
# LLM TOOLS
# ═══════════════════════════════════════════════════════════════════════════

llm_call:
  name: llm_call
  description: Call LLM for text generation
  input_schema:
    type: object
    properties:
      model:
        enum: [gpt-4-turbo, gpt-4, claude-3-opus, claude-3-sonnet]
      messages:
        type: array
        items:
          type: object
          properties:
            role: { enum: [system, user, assistant] }
            content: { type: string }
      temperature:
        type: number
        default: 0.7
      max_tokens:
        type: integer
        default: 1024
      response_format:
        type: object
    required: [model, messages]
  output_schema:
    type: object
    properties:
      content: { type: string }
      finish_reason: { type: string }
      usage:
        type: object
        properties:
          prompt_tokens: { type: integer }
          completion_tokens: { type: integer }
  timeout_ms: 60000
  rate_limit:
    requests_per_minute: 500
    tokens_per_minute: 150000

# ═══════════════════════════════════════════════════════════════════════════
# IMAGE GENERATION TOOLS
# ═══════════════════════════════════════════════════════════════════════════

sdxl_inference:
  name: sdxl_inference
  description: Generate image using SDXL model
  input_schema:
    type: object
    properties:
      prompt: { type: string }
      negative_prompt: { type: string }
      width: { type: integer, default: 1024 }
      height: { type: integer, default: 1024 }
      guidance_scale: { type: number, default: 7.5 }
      num_inference_steps: { type: integer, default: 30 }
      seed: { type: integer }
      scheduler: { enum: [ddim, euler, dpm++] }
    required: [prompt]
  output_schema:
    type: object
    properties:
      image_uri: { type: string }
      seed: { type: integer }
      latents: { type: string }  # For refinement
  timeout_ms: 60000

controlnet_apply:
  name: controlnet_apply
  description: Apply ControlNet conditioning to generation
  input_schema:
    type: object
    properties:
      control_type: { enum: [canny, depth, pose, semantic, reference] }
      control_image_uri: { type: string }
      weight: { type: number, default: 1.0 }
      region_mask_uri: { type: string }
    required: [control_type, control_image_uri]
  output_schema:
    type: object
    properties:
      conditioning_tensor_uri: { type: string }
  timeout_ms: 10000

lora_load:
  name: lora_load
  description: Load LoRA adapter for brand-specific styling
  input_schema:
    type: object
    properties:
      adapter_uri: { type: string }
      weight: { type: number, default: 0.8 }
    required: [adapter_uri]
  output_schema:
    type: object
    properties:
      adapter_id: { type: string }
      loaded: { type: boolean }
  timeout_ms: 5000

# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION TOOLS
# ═══════════════════════════════════════════════════════════════════════════

clip_similarity:
  name: clip_similarity
  description: Compute CLIP similarity between image and text/image
  input_schema:
    type: object
    properties:
      image_uri: { type: string }
      reference:
        type: object
        properties:
          type: { enum: [text, image] }
          content: { type: string }
    required: [image_uri, reference]
  output_schema:
    type: object
    properties:
      similarity: { type: number }
      image_embedding: { type: array }
  timeout_ms: 5000

ssim_compare:
  name: ssim_compare
  description: Compute structural similarity between images
  input_schema:
    type: object
    properties:
      image_uri_a: { type: string }
      image_uri_b: { type: string }
      region:
        type: object
        properties:
          x: { type: integer }
          y: { type: integer }
          width: { type: integer }
          height: { type: integer }
    required: [image_uri_a, image_uri_b]
  output_schema:
    type: object
    properties:
      ssim: { type: number }
      mse: { type: number }
  timeout_ms: 3000

color_extract:
  name: color_extract
  description: Extract dominant colors from image region
  input_schema:
    type: object
    properties:
      image_uri: { type: string }
      num_colors: { type: integer, default: 5 }
      region:
        type: object
    required: [image_uri]
  output_schema:
    type: object
    properties:
      colors:
        type: array
        items:
          type: object
          properties:
            hex: { type: string }
            rgb: { type: array }
            percentage: { type: number }
  timeout_ms: 2000

# ═══════════════════════════════════════════════════════════════════════════
# STORAGE TOOLS
# ═══════════════════════════════════════════════════════════════════════════

s3_upload:
  name: s3_upload
  description: Upload file to S3 with CDN distribution
  input_schema:
    type: object
    properties:
      content:
        type: string
        description: Base64 encoded content or local path
      path: { type: string }
      content_type: { type: string }
      metadata: { type: object }
    required: [content, path]
  output_schema:
    type: object
    properties:
      uri: { type: string }
      cdn_uri: { type: string }
      etag: { type: string }
  timeout_ms: 30000

s3_download:
  name: s3_download
  description: Download file from S3
  input_schema:
    type: object
    properties:
      uri: { type: string }
      as_base64: { type: boolean, default: false }
    required: [uri]
  output_schema:
    type: object
    properties:
      content: { type: string }
      content_type: { type: string }
      size_bytes: { type: integer }
  timeout_ms: 30000
```

---

## A2A Communication Protocol

### Message Format

```typescript
interface A2AMessage {
  // Header
  message_id: string;
  correlation_id: string;  // Links related messages in a workflow
  trace_id: string;        // Distributed tracing
  
  // Routing
  source_agent: string;
  target_agent: string;
  message_type: 'REQUEST' | 'RESPONSE' | 'EVENT' | 'ERROR';
  
  // Payload
  payload: {
    action: string;
    data: Record<string, any>;
  };
  
  // Metadata
  timestamp: string;  // ISO 8601
  ttl_ms: number;
  priority: 'LOW' | 'NORMAL' | 'HIGH' | 'CRITICAL';
  
  // Security
  tenant_id: string;
  auth_context: {
    user_id?: string;
    service_account?: string;
    permissions: string[];
  };
}
```

### Communication Patterns

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       A2A COMMUNICATION PATTERNS                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PATTERN 1: Request-Response (Synchronous)                                  │
│  ───────────────────────────────────────────                                │
│  Use when: Response needed before continuing                                │
│                                                                              │
│  ┌───────────────┐         ┌───────────────┐                               │
│  │   Content     │         │    Graph      │                               │
│  │   Strategy    │         │    Query      │                               │
│  │    Agent      │         │    Agent      │                               │
│  └───────┬───────┘         └───────┬───────┘                               │
│          │                         │                                         │
│          │  REQUEST                │                                         │
│          │  (get_brand_context)    │                                         │
│          │────────────────────────▶│                                         │
│          │                         │                                         │
│          │                         │  Execute query                          │
│          │                         │  ───────────                            │
│          │                         │                                         │
│          │  RESPONSE               │                                         │
│          │  (context_data)         │                                         │
│          │◀────────────────────────│                                         │
│          │                         │                                         │
│                                                                              │
│  Implementation: Kafka request-reply with correlation_id                    │
│  Timeout: 10 seconds                                                         │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  PATTERN 2: Fire-and-Forget (Asynchronous)                                  │
│  ──────────────────────────────────────────                                 │
│  Use when: No immediate response needed                                      │
│                                                                              │
│  ┌───────────────┐         ┌───────────────┐                               │
│  │   Validation  │         │   Feedback    │                               │
│  │    Agent      │         │   Learning    │                               │
│  │               │         │    Agent      │                               │
│  └───────┬───────┘         └───────┬───────┘                               │
│          │                         │                                         │
│          │  EVENT                  │                                         │
│          │  (brand_violation)      │                                         │
│          │────────────────────────▶│                                         │
│          │                         │                                         │
│          │  (continue immediately) │  Process async                         │
│          │                         │  ─────────────                          │
│                                                                              │
│  Implementation: Kafka event topic, consumer processes independently        │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  PATTERN 3: Scatter-Gather (Parallel)                                       │
│  ─────────────────────────────────────                                      │
│  Use when: Multiple agents needed simultaneously                             │
│                                                                              │
│  ┌───────────────┐                                                          │
│  │   Content     │                                                          │
│  │   Strategy    │                                                          │
│  └───────┬───────┘                                                          │
│          │                                                                   │
│          │  SCATTER                                                          │
│          ├────────────────────────▶ Image Generation Agent                  │
│          │                                                                   │
│          ├────────────────────────▶ Text Generation Agent                   │
│          │                                                                   │
│          │                                                                   │
│          │  GATHER (wait for all)                                           │
│          │◀──────────────────────── Image result                            │
│          │◀──────────────────────── Text result                             │
│          │                                                                   │
│          │  Continue with aggregated results                                │
│                                                                              │
│  Implementation: Temporal.io parallel activities                            │
│  Timeout: Max of individual timeouts + buffer                               │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│  PATTERN 4: Saga (Long-Running Workflow)                                    │
│  ────────────────────────────────────────                                   │
│  Use when: Multi-step with compensating actions                             │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │   plan() ──▶ retrieve() ──▶ reason() ──▶ generate() ──▶ validate() │   │
│  │      │           │            │             │              │        │   │
│  │      │           │            │             │              │        │   │
│  │      ▼           ▼            ▼             ▼              ▼        │   │
│  │   [Save      [Cache       [Save         [Save          [Log       │   │
│  │    plan]      context]     reasoning]    draft]         result]   │   │
│  │                                                                      │   │
│  │   On failure, execute compensating actions in reverse               │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Implementation: Temporal.io workflow with saga pattern                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Kafka Topic Schema

```yaml
# Topic naming convention: agent.{direction}.{agent-name}

topics:
  # Task topics (input to agents)
  - name: agent.tasks.content-strategy
    partitions: 12
    replication: 3
    retention_ms: 604800000  # 7 days
    key: tenant_id  # Partition by tenant for ordering
    
  - name: agent.tasks.graph-query
    partitions: 24
    replication: 3
    retention_ms: 86400000  # 1 day
    key: brand_id
    
  - name: agent.tasks.reasoning
    partitions: 8
    replication: 3
    retention_ms: 86400000
    key: brand_id
    
  - name: agent.tasks.image-generation
    partitions: 8
    replication: 3
    retention_ms: 86400000
    key: brand_id
    
  - name: agent.tasks.text-generation
    partitions: 12
    replication: 3
    retention_ms: 86400000
    key: brand_id
    
  - name: agent.tasks.validation
    partitions: 12
    replication: 3
    retention_ms: 86400000
    key: brand_id
    
  - name: agent.tasks.feedback-learning
    partitions: 6
    replication: 3
    retention_ms: 604800000
    key: brand_id

  # Result topics (output from agents)
  - name: agent.results.content-strategy
    partitions: 12
    replication: 3
    retention_ms: 86400000
    key: correlation_id
    
  # ... similar for other result topics

  # Event topics (cross-cutting)
  - name: graph.updates
    partitions: 6
    replication: 3
    retention_ms: 2592000000  # 30 days
    key: brand_id
    
  - name: feedback.events
    partitions: 6
    replication: 3
    retention_ms: 2592000000
    key: tenant_id
    
  - name: metrics.events
    partitions: 12
    replication: 3
    retention_ms: 604800000
    key: agent_name
```

---

## Workflow Orchestration

### Temporal.io Workflow Definition

```typescript
// Content Generation Workflow

import { proxyActivities, sleep, condition } from '@temporalio/workflow';
import type * as activities from './activities';

const { 
  parseRequest,
  queryGraph,
  generateReasoning,
  generateImage,
  generateText,
  validateContent,
  saveResult,
  notifyUser
} = proxyActivities<typeof activities>({
  startToCloseTimeout: '5 minutes',
  retry: {
    maximumAttempts: 3,
    initialInterval: '1 second',
    maximumInterval: '30 seconds',
    backoffCoefficient: 2,
  },
});

export interface ContentGenerationInput {
  requestId: string;
  tenantId: string;
  brandId: string;
  prompt: string;
  contentType: string;
  constraints: Record<string, any>;
  outputSpecs: Record<string, any>;
}

export interface ContentGenerationOutput {
  requestId: string;
  status: 'success' | 'partial' | 'failed';
  imageUri?: string;
  text?: string;
  brandScore?: number;
  errors: string[];
}

export async function contentGenerationWorkflow(
  input: ContentGenerationInput
): Promise<ContentGenerationOutput> {
  
  const errors: string[] = [];
  let retryCount = 0;
  const maxRetries = 3;

  // Step 1: Parse and validate request
  const plan = await parseRequest(input);
  
  // Step 2: Retrieve brand context from graph
  const context = await queryGraph({
    brandId: input.brandId,
    constraints: input.constraints,
    tokenBudget: 1000,
  });
  
  // Step 3: Generate reasoning (thought images, layout, bindings)
  const reasoning = await generateReasoning({
    prompt: input.prompt,
    context: context,
    outputSpecs: input.outputSpecs,
  });
  
  // Step 4: Parallel generation of image and text
  const [imageResult, textResult] = await Promise.all([
    generateImage({
      reasoning: reasoning,
      brandId: input.brandId,
      outputSpecs: input.outputSpecs,
    }),
    generateText({
      prompt: input.prompt,
      context: context,
      contentType: input.contentType,
    }),
  ]);
  
  // Step 5: Validation loop
  let validationResult = await validateContent({
    imageUri: imageResult.imageUri,
    text: textResult.text,
    brandId: input.brandId,
    constraints: context.constraints,
  });
  
  while (validationResult.brandScore < 0.90 && retryCount < maxRetries) {
    retryCount++;
    
    // Identify which component failed
    if (validationResult.imageScore < 0.90) {
      // Refine image with specific fixes
      const refinedImage = await activities.refineImage({
        originalUri: imageResult.imageUri,
        failedChecks: validationResult.imageFailures,
        reasoning: reasoning,
      });
      imageResult.imageUri = refinedImage.imageUri;
    }
    
    if (validationResult.textScore < 0.90) {
      // Regenerate text with feedback
      const refinedText = await generateText({
        prompt: input.prompt,
        context: context,
        contentType: input.contentType,
        feedback: validationResult.textFailures,
      });
      textResult.text = refinedText.text;
    }
    
    // Re-validate
    validationResult = await validateContent({
      imageUri: imageResult.imageUri,
      text: textResult.text,
      brandId: input.brandId,
      constraints: context.constraints,
    });
  }
  
  // Step 6: Save result
  await saveResult({
    requestId: input.requestId,
    imageUri: imageResult.imageUri,
    text: textResult.text,
    brandScore: validationResult.brandScore,
    metadata: {
      reasoning: reasoning,
      validationDetails: validationResult,
    },
  });
  
  // Step 7: Notify user
  await notifyUser({
    tenantId: input.tenantId,
    requestId: input.requestId,
    status: validationResult.brandScore >= 0.90 ? 'ready' : 'needs_review',
  });
  
  return {
    requestId: input.requestId,
    status: validationResult.brandScore >= 0.90 ? 'success' : 'partial',
    imageUri: imageResult.imageUri,
    text: textResult.text,
    brandScore: validationResult.brandScore,
    errors: errors,
  };
}
```

### Workflow State Machine

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONTENT GENERATION STATE MACHINE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│    ┌──────────────────────────────────────────────────────────────────┐     │
│    │                                                                   │     │
│    │   ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐   │     │
│    │   │RECEIVED │────▶│PLANNING │────▶│RETRIEV- │────▶│REASONING│   │     │
│    │   │         │     │         │     │  ING    │     │         │   │     │
│    │   └─────────┘     └────┬────┘     └────┬────┘     └────┬────┘   │     │
│    │                        │               │               │         │     │
│    │                        │ [parse_error] │ [graph_error] │ [model_ │     │
│    │                        ▼               ▼               ▼  error] │     │
│    │                   ┌─────────┐     ┌─────────┐     ┌─────────┐   │     │
│    │                   │ FAILED  │     │ FAILED  │     │ FAILED  │   │     │
│    │                   │(invalid │     │(context │     │(reason- │   │     │
│    │                   │ request)│     │ unavail)│     │ing fail)│   │     │
│    │                   └─────────┘     └─────────┘     └─────────┘   │     │
│    │                                                                   │     │
│    │   ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐   │     │
│    │   │GENERAT- │────▶│VALIDAT- │────▶│ REFINE  │────▶│VALIDAT- │   │     │
│    │   │  ING    │     │  ING    │     │  (max3) │     │  ING    │   │     │
│    │   └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘   │     │
│    │        │               │               │               │         │     │
│    │        │ [gen_error]   │ [score>=0.9]  │ [retries      │[score  │     │
│    │        ▼               ▼               ▼  exhausted]   ▼ >=0.9] │     │
│    │   ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐   │     │
│    │   │ FAILED  │     │COMPLETED│     │ PARTIAL │     │COMPLETED│   │     │
│    │   │(gen     │     │(success)│     │(needs   │     │(success)│   │     │
│    │   │ error)  │     │         │     │ review) │     │         │   │     │
│    │   └─────────┘     └─────────┘     └─────────┘     └─────────┘   │     │
│    │                                                                   │     │
│    │   Terminal states: COMPLETED, PARTIAL, FAILED                    │     │
│    │                                                                   │     │
│    └──────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│   State transitions logged to:                                               │
│   • Redis (real-time state)                                                 │
│   • PostgreSQL (audit log)                                                  │
│   • Kafka (metrics stream)                                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Failure Handling

### Failure Categories & Recovery

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FAILURE HANDLING MATRIX                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  FAILURE TYPE         │ DETECTION    │ RECOVERY STRATEGY           │     │
│  ├────────────────────────────────────────────────────────────────────┤     │
│  │                                                                     │     │
│  │  TRANSIENT FAILURES                                                │     │
│  │  ──────────────────────────────────────────────────────────────── │     │
│  │  Network timeout      │ TCP timeout  │ Retry with backoff (3x)    │     │
│  │  Rate limit (429)     │ HTTP status  │ Wait + retry (exp backoff) │     │
│  │  Service unavailable  │ 503 status   │ Circuit breaker + fallback │     │
│  │  GPU OOM              │ CUDA error   │ Reduce batch size, retry   │     │
│  │                                                                     │     │
│  │  RECOVERABLE FAILURES                                              │     │
│  │  ──────────────────────────────────────────────────────────────── │     │
│  │  Validation failed    │ Score < 0.9  │ Refinement loop (max 3)    │     │
│  │  Model output invalid │ Schema check │ Re-prompt with feedback    │     │
│  │  Graph query empty    │ Empty result │ Widen search, use defaults │     │
│  │  LoRA not found       │ 404 error    │ Fall back to base model    │     │
│  │                                                                     │     │
│  │  PERMANENT FAILURES                                                │     │
│  │  ──────────────────────────────────────────────────────────────── │     │
│  │  Invalid input        │ Validation   │ Reject, notify user        │     │
│  │  Unauthorized         │ 401/403      │ Reject, log security event │     │
│  │  Brand not found      │ Graph lookup │ Reject, suggest onboarding │     │
│  │  Constraint conflict  │ Logic error  │ Reject, explain conflict   │     │
│  │                                                                     │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Circuit Breaker Configuration

```yaml
circuit_breakers:
  graph_service:
    failure_threshold: 5
    success_threshold: 3
    timeout_ms: 30000
    half_open_requests: 3
    fallback: use_cached_context
    
  llm_api:
    failure_threshold: 10
    success_threshold: 5
    timeout_ms: 60000
    half_open_requests: 5
    fallback: use_alternate_provider  # Claude if GPT fails
    
  image_generation:
    failure_threshold: 3
    success_threshold: 2
    timeout_ms: 120000
    half_open_requests: 2
    fallback: queue_for_retry
    
  validation_service:
    failure_threshold: 5
    success_threshold: 3
    timeout_ms: 30000
    half_open_requests: 3
    fallback: pass_with_warning  # Flag for human review
```

### Dead Letter Queue Handling

```typescript
interface DeadLetterMessage {
  original_message: A2AMessage;
  failure_reason: string;
  failure_count: number;
  first_failure_at: string;
  last_failure_at: string;
  stack_trace?: string;
}

// DLQ processor (runs as scheduled job)
async function processDLQ() {
  const dlqMessages = await kafka.consume('agent.dlq');
  
  for (const dlqMsg of dlqMessages) {
    const msg: DeadLetterMessage = JSON.parse(dlqMsg.value);
    
    // Classify failure
    if (isTransientFailure(msg.failure_reason)) {
      if (msg.failure_count < 10) {
        // Retry with exponential backoff
        await scheduleRetry(msg, calculateBackoff(msg.failure_count));
      } else {
        // Escalate to human review
        await createSupportTicket(msg);
      }
    } else if (isRecoverableFailure(msg.failure_reason)) {
      // Attempt automatic recovery
      const recovered = await attemptRecovery(msg);
      if (!recovered) {
        await createSupportTicket(msg);
      }
    } else {
      // Permanent failure - notify user and log
      await notifyUserOfFailure(msg);
      await logPermanentFailure(msg);
    }
  }
}
```

---

## Observability

### Tracing Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DISTRIBUTED TRACING                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Trace propagation: W3C Trace Context (traceparent header)                  │
│  Backend: Jaeger (compatible with OpenTelemetry)                            │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    EXAMPLE TRACE                                      │   │
│  │                                                                       │   │
│  │  trace_id: abc123def456                                              │   │
│  │  ────────────────────────────────────────────────────────────────    │   │
│  │                                                                       │   │
│  │  [API Gateway]──────────────────────────────────────────────(2ms)    │   │
│  │       │                                                               │   │
│  │       └──[Content Strategy Agent]───────────────────────────(50ms)   │   │
│  │              │                                                        │   │
│  │              ├──[Graph Query Agent]────────────────────────(80ms)    │   │
│  │              │       │                                                │   │
│  │              │       ├──[neo4j_query]──────────────────────(45ms)    │   │
│  │              │       └──[pgvector_search]──────────────────(25ms)    │   │
│  │              │                                                        │   │
│  │              └──[Reasoning Agent]───────────────────────(4200ms)     │   │
│  │                     │                                                 │   │
│  │                     └──[reasoning_model_inference]────(4000ms)       │   │
│  │                                                                       │   │
│  │  [Image Generation Agent]───────────────────────────────(18000ms)    │   │
│  │       │                                                               │   │
│  │       ├──[lora_load]──────────────────────────────────────(500ms)    │   │
│  │       ├──[sdxl_inference]─────────────────────────────(15000ms)      │   │
│  │       └──[s3_upload]─────────────────────────────────────(800ms)     │   │
│  │                                                                       │   │
│  │  [Text Generation Agent]────────────────────────────────(3000ms)     │   │
│  │       │                                                               │   │
│  │       └──[llm_call]──────────────────────────────────────(2800ms)    │   │
│  │                                                                       │   │
│  │  [Validation Agent]──────────────────────────────────────(1500ms)    │   │
│  │       │                                                               │   │
│  │       ├──[clip_similarity]───────────────────────────────(400ms)     │   │
│  │       ├──[ssim_compare]──────────────────────────────────(200ms)     │   │
│  │       └──[color_extract]─────────────────────────────────(150ms)     │   │
│  │                                                                       │   │
│  │  Total: 24,832ms                                                      │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Metrics Dashboard

```yaml
# Prometheus metrics exported by each agent

# Agent-level metrics
agent_requests_total:
  type: counter
  labels: [agent_name, status, tenant_id]
  
agent_request_duration_seconds:
  type: histogram
  labels: [agent_name, action]
  buckets: [0.1, 0.5, 1, 2, 5, 10, 30, 60, 120]
  
agent_active_tasks:
  type: gauge
  labels: [agent_name]

# Tool-level metrics
mcp_tool_calls_total:
  type: counter
  labels: [tool_name, status]
  
mcp_tool_duration_seconds:
  type: histogram
  labels: [tool_name]
  buckets: [0.01, 0.05, 0.1, 0.5, 1, 5, 10, 30]

# Workflow metrics
workflow_started_total:
  type: counter
  labels: [workflow_type, tenant_id]
  
workflow_completed_total:
  type: counter
  labels: [workflow_type, status]
  
workflow_duration_seconds:
  type: histogram
  labels: [workflow_type]
  buckets: [1, 5, 10, 30, 60, 120, 300]

# Business metrics
brand_score_distribution:
  type: histogram
  labels: [brand_id]
  buckets: [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0]
  
content_approved_total:
  type: counter
  labels: [brand_id, content_type]
  
refinement_iterations_total:
  type: counter
  labels: [brand_id, reason]
```

### Grafana Dashboard Panels

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AGENT ORCHESTRATION DASHBOARD                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ROW 1: System Health                                                        │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌───────────┐  │
│  │ Request Rate    │ │ Error Rate      │ │ P95 Latency     │ │ Active    │  │
│  │ ████████████    │ │ ██              │ │ █████           │ │ Workflows │  │
│  │ 127 req/min     │ │ 0.3%            │ │ 24.5s           │ │ 89        │  │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘ └───────────┘  │
│                                                                              │
│  ROW 2: Agent Performance                                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  Agent               │ Throughput │ P50 Latency │ P95 Latency │ Errors │ │
│  │  ────────────────────────────────────────────────────────────────────  │ │
│  │  content-strategy    │  45/min    │    120ms    │    350ms    │  0.1%  │ │
│  │  graph-query         │ 180/min    │     45ms    │     95ms    │  0.0%  │ │
│  │  reasoning           │  12/min    │   3,500ms   │   4,800ms   │  0.5%  │ │
│  │  image-generation    │  10/min    │  15,000ms   │  22,000ms   │  1.2%  │ │
│  │  text-generation     │  40/min    │   2,200ms   │   4,500ms   │  0.2%  │ │
│  │  validation          │  22/min    │   1,100ms   │   1,800ms   │  0.0%  │ │
│  │  feedback-learning   │   8/min    │    800ms    │   1,500ms   │  0.1%  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ROW 3: Brand Quality                                                        │
│  ┌─────────────────────────────┐ ┌─────────────────────────────────────────┐│
│  │ Brand Score Distribution    │ │ Approval Rate by Brand                  ││
│  │                             │ │                                         ││
│  │      ▂▃▅███▇▃▂              │ │ Brand A: ███████████████ 92%           ││
│  │     <0.7  0.9  1.0          │ │ Brand B: █████████████   85%           ││
│  │                             │ │ Brand C: ████████████████ 94%          ││
│  │  Mean: 0.91  Median: 0.93   │ │ Brand D: ██████████      78%           ││
│  └─────────────────────────────┘ └─────────────────────────────────────────┘│
│                                                                              │
│  ROW 4: Resource Utilization                                                 │
│  ┌─────────────────────────────┐ ┌─────────────────────────────────────────┐│
│  │ GPU Utilization             │ │ Kafka Consumer Lag                      ││
│  │                             │ │                                         ││
│  │  Reasoning: ████████  78%   │ │ content-strategy: 12                    ││
│  │  Image Gen: █████████ 85%   │ │ image-generation: 45 ⚠️                 ││
│  │  Validation: ███      32%   │ │ validation:       8                     ││
│  │                             │ │                                         ││
│  └─────────────────────────────┘ └─────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Next Document

Continue to **[05-monitoring-framework.md](./05-monitoring-framework.md)** for the comprehensive observability and alerting design.
