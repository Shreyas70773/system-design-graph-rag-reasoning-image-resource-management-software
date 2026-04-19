# GRAPH_SCHEMA_V2 — The Source of Truth

**Version:** 2.0.0  
**Status:** LOCKED. Changes require a schema migration PR + approval.  
**Validated by:** `backend/scripts/validate_graph_schema.py` (runs in CI)  
**Authoritative for:** every Pydantic model, every Cypher query, every V2 API contract.

---

## 0. Rules for this document

1. This file is the **only** place node types, relationships, and property names are defined.
2. All Pydantic models in `backend/app/schema_v2.py` are generated from this file OR must round-trip-match it (asserted in CI).
3. Every Cypher query in the V2 codebase must reference only node labels, relationship types, and property names declared below.
4. Changes to this file are made via a "schema migration" PR that:
   - Bumps the version header
   - Updates `backend/app/schema_v2.py`
   - Includes a Cypher migration script under `backend/migrations/v2/<version>.cypher`
   - Passes `validate_graph_schema.py` against a fresh Neo4j instance
5. `schema_version` is stored on the `Brand` node. V1 brands stay `"1.0"`. V2 brands are `"2.0"`. Code paths dispatch on this.

---

## 1. Node types

Every node has these **common properties** unless otherwise noted:
- `id: string` (UUID v4, primary key)
- `created_at: datetime` (ISO 8601)
- `updated_at: datetime` (ISO 8601)
- `schema_version: string` (default `"2.0"`)

### 1.1 Brand-level nodes

#### `(Brand)`
Root node for a brand's entire graph subtree.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | UUID |
| `name` | string | yes | |
| `source_url` | string | no | Scraped source, if any |
| `schema_version` | string | yes | `"2.0"` for V2 |
| `primary_hex` | list[string] | yes | Hex colours; authoritative list in `HAS_COLOR` edges |
| `aesthetic_prefs` | json | no | Learned. Format: `{ "lens_flare": "avoid", ... }` |
| `composition_prefs` | json | no | Learned. Format: `{ "product_y_bias": 0.1, ... }` |

#### `(Color)`
| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `hex` | string | yes | `#RRGGBB` |
| `lab_l` | float | yes | LAB L (D65 illuminant) |
| `lab_a` | float | yes | |
| `lab_b` | float | yes | |
| `usage_context` | list[string] | yes | Subset of `{digital, print, ooh}` |
| `name` | string | no | Human-readable (e.g. "Acme Blue") |

#### `(Font)`
| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `family` | string | yes | |
| `weight` | int | yes | 100–900 |
| `italic` | bool | yes | |
| `file_url` | string | no | For loading into the canvas |
| `license_status` | string | yes | `ok` / `restricted` / `unknown` |

### 1.2 Asset cluster (the replacement for V1's opaque `Asset`)

#### `(Asset)`
The hub of a decomposed brand asset. A single `Asset` has many related nodes.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `asset_type` | string | yes | `product` / `logo` / `character_ref` / `texture` / `environment_ref` |
| `source_url` | string | yes | Original 2D reference (base64 URL allowed) |
| `ingestion_status` | string | yes | `pending` / `decomposing` / `awaiting_approval` / `approved` / `rejected` |
| `vlm_description` | string | no | Populated in Pipeline A step 2 |
| `clip_embedding` | vector(768) | no | For similarity retrieval |
| `approved_at` | datetime | no | Set only when `ingestion_status = approved` |
| `approved_by_user_id` | string | no | |

#### `(Mesh3D)`
| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `file_url` | string | yes | GLB or GLTF URL |
| `vertex_count` | int | yes | |
| `bbox_min` | list[float] | yes | `[x, y, z]` |
| `bbox_max` | list[float] | yes | `[x, y, z]` |
| `canonical_scale_m` | float | yes | Estimated real-world scale in metres |
| `lod_level` | int | yes | 0 = coarsest, 3 = highest |
| `generator_model` | string | yes | e.g. `TRELLIS-v2` |
| `generator_version` | string | yes | |

