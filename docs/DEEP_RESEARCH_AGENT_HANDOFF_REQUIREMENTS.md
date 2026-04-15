# Deep Research Agent Handoff Requirements

Date: April 12, 2026
Project: Brand-Aligned GraphRAG Content Generation with Diffusion-Level Control
Owner: Capstone Team
Purpose: Collect high-confidence external evidence and implementation guidance required for a method-level research contribution.

## 1. Mission and Expected Outcome

You are tasked with gathering external evidence, implementation references, and validation frameworks to support a thesis-level claim:

Graph-conditioned diffusion guidance improves brand consistency, layout compliance, and identity preservation compared to prompt-only and retrieval-plus-prompt baselines on consumer GPU hardware.

Your output will be used to finalize:
- Research method and equations
- ComfyUI node design and implementation plan
- Experimental protocol and statistics plan
- Literature-backed novelty claim
- Faculty-ready report chapters

---

## 2. Non-Negotiable Questions to Answer

### 2.1 Novelty and Positioning
1. What is the strongest defensible novelty statement relative to 2023-2026 work in:
   - GraphRAG for generation
   - Controlled diffusion
   - Compositional generation
   - Brand/style consistency
2. Which exact gap is still unsolved by current methods that our approach addresses?
3. What nearest competing methods should we compare against to avoid weak novelty claims?

### 2.2 Diffusion-Level Method Design
1. What are the best-practice ways to inject external constraints into diffusion denoising?
2. Which approach is most feasible in ComfyUI with practical implementation effort:
   - guidance term in denoising update
   - conditioning through adapters
   - latent correction loop
   - post-denoise correction with refine passes
3. Which losses are realistic and meaningful for this project:
   - color alignment
   - layout compliance
   - identity consistency
   - text legibility

### 2.3 ComfyUI Technical Implementation
1. Which ComfyUI extension patterns are stable for custom node development?
2. Which existing open-source nodes or repos are closest to our needs (with licenses)?
3. What integration path is most stable for:
   - ControlNet and region priors
   - IP-Adapter or equivalent product conditioning
   - InstantID or PuLID identity consistency
4. What are common failure modes and mitigations when building custom control nodes?

### 2.4 Evaluation and Statistics
1. What objective metrics are accepted by current literature for each target dimension?
2. What are the best statistical tests for repeated, paired image-generation experiments?
3. What sample size guidance is realistic to obtain publishable-level confidence for a capstone?
4. What human evaluation protocol minimizes bias while remaining feasible?

### 2.5 Feasibility on Consumer Hardware
1. What model and resolution settings are realistic for RTX 5070 Ti class hardware?
2. What runtime optimization techniques provide the best speed/quality balance?
3. Which experiments should be prioritized if compute/time is constrained?

### 2.6 Compliance and Risk
1. Which model licenses, dataset usage rules, and third-party terms must be respected?
2. What privacy/ethics requirements apply to face identity references?
3. What claims should we avoid to prevent overstatement risk?

---

## 3. Required Deliverables from the Research Agent

Provide all items below.

### Deliverable A: Literature Evidence Pack
- Minimum 35 sources total.
- Minimum 15 peer-reviewed papers (journal/conference/workshop).
- Maximum 10 sources from blogs or non-academic pages.
- Include publication year, venue, core method, reported metrics, weaknesses, relevance score.
- Include a one-line "why it matters to us" for each source.

Required format:
- Table: Source, Year, Venue, Area, Method, Strength, Weakness, Relevance, Citation link.

### Deliverable B: SOTA Comparison Matrix
For each baseline family, summarize method details and expected behavior in our task.

Baseline families:
1. Prompt-only diffusion
2. Retrieval-plus-prompt approaches
3. Adapter-based conditioning
4. Constraint-guided or controllable diffusion
5. Identity-preserving generation pipelines

Required format:
- Matrix with columns: Method, Control granularity, Compute cost, Implementation complexity, Expected gains, Risks.

### Deliverable C: Recommended Method Stack (Ranked)
- Rank top 3 candidate implementation strategies for our project.
- For each strategy provide:
  - Why it is suitable
  - Expected measurable gain
  - Estimated effort in weeks
  - Dependency risk

Required format:
- Strategy card for each option plus a final recommendation.

### Deliverable D: Equation and Method Validation Note
- Validate or improve our candidate denoising equation with references.
- Define each loss term rigorously.
- Specify practical approximations for implementation in ComfyUI.
- Explain where gradients are exact vs proxy-based.

Required format:
- Math note with symbols table and assumptions.

### Deliverable E: ComfyUI Implementation Map
- Map each planned node to implementation references and alternatives.
- Include file structure recommendation for custom nodes.
- Include integration points with backend orchestration.

