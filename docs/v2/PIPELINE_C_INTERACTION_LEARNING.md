# PIPELINE C — Interaction and Learning

**Version:** C/1.0.0  
**Purpose:** Turn every user edit (in 3D canvas or 2D canvas) into a graph mutation, an `Interaction` node, and (eventually) a `PreferenceSignal` that modulates future scenes for the same brand.  
**Runtime:** In-process (CPU only, except the VLM natural-language command parser).

---

## 1. Inputs and outputs

**Input (from frontend, one of):**
- **Structured edit** — already in structured form: `{ action, target_id, params }`
- **Natural-language edit** — raw text + optional mask + optional target pixel coords

**Output:**
- Graph mutation (on the target `Placement`, `Material`, `Camera`, `Light`, `TextLayer`, `Scene`, or `Asset`)
- One `Interaction` node recording the event
- Possibly one `PreferenceSignal` node (if distillation threshold reached)
- Re-render request dispatched to Pipeline B for affected cameras

## 2. The structured edit command grammar

Locked. Every edit path ultimately produces one of these. The VLM in the NL path outputs this schema or fails.

```python
# backend/app/interaction/models.py
class StructuredEditCommand(BaseModel):
    action: Literal[
        "select", "move", "rotate", "scale", "delete", "duplicate",
        "change_material", "change_color", "add_object", "replace_object",
        "add_camera", "move_camera", "change_light",
        "add_text", "edit_text", "delete_text",
        "adjust_terrain", "regenerate_part", "approve_decomposition", "reject_decomposition"
    ]
    target_kind: Literal["placement", "material", "camera", "light", "text_layer", "scene", "asset", "semantic_part", "terrain"]
    target_id: str
    params: dict   # action-specific; validated by dispatch_schema below
    rerender_cameras: List[str] = []   # which cameras to rerun Pipeline B stages 4-8 on
```

Action parameter schemas are enumerated in `backend/app/interaction/dispatch_schema.py`. Each action has a Pydantic sub-model. Unknown action = 400.

## 3. Natural-language edit resolution

The most novel part of this pipeline. Called from `POST /api/v2/interactions/nl`.

### 3.1 Inputs
- `raw_text`: user's natural-language instruction
- `scene_id`: which scene they are editing
- `mask`: optional PNG alpha mask (from SAM 2.1 click-or-circle on 2D canvas)
- `pixel_coords`: optional `[x, y]` if user clicked without mask

### 3.2 Resolution steps

```
raw_text + mask/coords
        │
        ▼
1. Resolve targets:
     If mask provided:
       Query object_id_pass → unique Placement IDs intersecting mask
     Elif pixel_coords provided:
       Single Placement ID at those coords
     Else:
       Targets = entire scene (global edit)
        │
        ▼
2. VLM call (Qwen2.5-VL-7B):
     System: VLM_EDIT_COMMAND_V2 (locked prompt)
     User:
       - Image: current 2D render + mask overlay
       - Targets: Placement metadata for resolved IDs
       - Scene graph summary
       - Instruction: raw_text
     Output: StructuredEditCommand JSON (or {"error": "..."})
        │
        ▼
3. Validate:
     Pydantic parse → StructuredEditCommand
     Verify target_id is in resolved targets (prevents VLM from editing wrong thing)
        │
        ▼
4. Confidence gate:
     If vlm_confidence < 0.7 → reply with "please clarify" + suggested commands
     Else → proceed
        │
        ▼
5. Dispatch to applier (see §4)
```

### 3.3 Audit trail

Every NL call writes a `NaturalLanguageCommand` node regardless of outcome. The `applied` flag records whether the downstream edit actually committed. This gives us:
- VLM accuracy metrics: `applied = true` rate per command template
- Regression detection: VLM drift over version changes
- User-preference signal on phrasing: which phrasings succeed

## 4. Applier — structured command → graph mutation

Located at `backend/app/interaction/applier.py`. One method per action; each method:
1. Validates the user has permission on the target (auth TBD Phase 2; MVP is single-user)
2. Opens a Neo4j write transaction as the Pipeline C DB user
3. Records `Interaction` node first (before the mutation) so we can audit even failed mutations
4. Applies the mutation
5. Records the MODIFIED edge with `before_value` and `after_value` snapshots
6. Returns the list of cameras that need re-rendering

Example dispatch table:

