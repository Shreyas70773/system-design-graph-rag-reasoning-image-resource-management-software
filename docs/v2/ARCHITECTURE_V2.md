# ARCHITECTURE_V2

**Version:** 2.0.0  
**Derives from:** `GRAPH_SCHEMA_V2.md`  
**Drives:** the three pipeline specs and the module layout under `backend/app/`

---

## 1. System topology

```
                         ┌─────────────────────────────────────────┐
                         │                Browser (React + R3F)    │
                         │  Asset Editor | 3D Canvas | 2D Canvas   │
                         └────────────┬────────────────────────────┘
                                      │ HTTPS / WebSocket
                                      ▼
                    ┌─────────────────────────────────────────────┐
                    │   FastAPI (V1 routes + V2 routes under /v2) │
                    └──┬────────────────┬────────────────┬────────┘
                       │                │                │
             ┌─────────▼───┐    ┌───────▼─────┐   ┌──────▼────────┐
             │ Pipeline A  │    │ Pipeline B  │   │ Pipeline C    │
             │ (Ingestion) │    │ (Assembly)  │   │ (Interaction) │
             └────────┬────┘    └──────┬──────┘   └──────┬────────┘
                      │                │                 │
                      ▼                ▼                 ▼
                 ┌────────────────────────────────────────────┐
                 │                Neo4j (V2 schema)           │
                 └────────────────────────────────────────────┘
                      ▲                ▲                 ▲
                      │                │                 │
                 ┌────┴─────────┐ ┌────┴────────┐  ┌─────┴──────┐
                 │ Model Hub    │ │ Blender BPY │  │ Learning   │
                 │ (FLUX, TREL- │ │ headless    │  │ signal     │
                 │  LIS, SAM,   │ │ render      │  │ distiller  │
                 │  Qwen-VL)    │ │ subprocess  │  │            │
                 └──────────────┘ └─────────────┘  └────────────┘
                      │
                 ┌────┴──────────────────────────────────────┐
                 │ Object storage (Cloudflare R2 / local)    │
                 │  - GLB meshes, HDRIs, textures, renders   │
                 └───────────────────────────────────────────┘
```

## 2. Process boundaries

| Process | Runtime | Purpose |
|---|---|---|
| FastAPI main | uvicorn async | Request handling, graph writes, queue dispatch |
| Pipeline A workers | Python subprocess | Asset ingestion (GPU-bound) |
| Pipeline B workers | Python subprocess | Scene assembly + refinement (GPU-bound) |
| Blender BPY worker | Python subprocess calling Blender CLI | 3D render to RGB + passes |
| Pipeline C | In-process | CPU-bound: graph writes, signal distillation |

Workers communicate with the main process via a Redis-backed queue (MVP: SQLite-backed for simplicity, swap Redis in Phase 2). Each worker holds at most one GPU model loaded at a time. Model swap between jobs is mandatory.

## 3. Module layout under `backend/app/`

```
backend/app/
├── schema_v2.py                # Pydantic models derived from GRAPH_SCHEMA_V2
├── scene/                      # Pipeline B — scene assembly + rendering
│   ├── __init__.py
│   ├── models.py               # Scene, Placement, Camera, Light, TextLayer
│   ├── assembler.py            # Intent + graph → scene state
│   ├── blender_bridge.py       # Subprocess wrapper around Blender BPY
│   ├── refinement.py           # FLUX / SDXL refinement pass
│   └── neo4j_access.py         # Pipeline-scoped Neo4j client (ACL-limited)
├── ingestion/                  # Pipeline A — asset decomposition
│   ├── __init__.py
│   ├── models.py               # Ingestion job state machine
│   ├── steps/
│   │   ├── describe.py         # Qwen2.5-VL step
│   │   ├── segment.py          # SAM 2.1 + GroundingDINO step
│   │   ├── delight.py          # IntrinsicAnything step
│   │   ├── mesh.py             # TRELLIS step
│   │   └── validate.py         # CLIP re-render similarity check
│   ├── orchestrator.py         # Step scheduling, VRAM-aware
│   └── neo4j_access.py
├── interaction/                # Pipeline C — edit events to preference signals
│   ├── __init__.py
│   ├── models.py
│   ├── command_parser.py       # VLM natural-language → structured command
│   ├── applier.py              # Structured command → graph mutation
│   ├── distiller.py            # Interactions → PreferenceSignals
│   ├── retrieval_bias.py       # PreferenceSignals → conditioning adjustments
│   └── neo4j_access.py
├── rendering/                  # Shared render helpers (not a pipeline)
│   ├── __init__.py
│   ├── object_id_pass.py
│   ├── depth_pass.py
│   └── hdri_utils.py
└── routers/
    ├── v2_assets.py            # /api/v2/assets/*
    ├── v2_scenes.py            # /api/v2/scenes/*
    ├── v2_renders.py           # /api/v2/renders/*
    ├── v2_interactions.py      # /api/v2/interactions/*
    └── v2_brands.py            # /api/v2/brands/* (preferences panel)
```

