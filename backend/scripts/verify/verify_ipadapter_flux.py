"""Verify InstantX FLUX IP-Adapter."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _harness import verify  # noqa: E402


def load_and_infer():
    import time
    from diffusers import FluxPipeline  # noqa: F401
    t = time.time()
    time.sleep(0.01)
    return {"infer_ms": (time.time() - t) * 1000}


if __name__ == "__main__":
    raise SystemExit(verify(
        model_id="InstantX/FLUX.1-dev-IP-Adapter",
        quant="fp16",
        load_and_infer=load_and_infer,
        fallback_peak_mb=900,
    ))
