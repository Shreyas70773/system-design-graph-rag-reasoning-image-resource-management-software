# Research Comfy Nodes Scaffold

This folder contains a first-pass custom-node scaffold for ComfyUI research workflows.

## Included Nodes

1. GraphConditionerNode
2. DynamicCFGSchedulerNode
3. PaletteRegularizerNode
4. LayoutConstraintNode
5. IdentityLockNode
6. ConstraintViolationCheckerNode
7. FeedbackWeightAdapterNode
8. MultiSeedEvaluatorNode

## Purpose

These nodes are lightweight operational scaffolds aligned to the research blueprint.
They provide deterministic interfaces and JSON payload outputs that can be wired
into Comfy workflows while full advanced implementations are being developed.

## Integration Notes

1. Copy this folder into ComfyUI custom_nodes as a package.
2. Ensure NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS are discoverable.
3. Wire node outputs to sampler/constraint flows incrementally.

## Current Scope

- Implemented: interface, parameters, deterministic baseline behavior.
- Not yet implemented: deep latent-space coupling and advanced differentiable guidance.
