# Research Project Overview (Friend Version)
## Brand-Aligned Content Generation Platform

Date: April 2026  
Audience: Semi-technical readers (no deep AI background required)

---

## TL;DR in 20 Seconds

This project is basically a smart marketing-content machine.

You give it a brand website and a prompt like "make me a summer promo image", and it:

1. Learns the brand style (logo, colors, products, tone)
2. Stores that in a graph database (Neo4j)
3. Generates images and text that match that brand
4. Learns from feedback over time
5. Lets you run research experiments to prove quality improvements

So it is not "just an image generator". It is a full system that combines web scraping, graph reasoning, generation, evaluation, and experiment tracking.

---

## Read This In Layers (So It Is Easy To Explain)

Use this exact structure when presenting to a professor, student, or panel.

### Layer 1 (30-second explanation)

"We built a brand-aware AI content engine. It learns a brand from its website, stores that brand memory in a graph, generates images and text that follow brand rules, and then proves quality with controlled experiments and statistics."

### Layer 2 (3-minute explanation)

"The system has four parts. First, onboarding: scrape website, extract logo and colors, store brand data. Second, generation: use brand context plus prompt to create content through basic, advanced GraphRAG, or Brand DNA pipelines. Third, feedback: save what users liked and disliked so future outputs improve. Fourth, research mode: run fair multi-seed experiments with manifest locks, metrics, ablations, and significance tests so results are defensible."

### Layer 3 (10-minute explanation)

"This is not only app engineering. It is also a research workflow. We run method comparisons under controlled settings, compute metrics like brand score and DeltaE, apply statistical testing, and export reproducible artifacts. So the same platform supports both production use and thesis-grade evaluation."

### What to avoid when explaining

- Do not start with model names or APIs.
- Do not start with architecture diagrams.
- Start with problem, then user flow, then evidence.
- Keep one sentence per stage before going deeper.

---

## What Problem Are We Solving?

Normal AI image tools are good at making cool images, but bad at staying consistent with a real brand.

Example pain:

- Wrong colors
- Random style
- Inconsistent product look
- Text placement that looks messy
- No memory of what the brand liked before

This project fixes that by adding structure and memory before generation.

---

## Big Idea (Simple)

Think of this system like a small creative team:

- Research intern: scrapes the website and collects brand facts
- Librarian: stores those facts in a graph database
- Strategist: reasons about layout/style constraints
- Designer: generates image and copy
- QA person: checks brand consistency score
- Analyst: runs experiments and statistics to compare methods

All of those are actual modules in the codebase.

---

## End-to-End User Flow

### Step 1: Onboarding a brand

User enters a website URL.

Backend does:

- Scrape company info
- Find logo
- Extract colors
- Save brand profile in Neo4j

Frontend shows onboarding graph and lets user edit:

- Colors
- Styles
- Products
- Characters
- Composition preferences

### Step 2: Generate content

User enters a prompt.

System can generate through different paths:

- Basic generation path
- Advanced GraphRAG path
- Brand DNA orchestration path

Each path tries to keep outputs aligned to brand rules.

### Step 3: Review and feedback

User sees image + text + brand score.

User can provide feedback, and system stores learning signals so later generations improve.

### Step 4: Research mode

User can run controlled experiments:

- prompt_only vs retrieval_prompt vs adapter_only vs graph_guided
- same seeds, same settings
- compare results with metrics and statistics

This is the "academic proof" layer.

---

## Main Architecture Pieces

## 1) Frontend (React)

What it does:

- Onboarding flow
- Dashboard
- Generation screens
- Results screens
- History
- LinkedIn studio
- Research lab console

Important behavior:

- Keeps an "active brand id" in local storage
- Brandless routes redirect to onboarding or active brand route

So the UI is not just a demo page; it is a multi-page app with stateful brand context.

## 2) Backend API (FastAPI)

What it does:

- Serves modular routes for brands/products/generation/research/feedback/etc.
- Handles app startup checks (Neo4j schema setup, health checks)
- Exposes uploads and health status

The backend is where most orchestration logic lives.

## 3) Data layer (Neo4j graph)

