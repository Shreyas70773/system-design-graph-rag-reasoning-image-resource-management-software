from __future__ import annotations

import io
import os
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from app.capstone.models import InpaintTuning, SegmentationTuning
from app.capstone.runtime import (
    get_capstone_runtime_settings,
    has_sam2,
    has_torch,
    resolve_device,
)
from app.rendering.storage import fetch_image_bytes, put_bytes, save_pil


class SAM2UnavailableError(RuntimeError):
    """Raised when SAM 2 cannot be used."""


class LaMaUnavailableError(RuntimeError):
    """Raised when LaMa cannot be used."""


def _load_image(image_url: str) -> Image.Image:
    return Image.open(io.BytesIO(fetch_image_bytes(image_url))).convert("RGB")


def _mask_bbox(mask_arr: np.ndarray) -> list[int]:
    ys, xs = np.where(mask_arr > 0)
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def _largest_component(mask_arr: np.ndarray) -> np.ndarray:
    h, w = mask_arr.shape
    visited = np.zeros((h, w), dtype=bool)
    best: list[tuple[int, int]] = []

    for y in range(h):
        for x in range(w):
            if visited[y, x] or mask_arr[y, x] == 0:
                continue
            stack = [(y, x)]
            component: list[tuple[int, int]] = []
            visited[y, x] = True
            while stack:
                cy, cx = stack.pop()
                component.append((cy, cx))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and mask_arr[ny, nx] > 0:
                        visited[ny, nx] = True
                        stack.append((ny, nx))
            if len(component) > len(best):
                best = component

    out = np.zeros_like(mask_arr, dtype=np.uint8)
    for y, x in best:
        out[y, x] = 255
    return out


def refine_mask(mask_arr: np.ndarray, tuning: Optional[SegmentationTuning | InpaintTuning]) -> np.ndarray:
    if tuning is None:
        return (mask_arr > 0).astype(np.uint8) * 255

    refined = (mask_arr > 0).astype(np.uint8) * 255
    if getattr(tuning, "keep_largest_component", False):
        refined = _largest_component(refined)

    image = Image.fromarray(refined, mode="L")
    erode_px = int(getattr(tuning, "erode_px", 0) or 0)
    dilate_px = int(
        getattr(tuning, "dilate_px", 0) or getattr(tuning, "mask_dilate_px", 0) or 0
    )

    for _ in range(erode_px):
        image = image.filter(ImageFilter.MinFilter(3))
    for _ in range(dilate_px):
        image = image.filter(ImageFilter.MaxFilter(3))
    return (np.array(image) > 0).astype(np.uint8) * 255


def _mock_ellipse(image_url: str, click_x: float, click_y: float, label: str) -> Dict:
    img = _load_image(image_url)
    w, h = img.size
    cx = int(click_x * w)
    cy = int(click_y * h)
    rx = max(int(w * 0.18), 24)
    ry = max(int(h * 0.18), 24)
    x0, y0 = max(0, cx - rx), max(0, cy - ry)
    x1, y1 = min(w, cx + rx), min(h, cy + ry)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse([x0, y0, x1, y1], fill=255)
    mask_url = save_pil("capstone/masks", f"{label}-mock.png", mask, fmt="PNG")
    return {
        "mask_url": mask_url,
        "bbox": [x0, y0, x1, y1],
        "img_width": w,
        "img_height": h,
        "area_fraction": round(float(np.count_nonzero(np.array(mask)) / (w * h)), 4),
        "method": "mock_ellipse",
    }


class SAM2ClickSegmenter:
    def __init__(self) -> None:
        self.settings = get_capstone_runtime_settings()
        self.device = resolve_device(self.settings.device_preference)

    def status(self) -> Dict[str, object]:
        checkpoint = self.settings.resolved_sam2_checkpoint
        return {
            "package": has_sam2(),
            "torch": has_torch(),
            "checkpoint_path": str(checkpoint),
            "checkpoint_exists": checkpoint.exists(),
            "config": self.settings.sam2_config,
            "device": self.device,
            "ready": has_sam2() and checkpoint.exists(),
        }

    def segment_from_click(
        self,
        image_url: str,
        click_x: float,
        click_y: float,
        label: str = "object",
        tuning: Optional[SegmentationTuning] = None,
    ) -> Dict:
        state = self.status()
        if not bool(state["ready"]):
            if self.settings.allow_mock_fallbacks:
                return _mock_ellipse(image_url, click_x, click_y, label)
            raise SAM2UnavailableError(
                "SAM 2 is not ready. Set CAPSTONE_SAM2_CHECKPOINT and install the sam2 package."
            )

        predictor = _sam2_predictor(
            self.settings.sam2_config,
            str(self.settings.resolved_sam2_checkpoint),
            self.device,
        )
        img = _load_image(image_url)
        arr = np.array(img)
        h, w = arr.shape[:2]
        predictor.set_image(arr)
        point_coords = np.array([[click_x * w, click_y * h]], dtype=np.float32)
        point_labels = np.array([1], dtype=np.int32)
        masks, scores, _ = predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            multimask_output=True,
        )
        if tuning and tuning.multimask_strategy == "largest_mask":
            areas = [float(mask.sum()) for mask in masks]
            best_idx = int(np.argmax(areas))
        else:
            best_idx = int(np.argmax(scores))

        best = (masks[best_idx] > 0).astype(np.uint8) * 255
        refined = refine_mask(best, tuning)
        area_fraction = float(np.count_nonzero(refined) / (w * h))
        min_area = tuning.min_area_fraction if tuning else 0.0
        if area_fraction < min_area:
            raise RuntimeError(
                f"Segmented mask too small ({area_fraction:.5f} < {min_area:.5f}); adjust click or tuning."
            )

        mask_img = Image.fromarray(refined, mode="L")
        bbox = _mask_bbox(refined)
        mask_url = save_pil("capstone/masks", f"{label}-sam2.png", mask_img, fmt="PNG")
        return {
            "mask_url": mask_url,
            "bbox": bbox,
            "img_width": w,
            "img_height": h,
            "area_fraction": round(area_fraction, 4),
            "method": "sam2.1_click",
            "score": float(scores[best_idx]),
            "tuning": tuning.model_dump() if tuning else {},
        }


