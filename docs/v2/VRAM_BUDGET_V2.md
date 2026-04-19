# VRAM_BUDGET_V2

**Version:** 2.0.0  
**Target:** RTX 5070 Ti Ultra, 12 GB VRAM  
**Hard ceiling (CI gate):** 11.5 GB peak per stage

---

## 1. Budget table (hard limits)

Every row is enforced by `backend/scripts/vram_profile_v2.py` in CI. Exceeding a limit by > 5 % fails the build.

### Pipeline A — Asset ingestion

| Step | Model(s) in VRAM | Budget (GB) | Measured |
|---|---|---|---|
| 1. Intake | — | 0.0 | — |
| 2. VLM describe | Qwen2.5-VL-7B AWQ + CLIP | 7.8 | TBD |
| 3. Segment | GroundingDINO + SAM 2.1 | 5.3 | TBD |
| 4. Delight | IntrinsicAnything | 6.0 | TBD |
| 5. Mesh (TRELLIS) | TRELLIS | **10.0** ← peak | TBD |
| 6. Validate | Blender subprocess + CLIP | 4.0 | TBD |
| 7. Approve | — | 0.0 | — |

**Pipeline A peak: 10.0 GB.** Headroom: 1.5 GB for allocator overhead and safety.

### Pipeline B — Scene assembly and refinement

| Stage | Model(s) in VRAM | Budget (GB) | Measured |
|---|---|---|---|
| 1. Parse intent | — (Groq API) | 0.0 | — |
| 2. Graph-RAG | CLIP small (CPU ok) | 0.5 | TBD |
| 3. Scene build | — | 0.0 | — |
| 4. Blender render | Blender Eevee subprocess | 4.0 | TBD |
| 5. Refinement | FLUX-NF4 + PuLID LoRA + CNet Union + IP-Adapter | **11.0** ← peak | TBD |
| 6. Text compose | — (Pillow) | 0.0 | — |
| 7. Colour grade | — (NumPy) | 0.0 | — |
| 8. Write | — | 0.0 | — |

**Pipeline B peak: 11.0 GB.** Stages 4 and 5 are strictly sequential, never concurrent.

### Pipeline C — Interaction processing

| Branch | Model(s) in VRAM | Budget (GB) | Measured |
|---|---|---|---|
| Structured edit | — | 0.0 | — |
| NL edit | Qwen2.5-VL-7B AWQ + SAM 2.1 | 10.0 ← peak | TBD |
| Distiller | — | 0.0 | — |

**Pipeline C peak: 10.0 GB** (only on NL edits).

## 2. Concurrency rules

1. **No two pipelines run in the same worker process.** Separate Python processes.
2. **A single worker process loads at most one heavy model (≥ 5 GB) at any time.** Adapters may coexist.
3. **Pipeline A and Pipeline B never run concurrently on the same GPU.** The queue serialises.
4. **Pipeline C NL edits compete with Pipeline B refinement.** The queue scheduler detects an in-flight refinement and delays NL edits until after.
5. **Blender subprocesses count against VRAM even though they are separate processes** — CUDA contexts from Blender and the Python worker share the 12 GB pool. Enforced by: only launch Blender when Python worker has no heavy model loaded.

## 3. Measurement methodology

`backend/scripts/vram_profile_v2.py`:

- Uses `torch.cuda.reset_peak_memory_stats()` before each stage
- Captures `torch.cuda.max_memory_allocated()` and `torch.cuda.max_memory_reserved()` after
- Also captures GPU-wide peak via `nvidia-smi --query-gpu=memory.used --format=csv --loop-ms=100` to catch non-PyTorch allocations (Blender Eevee)
- Writes JSON + Markdown report to `docs/artifacts/vram_profile_v2/<timestamp>/`
- CI compares against this file's budget table

Sample output format:
```
Pipeline A, Step 5 (Mesh / TRELLIS):
  torch peak allocated:  9856 MiB
  torch peak reserved:   9920 MiB
  nvidia-smi peak:       9980 MiB
  budget:               10240 MiB  (10.0 GB)
  result:                OK (3.9 % under budget)
```

## 4. Runtime optimisations already assumed in budgets

- **Sequential CPU offload** is enabled on FLUX-NF4 → used to reclaim VRAM between cameras
- **Attention slicing** enabled on refinement stage
- **VAE tiling** enabled for outputs > 1024 px
- **`torch.cuda.empty_cache()`** called:
  - After every step in Pipeline A
  - After every camera in Pipeline B Stage 5
  - Before launching Blender subprocess
- **Gradient computation globally disabled** in all inference paths (`torch.inference_mode()`)
- **No `.cuda()` in hot paths** — models use `.to(device)` once at load time

## 5. What "over budget" looks like and how to respond

| Situation | Response |
|---|---|
| One stage over by ≤ 5 % on one commit | Warning in CI, investigate within 48 h |
| Over by > 5 % on one commit | CI red, commit blocked until fixed |
| Persistent creep over 3 commits | Emergency review: one of the runtime optimisations has been disabled or a dep update has increased memory |
| Catastrophic OOM on a user machine | Trigger R-3 contingency ladder (GGUF fallback, SDXL-Turbo fallback) |

## 6. Fallback budgets

If the primary refinement stack fails on target hardware, these alternatives ship with their own budgets:

| Fallback | Peak (GB) | Quality delta |
|---|---|---|
| FLUX schnell GGUF Q4_K_S + CNet Union | 8.0 | -5 % CLIP-I, visible on details |
| SDXL-Turbo + CNet Depth + IP-Adapter | 9.5 | -15 % brand identity, -10 % sharpness |
| Previz-only (no refinement) | 4.0 | -40 % photoreal rating |

The project ships even in the worst case; what varies is the "Refined" flag on renders.