#### `(Material)`
PBR material. Multiple materials can be attached to one `Asset`, each for a different part.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `albedo_url` | string | yes | Texture URL |
| `albedo_dominant_hex` | string | yes | For colour-matching to brand palette |
| `roughness_url` | string | no | |
| `metallic_url` | string | no | |
| `normal_url` | string | no | |
| `emissive_url` | string | no | |
| `uv_set_index` | int | yes | Default 0 |

#### `(SemanticPart)`
A named region of an asset. Example: "cap" on a bottle, "face" on a character.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `name` | string | yes | e.g. `cap`, `body`, `front_label`, `strap` |
| `mask_url` | string | yes | PNG alpha mask in 2D reference space |
| `uv_region` | json | yes | `{ u_min, v_min, u_max, v_max }` in the mesh's UV space |
| `part_type` | string | yes | `structural` / `label` / `decoration` / `logo_target` |
| `editable` | bool | yes | If false, user cannot regenerate this part |

#### `(LightProbe)`
Lighting captured from the reference photo. Used for delighting during ingestion.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `hdri_url` | string | no | Equirectangular HDRI generated from the reference |
| `estimated_direction` | list[float] | yes | `[x, y, z]` unit vector |
| `estimated_color_temp_k` | int | yes | |
| `estimated_intensity` | float | yes | |
| `confidence` | float | yes | 0..1 |

#### `(CanonicalPose)`
The asset's "hero" pose — how it looks in its brand-approved default.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `rotation_quat` | list[float] | yes | `[x, y, z, w]` |
| `suggested_camera_position` | list[float] | yes | |
| `suggested_camera_focal_mm` | float | yes | |

#### `(LogoAsset)`
Separate from `Asset` because logos attach to products via UV projection, not as standalone geometry.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `svg_url` | string | no | Preferred |
| `png_url` | string | no | Fallback |
| `dominant_hex` | string | yes | |
| `aspect_ratio` | float | yes | |
| `min_size_px` | int | yes | For auto-rejection at low resolution |

#### `(DecompositionRun)`
Provenance for every asset ingestion. Records which models did what, and what the user did afterwards.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `pipeline_version` | string | yes | `A/1.0.0` style |
| `vlm_model` | string | yes | |
| `segmenter_model` | string | yes | |
| `delighter_model` | string | no | |
| `mesh_model` | string | yes | |
| `started_at` | datetime | yes | |
| `completed_at` | datetime | no | |
| `user_approved` | bool | yes | |
| `user_regenerated_parts` | list[string] | no | Names of parts user re-ran |
| `user_edits_json` | json | no | Serialised edit log |
| `confidence_overall` | float | yes | 0..1 |

### 1.3 Scene-level nodes

#### `(Scene)`
A composition that can be rendered.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `brand_id` | string | yes | FK to `Brand.id`; enforced via edge too |
| `intent_text` | string | yes | Original user prompt |
| `scene_graph_json` | json | yes | Parsed scene graph from LLM |
| `deployment_context` | string | yes | `digital` / `print` / `ooh` |
| `status` | string | yes | `draft` / `rendered` / `published` |

#### `(Placement)`
An instance of an `Asset` within a `Scene`.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `asset_id` | string | yes | FK to `Asset.id`; also edge |
| `position` | list[float] | yes | `[x, y, z]` in scene units |
| `rotation_quat` | list[float] | yes | |
| `scale` | list[float] | yes | `[sx, sy, sz]` |
| `z_order` | int | yes | For flat-composition fallback |
| `cast_shadow` | bool | yes | |
| `receive_shadow` | bool | yes | |
| `material_override_ids` | list[string] | no | FKs to `Material.id` |
| `visible` | bool | yes | |

#### `(Camera)`
| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `position` | list[float] | yes | |
| `target` | list[float] | yes | Look-at point |
| `up` | list[float] | yes | Default `[0,1,0]` |
| `focal_length_mm` | float | yes | |
| `fov_deg` | float | yes | |
| `shot_type` | string | yes | `hero` / `detail` / `wide` / `custom` |
| `aspect_ratio` | string | yes | `1:1` / `16:9` / `9:16` / `4:5` |
| `resolution_px` | list[int] | yes | `[w, h]` |

