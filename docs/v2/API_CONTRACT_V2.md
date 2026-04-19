# API_CONTRACT_V2

**Version:** 2.0.0  
**Mount prefix:** `/api/v2/*`  
**Status:** Locked for Phase 1–2 execution. Changes require PR against this file first.

All request and response bodies correspond to Pydantic models in `backend/app/schema_v2.py`. This doc is the human-readable surface; the Pydantic models are the machine-readable truth.

---

## 1. Conventions

- All endpoints return JSON unless specified
- Errors follow `{"error": {"code": "...", "message": "...", "details": {...}}}` with appropriate 4xx/5xx status
- Long-running operations return `202 Accepted` with a `job_id` and provide progress via SSE on `GET /api/v2/jobs/{job_id}/stream`
- All IDs are UUID v4 strings
- Datetimes are ISO 8601 with timezone

## 2. Health & system

### `GET /api/v2/health`
Returns
```json
{ "status": "ok", "schema_version": "2.0.0", "model_stack_version": "2.0.0", "gpu": { "name": "RTX 5070 Ti Ultra", "vram_total_mb": 12288, "vram_free_mb": 11200 } }
```

### `GET /api/v2/schema/validate`
Runs `validate_graph_schema.py` style checks at request time. Admin-only post-MVP; open in MVP.

## 3. Asset ingestion (Pipeline A)

### `POST /api/v2/assets/ingest`
Submit an asset for decomposition.

Request:
```json
{
  "brand_id": "uuid",
  "asset_type": "product|logo|character_ref|texture|environment_ref",
  "source_image_url": "https://... or data:image/...",
  "optional_hints": {
    "label_region_hint": "front-center",
    "material_class_hint": "matte"
  }
}
```

Response `202 Accepted`:
```json
{ "job_id": "uuid", "asset_id": "uuid", "status": "decomposing" }
```

### `GET /api/v2/assets/{asset_id}`
Full decomposed view.

Response:
```json
{
  "asset": { /* Asset fields */ },
  "geometry": [ { /* Mesh3D fields */ } ],
  "materials": [ { /* Material fields */ } ],
  "parts": [ { /* SemanticPart fields */ } ],
  "light_probe": { /* LightProbe fields */ },
  "canonical_pose": { /* CanonicalPose */ },
  "decomposition_runs": [ { /* DecompositionRun */ } ]
}
```

### `GET /api/v2/assets/{asset_id}/graph`
Graph-view payload for the frontend inspector.

Response:
```json
{
  "nodes": [ { "id": "...", "label": "Asset", "props": { ... } } ],
  "edges": [ { "from": "...", "to": "...", "type": "HAS_GEOMETRY", "props": { ... } } ]
}
```

### `POST /api/v2/assets/{asset_id}/approve`
User approval checkpoint.

Request:
```json
{
  "approve": true,
  "part_overrides": [
    { "part_id": "uuid", "accepted": true },
    { "part_id": "uuid", "accepted": false, "regen_hint": "make the label glossier" }
  ],
  "material_tweaks": [
    { "material_id": "uuid", "albedo_hex": "#1a2b4c", "roughness": 0.4 }
  ]
}
```

Response:
```json
{ "status": "approved", "asset_id": "uuid", "regen_queued": ["part_id_1"] }
```

### `POST /api/v2/assets/{asset_id}/parts/{part_id}/regenerate`
Per-part regeneration (Strategy A primary, B fallback).

Request:
```json
{ "hint": "optional text hint", "force_strategy": "A|B|auto" }
```

Response: `202 Accepted` with `{ "job_id": "uuid" }`.

### `POST /api/v2/assets/{asset_id}/parts/{part_id}/adjust_mask`
Manual mask refinement via client-supplied brush strokes.

Request:
```json
{ "brush_strokes": [ { "x": [..], "y": [..], "mode": "add|remove" } ] }
```

## 4. Scene and rendering (Pipeline B)

### `POST /api/v2/scenes`
Create a scene from intent.

Request:
```json
{
  "brand_id": "uuid",
  "intent_text": "summer promo, product on beach, golden hour",
  "deployment_context": "digital|print|ooh",
  "camera_requests": [
    { "shot_type": "hero", "aspect_ratio": "1:1" },
    { "shot_type": "detail", "aspect_ratio": "16:9" }
  ]
}
```

Response `202 Accepted`:
```json
{ "job_id": "uuid", "scene_id": "uuid" }
```

### `GET /api/v2/scenes/{scene_id}`
Full scene state (everything needed to render in the frontend 3D canvas).

Response:
```json
{
  "scene": { /* Scene fields */ },
  "placements": [ { ... } ],
  "cameras": [ { ... } ],
  "lights": [ { ... } ],
  "terrain": null | { ... },
  "text_layers": [ { ... } ],
  "renders": [ { "id": "...", "camera_id": "...", "image_url": "...", "status": "pending|rendering|completed|failed" } ]
}
```

### `POST /api/v2/scenes/{scene_id}/render`
Request renders for one or more cameras.

