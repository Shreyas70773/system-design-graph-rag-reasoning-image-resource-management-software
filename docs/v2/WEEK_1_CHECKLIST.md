# WEEK 1 CHECKLIST — Foundation

**Start date:** 2026-04-20 (Monday)  
**Goal:** Everything the rest of the project needs in order to start.

Phase 0 acceptance gate: end of Friday. Gate script: `tests/phase0_gate.py`.

---

## Monday — Schema + Pydantic

- [ ] Read and confirm `docs/v2/GRAPH_SCHEMA_V2.md` is locked (version 2.0.0)
- [ ] Finalise `backend/app/schema_v2.py` — every node + relationship has a Pydantic model
- [ ] Write `backend/migrations/v2/0001_initial_schema.cypher` — constraints + indexes from schema §3
- [ ] Run the migration against a fresh local Neo4j instance
- [ ] Write `backend/scripts/validate_graph_schema.py` skeleton (detailed below)
- [ ] Verify validator exits 0 on the fresh migrated DB

**End-of-day check:**
```powershell
python backend/scripts/validate_graph_schema.py --neo4j-uri $env:NEO4J_URI
# Expected: "OK: schema matches GRAPH_SCHEMA_V2.md 2.0.0"
```

## Tuesday — Model download + disk verification

- [ ] Write `backend/scripts/download_models.py` per `MODEL_STACK_V2.md §5`
- [ ] Execute download with `HF_HUB_CACHE` pointed at a drive with ≥ 120 GB free
- [ ] Verify all 11 models downloaded (checksum via HF hub metadata)
- [ ] Record free VRAM at idle: `nvidia-smi` → `free_vram_idle.txt`
- [ ] Confirm Blender 4.2+ installed and `blender --version` returns cleanly

**End-of-day check:** downloads complete, disk usage logged.

## Wednesday — Per-model verification

- [ ] Implement `backend/scripts/verify/verify_qwen_vl.py`
- [ ] Implement `backend/scripts/verify/verify_grounding_sam.py`
- [ ] Implement `backend/scripts/verify/verify_intrinsic.py`
- [ ] Implement `backend/scripts/verify/verify_trellis.py`

**End-of-day check:**
```powershell
python backend/scripts/verify/verify_trellis.py
# Expected: PEAK_VRAM ~9800 MiB, STATUS OK
```

## Thursday — More verifications + VRAM profile driver

- [ ] Implement `backend/scripts/verify/verify_sam3d_body.py`
- [ ] Implement `backend/scripts/verify/verify_flux_schnell.py`
- [ ] Implement `backend/scripts/verify/verify_pulid_flux.py`
- [ ] Implement `backend/scripts/verify/verify_controlnet_union.py`
- [ ] Implement `backend/scripts/verify/verify_ipadapter_flux.py`
- [ ] Write `backend/scripts/vram_profile_v2.py` — runs all verify scripts sequentially, aggregates into JSON + Markdown

**End-of-day check:**
```powershell
python backend/scripts/vram_profile_v2.py --report-dir docs/artifacts/vram_profile_v2/2026-04-23
# Expected: all 9 models STATUS OK, report committed to docs/artifacts/
```

## Friday — Infrastructure + Phase 0 gate

- [ ] Create new backend modules: `scene/`, `ingestion/`, `rendering/`, `interaction/` with `__init__.py` + minimal placeholder `models.py`
- [ ] Mount `v2` router prefix in `backend/app/main.py` with a `GET /api/v2/health` endpoint
- [ ] Write SQLite-backed job queue: `backend/app/jobs.py` with submit/poll/stream primitives
- [ ] Write `tests/phase0_gate.py` — calls `validate_graph_schema.py`, `vram_profile_v2.py`, and V1 regression tests
- [ ] Run full gate and confirm green
- [ ] Update `progress.md` with Phase 0 complete + Phase 1 kickoff plan
- [ ] Commit and tag: `v2-phase0-complete`

**End-of-day check:**
```powershell
python tests/phase0_gate.py
# Expected: "Phase 0 gate: PASS"
```

---

## validate_graph_schema.py — Monday scope in detail

Must implement:

1. **Parser** for `GRAPH_SCHEMA_V2.md`:
   - Find all `#### ` headings under `## 1. Node types` → node labels
   - Parse the adjacent markdown tables for property name, type, required flag
   - Find all tables under `## 2. Relationship types` → relationship triples `(from, type, to)`
   - Find all `CREATE CONSTRAINT` statements under `## 3. Constraints`

