"""Pipeline B orchestrator. Wires intent parse → retrieve → build → render →
refine → text → grade → write."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from app.database.neo4j_v2 import neo4j_v2
from app.jobs import JobQueue
from app.scene.assembler import assemble_scene_state
from app.scene.blender_bridge import render_scene
from app.scene.color_grading import grade
from app.scene.intent_parser import parse_intent
from app.scene.refinement import refine
from app.scene.text_compositor import composite_text

logger = logging.getLogger(__name__)


class ScenePipeline:
    def __init__(self, queue: Optional[JobQueue] = None) -> None:
        self.queue = queue

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def create_and_render(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        brand_id = payload["brand_id"]
        intent = payload["intent_text"]
        deploy_ctx = payload.get("deployment_context", "digital")
        cams = payload.get("camera_requests") or [{"shot_type": "hero", "aspect_ratio": "1:1"}]

        # Stage 1.
        spec = parse_intent(intent, brand_id, deploy_ctx, cams)
        # Stages 2 + 3 (retrieve + build + persist).
        scene_id, plan = assemble_scene_state(spec, brand_id)
        # Stages 4–8 per camera.
        renders = self.render_scene_cameras(scene_id, plan)
        return {"scene_id": scene_id, "renders": renders}

    def render_scene_cameras(self, scene_id: str, plan: Optional[Dict[str, Any]] = None,
                             only_camera_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Produce renders for (all or specified) cameras of an existing scene."""
        if plan is None:
            plan = self._plan_from_graph(scene_id)
        if only_camera_ids:
            plan = {**plan, "cameras": [c for c in plan["cameras"] if c["id"] in only_camera_ids]}

        # Stage 4.
        previews = render_scene(plan)
        results: List[Dict[str, Any]] = []
        for preview in previews:
            start = time.time()
            cam_id = preview["camera_id"]
            # Stage 5.
            refined = refine(preview, plan)
            # Stage 6.
            post_text = composite_text(
                refined["refined_url"],
                plan.get("text_layers", []),
                scene_id, cam_id,
            )
            # Stage 7.
            graded = grade(
                post_text,
                plan.get("brand_context", {}).get("colors") or [],
                scene_id, cam_id,
            )
            total_time = time.time() - start
            # Stage 8 — write Render node.
            render_id = neo4j_v2.pipeline_b_add_render(scene_id, {
                "scene_id": scene_id,
                "camera_id": cam_id,
                "image_url": graded,
                "object_id_pass_url": preview["object_id_pass_url"],
                "depth_pass_url": preview["depth_url"],
                "refinement_model": refined["refinement_model"],
                "render_time_sec": total_time,
                "peak_vram_mb": refined.get("peak_vram_mb", 0),
            })
            results.append({
                "render_id": render_id,
                "camera_id": cam_id,
                "image_url": graded,
                "object_id_pass_url": preview["object_id_pass_url"],
                "depth_pass_url": preview["depth_url"],
                "refinement_model": refined["refinement_model"],
                "render_time_sec": total_time,
            })
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _plan_from_graph(self, scene_id: str) -> Dict[str, Any]:
        """Rebuild a plan dict from persisted scene nodes. Used when re-rendering."""
        data = neo4j_v2.get_scene_full(scene_id)
        if not data["scene"]:
            raise ValueError(f"Scene {scene_id} not found")
        scene = data["scene"]
        brand_ctx = neo4j_v2.retrieve_brand_context(scene["brand_id"], scene["deployment_context"])
        return {
            "scene_id": scene_id,
            "brand_id": scene["brand_id"],
            "deployment_context": scene["deployment_context"],
            "brand_context": {
                "brand": brand_ctx["brand"],
                "colors": brand_ctx["colors"],
                "fonts": brand_ctx["fonts"],
                "preferences": brand_ctx["preferences"],
            },
            "placements": [{
                "id": p["id"], "asset_id": p["asset_id"], "position": p.get("position", [0, 0, 0]),
            } for p in data["placements"]],
            "cameras": data["cameras"],
            "lights": data["lights"],
            "text_layers": data["text_layers"],
            "biases": {},
        }
