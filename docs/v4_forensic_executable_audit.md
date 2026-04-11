# Verdant-Minds V4 Forensic Execution Geometry

## 1) Data Metabolism: Input → Output

### Real execution path (single impulse)

```text
raw text
  -> VerdantSystem.process_input(text, metadata)
    -> AttentionBuffer gate (may drop to null-chunk if no escalation)
      -> _full_pipeline_process(text)
        -> CognitiveChunk(sections={sensory_input_section, processing_metrics_section})
        -> PipelineOrchestrator.run(blocks)
          1. SensoryInputBlock.process
          2. PatternRecognitionBlock.process
          3. MemoryBlock.process
          4. CommunicationBlock.process
             + DataKing.oversee hook
          5. ReasoningBlock.process
          6. EthicsBlock.process
             + EthicsKing.oversee hook
          7. ActionBlock.process
             + ForefrontKing.oversee hook
             + ThreeKingsCouncil.oversee hook
             + optional basin arbitration override
          8. LanguageBlock.process
          9. LearningBlock.process
        -> system-level coherence pass (_compute_coherence)
        -> thermodynamic update (_update_t_g)
        -> metrics + basin scan + basin dynamics
        -> final CognitiveChunk returned
```

### Junctions: standard input -> Verdant structures

- Raw `str` is first wrapped into a `CognitiveChunk` (`sensory_input_section`) in `_full_pipeline_process`.
- Sections become canonical transport substrate: each block reads/writes named dict sections.
- `PatternRecognitionBlock` transforms token stream into normalized concepts/keywords/tensions.
- `MemoryBlock` transforms symbolic concepts into sub-symbolic influence via `bridge.bidirectional_update(...)`.
- `EthomorphicBridge` maps concepts to dimension tuples `(type, dim_idx, weight)` and computes/update ECWF state.
- `ActionBlock` converts reasoning/ethics/memory scalars into a selected control action (`selected_action`).

### Losses / pruning / discards

- Token and concept pruning:
  - stopwords, short tokens (`<=2`), numeric tokens, duplicate concepts removed.
- Memory seeding filters:
  - minimum concept length, stopword reject, numeric reject, `basin_<n>` reject, hex-like reject.
- Activation loss:
  - propagation terminated below threshold and beyond max depth.
- Wave-to-telemetry reduction:
  - `wave_magnitude`/`wave_phase` arrays reduced to first scalar element in `MemoryBlock`.
- Reasoning truncation:
  - premise/inference lists sliced in planning output.
- Save-time pruning:
  - node connection lists truncated to max 50 entries; edges with weight `<0.01` discarded.

## 2) Governance Architecture (process brakes / rejection gates)

### Gating `if`/`try` controls that can block/alter execution

- **Attention gate**: no escalated attention item -> `_null_chunk(...)` (full pipeline skipped).
- **Basin routing gate**: disabled/no basins/no bridge -> micro-pipelines not run.
- **Data quality gate**: low quality or high novelty tags governance actions, modifies memory metadata.
- **Ethics gate**:
  - if status `review_needed`, response is hard-overridden and action changed to `defer_decision`.
- **Forefront gate**:
  - low confidence or high load can demote `answer_query` to `provide_partial_answer`.
- **Council gate**:
  - weighted vote can override action; weak override can be explicitly rejected.
- **Boundary emergence gate**:
  - rejects candidate on entropy range failure, low magnitude, duplicate combo-key, duplicate label.
- **Budding gate**:
  - interval/size/age/pressure/ejection checks block basin split when unmet.
- **Density gate**:
  - global edge pruning only activates when `edge/node > max_edge_ratio`.
- **Error swallowing (try/except)**:
  - `ThermalBridge` catches failures for basin detection, entropy fallback, metrics retrieval.
  - save-state pruning catches malformed edge weights.

### Handbrake for incoherence/entropy?

- No global `halt/raise` when coherence or entropy exceed thresholds.
- Incoherence (`triangle_valid_at_alpha1 == False`) causes penalties/overrides, not runtime stop.
- Entropy is used in scoring, phase modulation, and candidate rejection, not process termination.

### Write authority over MemoryWeb + hard-coded conditions

- `MemoryBlock`:
  - add concept if absent and `_should_seed_concept(...)` passes.
  - decay every cycle by phase-specific factor.
  - reinforce only when activation > 0.3.
- `EthomorphicBridge.update_memory_from_ecwf`:
  - activate concept only if computed activation > 0.2.
  - reinforce existing or create new concept; connect co-activated pairs.
- `detect_and_create_emergent_concepts_with_params` path:
  - adds emergent nodes when wave/novelty thresholds pass.
