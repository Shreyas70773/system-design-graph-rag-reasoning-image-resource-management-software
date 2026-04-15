"""
Run VRAM and latency profiling for research methods and emit reproducible artifacts.

Outputs:
- docs/artifacts/vram_profile_runs.csv
- docs/artifacts/vram_profile_summary.json
- docs/artifacts/vram_profile_report_generated.md
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


DEFAULT_MATRIX: List[Dict[str, Any]] = [
    {
        "run_id": "R01",
        "method": "prompt_only",
        "resolution": "768",
        "steps": 30,
        "sampler": "default",
        "precision": "fp16",
        "adapters": "none",
        "guidance_mode": "none",
        "decode_mode": "none",
        "batch_size": 1,
    },
    {
        "run_id": "R02",
        "method": "retrieval_prompt",
        "resolution": "768",
        "steps": 30,
        "sampler": "default",
        "precision": "fp16",
        "adapters": "none",
        "guidance_mode": "none",
        "decode_mode": "none",
        "batch_size": 1,
    },
    {
        "run_id": "R03",
        "method": "adapter_only",
        "resolution": "768",
        "steps": 30,
        "sampler": "default",
        "precision": "fp16",
        "adapters": "control_stack_v1",
        "guidance_mode": "none",
        "decode_mode": "sparse",
        "batch_size": 1,
    },
    {
        "run_id": "R04",
        "method": "graph_guided",
        "resolution": "768",
        "steps": 30,
        "sampler": "default",
        "precision": "fp16",
        "adapters": "control_stack_v1",
        "guidance_mode": "proxy",
        "decode_mode": "sparse",
        "batch_size": 1,
    },
    {
        "run_id": "R05",
        "method": "graph_guided",
        "resolution": "1024",
        "steps": 30,
        "sampler": "default",
        "precision": "fp16",
        "adapters": "control_stack_v1",
        "guidance_mode": "proxy",
        "decode_mode": "sparse",
        "batch_size": 1,
    },
]


def query_gpu_memory_mb() -> Optional[Dict[str, Any]]:
    """Read current GPU memory usage via nvidia-smi, if available."""
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        first = output.strip().splitlines()[0]
        name, used, total = [item.strip() for item in first.split(",")]
        return {
            "name": name,
            "memory_used_mb": float(used),
            "memory_total_mb": float(total),
        }
    except Exception:
        return None


class GPUSampler:
    """Sample GPU memory in background while a run executes."""

    def __init__(self, interval_seconds: float = 0.5):
        self.interval_seconds = interval_seconds
        self.samples: List[float] = []
        self.gpu_name: Optional[str] = None
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            sample = query_gpu_memory_mb()
            if sample is not None:
                self.gpu_name = sample.get("name")
                self.samples.append(float(sample["memory_used_mb"]))
            time.sleep(self.interval_seconds)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=2.0)


@dataclass
class RunResult:
    run_id: str
    method: str
    resolution: str
    steps: int
    sampler: str
    precision: str
    adapters: str
    guidance_mode: str
    decode_mode: str
    batch_size: int
    status: str
    total_latency_s: float
    peak_vram_gb: Optional[float]
    avg_vram_gb: Optional[float]
    oom_event: bool
    run_api_id: Optional[str]
    error: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "method": self.method,
            "resolution": self.resolution,
            "steps": self.steps,
            "sampler": self.sampler,
            "precision": self.precision,
            "adapters": self.adapters,
            "guidance_mode": self.guidance_mode,
            "decode_mode": self.decode_mode,
            "batch_size": self.batch_size,
            "status": self.status,
            "total_latency_s": round(self.total_latency_s, 4),
            "peak_vram_gb": None if self.peak_vram_gb is None else round(self.peak_vram_gb, 4),
            "avg_vram_gb": None if self.avg_vram_gb is None else round(self.avg_vram_gb, 4),
            "oom_event": self.oom_event,
            "run_api_id": self.run_api_id,
            "error": self.error,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run VRAM profiling matrix against research API")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Backend API base URL")
    parser.add_argument("--brand-id", required=True, help="Brand ID used for profiling runs")
    parser.add_argument("--prompt", default="Research VRAM profiling scene", help="Prompt for profiling runs")
    parser.add_argument("--matrix-file", default=None, help="Optional JSON file containing profiling matrix")
    parser.add_argument("--out-dir", default="../docs/artifacts", help="Output artifact directory")
    parser.add_argument("--sample-interval", type=float, default=0.5, help="GPU sample interval seconds")
    parser.add_argument("--seed-set", default="11,22,33", help="Comma-separated integer seeds")
    parser.add_argument("--timeout", type=float, default=300.0, help="Per-request timeout seconds")
    parser.add_argument("--dry-run", action="store_true", help="Generate matrix output without API execution")
    return parser.parse_args()


def load_matrix(matrix_file: Optional[str]) -> List[Dict[str, Any]]:
    if not matrix_file:
        return DEFAULT_MATRIX

    with open(matrix_file, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, list):
        raise ValueError("Matrix file must contain a list of run configs")
    return payload


def parse_seeds(seed_set: str) -> List[int]:
    seeds = []
    for part in seed_set.split(","):
        part = part.strip()
        if not part:
            continue
        seeds.append(int(part))
    return seeds or [11, 22, 33]


def build_payload(config: Dict[str, Any], brand_id: str, prompt: str, seeds: List[int]) -> Dict[str, Any]:
    method = str(config.get("method", "graph_guided"))

    return {
        "brand_id": brand_id,
        "prompt": prompt,
        "method_name": method,
        "seeds": seeds,
        "num_inference_steps": int(config.get("steps", 30)),
        "guidance_scale": 7.5,
        "aspect_ratio": "1:1",
        "use_comfyui": False,
        "use_proxy_color": True,
        "module_toggles": {
            "color_regularizer": method != "prompt_only",
            "layout_constraint": method in {"adapter_only", "graph_guided"},
            "identity_lock": method in {"adapter_only", "graph_guided"},
            "dynamic_cfg": method == "graph_guided",
        },
        "notes": f"vram_profile:{config.get('run_id')}",
    }


def execute_config(
    api_url: str,
    config: Dict[str, Any],
    brand_id: str,
    prompt: str,
    seeds: List[int],
    sample_interval: float,
    timeout_seconds: float,
    dry_run: bool,
) -> RunResult:
    sampler = GPUSampler(interval_seconds=sample_interval)
    payload = build_payload(config, brand_id, prompt, seeds)

    run_id = str(config.get("run_id", "unknown"))
    method = str(config.get("method", "graph_guided"))
    status = "pending"
    api_run_id = None
    error = None
    oom_event = False

    started = time.perf_counter()
    sampler.start()
    try:
        if dry_run:
            status = "dry_run"
        else:
            response = requests.post(
                f"{api_url.rstrip('/')}/api/research/generate-controlled",
                json=payload,
                timeout=timeout_seconds,
            )
            if response.status_code == 200:
                body = response.json()
                api_run_id = body.get("run_id")
                status = "completed"
            else:
                status = "failed"
                error = f"HTTP {response.status_code}: {response.text[:500]}"
                if "out of memory" in response.text.lower() or "cuda" in response.text.lower():
                    oom_event = True
    except Exception as exc:
        status = "failed"
        error = str(exc)
        if "out of memory" in str(exc).lower() or "cuda" in str(exc).lower():
            oom_event = True
    finally:
        sampler.stop()

    elapsed = time.perf_counter() - started
    peak_vram_gb = None
    avg_vram_gb = None
    if sampler.samples:
        peak_vram_gb = max(sampler.samples) / 1024.0
        avg_vram_gb = statistics.mean(sampler.samples) / 1024.0

    return RunResult(
        run_id=run_id,
        method=method,
        resolution=str(config.get("resolution", "768")),
        steps=int(config.get("steps", 30)),
        sampler=str(config.get("sampler", "default")),
        precision=str(config.get("precision", "fp16")),
        adapters=str(config.get("adapters", "none")),
        guidance_mode=str(config.get("guidance_mode", "none")),
        decode_mode=str(config.get("decode_mode", "none")),
        batch_size=int(config.get("batch_size", 1)),
        status=status,
        total_latency_s=elapsed,
        peak_vram_gb=peak_vram_gb,
        avg_vram_gb=avg_vram_gb,
        oom_event=oom_event,
        run_api_id=api_run_id,
        error=error,
    )


def write_csv(results: List[RunResult], out_path: Path) -> None:
    rows = [r.to_dict() for r in results]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["run_id", "status"])
        writer.writeheader()
        writer.writerows(rows)


def write_summary(results: List[RunResult], out_path: Path, metadata: Dict[str, Any]) -> None:
    payload = {
        "metadata": metadata,
        "results": [r.to_dict() for r in results],
        "stats": {
            "total_runs": len(results),
            "completed_runs": len([r for r in results if r.status == "completed"]),
            "failed_runs": len([r for r in results if r.status == "failed"]),
            "oom_runs": len([r for r in results if r.oom_event]),
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def write_markdown(results: List[RunResult], out_path: Path, metadata: Dict[str, Any]) -> None:
    lines: List[str] = []
    lines.append("# Generated VRAM Profiling Report")
    lines.append("")
    lines.append(f"Generated at: {metadata['generated_at_utc']}")
    lines.append(f"API URL: {metadata['api_url']}")
    lines.append(f"Brand ID: {metadata['brand_id']}")
    lines.append(f"Dry run: {metadata['dry_run']}")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| run_id | method | status | peak_vram_gb | avg_vram_gb | latency_s | oom_event | run_api_id |")
    lines.append("|---|---|---|---:|---:|---:|---|---|")
    for result in results:
        lines.append(
            f"| {result.run_id} | {result.method} | {result.status} | "
            f"{'' if result.peak_vram_gb is None else round(result.peak_vram_gb, 4)} | "
            f"{'' if result.avg_vram_gb is None else round(result.avg_vram_gb, 4)} | "
            f"{round(result.total_latency_s, 4)} | {result.oom_event} | {result.run_api_id or ''} |"
        )

    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- This report is generated automatically from backend/scripts/run_vram_profile.py.")
    lines.append("- If peak_vram_gb is empty, nvidia-smi was unavailable during capture.")
    lines.append("- Replace dry_run with live execution before closing blocker B2.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    args = parse_args()
    matrix = load_matrix(args.matrix_file)
    seeds = parse_seeds(args.seed_set)

    out_dir = Path(args.out_dir).resolve()
    results: List[RunResult] = []

    for config in matrix:
        result = execute_config(
            api_url=args.api_url,
            config=config,
            brand_id=args.brand_id,
            prompt=args.prompt,
            seeds=seeds,
            sample_interval=args.sample_interval,
            timeout_seconds=args.timeout,
            dry_run=args.dry_run,
        )
        results.append(result)
        print(json.dumps(result.to_dict(), indent=2))

    metadata = {
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "api_url": args.api_url,
        "brand_id": args.brand_id,
        "prompt": args.prompt,
        "seed_set": seeds,
        "dry_run": args.dry_run,
        "cwd": os.getcwd(),
    }

    write_csv(results, out_dir / "vram_profile_runs.csv")
    write_summary(results, out_dir / "vram_profile_summary.json", metadata)
    write_markdown(results, out_dir / "vram_profile_report_generated.md", metadata)

    print(f"Artifacts written to: {out_dir}")


if __name__ == "__main__":
    main()
