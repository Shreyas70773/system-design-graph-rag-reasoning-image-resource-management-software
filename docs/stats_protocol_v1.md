# Statistical Protocol v1.0

Date: April 12, 2026
Project: Brand-Aligned GraphRAG Visual Synthesis
Status: Approved for Execution (Internal)

## 1. Purpose

Define a defensible statistical analysis plan for comparing generation methods under a paired experimental design.

## 2. Experimental Design

### 2.1 Experimental Unit
One paired comparison unit is:
- same brand
- same prompt
- same seed
- same base generation settings where applicable

Unit key format:
`brand_id|prompt_id|seed|resolution|sampler|steps`

### 2.2 Methods Compared
1. Prompt-only baseline
2. Retrieval-plus-prompt baseline
3. Adapter-only control baseline
4. Graph-conditioned method (primary)

### 2.3 Primary Outcomes
1. Color alignment (DeltaE summary and pass rate)
2. Layout compliance (IoU or rule score)
3. Identity consistency (embedding cosine)
4. Text quality (OCR confidence and contrast proxy)
5. Runtime (latency and peak VRAM)

## 3. Hypotheses Template

For each metric M and comparison A vs B:
- Null: median paired delta $M_A - M_B = 0$
- Alternative: median paired delta $M_A - M_B \neq 0$

Directional hypotheses may be declared per metric before analysis freeze.

## 4. Statistical Tests

### 4.1 Pairwise Paired Comparisons
Use Wilcoxon signed-rank test.

Do not use Mann-Whitney U for paired comparisons.

### 4.2 Multi-Method Paired Comparison
Use Friedman test across methods.

If Friedman is significant, run post-hoc pairwise Wilcoxon signed-rank tests with Holm correction.

## 5. Effect Sizes and Intervals

### 5.1 Effect Size Reporting
- Pairwise Wilcoxon: rank-biserial correlation.
- Friedman omnibus: Kendall's W.

### 5.2 Confidence Intervals
- 95% bootstrap confidence intervals for paired deltas.
- Report CI for key aggregate outcomes by method.

## 6. Multiple Comparisons Control

Use Holm correction for families of pairwise post-hoc tests.

Each figure/table must declare:
- family of tests
- correction method
- adjusted p-values

## 7. Sample Size and Power Guidance

Minimum planning target:
- >= 48 paired units per brand-method comparison for medium effect assumptions.

Recommended operational target:
- scale toward >= 120 paired units where feasible due to cross-brand variability.

Final sample counts must be reported by brand and method.

## 8. Data Quality and Exclusion Rules

Exclude units only if one of the following is true:
1. generation failed for any compared method
2. missing metric output due to runtime/tool failure
3. manifest mismatch violates paired parity

All exclusions must be logged with reason code and count.

## 9. Reproducibility Requirements

For each analysis run, store:
- manifest hash
- metric table hash
- script version or commit hash
- analysis timestamp

Artifacts:
- `experiments/stats/*.csv`
- `experiments/stats/*.json`
- `experiments/stats/analysis_log.md`

## 10. Report Output Schema

Each statistical result row must include:
1. metric_name
2. comparison
3. test_name
4. n_pairs
5. effect_size
6. ci_low
7. ci_high
8. p_raw
9. p_adjusted
10. decision

## 11. Governance

Owner: B1 Owner (Research Lead)
Reviewer: Supervisor/Faculty
Deadline: TBD
Gate: Approved for implementation and data collection; supervisor review still required before thesis freeze.
