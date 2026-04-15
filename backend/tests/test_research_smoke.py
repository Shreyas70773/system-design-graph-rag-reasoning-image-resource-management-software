import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.routers import research as research_router
from app.services.experiment_runner import ManifestConflictError


class _DummyRunner:
    async def run_controlled_generation(self, payload):
        return {
            "run_id": "run_test_001",
            "experiment_id": payload.get("experiment_id") or "exp_test_001",
            "brand_id": payload["brand_id"],
            "method_name": payload.get("method_name", "graph_guided"),
            "status": "completed",
            "summary": {
                "candidate_count": len(payload.get("seeds", [11, 22, 33])),
                "success_rate": 1.0,
                "brand_score_mean": 0.71,
                "color_alignment_mean": 0.68,
                "delta_e_ciede2000_mean": 4.2,
                "delta_e_ciede2000_pass_rate_mean": 0.33,
            },
            "candidates": [],
        }

    async def run_ablation(self, payload):
        return {
            "experiment_id": payload.get("experiment_id") or "exp_test_001",
            "total_runs": 2,
            "runs": [
                {"run_id": "run_base", "method_name": "graph_guided"},
                {"run_id": "run_abl_1", "method_name": "graph_guided:fixed_cfg"},
            ],
        }

    async def compare_experiment(self, experiment_id):
        return {
            "experiment_id": experiment_id,
            "run_count": 2,
            "comparison": {
                "run_count": 2,
                "runs": [
                    {"run_id": "run_base", "method_name": "graph_guided", "summary": {"brand_score_mean": 0.71}},
                    {"run_id": "run_prompt", "method_name": "prompt_only", "summary": {"brand_score_mean": 0.52}},
                ],
            },
        }

    async def run_deltae_refinement_job(self, run_id):
        return {
            "run_id": run_id,
            "snapshot_id": "metric_deltae_001",
            "candidate_count": 3,
            "summary": {
                "delta_e_ciede2000_mean": 3.9,
                "delta_e_ciede2000_pass_rate_mean": 0.4,
            },
        }


class _ManifestConflictRunner:
    async def run_controlled_generation(self, payload):
        raise ManifestConflictError(
            "Experiment manifest conflict detected.",
            {
                "experiment_id": payload.get("experiment_id") or "exp_test_001",
                "requested_parity_hash": "hash_requested",
                "stored_parity_hash": "hash_stored",
                "differences": [
                    {
                        "field": "seeds",
                        "stored": [11, 22, 33],
                        "requested": [44, 55, 66],
                    }
                ],
            },
        )


class ResearchEndpointSmokeTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_generate_controlled_endpoint(self):
        payload = {
            "brand_id": "brand_test_001",
            "prompt": "Hero launch visual",
            "method_name": "graph_guided",
            "seeds": [11, 22],
        }

        with patch.object(research_router, "get_experiment_runner", return_value=_DummyRunner()):
            response = self.client.post("/api/research/generate-controlled", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "completed")
        self.assertIn("summary", body)

    def test_stats_endpoint(self):
        rows = [
            {"run_id": "run_1", "method_name": "prompt_only", "metrics": {"seed": 11, "brand_score": 0.40}},
            {"run_id": "run_1", "method_name": "prompt_only", "metrics": {"seed": 22, "brand_score": 0.45}},
            {"run_id": "run_2", "method_name": "graph_guided", "metrics": {"seed": 11, "brand_score": 0.62}},
            {"run_id": "run_2", "method_name": "graph_guided", "metrics": {"seed": 22, "brand_score": 0.66}},
        ]

        with patch.object(research_router.neo4j_client, "get_candidate_metrics_for_experiment", return_value=rows):
            response = self.client.get(
                "/api/research/stats/exp_test_001",
                params={
                    "metric": "brand_score",
                    "baseline_method": "prompt_only",
                    "bootstrap_resamples": 300,
                    "ci_alpha": 0.1,
                    "random_seed": 7,
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("result", body)
        pairwise = body["result"].get("pairwise", [])
        self.assertGreaterEqual(len(pairwise), 1)

        first = pairwise[0]
        self.assertIn("delta_mean_ci", first)
        self.assertIn("effect_size", first)
        self.assertIn("p_value_adjusted_holm", first)
        self.assertEqual(body["result"]["analysis_config"]["bootstrap_resamples"], 300)
        self.assertAlmostEqual(body["result"]["analysis_config"]["ci_alpha"], 0.1)

    def test_deltae_job_endpoint(self):
        with patch.object(research_router, "get_experiment_runner", return_value=_DummyRunner()):
            response = self.client.post("/api/research/jobs/deltae/run_test_001")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["run_id"], "run_test_001")
        self.assertIn("summary", body)

    def test_export_run_json_endpoint(self):
        run = {
            "id": "run_test_001",
            "experiment_id": "exp_test_001",
            "brand_id": "brand_test_001",
            "method_name": "graph_guided",
            "candidates": [
                {
                    "id": "cand_001",
                    "seed": 11,
                    "status": "completed",
                    "image_url": "https://example.com/image.png",
                    "model_used": "sdxl",
                    "provider": "fallback",
                    "latency_ms": 1200,
                }
            ],
        }
        metrics = [
            {
                "level": "candidate",
                "candidate_id": "cand_001",
                "metrics": {
                    "brand_score": 0.72,
                    "color_alignment_score": 0.69,
                    "delta_e_ciede2000_mean": 4.1,
                },
            }
        ]

        with patch.object(research_router.neo4j_client, "get_experiment_run", return_value=run), patch.object(
            research_router.neo4j_client, "get_metrics_for_run", return_value=metrics
        ):
            response = self.client.get("/api/research/export/run/run_test_001", params={"format": "json"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("rows", body)
        self.assertEqual(len(body["rows"]), 1)

    def test_export_run_csv_endpoint(self):
        run = {
            "id": "run_test_001",
            "experiment_id": "exp_test_001",
            "brand_id": "brand_test_001",
            "method_name": "graph_guided",
            "candidates": [
                {
                    "id": "cand_001",
                    "seed": 11,
                    "status": "completed",
                    "image_url": "https://example.com/image.png",
                    "model_used": "sdxl",
                    "provider": "fallback",
                    "latency_ms": 1200,
                }
            ],
        }
        metrics = [
            {
                "level": "candidate",
                "candidate_id": "cand_001",
                "metrics": {
                    "brand_score": 0.72,
                    "color_alignment_score": 0.69,
                    "delta_e_ciede2000_mean": 4.1,
                },
            }
        ]

        with patch.object(research_router.neo4j_client, "get_experiment_run", return_value=run), patch.object(
            research_router.neo4j_client, "get_metrics_for_run", return_value=metrics
        ):
            response = self.client.get("/api/research/export/run/run_test_001", params={"format": "csv"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers.get("content-type", ""))
        csv_text = response.content.decode("utf-8")
        self.assertIn("run_id,experiment_id,brand_id,method_name", csv_text)
        self.assertIn("run_test_001", csv_text)

    def test_manifest_validation_endpoint(self):
        validation_payload = {
            "exists": True,
            "matches": False,
            "experiment_id": "exp_test_001",
            "requested_parity_hash": "hash_requested",
            "stored_parity_hash": "hash_stored",
            "differences": [
                {
                    "field": "locked_config.guidance_scale",
                    "stored": 7.5,
                    "requested": 9.0,
                }
            ],
        }

        with patch.object(research_router.neo4j_client, "validate_experiment_manifest", return_value=validation_payload):
            response = self.client.post(
                "/api/research/manifest/validate",
                json={
                    "experiment_id": "exp_test_001",
                    "brand_id": "brand_test_001",
                    "prompt": "Hero launch visual",
                    "seeds": [11, 22, 33],
                    "locked_config": {"guidance_scale": 9.0},
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["matches"])
        self.assertEqual(len(body["differences"]), 1)

    def test_generate_controlled_manifest_conflict(self):
        payload = {
            "brand_id": "brand_test_001",
            "prompt": "Hero launch visual",
            "method_name": "graph_guided",
            "seeds": [44, 55, 66],
            "experiment_id": "exp_test_001",
        }

        with patch.object(research_router, "get_experiment_runner", return_value=_ManifestConflictRunner()):
            response = self.client.post("/api/research/generate-controlled", json=payload)

        self.assertEqual(response.status_code, 409)
        body = response.json()
        self.assertEqual(body["detail"]["error"], "manifest_conflict")
        self.assertIn("differences", body["detail"]["conflict"])


if __name__ == "__main__":
    unittest.main()