#### `(Light)`
| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `light_type` | string | yes | `directional` / `point` / `area` / `hdri` |
| `position` | list[float] | no | For non-directional |
| `direction` | list[float] | no | For directional |
| `color_hex` | string | yes | |
| `color_temp_k` | int | yes | |
| `intensity` | float | yes | |
| `casts_shadow` | bool | yes | |
| `hdri_url` | string | no | For `hdri` type |

#### `(Terrain)`
Optional. A scene can have zero or one terrain.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `heightmap_url` | string | yes | 16-bit PNG |
| `size_m` | list[float] | yes | `[x_m, z_m]` |
| `texture_layer_ids` | list[string] | yes | FKs to `Material.id` |
| `blend_mask_urls` | list[string] | no | Per-layer masks |

#### `(TextLayer)`
2D text overlays rendered after the 3D pass. First-class citizens so they are editable after render.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `text` | string | yes | |
| `font_id` | string | yes | FK to `Font.id` |
| `size_px` | int | yes | |
| `color_hex` | string | yes | |
| `position_norm` | list[float] | yes | `[x, y]` in `[0, 1]` over the render canvas |
| `anchor` | string | yes | `top-left` / `center` / ... |
| `max_width_norm` | float | yes | |
| `z` | int | yes | Stacking order among text layers |

#### `(Render)`
A completed render of a `Scene` from a `Camera`.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `scene_id` | string | yes | FK |
| `camera_id` | string | yes | FK |
| `image_url` | string | yes | Composed final render |
| `object_id_pass_url` | string | yes | Hidden pass for click-to-select |
| `depth_pass_url` | string | no | For debugging |
| `refinement_model` | string | yes | e.g. `FLUX.1-schnell-NF4` |
| `render_time_sec` | float | yes | |
| `peak_vram_mb` | int | yes | Captured by `vram_profile_v2.py` hooks |

### 1.4 Interaction and learning nodes

#### `(Interaction)`
Captures a single user action. Written by Pipeline C.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `session_id` | string | yes | |
| `user_id` | string | yes | |
| `timestamp` | datetime | yes | |
| `interaction_type` | string | yes | See list below |
| `surface` | string | yes | `3d_canvas` / `2d_canvas` / `asset_editor` / `learned_prefs_panel` |
| `natural_language` | string | no | Populated for `nl_edit` type |
| `structured_command_json` | json | yes | The resolved edit command |

Permitted `interaction_type` values (enum, update this list when adding):
`select`, `move`, `rotate`, `scale`, `delete`, `duplicate`, `change_material`, `change_color`, `add_object`, `replace_object`, `nl_edit`, `approve_decomposition`, `reject_decomposition`, `regenerate_part`, `add_camera`, `move_camera`, `change_light`, `add_text`, `edit_text`, `delete_text`, `adjust_terrain`.

#### `(PreferenceSignal)`
Learned signal distilled from one or more interactions.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `subject_kind` | string | yes | e.g. `composition.product_y` |
| `direction` | float | yes | -1..+1 |
| `weight` | float | yes | 0..1, decays over time |
| `half_life_days` | int | yes | Default 30 |
| `source_interaction_ids` | list[string] | yes | Backlinks |
| `superseded_by_id` | string | no | If a newer signal overrode this |

#### `(NaturalLanguageCommand)`
Distinct node so we can audit VLM behaviour independent of graph state.

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | |
| `raw_text` | string | yes | |
| `vlm_model` | string | yes | |
| `mask_url` | string | no | Circle-mask if provided |
| `target_placement_ids` | list[string] | yes | Resolved targets |
| `resolved_action` | string | yes | One of the structured verbs |
| `resolved_params_json` | json | yes | |
| `confidence` | float | yes | |
| `applied` | bool | yes | Whether the edit was actually performed |

---

## 2. Relationship types

All relationships have:
- `created_at: datetime`

### 2.1 Brand-asset relationships