2. **Pydantic reflection**:
   - Import `backend.app.schema_v2`
   - For every Pydantic model class, compare against the corresponding doc declaration
   - Fail with precise diff on any mismatch

3. **Live DB introspection** (if `--neo4j-uri` provided):
   - `CALL db.schema.nodeTypeProperties()` → compare against doc
   - `CALL db.schema.relTypeProperties()` → compare
   - `SHOW CONSTRAINTS` → assert every doc-declared constraint is live

4. **Exit codes**:
   - 0 — all good
   - 1 — doc/code mismatch
   - 2 — doc/db mismatch
   - 3 — doc parse failure

5. **Output format**:
   ```
   OK: schema matches GRAPH_SCHEMA_V2.md 2.0.0
     - 18 node types verified
     - 27 relationship types verified
     - 11 constraints verified
     - 4 indexes verified
   ```

   Or:
   ```
   FAIL: schema drift detected
     DRIFT [pydantic]: Asset.confidence (in doc) missing from schema_v2.py
     DRIFT [db]: constraint asset_id missing on live DB
   ```

---

## Deliverables by end of Friday

Files that must exist and be green:

```
docs/v2/
  ├── README.md                          ✓ (created)
  ├── PRD.md                             ✓
  ├── GRAPH_SCHEMA_V2.md                 ✓
  ├── ARCHITECTURE_V2.md                 ✓
  ├── PIPELINE_A_ASSET_INGESTION.md      ✓
  ├── PIPELINE_B_SCENE_ASSEMBLY.md       ✓
  ├── PIPELINE_C_INTERACTION_LEARNING.md ✓
  ├── MODEL_STACK_V2.md                  ✓
  ├── VRAM_BUDGET_V2.md                  ✓
  ├── API_CONTRACT_V2.md                 ✓
  ├── IMPLEMENTATION_ROADMAP.md          ✓
  ├── RISK_REGISTER.md                   ✓
  ├── RESEARCH_NOVELTY_V2.md             ✓
  └── WEEK_1_CHECKLIST.md                ✓ (this)

backend/app/
  ├── schema_v2.py                       ← Monday
  ├── jobs.py                            ← Friday
  ├── scene/__init__.py                  ← Friday
  ├── ingestion/__init__.py              ← Friday
  ├── rendering/__init__.py              ← Friday
  ├── interaction/__init__.py            ← Friday
  └── routers/v2_health.py               ← Friday

backend/migrations/v2/
  └── 0001_initial_schema.cypher         ← Monday

backend/scripts/
  ├── validate_graph_schema.py           ← Monday
  ├── download_models.py                 ← Tuesday
  ├── vram_profile_v2.py                 ← Thursday
  └── verify/
      ├── verify_qwen_vl.py              ← Wednesday
      ├── verify_grounding_sam.py        ← Wednesday
      ├── verify_intrinsic.py            ← Wednesday
      ├── verify_trellis.py              ← Wednesday
      ├── verify_sam3d_body.py           ← Thursday
      ├── verify_flux_schnell.py         ← Thursday
      ├── verify_pulid_flux.py           ← Thursday
      ├── verify_controlnet_union.py     ← Thursday
      └── verify_ipadapter_flux.py       ← Thursday

tests/
  └── phase0_gate.py                     ← Friday

docs/artifacts/vram_profile_v2/
  └── 2026-04-23/report.md               ← Thursday

progress.md                              ← Friday update
```

---

## Risks this week

| Risk | Mitigation |
|---|---|
| Model download fails / corrupt | Use `huggingface-cli download` with verification flags; retry on failure |
| TRELLIS install issues on Windows | Have WSL2 fallback plan; if Windows fails, run TRELLIS in WSL as subprocess |
| FLUX NF4 doesn't fit with PuLID | Identified as R-3; fallback ladder defined in `RISK_REGISTER.md` |
| `validate_graph_schema.py` too brittle on doc changes | Use a permissive parser; fail-closed but emit readable diffs |

---

## If anything slips past Friday

Phase 1 is blocked. Do not begin Phase 1 work. Triage Monday morning. This is the only time the schedule is not negotiable — every other phase can absorb slack, Phase 0 cannot.
