# Branch V3 Implementation Plan: Full Experiment-Rigor Readiness

## Phase 1: Minimum rigor patch set (target: V2.2-level rigor on V3)

This phase is the smallest viable code set needed to make V3 support reproducible multi-seed regime studies plus the core dynamical analyses (onset, growth, branching, compression/branch coupling, basin persistence lineage).

---

## 1) Telemetry upgrades (Phase 1)

### 1.1 Add stable schema/version headers in cycle + summary outputs

**Why it matters scientifically**
- Ensures downstream analysis scripts can detect schema drift and fail fast rather than silently mixing incompatible fields across runs/regimes.

**New fields/files**
- `cycles.jsonl` (`CycleRecord`) add:
  - `schema_version: "v3.1"`
  - `regime_label: str`
  - `branch_label: str` (e.g., `v3`)
  - `run_label: str | null`
- `summary.json` (`SessionSummary`) add:
  - `schema_version: "v3.1"`
  - `regime_label`, `branch_label`, `run_label`

**Backward compatibility impact**
- Backward compatible: only additive fields. Older consumers ignoring unknown fields continue to work.

**Exact file/function edit targets**
- `cultivation/schemas.py` (`CycleRecord`, `SessionSummary`)
- `cultivation/runner.py::_run_seed` (populate fields)
- `cultivation/cli.py::main` (accept new labels)

---

### 1.2 Add per-cycle emergent event ledger for lineage/genealogy

**Why it matters scientifically**
- Required to reconstruct causal lineage DAG over time (created node IDs, parents, mechanism), instead of inferring from final state only.

**New fields/files**
- `cycles.jsonl` add:
  - `emergent_node_ids_created: list[str]`
  - `emergent_events: list[{
      "node_id": str,
      "source": "wave_emergence"|"boundary_emergence"|"other",
      "parent_concepts": list[str],
      "parent_basins": list[str] | null,
      "combo_key": str | null,
      "creation_time": float | null
    }]`

**Backward compatibility impact**
- Additive only. Existing pipelines still parse older fields.

**Exact file/function edit targets**
- `cultivation/schemas.py::CycleRecord`
- `verdant/pipeline/blocks/memory.py` (capture created emergent IDs from `memory_section.emergent_concepts`)
- `verdant/system.py::_evaluate_candidate_emergence` (return or register event payloads)
- `cultivation/runner.py::_run_seed` (assemble and persist per-cycle event list)

---

### 1.3 Add per-cycle basin membership snapshots + scan freshness

**Why it matters scientifically**
- Basin persistence and genealogy claims require node→basin assignments over time, not just aggregate basin counts.

**New fields/files**
- `cycles.jsonl` add:
  - `basin_memberships_snapshot: {
      "scanned_this_cycle": bool,
      "basin_ids": list[str],
      "node_to_basin": dict[str, str],
      "basin_sizes": dict[str, int]
    }`

**Backward compatibility impact**
- Additive; can be optional (`null`) to keep file size manageable if gated by flag.

**Exact file/function edit targets**
- `verdant/system.py` (existing `basins_section` already has basins + `scanned_this_cycle`)
- `cultivation/runner.py::_run_seed` (extract `basins_section`, normalize membership map)
- `cultivation/schemas.py::CycleRecord`

---

### 1.4 Add per-cycle graph delta telemetry (not full adjacency dump)

**Why it matters scientifically**
- Enables flux/burst/branch dynamics and scaffold evolution analysis without huge storage overhead.

**New fields/files**
- `cycles.jsonl` add:
  - `graph_delta: {
      "nodes_added": list[str],
      "nodes_removed": list[str],
      "edges_added": list[[str,str]],
      "edges_removed": list[[str,str]],
      "ee_edges_added": int,
      "ee_edges_removed": int,
      "cross_basin_edges_added": int,
      "cross_basin_edges_removed": int
    }`

**Backward compatibility impact**
- Additive. If disabled, can emit empty/default delta.

**Exact file/function edit targets**
- `cultivation/runner.py::_run_seed` (track previous cycle node/edge sets and compute deltas)
- `cultivation/schemas.py::CycleRecord`

---

### 1.5 Expand branch/compression telemetry to event-conditioned analysis

**Why it matters scientifically**
- Compression→branch probability and largest-basin-around-branch are key dynamic claims and need explicit per-cycle covariates.

**New fields/files**
- `cycles.jsonl` add:
  - `branch_event: bool` (derived from `bud_events_count > 0`)
  - `largest_basin_size` already exists; keep
  - `compression_metrics: {
      "global_edge_ratio_before": float,
      "global_edge_ratio_after": float,
      "density_regulation_edges_removed": int,
      "mean_basin_pressure": float,
      "max_basin_pressure": float
    }`

**Backward compatibility impact**
- Mostly aliases/derived from existing fields + additive nested summary, safe for existing readers.