| From → To | Type | Properties | Cardinality |
|---|---|---|---|
| `Brand` → `Color` | `HAS_COLOR` | `priority` (primary/secondary/accent), `contexts` | 1:N |
| `Brand` → `Font` | `HAS_FONT` | `priority`, `contexts` | 1:N |
| `Brand` → `Asset` | `HAS_ASSET` | `approved_usage_contexts` | 1:N |
| `Brand` → `LogoAsset` | `HAS_LOGO` | `is_primary` (bool) | 1:N |
| `Brand` → `PreferenceSignal` | `LEARNED_PREF` | — | 1:N |

### 2.2 Asset decomposition relationships

| From → To | Type | Properties | Cardinality |
|---|---|---|---|
| `Asset` → `Mesh3D` | `HAS_GEOMETRY` | — | 1:N (multiple LODs) |
| `Asset` → `Material` | `HAS_MATERIAL` | `part_name` (nullable) | 1:N |
| `Asset` → `SemanticPart` | `HAS_PART` | — | 1:N |
| `Asset` → `LightProbe` | `HAS_LIGHT_PROBE` | — | 1:1 |
| `Asset` → `CanonicalPose` | `HAS_CANONICAL_POSE` | — | 1:1 |
| `Asset` → `DecompositionRun` | `DECOMPOSED_BY` | — | 1:N (one per re-run) |
| `SemanticPart` → `Material` | `USES_MATERIAL` | — | N:1 |
| `SemanticPart` → `LogoAsset` | `REFERENCES_LOGO` | — | N:1 |

### 2.3 Scene composition relationships

| From → To | Type | Properties | Cardinality |
|---|---|---|---|
| `Brand` → `Scene` | `OWNS_SCENE` | — | 1:N |
| `Scene` → `Placement` | `HAS_PLACEMENT` | — | 1:N |
| `Placement` → `Asset` | `INSTANCE_OF` | — | N:1 |
| `Scene` → `Camera` | `HAS_CAMERA` | — | 1:N |
| `Scene` → `Light` | `HAS_LIGHT` | — | 1:N |
| `Scene` → `Terrain` | `HAS_TERRAIN` | — | 1:1 |
| `Scene` → `TextLayer` | `HAS_TEXT_LAYER` | — | 1:N |
| `Scene` → `Render` | `HAS_RENDER` | — | 1:N |

### 2.4 Interaction and learning relationships

| From → To | Type | Properties | Cardinality |
|---|---|---|---|
| `Interaction` → `Placement` | `MODIFIED` | `field_name`, `before_value`, `after_value` | N:N |
| `Interaction` → `Asset` | `MODIFIED` | same | N:N |
| `Interaction` → `Material` | `MODIFIED` | same | N:N |
| `Interaction` → `Camera` | `MODIFIED` | same | N:N |
| `Interaction` → `Light` | `MODIFIED` | same | N:N |
| `Interaction` → `TextLayer` | `MODIFIED` | same | N:N |
| `Interaction` → `NaturalLanguageCommand` | `RESOLVED_BY` | — | N:1 |
| `Interaction` → `PreferenceSignal` | `CONTRIBUTED_TO` | `weight_contribution` | N:N |
| `PreferenceSignal` → `PreferenceSignal` | `SUPERSEDES` | — | 1:1 |

---

## 3. Constraints and indexes

### 3.1 Uniqueness constraints
```
CREATE CONSTRAINT brand_id IF NOT EXISTS FOR (b:Brand) REQUIRE b.id IS UNIQUE;
CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (a:Asset) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT scene_id IF NOT EXISTS FOR (s:Scene) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT placement_id IF NOT EXISTS FOR (p:Placement) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT camera_id IF NOT EXISTS FOR (c:Camera) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT interaction_id IF NOT EXISTS FOR (i:Interaction) REQUIRE i.id IS UNIQUE;
CREATE CONSTRAINT render_id IF NOT EXISTS FOR (r:Render) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT color_hex IF NOT EXISTS FOR (c:Color) REQUIRE c.hex IS UNIQUE;
```