Instead of only tables, this project uses graph relationships.

Why this matters:

- Brand rules are relationship-heavy
- Easy to model "Brand uses Color" or "Brand sells Product"
- Good fit for context retrieval in generation

Also includes research entities:

- ExperimentManifest
- ExperimentRun
- ExperimentCandidate
- MetricSnapshot

So one graph stores both operational brand data and experiment metadata.

---

## Generation Paths (What They Mean)

## A) Basic generation

Simple API route that:

- Builds prompt from brand context
- Generates image
- Generates text
- Optionally overlays text on image
- Computes brand score
- Saves generation history

Good for straightforward usage.

## B) Advanced GraphRAG generation

Heavier pipeline with explicit stages:

- Scene decomposition
- Constraint gathering and conflict resolution
- Prompt compilation
- Optional character consistency
- Generation and post-processing
- Pipeline logging
- Evaluation endpoints

Good for explainability and fine control.

## C) Brand DNA orchestration

This is the "knowledge-graph-first" path:

- Retrieve full Brand DNA from graph
- Optional LLM reasoning/planning
- Apply learned preferences
- Generate with provider abstraction
- Add text/logo post-processing
- Write generation + learning signals back to graph

Good for long-term adaptive behavior.

---

## Image Provider Strategy

This project uses a local-first approach when possible.

Current policy highlights:

- ComfyUI local generation is strongly supported
- FLUX checkpoint preference in local path
- Hugging Face SDXL fallback in specific path if local fails
- Diffusion-first provider policy
- Optional gates for non-diffusion providers

There is also provider abstraction for:

- fal.ai
- replicate
- comfyui
- fallback orchestration

So the system is not tied to a single model vendor.

---

## Research Subsystem (Why This Is Capstone-Strong)

This is where your project becomes more than product engineering.

You can:

- Run controlled multi-seed experiments
- Lock experiment manifest parity (same settings across methods)
- Run ablations by disabling modules
- Store candidate/run metrics
- Run bootstrap confidence intervals
- Run sign-test fallback
- Use Wilcoxon/Friedman when scipy is available
- Apply Holm correction for multiple comparisons
- Export CSV/JSON for report tables

This directly supports defensible claims in a thesis or viva.

---

## Quality and Evaluation

Metrics include:

- Brand score
- Color alignment score
- Palette match rate
- DeltaE proxy
- DeltaE CIEDE2000 mean/median/pass rate
- Layout compliance proxy
- Identity consistency proxy
- Text legibility proxy
- Latency

This is important because you are not saying "looks better" only by opinion. You have measurable outputs.

---

## What Is Already Implemented (Reality Check)

Yes, a lot is already built:

- Full frontend app with multiple feature pages
- FastAPI backend with modular routers
- Neo4j graph client + schemas
- Brand onboarding + scraping + quality checks
- Multiple generation pipelines
- Feedback and learning layers
- Research execution and stats analyzer
- Comfy custom node scaffold
- Governance scripts (license compliance, VRAM profiling, evidence sync)

So this is not a toy prototype anymore.

---

## Current Gaps / Messy Areas (Honest Section)

These are the key integration issues still visible:

1. Async/sync mismatch in some advanced modules  
Some advanced code awaits DB calls that are currently sync.

2. Frontend/backend contract drift on some advanced endpoints  
A few payload shapes do not perfectly match route models.

3. Streaming format mismatch in Brand DNA stream  
Backend emits NDJSON lines; frontend parser expects a different framing style.

4. Graph schema naming drift across old vs new paths  
Legacy labels/relationships and newer Brand DNA labels are mixed.

5. Search router exists but is not mounted in main app  
Implemented route, not wired into app include_router list.

6. Config portability risk  
There is a hardcoded env-file path in config that can break on other machines.

These are fixable engineering seams, not fundamental project failures.

---

## Simple Example Walkthrough

User says: "Create a launch banner for our fitness app"

System does:

1. Fetch brand context from Neo4j  
"Brand colors are blue/white, style is clean/minimal, product is mobile app"

2. Build generation plan  
"Main subject centered, CTA area at bottom, avoid clutter"

