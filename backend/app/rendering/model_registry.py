"""ModelRegistry enforces invariant I-6: one heavy model in VRAM per worker.

Every model load path in Pipelines A and B goes through ``ModelRegistry``.
Adapters (LoRAs, ControlNets, IP-Adapters) are not "heavy" and may coexist
with one heavy base model.

This implementation is intentionally minimal for Phase 0. Week 2 extends it
with eviction policies and explicit HF cache handling.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, Optional

logger = logging.getLogger(__name__)

HEAVY_MODEL_VRAM_THRESHOLD_MB = 5_000


class ModelRegistryError(RuntimeError):
    pass


class ModelRegistry:
    """One heavy model, many adapters, no silent leaks."""

    def __init__(self) -> None:
        self._heavy_model: Optional[Any] = None
        self._heavy_model_key: Optional[str] = None
        self._adapters: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Heavy model slot
    # ------------------------------------------------------------------

    def load_heavy(self, key: str, loader: Callable[[], Any]) -> Any:
        if self._heavy_model_key == key and self._heavy_model is not None:
            return self._heavy_model
        if self._heavy_model is not None:
            logger.info("Evicting heavy model %s to load %s", self._heavy_model_key, key)
            self.unload_heavy()
        logger.info("Loading heavy model %s", key)
        self._heavy_model = loader()
        self._heavy_model_key = key
        return self._heavy_model

    def unload_heavy(self) -> None:
        if self._heavy_model is None:
            return
        key = self._heavy_model_key
        self._heavy_model = None
        self._heavy_model_key = None
        self._free_cuda_cache()
        logger.info("Unloaded heavy model %s", key)

    @contextmanager
    def heavy(self, key: str, loader: Callable[[], Any]) -> Iterator[Any]:
        model = self.load_heavy(key, loader)
        try:
            yield model
        finally:
            self.unload_heavy()

    # ------------------------------------------------------------------
    # Adapter slots
    # ------------------------------------------------------------------

    def load_adapter(self, key: str, loader: Callable[[], Any]) -> Any:
        if key not in self._adapters:
            logger.info("Loading adapter %s", key)
            self._adapters[key] = loader()
        return self._adapters[key]

    def unload_adapter(self, key: str) -> None:
        self._adapters.pop(key, None)

    def unload_all_adapters(self) -> None:
        self._adapters.clear()
        self._free_cuda_cache()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _free_cuda_cache() -> None:
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        except ImportError:
            pass
