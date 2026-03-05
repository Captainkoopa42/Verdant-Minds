# Verdant-Minds architecture

This document describes the implemented architecture at a practical level.

## System shape

`UnifiedSystem` (exported as `usm.UnifiedSyntheticMind`) coordinates:

1. Nine sequential processing blocks.
2. Governance via `ThreeKingsLayer` (`DataKing`, `ForefrontKing`, `EthicsKing`).
3. `MemoryWeb` graph memory.
4. `ECWFCore` wave-state model.
5. `MemoryECWFBridge` coupling memory and wave state.
6. Per-input data container `CognitiveChunk`.

## Nine-block processing order

For each input, a `CognitiveChunk` passes through:

1. Sensory Input
2. Pattern Recognition
3. Memory Storage
4. Internal Communication
5. Reasoning & Planning
6. Ethics & Values
7. Action Selection
8. Language Processing
9. Continual Learning

## Thermodynamic and coherence telemetry

Per-cycle telemetry commonly includes:

- `T_g` (glass transition temperature)
- `system_entropy`
- `T_cog = 1 - T_g + system_entropy` (cultivator telemetry)
- HCI (`housed_contradiction_index`)
- `resonance_patterns` summary from continual learning

## Memory and edge dynamics

- Concepts are stored in `MemoryWeb.memory_store`.
- Connections can include ethical-distance metadata (`delta_e`) and edge acceptance logic (`pconnect`).
- Kernel loop CSV reports `mean_edge_delta_e` as a periodic edge-level summary metric.

## Implementations and scope notes

- `scripts/kernel_loop.py --demo` includes a demo-specific **FCE estimate heuristic** for reporting.
- `scripts/verdant_llm_cultivator.py` is the canonical long-run telemetry/cultivation workflow.
- Do not treat demo FCE and cultivator `T_cog` as the same quantity.

## Emergent scaffolding analysis

`scripts/analysis/scaffolding_from_state.py` analyzes persisted state files by:

1. Reading `memory_web.memory_store`.
2. Detecting emergent nodes via `metadata.origin == wave_emergence`.
3. Using creation times from `metadata.creation_time` (label timestamp fallback).
4. Building a weighted undirected graph and top-k backbone per node.
5. Evaluating emergent↔emergent backbone edges for temporal orientation (`earlier-share`).
6. Running shuffle trials to estimate a null baseline.

## Limitations

- LLM provider nondeterminism affects cultivation trajectories.
- Results depend on the available state/log schema.
- Resume runs reuse prior state and are not equivalent to from-scratch runs with the same cycle count.
