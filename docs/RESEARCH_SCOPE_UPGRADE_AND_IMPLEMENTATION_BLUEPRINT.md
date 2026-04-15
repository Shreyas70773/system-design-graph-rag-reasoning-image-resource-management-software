# Research Scope Upgrade and Implementation Blueprint

Date: April 12, 2026
Project: Brand-Aligned GraphRAG Content Generation System

## 1. Why This Upgrade Is Needed

The current project already demonstrates a strong engineering prototype:
- Brand scraping and brand graph creation
- GraphRAG-style context retrieval
- Prompt compilation and multi-provider generation
- Feedback collection and iterative generation loops

However, to become a high-impact final year research outcome, the project must move from application-level orchestration to method-level innovation.

### Current Limitation
Current generation mostly influences output by prompt engineering and routing decisions.

### Target Research Upgrade
Inject brand constraints directly into the diffusion denoising process using graph-conditioned guidance in ComfyUI.

This creates a true research contribution, not only a product integration.

---

## 2. Core Research Claim

Graph-conditioned, constraint-aware diffusion guidance improves brand consistency, layout compliance, and identity preservation compared to prompt-only and retrieval-plus-prompt baselines, while remaining practical on consumer RTX hardware.

---

## 3. Research Objectives

1. Design a graph-conditioned diffusion guidance mechanism for brand alignment.
2. Implement custom ComfyUI nodes that convert Brand DNA into denoising-time control signals.
3. Quantify improvements with objective metrics and statistical significance.
4. Build an explainable product demo that exposes graph influence, constraints, and feedback learning.

---

## 4. Research Questions and Hypotheses

### RQ1
Does diffusion-time graph guidance reduce brand color drift versus prompt-only generation?

Hypothesis H1:
Average color error to brand palette is significantly lower for graph-conditioned diffusion.

### RQ2
Does constraint-aware guidance improve structural compliance (layout, product placement, text region quality)?

Hypothesis H2:
Constraint satisfaction scores are significantly higher for graph-conditioned diffusion.

### RQ3
Does feedback-adaptive weighting improve output quality over repeated generations?

Hypothesis H3:
User acceptance and preference scores increase across feedback iterations.

---

## 5. Proposed Method (Math Layer Contribution)

### 5.1 Denoising Update with Graph Guidance
Use classifier-free guidance plus graph-conditioned correction:

eps_hat_t = eps_u + s_t * (eps_c - eps_u) + alpha_t * grad_term_t

Where:
- eps_u: unconditional prediction
- eps_c: text-conditional prediction
- s_t: timestep-dependent CFG scale
- grad_term_t: gradient-like correction from brand objective
- alpha_t: guidance weight schedule

### 5.2 Brand Objective

L_brand = w_color * L_color + w_layout * L_layout + w_identity * L_identity + w_text * L_text

- L_color: palette consistency loss (Lab space distance, DeltaE)
- L_layout: region and composition compliance loss
- L_identity: face or character consistency loss (embedding similarity)
- L_text: text area contrast and legibility quality proxy

### 5.3 Guidance Schedule

alpha_t = alpha_max * (1 - t/T)^gamma

Higher correction near later denoising stages to preserve global coherence while refining brand details.

---

## 6. System Upgrade Architecture

## 6.1 Existing System (Keep)
- FastAPI orchestration
- Neo4j brand graph
- Brand DNA retrieval
- Feedback endpoints
- Frontend workflow pages

## 6.2 New Research Layer (Add)
- ComfyUI as primary controlled generation engine
- Custom ComfyUI nodes for graph-conditioned diffusion control
- Experiment harness and metrics pipeline
- Research dashboard for comparisons and ablations

### 6.3 New Components
1. GraphConditioner Node
2. DynamicCFGScheduler Node
3. PaletteRegularizer Node
4. LayoutConstraint Node
5. IdentityLock Node
6. ConstraintViolationChecker Node
7. FeedbackWeightAdapter Node
8. MultiSeedEvaluator Node

---

## 7. Detailed Implementation Plan

## 7.1 Workstream A: ComfyUI Foundation

