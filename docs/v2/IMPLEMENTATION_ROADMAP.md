# IMPLEMENTATION_ROADMAP

**Version:** 2.0.0  
**Duration:** 16–20 weeks  
**Ambition:** Full scope per PRD §4 with AC-1..AC-10 green.

Each phase has an **acceptance gate**. Phases are not "done" until the gate is green. Gates are scripted where possible.

---

## Phase 0 — Foundation (Week 1)

**Goal:** Everything needed to make the rest of the project possible.

| Task | Owner | Exit criteria |
|---|---|---|
| Lock `GRAPH_SCHEMA_V2.md` | Lead | Version 2.0.0 tagged, no open edits |
| Write `schema_v2.py` Pydantic models | Lead | Every node/relationship in schema has a model |
| Run `validate_graph_schema.py` against dev Neo4j | Lead | Exits 0 on fresh DB after migration |
| Install target model stack (FLUX-NF4, TRELLIS, SAM 2.1, Qwen2.5-VL, IntrinsicAnything, PuLID-FLUX) | Lead | Each loads + infers + unloads in isolation |
| Run `vram_profile_v2.py` per-model | Lead | Each model's peak VRAM recorded |
| Stand up SQLite-backed job queue | Lead | Submit → enqueue → worker picks up → complete |
| Wire `/api/v2` router prefix in main FastAPI | Lead | `GET /api/v2/health` returns 200 |
| V1 regression snapshot | Lead | V1 routes still pass existing tests |

**Gate:** `tests/phase0_gate.py` — schema validates, VRAM profile matches budget table, V1 routes green.

---

## Phase 1 — Asset ingestion pipeline (Weeks 2–4)

**Goal:** A user can upload a product image and reach approved-in-graph in ≤ 5 min via CLI and API. No UI beyond a minimal approval page.

| Task | Weeks |
|---|---|
| `ingestion/steps/describe.py` + locked prompt | 2 |
| `ingestion/steps/segment.py` (GroundingDINO + SAM 2.1) | 2 |
| `ingestion/steps/delight.py` (IntrinsicAnything) | 2 |
| `ingestion/steps/mesh.py` (TRELLIS) | 3 |
| `ingestion/steps/validate.py` (CLIP re-render) | 3 |
| `ingestion/orchestrator.py` with VRAM-aware sequencing | 3 |
| `POST /api/v2/assets/ingest` + SSE progress | 3 |
| Minimal approval page (R3F viewer + Approve/Reject/Regen-part) | 4 |
| Per-part regen Strategy A | 4 |
| 20-asset smoke test (5 products, 5 characters, 5 logos, 5 textures) | 4 |

**Gate:** AC-1 — any fresh product image reaches approved state in ≤ 5 min on 12 GB VRAM; `tests/ingestion/test_end_to_end.py` passes.

---

## Phase 2 — Scene assembly pipeline, backend only (Weeks 5–7)

**Goal:** Given a brand with approved assets, the system can produce a 3D scene and render 2 camera angles at previz quality (no neural refinement yet).

| Task | Weeks |
|---|---|
| `scene/assembler.py` with intent parsing + Cypher retrieval | 5 |
| Scene-graph JSON parser with Pydantic validation | 5 |
| `scene/blender_bridge.py` — subprocess lifecycle, pipe protocol | 5–6 |
| Blender render script: RGB + depth + normal + object-ID passes | 6 |
| Multi-camera caching (keep Blender alive between cameras) | 6 |
| `POST /api/v2/scenes` — submit intent, return scene_id | 7 |
| `GET /api/v2/scenes/:id/renders` | 7 |
| Stage 7 color grading (LAB gamut clip) | 7 |
| Stage 6 text compositing | 7 |

**Gate:** For a test brand with 3 approved assets, submitting "hero shot in park, golden hour" yields a Scene + 2 Renders (previz, not photoreal yet) in ≤ 90 s. View-to-view ΔE variance ≤ 3.0.

---

## Phase 3 — 3D canvas read + simple editing (Weeks 8–9)

**Goal:** Frontend R3F canvas that renders any Scene from graph, supports select/move/rotate/scale with gizmos, writes edits through Pipeline C.

| Task | Weeks |
|---|---|
| R3F scene loader from graph (Zustand store) | 8 |
| TransformControls gizmo integration | 8 |
| Click-to-select on 3D canvas | 8 |
| Edit dispatcher → `POST /api/v2/interactions` | 9 |
| Pipeline C `applier.py` for move/rotate/scale/delete actions | 9 |
| Camera preset UI | 9 |
| Live re-render on edit (Pipeline B stages 4–8 only, skip parse/retrieval) | 9 |

**Gate:** AC-3 — a user can drag an object on the 3D canvas and see a re-rendered result within 30 seconds.

---

## Phase 4 — Neural refinement pass (Weeks 10–11)

**Goal:** Upgrade renders from previz to photoreal. This is the VRAM-critical phase.

| Task | Weeks |
|---|---|
| Install FLUX.1-schnell NF4 + test generation | 10 |
| Integrate ControlNet Depth + Normal | 10 |
| Integrate PuLID-FLUX for character placements | 10 |
| Integrate IP-Adapter-Plus for product texture fidelity | 11 |
| `refinement.py` orchestration | 11 |
| VRAM profiling + optimisation (target ≤ 11 GB peak) | 11 |
| A/B comparison: previz vs refined on 10 test scenes | 11 |

