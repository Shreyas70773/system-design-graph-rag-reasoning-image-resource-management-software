# Research API Quickstart

Date: April 12, 2026
Status: Active

This quickstart covers the newly added research execution endpoints.

## 1. Endpoints

Base path: `/api/research`

1. `POST /generate-controlled`
2. `POST /run-ablation`
3. `GET /metrics/{run_id}`
4. `GET /manifest/{experiment_id}`
5. `POST /manifest/validate`
6. `GET /compare/{experiment_id}`
7. `GET /stats/{experiment_id}`
8. `POST /jobs/deltae/{run_id}`
9. `GET /export/run/{run_id}`
10. `GET /export/experiment/{experiment_id}`
11. `GET /runs/{brand_id}`

## 2. Controlled Run Example

Request:

```json
{
  "brand_id": "your_brand_id",
  "prompt": "Product hero shot for summer launch with clean layout",
  "method_name": "graph_guided",
  "seeds": [11, 22, 33],
  "num_inference_steps": 30,
  "guidance_scale": 7.5,
  "use_comfyui": false,
  "use_proxy_color": true,
  "module_toggles": {
    "color_regularizer": true,
    "layout_constraint": true,
    "identity_lock": true,
    "dynamic_cfg": true
  }
}
```

Response includes:
- `run_id`
- `experiment_id`
- run-level summary
- candidate-level outputs

## 3. Ablation Run Example

Request:

```json
{
  "brand_id": "your_brand_id",
  "prompt": "Launch campaign with premium lifestyle context",
  "base_method": "graph_guided",
  "seeds": [11, 22, 33],
  "ablations": [
    "without_color_regularizer",
    "without_layout_constraint",
    "without_identity_lock",
    "fixed_cfg"
  ]
}
```

This creates a base run plus one run per ablation under a shared `experiment_id`.

## 4. Comparison and Metrics

1. Compare all runs in an experiment:
- `GET /api/research/compare/{experiment_id}`

2. Fetch metric snapshots for one run:
- `GET /api/research/metrics/{run_id}`

3. List recent runs for one brand:
- `GET /api/research/runs/{brand_id}?limit=20`

4. Compute paired statistics for one metric:
- `GET /api/research/stats/{experiment_id}?metric=brand_score&baseline_method=prompt_only`
- Optional controls:
  - `bootstrap_resamples` (default 2000, min 100)
  - `ci_alpha` (default 0.05)
  - `random_seed` (default 42)
- Response includes per-method pairwise outputs with:
  - `delta_mean_ci` (bootstrap confidence interval)
  - `effect_size.cohen_dz`
  - `p_value_adjusted_holm`

5. Trigger Lab-space DeltaE refinement for a run:
- `POST /api/research/jobs/deltae/{run_id}`

6. Export one run (JSON or CSV):
- `GET /api/research/export/run/{run_id}?format=json`
- `GET /api/research/export/run/{run_id}?format=csv`

7. Export experiment summary table (JSON or CSV):
- `GET /api/research/export/experiment/{experiment_id}?format=json`
- `GET /api/research/export/experiment/{experiment_id}?format=csv`

8. Fetch locked experiment manifest:
- `GET /api/research/manifest/{experiment_id}`

9. Validate a requested manifest against lock:
- `POST /api/research/manifest/validate`

## 5. UI Entry Point

Frontend route added:
- `/research`

The page supports:
- controlled run execution
- ablation execution
- experiment comparison
- manifest retrieval
- DeltaE job trigger
- JSON and CSV export
- listing recent runs

## 6. Storage Model

Research entities are persisted in Neo4j:
- `ExperimentManifest`
- `ExperimentRun`
- `ExperimentCandidate`
- `MetricSnapshot`

Each run stores seeds, config, status, result summary, and per-candidate metrics.
Each experiment manifest stores locked prompt/seed/config parity for reproducible comparisons.

When an existing lock is violated, `POST /generate-controlled` returns HTTP 409 with:
- `error: manifest_conflict`
- requested and stored parity hashes
- field-level differences

## 7. Important Notes

1. ComfyUI path is optional. If `use_comfyui=true`, provide a workflow payload.
2. Color metrics now include both proxy and Lab-space CIEDE2000 outputs.
3. Use manifest locking for strict paired parity across baseline and ablation runs.
4. Ensure `openai` dependency is present for full app imports.
5. For report tables, prefer Holm-adjusted p-values and include effect sizes and CI bounds.

## 8. Report Table Templates

CSV templates for thesis/report tables are available in `docs/templates`:
1. `experiment_main_metrics_template.csv`
2. `ablation_contribution_template.csv`
3. `runtime_profile_template.csv`
4. `human_eval_template.csv`

## 9. Operational Scripts

1. VRAM profiling pipeline:
- `backend/scripts/run_vram_profile.py`

2. Evidence and claim sync:
- `backend/scripts/sync_evidence_status.py --write`

3. License policy enforcement:
- `backend/scripts/check_license_compliance.py --scope research`
- `backend/scripts/check_license_compliance.py --scope deployment`
