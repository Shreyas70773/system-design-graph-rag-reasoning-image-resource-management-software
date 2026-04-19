# MODEL_STACK_V2

**Version:** 2.0.0  
**Target GPU:** RTX 5070 Ti Ultra, 12 GB VRAM  
**Target host:** 32 GB RAM, Ultra 9 CPU, Windows 11

Every model's exact identifier, loader, quantisation, and purpose is locked here. Changes require bumping this file's version + a PR.

---

## 1. Summary table

| Role | Model | Source | Quantisation | Peak VRAM | Loaded in |
|---|---|---|---|---|---|
| Intent LLM | Llama 3.3 70B | Groq API | — | 0 (remote) | Pipeline B |
| Vision-language (ingestion + NL edits) | Qwen2.5-VL-7B-Instruct | HF `Qwen/Qwen2.5-VL-7B-Instruct-AWQ` | AWQ | ~6.2 GB | Pipeline A, Pipeline C |
| Grounded detection | GroundingDINO Tiny | HF `IDEA-Research/grounding-dino-tiny` | fp16 | ~1.5 GB | Pipeline A |
| Segmentation | SAM 2.1 Hiera-Large | HF `facebook/sam2.1-hiera-large` | fp16 | ~3.8 GB | Pipeline A, Pipeline C |
| Delighting | IntrinsicAnything | HF `zxhezexin/IntrinsicAnything` | fp16 | ~6.0 GB | Pipeline A |
| Image → 3D | TRELLIS | HF `microsoft/TRELLIS-image-large` | fp16 | ~9.8 GB | Pipeline A |
| 3D body mesh (humans) | SAM 3D Body | HF `facebook/sam3d-body` | fp16 | ~6.0 GB | Pipeline A (character only) |
| Refinement (primary) | FLUX.1-schnell | HF `black-forest-labs/FLUX.1-schnell` | NF4 via `bnb` | ~10.0 GB | Pipeline B |
| Face identity | PuLID-FLUX | HF `guozinan/PuLID` | LoRA on FLUX | +1.2 GB | Pipeline B (character only) |
| Structure control | FLUX ControlNet Union | HF `Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro` | fp16 | +1.8 GB | Pipeline B |
| Image prompt | IP-Adapter-Plus for FLUX | HF `InstantX/FLUX.1-dev-IP-Adapter` | fp16 | +0.8 GB | Pipeline B |
| CLIP (retrieval + validation) | `openai/clip-vit-large-patch14` | HF | fp16 | ~1.8 GB | Pipeline A, Pipeline B |
| **Refinement fallback 1** | FLUX.1-schnell | HF, GGUF Q4_K_S | GGUF | ~6.5 GB | Pipeline B (fallback) |
| **Refinement fallback 2** | SDXL-Turbo | HF `stabilityai/sdxl-turbo` | fp16 | ~7.5 GB | Pipeline B (fallback) |
| **Refinement fallback 2 adapter** | ControlNet Depth (SDXL) | HF `diffusers/controlnet-depth-sdxl-1.0` | fp16 | +2.5 GB | Pipeline B (fallback) |

Peak VRAM in any single pipeline stage is governed by §4 — no stage loads more than ~11.0 GB.

## 2. Model choice justifications

### Qwen2.5-VL-7B-Instruct AWQ
Chosen over Llava, InternVL, GPT-4V:
- Runs locally → critical for Pipeline C latency and privacy
- AWQ quant fits in 6 GB
- Structured-output compliance is strong when given Pydantic-style schemas in the prompt
- Alternative considered and rejected: Llava-Next-7B (weaker at structured outputs on benchmark)