Required format:
- Node-by-node table:
  Node name, input schema, output schema, algorithm, dependencies, reference repos, license, expected runtime overhead.

### Deliverable F: Evaluation Protocol Pack
- Final metric definitions and formulas.
- Exact experiment design and randomization policy.
- Statistical testing pipeline.
- Human study protocol and rubric.

Required format:
- Experiment protocol v1.0 ready to execute.

### Deliverable G: Reproducibility and Reporting Standards
- Required metadata to log per run.
- Recommended folder structure for experiments.
- Result table templates for report chapters.

Required format:
- Reproducibility checklist + templates.

### Deliverable H: Risk Register and Mitigation Plan
- Top technical, legal, and timeline risks.
- Severity and probability score.
- Clear mitigation and fallback for each risk.

Required format:
- Risk table with owner and trigger conditions.

---

## 4. Source Quality and Validation Rules

The research agent must follow these rules:

1. Prefer primary sources over summaries.
2. Do not rely on a single source for major decisions.
3. For each key claim, provide at least 2 independent references.
4. Mark source confidence as High, Medium, or Low.
5. Separate proven findings from speculative recommendations.
6. Flag if evidence is outdated for 2026 context.
7. Include direct URLs for all references.

---

## 5. Hard Constraints for Recommendations

All recommendations must satisfy:

1. Implementable by capstone team within 8 weeks.
2. Compatible with local RTX 5070 Ti workflow.
3. Compatible with ComfyUI custom-node ecosystem.
4. Defensible with quantitative evaluation and ablations.
5. Legally usable under model and code licenses.

If a recommendation violates any constraint, mark it as Not Feasible.

---

## 6. Data and Evaluation Requirements to Prepare

The research agent should also return requirements for:

1. Brand dataset specification
   - number of brands
   - required fields
   - asset quality thresholds
2. Prompt benchmark specification
   - distribution across campaign types
   - complexity bins
3. Human evaluation setup
   - rater count
   - blind comparison protocol
   - scoring rubric
4. Runtime benchmark setup
   - warm start and cold start metrics
   - memory profile and throughput metrics

---

## 7. Mandatory Output Template

Return output in this exact structure:

1. Executive summary (1 page)
2. Final novelty claim and defense paragraph
3. Literature matrix
4. SOTA comparison matrix
5. Ranked method options with recommendation
6. Equation validation note
7. ComfyUI node implementation map
8. Experimental protocol and statistics plan
9. Reproducibility package specification
10. Risk register with mitigations
11. Immediate next 10 implementation actions
12. Full references with links

---

## 8. Query Bank (Use These Search Directions)

The research agent should query across these themes:

1. controllable diffusion guidance constraints denoising objective
2. graph-conditioned image generation retrieval conditioned diffusion
3. compositional diffusion layout control region constraints
4. color consistency metrics DeltaE brand alignment image generation
5. identity consistency in diffusion InstantID PuLID evaluation
6. ComfyUI custom node development best practices
7. adapter-based conditioning IP-Adapter ControlNet comparison
8. statistics for paired image generation evaluation human preference tests
9. reproducibility standards in generative image research
10. legal licensing for open image models and extensions

---

## 9. Acceptance Criteria for Research Agent Output

The handoff is accepted only if all criteria below are met:

1. At least 35 sources with clear confidence tagging.
2. Clear final recommendation among at least 3 method options.
3. Equation-level guidance tied to implementation reality.
4. Complete metric and statistics protocol, not just suggestions.
5. Explicit license and compliance notes for major dependencies.
6. Risk table with concrete fallbacks.
7. Actionable next steps that can be started immediately.

Mandatory rejection triggers:
1. Uses statistical tests that do not match the design (for paired experiments, Mann-Whitney U alone is not acceptable).
2. Uses unsupported numeric claims without direct citations.
3. Uses mostly blogs or non-peer-reviewed sources for core method claims.
4. Omits license constraints for identity, adapter, or model dependencies.
5. Provides equations without implementation notes explaining differentiable vs proxy terms.
6. Reuses percentage gains from unrelated methods without direct method match and citation.

---

## 10. Immediate Internal Team Usage Plan

After receiving research output, our team will do:

1. Freeze method stack and baseline list.
2. Freeze experiment protocol and metrics.
3. Start ComfyUI node implementation in priority order:
   - GraphConditioner
   - DynamicCFGScheduler
   - PaletteRegularizer
4. Start pilot experiment on 2 brands.
5. Generate first evidence table and faculty checkpoint summary.

---

## 11. Priority Ordering for Implementation

If evidence or time is limited, prioritize in this order:

