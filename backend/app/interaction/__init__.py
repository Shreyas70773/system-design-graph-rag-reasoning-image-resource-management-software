"""Pipeline C — Interaction and learning.

See docs/v2/PIPELINE_C_INTERACTION_LEARNING.md for the full spec.

Public surface:
    - command_parser.NLCommandParser  — VLM NL → StructuredEditCommand
    - applier.EditApplier             — StructuredEditCommand → graph mutation
    - distiller.PreferenceDistiller   — interactions → PreferenceSignal
    - retrieval_bias.apply_biases     — PreferenceSignal → conditioning deltas
"""

__all__: list[str] = []