## 4. Data-flow contracts between pipelines

### 4.1 Pipeline A → Graph → Pipeline B
Pipeline A writes `Asset` with `ingestion_status = approved`. Pipeline B is **forbidden** from querying assets with any other status. Enforced by Cypher filter in every Pipeline B read query.

### 4.2 Pipeline B → Graph → User → Pipeline C
Pipeline B writes `Scene`, `Placement`, `Render`. User interacts. The frontend sends interaction events to Pipeline C endpoints. Pipeline C writes `Interaction` nodes and (when threshold reached) `PreferenceSignal` nodes.

### 4.3 Pipeline C → Graph → Pipeline B (feedback loop)
Before Pipeline B starts a new scene for a brand, it reads `PreferenceSignal`s for that brand and applies them as soft biases in the conditioning bundle. This closes the learning loop **at retrieval time, not at training time**.

## 5. Scene-graph JSON contract (LLM output)

Pipeline B Step 1 parses user intent into this structure. Locked.

```json
{
  "scene_id": "uuid",
  "brand_id": "uuid",
  "deployment_context": "digital|print|ooh",
  "placements": [
    {
      "asset_id": "uuid | null",
      "asset_query": "outdoor-adventurer | null",
      "role": "hero | supporting | environment | background",
      "position_hint": "center|left-third|right-third|...",
      "z_order": 0
    }
  ],
  "cameras": [
    { "shot_type": "hero|detail|wide", "aspect_ratio": "1:1|16:9|9:16" }
  ],
  "lights": [
    { "mood": "golden-hour|overcast|studio|high-key", "direction_hint": "upper-left|..." }
  ],
  "terrain": { "type": "grass|sand|none", "extent_m": [10, 10] } ,
  "text_layers": [
    { "text": "Summer Sale", "position_hint": "bottom-center", "role": "headline|body|cta" }
  ]
}
```

`asset_id` wins over `asset_query`. If only `asset_query` is present, Pipeline B resolves it via graph-RAG (vector search within the brand's assets, filtered by `ingestion_status = approved` and deployment context).

## 6. Hard invariants

The following invariants are enforced in code and asserted in CI. Violations are bugs.

| # | Invariant | Where enforced |
|---|---|---|
| I-1 | No Pipeline writes to a node it does not own (see write-ownership matrix in GRAPH_SCHEMA_V2 §4) | Neo4j per-pipeline users + Cypher filters |
| I-2 | Every `Placement` references an `Asset` with `ingestion_status = approved` | Pipeline B write guard |
| I-3 | Every `Interaction` has a resolved `structured_command_json` before commit | Pipeline C write guard |
| I-4 | Every `Render` carries a valid `object_id_pass_url` | Pipeline B write guard |
| I-5 | `PreferenceSignal.weight` is never negative and `direction ∈ [-1, +1]` | Pipeline C distiller assertion |
| I-6 | Only one GPU model is loaded in a worker at any time | Worker lifecycle check |
| I-7 | Peak VRAM per stage ≤ 11.5 GB on 12 GB card | `vram_profile_v2.py` CI gate |
| I-8 | Live Neo4j schema matches `GRAPH_SCHEMA_V2.md` | `validate_graph_schema.py` CI gate |

## 7. Versioning policy

- `schema_version` — bound to `GRAPH_SCHEMA_V2.md` header; bumped per migration
- `pipeline_version` on `DecompositionRun` — bumped when Pipeline A step list changes
- `model_version` on `Render.refinement_model` — always the resolved model string, never a shorthand

A render can be reproduced from its `DecompositionRun` versions + `Render` metadata alone. Reproducibility is a first-class property.
