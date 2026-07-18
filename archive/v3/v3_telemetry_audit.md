# Branch V3 Telemetry Audit (Rigor/Reproducibility)

## Executive summary

Verdant Branch V3 has a solid **run artifact spine** (`cycles.jsonl`, `summary.json`, `state.json`) and enough telemetry for coarse phase/onset, growth, and some branching diagnostics. It is **not yet sufficient for full V2.2-level dynamical-systems rigor** because key per-cycle structural observables are absent (node→basin memberships, per-cycle graph snapshots/deltas, explicit emergent-node creation IDs, and robust lineage/coupling snapshots).

**Verdict:** **V3 needs targeted telemetry upgrades before equivalent rigor.**

---

## A) What already exists and what it currently supports

| Analysis objective | Current support in V3 | Evidence (code-grounded) | Sufficiency judgment |
|---|---|---|---|
| Onset threshold analysis | Per-cycle `cycle_index`, `phase`, `t_g`, `entropy`, `hci`, `emergent_count` in `cycles.jsonl`. | `CycleRecord` schema fields and write path in runner loop. | **Sufficient (baseline level)** |
| Memory/emergent growth analysis | Per-cycle `memory_size`, `emergent_count`; end-state `memory_web.memory_store`. | `CycleRecord` + final `state.json` snapshot via `save_state`. | **Sufficient for count dynamics; weak for causal structure over time** |
| Burst/flux analysis | `phase`, `entropy`, `hci`, intervention markers, density regulation counts, edge ratio before/after. | `CycleRecord` dynamics/intervention fields; `_apply_basin_dynamics`. | **Partially sufficient** |
| Basin persistence analysis | Per-cycle aggregate basin telemetry (`basin_count`, `largest_basin_size`, `self_cluster_basin_id`, `emergent_basins`) and final `extra.last_basins`/`extra.basin_states`. | `_basin_telemetry_from_chunk`, `CycleRecord`, `save_state(extra=...)`. | **Partial; no per-cycle membership snapshots** |
| Branch timing analysis | Per-cycle `bud_events_count`, `bud_parent_basin_id`, `bud_new_basin_id`, `bud_new_basin_size`, plus pressure breakdown. | `_dynamics_telemetry_from_chunk`, `_apply_basin_dynamics`, `CycleRecord`. | **Sufficient for coarse branch timing** |
| Basin genealogy from explicit bud events | Parent/new basin IDs are logged on bud cycles; `basin_states` stores `parent_basin` for budded basin local state. | `maybe_bud_basin` sets `parent_basin`; runner writes bud fields. | **Partial; lacks full branch tree history snapshots** |
| Compression → branch probability | Compression proxies exist (`basin_density_*`, `global_edge_ratio_*`, `density_regulation_edges_removed`) with branch events (`bud_events_count`). | `_apply_basin_dynamics` + `CycleRecord` fields. | **Partially sufficient; missing explicit compression metric per basin per cycle and event-linked dataset** |

---

## B) Missing telemetry for stronger rigor

Requested item -> current status -> gap.

1. **Node→basin assignments per cycle**  
   - **Missing** in `cycles.jsonl`. Only aggregate basin counts/sizes are recorded there.  
   - Basin node lists exist in chunk/state (`basins_section.basins[].nodes`, `extra.last_basins`) but are not persisted per cycle in the run log.

2. **Per-cycle edge list / adjacency**  
   - **Missing** in `cycles.jsonl` and `summary.json`.  
   - Only final graph edges are available in `state.json` (`memory_web.edges`), preventing temporal edge dynamics reconstruction.

3. **Emergent node IDs created per cycle**  
   - **Missing** explicit list per cycle.  
   - Only scalar counts are logged (`emergent_count`, `boundary_emergents_created`), not created node labels.

4. **Parent/source lineage metadata for emergent nodes (per cycle event form)**  
   - **Partially present** in node metadata (`parent_concepts`, `origin`, etc.) in final `state.json`.  
   - **Missing** per-cycle event records linking `created_node_id -> parents -> cycle -> source mechanism`.

5. **Explicit per-cycle cross-basin coupling**  
   - **Missing** quantitative coupling matrix/weights.  
   - Only `boundary_pairs` candidate IDs are logged, without edge-weight flow, cross-basin cut weight, or activation transfer metrics.

6. **Per-cycle community membership snapshots**  
   - **Missing** in durable run artifacts.  
   - Community/basin membership appears in runtime chunk basins section and final state, but not persisted each cycle in `cycles.jsonl`.

