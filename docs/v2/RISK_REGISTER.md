# RISK_REGISTER — V2

**Version:** 2.0.0  
**Purpose:** Each risk has (a) a detection mechanism, (b) a prevention mechanism, (c) a contingency plan, and (d) an owner. No risk is "monitored" — every risk is **actively enforced not to happen**.

---

## R-1 — Graph schema drift between docs, code, and live DB

**Impact if it happens:** Catastrophic. Every V1 issue the project already had, but 3× larger surface area. Code paths referencing stale property names. Broken queries at runtime. Re-work of weeks of output.

**Detection mechanism (automated):**
- `backend/scripts/validate_graph_schema.py`:
  - Parses `docs/v2/GRAPH_SCHEMA_V2.md` for node types, properties, relationships, constraints
  - Introspects `backend/app/schema_v2.py` Pydantic models
  - Connects to the Neo4j dev instance and queries the live schema
  - **Fails non-zero** on any of:
    - Doc declares a property that the Pydantic model doesn't have
    - Pydantic model has a property not in the doc
    - Live Neo4j has a label / property / constraint not in the doc
    - Live Neo4j is missing a required constraint from §3.1 of the doc
- Runs in pre-commit hook (fast path, skips live DB)
- Runs in CI on every PR against `main` (full path with DB)
- Runs every Friday as part of the weekly rhythm

**Prevention mechanism:**
- Pipeline-scoped Neo4j users (§4 of schema doc) — no pipeline can create a node it doesn't own
- Pydantic models are `extra="forbid"` so unknown fields fail parse
- Cypher queries use parameter-only style; no string interpolation of property names
- The schema doc has explicit "how to change" process (§6)

**Contingency if it happens anyway:**
1. Revert the offending PR
2. Re-run `validate_graph_schema.py` to confirm green
3. If multi-branch divergence: drop dev Neo4j, re-run migrations from `backend/migrations/v2/`

**Owner:** Lead engineer. Every PR author is co-owner of the check.

**Status:** **Mitigation in place from Day 1.** The validator is a Phase 0 deliverable.

---

## R-2 — Per-part mesh regeneration fails visually (UV seams)

**Impact if it happens:** The full-editor per-part approval UX (chosen in the ideation session) does not ship, which breaks US-A3/A4 and degrades the "transparent decomposition" research supporting claim.

**Detection mechanism (automated):**
- `tests/ingestion/test_per_part_regen.py` runs on every ingestion PR
- Seam check: compute CLIP similarity between the per-part regen output and the unchanged neighbouring parts' UV boundaries
- Fails if similarity < 0.85
- Sample of 3 bottles + 3 bags + 3 characters as golden set

**Prevention mechanism:**
- Strategy A implementation (crop-and-realign) includes a seam-blending step using Poisson blending on the UV map
- UV coordinates for `SemanticPart.uv_region` are padded by 5 % on each side during regen to hide seam artefacts
- Test gate prevents merging Strategy A changes that regress seam quality

**Contingency if it happens anyway:**
- Fall back automatically to Strategy B (whole-object regen with emphasis) — wired in from Phase 1
- Strategy B degrades UX slightly ("we're regenerating the whole object, highlighting the cap") but always produces clean meshes
- Failure mode is visible to user, not silent

**Decision point:** End of Week 7 (Phase 1 exit). If Strategy A is failing the seam test on > 30 % of golden set, default to Strategy B and document Strategy A as future work.

**Owner:** Lead engineer. Reviewed weekly from Week 5.

**Status:** **Both strategies scaffolded in Phase 1.** Fallback path exists before primary path is trusted.

---

## R-3 — FLUX + PuLID + dual ControlNet OOM on 12 GB VRAM

**Impact if it happens:** Neural refinement pass cannot run. System ships with previz-quality renders only. Flagship AC-2 (photoreal view consistency) fails.

**Detection mechanism (automated):**
- `backend/scripts/vram_profile_v2.py`:
  - Instruments every pipeline stage with `torch.cuda.max_memory_allocated()` and `torch.cuda.max_memory_reserved()`
  - Writes a report table after each stage
  - **Fails non-zero** if any stage's peak exceeds `VRAM_BUDGET_V2.md` declared limit by more than 5 %
