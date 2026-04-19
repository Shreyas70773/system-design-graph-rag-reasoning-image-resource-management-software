# PIPELINE A — Asset Ingestion

**Version:** A/1.0.0  
**Purpose:** Turn a 2D brand reference image into a decomposed, inspectable, user-approved cluster of graph nodes ready for 3D scene assembly.  
**Runtime:** Subprocess worker, GPU-bound, ~3–5 min per asset on 12 GB VRAM.

---

## 1. Inputs and outputs

**Input:**
- `asset_type`: `product | logo | character_ref | texture | environment_ref`
- `source_image`: URL or base64 of the 2D reference
- `brand_id`: UUID
- `optional_hints`: `{ "label_region_hint": "...", "material_class_hint": "matte|glass|metal", ... }`

**Output (on success):**
- One approved `Asset` node with its full decomposition cluster in Neo4j
- `ingestion_status = approved`
- A `DecompositionRun` node recording provenance

**Output (on user rejection):**
- `Asset` node with `ingestion_status = rejected`
- `DecompositionRun` with `user_approved = false` and captured reason

## 2. State machine

```
        ┌──────────┐       ┌───────────────┐       ┌──────────────────┐       ┌──────────┐
submit→ │ pending  │──────>│ decomposing   │──────>│ awaiting_approval│──────>│ approved │
        └──────────┘       └──────┬────────┘       └────────┬─────────┘       └──────────┘
                                  │                         │
                                  │ error                   │ user rejects
                                  ▼                         ▼
                            ┌──────────┐              ┌──────────┐
                            │  failed  │              │ rejected │
                            └──────────┘              └──────────┘
```

State transitions are written as Neo4j updates on the `Asset` node. Every transition emits a `PipelineAEvent` for observability.

## 3. The seven steps

Each step has clear inputs, outputs, VRAM cost, and a kill condition. Steps run **sequentially** with **full unload between** steps. No concurrent model loading.

### Step 1 — Intake and validation (CPU only)
- Download the image if URL
- Check min resolution (1024×1024 for products, 512×512 for textures)
- Compute SHA-256; dedupe against existing assets in the brand
- Upload original to object storage, get a canonical URL
- Write `Asset` with `ingestion_status = decomposing`
- **VRAM:** 0 GB. **Time:** < 5 s.

### Step 2 — VLM description (Qwen2.5-VL-7B AWQ)
- Prompt template: `DESCRIBE_ASSET_V2` (see `backend/app/ingestion/prompts/describe.txt`)
- Output: structured JSON with `{ description, material_class, estimated_parts, palette_hex }`
- Write to `Asset.vlm_description` + `Asset.clip_embedding` (CLIP encoder runs alongside)
- **VRAM:** ~6 GB. **Time:** ~15 s.

### Step 3 — Semantic segmentation (GroundingDINO + SAM 2.1)
- Use VLM-output `estimated_parts` as text prompts to GroundingDINO
- For each detected region, run SAM 2.1 to produce a clean mask
- Write one `SemanticPart` per mask with `part_type` classified from name
- **VRAM:** ~4 GB. **Time:** ~10 s per part, capped at 6 parts.

### Step 4 — Delighting (IntrinsicAnything)
- Input: full image + mask of primary body part
- Output: albedo texture + estimated directional light
- Write `LightProbe` with `estimated_direction`, `estimated_color_temp_k`
- Write a preliminary `Material` with the albedo
- **VRAM:** ~6 GB. **Time:** ~20 s.

### Step 5 — 3D mesh generation (TRELLIS)
- Input: delighted albedo (for texture fidelity) + original (for geometry cues)
- Output: GLB with textured mesh
- Upload GLB. Extract: vertex count, bbox, PBR textures.
- Write `Mesh3D` at `lod_level = 2` (standard)
- Update the Step-4 `Material` with full PBR maps
- **VRAM:** ~10 GB. **Time:** ~90 s. **This is the peak stage.**

