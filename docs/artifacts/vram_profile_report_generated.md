# Generated VRAM Profiling Report

Generated at: 2026-04-12T11:12:44Z
API URL: http://127.0.0.1:8000
Brand ID: a04480f7
Dry run: False

## Results

| run_id | method | status | peak_vram_gb | avg_vram_gb | latency_s | oom_event | run_api_id |
|---|---|---|---:|---:|---:|---|---|
| R01 | prompt_only | completed | 0.0 | 0.0 | 12.735 | False | run_250ecc76c92d |
| R02 | retrieval_prompt | completed | 0.0 | 0.0 | 11.3558 | False | run_2d3e3afea075 |
| R03 | adapter_only | completed | 0.0 | 0.0 | 12.6908 | False | run_37230a5a0072 |
| R04 | graph_guided | completed | 0.0 | 0.0 | 11.9219 | False | run_8d2c8656b43d |
| R05 | graph_guided | completed | 0.0 | 0.0 | 11.2165 | False | run_7699f831d3c3 |

## Notes

- This report is generated automatically from backend/scripts/run_vram_profile.py.
- If peak_vram_gb is empty, nvidia-smi was unavailable during capture.
- Replace dry_run with live execution before closing blocker B2.