- Runs in CI on every PR that touches `backend/app/scene/` or `backend/app/rendering/` or `backend/app/ingestion/steps/`
- Runs as a gated test on every Phase 4+ merge

**Prevention mechanism (multi-layer):**

Layer 1 — Budgeting discipline
- `VRAM_BUDGET_V2.md` declares peak for every stage before implementation starts
- Each model gets a single-model VRAM profile in Phase 0 before being added to a pipeline
- Concurrent model loading is **forbidden by invariant I-6** (one model per worker)

Layer 2 — Architecture choices
- FLUX.1-schnell NF4 (not dev, not BF16)
- PuLID-FLUX loaded as LoRA on top of FLUX, not as a separate full model
- ControlNets loaded via ControlNet Union (single model handling multiple control types)
- IP-Adapter-Plus as an adapter, not a parallel encoder

Layer 3 — Runtime mitigations
- Sequential CPU offload (`enable_sequential_cpu_offload()`) on refinement stage
- `torch.cuda.empty_cache()` between cameras within a scene
- Attention slicing enabled
- VAE tiling for output > 1024 px

Layer 4 — Subprocess isolation
- Blender render exits before FLUX loads (guaranteed by separate subprocesses)
- No shared CUDA context between workers

**Contingency if it happens anyway:**
1. Fall back to FLUX.1-schnell Q4_K_S GGUF (~6 GB) — lower quality ceiling but fits comfortably
2. If GGUF still fails: fall back to SDXL-Turbo with ControlNet Depth + IP-Adapter (no PuLID, no Normal) — this is the V1 refinement stack, known to work
3. If all above fail: ship previz quality with a "neural refinement coming" banner; rent A10G for benchmark runs only
4. Document the OOM reproduction case in `docs/v2/known_issues.md`

**Owner:** Lead engineer. Phase 4 is the high-risk window.

**Status:** **Four layers of mitigation staged into Phase 0 + Phase 4.** Single-model profile baseline established in Phase 0.

---

## R-4 — LLM (Groq) scene-graph parser produces invalid JSON or hallucinates asset_ids (added risk)

**Impact if it happens:** Pipeline B Stage 1 fails silently or succeeds with bogus content. Bad references propagate into rendered scenes.

**Detection mechanism:**
- Pydantic `SceneGraphSpec` validation is strict; parse failure = Stage 1 failure
- Post-validation verifier: every `asset_id` in scene-graph must exist and have `ingestion_status = approved` for the target brand; otherwise fall back to `asset_query` vector search
- Per-week sample of 10 parse outputs reviewed manually

**Prevention:**
- Few-shot prompt with 5 exemplars (good + 2 bad-with-correction)
- JSON schema provided to Groq via structured-output mode where available
- Retry-once pattern with stricter "your previous response failed because X" in the second attempt

**Contingency:** After 2 retries, return error to user with rephrase suggestion. Do not attempt generation from malformed intent.

**Owner:** Lead. Addressed in Phase 2 Week 5.

---

## R-5 — Preference signals cause runaway bias (added risk)

**Impact if it happens:** A handful of user edits overfit the brand's preference state, producing outputs the user doesn't actually want but can't explain. Undermines the flagship research claim.

**Detection:**
- `tests/interaction/test_bounds.py` synthesises 100 consistent edits; asserts bounded deltas
- `tests/interaction/test_decay.py` asserts half-life behaviour
- Monthly review of top-weight preference signals per brand in an ops dashboard (Phase 7 deliverable)

**Prevention:**
- Hard bounds coded in `retrieval_bias.py` (not configurable)
- Supersession logic ensures flip-flopped preferences cancel rather than amplify
- User can delete any preference via the Learned Preferences panel (US-L3)

**Contingency:** "Reset learned preferences" button per brand. Audit trail is preserved via `Interaction` nodes even if signals are deleted.

**Owner:** Lead. Addressed in Phase 7.

---

## Risk-register review cadence

- **Every Friday:** Lead runs all mitigation scripts, checks status column
- **End of each phase:** Re-read this file; update statuses; add any new risks discovered during the phase
- **Before each merge to main:** CI runs R-1, R-3 checks automatically