---

## C) Brittle/inconsistent structures that complicate automation

1. **Dual run pipelines with divergent schemas** (`cultivation/runner.py` vs `scripts/verdant_llm_cultivator.py`)  
   - One uses `cycle_index`/`emergent_count`; the other uses `cycle`/`emergent_concepts_created`; output filenames and payload structure differ.

2. **Potentially stale basin aggregates in per-cycle logs**  
   - Basins are only rescanned at `basin_scan_interval`; non-scan cycles still log basin aggregates derived from last scan, which can be misread as current-cycle truth.

3. **Final-state-only structural exports for graph/basins**  
   - Analysis scripts (`analysis/*`) mostly consume `state.json` terminal snapshot, limiting longitudinal reproducibility for temporal DAG and genealogy claims.

4. **Telemetry nesting heterogeneity**  
   - Some fields are top-level (`emergent_count`), others nested in `telemetry`, and some in `extra` state payload. This increases parser fragility.

---

## Exact locations to add telemetry hooks (for each missing item)

### 1) Node→basin assignments per cycle
- **Capture source:** `verdant/system.py` after `chunk.update_section("basins_section", ...)` where `basins` already include node lists.  
- **Persist path:** `cultivation/runner.py` in `_run_seed` before constructing `CycleRecord` (extract `basins_section` and write `node_basin_assignments` / `basin_memberships_snapshot` fields).

### 2) Per-cycle edge list/adjacency
- **Capture source:** `cultivation/runner.py` within cycle loop after `system.process_input(...)`.  
- **Implementation option A:** add compact per-cycle edge delta (`added_edges`, `removed_edges`, `rewired_edges`) in `CycleRecord`.  
- **Implementation option B:** write sidecar `graph_deltas.jsonl` from the same loop.
- **Final state remains in:** `verdant/system.py::save_state` + `verdant/memory/persistence.py::save_snapshot`.

### 3) Emergent node IDs created per cycle
- **Capture source:** `verdant/pipeline/blocks/memory.py` (`memory_section` contains `emergent_concepts`) and/or `verdant/system.py::_apply_basin_dynamics` for boundary emergents return values.  
- **Persist path:** `cultivation/runner.py` cycle record creation: add `emergent_node_ids_created` and `boundary_emergent_ids_created`.

### 4) Parent/source lineage metadata (event form)
- **Capture source:**  
  - `ethomorphic/bridge/emergence.py::detect_and_create_emergent_concepts` (has `origin="wave_emergence"`, `parent_concepts`, `combo_key`).  
  - `verdant/system.py::_evaluate_candidate_emergence` (has `origin="boundary_emergence"`, parent basins + parents).  
- **Persist path:** `cultivation/runner.py` add per-cycle `emergent_events` list with `{node_id, source, parent_concepts, parent_basins?, combo_key, creation_time}`.

### 5) Explicit per-cycle cross-basin coupling
- **Capture source:** `verdant/memory/basin_dynamics.py::maybe_propose_boundary_candidates` currently computes overlap and crossing sets.  
- **Persist path:** extend return payload / chunk `basin_dynamics_section` to include numeric coupling statistics per basin pair (e.g., crossing edge count, crossing weight sum, overlap score full table), then write through `cultivation/runner.py`.

### 6) Per-cycle community membership snapshots
- **Capture source:** `verdant/system.py` where `self._last_basins` exists every cycle (with scan freshness flag).  
- **Persist path:** `cultivation/runner.py` add `basin_memberships` with `scanned_this_cycle`; optionally add periodic full snapshots sidecar (`basin_memberships.jsonl`) to keep `cycles.jsonl` compact.

---

## Prioritized checklist (highest value -> lowest)

1. **Add per-cycle emergent event log** (`node_id`, `source`, `parent_concepts`, `cycle`, optional `parent_basins`).
2. **Add per-cycle node→basin membership snapshot** with `scanned_this_cycle` and stable basin IDs.
3. **Add per-cycle graph deltas** (at least emergent↔emergent and cross-basin edge changes).
4. **Add explicit cross-basin coupling metrics per basin pair** (weights/counts/overlap).
5. **Normalize telemetry schema names across pipelines** (`cycle_index` vs `cycle`, `emergent_count` vs `emergent_concepts_created`).
6. **Add machine-readable telemetry schema versioning** in `cycles.jsonl` and `summary.json` for parser stability.