**Exact file/function edit targets**
- `cultivation/runner.py::_run_seed` (derive extra compression summaries)
- `cultivation/schemas.py::CycleRecord`

---

## 2) Packaging upgrades (Phase 1)

### 2.1 Add run manifest for multi-seed/regime reproducibility

**Why it matters scientifically**
- Enables exact cohort reconstruction for cross-seed/regime comparisons; prevents ambiguous provenance.

**New fields/files**
- `run_dir/manifest.json`:
  - `manifest_version`
  - `created_utc`
  - `branch_label`, `regime_label`, `run_label`
  - `seed_spec`, `seed_list`
  - full runner config snapshot
  - `git`: `commit`, `branch`, `dirty`
  - relative artifact index for each seed (`cycles.jsonl`, `summary.json`, `state.json`)

**Backward compatibility impact**
- New file only; no breakage.

**Exact file/function edit targets**
- `cultivation/runner.py::run`
- new helper module `cultivation/packaging.py` (git metadata + checksums)
- `cultivation/cli.py::main` (label args)

---

### 2.2 Add seed-level metadata sidecar

**Why it matters scientifically**
- Allows seed-level validation and easier exclusion/reporting when failures occur.

**New fields/files**
- `seed_<n>/metadata.json`:
  - seed, start/end time, duration, status, error (if any), checksums for seed artifacts.

**Backward compatibility impact**
- New optional file only.

**Exact file/function edit targets**
- `cultivation/runner.py::_run_seed`
- `cultivation/packaging.py`

---

## 3) Analysis/plot upgrades (Phase 1)

### 3.1 Add unified multi-run analysis entrypoint for minimum rigor figures

**Why it matters scientifically**
- Current analysis is single-state. V2.2-level claims require multi-seed trajectory comparisons across regimes.

**New fields/files**
- New script: `analysis/paper_figures.py` (minimum version)
- New outputs:
  - `fig_01_memory_growth_by_regime.(png|pdf)` + paired CSV
  - `fig_02_emergent_growth_by_regime.(png|pdf)` + CSV
  - `fig_03_basin_persistence_over_time.(png|pdf)` + CSV
  - `fig_04_branch_timeline.(png|pdf)` + CSV
  - `fig_05_compression_vs_branch_probability.(png|pdf)` + CSV
  - `fig_06_largest_basin_around_branch_events.(png|pdf)` + CSV
  - `fig_08_regime_phase_map.(png|pdf)` + CSV
  - `fig_09_onset_threshold_comparison.(png|pdf)` + CSV

**Backward compatibility impact**
- No change to existing scripts; additive new pipeline.

**Exact file/function edit targets**
- new `analysis/paper_figures.py`
- new `analysis/lib/load_runs.py` (load manifests + cycles)
- new `analysis/lib/metrics.py` (onset, event windows, probability bins)
- new `analysis/lib/plots.py` (renderers)
- `analysis/README.md` add usage section

---

## Phase 2: Paper-ready patch set (reviewer-friendly, bundleable)

This phase adds publication ergonomics and reviewer handoff integrity on top of Phase 1.

---

## 1) Telemetry upgrades (Phase 2)

### 1.1 Add cross-basin coupling table snapshots

**Why it matters scientifically**
- Strengthens boundary emergence and cross-basin interaction claims beyond pair IDs.

**New fields/files**
- `cycles.jsonl` add `cross_basin_coupling: list[{basin_a, basin_b, crossing_edge_count, crossing_weight_sum, overlap_score}]`.

**Backward compatibility impact**
- Additive; can be optionally emitted if computation budget limited.

**Exact file/function edit targets**
- `verdant/memory/basin_dynamics.py::maybe_propose_boundary_candidates`
- `verdant/system.py::_apply_basin_dynamics` (store richer coupling)
- `cultivation/runner.py::_run_seed`
- `cultivation/schemas.py::CycleRecord`

---

### 1.2 Add burst event canonicalization

**Why it matters scientifically**
- Heavy-tail/burst claims should not depend on ad hoc post-hoc definitions.

**New fields/files**
- `cycles.jsonl` add:
  - `burst_size_emergent_delta`
  - `burst_size_memory_delta`
  - optional `is_burst_event` under fixed thresholding rule metadata.

**Backward compatibility impact**
- Additive.

**Exact file/function edit targets**
- `cultivation/runner.py::_run_seed`
- `cultivation/schemas.py::CycleRecord`

---

## 2) Packaging upgrades (Phase 2)

### 2.1 Bundle builder script + bundle manifest

**Why it matters scientifically**
- Reviewer should receive one archive with provenance, checksums, and exact figure table linkage.

