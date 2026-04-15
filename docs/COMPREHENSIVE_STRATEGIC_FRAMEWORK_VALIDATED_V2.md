# Comprehensive Strategic Framework for Graph-Conditioned Diffusion Control (Validated v2)

Date: April 12, 2026  
Project: Brand-Aligned GraphRAG Visual Synthesis  
Scope: Faculty-defensible research plan plus implementation strategy for an 8-week capstone

## 1. Executive Summary

This framework defines a method-level research contribution that combines GraphRAG with diffusion-time control to improve brand-consistent image generation under practical hardware constraints.

The core claim is:

Graph-conditioned diffusion guidance can improve brand color fidelity, layout compliance, and identity consistency over prompt-only and retrieval-plus-prompt baselines without full model fine-tuning.

The practical recommendation is a staged strategy:
1. Primary path: Hybrid Graph-Adapter control (GraphConditioner + IP-Adapter or ControlNet + PaletteRegularizer).
2. Secondary path: Lightweight in-loop guidance term for selected timesteps only.
3. Stretch path: Post-denoise critic refinement for offline quality, not real-time generation.

This sequence maximizes measurable gains while reducing implementation risk on RTX 5070 Ti class hardware.

---

## 2. Final Novelty Claim and Defense

### Novelty Claim
The novelty is an architecture-level unification of structured graph retrieval and diffusion-time control where graph-derived constraints are translated into latent-space guidance signals during denoising, not only into the initial text prompt.

### Defense
Prior systems usually do one of the following:
- Prompt-only conditioning with no persistent constraint enforcement.
- Retrieval-plus-prompt grounding that improves semantic context but weakly controls spatial and identity binding.
- Domain-specific control methods that do not generalize to brand-level multi-constraint synthesis.

This framework targets the semantic-visual binding gap by maintaining graph-informed control signals across denoising timesteps, enabling better preservation of palette, composition, and identity relationships.

---

## 3. Critical Corrections to Apply Before Final Submission

The following corrections should be treated as mandatory quality fixes for research defensibility.

1. Statistical test alignment:
- For paired generation experiments, use Wilcoxon signed-rank, not Mann-Whitney U.
- Use Mann-Whitney U only for independent samples.

2. Color-loss placement:
- CIEDE2000 should be computed in Lab color space on decoded images or differentiable previews.
- Do not claim exact DeltaE directly on raw latent tensors without a defined decode or proxy pipeline.

3. Guidance equation clarity:
- Separate inference-time guidance from full training-time gradients.
- Explicitly state when using finite-difference or score-proxy approximations.

4. Source reliability balance:
- Ensure peer-reviewed sources dominate all key claims.
- Use blog or industry sources only for tooling and operational context, not core scientific claims.
 - Do not transfer reported percentage gains from unrelated methods into this project's expected outcomes.

5. License compliance precision:
- Verify license constraints for each dependency used in identity or adapter modules.
- Mark non-commercial dependencies as research-only if applicable.

---

## 4. Method Formulation (Corrected)

### 4.1 Controlled Denoising Objective
A practical inference-time formulation is:

$$
\hat{\epsilon}_t = \epsilon_\theta(x_t, c_t) + \alpha_t \cdot g_t
$$

Where:
- $x_t$: latent at timestep $t$
- $\epsilon_\theta$: model noise prediction conditioned on prompt and controls
- $g_t$: graph-derived guidance direction (exact gradient or proxy estimate)
- $\alpha_t$: timestep schedule controlling guidance strength

A useful schedule is:

$$
\alpha_t = \alpha_{\max} \cdot (1 - t/T)^\gamma
$$

Apply stronger control in later denoising stages for detail alignment and weaker control early for global composition stability.

### 4.2 Composite Brand Loss

$$
\mathcal{L}_{brand} = \lambda_{color}\mathcal{L}_{color} + \lambda_{layout}\mathcal{L}_{layout} + \lambda_{id}\mathcal{L}_{id} + \lambda_{text}\mathcal{L}_{text}
$$

