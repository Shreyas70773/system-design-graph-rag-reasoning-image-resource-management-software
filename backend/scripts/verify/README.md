# Model verification scripts

One script per model in `docs/v2/MODEL_STACK_V2.md`. Each script must:

1. Load the model with the exact identifier + quantisation declared in the stack doc
2. Run one inference on a reference input
3. Record `LOAD_MS`, `INFER_MS`, and `PEAK_VRAM` (MiB)
4. Print the output in the exact key-colon-value format below (the parser in `vram_profile_v2.py` is case-insensitive but whitespace-sensitive)
5. Cleanly exit the process — all CUDA memory freed

## Output format

```
MODEL:     <identifier>
QUANT:     <quant>
LOAD_MS:   <ms>
INFER_MS:  <ms>
PEAK_VRAM: <MiB>
STATUS:    OK
```

On error, last line must be `STATUS: FAIL` and stderr can describe why.

## Scripts to implement (Phase 0 Week 1)

- `verify_qwen_vl.py` — `Qwen/Qwen2.5-VL-7B-Instruct-AWQ`
- `verify_grounding_sam.py` — GroundingDINO-Tiny + SAM 2.1 Hiera-Large
- `verify_intrinsic.py` — `zxhezexin/IntrinsicAnything`
- `verify_trellis.py` — `microsoft/TRELLIS-image-large`
- `verify_sam3d_body.py` — `facebook/sam3d-body`
- `verify_flux_schnell.py` — `black-forest-labs/FLUX.1-schnell` (NF4)
- `verify_pulid_flux.py` — FLUX + `guozinan/PuLID` LoRA stacked
- `verify_controlnet_union.py` — `Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro`
- `verify_ipadapter_flux.py` — `InstantX/FLUX.1-dev-IP-Adapter`

Reference input for each lives under `backend/scripts/verify/fixtures/`.

## Peak-VRAM measurement

```python
import torch
torch.cuda.reset_peak_memory_stats()
# ... load + infer ...
peak_mb = torch.cuda.max_memory_allocated() // (1024 * 1024)
print(f"PEAK_VRAM: {peak_mb}")
```

This measures only the PyTorch-allocated peak. For subprocess-based models
(Blender), `vram_profile_v2.py` falls back to nvidia-smi sampling.
