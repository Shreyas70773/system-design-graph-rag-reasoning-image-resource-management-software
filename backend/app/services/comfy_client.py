"""
ComfyUI client service.
Provides minimal job submission and polling utilities for research workflows.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
import asyncio
import httpx
import os
import subprocess

from app.config import get_settings


class ComfyClient:
    """HTTP client wrapper for ComfyUI APIs."""

    def __init__(self, base_url: Optional[str] = None, timeout_seconds: float = 30.0):
        settings = get_settings()
        self.base_url = (base_url or settings.comfyui_url or "http://127.0.0.1:8001").rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.auto_start_enabled = bool(settings.comfyui_auto_start)
        self.auto_start_timeout_seconds = max(5, int(settings.comfyui_auto_start_timeout_seconds))
        self._configured_executable = (settings.comfyui_desktop_executable or "").strip()
        self._auto_start_attempted = False
        self._candidate_urls = self._dedupe_urls([
            self.base_url,
            "http://127.0.0.1:8001",
            "http://127.0.0.1:8188",
            "http://localhost:8001",
            "http://localhost:8188",
        ])

    @staticmethod
    def _dedupe_urls(urls: Sequence[str]) -> List[str]:
        seen = set()
        unique_urls: List[str] = []
        for raw_url in urls:
            candidate = str(raw_url or "").strip().rstrip("/")
            if not candidate:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            unique_urls.append(candidate)
        return unique_urls

    def _get_executable_candidates(self) -> List[str]:
        candidates = []
        if self._configured_executable:
            candidates.append(self._configured_executable)

        env_override = os.getenv("COMFYUI_DESKTOP_EXE", "").strip()
        if env_override:
            candidates.append(env_override)

        local_app_data = os.getenv("LOCALAPPDATA", "").strip()
        program_files = os.getenv("ProgramFiles", "").strip()
        program_files_x86 = os.getenv("ProgramFiles(x86)", "").strip()

        if local_app_data:
            candidates.append(os.path.join(local_app_data, "Programs", "ComfyUI", "ComfyUI.exe"))
        if program_files:
            candidates.append(os.path.join(program_files, "ComfyUI", "ComfyUI.exe"))
        if program_files_x86:
            candidates.append(os.path.join(program_files_x86, "ComfyUI", "ComfyUI.exe"))

        return self._dedupe_urls(candidates)

    def _try_auto_start(self) -> Dict[str, Any]:
        if os.name != "nt":
            return {"attempted": False, "started": False, "reason": "auto-start currently supported only on Windows"}

        errors: List[str] = []
        for executable_path in self._get_executable_candidates():
            if not os.path.isfile(executable_path):
                continue

            try:
                process = subprocess.Popen(
                    [executable_path],
                    cwd=os.path.dirname(executable_path),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return {
                    "attempted": True,
                    "started": True,
                    "path": executable_path,
                    "pid": process.pid,
                }
            except Exception as exc:
                errors.append(f"{executable_path}: {exc}")

        if errors:
            return {
                "attempted": True,
                "started": False,
                "reason": "; ".join(errors),
            }

        return {
            "attempted": True,
            "started": False,
            "reason": "No ComfyUI executable was found in configured or default locations.",
        }

    async def _probe_candidates(self) -> Dict[str, Any]:
        ordered_urls = self._dedupe_urls([self.base_url] + self._candidate_urls)
        attempted: Dict[str, str] = {}

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for url in ordered_urls:
                try:
                    response = await client.get(f"{url}/system_stats")
                    if response.status_code == 200:
                        self.base_url = url
                        self._candidate_urls = self._dedupe_urls([url] + self._candidate_urls)
                        return {
                            "ok": True,
                            "base_url": url,
                            "details": response.json(),
                            "attempted_urls": ordered_urls,
                        }

                    attempted[url] = f"unexpected status {response.status_code}"
                except Exception as exc:
                    attempted[url] = str(exc)

        return {
            "ok": False,
            "attempted_urls": ordered_urls,
            "errors": attempted,
        }

    async def _resolve_base_url(self, auto_start: bool = False) -> Dict[str, Any]:
        probe_result = await self._probe_candidates()
        if probe_result.get("ok"):
            return probe_result

        auto_start_result: Dict[str, Any] = {
            "attempted": False,
            "started": False,
        }

        should_auto_start = auto_start and self.auto_start_enabled and not self._auto_start_attempted
        if should_auto_start:
            self._auto_start_attempted = True
            auto_start_result = self._try_auto_start()

            if auto_start_result.get("started"):
                max_polls = max(3, int(self.auto_start_timeout_seconds))
                for _ in range(max_polls):
                    await asyncio.sleep(1.0)
                    retry_result = await self._probe_candidates()
                    if retry_result.get("ok"):
                        retry_result["auto_start"] = auto_start_result
                        return retry_result

        attempted_urls = probe_result.get("attempted_urls", self._candidate_urls)
        errors = probe_result.get("errors", {})
        error_fragments = [f"{url} -> {errors.get(url, 'unreachable')}" for url in attempted_urls]
        error_message = "ComfyUI is unreachable. Tried: " + "; ".join(error_fragments)

        if auto_start and self.auto_start_enabled and auto_start_result.get("attempted"):
            if auto_start_result.get("started"):
                error_message += (
                    f" | Auto-start launched {auto_start_result.get('path')} but no API became available "
                    f"within {self.auto_start_timeout_seconds}s."
                )
            else:
                error_message += f" | Auto-start failed: {auto_start_result.get('reason', 'unknown reason')}"

        return {
            "ok": False,
            "error": error_message,
            "attempted_urls": attempted_urls,
            "errors": errors,
            "auto_start": auto_start_result,
        }

    async def health(self, auto_start: bool = False) -> Dict[str, Any]:
        """Check whether ComfyUI API is reachable."""
        resolved = await self._resolve_base_url(auto_start=auto_start)
        if not resolved.get("ok"):
            return {
                "ok": False,
                "error": resolved.get("error", "ComfyUI is unreachable."),
                "attempted_urls": resolved.get("attempted_urls", []),
                "errors": resolved.get("errors", {}),
            }

        return {
            "ok": True,
            "base_url": resolved.get("base_url", self.base_url),
            "attempted_urls": resolved.get("attempted_urls", []),
            "details": resolved.get("details", {}),
            "auto_start": resolved.get("auto_start"),
        }

    async def list_models(self, model_type: str = "checkpoints", auto_start: bool = False) -> Dict[str, Any]:
        """List model names from ComfyUI /models/<type> endpoint."""
        health = await self.health(auto_start=auto_start)
        if not health.get("ok"):
            return {
                "ok": False,
                "error": health.get("error", "ComfyUI is unreachable."),
                "attempted_urls": health.get("attempted_urls", []),
            }

        model_type = str(model_type or "checkpoints").strip().strip("/")
        if not model_type:
            model_type = "checkpoints"

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url}/models/{model_type}")
            if response.status_code == 404:
                return {
                    "ok": False,
                    "error": f"ComfyUI endpoint /models/{model_type} is unavailable on {self.base_url}.",
                    "base_url": self.base_url,
                }

            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list):
                model_names = payload
            elif isinstance(payload, dict):
                nested_models = payload.get("models")
                if isinstance(nested_models, list):
                    model_names = nested_models
                else:
                    model_names = list(payload.keys())
            else:
                model_names = []

            return {
                "ok": True,
                "base_url": self.base_url,
                "model_type": model_type,
                "models": [str(name) for name in model_names if name],
            }

    async def submit_workflow(self, workflow: Dict[str, Any], client_id: str = "research-runner") -> Dict[str, Any]:
        """Submit a workflow JSON to ComfyUI."""
        resolved = await self._resolve_base_url(auto_start=False)
        if not resolved.get("ok"):
            raise RuntimeError(resolved.get("error", "ComfyUI is unreachable."))

        payload = {
            "prompt": workflow,
            "client_id": client_id,
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/prompt", json=payload)
            response.raise_for_status()
            return response.json()

    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """Fetch history object for a submitted prompt."""
        resolved = await self._resolve_base_url(auto_start=False)
        if not resolved.get("ok"):
            raise RuntimeError(resolved.get("error", "ComfyUI is unreachable."))

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url}/history/{prompt_id}")
            response.raise_for_status()
            return response.json()

    async def get_queue(self) -> Dict[str, Any]:
        """Fetch queue snapshot."""
        resolved = await self._resolve_base_url(auto_start=False)
        if not resolved.get("ok"):
            raise RuntimeError(resolved.get("error", "ComfyUI is unreachable."))

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url}/queue")
            response.raise_for_status()
            return response.json()

    async def wait_for_completion(
        self,
        prompt_id: str,
        max_polls: int = 120,
        poll_interval_seconds: float = 1.5,
    ) -> Dict[str, Any]:
        """
        Poll history until completion.

        Returns a dict with:
        - completed: bool
        - history: dict
        - error: optional str
        """
        for _ in range(max_polls):
            history = await self.get_history(prompt_id)
            if prompt_id in history:
                return {"completed": True, "history": history[prompt_id]}

            await asyncio.sleep(poll_interval_seconds)

        return {
            "completed": False,
            "error": "Timed out waiting for ComfyUI prompt completion",
        }

    def extract_image_urls(self, history_payload: Dict[str, Any]) -> List[str]:
        """Extract generated image URLs from ComfyUI history payload."""
        outputs = history_payload.get("outputs", {})
        urls: List[str] = []

        for node_output in outputs.values():
            images = node_output.get("images", [])
            for img in images:
                filename = img.get("filename")
                subfolder = img.get("subfolder", "")
                image_type = img.get("type", "output")
                if not filename:
                    continue
                urls.append(
                    f"{self.base_url}/view?filename={filename}&subfolder={subfolder}&type={image_type}"
                )

        return urls
