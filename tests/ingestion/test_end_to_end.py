"""AC-1: 2D → 3D asset ingestion produces Mesh3D + parts + material + lightprobe."""

from __future__ import annotations


def test_ingestion_end_to_end_mock_mode(fake_db, brand_in_db, sample_image_url):
    from app.ingestion.orchestrator import IngestionOrchestrator

    orch = IngestionOrchestrator()
    result = orch.run("test-job-1", {
        "brand_id": brand_in_db,
        "asset_type": "product",
        "source_image_url": sample_image_url,
    })

    assert result["asset_id"]
    assert result["mesh_id"]
    assert result["material_id"]
    assert len(result["part_ids"]) >= 1
    assert result["status"] == "awaiting_approval"

    full = fake_db.get_asset_full(result["asset_id"])
    assert full["asset"]["ingestion_status"] == "awaiting_approval"
    assert full["asset"]["vlm_description"]
    assert full["geometry"], "mesh attached"
    assert full["materials"], "material attached"
    assert full["parts"], "parts attached"
    assert full["light_probe"], "light probe attached"
    assert full["canonical_pose"], "canonical pose attached"
    assert full["decomposition_runs"], "decomposition provenance recorded"


def test_mesh_glb_is_valid_glb_binary(fake_db, brand_in_db, sample_image_url):
    from app.ingestion.orchestrator import IngestionOrchestrator
    from app.rendering.storage import local_path_for_url

    orch = IngestionOrchestrator()
    result = orch.run("test-job-2", {
        "brand_id": brand_in_db,
        "asset_type": "product",
        "source_image_url": sample_image_url,
    })
    full = fake_db.get_asset_full(result["asset_id"])
    mesh_url = full["geometry"][0]["file_url"]
    path = local_path_for_url(mesh_url)
    assert path is not None and path.exists()
    data = path.read_bytes()
    # GLB magic = 0x46546C67 ("glTF")
    assert data[:4] == b"glTF"
    # Version 2
    import struct
    version, = struct.unpack("<I", data[4:8])
    assert version == 2


def test_approval_flips_asset_status(fake_db, brand_in_db, sample_image_url):
    from app.ingestion.orchestrator import IngestionOrchestrator
    from app.interaction.applier import apply
    from app.schema_v2 import EditTargetKind, InteractionType, StructuredEditCommand

    orch = IngestionOrchestrator()
    res = orch.run("test-job-3", {
        "brand_id": brand_in_db,
        "asset_type": "product",
        "source_image_url": sample_image_url,
    })
    apply(
        StructuredEditCommand(
            action=InteractionType.APPROVE_DECOMPOSITION,
            target_kind=EditTargetKind.ASSET,
            target_id=res["asset_id"],
            params={},
        ),
        actor="creative_director",
        surface="asset_editor",
    )
    assert fake_db.get_asset_full(res["asset_id"])["asset"]["ingestion_status"] == "approved"
