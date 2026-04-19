"""Verify whether local SAM 2 and LaMa paths are ready for the capstone flow."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.capstone.inference import lama_inpainter, sam2_segmenter


def main() -> int:
    payload = {
        "sam2": sam2_segmenter.status(),
        "lama": lama_inpainter.status(),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
