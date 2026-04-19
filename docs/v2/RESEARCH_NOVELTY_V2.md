# RESEARCH_NOVELTY_V2

**Version:** 2.0.0  
**Target acceptance score:** ≥ 90/100 per the bar in `docs/RESEARCH_PROJECT_OVERVIEW.md §Hard Constraints`  
**Strategy:** One flagship claim. Three supporting claims that enable measurement of the flagship.

---

## Flagship claim

> **Brand consistency in generative outputs can be improved by representing user interactions as graph state changes that modulate retrieval, without any model fine-tuning.**

Precise version:

> *Given a fixed generation backbone and a fixed brand knowledge graph, a system that (a) decomposes brand assets into an inspectable sub-graph, (b) supports round-trip editing between 2D renders and 3D scenes, and (c) distils user edits into decay-weighted graph `PreferenceSignal` nodes that bias retrieval, achieves a statistically significant brand-consistency improvement of ≥ 10 % over the same backbone without signal-based retrieval bias, after 20 interactions per brand, with bootstrap 95 % CIs non-overlapping and Holm-corrected p < 0.01 across the three primary metrics.*

This is the only claim we pitch as the thesis headline. Everything else is structural support.

## Three supporting claims

Each is independently measurable and publishable as a contribution, but narratively serves to enable the flagship.

### Support claim 1 — Transparent decomposition enables user-inspectable brand knowledge
> A multi-step ingestion pipeline (VLM describe → grounded segment → delight → 3D mesh → validate) combined with a typed property-graph storage schema allows users to correctly predict the system's downstream behaviour on new briefs at a rate significantly above chance.

Measures: user-prediction accuracy test (human study), inter-rater agreement on predicted behaviours.

### Support claim 2 — Geometric 3D scene assembly yields measurable multi-view brand consistency
> Rendering N camera angles of a single 3D scene produces lower brand ΔE variance and lower identity-SSIM variance than generating N images from an equivalent 2D diffusion pipeline, at matched compute budget.

Measures: view-to-view brand ΔE variance, CLIP-I variance, SAM mask shape variance, at matched total FLOPs.

### Support claim 3 — Round-trip edit commutation
> An edit applied on the 2D canvas and an edit applied on the 3D canvas produce identical graph states when they encode the same semantic change. (Equivalent expressiveness between the two interaction surfaces.)

Measures: commutation test suite — 50 edits applied on both surfaces, graph state diff must be empty for the semantically-equivalent pairs.

## Why this passes the 90/100 bar

Against the 8 hard constraints in `RESEARCH_PROJECT_OVERVIEW.md`:

1. **Expected acceptance ≥ 90**: yes, claim is falsifiable with a concrete threshold (≥ 10 %) and pre-registered metrics.
2. **Method-level novelty, not architecture repackaging**: the novelty is *the mechanism by which user edits become retrieval-time biases without retraining*. This is a method, not a wiring diagram.
3. **No repurposed-combination claims**: the flagship is specifically about non-fine-tuning adaptation via graph state. Support claims frame necessary properties.
4. **Canonical benchmark**: `BrandInteractionBench` (defined in §4 below), public protocol committed to `experiments/v2/`.
5. **Preregistered hypotheses + powered study**: `experiments/v2/preregistration.md` fixed before data collection; power analysis in same file.
6. **Compute-parity baselines + full ablation matrix**: see §5.
7. **Reproducibility artifacts**: seed-locked, config-locked, commit-locked `experiments/v2/reproduce.sh`.
8. **Blinded human study + inter-rater reliability**: required for support claims 1 and 3 (§6).

## Positioning against prior work

| Prior work | What it does | Why we are different |
|---|---|---|
| RAG + diffusion (generic) | Retrieval-augmented prompts | Retrieval here is **graph-relational**, not similarity-only, and modulation happens at multiple pipeline stages, not just prompt concatenation |
| IP-Adapter / InstantID | Reference-image conditioning | We use these as one component. The novelty is the graph-traversed relational filtering that selects which reference is passed |
| LayerDiffuse | Native RGBA foreground diffusion | We supersede with 3D-first assembly; LayerDiffuse produces one flat RGBA, we produce a renderable 3D scene |
| IC-Light | Physically-grounded relighting | Replaced by real HDRI lighting in Blender (physically correct by construction) |
| DreamBooth / LoRA personalisation | Fine-tune on brand data | We explicitly **do not fine-tune**; adaptation is via graph state changes. This is the flagship's entire point |
| RLHF / preference optimisation for text | Learn preferences via reward models | Same aim, no reward model, no gradient updates; preferences are graph nodes with decay |
| GraphRAG (LLM literature) | Graph as context for text gen | Extended here to image-generation conditioning via multiple modalities (colour LAB, 3D mesh, PBR material, composition biases) |

