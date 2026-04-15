# Research Table Schemas

These CSV templates align with thesis/report tables for Phase 2 exports and analysis.

## Files

1. `experiment_main_metrics_template.csv`
- One row per method run in an experiment.
- Used for primary result table.

2. `ablation_contribution_template.csv`
- One row per ablation comparison against base method.
- Used for module contribution analysis.

3. `runtime_profile_template.csv`
- One row per run configuration in profiling matrix.
- Used for feasibility and hardware discussion.

4. `human_eval_template.csv`
- One row per rater pairwise comparison.
- Used for human preference and reliability analysis.

## Notes

- Keep `experiment_id` and `run_id` consistent with API exports.
- Use adjusted p-values for inferential statistics columns.
- Keep metric definitions synchronized with `docs/stats_protocol_v1.md`.