| action | graph target | mutation |
|---|---|---|
| `move` | Placement | `p.position = params.position` |
| `rotate` | Placement | `p.rotation_quat = params.quat` |
| `scale` | Placement | `p.scale = params.scale` |
| `change_color` | Material or Placement.material_override | `m.albedo_dominant_hex = params.hex` (and regenerate albedo texture if not a solid override) |
| `delete` | Placement | remove `HAS_PLACEMENT` edge; keep node for audit with `visible=false` |
| `replace_object` | Placement | `p.asset_id = params.new_asset_id` + update `INSTANCE_OF` edge |
| `regenerate_part` | SemanticPart | triggers Pipeline A per-part re-run |
| `add_text` | Scene | creates new `TextLayer` |

All mutations are idempotent if the applier is given a command with an already-current state. This makes retries safe.

## 5. Distillation — Interactions → PreferenceSignals

Runs in a background task every 5 minutes (or on demand when brand page is opened). Located at `backend/app/interaction/distiller.py`.

### 5.1 Candidate patterns and their signal types

| Observation pattern | Signal produced |
|---|---|
| User moves product `+y` > 0.05 on ≥ 3 scenes in 7 days | `composition.product_y_bias = +0.08` (weight 0.4, half-life 30 d) |
| User deletes `lens_flare` placement on ≥ 2 scenes | `aesthetic.lens_flare = avoid` (weight 0.6, half-life 60 d) |
| User warms color temp by ≥ 300 K on ≥ 3 scenes | `lighting.color_temp_bias = +300` (weight 0.3) |
| User regenerates the same part with same hint twice | `ingestion.part_regen_hint = <hint>` (weight 0.5; applies in Pipeline A) |
| User accepts a specific camera template on ≥ 5 scenes | `camera.template.<shot_type> = saved_config` (weight 0.8) |
| User approves decomposition parts without edits | `ingestion.trust_autoDecompose = +0.1` (nudge model selection) |

### 5.2 Decay model

```
weight(t) = weight_0 * 0.5 ** ((t_now - t_created) / half_life_days)
```

Applied on retrieval (Pipeline B Stage 2). Signals with weight < 0.05 are ignored and periodically garbage-collected (after 180 days past creation).

### 5.3 Supersession

When a new signal contradicts an old one (same `subject_kind`, opposite `direction`), the distiller:
1. Writes the new `PreferenceSignal`
2. Writes a `SUPERSEDES` edge to the old one
3. Halves the old one's weight (fast decay) but keeps it for audit

This gives the creative director visibility into "preference flip-flop" patterns.

## 6. Retrieval-side usage

Pipeline B Stage 2 reads preference signals filtered by `weight > 0.05`. The `retrieval_bias.py` module converts them into:
- `position_deltas: dict[role, Vec3]` — applied at Stage 3
- `color_target_tilt: Vec3` (LAB space) — applied at Stage 7
- `lighting_overrides: dict[field, float]` — applied at Stage 3
- `refinement_overrides: dict[field, float]` — applied at Stage 5

Hard brand rules always win. Preference biases are bounded:
- Position deltas: ≤ 15 % of scene extent
- Color tilt: ≤ 5 ΔE from brand target
- Lighting: ≤ ±500 K, ≤ ±30 % intensity

These bounds are hard-coded and not user-configurable in MVP. They prevent runaway learning from a small set of outlier edits.

## 7. Creative director's "Learned Preferences" panel

`GET /api/v2/brands/:brand_id/preferences`:

Returns all active `PreferenceSignal` nodes with:
- Current effective weight (after decay)
- Source interactions (IDs + human-readable descriptions)
- Affected stages in Pipeline B
- Option to delete

Frontend route: `/brands/:id/preferences`. The panel is the user-facing embodiment of the "transparent decomposition + transparent learning" research claim.

## 8. Acceptance tests

- `tests/interaction/test_structured_dispatch.py` — each of the ~20 action verbs round-trips through a mutation
- `tests/interaction/test_nl_resolution.py` — 50 seeded natural-language prompts → ≥ 90 % correct StructuredEditCommand
- `tests/interaction/test_distiller_thresholds.py` — synthetic 3×same-move events produce expected PreferenceSignal
- `tests/interaction/test_decay.py` — weight(t=30 days) ≈ 0.5 * weight(0)
- `tests/interaction/test_supersession.py` — contradicting signal supersedes and halves old weight
- `tests/interaction/test_bounds.py` — even with 100 consistent preference events, position delta never exceeds 15 %
