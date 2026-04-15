# Experiment Artifact Pack

This folder stores reproducible research artifacts for paired method comparisons.

## Folder Layout

1. experiments/01_baselines
2. experiments/02_graph_guided
3. experiments/03_ablations
4. experiments/04_human_eval
5. experiments/stats
6. experiments/configs
7. experiments/manifests

## Minimum Artifact Rule

Every experiment batch should include:
- a manifest JSON in experiments/manifests
- generated outputs grouped by method folder
- statistical tables in experiments/stats
- human-evaluation sheets in experiments/04_human_eval when applicable

## Naming Convention

Use this prefix format:
- EXP_<date>_<brand>_<batch>

Example:
- EXP_2026-04-12_brand_001_batch_a
