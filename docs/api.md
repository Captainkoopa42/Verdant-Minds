# API reference (current code)

This is a compact, code-aligned reference for the public entry points used in this repository.

## Primary import

```python
from usm import UnifiedSyntheticMind
```

`UnifiedSyntheticMind` is an alias to `UnifiedSystem`.

## Core methods

### `process_input(input_text, metadata=None) -> CognitiveChunk`

What this does: runs one full nine-block cycle and returns the populated `CognitiveChunk`.

### `get_response(input_text, metadata=None) -> str`

What this does: convenience wrapper around processing that returns text output.

### `initialize_knowledge(ethical_concepts=None) -> dict`

What this does: seeds baseline knowledge concepts (and optional extra ethical concepts).

### `get_system_metrics() -> dict`

What this does: returns runtime/system metrics (including thermodynamic and memory summaries).

### `save_system_state(filepath) -> bool`

What this does: writes JSON state to disk.

### `load_system_state(filepath) -> UnifiedSyntheticMind`

What this does: classmethod constructor that loads a saved state file.

## Script-facing telemetry terms

- `T_g`: glass transition temperature.
- `T_cog`: in cultivator telemetry, `1 - T_g + system_entropy`.
- `HCI`: housed contradiction index.
- `resonance_patterns`: continual-learning resonance summary.
- `mean_edge_delta_e`: kernel loop edge-distance summary.

## Script interfaces

- `scripts/verdant_repl.py`: interactive loop.
- `scripts/verdant_telemetry.py`: structured telemetry loop.
- `scripts/kernel_loop.py --demo`: fixed 5-step demonstration (includes demo-only FCE estimate heuristic).
- `scripts/verdant_llm_cultivator.py`: multi-cycle cultivation with save/load support.
- `scripts/analysis/scaffolding_from_state.py`: emergent scaffolding metrics from a saved state.

## Reproducibility reminder

When sharing outputs, include seed/run context, fresh vs resume mode, provider chain, and cycle count.
