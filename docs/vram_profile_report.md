# VRAM Profile Report Template

Date: April 12, 2026
Project: Brand-Aligned GraphRAG Visual Synthesis
Status: Draft Template

## 0. Automated Profiler Script

Use:
- `backend/scripts/run_vram_profile.py`
- `backend/scripts/vram_profile_matrix.sample.json`

Example command:

`cd backend && python scripts/run_vram_profile.py --brand-id <brand_id> --api-url http://localhost:8000 --matrix-file scripts/vram_profile_matrix.sample.json`

Generated artifacts:
- `docs/artifacts/vram_profile_runs.csv`
- `docs/artifacts/vram_profile_summary.json`
- `docs/artifacts/vram_profile_report_generated.md`

Note:
- Use `--dry-run` to validate pipeline wiring before live API execution.

## 1. Purpose

Quantify memory and runtime feasibility of the generation stack on target hardware and define safe fallback configurations.

## 2. Hardware and Software Environment

| Field | Value |
|---|---|
| GPU | RTX 5070 Ti (12 GB) |
| Driver Version | TBD |
| CUDA Version | TBD |
| PyTorch Version | TBD |
| ComfyUI Commit | TBD |
| Model Checkpoint | TBD |

## 3. Profiling Protocol

1. Warm-up runs: 3
2. Measured runs per config: 5
3. Resolution tiers: 768 and 1024
4. Precision modes: fp16/bf16 (as available)
5. Workloads must use fixed seed lists for comparability.

## 4. Configuration Matrix

| run_id | method | resolution | steps | sampler | precision | adapters | guidance_mode | decode_mode | batch_size | status |
|---|---|---:|---:|---|---|---|---|---|---:|---|
| R01 | prompt_only | 768 | 30 | TBD | fp16 | none | none | none | 1 | pending |
| R02 | retrieval_prompt | 768 | 30 | TBD | fp16 | none | none | none | 1 | pending |
| R03 | adapter_control | 768 | 30 | TBD | fp16 | control_stack_v1 | none | sparse | 1 | pending |
| R04 | graph_guided | 768 | 30 | TBD | fp16 | control_stack_v1 | proxy | sparse | 1 | pending |
| R05 | graph_guided | 1024 | 30 | TBD | fp16 | control_stack_v1 | proxy | sparse | 1 | pending |

## 5. Metrics to Capture

For every run:
1. peak_vram_gb
2. avg_vram_gb
3. avg_step_ms
4. total_latency_s
5. oom_event (yes or no)
6. quality_proxy_score (optional)

## 6. Result Table

| run_id | peak_vram_gb | avg_vram_gb | total_latency_s | oom_event | notes |
|---|---:|---:|---:|---|---|
| R01 | TBD | TBD | TBD | no | |
| R02 | TBD | TBD | TBD | no | |
| R03 | TBD | TBD | TBD | no | |
| R04 | TBD | TBD | TBD | no | |
| R05 | TBD | TBD | TBD | TBD | |

## 7. Acceptance Criteria

1. No OOM for primary production configuration.
2. Peak VRAM <= 11.5 GB for stable operation.
3. Runtime variation across repeated runs remains bounded.

## 8. Fallback Policy

If VRAM exceeds threshold:
1. reduce resolution
2. reduce concurrent adapters
3. switch from dense decode to sparse decode color checks
4. reduce guidance update frequency

## 9. Evidence Artifacts

Required attachments:
1. profiler logs
2. environment export
3. run manifests
4. screenshot or tabular summary from monitoring tools

## 10. Governance

Owner: B2 Owner (Engineering Lead)
Reviewer: Research Lead
Deadline: TBD
Gate: Must be closed before full-scale experiments.
