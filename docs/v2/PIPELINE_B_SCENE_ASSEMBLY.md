# PIPELINE B — Scene Assembly and Rendering

**Version:** B/1.0.0  
**Purpose:** Turn user intent + graph brand knowledge into a 3D scene, render N camera angles, apply neural refinement, write `Render` nodes back to graph.  
**Runtime:** Subprocess worker, GPU-bound, ~3–5 min for first render of a new scene, ~30 s per additional camera angle.

---

## 1. Inputs and outputs

**Input:**
- `brand_id`: UUID
- `intent_text`: natural-language prompt
- `deployment_context`: `digital | print | ooh`
- `camera_requests` (optional): list of shot types or explicit camera specs

**Output:**
- One `Scene` node
- N `Placement`, `Camera`, `Light`, `Terrain`, `TextLayer` child nodes
- One `Render` per camera, with `image_url`, `object_id_pass_url`, `depth_pass_url`

## 2. Stages

```
   Intent + brand_id
         │
         ▼
 ┌─────────────────┐
 │ 1. Intent parse │  Groq Llama 3.3 → scene_graph_json
 └────────┬────────┘
          ▼
 ┌────────────────────────┐
 │ 2. Graph-RAG retrieval │  Cypher multi-hop + vector search + preference bias
 └──────────┬─────────────┘
            ▼
 ┌──────────────────────────┐
 │ 3. Scene state build     │  Instantiate Scene, Placements, Cameras, Lights
 └──────────┬───────────────┘
            ▼
 ┌──────────────────────────┐
 │ 4. Blender render (BPY)  │  For each camera: RGB + depth + normal + object-ID passes
 └──────────┬───────────────┘
            ▼
 ┌──────────────────────────┐
 │ 5. Neural refinement     │  FLUX.1-schnell + ControlNet Depth + Normal + PuLID + IP-Adapter
 └──────────┬───────────────┘
            ▼
 ┌──────────────────────────┐
 │ 6. 2D text compositing   │  Render TextLayers on top of refined RGB
 └──────────┬───────────────┘
            ▼
 ┌──────────────────────────┐
 │ 7. Color grading         │  LAB-space gamut clip toward brand palette
 └──────────┬───────────────┘
            ▼
 ┌──────────────────────────┐
 │ 8. Write Render nodes    │  Final artefacts + passes to object storage + graph
 └──────────────────────────┘
```

## 3. Stage details

### Stage 1 — Intent parse (LLM)
- Model: Groq Llama 3.3 70B
- System prompt: `SCENE_GRAPH_PARSER_V2` (locked at `backend/app/scene/prompts/parser.txt`)
- Output: scene-graph JSON conforming to the contract in `ARCHITECTURE_V2.md §5`
- Validated by Pydantic `SceneGraphSpec` before proceeding
- **Time:** ~3 s. **VRAM:** 0 (Groq is API).

### Stage 2 — Graph-RAG retrieval
Runs the V2 Cypher query shown below. Also applies preference signals.

```cypher
MATCH (b:Brand {id: $brand_id, schema_version: '2.0'})-[:HAS_COLOR]->(c:Color)
WHERE $deployment_context IN c.usage_context
WITH b, collect(c) AS colors
OPTIONAL MATCH (b)-[:HAS_FONT]->(f:Font)
OPTIONAL MATCH (b)-[:HAS_ASSET]->(a:Asset {ingestion_status: 'approved'})
OPTIONAL MATCH (a)-[:HAS_GEOMETRY]->(m:Mesh3D)
OPTIONAL MATCH (a)-[:HAS_MATERIAL]->(mat:Material)
OPTIONAL MATCH (a)-[:HAS_LIGHT_PROBE]->(lp:LightProbe)
OPTIONAL MATCH (b)-[:LEARNED_PREF]->(ps:PreferenceSignal)
WHERE ps.weight > 0.05
RETURN b, colors, collect(DISTINCT f) AS fonts,
       collect(DISTINCT {asset: a, mesh: m, material: mat, light: lp}) AS assets,
       collect(DISTINCT ps) AS preferences
```

For scene-graph nodes with `asset_query` (not `asset_id`), a second vector-search query runs:

```cypher
CALL db.index.vector.queryNodes('asset_clip_embedding', 5, $query_embedding)
YIELD node, score
MATCH (b:Brand {id: $brand_id})-[:HAS_ASSET]->(node)
WHERE node.ingestion_status = 'approved'
RETURN node, score ORDER BY score DESC LIMIT 1
```

Preference signals are distilled into:
- Position biases: `preference_vector.composition_biases`
- Color biases: tilt the LAB target for grading stage
- Aesthetic biases: dial refinement-pass parameters (e.g. `steps_bonus`, `guidance_shift`)

**Time:** ~1 s Cypher + ~1 s embedding.