### 3.2 Existence constraints (key required properties)
```
CREATE CONSTRAINT brand_name IF NOT EXISTS FOR (b:Brand) REQUIRE b.name IS NOT NULL;
CREATE CONSTRAINT brand_version IF NOT EXISTS FOR (b:Brand) REQUIRE b.schema_version IS NOT NULL;
CREATE CONSTRAINT asset_type IF NOT EXISTS FOR (a:Asset) REQUIRE a.asset_type IS NOT NULL;
CREATE CONSTRAINT scene_context IF NOT EXISTS FOR (s:Scene) REQUIRE s.deployment_context IS NOT NULL;
```

### 3.3 Vector indexes
```
CREATE VECTOR INDEX asset_clip_embedding IF NOT EXISTS
FOR (a:Asset) ON (a.clip_embedding)
OPTIONS { indexConfig: { `vector.dimensions`: 768, `vector.similarity_function`: 'cosine' } };
```

### 3.4 Range / lookup indexes
```
CREATE INDEX interaction_session IF NOT EXISTS FOR (i:Interaction) ON (i.session_id);
CREATE INDEX interaction_timestamp IF NOT EXISTS FOR (i:Interaction) ON (i.timestamp);
CREATE INDEX asset_status IF NOT EXISTS FOR (a:Asset) ON (a.ingestion_status);
CREATE INDEX render_scene IF NOT EXISTS FOR (r:Render) ON (r.scene_id);
```

---

## 4. Pipeline write-ownership matrix

Every node and relationship has **exactly one** pipeline that is permitted to create it. This prevents drift.

| Node / Relationship | Created by | Updated by |
|---|---|---|
| `Brand`, `Color`, `Font`, `LogoAsset`, `HAS_COLOR`, `HAS_FONT`, `HAS_LOGO` | V1 onboarding (unchanged) | V2 learning loop (`aesthetic_prefs` etc.) |
| `Asset`, `Mesh3D`, `Material`, `SemanticPart`, `LightProbe`, `CanonicalPose`, `DecompositionRun`, `HAS_GEOMETRY`, `HAS_MATERIAL`, `HAS_PART`, `HAS_LIGHT_PROBE`, `HAS_CANONICAL_POSE`, `DECOMPOSED_BY`, `USES_MATERIAL`, `REFERENCES_LOGO` | **Pipeline A** | Pipeline A (re-ingestion) or user approval events |
| `Scene`, `Placement`, `Camera`, `Light`, `Terrain`, `TextLayer`, `Render`, `OWNS_SCENE`, `HAS_PLACEMENT`, `INSTANCE_OF`, `HAS_CAMERA`, `HAS_LIGHT`, `HAS_TERRAIN`, `HAS_TEXT_LAYER`, `HAS_RENDER` | **Pipeline B** | Pipeline C (via structured edit commands) |
| `Interaction`, `PreferenceSignal`, `NaturalLanguageCommand`, `MODIFIED`, `RESOLVED_BY`, `CONTRIBUTED_TO`, `SUPERSEDES`, `LEARNED_PREF` | **Pipeline C** | Pipeline C only |

Enforcement: each pipeline has its own Neo4j user with ACL limited to its write-ownership set. See `backend/app/scene/neo4j_access.py` (TBD week 2).

---

## 5. Backwards compatibility with V1

V1 brands live in the same database. Dispatch is driven by `Brand.schema_version`:
- `"1.0"` → V1 routers, V1 generation, V1 asset representation
- `"2.0"` → V2 routers, V2 pipelines

V1 nodes that exist alongside V2:
- V1 `Asset` (flat, with `base64` property) — unchanged, V2 ignores these
- V1 `Generation` — unchanged, V2's `Render` is a separate label

No V1 data is modified by V2 code paths. A future migration tool (Pipeline D, post-MVP) will upgrade V1 brands to V2 via Pipeline A on each of their assets.

---

## 6. How to change this schema

1. Open a branch named `schema/v2.<next-version>`.
2. Edit this file. Bump version header.
3. Update `backend/app/schema_v2.py`.
4. Write a Cypher migration at `backend/migrations/v2/<new-version>.cypher`.
5. Run `backend/scripts/validate_graph_schema.py --fresh` locally. Must pass.
6. Open PR. CI re-runs the validator. Must pass.
7. Merge only when green.

Violations of this process are reverts. No exceptions.