**New fields/files**
- New script: `analysis/package_run_bundle.py` (or `scripts/package_experiment_bundle.py`)
- Output archive + `bundle_manifest.json` containing:
  - included runs/manifests/figures/tables,
  - checksums,
  - generation command and git stamp.

**Backward compatibility impact**
- Additive tooling.

**Exact file/function edit targets**
- new `analysis/package_run_bundle.py`
- update `colab/cells/08_bundle_download.py` to call script instead of ad hoc zip logic

---

### 2.2 Deterministic paper export contract

**Why it matters scientifically**
- Ensures byte-level stable naming and complete traceability for paper revisions.

**New fields/files**
- `paper_outputs/<package_id>/figure_manifest.json`
- deterministic naming convention `fig_XX_<slug>.png/pdf` and `table_XX_<slug>.csv`.

**Backward compatibility impact**
- Additive.

**Exact file/function edit targets**
- `analysis/paper_figures.py`
- new `analysis/lib/export.py`

---

## 3) Analysis/plot upgrades (Phase 2)

### 3.1 Complete the full 10-paper-figure suite

**Why it matters scientifically**
- Achieves fully automated publication package for all declared main claims.

**New fields/files**
- Add remaining figures:
  - `fig_07_burst_ccdf_heavytail_comparison`
  - `fig_10_genealogy_lineage_summary` (if lineage telemetry present; else explicit downgraded placeholder with warning manifest entry).

**Backward compatibility impact**
- Additive; fail-fast/warn behavior for missing lineage fields.

**Exact file/function edit targets**
- `analysis/paper_figures.py`
- `analysis/lib/metrics.py` (CCDF + power-law/alternative fit summaries)
- `analysis/lib/plots.py`

---

## Exact file/function edit targets (consolidated)

### Telemetry
- `cultivation/schemas.py`
  - expand `CycleRecord` and `SessionSummary` with schema/provenance/lineage/delta fields.
- `cultivation/cli.py::main`
  - add `--regime-label`, `--run-label`, `--branch-label`.
- `cultivation/runner.py::run`
  - write run `manifest.json`.
- `cultivation/runner.py::_run_seed`
  - emit new cycle telemetry fields, seed `metadata.json`, and graph deltas.
- `verdant/system.py::_apply_basin_dynamics`
  - expose richer cross-basin coupling telemetry.
- `verdant/system.py::_evaluate_candidate_emergence`
  - expose boundary emergence event payloads for per-cycle ledger.
- `verdant/pipeline/blocks/memory.py`
  - expose wave-emergence created node IDs/events to runner context.
- `verdant/memory/basin_dynamics.py::maybe_propose_boundary_candidates`
  - compute and return explicit coupling metrics.

### Packaging
- new `cultivation/packaging.py`
  - git stamp + checksum helpers.
- new `analysis/package_run_bundle.py` (or `scripts/package_experiment_bundle.py`)
  - reproducible archive + bundle manifest.
- `colab/cells/08_bundle_download.py`
  - migrate to bundle script invocation.

### Analysis/plot
- new `analysis/paper_figures.py`
- new `analysis/lib/load_runs.py`
- new `analysis/lib/metrics.py`
- new `analysis/lib/plots.py`
- new `analysis/lib/export.py`
- `analysis/README.md`
  - add paper pipeline docs.

---

## Recommended implementation order (final checklist)

1. **Schema/version + labels first**: extend `CycleRecord`/`SessionSummary`, add CLI labels, ensure additive compatibility.
2. **Run manifest + seed metadata**: implement `manifest.json` and `seed metadata.json` with git/provenance/checksums.
3. **Lineage/event telemetry**: add emergent event ledger and created-node IDs to per-cycle records.
4. **Basin membership + graph deltas**: add per-cycle `basin_memberships_snapshot` and `graph_delta`.
5. **Minimum paper analysis pipeline**: implement `analysis/paper_figures.py` for figures 1–6, 8, 9 with paired CSVs.
6. **Compression/branch probability + onset table validation tests**: add tests for derived metrics determinism.
7. **Cross-basin coupling enrichment**: extend basin dynamics and include in cycles telemetry.
8. **Burst CCDF + genealogy figure completion**: implement figures 7 and 10 with fail-fast guards.
9. **Bundle tooling**: add reproducible bundle script + `bundle_manifest.json` and wire Colab helper to it.
10. **Documentation + CI smoke**: update `analysis/README.md`; add integration smoke test that runs pipeline from manifest and verifies expected figures/tables.

---

## Notes on backward compatibility policy

- All telemetry/schema changes above are designed as **additive** fields where possible.
- Existing `cycles.jsonl`, `summary.json`, `state.json` readers should continue to operate if they ignore unknown fields.
- New analysis pipeline should support:
  - strict mode: require `schema_version >= v3.1`,
  - compatibility mode: degrade gracefully and skip figures requiring missing fields (with explicit warnings logged into `figure_manifest.json`).
