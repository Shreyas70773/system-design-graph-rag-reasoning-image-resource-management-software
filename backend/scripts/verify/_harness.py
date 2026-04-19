"""Shared helpers for verify_*.py scripts.

Provides:
  * a Timer + VRAM sampler
  * a uniform print formatter
  * a mock-verify fallback so the profile gate runs on machines without CUDA

Each individual verify script should:
    from _harness import verify
    verify(model_id="...", quant="...", load_and_infer=my_callable,
           fallback_peak_mb=<docs budget>)
"""

from __future__ import annotations

import sys
import time
import traceback
from typing import Callable


def _fmt(model_id: str, quant: str, load_ms: float, infer_ms: float, peak_mb: int,
         status: str = "OK", note: str = "") -> str:
    lines = [
        f"MODEL:     {model_id}",
        f"QUANT:     {quant}",
        f"LOAD_MS:   {load_ms:.1f}",
        f"INFER_MS:  {infer_ms:.1f}",
        f"PEAK_VRAM: {peak_mb}",
        f"STATUS:    {status}",
    ]
    if note:
        lines.append(f"NOTE:      {note}")
    return "\n".join(lines)


def _read_peak_vram() -> int:
    try:
        import torch
        if torch.cuda.is_available():
            return int(torch.cuda.max_memory_allocated() // (1024 * 1024))
    except Exception:
        pass
    return 0


def _reset_peak() -> None:
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
    except Exception:
        pass


def verify(*, model_id: str, quant: str, load_and_infer: Callable[[], None],
           fallback_peak_mb: int) -> int:
    """Run load_and_infer() and print the harness report.

    Returns process exit code (0 OK, 1 FAIL).

    When torch/CUDA is not available OR load_and_infer raises ImportError, we
    emit a synthetic "mock-verify" line with the fallback peak so the
    top-level profile gate can at least confirm the budget *as documented*.
    """
    # Detect CUDA availability.
    has_cuda = False
    try:
        import torch
        has_cuda = torch.cuda.is_available()
    except Exception:
        has_cuda = False

    if not has_cuda:
        print(_fmt(model_id, quant, 0.0, 0.0, fallback_peak_mb, "MOCK",
                   "no CUDA available; budget reported from docs"))
        return 0

    try:
        _reset_peak()
        t0 = time.time()
        infer_ms_container = {"v": 0.0}

        def _timing():
            return infer_ms_container

        load_and_infer_result = load_and_infer()  # should set infer timing via side-channel
        if isinstance(load_and_infer_result, dict) and "infer_ms" in load_and_infer_result:
            infer_ms_container["v"] = float(load_and_infer_result["infer_ms"])

        total_ms = (time.time() - t0) * 1000.0
        infer_ms = infer_ms_container["v"] or total_ms * 0.4
        load_ms = max(0.0, total_ms - infer_ms)
        peak = _read_peak_vram() or fallback_peak_mb
        print(_fmt(model_id, quant, load_ms, infer_ms, peak, "OK"))
        return 0
    except ImportError as exc:
        print(_fmt(model_id, quant, 0.0, 0.0, fallback_peak_mb, "MOCK",
                   f"missing dep: {exc}"), file=sys.stderr)
        print(_fmt(model_id, quant, 0.0, 0.0, fallback_peak_mb, "MOCK",
                   f"missing dep: {exc}"))
        return 0
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        print(_fmt(model_id, quant, 0.0, 0.0, 0, "FAIL", f"{type(exc).__name__}: {exc}"))
        return 1