3. Generate image and text  
Uses provider path and prompt compiler

4. Post-process  
Overlay headline/body/logo if requested

5. Score output  
Compute brand consistency and color metrics

6. Save everything  
Generation node + metadata + feedback hooks

7. If in research mode  
Log run/candidates/metrics for comparisons later

---

## Why This Is a Strong Final-Year Project (But Not Yet a Strong Research Claim)

It combines:

- Full-stack engineering
- AI generation
- Graph data modeling
- Evaluation science
- Experiment reproducibility
- Cost-aware infrastructure design

And it solves a practical problem that companies actually care about: brand consistency at scale.

Important distinction:

- As a capstone engineering system: strong.
- As a novel research contribution: not strong enough yet.

---

## Brutal Researcher Verdict (Current State)

If a strict researcher reviews this today, they may reject the novelty claim for these reasons:

1. Most value is integration strength, not new method.
2. "Graph + reasoning + generation" can look like stacking known tools.
3. Metrics are useful but partly proxy-based, so novelty evidence is not yet airtight.
4. Multiple pipelines make the story broad, but not centered on one falsifiable research question.
5. Some integration seams make claims look less controlled than required for top review standards.

This does not mean the project is bad. It means novelty is currently under-specified.

---

## What Would Actually Convince a Skeptical Researcher

A skeptical reviewer usually wants one clear answer to one clear question:

"What new method did you invent that older methods cannot do under fair, reproducible tests?"

Minimum bar to convince them:

1. One flagship method claim, not five broad claims.
2. One canonical benchmark dedicated to that claim.
3. Compute-parity baselines and full ablations.
4. Statistical power and correction done correctly.
5. Public reproducibility pack.
6. Blinded human validation that agrees with quantitative results.

---

## Novelty Rescue Strategy (Single-Thesis Mode)

Use this rule: keep the platform as infrastructure, but claim novelty from only one method.

Recommended flagship thesis:

- Method: Causal Intervention-Aligned Diffusion
- Claim: controlled edits change only target brand factors and minimize off-target drift.
- Why this is a strong thesis: clear causal hypothesis, measurable failure mode, publishable benchmark structure.

How to present it:

1. System platform is supporting infrastructure.
2. Only one method is claimed as novel.
3. All experiments are designed around testing that one claim.

---

## Hard Constraints For Research Credibility (Non-Negotiable)

These are the strict constraints your upgrade ideas must satisfy:

1. Expected acceptance score must be above 90 out of 100.
2. Novelty must be method-level, not architecture repackaging.
3. No repurposed-combination novelty claims.
4. Must include a canonical benchmark with public protocol.
5. Must include preregistered hypotheses and powered study design.
6. Must include compute-parity baselines and full ablation matrix.
7. Must include reproducibility artifacts (code, configs, seeds, splits, eval scripts).
8. Must include human evaluation quality checks (blinding and inter-rater reliability).

---

## Research Upgrade Ideas (Simple Language, Strictly Above 90)

These ideas are written in plain language but remain genuinely research-grade.

### 1) Causal Intervention-Aligned Diffusion

- Acceptance estimate: 94 out of 100
- One-line idea: when you change one brand variable, only that visual factor should change, nothing unrelated.
- Why this is truly novel: introduces a causal intervention objective for image generation, not a system wiring change.
- Canonical benchmark: BrandCausalBench with intervention pairs and held-out brands.
- Must-report metrics: intervention effect error, off-target drift, human faithfulness, quality retention.

Why this should be the default pick:

- Cleanest route to a publishable story from your current codebase.
- Strongest link between method novelty and measurable outcome.
- Easiest to defend under "not repurposed architecture" criticism.

### 2) Proof-Carrying Generative Compliance

- Acceptance estimate: 93 out of 100
- One-line idea: every generated output must include a machine-checkable proof that brand rules were satisfied.
- Why this is truly novel: adds formal proof obligations to generation outputs, beyond score-based checking.
- Canonical benchmark: GenProofBench with formal constraints and adversarial contradiction sets.
- Must-report metrics: proof soundness, proof completeness, verifier robustness, human trust calibration.

