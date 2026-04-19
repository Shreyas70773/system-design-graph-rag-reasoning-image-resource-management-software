"""Shared rendering helpers.

Houses the model registry (VRAM discipline per invariant I-6), object-ID
pass utilities, depth-pass utilities, and HDRI handling. Not a pipeline; a
library used by Pipelines A and B.
"""

from .model_registry import ModelRegistry  # noqa: F401

__all__ = ["ModelRegistry"]
