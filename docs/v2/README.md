# V2 — Graph-RAG Conditioned 3D Scene Authoring

**Status:** Active development  
**Start date:** 2026-04-17  
**Target completion:** 16–20 weeks  
**Scope:** Replace the V1 2D-layer image pipeline with a 3D-first brand-aware scene authoring system whose rendered 2D views are a side effect of an inspectable, editable, learning graph.

---

## What V2 is

A brand-aware 3D scene editor in which:

1. **Every brand asset is decomposed in the graph.** No base64 blobs. Every product, character, and environment reference is stored as a cluster of inspectable nodes (geometry, materials, semantic parts, light probes, decomposition provenance).
2. **The 3D scene is the canonical artifact.** 2D images are renders of it from named cameras. Multiple camera angles of the same scene are free.
3. **Every user interaction is a first-class graph citizen.** Drag, rotate, delete, right-click-change, circle-and-describe — all become `Interaction` nodes linked to what they modified, producing `PreferenceSignal`s that modulate future retrieval.
4. **Edits in 2D round-trip through 3D.** Clicking an object on a flat render resolves to its `Placement` node via a hidden object-ID pass; the edit happens on the 3D scene and the 2D render is recomputed. There is no 2D-only editing path except for truly 2D artefacts (text layers, post-process grading).

## What V2 is NOT

- Not an incremental upgrade of V1's SDXL-plus-ControlNet generator.
- Not a replacement for Blender. We use Blender (BPY) headlessly as one stage.
- Not a retrieval-augmented prompt-stuffing system.

---

## How to read this folder

Read in this order. Each document references the ones above it.

| # | Document | What it locks down |
|---|---|---|
| 1 | `PRD.md` | Product vision, personas, user stories, acceptance criteria |
| 2 | `GRAPH_SCHEMA_V2.md` | **The source of truth.** Every node/relationship/property. Every other doc derives from this. |
| 3 | `ARCHITECTURE_V2.md` | High-level system topology; how pipelines A/B/C connect |
| 4 | `PIPELINE_A_ASSET_INGESTION.md` | 2D brand asset → decomposed 3D graph cluster, with user approval |
| 5 | `PIPELINE_B_SCENE_ASSEMBLY.md` | Graph + intent → 3D scene → multi-view 2D renders |
| 6 | `PIPELINE_C_INTERACTION_LEARNING.md` | User edits → graph mutations → preference signals → retrieval modulation |
| 7 | `MODEL_STACK_V2.md` | Every model we load, why, version, VRAM cost |
| 8 | `VRAM_BUDGET_V2.md` | Per-stage VRAM accounting for the 12 GB 5070 Ti Ultra target |
| 9 | `API_CONTRACT_V2.md` | New FastAPI endpoints for V2 |
| 10 | `IMPLEMENTATION_ROADMAP.md` | 16–20 week plan with acceptance gates |
| 11 | `RISK_REGISTER.md` | The three risks + automated mitigations |
| 12 | `RESEARCH_NOVELTY_V2.md` | Flagship + 3 supporting claims, with benchmarks |
| 13 | `WEEK_1_CHECKLIST.md` | Concrete Monday-Friday tasks for this week |

---

## How V2 coexists with V1

- **V1 code stays where it is.** V1 routes keep serving V1 pages during the entire V2 build.
- **V2 code goes into new modules under `backend/app/`:** `scene/`, `ingestion/`, `rendering/`, `interaction/`, plus `schema_v2.py`.
- **V2 routes mount under `/api/v2/*`** to prevent collision.
- **V2 schema coexists with V1 schema in Neo4j** via `Brand` node `schema_version` property. V1 brands stay V1. Newly onboarded brands are V2.
- **Migration tooling** (V1 brand → V2 decomposed asset graph) is a Phase-4 deliverable, not a blocker.

---

## The three risks and their automated mitigations

(See `RISK_REGISTER.md` for full detail.)

1. **Graph schema drift** → CI-enforced by `backend/scripts/validate_graph_schema.py`. Build fails if live Neo4j diverges from `GRAPH_SCHEMA_V2.md`.
2. **Per-part mesh regeneration UX** → Two-tier fallback: crop-and-realign first, whole-object-with-emphasis second. Decision point at week 7.
3. **FLUX + PuLID + dual ControlNet OOM on 12 GB** → `backend/scripts/vram_profile_v2.py` runs weekly and gates every refinement-stage PR. OOM = build fails.

---

## Flagship research claim

> **Brand consistency improves with use, without retraining, purely because user edits are expressed as graph state changes that modulate retrieval.**

Three supporting claims make this claim measurable and honest. See `RESEARCH_NOVELTY_V2.md`.
