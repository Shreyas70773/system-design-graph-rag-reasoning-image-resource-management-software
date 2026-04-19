# Capstone Accuracy Tuning

## Why This Matters

Once SAM 2 and LaMa are running locally, the first quality gains usually come from mask quality rather than changing the base model.

This backend now exposes tunable parameters for exactly that reason.

## Segmentation Parameters

Use these with `POST /api/v3/scenes/{scene_id}/segment-click` under `tuning`.

```json
{
  "click_x": 0.42,
  "click_y": 0.58,
  "label": "chair",
  "tuning": {
    "multimask_strategy": "largest_mask",
    "dilate_px": 2,
    "erode_px": 0,
    "keep_largest_component": true,
    "min_area_fraction": 0.002
  }
}
```

### What each parameter does

- `multimask_strategy`
  - `best_score`: safer default
  - `largest_mask`: better when SAM under-segments the object
- `dilate_px`
  - expands the mask boundary
  - useful when object edges are being clipped
- `erode_px`
  - shrinks the mask slightly
  - useful when SAM bleeds into nearby background
- `keep_largest_component`
  - removes stray islands
  - usually improves stability for inpainting
- `min_area_fraction`
  - rejects tiny accidental masks from bad clicks

## Inpainting Parameters

Use these with `POST /api/v3/scenes/{scene_id}/remove-object` under `tuning`.

```json
{
  "object_id": "obj_123",
  "tuning": {
    "mask_dilate_px": 8,
    "neighbor_limit": 6,
    "preserve_text_regions": true
  }
}
```

### What each parameter does

- `mask_dilate_px`
  - expands the removal mask before LaMa runs
  - usually improves background cleanup around object boundaries
- `neighbor_limit`
  - changes how much graph context is retrieved and stored with the edit
  - useful for later evaluation and ablation
- `preserve_text_regions`
  - reserved for the next iteration where text regions are protected explicitly during object removal

## First Accuracy Use Case

Start with a scene where object removal often leaves a halo:

- a chair on patterned tiles
- a lamp against a textured wall
- a bottle in front of shelves

Try this progression:

1. baseline
   - segmentation `best_score`
   - inpaint `mask_dilate_px = 4`
2. higher recall
   - segmentation `largest_mask`
   - `dilate_px = 2`
   - inpaint `mask_dilate_px = 8`
3. tighter edges
   - segmentation `erode_px = 1`
   - inpaint `mask_dilate_px = 2`

Compare:

- edge halos
- leftover object fragments
- background continuity
- whether graph neighbor retrieval matches the visual surroundings

## Practical Research Angle

This gives you a clean capstone mini-study:

> How much does post-segmentation mask tuning improve graph-guided inpainting quality before any model retraining?

That is a realistic and defendable improvement path for your paper.