**Gate:** AC-7 — peak VRAM ≤ 11.5 GB; AC-2 — view-to-view brand ΔE variance ≤ 3.0 on refined renders; refined render quality rated ≥ 4/5 by internal review on 8/10 scenes.

**Buffer:** 1 week built into Phase 4 for OOM debugging. This is the single highest-risk phase.

---

## Phase 5 — Asset editor full per-part approval UX (Weeks 12–13)

**Goal:** Replace the minimal approval page from Phase 1 with the full per-part editor from PRD §4.1.

| Task | Weeks |
|---|---|
| Per-part selection + highlight in R3F viewer | 12 |
| Mask boundary adjustment UI (server-side SAM roundtrip) | 12 |
| Material sliders (albedo, roughness, metallic) | 12 |
| Per-part regeneration with hint input | 13 |
| Strategy B fallback wiring (whole-object emphasis regen) | 13 |
| Side-by-side original-vs-decomposition view | 13 |

**Gate:** AC-4 proxy — on 20 test assets, 60 %+ of users complete approval without regenerating any part. Per-part regen works for cap/label/body on bottle test case.

---

## Phase 6 — 2D interactive canvas (Weeks 14–15)

**Goal:** Click, drag, right-click, circle-and-describe on rendered 2D images.

| Task | Weeks |
|---|---|
| Object-ID pass resolver endpoint `POST /api/v2/renders/:id/pick` | 14 |
| Frontend: hover + click on 2D canvas resolved to Placement | 14 |
| Drag on 2D canvas → graph update via Pipeline C | 14 |
| Right-click menu with context-aware actions | 14 |
| SAM 2.1 server-side masking endpoint | 15 |
| VLM command parser `command_parser.py` | 15 |
| NL edit end-to-end: circle + prompt → graph mutation | 15 |
| Text layer creation / edit / delete UI | 15 |

**Gate:** AC-4 — click-to-select ≥ 95 % correct on 50 test cases. AC-9 — NL edit ≥ 90 % correct on 50 seeded prompts.

---

## Phase 7 — Learning loop (Weeks 16–17)

**Goal:** Preference signals distilled from interactions actually modulate Pipeline B outputs, and a Learned Preferences panel surfaces them.

| Task | Weeks |
|---|---|
| `distiller.py` — pattern detection background job | 16 |
| PreferenceSignal decay + supersession logic | 16 |
| `retrieval_bias.py` — signal → conditioning adjustments | 16 |
| `GET /api/v2/brands/:id/preferences` | 17 |
| Learned Preferences panel UI | 17 |
| 20-interaction controlled study: first-gen vs post-20-edits-gen | 17 |

**Gate:** AC-5 — 20-edit learning curve shows ≥ 10 % brand-score improvement with non-overlapping bootstrap CIs.

---

## Phase 8 — Benchmarks, ablations, thesis-grade evaluation (Weeks 18–19)

**Goal:** All research novelty claims are measured, ablated, and documented.

| Task | Weeks |
|---|---|
| View-consistency benchmark (flagship claim support 2) | 18 |
| Learning-efficacy benchmark (flagship) | 18 |
| Round-trip commutation tests | 19 |
| Transparency human-eval protocol | 19 |
| Compute-parity baselines (V1 SDXL, BaselineB, BaselineC per earlier brief) | 19 |
| Ablation matrix (learning off, refinement off, 3D off → 2D only) | 19 |
| Statistical reporting (Holm correction, bootstrap CIs) | 19 |
| Reproducibility bundle (seeds, configs, commit hashes) | 19 |

**Gate:** All AC-1..AC-10 green. Benchmark numbers with CIs reported in `experiments/v2_benchmark_results.md`.

---

## Phase 9 — Stretch features (Week 20)

Ship only if Phase 8 passed its gate and there is real slack. Cut first if schedule slips.

- Terrain heightmap paint
- Polygon-detail slider (LOD-tier switch)
- Cross-camera brand consistency audit report
- Multi-brand scene composition preview

---

## Weekly rhythm

Every Friday:
1. Run the current phase's acceptance gate script
2. Run `validate_graph_schema.py` (always)
3. Run `vram_profile_v2.py` (from Phase 4 onward)
4. Update `progress.md` with gate status + next-week focus
5. If gate red: Monday starts with triage, not new work

## Slip-ahead policy

If a phase's gate is not green by end of its last week:
- **Phase 4 (neural refinement)**: top priority. Cut stretch (Phase 9) entirely if this slips.
- **Phase 7 (learning loop)**: if this slips, the flagship claim is at risk. Protect at all costs.
- **All others**: slip quietly; shorten Phase 9 window.

## Cross-phase dependencies

```
Phase 0 ──> Phase 1 ──> Phase 2 ──> Phase 3 ──> Phase 4
                                         │          │
                                         ▼          ▼
                                     Phase 5    Phase 6 ──> Phase 7 ──> Phase 8 ──> (Phase 9)
```

Phase 5 depends on Phase 3 (R3F canvas) not Phase 4.  
Phase 6 depends on Phase 4 (object-ID pass is produced during neural refinement setup).  
Phase 7 depends on Phase 6 (needs enough interaction volume to test distillation).

## Definition of done for V2 MVP

All of:
1. All AC-1..AC-10 green in CI
2. `RISK_REGISTER.md` items R-1, R-2, R-3 all have "automated mitigation in place and passing"
3. `RESEARCH_NOVELTY_V2.md` flagship claim has a reproducible benchmark script
4. `docs/v2/` is current with implementation
5. Demo walkthrough scripted and tested on 12 GB card
