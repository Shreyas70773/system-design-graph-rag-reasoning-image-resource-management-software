"""
ComfyUI custom node registration for research modules.
"""

from .research_nodes import (
    ConstraintViolationCheckerNode,
    DynamicCFGSchedulerNode,
    FeedbackWeightAdapterNode,
    GraphConditionerNode,
    IdentityLockNode,
    LayoutConstraintNode,
    MultiSeedEvaluatorNode,
    PaletteRegularizerNode,
)


NODE_CLASS_MAPPINGS = {
    "GraphConditionerNode": GraphConditionerNode,
    "DynamicCFGSchedulerNode": DynamicCFGSchedulerNode,
    "PaletteRegularizerNode": PaletteRegularizerNode,
    "LayoutConstraintNode": LayoutConstraintNode,
    "IdentityLockNode": IdentityLockNode,
    "ConstraintViolationCheckerNode": ConstraintViolationCheckerNode,
    "FeedbackWeightAdapterNode": FeedbackWeightAdapterNode,
    "MultiSeedEvaluatorNode": MultiSeedEvaluatorNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GraphConditionerNode": "Graph Conditioner",
    "DynamicCFGSchedulerNode": "Dynamic CFG Scheduler",
    "PaletteRegularizerNode": "Palette Regularizer",
    "LayoutConstraintNode": "Layout Constraint",
    "IdentityLockNode": "Identity Lock",
    "ConstraintViolationCheckerNode": "Constraint Violation Checker",
    "FeedbackWeightAdapterNode": "Feedback Weight Adapter",
    "MultiSeedEvaluatorNode": "Multi Seed Evaluator",
}