### GroundingDINO + SAM 2.1
Chosen over direct SAM 2.1 prompt-free segmentation:
- GroundingDINO gives us text-conditioned proposals (we pass the VLM's part names)
- SAM 2.1's Hiera-Large provides strong boundary quality on hair/fabric
- Alternative considered: SAM 3 (too new, unstable on Windows as of 2026-04)

### IntrinsicAnything
Chosen over DiLightNet, NeuS-based delighting:
- Outputs both albedo and estimated directional light in one pass
- Compatible with TRELLIS output format (both use equirectangular intermediate)
- Alternative considered and rejected: DiLightNet (harder to integrate, no ready-made PyTorch weights)

### TRELLIS (over Hunyuan3D 2.1)
Chosen because:
- Outputs high-quality PBR textures natively, not just vertex colour
- Structured latents produce cleaner topology
- Active maintenance by Microsoft as of 2026-04
- Hunyuan3D 2.1 is a strong alternative; locked as future swap if TRELLIS licensing changes

### FLUX.1-schnell NF4 (over SDXL / FLUX.1-dev)
Chosen because:
- 4-step inference (8–12 s per image on 5070 Ti) fits latency budget
- NF4 quantisation fits 12 GB headroom
- Schnell's distilled guidance removes the need for CFG — saves VRAM and time
- PuLID support is strong on FLUX
- Alternative considered: FLUX.1-dev Q4_K_S GGUF — higher quality ceiling but 25+ step inference, latency too high for interactive edits

### PuLID-FLUX (over InstantID, InfU)
Chosen because:
- Best face identity preservation on FLUX backbone in 2025–2026 head-to-head evals
- Ships as LoRA, minimal VRAM delta
- InfU was considered; ~1.5 GB larger and harder to compose with ControlNets

### FLUX ControlNet Union Pro (over separate Depth + Normal + Canny ControlNets)
Chosen because:
- Single model handles multiple control modalities via task conditioning
- Saves ~2 GB vs. loading two separate ControlNets
- Quality parity with task-specific ControlNets (confirmed in Shakker Labs report, 2025)

## 3. Lifecycle — when models load and unload

Workers hold models under a `ModelRegistry` (`backend/app/rendering/model_registry.py`) that enforces:
- At most one "heavy" model (≥ 5 GB) in VRAM per worker at any time
- Adapters (LoRAs, IP-Adapters, ControlNets) may coexist with a heavy model
- `.unload()` called explicitly before loading a new heavy model; triggers `torch.cuda.empty_cache()`

Example Pipeline A flow per asset (time-ordered):
```
load Qwen2.5-VL → infer → unload (free 6 GB)
load SAM 2.1 + GroundingDINO → infer → unload (free 5 GB)
load IntrinsicAnything → infer → unload (free 6 GB)
load TRELLIS → infer → unload (free 10 GB)
load Blender Eevee (subprocess) + CLIP → validate → unload (free 4 GB)
→ approval queue
```

Pipeline B refinement stage keeps FLUX-NF4 + PuLID LoRA + ControlNet Union + IP-Adapter loaded as a single bundle, since all are needed per camera render.

## 4. Install + first-run verification

Phase 0 Week 1 Day 3–5: each model gets its own verification script under `backend/scripts/verify/`:
- `verify_qwen_vl.py` — load, describe a sample image, assert VRAM peak
- `verify_grounding_sam.py`
- `verify_intrinsic.py`
- `verify_trellis.py`
- `verify_sam3d_body.py`
- `verify_flux_schnell.py`
- `verify_pulid_flux.py`
- `verify_controlnet_union.py`
- `verify_ipadapter_flux.py`

Each script prints:
```
MODEL:     <identifier>
QUANT:     <quant>
LOAD_MS:   <ms>
INFER_MS:  <ms on reference input>
PEAK_VRAM: <MiB>
STATUS:    OK | FAIL
```

Phase 0 acceptance = every script prints `STATUS: OK` and the peak VRAM matches this table's prediction within ±10 %.

## 5. Model download manifest

Total disk space required: **~95 GB**. Downloads managed by `backend/scripts/download_models.py`:

```python
MODELS = [
    {"id": "Qwen/Qwen2.5-VL-7B-Instruct-AWQ", "size_gb": 8.0},
    {"id": "IDEA-Research/grounding-dino-tiny", "size_gb": 0.8},
    {"id": "facebook/sam2.1-hiera-large", "size_gb": 2.4},
    {"id": "zxhezexin/IntrinsicAnything", "size_gb": 6.0},
    {"id": "microsoft/TRELLIS-image-large", "size_gb": 14.0},
    {"id": "facebook/sam3d-body", "size_gb": 5.0},
    {"id": "black-forest-labs/FLUX.1-schnell", "size_gb": 24.0},
    {"id": "guozinan/PuLID", "size_gb": 1.2},
    {"id": "Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro", "size_gb": 2.4},
    {"id": "InstantX/FLUX.1-dev-IP-Adapter", "size_gb": 1.0},
    {"id": "openai/clip-vit-large-patch14", "size_gb": 1.6},
]
```

All models use `HF_HOME` cache (default `~/.cache/huggingface`). Explicit cache dir configurable via `HF_HUB_CACHE` env var.

## 6. Version-pinning policy

Every model ID above is a "target" at time of spec lock (2026-04-17). The runtime resolves to a **specific commit hash**, recorded per-run in `Render.refinement_model` (as `model_id@commit_hash`). This gives us reproducibility without forcing a specific hash in this document.

Model version updates are proposed via PR; the PR must include:
- Diff of benchmark numbers against the old version on the 10 canonical test scenes
- Updated peak-VRAM row in §1
- Updated `DecompositionRun.pipeline_version` if Pipeline A is affected
