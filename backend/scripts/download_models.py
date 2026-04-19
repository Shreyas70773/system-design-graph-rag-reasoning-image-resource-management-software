"""Download all V2 model weights listed in MODEL_STACK_V2.md.

Run from the repo root:
    python backend/scripts/download_models.py --all
Or selectively:
    python backend/scripts/download_models.py qwen flux

Total disk footprint ~95 GB. Uses the Hugging Face hub cache at
$HF_HOME (default ~/.cache/huggingface).
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Callable, Dict

MANIFEST: Dict[str, Dict[str, object]] = {
    "qwen":        {"repo": "Qwen/Qwen2.5-VL-7B-Instruct-AWQ",        "files": None, "approx_gb": 6.0},
    "sam2":        {"repo": "facebook/sam2.1-hiera-large",             "files": None, "approx_gb": 2.5},
    "gdino":       {"repo": "IDEA-Research/grounding-dino-tiny",       "files": None, "approx_gb": 0.9},
    "intrinsic":   {"repo": "zxhezexin/IntrinsicAnything",             "files": None, "approx_gb": 5.0},
    "trellis":     {"repo": "microsoft/TRELLIS-image-large",           "files": None, "approx_gb": 12.0},
    "sam3d_body":  {"repo": "facebook/sam3d-body",                     "files": None, "approx_gb": 4.0,
                    "note": "placeholder repo id; confirm once official release ships"},
    "flux":        {"repo": "black-forest-labs/FLUX.1-schnell",        "files": None, "approx_gb": 24.0},
    "pulid":       {"repo": "guozinan/PuLID",                          "files": None, "approx_gb": 1.0},
    "cnet_union":  {"repo": "Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro", "files": None, "approx_gb": 5.5},
    "ipa":         {"repo": "InstantX/FLUX.1-dev-IP-Adapter",          "files": None, "approx_gb": 1.2},
    "clip":        {"repo": "openai/clip-vit-large-patch14",           "files": None, "approx_gb": 1.7},
}


def _download_one(key: str) -> bool:
    entry = MANIFEST[key]
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("huggingface_hub not installed. `pip install huggingface_hub`", file=sys.stderr)
        return False
    try:
        print(f"[download] {key}: {entry['repo']} (~{entry['approx_gb']} GB)")
        snapshot_download(repo_id=entry["repo"], allow_patterns=entry.get("files"))
        print(f"[download] {key}: OK")
        return True
    except Exception as exc:  # noqa: BLE001
        note = entry.get("note") or ""
        print(f"[download] {key}: FAILED ({exc}) {note}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("keys", nargs="*", help=f"Any of: {', '.join(MANIFEST)}")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if args.all:
        keys = list(MANIFEST)
    else:
        keys = [k for k in args.keys if k in MANIFEST]
        unknown = set(args.keys) - set(keys)
        if unknown:
            print(f"Unknown keys: {unknown}. Valid: {list(MANIFEST)}", file=sys.stderr)
            return 2

    if not keys:
        parser.print_help()
        return 0

    failures = 0
    total_gb = sum(float(MANIFEST[k]["approx_gb"]) for k in keys)
    print(f"Downloading {len(keys)} repos, ~{total_gb:.1f} GB total")
    for k in keys:
        ok = _download_one(k)
        if not ok:
            failures += 1
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