### Tasks
1. Install and benchmark ComfyUI pipeline on local RTX laptop.
2. Integrate base model stack:
   - SDXL base
   - Optional Flux path for comparison
   - LoRA support for brand adapters
3. Define reproducible inference settings:
   - fixed seeds
   - fixed step counts
   - fixed scheduler options

### Output
A stable, reproducible local generation environment for experiments.

---

## 7.2 Workstream B: Custom Node Development

### 1) GraphConditioner Node
Purpose:
Convert Brand DNA graph into structured conditioning vectors and masks.

Inputs:
- brand_id
- prompt text
- scene graph elements
- optional selected product and character

Outputs:
- graph_cond_vector
- element_masks
- constraint_weight_map

Implementation:
- Query Brand DNA via backend endpoint
- Encode color/style/constraint features into dense vectors
- Build mask priors for product/logo/text zones
- Emit per-sample conditioning packet consumed by downstream nodes

### 2) DynamicCFGScheduler Node
Purpose:
Apply adaptive CFG schedule across timesteps.

Inputs:
- base_cfg
- timestep t
- confidence from preferences and constraints

Output:
- cfg_t

Implementation:
- Define scheduler profile (linear, polynomial, exponential)
- Allow context-conditioned scaling (high-confidence preferences -> stronger guidance)

### 3) PaletteRegularizer Node
Purpose:
Reduce brand color drift during generation.

Inputs:
- latent or decoded preview
- target palette
- tolerance thresholds

Output:
- corrected latent update
- per-step color deviation logs

Implementation:
- Compute color histograms or Lab-based distance to palette
- Apply lightweight correction term to denoising update
- Log DeltaE trends over timesteps

### 4) LayoutConstraint Node
Purpose:
Enforce composition constraints from scene graph.

Inputs:
- scene element map
- composition template
- region importance scores

Output:
- spatial prior maps
- layout compliance score

Implementation:
- Use masks and region priors
- Penalize major violations of reserved regions

### 5) IdentityLock Node
Purpose:
Preserve character identity across generations.

Inputs:
- reference identity embedding
- generated face embedding

Output:
- identity consistency score
- optional correction guidance

Implementation:
- Use face embedding extractor
- Apply threshold gating and correction weighting

### 6) ConstraintViolationChecker Node
Purpose:
Check generated output against hard and soft constraints.

Outputs:
- pass or fail
- violation report
- auto-refine triggers

### 7) FeedbackWeightAdapter Node
Purpose:
Update guidance weights from user feedback patterns.

Implementation:
- Consume learned preference confidence
- Adjust w_color, w_layout, w_identity, w_text automatically

### 8) MultiSeedEvaluator Node
Purpose:
Generate N candidates and auto-select best by weighted score.

Output:
- best image
- candidate score table

---

## 7.3 Workstream C: Backend Integration

### New Backend Responsibilities
1. ComfyUI job submission and status tracking
2. Node parameterization from Brand DNA
3. Experiment run metadata storage
4. Metric aggregation API

### Recommended Backend Additions
- service: comfy_client
- service: experiment_runner
- service: metric_evaluator
- router: research endpoints

### Example API Endpoints
- POST /api/research/generate-controlled
- POST /api/research/run-ablation
- GET /api/research/metrics/{run_id}
- GET /api/research/compare/{experiment_id}

---

## 7.4 Workstream D: Data and Schema Upgrades

Extend graph model with research entities:
- ExperimentRun
- ModelConfig
- AblationConfig
- MetricSnapshot
- ConstraintViolation

Store:
- seed
- scheduler
- guidance weights
- runtime
- per-metric outputs

This enables reproducibility and thesis-grade evidence.

---

## 7.5 Workstream E: Frontend Product and Demo Upgrade

### New UI Features
1. Research Mode switch
2. Side-by-side comparison:
   - Baseline
   - Retrieval + prompt
   - Full graph-conditioned diffusion
3. Constraint diagnostics panel
4. Live metric readout
5. Feedback-to-weight update visualization