@lru_cache(maxsize=1)
def _sam2_predictor(config_path: str, checkpoint_path: str, device: str):
    from sam2.build_sam import build_sam2  # noqa: WPS433
    from sam2.sam2_image_predictor import SAM2ImagePredictor  # noqa: WPS433

    model = build_sam2(config_path, checkpoint_path, device=device)
    return SAM2ImagePredictor(model)


class LaMaInpainter:
    def __init__(self) -> None:
        self.settings = get_capstone_runtime_settings()

    def status(self) -> Dict[str, object]:
        repo = self.settings.resolved_lama_repo_path
        model = self.settings.resolved_lama_model_path
        script = (repo / "bin" / "predict.py") if repo else None
        return {
            "repo_path": str(repo) if repo else None,
            "repo_exists": bool(repo and repo.exists()),
            "predict_script": str(script) if script else None,
            "predict_script_exists": bool(script and script.exists()),
            "model_path": str(model) if model else None,
            "model_exists": bool(model and model.exists()),
            "python_executable": self.settings.lama_python_executable,
            "device": resolve_device(self.settings.device_preference),
            "ready": bool(repo and repo.exists() and script and script.exists() and model and model.exists()),
        }

    def inpaint(self, image_url: str, mask_url: str, tuning: Optional[InpaintTuning] = None) -> Dict:
        state = self.status()
        if not bool(state["ready"]):
            raise LaMaUnavailableError(
                "LaMa is not ready. Set CAPSTONE_LAMA_REPO_PATH and CAPSTONE_LAMA_MODEL_PATH."
            )

        image = _load_image(image_url)
        mask = Image.open(io.BytesIO(fetch_image_bytes(mask_url))).convert("L")
        if mask.size != image.size:
            mask = mask.resize(image.size, Image.NEAREST)
        mask_arr = np.array(mask.point(lambda px: 255 if px >= 127 else 0))
        mask = Image.fromarray(refine_mask(mask_arr, tuning), mode="L")

        repo = self.settings.resolved_lama_repo_path
        model = self.settings.resolved_lama_model_path
        assert repo is not None
        assert model is not None
        device = resolve_device(self.settings.device_preference)

        runtime_root = Path(__file__).resolve().parents[2] / "uploads" / "capstone-runtime"
        runtime_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="capstone-lama-", dir=str(runtime_root)) as tmpdir:
            base = Path(tmpdir)
            indir = base / "input"
            outdir = base / "output"
            indir.mkdir(parents=True, exist_ok=True)
            outdir.mkdir(parents=True, exist_ok=True)

            image_path = indir / "sample.png"
            mask_path = indir / "sample_mask.png"
            image.save(image_path, format="PNG")
            mask.save(mask_path, format="PNG")

            script_path = repo / "bin" / "predict.py"
            rel_model = Path(os.path.relpath(model, start=base)).as_posix()
            command = [
                self.settings.lama_python_executable,
                str(script_path),
                f"model.path={rel_model}",
                "indir=input",
                "outdir=output",
                "dataset.img_suffix=.png",
                f"device={device}",
                "hydra.run.dir=.",
                "hydra.output_subdir=null",
            ]
            env = dict(os.environ)
            env["PYTHONPATH"] = str(repo) + (
                os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
            )
            completed = subprocess.run(
                command,
                cwd=str(base),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    "LaMa predict failed: "
                    + "\n".join(
                        line for line in [completed.stdout[-1000:], completed.stderr[-1000:]] if line
                    )
                )

            result_path = outdir / "sample.png"
            if not result_path.exists():
                candidates = sorted(outdir.glob("*.png"))
                if not candidates:
                    raise RuntimeError("LaMa predict completed but no output image was produced")
                result_path = candidates[0]

            result_bytes = result_path.read_bytes()
            result_url = put_bytes("capstone/inpaints", "lama-result.png", result_bytes, mime="image/png")
            return {
                "result_url": result_url,
                "method": "lama/big-lama",
                "stdout_tail": completed.stdout[-500:],
                "tuning": tuning.model_dump() if tuning else {},
            }


sam2_segmenter = SAM2ClickSegmenter()
lama_inpainter = LaMaInpainter()