Definitions:
- $\mathcal{L}_{color}$: DeltaE-based palette deviation in Lab space.
- $\mathcal{L}_{layout}$: mask overlap or cross-entropy against graph-derived spatial priors.
- $\mathcal{L}_{id}$: embedding-distance loss against identity references.
- $\mathcal{L}_{text}$: OCR confidence and contrast penalty for text regions.

### 4.3 Practical Guidance Computation
- Differentiable path: compute gradients for differentiable terms.
- Proxy path: finite differences on latent perturbations for non-differentiable constraints.
- Hybrid path: combine exact and proxy components with bounded norm clipping to avoid instability.

---

## 5. Ranked Method Options (Implementation Decision)

### Option 1: Hybrid Graph-Adapter Pipeline (Recommended)
- Components: GraphConditioner + ControlNet or region priors + IP-style adapters + palette regularization.
- Expected value: best quality-risk ratio and fast implementation.
- Estimated effort: 3 to 4 weeks for stable first version.
- Risk: adapter and checkpoint compatibility drift.

### Option 2: Selective In-Loop Guidance (Research Upgrade)
- Components: lightweight guidance term injected on selected timesteps.
- Expected value: stronger scientific contribution and fine control.
- Estimated effort: 4 to 6 weeks depending on sampler integration complexity.
- Risk: runtime and VRAM spikes if guidance is too frequent.

### Option 3: Post-Denoise Critic Refinement (Offline Quality Mode)
- Components: generate -> evaluate -> local correction loops.
- Expected value: improved subjective quality for difficult scenes.
- Estimated effort: 3 to 5 weeks.
- Risk: high latency, weaker suitability for interactive usage.

Recommendation:
- Use Option 1 as production baseline and thesis anchor.
- Add Option 2 as ablation or advanced branch.
- Keep Option 3 as optional offline mode.

---

## 6. ComfyUI Node Architecture (Execution-Oriented)

### Priority Nodes
1. GraphConditioner
- Inputs: brand_id, scene intent, product ids, optional character id.
- Outputs: conditioning packet (palette vector, region priors, identity references, weight map).

2. DynamicCFGScheduler
- Inputs: base CFG, timestep, constraint confidence.
- Outputs: cfg_t and alpha_t.

3. PaletteRegularizer
- Inputs: decoded preview or latent proxy, palette targets.
- Outputs: color penalty signal and logged DeltaE trajectory.

4. LayoutConstraintNode
- Inputs: region masks and relation priors.
- Outputs: layout score and correction proposal.

5. IdentityLockNode
- Inputs: reference embeddings and generated embeddings.
- Outputs: identity score and optional correction weight.

### Secondary Nodes
6. ConstraintViolationChecker
7. FeedbackWeightAdapter
8. MultiSeedEvaluator

### Runtime Strategy
- Keep adapter count minimal per run.
- Use selective node activation for ablations.
- Log per-step overhead by node for bottleneck analysis.
- Use sparse decode or proxy color checks instead of full decode every denoising step when VRAM is constrained.

---

## 7. Experimental Protocol (Corrected and Defensible)

### 7.1 Dataset and Prompt Design
- Brands: 8 to 12 across distinct visual archetypes.
- Prompts: 30 to 50 per brand spanning product focus, lifestyle, text overlay, and campaign styles.
- Seeds: 3 to 5 per prompt per method.

### 7.2 Methods to Compare
1. Prompt-only baseline
2. Retrieval-plus-prompt baseline
3. Adapter-only control baseline
4. Proposed graph-conditioned method

### 7.3 Core Metrics
- Color alignment: mean DeltaE and threshold pass rate.
- Layout compliance: IoU or mask-rule satisfaction.
- Identity consistency: embedding cosine similarity.
- Text quality: OCR confidence and contrast proxy.
- Human preference: pairwise ranking or Likert with blind setup.
- Runtime: latency, VRAM peak, throughput.

### 7.4 Statistical Plan
- Paired setting per brand-prompt-seed tuple.
- Primary test: Wilcoxon signed-rank for pairwise method comparison.
- Use Mann-Whitney U only for independent-sample analyses.
- Multi-method comparison: Friedman test, then post-hoc corrected pairwise analysis.
- Effect sizes: rank-biserial or Cliff-style equivalent for non-parametric tests.
- Multiple comparisons: Holm correction.
- Confidence intervals: bootstrap intervals for metric deltas.