### Stage 3 — Scene state build
- Instantiate one Python `SceneState` object (`backend/app/scene/models.py`)
- Resolve `asset_query` entries via vector search
- Convert position hints ("center", "left-third") to 3D coordinates via a fixed grid
- Apply preference signal position biases to final coordinates
- For each camera request: generate `Camera` with computed position + target based on scene bbox
- Write `Scene`, `Placement`, `Camera`, `Light`, `Terrain`, `TextLayer` nodes to graph

**Time:** ~2 s.

### Stage 4 — Blender BPY render
- Launch Blender headless subprocess: `blender --background --python scene/blender_script.py -- <scene_id>`
- The Python script:
  1. Loads GLB meshes from each Placement's referenced Asset
  2. Sets materials from Material nodes (with overrides from Placement.material_override_ids)
  3. Sets lights from Light nodes
  4. Sets terrain heightmap if present
  5. For each Camera: render with **Eevee Next** (faster) or **Cycles** (quality) — configurable; default Eevee
  6. Output passes: RGB, Depth (32-bit), Normal, Object ID (integer per Placement)
- Upload all passes to object storage
- **Time:** ~10–20 s per camera angle (Eevee). **VRAM:** ~4 GB.

### Stage 5 — Neural refinement
For each camera render:
- Model: FLUX.1-schnell NF4 (~10 GB) with ControlNet Depth + ControlNet Normal + PuLID-FLUX (for character placements) + IP-Adapter (for brand asset texture fidelity)
- Conditioning:
  - ControlNet Depth weight: 0.8
  - ControlNet Normal weight: 0.6
  - PuLID face injection (only if scene has a `character_ref` placement): weight 0.7
  - IP-Adapter from primary brand asset: weight 0.5
  - Text prompt: compiled from scene graph + brand aesthetic prefs
- Steps: 4 (schnell). Guidance: 0 (schnell uses distilled guidance).
- Output: refined RGB matching the 3D geometry + brand textures

**Time:** ~8 s per camera on 5070 Ti. **VRAM peak:** ~11.0 GB.

### Stage 6 — 2D text compositing
- Render each `TextLayer` using Pillow
- Respect `position_norm`, `anchor`, `font_id` (load font file from `Font.file_url`)
- Blend with alpha over the refined RGB
- **Time:** < 1 s per camera.

### Stage 7 — Colour grading
- Convert final RGB → LAB
- Compute dominant colours; compare to brand's `Color` palette
- Apply gamut clip: colours outside the brand's approved LAB gamut are pulled toward nearest allowed colour
- Clamp strength: preference-signal-biased (user who rejects aggressive grading gets weaker grading next time)
- **Time:** ~1 s per camera.

### Stage 8 — Write Render nodes
- Upload final composite, object-ID pass, depth pass
- Write one `Render` node per camera
- Emit websocket event to frontend: `render.completed`

## 4. VRAM budget per scene render

| Stage | Peak GB | Notes |
|---|---|---|
| 1 | 0 | Groq API |
| 2 | 0 | Cypher + CLIP embedding on CPU (small model) |
| 3 | 0 | CPU only |
| 4 | ~4 | Blender Eevee subprocess |
| 5 | ~11 | FLUX-NF4 + ControlNets + PuLID |
| 6 | 0 | Pillow |
| 7 | 0 | NumPy |
| 8 | 0 | I/O |

Stages 4 and 5 **never** run concurrently. Blender subprocess exits before FLUX loads.

## 5. Caching for multi-camera efficiency

Once a scene's Stage 4 Blender environment is loaded, rendering additional cameras is cheap:
- Keep the Blender subprocess alive with a pipe-based command protocol
- Subsequent cameras: just issue `render <camera_id>` command — 8–15 s each
- Stage 5 refinement is independent per camera; parallelise with batch size 1 on GPU (sequential in practice)

**Amortised cost of Nth camera angle on the same scene:** ~25 s total (10 s Blender + 8 s refinement + 7 s post).

## 6. Preference-signal modulation (Pipeline C feedback)

Every scene assembly reads `PreferenceSignal` nodes for the brand and applies:

| `subject_kind` prefix | Modulation |
|---|---|
| `composition.*` | Shifts placement positions before writing |
| `color.*` | Shifts colour-grading target in Stage 7 |
| `lighting.*` | Adjusts `Light.color_temp_k` and `intensity` defaults |
| `refinement.*` | Adjusts Stage 5 weights |
| `camera.*` | Biases camera position generation |

Hard brand constraints (primary hex values, approved-usage contexts) **cannot** be overridden by preference signals. Enforced in `interaction/retrieval_bias.py`.

## 7. Acceptance tests

- `tests/scene/test_parse_intent.py` — 20 seeded prompts, assert valid scene-graph JSON
- `tests/scene/test_view_consistency.py` — render 3 cameras, assert brand ΔE variance ≤ 3.0
- `tests/scene/test_second_camera_latency.py` — assert additional camera render ≤ 45 s
- `tests/scene/test_preference_bias_applied.py` — seeded preferences shift output as expected
- `tests/scene/test_vram_profile.py` — assert peak matches §4 table within ±10 %