### Demo Storyline
1. Show brand graph context
2. Generate baseline and upgraded outputs with identical seed
3. Show quantitative metric differences
4. Apply user feedback and regenerate
5. Show measurable improvement and updated learned preferences

---

## 8. Experimental Design

## 8.1 Dataset and Prompt Set
- 8 to 12 brands
- 30 to 50 prompts per brand
- 3 to 5 seeds per prompt

## 8.2 Baselines
1. Prompt-only generation
2. Graph retrieval plus prompt injection
3. Proposed graph-conditioned diffusion method

## 8.3 Ablations
1. Without color regularizer
2. Without layout constraint
3. Without identity lock
4. Fixed CFG vs dynamic CFG
5. Static weights vs feedback-adaptive weights

## 8.4 Metrics
- Color alignment: DeltaE to brand palette
- Layout compliance: region overlap and rule satisfaction
- Identity consistency: embedding similarity
- Text legibility proxy: OCR confidence and contrast score
- User preference: pairwise ranking and acceptance rate
- Runtime metrics: latency and memory use

## 8.5 Statistics
- Paired significance testing (paired t-test or Wilcoxon)
- Effect size reporting
- Confidence intervals

---

## 9. Hardware and Feasibility Plan

Target hardware:
- RTX 5070 Ti
- Ultra 9 CPU
- 32 GB RAM

Practical strategy:
- Mixed precision inference
- Batch size 1 with multi-seed sequential evaluation
- 768 or 1024 resolutions depending on latency budget
- Keep training lightweight (LoRA only where necessary)

This is enough for strong prototype-level research if experiment design is disciplined.

---

## 10. Eight-Week Execution Timeline

Week 1:
- Finalize research protocol and metrics
- Set up ComfyUI reproducible baseline workflow

Week 2:
- Implement GraphConditioner and DynamicCFGScheduler
- Integrate backend job runner

Week 3:
- Implement PaletteRegularizer and LayoutConstraint
- Add first metric pipeline

Week 4:
- Implement IdentityLock and ViolationChecker
- Run pilot experiments on 2 brands

Week 5:
- Implement FeedbackWeightAdapter and MultiSeedEvaluator
- Run full dataset experiments

Week 6:
- Run full ablation study and statistics
- Build research dashboard views

Week 7:
- Final product polish and defense demo script
- Draft report results and discussion chapters

Week 8:
- Final thesis formatting, figures, and rehearsal
- Freeze reproducibility package

---

## 11. Deliverables for Faculty and Defense

1. Research report with full method, equations, experiments, and statistical analysis.
2. ComfyUI custom node package with documentation.
3. Reproducibility pack:
   - prompt sets
   - seeds
   - configs
   - result tables
4. Product demo with baseline vs upgraded system and feedback loop.
5. Technical appendix with implementation details and failure analysis.

---

## 12. Success Criteria (Outcome-Oriented)

Research success:
- Statistically significant improvements on key metrics
- Clear ablation evidence showing each module contribution

Engineering success:
- Stable generation pipeline and experiment logging
- End-to-end reproducibility for selected runs

Product success:
- Explainable demo showing measurable value of graph-conditioned diffusion
- Faculty can observe method advantage directly

---

## 13. Immediate Next Actions (First 7 Days)

1. Freeze exact hypotheses, metrics, and baseline definitions.
2. Stand up ComfyUI branch and run baseline benchmark script.
3. Implement GraphConditioner and DynamicCFGScheduler first.
4. Create experiment tracking schema and run logging templates.
5. Prepare first mini report with pilot comparisons on 2 brands.

---

## 14. Recommended Report Chapter Structure

1. Introduction and motivation
2. Related work and gap analysis
3. System architecture and Brand DNA graph
4. Proposed graph-conditioned diffusion method
5. Implementation details (ComfyUI nodes and backend integration)
6. Experimental setup and evaluation protocol
7. Results, ablations, and statistical analysis
8. Product demonstration and practical impact
9. Limitations and future work
10. Conclusion

---

This blueprint upgrades the project from feature-rich prototype to a method-driven, evidence-backed research project with a strong product demonstration.