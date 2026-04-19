from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.capstone.store import capstone_scene_store
from app.main import app


client = TestClient(app)


def _make_png(path: Path, color=(240, 240, 240), size=(256, 256)) -> Path:
    Image.new("RGB", size, color).save(path, format="PNG")
    return path


def test_capstone_upload_and_remove_flow_with_mocked_models(tmp_path, monkeypatch):
    capstone_scene_store.root = tmp_path / "scenes"
    capstone_scene_store.root.mkdir(parents=True, exist_ok=True)

    upload_bytes = io.BytesIO()
    Image.new("RGB", (256, 256), (245, 245, 245)).save(upload_bytes, format="PNG")
    upload_bytes.seek(0)

    upload_resp = client.post(
        "/api/v3/scenes/upload",
        files={"file": ("scene.png", upload_bytes.getvalue(), "image/png")},
        data={"title": "Test Scene"},
    )
    assert upload_resp.status_code == 200, upload_resp.text
    scene = upload_resp.json()
    scene_id = scene["scene"]["scene_id"]

    mask_path = _make_png(tmp_path / "mask.png", color=(255, 255, 255))
    result_path = _make_png(tmp_path / "result.png", color=(220, 220, 220))

    def _fake_segment(image_url, click_x, click_y, label, tuning=None):  # noqa: ARG001
        return {
            "mask_url": str(mask_path),
            "bbox": [40, 60, 140, 180],
            "img_width": 256,
            "img_height": 256,
            "area_fraction": 0.1,
            "method": "sam2.1_click",
            "score": 0.98,
            "tuning": tuning.model_dump() if tuning else {},
        }

    def _fake_inpaint(image_url, mask_url, tuning=None):  # noqa: ARG001
        return {
            "result_url": str(result_path),
            "method": "lama/big-lama",
            "tuning": tuning.model_dump() if tuning else {},
        }

    monkeypatch.setattr("app.routers.v3_capstone.sam2_segmenter.segment_from_click", _fake_segment)
    monkeypatch.setattr("app.routers.v3_capstone.lama_inpainter.inpaint", _fake_inpaint)

    segment_resp = client.post(
        f"/api/v3/scenes/{scene_id}/segment-click",
        json={
            "click_x": 0.5,
            "click_y": 0.5,
            "label": "chair",
            "tuning": {"multimask_strategy": "largest_mask", "dilate_px": 2},
        },
    )
    assert segment_resp.status_code == 200, segment_resp.text
    object_id = segment_resp.json()["scene_object_id"]

    remove_resp = client.post(
        f"/api/v3/scenes/{scene_id}/remove-object",
        json={"object_id": object_id, "tuning": {"mask_dilate_px": 8, "neighbor_limit": 6}},
    )
    assert remove_resp.status_code == 200, remove_resp.text
    payload = remove_resp.json()
    assert payload["removed_object_id"] == object_id
    assert payload["history_size"] >= 2
    assert payload["objects"] == []


def test_accuracy_presets_endpoint():
    response = client.get("/api/v3/accuracy-presets")
    assert response.status_code == 200
    payload = response.json()
    assert "segmentation" in payload
    assert "inpainting" in payload