### 7.5 Human Evaluation Protocol
- Blind side-by-side presentation.
- Randomized image order and method anonymization.
- Minimum 10 raters with calibration examples.
- Report inter-rater agreement and disagreement analysis.

---

## 8. Reproducibility Specification

### Per-Run Metadata (Mandatory)
- model_id, checkpoint hash, sampler, steps, cfg schedule
- seed, resolution, precision mode, adapter stack
- graph snapshot id or hash
- guidance weights and schedule parameters
- runtime telemetry (latency, VRAM peak)
- software versions and node commit hashes

### Folder Template
- experiments/01_baselines
- experiments/02_graph_guided
- experiments/03_ablations
- experiments/04_human_eval
- experiments/stats
- experiments/configs
- experiments/manifests

### Report Tables to Pre-Define
- Main metrics by method
- Ablation deltas by removed module
- Runtime profile by configuration
- Human preference summary

---

## 9. Risk Register (Practical)

1. VRAM overflow
- Trigger: peak memory approaches card limit.
- Mitigation: lower resolution, sequential offload, reduced adapter concurrency.
- Fallback: sparse decode schedule for color-loss evaluation and guidance update.

2. Guidance instability
- Trigger: artifacts rise as guidance increases.
- Mitigation: clip guidance norm, damp alpha schedule, reduce update frequency.

3. License conflict
- Trigger: incompatible dependency terms for intended use.
- Mitigation: maintain dependency license table and approved alternatives.
- Fallback: replace restricted identity tools with permissible alternatives when required.

4. Dataset rights uncertainty
- Trigger: unclear permission for logos or identity references.
- Mitigation: use licensed assets and written approvals only.

5. Timeline slippage
- Trigger: Node 1 to Node 3 not stable by end of Week 3.
- Mitigation: freeze advanced branch, complete baseline and one strong control module first.

---

## 10. Eight-Week Delivery Plan with Gates

Week 1:
- Freeze hypotheses, metrics, baselines, and compliance checklist.
- Stand up reproducible baseline ComfyUI workflow.

Week 2:
- Implement GraphConditioner and DynamicCFGScheduler.
- Add backend job tracking for controlled runs.

Week 3:
- Implement PaletteRegularizer and layout module.
- Run pilot on 2 brands and inspect failure modes.

Week 4:
- Implement IdentityLock and violation checker.
- Finalize metric pipeline and paired-run manifests.

Week 5:
- Full data generation for baselines and primary method.
- Begin ablations with disabled modules.

Week 6:
- Complete statistical analysis and human evaluation round.
- Build comparison dashboard for faculty demo.

Week 7:
- Consolidate report chapters and failure analysis.
- Prepare defense script and reproducibility package.

Week 8:
- Final polish, rerun critical experiments, freeze artifacts.

Go or No-Go gates:
- End Week 3: stable generation and valid metric logs.
- End Week 5: complete method comparison dataset.
- End Week 6: statistically analyzable evidence package.

---

## 11. Immediate Next 10 Actions

1. Convert this framework into a locked protocol document (versioned).
2. Create a source-validation sheet with confidence tiers.
3. Approve baseline definitions and metric formulas with supervisor.
4. Finalize dependency license matrix.
5. Implement GraphConditioner node scaffold.
6. Implement DynamicCFGScheduler node scaffold.
7. Implement PaletteRegularizer minimal working version.
8. Build run manifest generator for paired experiments.
9. Execute pilot run on 2 brands with 10 prompts each.
10. Produce first checkpoint report with failure analysis.

---

## 12. What to Request from the Deep Research Agent Next

Ask for a revision pass that explicitly addresses:
1. Paired-test correction and full statistics pipeline.
2. Peer-reviewed source strengthening for all major claims.
3. Verified license terms for each proposed dependency.
4. Clear mapping from equations to ComfyUI-operational approximations.
5. Numeric thresholds for acceptance criteria per metric.

This creates a direct bridge from research narrative to implementation-grade execution.