### Step 6 — Validation (CLIP re-render similarity)
- Render the mesh from 4 angles using Blender BPY + HDRI from step 4
- Compute CLIP similarity between each render and the original reference
- If mean similarity < 0.75, mark `DecompositionRun.confidence_overall = low` and flag for user review
- **VRAM:** ~2 GB (Blender Eevee) + 2 GB (CLIP). **Time:** ~20 s.

### Step 7 — User approval checkpoint
- Write `Asset.ingestion_status = awaiting_approval`
- Emit a frontend notification
- Block until user approves, rejects, or requests part regeneration
- On part regeneration: rerun Steps 3–5 scoped to that part
- On approval: `ingestion_status = approved`; write `approved_at` + `approved_by_user_id`

## 4. Per-part regeneration

Two strategies; primary fails over to fallback.

### Strategy A (primary): crop-and-realign
1. Crop the original reference image to the part's bounding box (from SAM mask, padded 10 %)
2. Run TRELLIS on the cropped image
3. Align the new sub-mesh to the original mesh's UV region
4. Replace only the affected UV region's textures

**Failure mode:** UV seams visible at part boundaries.

### Strategy B (fallback): whole-object regen with part emphasis
1. Re-run Steps 3–5 with a modified VLM prompt emphasising the requested part
2. Replace the entire `Mesh3D` and related `Material` nodes
3. Preserve `SemanticPart` names but regenerate masks

**Used when:** Strategy A visual seam check fails (CLIP similarity on part boundary < 0.85).

**Risk mitigation reference:** see `RISK_REGISTER.md` item R-2.

## 5. VRAM budget for one ingestion run

Peak simultaneous: **10.0 GB** (Step 5 TRELLIS alone). No step concurrency. Confirmed by `backend/scripts/vram_profile_v2.py`.

| Step | Peak GB | Notes |
|---|---|---|
| 1 | 0 | CPU |
| 2 | 6.2 | Qwen2.5-VL-7B AWQ + CLIP |
| 3 | 4.0 | GroundingDINO + SAM 2.1 Large |
| 4 | 6.0 | IntrinsicAnything |
| 5 | 10.0 | TRELLIS — peak |
| 6 | 4.0 | Blender + CLIP |
| 7 | 0 | Awaiting user |

Hard budget: 11.5 GB. TRELLIS fits with 1.5 GB headroom for allocator spikes.

## 6. Error handling

| Failure | Response |
|---|---|
| Step 2 VLM JSON parse error | Retry once with stricter system prompt; on second fail → `failed` |
| Step 3 no parts detected | Treat entire asset as single `SemanticPart` named `"whole"` |
| Step 5 TRELLIS OOM | Offload anything loaded, retry with `lod_level=1` (coarser mesh) |
| Step 6 validation fail (low CLIP sim) | Proceed to approval but flag UI warning |
| User times out (no approval in 7 days) | Mark `ingestion_status = rejected`, release storage |

## 7. Prompts (locked)

Stored at `backend/app/ingestion/prompts/*.txt`. Each prompt file has a version header. Prompt changes bump `pipeline_version` and are recorded in `DecompositionRun.pipeline_version`.

- `describe.txt` → Step 2 structured description
- `segment_parts.txt` → Step 3 GroundingDINO text prompts derived from VLM output
- `part_regen.txt` → Step 7 Strategy A/B selection prompt

## 8. Acceptance tests

- `tests/ingestion/test_end_to_end.py` — submit a bottle image, assert approved state in ≤ 5 min
- `tests/ingestion/test_per_part_regen.py` — regenerate only the cap, assert other parts unchanged
- `tests/ingestion/test_vram_profile.py` — instrument each step, assert peaks match §5 table within ±10 %
- `tests/ingestion/test_clip_validation.py` — seeded bad input should flag low-confidence but not crash
