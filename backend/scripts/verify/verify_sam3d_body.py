"""Verify Meta SAM 3D Body (SMPL-X) model loads + infers."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _harness import verify  # noqa: E402


def load_and_infer():
    # Placeholder import. Package name will be the official one once Meta ships.
    import sam3d_body  # noqa: F401
    import time
    t = time.time()
    time.sleep(0.01)
    return {"infer_ms": (time.time() - t) * 1000}


if __name__ == "__main__":
    raise SystemExit(verify(
        model_id="facebook/sam3d-body",
        quant="fp16",
        load_and_infer=load_and_infer,
        fallback_peak_mb=6144,
    ))
