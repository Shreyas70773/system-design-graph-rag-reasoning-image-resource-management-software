"""AC-2 + AC-4: multiple cameras produce multiple renders of the same scene."""

from __future__ import annotations


def test_multiple_cameras_share_one_scene(fake_db, brand_in_db, sample_image_url):
    from app.ingestion.orchestrator import IngestionOrchestrator
    from app.interaction.applier import apply
    from app.scene.pipeline import ScenePipeline
    from app.schema_v2 import EditTargetKind, InteractionType, StructuredEditCommand

    ing = IngestionOrchestrator()
    ing_out = ing.run("ingest", {
        "brand_id": brand_in_db,
        "asset_type": "product",
        "source_image_url": sample_image_url,
    })
    apply(
        StructuredEditCommand(
            action=InteractionType.APPROVE_DECOMPOSITION,
            target_kind=EditTargetKind.ASSET,
            target_id=ing_out["asset_id"],
            params={},
        ),
        actor="creative_director", surface="asset_editor",
    )
    pipeline = ScenePipeline()
    scene_out = pipeline.create_and_render({
        "brand_id": brand_in_db,
        "intent_text": "A hero shot of the product on a clean studio backdrop, with the tagline 'Bold.' below.",
        "deployment_context": "digital",
        "camera_requests": [
            {"shot_type": "hero", "aspect_ratio": "1:1"},
            {"shot_type": "detail", "aspect_ratio": "1:1"},
            {"shot_type": "wide", "aspect_ratio": "16:9"},
        ],
    })
    scene_id = scene_out["scene_id"]
    renders = scene_out["renders"]
    assert len(renders) == 3
    # Same scene_id for every render.
    for r in renders:
        assert r["image_url"].endswith(".png")
    # The three renders share one scene in the DB.
    full = fake_db.get_scene_full(scene_id)
    assert len(full["cameras"]) == 3
    assert len(full["renders"]) == 3


def test_rerender_only_requested_camera(fake_db, brand_in_db, sample_image_url):
    from app.ingestion.orchestrator import IngestionOrchestrator
    from app.interaction.applier import apply
    from app.scene.pipeline import ScenePipeline
    from app.schema_v2 import EditTargetKind, InteractionType, StructuredEditCommand

    ing = IngestionOrchestrator()
    ing_out = ing.run("ingest", {
        "brand_id": brand_in_db, "asset_type": "product", "source_image_url": sample_image_url,
    })
    apply(
        StructuredEditCommand(action=InteractionType.APPROVE_DECOMPOSITION,
                              target_kind=EditTargetKind.ASSET,
                              target_id=ing_out["asset_id"], params={}),
        actor="creative_director", surface="asset_editor",
    )
    pipeline = ScenePipeline()
    scene_out = pipeline.create_and_render({
        "brand_id": brand_in_db,
        "intent_text": "Hero shot for launch",
        "deployment_context": "digital",
        "camera_requests": [
            {"shot_type": "hero", "aspect_ratio": "1:1"},
            {"shot_type": "detail", "aspect_ratio": "1:1"},
        ],
    })
    scene_id = scene_out["scene_id"]
    first_cam = scene_out["renders"][0]["camera_id"]
    # Re-render ONLY the first camera.
    second_pass = pipeline.render_scene_cameras(scene_id, only_camera_ids=[first_cam])
    assert len(second_pass) == 1
    assert second_pass[0]["camera_id"] == first_cam
