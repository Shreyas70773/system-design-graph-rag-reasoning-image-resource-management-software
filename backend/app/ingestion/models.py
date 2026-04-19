"""Pipeline A job state and step interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Protocol


class StepName(str, Enum):
    INTAKE = "intake"
    DESCRIBE = "describe"
    SEGMENT = "segment"
    DELIGHT = "delight"
    MESH = "mesh"
    VALIDATE = "validate"
    AWAIT_APPROVAL = "await_approval"


@dataclass
class IngestionJob:
    job_id: str
    asset_id: str
    brand_id: str
    source_image_url: str
    current_step: StepName = StepName.INTAKE
    started_at: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None
    progress_pct: int = 0


class IngestionStep(Protocol):
    """Every step implements this interface.

    Steps must:
      - not keep any CUDA memory allocated after returning
      - tolerate repeated invocation (idempotent)
      - record their own timing in the job's metadata
    """

    name: StepName

    def run(self, job: IngestionJob) -> None: ...