Request:
```json
{ "camera_ids": ["uuid1", "uuid2"], "quality": "previz|refined" }
```

Response: `202 Accepted`.

### `GET /api/v2/renders/{render_id}`
Response:
```json
{
  "render": { /* Render fields */ },
  "object_id_pass_url": "https://...",
  "depth_pass_url": "https://...",
  "vram_peak_mb": 11050
}
```

### `POST /api/v2/renders/{render_id}/pick`
Click-to-select on a 2D render.

Request:
```json
{ "x": 420, "y": 380 }
```

Response:
```json
{ "placement_id": "uuid", "asset_id": "uuid", "object_name": "Bottle (hero)" }
```

### `POST /api/v2/renders/{render_id}/mask`
Circle-or-brush masking via SAM 2.1 server-side.

Request:
```json
{ "points": [ {"x": 300, "y": 200, "label": 1} ], "box": null }
```

Response:
```json
{ "mask_png_url": "https://...", "covered_placement_ids": ["uuid"] }
```

## 5. Interactions (Pipeline C)

### `POST /api/v2/interactions`
Structured edit. See `StructuredEditCommand` in `PIPELINE_C_INTERACTION_LEARNING.md §2`.

Request:
```json
{
  "scene_id": "uuid",
  "session_id": "uuid",
  "command": {
    "action": "move",
    "target_kind": "placement",
    "target_id": "uuid",
    "params": { "position": [1.2, 0.0, 0.5] },
    "rerender_cameras": ["camera_uuid_1"]
  }
}
```

Response:
```json
{ "interaction_id": "uuid", "rerender_job_ids": ["uuid"], "updated_fields": ["position"] }
```

### `POST /api/v2/interactions/nl`
Natural-language edit path.

Request:
```json
{
  "scene_id": "uuid",
  "session_id": "uuid",
  "raw_text": "make this bottle a bit bigger and warmer",
  "mask_png_url": "https://... (optional)",
  "pixel_coords": [450, 320]
}
```

Response (success):
```json
{
  "interaction_id": "uuid",
  "nl_command_id": "uuid",
  "resolved_command": { /* StructuredEditCommand */ },
  "confidence": 0.89,
  "applied": true,
  "rerender_job_ids": ["uuid"]
}
```

Response (low confidence):
```json
{
  "nl_command_id": "uuid",
  "applied": false,
  "confidence": 0.54,
  "clarification_needed": true,
  "suggested_commands": [
    { "human_text": "Make the bottle 20% bigger", "command": { ... } },
    { "human_text": "Warm the bottle's color temperature", "command": { ... } }
  ]
}
```

### `GET /api/v2/interactions?scene_id=...`
Audit trail for a scene.

## 6. Brands and learned preferences

### `GET /api/v2/brands/{brand_id}/preferences`
Learned preferences panel.

Response:
```json
{
  "brand_id": "uuid",
  "active_signals": [
    {
      "id": "uuid",
      "subject_kind": "composition.product_y_bias",
      "direction": 0.08,
      "effective_weight": 0.32,
      "half_life_days": 30,
      "created_at": "2026-04-10T12:00:00Z",
      "source_interactions": [ { "id": "uuid", "summary": "moved bottle up on Oct 5" } ],
      "affected_stages": ["B-Stage3"]
    }
  ]
}
```

### `DELETE /api/v2/brands/{brand_id}/preferences/{signal_id}`
Remove a learned preference (US-L3).

## 7. Jobs

### `GET /api/v2/jobs/{job_id}`
Response:
```json
{
  "job_id": "uuid",
  "status": "queued|running|completed|failed",
  "pipeline": "A|B|C",
  "progress_pct": 65,
  "current_step": "mesh",
  "result_url": null
}
```

### `GET /api/v2/jobs/{job_id}/stream`
Server-sent events with progress updates. Event types:
- `progress` — `{ "pct": number, "step": string }`
- `warning` — `{ "message": string }`
- `completed` — `{ "result_url": string }`
- `failed` — `{ "error": string }`

## 8. Error code catalogue

| Code | HTTP | Meaning |
|---|---|---|
| `E_SCHEMA_VALIDATION` | 400 | Request body failed Pydantic |
| `E_BRAND_NOT_FOUND` | 404 | Brand ID missing or wrong schema version |
| `E_ASSET_NOT_APPROVED` | 409 | Operation requires approved asset |
| `E_VRAM_UNAVAILABLE` | 503 | Queue full / GPU busy |
| `E_VLM_LOW_CONFIDENCE` | 422 | NL edit below threshold |
| `E_SCHEMA_DRIFT` | 500 | validate_graph_schema detected drift |
| `E_OOM` | 500 | Refinement OOM; fallback triggered |
| `E_GROQ_PARSE` | 500 | Scene-graph parser returned invalid JSON after retries |

## 9. Versioning the API

- Breaking changes → new path prefix `/api/v3/*`, never a silent change under `/api/v2/*`
- Additive changes (new endpoints, new optional fields) → fine under `/api/v2/*`
- This doc's version header bumps on any change; PR must update it
