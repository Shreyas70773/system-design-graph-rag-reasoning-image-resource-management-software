# Capstone Upgrade Plan

## What The Current Repo Already Gives You

- A working React + FastAPI codebase with routing, storage, and Neo4j hooks
- A usable layer-editing prototype for segmentation, masked edits, and edit metrics
- A V2 graph discipline mindset that is still valuable for your capstone

## What Does Not Match The New PRD

- The product is still framed as brand/content generation, not photograph manipulation
- The graph stores brand/asset/scene-composition entities, not persistent photo objects and edit history
- Inpainting is currently brand-conditioned image editing, not scene-graph-aware object removal
- There is no first-class `Scene -> ImageObject -> SpatialRelationship -> EditEvent -> CanvasVersion` backbone
- OCR text editing, aspect-ratio graph updates, and cross-session scene memory are not yet system primitives

## Keep vs Replace

- Keep: FastAPI app shell, local storage approach, testing structure, and the idea of graph-backed conditioning
- Keep with adaptation: segmentation, masked editing surface, queue/worker patterns, and canvas UI patterns
- Replace: brand-centric schema as the capstone core data model
- Replace: product-generation framing in README/docs when you prepare the final submission branch

## Foundation Added In This Upgrade

- `backend/app/capstone/models.py`
  Defines the V3 capstone nodes for `Scene`, `ImageObject`, `TextRegion`, `SpatialRelationship`, `EditEvent`, and `CanvasVersion`
- `backend/app/capstone/store.py`
  Adds a JSON-backed scene store, spatial-relationship inference, edit history, and inpaint-context retrieval
- `backend/app/routers/v3_capstone.py`
  Exposes `/api/v3/...` endpoints for scene creation, object registration, text regions, history, aspect-ratio updates, and GraphRAG context lookup
- `backend/app/database/capstone_schema_v3.cypher`
  Adds Neo4j constraints for the new capstone labels

## Immediate Build Order From Here

1. Connect the frontend canvas to `/api/v3/scenes` and `/api/v3/scenes/{id}/objects`
2. Replace mock object registration with SAM 2 masks + bbox extraction
3. Route remove/move/resize operations through `EditEvent` creation
4. Attach LaMa inpaint/outpaint calls to the V3 scene store so every edit updates both pixels and graph state
5. Add OCR-backed `TextRegion` creation and inline text edit flows
6. Add evaluation scripts that compare blind inpaint vs graph-guided inpaint using the same scene snapshots

## Capstone Positioning

Your strongest capstone story is no longer "I built a content generator." It is:

> "I upgraded an AI editing prototype into a persistent scene-graph image manipulation system where every object, text region, and edit is represented explicitly and can be retrieved for context-aware inpainting and evaluation."
