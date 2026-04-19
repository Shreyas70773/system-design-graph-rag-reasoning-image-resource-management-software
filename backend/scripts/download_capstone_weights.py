"""Download the minimal capstone model weights.

Downloads:
- SAM 2.1 Hiera Large checkpoint
- Big-LaMa weights snapshot

Examples:
    python backend/scripts/download_capstone_weights.py
    python backend/scripts/download_capstone_weights.py --skip-lama
"""

from __future__ import annotations

import argparse
from pathlib import Path


def ensure_hf() -> None:
    try:
        import huggingface_hub  # noqa: F401
    except ImportError as exc:  # pragma: no cover - simple CLI guard
        raise SystemExit("Install huggingface_hub first: pip install huggingface_hub") from exc


def download_sam2(dest: Path) -> Path:
    from huggingface_hub import hf_hub_download

    dest.mkdir(parents=True, exist_ok=True)
    file_path = hf_hub_download(
        repo_id="facebook/sam2.1-hiera-large",
        filename="sam2.1_hiera_large.pt",
        local_dir=str(dest),
        local_dir_use_symlinks=False,
    )
    return Path(file_path)


def download_big_lama(dest: Path) -> Path:
    from huggingface_hub import snapshot_download

    dest.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id="smartywu/big-lama",
        local_dir=str(dest),
        local_dir_use_symlinks=False,
    )
    return dest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sam2-dir", default="backend/checkpoints", help="Directory for SAM 2 checkpoint")
    parser.add_argument("--lama-dir", default="models/big-lama", help="Directory for Big-LaMa weights")
    parser.add_argument("--skip-sam2", action="store_true")
    parser.add_argument("--skip-lama", action="store_true")
    args = parser.parse_args()

    ensure_hf()

    if not args.skip_sam2:
        sam2_path = download_sam2(Path(args.sam2_dir))
        print(f"[OK] SAM2 checkpoint: {sam2_path}")

    if not args.skip_lama:
        lama_path = download_big_lama(Path(args.lama_dir))
        print(f"[OK] Big-LaMa weights: {lama_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