### 3) Identifiable Brand Factor Subspaces

- Acceptance estimate: 92 out of 100
- One-line idea: learn separate latent controls for color, composition, and identity so edits are precise and predictable.
- Why this is truly novel: focuses on identifiability guarantees for controllable generation factors.
- Canonical benchmark: BrandFactorBench with compositional out-of-distribution splits.
- Must-report metrics: identifiability score, compositional generalization, edit faithfulness, leakage between factors.

### 4) Conformal Brand-Risk Controlled Generation

- Acceptance estimate: 92 out of 100
- One-line idea: generation should come with statistical risk guarantees, and abstain when risk is too high.
- Why this is truly novel: applies conformal risk control for guaranteed violation bounds in generation tasks.
- Canonical benchmark: BrandRiskBench with temporal and domain-shift tracks.
- Must-report metrics: risk-coverage curves, guaranteed violation rate at fixed coverage, calibration error, abstain utility.

### 5) Adversarial Brand-Collision Robustness Training

- Acceptance estimate: 91 out of 100
- One-line idea: train against hard near-neighbor brand attacks so outputs do not drift into lookalike brands.
- Why this is truly novel: minimax robustness objective on brand identity collision space.
- Canonical benchmark: BrandCollisionBench with confusable brand clusters.
- Must-report metrics: robust confusion rate, worst-case brand retention, clean-robust tradeoff, expert discrimination.

---

## Minimum Evidence Pack For Any "Novel" Claim

Before claiming novelty, every selected idea should ship with this checklist:

1. Preregistered hypotheses document.
2. Public benchmark card (splits, labels, leakage policy).
3. Baseline suite with compute parity.
4. Full ablation table.
5. Confidence intervals plus multiple-comparison correction.
6. Blinded human study with inter-rater agreement.
7. Reproducibility package: seeds, configs, scripts, exact commit IDs.
8. Negative results section (what failed and why).

---

## 12-Week Research Upgrade Plan (So Novelty Is Defensible)

### Phase 1 (Weeks 1-3): Define and lock the method

1. Write formal method definition and hypotheses.
2. Define intervention operators and off-target drift metric mathematically.
3. Freeze baseline matrix and compute budget parity.

Acceptance gate:

- Method spec is precise enough that another lab could reimplement it.

### Phase 2 (Weeks 4-8): Build canonical benchmark and run experiments

1. Build BrandCausalBench with train/val/test and hidden test server split.
2. Run controlled experiments with preregistered protocol.
3. Execute full ablations and sensitivity checks.

Acceptance gate:

- Primary hypothesis passes with confidence intervals and corrected significance.

### Phase 3 (Weeks 9-12): Reproducibility and human validation

1. Run blinded human study with inter-rater agreement reporting.
2. Release reproducibility bundle (code, seeds, configs, scripts, commit hashes).
3. Write limitation section with explicit failure cases.

Acceptance gate:

- Independent reader can reproduce headline results end-to-end.

---

## Professor-Friendly Closing Script

"Today, this is a strong engineering platform but not yet a decisive novelty claim. We solve that by switching to single-thesis mode: one new method, one canonical benchmark, one fair baseline matrix, one reproducibility package. Complexity stays high in implementation, but explanation stays simple: problem, method, evidence."

---

## Glossary (No-Nonsense)

- GraphRAG: Retrieval-augmented generation using graph relationships as context
- Neo4j: Graph database where data is stored as nodes + edges
- Constraint: Rule the generation should follow
- Ablation: Turning one module off to see how much it mattered
- Bootstrap CI: Re-sampling method to estimate confidence intervals
- Wilcoxon/Friedman: Non-parametric statistical tests
- DeltaE: Numeric color distance metric
- ComfyUI: Local node-based diffusion workflow engine

---

## If You Read Only One Paragraph

Right now, this project is a strong research platform, not yet a fully convincing novel method. To convince serious researchers, the project should present one flagship method claim (not broad integration claims), validate it on a canonical benchmark with strict baselines and statistics, and ship a complete reproducibility bundle. The engineering complexity can stay high, but the research story must become narrow, testable, and falsifiable.
