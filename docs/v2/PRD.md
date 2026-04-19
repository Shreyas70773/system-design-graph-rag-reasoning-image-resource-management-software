# V2 Product Requirements Document
**Version:** 2.0.0  
**Status:** Locked for Phase 1–2 execution  
**Last updated:** 2026-04-17
---
## 1. Problem statement
Current brand-aware image generation tools, including V1 of this project, fail brand use cases on four structural axes:
1. **Opaque asset representation.** A product image is stored as `Asset { base64, embedding }`. The user cannot see how the system "understands" the bottle — its geometry, its label region, its lighting. Therefore the user cannot trust or correct the system's interpretation.
2. **Single-view output.** A 2D generation commits to one camera, one framing, one lighting — all simultaneously. Producing a second matching shot from the same intent is an unbounded retry-the-dice operation.
3. **Edits are destructive.** Inpainting re-diffuses over existing pixels. Selective regeneration is impossible because the rendered image has no latent structure remaining post-hoc.
4. **Preferences are forgotten.** User thumbs-down events go into a log, not into the graph's conditioning surface. The next generation for the same brand makes the same mistake.
## 2. Product vision
> A brand-aware 3D scene editor. Upload brand assets, watch them decompose into an inspectable 3D knowledge graph, compose scenes by placing objects in 3D space, render multiple 2D camera angles for any output context, and edit freely at either the 3D or 2D layer — with every edit teaching the graph about brand preferences without any model fine-tuning.
## 3. Primary personas
### P1 — Brand marketer (primary user)
- Manages a SKU catalogue and quarterly campaigns
- Needs multiple framings of each hero product (square for IG, 16:9 for web banner, 9:16 for stories)
- Does not know Blender, does not want to learn Blender
- Will click "Approve" or "Regenerate" on a per-part basis
- Success metric: produces 5 branded assets in 30 minutes from a single reference photo
### P2 — Creative director (approver)
- Reviews and approves/rejects
