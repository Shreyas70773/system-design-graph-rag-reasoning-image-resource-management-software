"""
Research experiment runner.
Executes controlled generation runs, ablations, and comparison payloads.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from copy import deepcopy
from datetime import datetime
import time
import uuid

from app.database.neo4j_client import get_neo4j_client
from app.generation.image_generators import (
    BrandCondition,
    GenerationRequest,
    get_generator,
)
from app.services.comfy_client import ComfyClient
from app.services.graph_conditioning import DynamicCFGScheduler, GraphConditioner
from app.services.metric_evaluator import MetricEvaluator


class ManifestConflictError(Exception):
    """Raised when an experiment run violates an existing manifest lock."""

    def __init__(self, message: str, conflict: Dict[str, Any]):
        super().__init__(message)
        self.conflict = conflict


class ExperimentRunner:
    """Orchestrates controlled research runs for GraphRAG diffusion experiments."""

    def __init__(self):
        self.neo4j = get_neo4j_client()
        self.metric_evaluator = MetricEvaluator()
        self.comfy_client = ComfyClient()
        self.graph_conditioner = GraphConditioner()
        self.cfg_scheduler = DynamicCFGScheduler()

    async def run_controlled_generation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Run a controlled experiment for a single method across multiple seeds."""
        brand_id = request["brand_id"]
        prompt = request["prompt"]
        method_name = request.get("method_name", "graph_guided")
        image_provider = str(request.get("image_provider", "replicate")).strip().lower() or "replicate"
        seeds = sorted([int(s) for s in (request.get("seeds") or [11, 22, 33])])
        experiment_id = request.get("experiment_id") or f"exp_{datetime.utcnow().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"

        request = dict(request)
        request["experiment_id"] = experiment_id
        request["seeds"] = seeds
        request["image_provider"] = image_provider

        if image_provider == "comfyui":
            request["use_comfyui"] = True

        brand_context = self.neo4j.get_brand_context(brand_id)
        if not brand_context:
            raise ValueError("Brand not found")

        if request.get("product_ids"):
            products = self.neo4j.get_products_by_ids(request.get("product_ids", []))
            if products:
                brand_context["selected_products"] = products

        # Lock parity manifest for this experiment to guarantee seed/prompt/config consistency.
        manifest_payload = self._build_manifest_payload(request)
        manifest_state = self.neo4j.lock_experiment_manifest(manifest_payload)
        if not manifest_state.get("matches"):
            raise ManifestConflictError(
                "Experiment manifest conflict detected.",
                {
                    "experiment_id": experiment_id,
                    "requested_parity_hash": manifest_state.get("requested_parity_hash"),
                    "stored_parity_hash": manifest_state.get("stored_parity_hash"),
                    "differences": manifest_state.get("differences", []),
                    "stored_manifest": manifest_state.get("manifest"),
                    "requested_manifest": manifest_state.get("requested_manifest"),
                },
            )

        run_meta = self.neo4j.create_experiment_run({
            "experiment_id": experiment_id,
            "brand_id": brand_id,
            "method_name": method_name,
            "prompt": prompt,
            "status": "running",
            "seeds": seeds,
            "config": {
                "num_inference_steps": request.get("num_inference_steps", 30),
                "guidance_scale": request.get("guidance_scale", 7.5),
                "aspect_ratio": request.get("aspect_ratio", "1:1"),
                "image_provider": image_provider,
                "module_toggles": request.get("module_toggles", {}),
                "use_comfyui": bool(request.get("use_comfyui", False)),
                "use_proxy_color": bool(request.get("use_proxy_color", True)),
            },
            "notes": request.get("notes"),
            "started_at": datetime.utcnow().isoformat(),
        })

        run_id = run_meta["run_id"]
        started = time.perf_counter()
        candidate_results: List[Dict[str, Any]] = []
        candidate_metrics: List[Dict[str, Any]] = []

        try:
            for seed in seeds:
                candidate = await self._run_single_candidate(
                    brand_context=brand_context,
                    request=request,
                    method_name=method_name,
                    seed=seed,
                )

                candidate_id = self.neo4j.save_experiment_candidate(run_id, candidate)
                candidate["candidate_id"] = candidate_id

                metrics = await self.metric_evaluator.evaluate_candidate(brand_context, candidate)
                self.neo4j.save_metric_snapshot(
                    run_id=run_id,
                    metrics=metrics,
                    level="candidate",
                    candidate_id=candidate_id,
                )

                candidate_results.append(candidate)
                candidate_metrics.append(metrics)

            run_summary = self.metric_evaluator.aggregate_run_metrics(candidate_metrics)
            self.neo4j.save_metric_snapshot(
                run_id=run_id,
                metrics=run_summary,
                level="run",
            )

            duration_ms = int((time.perf_counter() - started) * 1000)
            self.neo4j.update_experiment_run(run_id, {
                "status": "completed",
                "duration_ms": duration_ms,
                "completed_at": datetime.utcnow().isoformat(),
                "result_summary": run_summary,
            })

            return {
                "run_id": run_id,
                "experiment_id": run_meta["experiment_id"],
                "manifest": manifest_state.get("manifest"),
                "brand_id": brand_id,
                "method_name": method_name,
                "status": "completed",
                "duration_ms": duration_ms,
                "summary": run_summary,
                "candidates": candidate_results,
            }

        except Exception as exc:
            self.neo4j.update_experiment_run(run_id, {
                "status": "failed",
                "error_message": str(exc),
                "completed_at": datetime.utcnow().isoformat(),
            })
            raise

    async def run_ablation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Run base method plus ablations under a shared experiment ID."""
        ablations = request.get("ablations") or [
            "without_color_regularizer",
            "without_layout_constraint",
            "without_identity_lock",
            "fixed_cfg",
        ]

        experiment_id = request.get("experiment_id") or f"exp_{uuid.uuid4().hex[:8]}"
        base_method = request.get("base_method", "graph_guided")

        base_toggles = {
            "color_regularizer": True,
            "layout_constraint": True,
            "identity_lock": True,
            "dynamic_cfg": True,
        }

        runs: List[Dict[str, Any]] = []

        base_request = dict(request)
        base_request["experiment_id"] = experiment_id
        base_request["method_name"] = base_method
        base_request["module_toggles"] = base_toggles
        base_request["notes"] = f"Base run for {base_method}"
        runs.append(await self.run_controlled_generation(base_request))

        for ablation_name in ablations:
            toggles = dict(base_toggles)
            if ablation_name == "without_color_regularizer":
                toggles["color_regularizer"] = False
            elif ablation_name == "without_layout_constraint":
                toggles["layout_constraint"] = False
            elif ablation_name == "without_identity_lock":
                toggles["identity_lock"] = False
            elif ablation_name == "fixed_cfg":
                toggles["dynamic_cfg"] = False

            ablation_request = dict(request)
            ablation_request["experiment_id"] = experiment_id
            ablation_request["method_name"] = f"{base_method}:{ablation_name}"
            ablation_request["module_toggles"] = toggles
            ablation_request["notes"] = f"Ablation run: {ablation_name}"

            runs.append(await self.run_controlled_generation(ablation_request))

        return {
            "experiment_id": experiment_id,
            "total_runs": len(runs),
            "runs": runs,
        }

    async def compare_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """Return comparison payload for all runs in an experiment."""
        runs = self.neo4j.compare_experiment_runs(experiment_id)
        if not runs:
            return {
                "experiment_id": experiment_id,
                "run_count": 0,
                "runs": [],
                "comparison": {"run_count": 0, "runs": []},
            }

        comparison = self.metric_evaluator.summarize_comparison(runs)
        return {
            "experiment_id": experiment_id,
            "run_count": len(runs),
            "runs": runs,
            "comparison": comparison,
        }

    async def run_deltae_refinement_job(self, run_id: str) -> Dict[str, Any]:
        """Re-evaluate run candidates with Lab-space DeltaE metrics and store snapshots."""
        run = self.neo4j.get_experiment_run(run_id)
        if not run:
            raise ValueError("Research run not found")

        brand_id = run.get("brand_id")
        brand_context = self.neo4j.get_brand_context(brand_id)
        if not brand_context:
            raise ValueError("Brand context not found for run")

        candidates = run.get("candidates", [])
        candidate_metrics: List[Dict[str, Any]] = []

        started = time.perf_counter()
        for candidate in candidates:
            metrics = await self.metric_evaluator.evaluate_candidate(brand_context, candidate)
            metrics["job_type"] = "deltae_refinement"
            self.neo4j.save_metric_snapshot(
                run_id=run_id,
                metrics=metrics,
                level="candidate",
                candidate_id=candidate.get("id"),
            )
            candidate_metrics.append(metrics)

        run_summary = self.metric_evaluator.aggregate_run_metrics(candidate_metrics)
        run_summary["job_type"] = "deltae_refinement"
        run_summary["deltae_refined_at"] = datetime.utcnow().isoformat()

        snapshot_id = self.neo4j.save_metric_snapshot(
            run_id=run_id,
            metrics=run_summary,
            level="run",
        )

        duration_ms = int((time.perf_counter() - started) * 1000)
        self.neo4j.update_experiment_run(run_id, {
            "status": run.get("status", "completed"),
            "duration_ms": run.get("duration_ms") or duration_ms,
            "result_summary": {
                **(run.get("result_summary") or {}),
                "deltae_refinement": {
                    "snapshot_id": snapshot_id,
                    "completed_at": run_summary["deltae_refined_at"],
                    "duration_ms": duration_ms,
                    "delta_e_ciede2000_mean": run_summary.get("delta_e_ciede2000_mean"),
                    "delta_e_ciede2000_pass_rate_mean": run_summary.get("delta_e_ciede2000_pass_rate_mean"),
                },
            },
        })

        return {
            "run_id": run_id,
            "snapshot_id": snapshot_id,
            "candidate_count": len(candidates),
            "duration_ms": duration_ms,
            "summary": run_summary,
        }

    async def _run_single_candidate(
        self,
        brand_context: Dict[str, Any],
        request: Dict[str, Any],
        method_name: str,
        seed: int,
    ) -> Dict[str, Any]:
        """Execute one seeded candidate run and return structured candidate payload."""
        started = time.perf_counter()
        compiled_prompt = self._build_prompt(method_name, brand_context, request.get("prompt", ""))

        conditioning_packet = self.graph_conditioner.build_packet(
            brand_context=brand_context,
            request=request,
            method_name=method_name,
        )

        total_steps = max(int(request.get("num_inference_steps", 30)), 2)
        dynamic_enabled = bool((request.get("module_toggles") or {}).get("dynamic_cfg", True))
        effective_cfg = self.cfg_scheduler.effective_cfg_for_run(
            base_cfg=float(request.get("guidance_scale", 7.5)),
            total_steps=total_steps,
            confidence=conditioning_packet.confidence,
            dynamic_enabled=dynamic_enabled,
            method_name=method_name,
        )
        cfg_schedule_preview = self.cfg_scheduler.build_schedule_preview(
            base_cfg=float(request.get("guidance_scale", 7.5)),
            total_steps=total_steps,
            confidence=conditioning_packet.confidence,
        )

        def _failed_candidate(error_message: str, provider: str = "comfyui", model_used: str = "comfyui_workflow") -> Dict[str, Any]:
            return {
                "seed": seed,
                "status": "failed",
                "method_name": method_name,
                "image_url": None,
                "model_used": model_used,
                "provider": provider,
                "prompt_used": compiled_prompt,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "colors": [],
                "error_message": error_message,
                "metadata": {
                    "graph_conditioning": conditioning_packet.as_dict(),
                    "cfg_schedule_preview": cfg_schedule_preview,
                    "effective_guidance_scale": effective_cfg,
                },
            }

        # Optional ComfyUI path
        comfy_workflow = request.get("comfy_workflow")
        comfy_selected = bool(request.get("use_comfyui")) or str(request.get("image_provider", "")).strip().lower() == "comfyui"

        if comfy_selected:
            comfy_health = await self.comfy_client.health(auto_start=True)
            if not comfy_health.get("ok"):
                return _failed_candidate(
                    f"ComfyUI health check failed: {comfy_health.get('error', 'unknown error')}"
                )

            workflow_mode = "custom"
            selected_checkpoint = None

            if comfy_workflow and (not isinstance(comfy_workflow, dict) or isinstance(comfy_workflow, list)):
                return _failed_candidate("ComfyUI workflow JSON must be an object keyed by node IDs.")

            if not comfy_workflow:
                checkpoints_result = await self.comfy_client.list_models("checkpoints", auto_start=False)
                if not checkpoints_result.get("ok"):
                    return _failed_candidate(
                        "ComfyUI is reachable but checkpoint listing failed: "
                        f"{checkpoints_result.get('error', 'unknown error')}"
                    )

                checkpoints = checkpoints_result.get("models") or []
                if not checkpoints:
                    return _failed_candidate(
                        "No local ComfyUI checkpoints were found. Install at least one .safetensors/.ckpt model "
                        "under your ComfyUI models/checkpoints folder, then rerun."
                    )

                selected_checkpoint = str(checkpoints[0])
                comfy_workflow = self._build_default_comfy_workflow(
                    prompt=compiled_prompt,
                    negative_prompt=str(request.get("negative_prompt") or "low quality, blurry, distorted, watermark"),
                    seed=seed,
                    steps=total_steps,
                    cfg=effective_cfg,
                    aspect_ratio=str(request.get("aspect_ratio", "1:1")),
                    checkpoint_name=selected_checkpoint,
                )
                workflow_mode = "auto_default"

            try:
                conditioned_workflow = self._inject_conditioning_into_workflow(
                    workflow=comfy_workflow,
                    conditioning=conditioning_packet.as_dict(),
                    effective_cfg=effective_cfg,
                )
                submitted = await self.comfy_client.submit_workflow(conditioned_workflow)
                prompt_id = submitted.get("prompt_id")
                if not prompt_id:
                    return _failed_candidate("ComfyUI submission returned no prompt_id.")

                completion = await self.comfy_client.wait_for_completion(prompt_id)
                if not completion.get("completed"):
                    return _failed_candidate(
                        f"ComfyUI did not complete prompt {prompt_id}: {completion.get('error', 'unknown error')}"
                    )

                image_urls = self.comfy_client.extract_image_urls(completion.get("history", {}))
                if not image_urls:
                    return _failed_candidate(f"ComfyUI completed prompt {prompt_id} but returned no images.")

                latency_ms = int((time.perf_counter() - started) * 1000)
                return {
                    "seed": seed,
                    "status": "completed",
                    "method_name": method_name,
                    "image_url": image_urls[0],
                    "model_used": "comfyui_workflow",
                    "provider": "comfyui",
                    "prompt_used": compiled_prompt,
                    "latency_ms": latency_ms,
                    "colors": [],
                    "metadata": {
                        "prompt_id": prompt_id,
                        "comfy_image_urls": image_urls,
                        "comfy_base_url": comfy_health.get("base_url"),
                        "comfy_workflow_mode": workflow_mode,
                        "comfy_checkpoint": selected_checkpoint,
                        "graph_conditioning": conditioning_packet.as_dict(),
                        "cfg_schedule_preview": cfg_schedule_preview,
                        "effective_guidance_scale": effective_cfg,
                        "layout": request.get("layout", "centered"),
                        "text_position": request.get("text_position", "bottom"),
                        "character_reference_url": conditioning_packet.character_reference_url,
                        "product_reference_url": conditioning_packet.product_reference_url,
                    },
                }
            except Exception as exc:
                error_message = f"ComfyUI execution failed: {exc}"
                normalized = str(exc).lower()
                if any(token in normalized for token in [
                    "pytorchstreamreader",
                    "failed finding central directory",
                    "unexpected eof",
                    "pickle data was truncated",
                    "invalid load key",
                    "file is not a zip file",
                    "safetensors",
                ]):
                    error_message += (
                        " | Hint: the selected checkpoint appears incomplete/corrupted. "
                        "If a model download is still running, wait for completion and retry."
                    )

                return _failed_candidate(error_message)

        generator_provider = str(request.get("image_provider", "replicate")).strip().lower() or "replicate"
        if generator_provider == "comfyui":
            return _failed_candidate(
                "ComfyUI provider selected but ComfyUI path was not executed. Check workflow and health.",
                provider="comfyui",
                model_used="comfyui_workflow",
            )
        generator = get_generator(generator_provider)
        condition = self._build_condition(brand_context, request, method_name)
        if method_name in {"adapter_only", "graph_guided"} and dynamic_enabled:
            condition.style_strength = max(condition.style_strength, min(1.0, 0.55 + (0.35 * conditioning_packet.confidence)))

        gen_request = GenerationRequest(
            prompt=compiled_prompt,
            brand_id=request["brand_id"],
            brand_condition=condition,
            num_images=1,
            guidance_scale=effective_cfg,
            num_inference_steps=request.get("num_inference_steps", 30),
            seed=seed,
        )

        product_ref = condition.product_image_url
        character_ref = condition.face_image_url

        if method_name in {"adapter_only", "graph_guided"} and product_ref and character_ref and hasattr(generator, "generate_with_product_and_character"):
            result = await generator.generate_with_product_and_character(
                gen_request,
                product_ref,
                character_ref,
                condition.product_strength,
                condition.face_strength,
            )
        elif method_name in {"adapter_only", "graph_guided"} and product_ref:
            result = await generator.generate_with_product(gen_request, product_ref, condition.product_strength)
        elif method_name in {"adapter_only", "graph_guided"} and character_ref:
            result = await generator.generate_with_character(gen_request, character_ref, condition.face_strength)
        else:
            result = await generator.generate(gen_request)

        latency_ms = int((time.perf_counter() - started) * 1000)

        if not result.success:
            provider_error = result.error_message or "Image generation failed"
            if result.provider == "fal.ai":
                normalized_error = provider_error.lower()
                if "authentication" in normalized_error or "cannot access application" in normalized_error:
                    provider_error = (
                        f"{provider_error} | Hint: FAL_KEY is missing/invalid or lacks access. "
                        "Set a valid FAL_KEY in backend/.env or switch Image Provider to replicate/comfyui."
                    )
            elif result.provider == "replicate":
                normalized_error = provider_error.lower()
                if "insufficient credit" in normalized_error or "status\":402" in normalized_error:
                    provider_error = (
                        f"{provider_error} | Hint: Replicate credits are required for this model. "
                        "Either add Replicate credit, use ComfyUI with a workflow, or configure FAL_KEY."
                    )

            return {
                "seed": seed,
                "status": "failed",
                "method_name": method_name,
                "image_url": None,
                "model_used": result.model_used,
                "provider": result.provider,
                "prompt_used": compiled_prompt,
                "latency_ms": latency_ms,
                "colors": [],
                "error_message": provider_error,
                "metadata": {
                    "conditioners_used": result.conditioners_used,
                    "graph_conditioning": conditioning_packet.as_dict(),
                    "cfg_schedule_preview": cfg_schedule_preview,
                    "effective_guidance_scale": effective_cfg,
                    "layout": condition.layout,
                    "text_position": condition.text_position,
                    "character_reference_url": condition.face_image_url,
                    "product_reference_url": condition.product_image_url,
                },
            }

        return {
            "seed": seed,
            "status": "completed",
            "method_name": method_name,
            "image_url": result.image_url,
            "model_used": result.model_used,
            "provider": result.provider,
            "prompt_used": result.compiled_prompt or compiled_prompt,
            "latency_ms": latency_ms,
            "colors": [],
            "metadata": {
                "generation_time_ms": result.generation_time_ms,
                "conditioners_used": result.conditioners_used,
                "cost_usd": result.cost_usd,
                "graph_conditioning": conditioning_packet.as_dict(),
                "cfg_schedule_preview": cfg_schedule_preview,
                "effective_guidance_scale": effective_cfg,
                "layout": condition.layout,
                "text_position": condition.text_position,
                "character_reference_url": condition.face_image_url,
                "product_reference_url": condition.product_image_url,
            },
        }

    def _inject_conditioning_into_workflow(
        self,
        workflow: Dict[str, Any],
        conditioning: Dict[str, Any],
        effective_cfg: float,
    ) -> Dict[str, Any]:
        """
        Inject graph-conditioned values into a Comfy workflow when compatible input keys are present.

        This keeps compatibility with generic workflows by only overriding keys that already exist.
        """
        if not isinstance(workflow, dict):
            return workflow

        workflow_copy = deepcopy(workflow)
        for node in workflow_copy.values():
            if not isinstance(node, dict):
                continue

            node_inputs = node.get("inputs")
            if not isinstance(node_inputs, dict):
                continue

            class_type = str(node.get("class_type", "")).lower()

            # Generic sampler cfg override.
            if "cfg" in node_inputs:
                node_inputs["cfg"] = effective_cfg

            # Graph conditioning compatible keys.
            if "graph_cond_vector" in node_inputs:
                node_inputs["graph_cond_vector"] = conditioning.get("palette_vector", [])
            if "constraint_weight_map" in node_inputs:
                node_inputs["constraint_weight_map"] = conditioning.get("constraint_weight_map", {})
            if "layout_priors" in node_inputs:
                node_inputs["layout_priors"] = conditioning.get("layout_priors", {})
            if "style_keywords" in node_inputs:
                node_inputs["style_keywords"] = conditioning.get("style_keywords", [])
            if "conditioning_confidence" in node_inputs:
                node_inputs["conditioning_confidence"] = conditioning.get("confidence", 0.0)

            # Class-specific best-effort mappings.
            if class_type == "graphconditioner":
                if "palette_hex" in node_inputs:
                    node_inputs["palette_hex"] = conditioning.get("palette_hex", [])
                if "brand_id" in node_inputs:
                    node_inputs["brand_id"] = conditioning.get("brand_id")
            elif class_type == "dynamiccfgscheduler":
                if "base_cfg" in node_inputs:
                    node_inputs["base_cfg"] = effective_cfg
                if "confidence" in node_inputs:
                    node_inputs["confidence"] = conditioning.get("confidence", 0.0)

        return workflow_copy

    def _aspect_ratio_to_dimensions(self, aspect_ratio: str) -> tuple[int, int]:
        """Map aspect ratio tokens to practical latent sizes for default Comfy workflows."""
        ratio = str(aspect_ratio or "1:1").strip()
        mapping = {
            "1:1": (1024, 1024),
            "16:9": (1216, 704),
            "9:16": (704, 1216),
            "4:3": (1152, 896),
            "3:4": (896, 1152),
            "3:2": (1152, 768),
            "2:3": (768, 1152),
        }
        return mapping.get(ratio, (1024, 1024))

    def _build_default_comfy_workflow(
        self,
        prompt: str,
        negative_prompt: str,
        seed: int,
        steps: int,
        cfg: float,
        aspect_ratio: str,
        checkpoint_name: str,
    ) -> Dict[str, Any]:
        """Construct a basic text-to-image workflow using CheckpointLoaderSimple."""
        width, height = self._aspect_ratio_to_dimensions(aspect_ratio)
        safe_steps = max(5, min(int(steps), 100))
        safe_cfg = max(1.0, min(float(cfg), 20.0))
        safe_seed = max(0, int(seed))

        return {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": checkpoint_name,
                },
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["1", 1],
                },
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["1", 1],
                },
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1,
                },
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": safe_seed,
                    "steps": safe_steps,
                    "cfg": safe_cfg,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0],
                },
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["5", 0],
                    "vae": ["1", 2],
                },
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "research_lab",
                    "images": ["6", 0],
                },
            },
        }

    def _build_prompt(self, method_name: str, brand_context: Dict[str, Any], user_prompt: str) -> str:
        """Build method-specific prompt text for controlled studies."""
        if method_name == "prompt_only":
            return user_prompt

        brand_name = brand_context.get("name", "Brand")
        colors = [c.get("hex") for c in brand_context.get("colors", []) if c.get("hex")]
        color_clause = f"Brand colors: {', '.join(colors[:4])}." if colors else ""

        if method_name == "retrieval_prompt":
            return f"For {brand_name}. {color_clause} {user_prompt}".strip()

        if method_name == "adapter_only":
            return f"For {brand_name}. Use strong product and identity adherence. {color_clause} {user_prompt}".strip()

        # graph_guided and other research variants
        return (
            f"For {brand_name}. Respect graph constraints for layout, palette, and identity. "
            f"{color_clause} {user_prompt}"
        ).strip()

    def _build_manifest_payload(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create locked manifest payload used for parity checks across runs."""
        return {
            "experiment_id": request["experiment_id"],
            "brand_id": request.get("brand_id"),
            "prompt": request.get("prompt", ""),
            "seeds": request.get("seeds") or [11, 22, 33],
            "locked_config": {
                "aspect_ratio": request.get("aspect_ratio", "1:1"),
                "num_inference_steps": request.get("num_inference_steps", 30),
                "guidance_scale": request.get("guidance_scale", 7.5),
                "use_comfyui": bool(request.get("use_comfyui", False)),
                "use_proxy_color": bool(request.get("use_proxy_color", True)),
            },
        }

    def _build_condition(self, brand_context: Dict[str, Any], request: Dict[str, Any], method_name: str) -> BrandCondition:
        """Create BrandCondition based on method and toggles."""
        toggles = request.get("module_toggles") or {}

        brand_colors = [c.get("hex") for c in brand_context.get("colors", []) if c.get("hex")]

        condition = BrandCondition(
            primary_colors=brand_colors if method_name != "prompt_only" else [],
            style_keywords=[],
            negative_keywords=[],
            layout="centered",
            text_density="moderate",
            text_position="bottom",
            aspect_ratio=request.get("aspect_ratio", "1:1"),
            style_strength=0.8,
        )

        if method_name in {"adapter_only", "graph_guided"}:
            selected_products = brand_context.get("selected_products", [])
            if selected_products:
                condition.product_image_url = selected_products[0].get("image_url")
                condition.product_strength = 0.65

            if request.get("character_reference_url"):
                condition.face_image_url = request.get("character_reference_url")
                condition.face_strength = 0.7

        if toggles.get("dynamic_cfg") is False:
            condition.style_strength = 0.6

        return condition


_runner_singleton: Optional[ExperimentRunner] = None


def get_experiment_runner() -> ExperimentRunner:
    """Get singleton experiment runner instance."""
    global _runner_singleton
    if _runner_singleton is None:
        _runner_singleton = ExperimentRunner()
    return _runner_singleton
