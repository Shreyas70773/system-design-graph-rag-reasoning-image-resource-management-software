import asyncio
import base64
import io
import unittest

from PIL import Image, ImageDraw

from app.services.graph_conditioning import DynamicCFGScheduler, GraphConditioner
from app.services.metric_evaluator import MetricEvaluator


def _make_test_image_bytes(size: int = 192) -> bytes:
    image = Image.new("RGB", (size, size), color=(38, 44, 60))
    draw = ImageDraw.Draw(image)

    # Brighter centered subject region for layout proxy.
    subject_size = int(size * 0.45)
    start = (size - subject_size) // 2
    end = start + subject_size
    draw.rectangle((start, start, end, end), fill=(208, 122, 92))

    # Bottom stripe to create a text-zone contrast signal.
    stripe_top = int(size * 0.72)
    draw.rectangle((0, stripe_top, size, size), fill=(245, 245, 245))

    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class GraphConditionerTests(unittest.TestCase):
    def test_build_packet_contains_conditioning_fields(self):
        conditioner = GraphConditioner()

        brand_context = {
            "colors": [{"hex": "#FF6A4D"}, {"hex": "#1F2937"}],
            "styles": [{"name": "premium"}, {"name": "editorial"}],
            "selected_products": [{"image_url": "https://example.com/product.png"}],
            "tagline": "Elevated product stories for modern brands",
        }
        request = {
            "brand_id": "brand_001",
            "module_toggles": {
                "color_regularizer": True,
                "layout_constraint": True,
                "identity_lock": True,
                "dynamic_cfg": True,
            },
            "character_reference_url": "https://example.com/character.png",
        }

        packet = conditioner.build_packet(brand_context, request, method_name="graph_guided")
        packet_dict = packet.as_dict()

        self.assertEqual(packet_dict["brand_id"], "brand_001")
        self.assertGreater(len(packet_dict["palette_hex"]), 0)
        self.assertGreater(len(packet_dict["palette_vector"]), 0)
        self.assertGreater(packet_dict["confidence"], 0.0)
        self.assertIn("w_color", packet_dict["constraint_weight_map"])


class DynamicCFGSchedulerTests(unittest.TestCase):
    def test_effective_cfg_is_dynamic_when_enabled(self):
        scheduler = DynamicCFGScheduler()
        base_cfg = 7.5

        disabled = scheduler.effective_cfg_for_run(
            base_cfg=base_cfg,
            total_steps=30,
            confidence=0.8,
            dynamic_enabled=False,
            method_name="graph_guided",
        )
        enabled = scheduler.effective_cfg_for_run(
            base_cfg=base_cfg,
            total_steps=30,
            confidence=0.8,
            dynamic_enabled=True,
            method_name="graph_guided",
        )

        self.assertAlmostEqual(disabled, base_cfg)
        self.assertGreaterEqual(enabled, base_cfg)


class MetricEvaluatorProxyTests(unittest.TestCase):
    def setUp(self):
        self.evaluator = MetricEvaluator()
        self.image_bytes = _make_test_image_bytes()
        encoded = base64.b64encode(self.image_bytes).decode("utf-8")
        self.data_uri = f"data:image/png;base64,{encoded}"

    def test_layout_and_text_proxy_scores_exist(self):
        layout_score = self.evaluator.compute_layout_compliance_score(self.image_bytes, expected_layout="centered")
        text_score = self.evaluator.compute_text_legibility_score(self.image_bytes, text_position="bottom")

        self.assertIsNotNone(layout_score)
        self.assertIsNotNone(text_score)
        self.assertGreaterEqual(layout_score, 0.0)
        self.assertLessEqual(layout_score, 1.0)
        self.assertGreaterEqual(text_score, 0.0)
        self.assertLessEqual(text_score, 1.0)

    def test_identity_proxy_score_for_matching_reference(self):
        score = asyncio.run(
            self.evaluator.compute_identity_consistency_score(
                generated_image_bytes=self.image_bytes,
                reference_image_url=self.data_uri,
            )
        )

        self.assertIsNotNone(score)
        self.assertGreaterEqual(score, 0.95)


if __name__ == "__main__":
    unittest.main()
