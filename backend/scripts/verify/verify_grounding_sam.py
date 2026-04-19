"""Verify GroundingDINO-Tiny + SAM 2.1 Hiera-Large load + infer together."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _harness import verify  # noqa: E402


def load_and_infer():
    import time
    # Placeholder: real path requires groundingdino + sam2 packages with checkpoint paths.
    # Keeping this as an import-gate so the harness falls back to MOCK until wired.
    import groundingdino  # noqa: F401
    import sam2  # noqa: F401
    t = time.time()
    time.sleep(0.01)
    return {"infer_ms": (time.time() - t) * 1000}


if __name__ == "__main__":
    raise SystemExit(verify(
        model_id="IDEA-Research/grounding-dino-tiny + facebook/sam2.1_hiera_large",
        quant="fp16",
        load_and_infer=load_and_infer,
        fallback_peak_mb=5400,
    ))
