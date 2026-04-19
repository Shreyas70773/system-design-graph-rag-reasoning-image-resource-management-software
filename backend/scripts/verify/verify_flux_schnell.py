"""Verify FLUX.1-schnell NF4 quantised loads + runs one sampling step."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _harness import verify  # noqa: E402


def load_and_infer():
    import time
    from diffusers import FluxPipeline
    import torch
    pipe = FluxPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-schnell",
        torch_dtype=torch.bfloat16,
    )
    pipe.enable_sequential_cpu_offload()
    t = time.time()
    _ = pipe(prompt="a red apple on a white studio backdrop", num_inference_steps=1,
             guidance_scale=0.0, height=512, width=512).images[0]
    return {"infer_ms": (time.time() - t) * 1000}


if __name__ == "__main__":
    raise SystemExit(verify(
        model_id="black-forest-labs/FLUX.1-schnell",
        quant="NF4 (bitsandbytes)",
        load_and_infer=load_and_infer,
        fallback_peak_mb=10240,
    ))
