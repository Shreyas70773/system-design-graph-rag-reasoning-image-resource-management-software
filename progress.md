# Project Execution Progress

Date Started: 2026-04-12
Mode: Continuous implementation until closure

## Overall Goal
Finish all remaining research-upgrade and readiness tasks identified in the latest gap review.

## Work Queue
1. [x] Create and maintain this progress tracker
2. [x] Implement graph-conditioning runtime layer (GraphConditioner + DynamicCFGScheduler)
3. [x] Integrate graph-conditioning layer into controlled runner and Comfy workflow injection
4. [x] Replace metric placeholders with measured layout, identity, and text-legibility proxies
5. [x] Add/expand tests for new research services and metrics
6. [x] Run full validation (compile, tests, frontend build)
7. [x] Add VRAM profiling execution script and artifact output pipeline
8. [x] Add claim-ledger updater and evidence status utility
9. [x] Finalize license matrix decisions with enforceable policy checks
10. [x] Implement Comfy custom-node package scaffold for research modules
11. [x] Execute experiment artifact pack bootstrap (manifests, stats, human-eval folders)
12. [x] Final polish, unresolved TODO cleanup, and defense-ready freeze

## Activity Log
- 2026-04-12: Initialized progress tracking file and queued remaining blocks.
- 2026-04-12: Added graph conditioning services and dynamic CFG scheduling.
- 2026-04-12: Wired conditioning packet and CFG preview into experiment runner and Comfy workflow injection.
- 2026-04-12: Implemented proxy metric computation for layout, identity, and text legibility.
- 2026-04-12: Added unit tests for graph conditioning and metric proxy services.
- 2026-04-12: Added executable VRAM profiling script plus matrix template and generated dry-run artifacts.
- 2026-04-12: Added evidence sync utility and updated claim ledger based on current artifact readiness.
- 2026-04-12: Added license policy JSON, automated license compliance checker, and generated compliance report artifact.
- 2026-04-12: Added Comfy custom-node scaffold package with 8 planned research nodes and Comfy registration mappings.
- 2026-04-12: Bootstrapped experiments artifact structure with manifest/config templates and stats/human-eval logs.
- 2026-04-12: Implemented logo upload endpoint with local/R2 storage service and static uploads mount.
- 2026-04-12: Completed full compile/tests/build validation after all recent changes.
- 2026-04-12: B1 and B4 now auto-evaluate as closed via evidence sync script.
- 2026-04-12: B3 auto-evaluates as closed after claim-ledger normalization and hypothesis relabeling.
- 2026-04-12: Remaining open blocker is B2 (requires live VRAM profiling runs, not dry-run).
- 2026-04-12: Verified Neo4j runtime connection is currently unavailable in this environment, blocking live experiment execution for B2.
- 2026-04-12: Diagnosed Neo4j TLS routing failure, added +ssc trust fallback, and validated live Neo4j connection.
- 2026-04-12: Executed live (non-dry-run) VRAM profiling matrix with completed runs and zero OOM events.
- 2026-04-12: Re-synced evidence and claim ledger; B1-B4 all closed.

## Completion Status
- V1 project execution queue completed.
- Evidence blockers B1-B4 closed.
- Final validation sweep completed.

## V2 Kickoff (2026-04-17)

Full V2 redesign begun: 3D-first brand-aware scene authoring with graph-RAG learning loop. See `docs/v2/` for all specs.

### V2 foundational artefacts created (2026-04-17)
- Locked schema: `docs/v2/GRAPH_SCHEMA_V2.md` (v2.0.0) — 21 node types, 25 relationship types, 12 constraints, 4 indexes
- PRD with 10 acceptance criteria: `docs/v2/PRD.md`
- Architecture + 3 pipeline specs (A ingestion, B assembly, C interaction)
- Implementation roadmap (16–20 weeks, 10 phases), risk register, model stack, VRAM budget, API contract, research novelty, Week-1 checklist
- Pydantic models: `backend/app/schema_v2.py` — validated live against doc
- New modules: `backend/app/scene/`, `ingestion/`, `rendering/`, `interaction/`
- `backend/app/routers/v2_health.py` wired at `/api/v2/health`
- Job queue: `backend/app/jobs.py` (SQLite-backed)
- **Risk R-1 mitigation live:** `backend/scripts/validate_graph_schema.py` — exits 0 on current state
- **Risk R-3 scaffold live:** `backend/scripts/vram_profile_v2.py` — ready for Week 1 verify scripts
- Migration: `backend/migrations/v2/0001_initial_schema.cypher`
- Phase 0 gate: `tests/phase0_gate.py` — **PASSES** today

### Next: Week 1 (2026-04-20 → 2026-04-25)
See `docs/v2/WEEK_1_CHECKLIST.md`. Daily deliverables locked; Friday end-of-week gate = Phase 0 complete.

## V2 Blocker Snapshot
- R-1 (schema drift): **Mitigation live in CI.** `validate_graph_schema.py` runs green.
- R-2 (per-part mesh seams): Strategy A + fallback B scaffolded; decision point Week 7.
- R-3 (12 GB OOM): Profile script ready; verify scripts + budget gate active from Week 1.
