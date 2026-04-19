"""Verify Qwen2.5-VL-7B-Instruct-AWQ loads + infers within budget."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _harness import verify  # noqa: E402


def load_and_infer():
    import time
    from PIL import Image
    from transformers import AutoModelForVision2Seq, AutoProcessor
    model_id = "Qwen/Qwen2.5-VL-7B-Instruct-AWQ"
    proc = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForVision2Seq.from_pretrained(
        model_id, device_map="cuda", torch_dtype="auto", trust_remote_code=True,
    )
    img = Image.new("RGB", (512, 512), (200, 120, 60))
    t = time.time()
    inputs = proc(images=img, text="Describe this image briefly as JSON.", return_tensors="pt").to("cuda")
    _ = model.generate(**inputs, max_new_tokens=32)
    return {"infer_ms": (time.time() - t) * 1000}


if __name__ == "__main__":
    raise SystemExit(verify(
        model_id="Qwen/Qwen2.5-VL-7B-Instruct-AWQ",
        quant="AWQ int4",
        load_and_infer=load_and_infer,
        fallback_peak_mb=6400,
    ))
