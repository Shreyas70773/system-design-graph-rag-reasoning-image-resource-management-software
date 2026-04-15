# Brand-Aligned Content Generation Platform
## System Architecture Overview

**Version**: 1.0  
**Date**: January 2026  
**Status**: Design Phase

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Architecture Principles](#architecture-principles)
3. [High-Level System Architecture](#high-level-system-architecture)
4. [Component Breakdown](#component-breakdown)
5. [Data Flow Diagrams](#data-flow-diagrams)
6. [Technology Stack](#technology-stack)
7. [Open Questions Resolution](#open-questions-resolution)

---

## Executive Summary

This document describes the architecture for a **production-grade, graph-augmented content generation system** that combines:

- **Semantic Knowledge Graphs** for brand identity representation
- **GraphRAG** for context-aware retrieval during generation
- **Reasoning-Augmented Generation** for planning before synthesis
- **Multi-Agent Orchestration** for modular, scalable workflows
- **Continuous Learning** from user feedback loops

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Graph Database | **Neo4j + pgvector hybrid** | Neo4j for graph traversal, pgvector for embeddings co-location |
| Image Generation | **Fine-tuned SDXL + Custom Reasoning Head** | Balance between quality, cost, and customization |
| Agent Protocol | **MCP + A2A over Kafka** | Standardized tool use + async agent coordination |
| Multi-Tenancy | **Shared compute, isolated data** | Cost-efficient with strong data boundaries |
| Feedback Processing | **Hybrid: real-time for critical, batch for aggregate** | Immediate graph updates for explicit signals |

---

## Architecture Principles

### 1. Separation of Concerns (Thinker-Generator-Validator)
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GENERATION PIPELINE                              │
├─────────────────┬─────────────────┬─────────────────┬───────────────────┤
│    RETRIEVER    │     THINKER     │    GENERATOR    │    VALIDATOR      │
│                 │                 │                 │                   │
│ • Graph Query   │ • Reasoning     │ • Pixel/Token   │ • Constraint      │
│ • Vector Search │ • Planning      │   Synthesis     │   Checking        │
│ • Context       │ • Constraint    │ • Refinement    │ • Brand Score     │
│   Assembly      │   Binding       │                 │   Computation     │
└─────────────────┴─────────────────┴─────────────────┴───────────────────┘
```

### 2. Graph as Source of Truth
- All brand knowledge versioned in graph structures
- Generation guided by graph-based semantic priors
- User feedback modifies graph edges/attributes directly

### 3. Explicit Reasoning Before Synthesis
```
Input → Graph Traversal → Reasoning Phase → Generation Phase → Validation
                ↓               ↓                  ↓               ↓
         [Context]      [Thought Images]     [Final Output]  [Brand Score]
```

### 4. Production-First Design
- 99.9% uptime with graceful degradation
- Cost-per-generation optimization
- Observability at every pipeline stage

---

## High-Level System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                    CLIENT LAYER                                           │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   Web Dashboard │  │   Mobile App    │  │   API Clients   │  │   Integrations  │     │
│  │   (React/Next)  │  │   (Future)      │  │   (REST/GraphQL)│  │   (Zapier/etc)  │     │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘     │
└───────────┼────────────────────┼────────────────────┼────────────────────┼───────────────┘
            │                    │                    │                    │
            └────────────────────┴──────────┬─────────┴────────────────────┘
                                            │
┌───────────────────────────────────────────┼──────────────────────────────────────────────┐
│                                   API GATEWAY                                             │
├───────────────────────────────────────────┼──────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────────────────┐     │
│  │  Kong/AWS API Gateway                                                            │     │
│  │  • Authentication (JWT/OAuth2)  • Rate Limiting  • Request Routing              │     │
│  │  • Multi-tenant Isolation       • SSL Termination  • Request Logging            │     │
│  └─────────────────────────────────────────────────────────────────────────────────┘     │
└───────────────────────────────────────────┬──────────────────────────────────────────────┘
                                            │
┌───────────────────────────────────────────┼──────────────────────────────────────────────┐
│                              ORCHESTRATION LAYER                                          │
├───────────────────────────────────────────┼──────────────────────────────────────────────┤
│                    ┌──────────────────────┴────────────────────┐                         │
│                    │        WORKFLOW ORCHESTRATOR              │                         │
│                    │        (Temporal.io)                      │                         │
│                    │                                           │                         │
│                    │  • Saga Patterns for Multi-Step Workflows │                         │
│                    │  • Retry Logic with Exponential Backoff   │                         │
│                    │  • Workflow Versioning & Migration        │                         │
│                    │  • Long-Running Process Management        │                         │
│                    └───────────────────┬───────────────────────┘                         │
│                                        │                                                  │
│    ┌───────────────────────────────────┼───────────────────────────────────┐             │
│    │                     MESSAGE BUS (Apache Kafka)                        │             │
│    │  Topics: generation.requests | feedback.events | graph.updates       │             │
│    │          agent.tasks | metrics.events | audit.logs                   │             │
│    └───────────────────────────────────┬───────────────────────────────────┘             │
└───────────────────────────────────────────────────────────────────────────────────────────┘
                                         │
┌────────────────────────────────────────┼─────────────────────────────────────────────────┐
│                              AGENT LAYER (A2A Protocol)                                   │
├────────────────────────────────────────┼─────────────────────────────────────────────────┤
│                                        │                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │ BRAND           │  │ CONTENT         │  │ REASONING       │  │ IMAGE           │     │
│  │ INTELLIGENCE    │  │ STRATEGY        │  │ AGENT           │  │ GENERATION      │     │
│  │ AGENT           │  │ AGENT           │  │                 │  │ AGENT           │     │
│  │                 │  │                 │  │ • Thought Image │  │                 │     │
│  │ • Graph CRUD    │  │ • Request Parse │  │   Generation    │  │ • SDXL/Flux     │     │
│  │ • Schema Mgmt   │  │ • Plan Creation │  │ • Layout Plan   │  │ • ControlNet    │     │
│  │ • Version Ctrl  │  │ • Orchestration │  │ • Color Binding │  │ • Refinement    │     │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘     │
│           │                    │                    │                    │               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │ TEXT            │  │ VALIDATION      │  │ FEEDBACK        │  │ GRAPH QUERY     │     │
│  │ GENERATION      │  │ AGENT           │  │ LEARNING        │  │ AGENT           │     │
│  │ AGENT           │  │                 │  │ AGENT           │  │ (GraphRAG)      │     │
│  │                 │  │ • Constraint    │  │                 │  │                 │     │
│  │ • GPT-4/Claude  │  │   Checking      │  │ • Signal        │  │ • Multi-Hop     │     │
│  │ • Brand Voice   │  │ • Brand Score   │  │   Aggregation   │  │   Traversal     │     │
│  │ • Multi-Lang    │  │ • Violation     │  │ • Graph Mutate  │  │ • Hybrid Search │     │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘     │
│           │                    │                    │                    │               │
└───────────┴────────────────────┴────────────────────┴────────────────────┴───────────────┘
            │                    │                    │                    │
┌───────────┴────────────────────┴────────────────────┴────────────────────┴───────────────┐
│                              SERVICE LAYER (MCP Protocol)                                 │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │ GRAPH SERVICE   │  │ VECTOR SERVICE  │  │ STORAGE SERVICE │  │ ML INFERENCE    │     │
│  │                 │  │                 │  │                 │  │ SERVICE         │     │
│  │ • Neo4j Driver  │  │ • Embedding Gen │  │ • S3/GCS       │  │                 │     │
│  │ • Cypher Query  │  │ • ANN Search    │  │ • CDN Assets   │  │ • Model Serving │     │
│  │ • Schema Valid  │  │ • Index Mgmt    │  │ • Blob Storage │  │ • Batch/Stream  │     │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘     │
│           │                    │                    │                    │               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │ EXTERNAL APIs   │  │ FEEDBACK        │  │ SCHEDULING      │  │ NOTIFICATION    │     │
│  │ SERVICE         │  │ SERVICE         │  │ SERVICE         │  │ SERVICE         │     │
│  │                 │  │                 │  │                 │  │                 │     │
│  │ • OpenAI/Claude │  │ • Signal Ingest │  │ • Cron Jobs     │  │ • Email/Slack   │     │
│  │ • Ad Platforms  │  │ • Aggregation   │  │ • Calendar Sync │  │ • Webhooks      │     │
│  │ • Analytics     │  │ • Persistence   │  │ • Publishing    │  │ • Push Notifs   │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│                                                                                           │
└──────────────────────────────────────────────────────────────────────────────────────────┘
                                            │
┌───────────────────────────────────────────┼──────────────────────────────────────────────┐
│                              DATA LAYER                                                   │
├───────────────────────────────────────────┼──────────────────────────────────────────────┤
│                                           │                                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐     │
│  │                           PRIMARY DATA STORES                                    │     │
│  │                                                                                  │     │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐    │     │
│  │  │   Neo4j       │  │  PostgreSQL   │  │   Redis       │  │     S3        │    │     │
│  │  │   (Graph)     │  │  + pgvector   │  │   (Cache)     │  │  (Assets)     │    │     │
│  │  │               │  │               │  │               │  │               │    │     │
│  │  │ • Brand Graph │  │ • User Data   │  │ • Session     │  │ • Images      │    │     │
│  │  │ • Ontologies  │  │ • Embeddings  │  │ • Hot Graph   │  │ • Models      │    │     │
│  │  │ • Relations   │  │ • Analytics   │  │ • Rate Limit  │  │ • Exports     │    │     │
│  │  │ • Versions    │  │ • Audit Logs  │  │ • Pub/Sub     │  │ • Backups     │    │     │
│  │  └───────────────┘  └───────────────┘  └───────────────┘  └───────────────┘    │     │
│  └─────────────────────────────────────────────────────────────────────────────────┘     │
│                                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐     │
│  │                           SPECIALIZED STORES                                     │     │
│  │                                                                                  │     │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                        │     │
│  │  │ ClickHouse    │  │ Elasticsearch │  │ TimescaleDB   │                        │     │
│  │  │ (Analytics)   │  │ (Full-Text)   │  │ (Time-Series) │                        │     │
│  │  │               │  │               │  │               │                        │     │
│  │  │ • Events      │  │ • Content     │  │ • Metrics     │                        │     │
│  │  │ • Metrics     │  │ • Search      │  │ • Traces      │                        │     │
│  │  │ • Aggregates  │  │ • Logs        │  │ • SLOs        │                        │     │
│  │  └───────────────┘  └───────────────┘  └───────────────┘                        │     │
│  └─────────────────────────────────────────────────────────────────────────────────┘     │
│                                                                                           │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Client Layer
| Component | Technology | Responsibility |
|-----------|------------|----------------|
| Web Dashboard | Next.js 14 + React | Content management, brand settings, analytics |
| API Gateway | Kong / AWS API Gateway | Auth, rate limiting, routing, multi-tenant isolation |

### 2. Orchestration Layer
| Component | Technology | Responsibility |
|-----------|------------|----------------|
| Workflow Engine | Temporal.io | Long-running workflows, saga patterns, retry logic |
| Message Bus | Apache Kafka | Async event streaming, agent coordination |
| Task Queue | Redis + Bull | Short-lived job processing |

### 3. Agent Layer (8 Specialized Agents)
| Agent | Primary Function | Dependencies |
|-------|------------------|--------------|
| Brand Intelligence | Graph construction & maintenance | Neo4j, Web Scraper |
| Content Strategy | Request parsing, plan generation | LLM (GPT-4), Graph Query |
| Reasoning | Thought image generation, layout planning | Custom Reasoning Model |
| Image Generation | High-res pixel synthesis | SDXL, ControlNet |
| Text Generation | Brand-aligned copywriting | GPT-4/Claude |
| Validation | Constraint checking, brand scoring | Graph Service, Vision Model |
| Feedback Learning | Signal aggregation, graph mutation | Kafka, Neo4j |
| Graph Query (GraphRAG) | Multi-hop traversal, hybrid search | Neo4j, pgvector |

### 4. Service Layer (MCP Tools)
| Service | Protocol | Function |
|---------|----------|----------|
| Graph Service | MCP Tool | CRUD operations on brand graph |
| Vector Service | MCP Tool | Embedding generation, similarity search |
| Storage Service | MCP Tool | Asset management (S3/CDN) |
| ML Inference | MCP Tool | Model serving (TorchServe/Triton) |
| External APIs | MCP Tool | OpenAI, Claude, ad platform connectors |

### 5. Data Layer
| Store | Technology | Data Type | Retention |
|-------|------------|-----------|-----------|
| Graph DB | Neo4j Enterprise | Brand ontology, relations | Indefinite (versioned) |
| Vector DB | PostgreSQL + pgvector | Embeddings (512-1536 dim) | 90 days (archived) |
| Cache | Redis Cluster | Hot data, sessions | 24 hours |
| Object Store | S3 + CloudFront | Generated assets, models | 1 year |
| Analytics | ClickHouse | Event streams, metrics | 2 years |

---

## Data Flow Diagrams

### Content Generation Flow (Happy Path)

```
┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  User   │    │   API       │    │  Content    │    │   Graph     │    │  Reasoning  │
│ Request │───▶│  Gateway    │───▶│  Strategy   │───▶│   Query     │───▶│   Agent     │
│         │    │             │    │   Agent     │    │   Agent     │    │             │
└─────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                                │
                    ┌───────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────┐
│   Image     │    │    Text     │    │ Validation  │    │  Dashboard  │    │  User   │
│ Generation  │───▶│ Generation  │───▶│   Agent     │───▶│   (Preview) │───▶│ Review  │
│   Agent     │    │   Agent     │    │             │    │             │    │         │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────┘
       │                  │                  │
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              Kafka Event Stream                                       │
│  generation.started → generation.image.complete → generation.text.complete →         │
│  validation.complete → generation.ready_for_review                                   │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### Feedback Loop Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    User     │    │  Feedback   │    │   Signal    │    │   Graph     │
│  Feedback   │───▶│   Service   │───▶│  Classifier │───▶│  Mutation   │
│  (UI/API)   │    │             │    │             │    │  Proposer   │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                │
                                                                ▼
                   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
                   │   Graph     │    │  Conflict   │    │  Version    │
                   │   Commit    │◀───│  Resolver   │◀───│  Validator  │
                   │             │    │             │    │             │
                   └──────┬──────┘    └─────────────┘    └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │  Retrain    │
                   │  Signal     │ (if threshold reached)
                   │  Emitter    │
                   └─────────────┘
```

---

## Technology Stack

### Infrastructure
```yaml
Cloud Provider: AWS (primary) / GCP (secondary for ML)
Container Orchestration: Amazon EKS (Kubernetes 1.28+)
Service Mesh: Istio (mTLS, traffic management)
Infrastructure as Code: Terraform + Pulumi
CI/CD: GitHub Actions + ArgoCD
Secrets Management: HashiCorp Vault
```

### Data Stores
```yaml
Graph Database: Neo4j Enterprise 5.x (Aura for managed)
Relational + Vector: PostgreSQL 15 + pgvector extension
Cache: Redis 7.x Cluster (ElastiCache)
Object Storage: S3 + CloudFront CDN
Message Queue: Amazon MSK (Managed Kafka)
Analytics: ClickHouse Cloud
Search: Elasticsearch 8.x (OpenSearch compatible)
```

### AI/ML Stack
```yaml
LLM Provider: OpenAI GPT-4 Turbo (primary), Anthropic Claude 3 (fallback)
Image Generation: Fine-tuned SDXL 1.0 + Custom Reasoning Head
Embedding Model: OpenAI text-embedding-3-large (1536 dim)
Model Serving: NVIDIA Triton Inference Server
Training: PyTorch 2.x + DeepSpeed
Experiment Tracking: Weights & Biases
```

### Application Stack
```yaml
API Framework: FastAPI (Python) / NestJS (TypeScript)
Frontend: Next.js 14 + TailwindCSS + shadcn/ui
Workflow Engine: Temporal.io
Agent Framework: Custom (MCP + A2A protocols)
Monitoring: Prometheus + Grafana + Jaeger
Logging: Vector + Loki
```

---

## Open Questions Resolution

### Q1: Graph Database Selection
**Decision**: Neo4j + pgvector Hybrid

**Rationale**:
| Requirement | Neo4j | TigerGraph | Custom |
|-------------|-------|------------|--------|
| GraphRAG patterns | ★★★★★ | ★★★★☆ | ★★☆☆☆ |
| Vector search native | ★★★☆☆ | ★★☆☆☆ | ★★★★★ |
| Operational maturity | ★★★★★ | ★★★★☆ | ★★☆☆☆ |
| Multi-tenancy | ★★★★☆ | ★★★☆☆ | ★★★★★ |
| Cost at scale | ★★★☆☆ | ★★☆☆☆ | ★★★★☆ |

**Architecture**:
- **Neo4j**: Graph structure, relationships, traversal queries
- **pgvector**: Co-located embeddings for hybrid search
- **Redis**: Hot graph cache for <100ms queries

### Q2: Image Model Strategy
**Decision**: Fine-tuned SDXL + Custom Reasoning Head

**Approach**:
1. **Base Model**: SDXL 1.0 (open-source, fine-tunable)
2. **Reasoning Head**: Custom transformer layer trained on:
   - Thought image generation (low-res compositional sketches)
   - Brand constraint encoding (graph → latent space)
3. **ControlNet**: Logo placement, layout enforcement
4. **LoRA Adapters**: Per-brand fine-tuning (lightweight)

**Cost Model**:
| Approach | Quality | Latency | Cost/Image | Customization |
|----------|---------|---------|------------|---------------|
| API (DALL-E 3) | High | 5-10s | $0.04-0.12 | Low |
| SDXL (self-hosted) | High | 15-25s | $0.01-0.02 | High |
| **SDXL + Reasoning** | Higher | 20-30s | $0.02-0.03 | Very High |

### Q3: Feedback Aggregation Strategy
**Decision**: Hybrid (Real-time + Batch)

**Real-time Processing** (< 5 minute reflection):
- Explicit negative signals (rejection, brand violation flag)
- Critical constraint additions ("never use this color")
- High-confidence corrections (>95% classification confidence)

**Batch Processing** (nightly):
- Implicit signals (engagement metrics, edit distance)
- Low-confidence signals requiring human review
- Aggregate trend analysis (seasonal adjustments)

**Architecture**:
```
Real-time Path:
  User Feedback → Kafka → Signal Classifier → 
    IF confidence > 0.95 AND signal_type IN (explicit_negative, constraint_add):
      → Immediate Graph Mutation → Cache Invalidation
    ELSE:
      → Batch Queue

Batch Path:
  Feedback Events (24h window) → Aggregation Pipeline →
    Human Review Dashboard → Approved Mutations → Graph Commit
```

### Q4: Multi-Tenancy Strategy
**Decision**: Shared Compute, Isolated Data

**Isolation Boundaries**:
| Layer | Isolation Level | Mechanism |
|-------|-----------------|-----------|
| Graph Data | Full isolation | Separate Neo4j databases per tenant |
| Embeddings | Full isolation | Tenant-prefixed vectors in pgvector |
| Models | Shared base + Isolated LoRA | Per-brand LoRA adapters |
| Compute | Shared with resource quotas | K8s resource quotas + priority classes |
| API | Logical isolation | JWT tenant claims, request routing |

**Cost Efficiency**:
- Shared GPU pools (3-5x cost reduction vs dedicated)
- Per-tenant billing via metering service
- Burst capacity sharing across tenants

### Q5: Caching Strategy
**Decision**: Multi-Layer Caching with Intelligent Invalidation

**Cache Layers**:
```
┌─────────────────────────────────────────────────────────────────┐
│  L1: CDN (CloudFront)                                           │
│  • Generated images (immutable, 1 year TTL)                     │
│  • Static brand assets (logos, fonts)                           │
│  Hit Rate Target: 85%+                                          │
├─────────────────────────────────────────────────────────────────┤
│  L2: Redis Cluster                                              │
│  • Hot graph subgraphs (brand constraints for active campaigns) │
│  • Recent generation results (deduplication)                    │
│  • Session data, rate limit counters                            │
│  TTL: 1-24 hours (adaptive)                                     │
│  Hit Rate Target: 70%+                                          │
├─────────────────────────────────────────────────────────────────┤
│  L3: Local (Pod-level)                                          │
│  • Embedding model weights                                      │
│  • Compiled Cypher query plans                                  │
│  TTL: Pod lifetime                                              │
└─────────────────────────────────────────────────────────────────┘
```

**Invalidation Strategy**:
- Graph mutations → Targeted cache invalidation via Redis Pub/Sub
- Content-addressable keys for generated assets (never invalidate, only add)
- Version-based cache keys for brand configurations

---

## Next Steps

1. **[02-graphrag-design.md](./02-graphrag-design.md)**: Detailed GraphRAG schema and query patterns
2. **[03-image-generation-pipeline.md](./03-image-generation-pipeline.md)**: Reasoning-augmented generation architecture
3. **[04-agent-orchestration.md](./04-agent-orchestration.md)**: Multi-agent coordination blueprint
4. **[05-monitoring-framework.md](./05-monitoring-framework.md)**: Observability and alerting
5. **[06-implementation-roadmap.md](./06-implementation-roadmap.md)**: Phased delivery plan

---

*Document Owner: System Architecture Team*  
*Last Updated: January 2026*