## Benchmark — BrandInteractionBench

Public protocol, splits, scoring. Committed to `experiments/v2/BrandInteractionBench/`.

### Corpus
- 30 synthetic brands (generated + hand-curated to balance colour diversity, product types, aesthetic modes)
- 10 assets per brand (product, logo, character_ref, textures)
- 50 intent prompts per brand across deployment contexts

### Tracks

**Track T1 — Learning curve (flagship)**  
For each brand, run: first-gen on 50 prompts → seed 20 interactions from a fixed script → post-20 first-gen on held-out 50 prompts. Report brand score + ΔE + identity SSIM delta.

**Track T2 — View consistency (support 2)**  
For each scene (150 scenes total), render 3 camera angles. Compute brand ΔE variance across the 3 renders.

**Track T3 — Round-trip commutation (support 3)**  
50 edit pairs (2D version, 3D version). Apply each and compute graph-state diff.

**Track T4 — Decomposition transparency (support 1)**  
Human study: 20 annotators, 10 assets each. Given the decomposition graph view, predict "will system accept this new brief?" 100 held-out brief predictions per annotator.

### Metrics (pre-registered)

| Metric | Computation | Pre-registered threshold |
|---|---|---|
| Brand ΔE mean | CIEDE2000 between dominant render colours and brand palette | lower better; flagship Δ ≥ 10 % |
| Identity SSIM | SSIM on product crops vs. brand reference | higher better |
| View variance ΔE | std-dev of ΔE across camera angles of same scene | lower better; support 2 threshold ≤ 3.0 |
| Commutation rate | fraction of (2D,3D) edit pairs producing identical graph diffs | ≥ 95 % |
| Prediction accuracy (human) | % correct on held-out brief predictions | significantly above 50 % with kappa ≥ 0.4 |

### Statistical reporting
- Bootstrap 95 % CIs with 10 000 resamples
- Holm correction for multiple comparisons across the 3 flagship metrics
- Effect sizes: Cohen's d for paired metrics
- Inter-rater reliability: Fleiss' kappa for Track T4

## Ablation matrix

Ordered by centrality to flagship. Each row removes one component; all other components equal; same 30 brands, same 1500 prompts.

| Ablation | What's removed | What should drop |
|---|---|---|
| A0 — full system | — | baseline |
| A1 — no learning | `retrieval_bias.py` returns no-op | flagship Δ collapses to 0 |
| A2 — no 3D, 2D flat | Pipeline B Stage 4–5 replaced with single SDXL pass | Track T2 variance rises ≥ 3× |
| A3 — no decomposition | Assets stored as V1 blobs | Track T4 prediction accuracy ≈ chance |
| A4 — no round-trip | 2D edits processed as pixel inpaint | Track T3 commutation < 50 % |
| A5 — no preference decay | `weight(t) = weight_0` forever | Runaway bias visible on long-interaction test |
| A6 — no graph relational filter | Asset retrieval by vector sim only | Brand score drop, qualitative regressions |

## Human study protocol

### Track T4 (transparency)
- 20 annotators (5 marketing professionals, 5 designers, 10 general)
- Blind to system identity
- IRB-style consent + honorarium
- Web form with 100 held-out brief predictions per annotator
- Inter-rater agreement target: kappa ≥ 0.4
- Preregistered in `experiments/v2/preregistration.md`

### Track T5 (support qualitative quality, optional)
Side-by-side preference on 50 scenes: V2 vs each ablation. Binary choice + 5-point Likert for "brand fit". Reported but not flagship.

## Reproducibility package

`experiments/v2/reproduce.sh` takes a single argument (`--track T1|T2|T3|T4`) and:
1. Verifies exact git commit, model commit hashes, seed list
2. Spins up Neo4j from a frozen snapshot (`experiments/v2/neo4j_dump.cypher`)
3. Runs the track end-to-end
4. Generates the same plots + tables in the thesis

Outputs:
- `experiments/v2/results/<track>/metrics.json`
- `experiments/v2/results/<track>/plots.pdf`
- `experiments/v2/results/<track>/bootstrap_cis.csv`
- Checksum manifest verifying nothing drifted from the preregistered run

## Timeline for research artefacts

Mapped to `IMPLEMENTATION_ROADMAP.md`:
- Week 5: preregistration.md written and locked (before Pipeline B code has any benchmarks run)
- Weeks 11–12: A1, A2 ablation code ready
- Weeks 13–15: human study instruments built
- Weeks 16–17: Track T1 baseline + post-learning runs
- Week 18–19: all tracks executed; reproducibility script tested
- Week 20: paper-ready figures + tables finalised