1. Color and layout control with measurable metrics
2. Identity consistency module
3. Feedback-adaptive weights
4. Multi-seed candidate optimization

This order maximizes early measurable results and thesis strength.

---

## 12. Final Note

This handoff is designed to convert broad ambition into evidence-backed implementation decisions. The deep research agent should optimize for:
- high-confidence sources
- implementability
- measurable outcomes
- faculty defensibility

If tradeoffs are required, prioritize scientific defensibility over feature breadth.

---

## 13. Source Reliability Gate (Required Scoring)

The research agent must label each source with one reliability tier and confidence score.

Tier rules:
1. Tier A: Peer-reviewed publication or official model paper/spec.
2. Tier B: Official documentation from model/framework maintainers.
3. Tier C: Reputable engineering blogs or technical writeups.
4. Tier D: Community posts, forums, unsupervised repositories.

Usage rules:
1. Core novelty, method, and metric claims must be primarily Tier A and Tier B.
2. Tier C can support implementation pragmatics and hardware notes.
3. Tier D cannot be used alone for key scientific claims.

Scoring:
1. Confidence score from 0.0 to 1.0 for each source.
2. Mark any claim below 0.7 confidence as provisional.

---

## 14. Statistics Correctness Gate (Required)

The research agent must explicitly validate statistical-test selection.

Minimum requirements:
1. Identify if samples are paired or independent.
2. For paired non-parametric comparisons, use Wilcoxon signed-rank.
3. For 3 or more paired methods, use Friedman test and corrected post-hoc tests.
4. Report effect sizes and confidence intervals.
5. Apply multiple-comparison correction when relevant.

---

## 15. Copy-Paste Prompt for Your Deep Research Agent

Use the prompt below directly:

You are a research specialist supporting a capstone project on graph-conditioned diffusion control for brand-aligned content generation. Your task is to produce a high-confidence research and implementation package that enables an 8-week build and evaluation cycle on consumer RTX hardware.

Project claim to validate:
Graph-conditioned diffusion guidance improves brand consistency, layout compliance, and identity preservation compared to prompt-only and retrieval-plus-prompt baselines.

Scope and output rules:
1. Read and follow all requirements in this file exactly.
2. Provide all mandatory deliverables A-H.
3. Use at least 35 sources with confidence labels.
4. For key claims, provide at least 2 independent references.
5. Mark recommendations that are not feasible in 8 weeks as Not Feasible.
6. Include implementation-ready guidance, not only theory.
7. Include legal and license notes for major dependencies.

Output format must follow Section 7 exactly:
1. Executive summary (1 page)
2. Final novelty claim and defense paragraph
3. Literature matrix
4. SOTA comparison matrix
5. Ranked method options with recommendation
6. Equation validation note
7. ComfyUI node implementation map
8. Experimental protocol and statistics plan
9. Reproducibility package specification
10. Risk register with mitigations
11. Immediate next 10 implementation actions
12. Full references with links

Quality bar:
- Prioritize peer-reviewed and primary sources.
- Distinguish proven findings from speculative ideas.
- Optimize for faculty-defensible evidence and immediate engineering execution.

---

## 16. Red-Team Closure Protocol (Mandatory Before Implementation)

If a red-team report returns Conditional Pass or Fail, implementation cannot proceed until this closure protocol is completed.

### 16.1 Blocker Closure Matrix
For each blocker, provide:
1. blocker_id
2. severity
3. finding summary
4. corrective action
5. objective evidence artifact
6. owner
7. due date
8. closure status

### 16.2 Mandatory Closures for This Project
1. B1 Statistics mismatch:
   - paired design must use Wilcoxon signed-rank for pairwise comparisons.
   - 3 or more paired methods must use Friedman plus corrected post-hoc tests.
   - include effect sizes and confidence intervals.
2. B2 VRAM budget collision:
   - run memory profiling on target workflow and record peak VRAM.
   - replace per-step full decode color loss with sparse decode or proxy strategy if needed.
3. B3 Unverified gains:
   - remove borrowed percentage improvements unless directly supported by method-matched evidence.
   - mark expected gains as hypotheses until measured in project experiments.
4. B4 License conflict:
   - provide dependency license matrix with allowed usage scope.
   - mark non-commercial tools as research-only or replace with permissible alternatives.

### 16.3 Required Evidence Artifacts
1. Statistics protocol note with test-selection rationale.
2. VRAM profiling report with reproducible settings.
3. Claim ledger mapping every numeric claim to a citation.
4. License matrix for all model, adapter, and identity components.

### 16.4 Go or No-Go Rule
Go status is granted only when all Critical and High blockers are marked Closed with evidence links.