- `_evaluate_candidate_emergence`:
  - adds boundary emergent node + edges when entropy and magnitude thresholds pass.
- `regulate_density` / `prune_basin_edges`:
  - removes edges by ratio/weight policies.
- `ablate_oldest_emergent_nodes` (interventions module): removes nodes (experimental tooling).

## 3) Sub-symbolic Pipeline (Graph ↔ ECWF)

### Bridge mechanics

1. Concept → dimensions:
   - `assign_concept_mappings` creates tuples `(cognitive|ethical, dim_idx, weight)`.
2. Symbolic memory -> ECWF params:
   - `update_ecwf_from_memory` aggregates influence from concepts + neighbors into cognitive/ethical vectors.
   - calls `ecwf.update_parameters(...)`.
3. ECWF -> symbolic memory:
   - `update_memory_from_ecwf` computes `wave_output`, extracts magnitude/phase/entropy, computes concept activation, reinforces/creates concepts, connects co-activated concepts.

### Exact emergence coupling points (wave result causes graph change)

- `EthomorphicBridge.update_memory_from_ecwf`:
  - wave-derived activation > 0.2 leads to concept reinforcement/creation and concept-concept edges.
- `MemoryBlock.process`:
  - computes `wave_output = ecwf.compute_ecwf(...)`; calls emergent detector that can add emergent nodes/edges.
- `VerdantSystem._evaluate_candidate_emergence`:
  - computes ECWF sensitivities -> entropy/magnitude checks -> if passed, adds boundary emergent node and edges.

## 4) Resource & Bottleneck Analysis

### Empirical timing signal available in runtime

- `PipelineOrchestrator.run` records per-block wall time into `processing_metrics_section.block_timings`.
- Local sample run (`5` short impulses, default settings) yielded dominant times in:
  - `MemoryStorage` ~11.7 ms
  - `ContinualLearning` ~9.1 ms
  - others sub-ms

### Dominant compute classes

- **NumPy/ECWF hot path**:
  - `compute_ecwf` loops across facets with tensor ops + complex exponentials.
  - `compute_sensitivities` performs baseline ECWF + per-dimension perturbed ECWF runs.
- **Graph hot path**:
  - spreading activation BFS, related retrieval, basin detection/community detection, edge pruning.
- At larger dimensionality/facet counts, ECWF sensitivity loops are primary FLOP hotspot.
- At very large graph size/density, community detection/pruning and repeated graph traversals become wall-clock dominant on the symbolic side.

## 5) Persistence & Truth State

### Save/load findings

- No `latest.json` checkpoint pointer exists in Verdant runtime modules.
- `save_state(path)` writes full system state JSON directly to provided filename.
- Saved state includes:
  - `memory_web` (nodes/edges/store)
  - `bridge` (dimension mappings/history/metrics)
  - `ecwf` full state via `ecwf.to_state_dict()`
  - kings state + thermodynamic/coherence/basin telemetry
- `load_state(path)` restores all above, rewires block references.

### Is Ψ saved?

- Yes. ECWF state is serialized/deserialized via `self.ecwf.to_state_dict()` / `ECWFCore.from_state_dict(...)`.
- Bridge state and concept-dimension mappings are also saved/restored.

### Phase coherence continuity across reboot

- Preserved by restoring ECWF parameters/state, bridge mappings, `t_g`, entropy history, and coherence metrics.
- Additional stochastic continuity handled via optional numpy RNG state restore when present.

## Structural invariants (hard-coded laws)

- Pipeline order is fixed by block list in `VerdantSystem.__init__` and orchestrator execution loop.
- Thermodynamic phase boundaries are fixed:
  - `<0.4 Rigid`, `0.4..0.6 Flexible`, `>0.6 Chaotic`.
- Coherence alpha grid defaults fixed in invariants module unless caller overrides.
- Memory decay lower floor (0.1 stability floor in `MemoryWeb.decay`).
- Activation thresholds fixed in code paths (e.g., bridge activation > 0.2; reinforcement trigger > 0.3).
- Save-state pruning constants fixed (`max_conn=50`, `min_edge_weight=0.01`).
- Basin routing scan hyperparameters clamped to minimum 1 where configured.

## Theatrical gaps (computed but weak/no downstream force)

- `ReasoningBlock._wave_uncertainty` computes adjustments but does not rewrite inference confidences.
- `ThreeKingsCouncil._resolve_confidence` computes consensus and discards result.
- `MemoryBlock` computes `novelty_score` after concept insertion, collapsing novelty toward zero in common paths.
- `LanguageBlock` stores H1 fields in context extra but template backend path does not consume those fields for decision branching.
- `ThermalBridge.get_identity_bias_tokens` computes token weights, but no in-repo generation backend consumes those tokens for logits.
