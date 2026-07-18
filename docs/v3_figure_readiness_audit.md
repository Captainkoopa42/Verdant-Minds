# Branch V3 Audit: Automated Paper-Ready Plot & Figure Generation

## Figure readiness matrix

Legend: **Ready** = directly reproducible from existing automated scripts and V3 outputs; **Partial** = telemetry exists but no first-class automated figure pipeline for requested claim; **Blocked** = missing telemetry and/or schema/packaging prevents robust automation.

| # | Required figure | Readiness | What exists now | Primary blocker type |
|---|---|---|---|---|
| 1 | Memory growth by regime | **Partial** | `cycles.jsonl` includes per-cycle `memory_size`; multi-seed runs exist. | Missing analysis logic + packaging/manifesting for regime grouping. |
| 2 | Emergent growth by regime | **Partial** | `cycles.jsonl` includes per-cycle `emergent_count`. | Missing analysis logic + packaging/manifesting for regime grouping. |
| 3 | Basin persistence over time | **Partial/Weak** | Per-cycle aggregate basin fields (`basin_count`, `largest_basin_size`) exist. | Missing telemetry (per-cycle basin memberships/IDs persistence snapshots). |
| 4 | Branch timeline | **Partial** | Per-cycle bud telemetry (`bud_events_count`, parent/new basin IDs) exists. | Missing analysis logic and plot script. |
| 5 | Compression vs branch probability | **Partial** | Compression proxies (`basin_density_*`, `global_edge_ratio_*`, density regulation) + branch fields exist. | Missing analysis logic (event-conditioned model/plot). |
| 6 | Largest basin around branch events | **Partial** | `largest_basin_size` + bud event cycle markers in same cycle record. | Missing analysis logic (event-window extraction + aggregate CI plot). |
| 7 | Burst-size CCDF / heavy-tail comparison | **Partial/Weak** | Can derive burst increments from per-cycle counts (e.g., Δ emergent_count). | Missing analysis logic; no standardized burst definition/output table. |
| 8 | Regime phase map | **Partial** | Per-cycle phase labels and `t_g`/entropy/HCI available. | Missing analysis logic for regime heatmap/state occupancy plots. |
| 9 | Onset threshold comparison across seeds/regimes | **Partial** | Onset proxies derivable from per-cycle trajectories across seeds. | Missing analysis logic + packaging metadata for reliable regime/branch comparison. |
| 10 | Genealogy/lineage summary | **Blocked** | Final state stores emergent metadata (`origin`, `parent_concepts`), and branch IDs on bud cycles. | Missing telemetry (no per-cycle emergent event lineage stream) + missing analysis logic. |

---

## What is already automated today

Current automated figure generation is centered on `analysis/run_all.py` -> `analysis/make_figures.py` and is **state-centric** (single `state.json`) rather than run/regime-centric.

Generated figure families today:
- `fig_scaffold_directed`
- `fig_null_distributions`
- `fig_age_gap_mixture`
- `fig_access_concentration`
- `fig_basin_size_distribution`
- `fig_basin_density_vs_emergent`

These are useful but do not cover the requested paper figure set focused on cycle dynamics and regime comparisons.

---

## Blockers by figure (strict)

### 1) Memory growth by regime
- **Blocker:** Missing automated multi-run/regime aggregation logic.
- **Why:** `analysis/run_all.py` accepts one `--state`; it does not consume run directories or seed cohorts.

### 2) Emergent growth by regime
- **Blocker:** Missing automated cohort plotting logic.
- **Why:** per-cycle telemetry exists, but no script computes seed-wise trajectories + regime means/uncertainty bands.

### 3) Basin persistence over time
- **Blocker:** Missing telemetry + analysis.
- **Why:** available cycle fields are aggregate counts/sizes, not per-cycle node→basin assignments and basin identity continuity snapshots.

### 4) Branch timeline
- **Blocker:** Missing analysis logic.
- **Why:** telemetry already records bud events and parent/new IDs, but no script materializes a branch timeline chart.

### 5) Compression vs branch probability
- **Blocker:** Missing analysis logic.
- **Why:** proxies exist but no event-conditioned table/model (e.g., logistic branch probability by compression bins).

### 6) Largest basin around branch events
- **Blocker:** Missing analysis logic.
- **Why:** event markers and basin size exist, but no windowed extraction/aggregation around branch cycles.

### 7) Burst-size CCDF / heavy-tail
- **Blocker:** Missing analysis logic + explicit burst schema.
- **Why:** derivation possible from deltas, but there is no canonical burst definition, fit procedure, or CSV output.

### 8) Regime phase map
- **Blocker:** Missing analysis logic.
- **Why:** phase and thermodynamic fields exist, but no occupancy map/transition matrix plotting script.

### 9) Onset threshold comparison across seeds/regimes
- **Blocker:** Missing analysis logic + packaging metadata.
- **Why:** onset requires consistent run/regime labeling and cohort aggregation; no run manifest/regime labels today.

### 10) Genealogy/lineage summary
- **Blocker:** Missing telemetry (primary) and analysis.
- **Why:** there is no per-cycle emergent-event ledger with created node IDs, parents, source mechanism, and cycle stamp for robust genealogy reconstruction.

---

## Exact improvements for publication-quality outputs

### A. Plot labeling / legends / titles

1. Add a shared style helper (e.g., `analysis/plot_style.py`) with:
   - consistent font sizes, color palette, line widths,
   - standardized axis labels and title templates including regime, seed-count, cycles, and commit short SHA.
2. Replace ambiguous labels (`earlier_share`) with explicit scientific labels (`older_to_newer_share`, `scaffolding_share`) in null plots.
3. Require legend entries to include `n_seeds`, CI definition (e.g., 95% bootstrap CI), and regime label.

### B. Export resolution and deterministic naming

1. Raise default PNG dpi from 220 to 300 (or 600 for line art option).
2. Keep deterministic base filenames per figure (`fig_01_memory_growth_by_regime.png`, etc.).
3. Avoid timestamp-only analysis folders for paper artifacts; include run/regime/manifest identifiers.

### C. CSV tables paired with each plot

For every plotted figure, emit a machine-readable table in `tables/`:
- `fig_01_memory_growth_by_regime.csv`
- `fig_02_emergent_growth_by_regime.csv`
- ...
- `fig_07_burst_ccdf.csv` (+ optional fit summary JSON)

Each CSV should include: `regime`, `seed`, `cycle`, `value`, plus aggregation fields where relevant (`mean`, `ci_low`, `ci_high`).

### D. Deterministic reproducibility metadata in figure outputs

Embed `figure_manifest.json` containing:
- source run manifest references,
- script version + git commit,
- CLI args,
- generated file checksums.

---

## Exact code changes needed (file/function level)

### 1) Unify run metadata needed for figure automation
- **`cultivation/cli.py::main`**
  - add `--regime-label`, `--run-label`, `--branch-label`.
- **`cultivation/runner.py::RunnerConfig`**
  - add metadata fields for labels + schema version strings.
- **`cultivation/runner.py::run`**
  - write run-root `manifest.json` with seed list, config, git metadata, artifact index.
- **`cultivation/schemas.py::SessionSummary`**
  - add provenance fields (commit, branch, regime, schema_version).

### 2) Add missing telemetry for lineage-grade figures
- **`cultivation/schemas.py::CycleRecord`**
  - add fields for `emergent_node_ids_created`, `emergent_events` (source/parents/cycle), optional `basin_memberships_snapshot`.
- **`cultivation/runner.py::_run_seed`**
  - capture and persist these fields per cycle.
- **`verdant/system.py::_evaluate_candidate_emergence` and emergence call sites**
  - expose created node IDs/events to runner pipeline in cycle context.

### 3) Build unified paper plot pipeline
- Add **`analysis/paper_figures.py`** (single orchestrator):
  - input: one or more run manifests
  - output: `paper_figures/<package_id>/figures/*` + `tables/*` + `figure_manifest.json`
  - generates all 10 requested figures with deterministic naming.
- Add **`analysis/lib/load_runs.py`**:
  - robust loader for run manifests, seed summaries, and cycles.
- Add **`analysis/lib/metrics.py`**:
  - onset extraction, branch windows, burst extraction, compression-bin branch probability.
- Add **`analysis/lib/plots.py`**:
  - style-safe plotting functions returning `(fig, dataframe)`.

### 4) Keep current scripts but re-scope them
- Keep `analysis/run_all.py` for single-state scaffold diagnostics.
- Position `analysis/paper_figures.py` as the primary publication pipeline.
- Update `analysis/README.md` with a “paper package” section and exact CLI examples.

---

## Recommended unified plot pipeline

## Proposed directory layout

```
analysis/
  paper_figures.py              # top-level orchestration for all paper figures
  lib/
    load_runs.py                # manifest + cycles/summary loaders
    metrics.py                  # derived metrics / event extraction
    plots.py                    # plotting primitives, legends, titles
    export.py                   # csv + png/pdf + manifest writers
  plot_style.py                 # shared style constants
```

## Proposed CLI

```bash
python analysis/paper_figures.py \
  --runs manifests/baseline.json manifests/p6style.json manifests/phase7.json \
  --outdir paper_outputs/v3_main \
  --dpi 300 \
  --format png,pdf
```

## Pipeline stages

1. **Load** run manifests and validate schema versions.
2. **Normalize** cycle records into long-form tables.
3. **Compute** derived metrics for all required claims.
4. **Render** standardized figures + paired CSVs.
5. **Emit** `figure_manifest.json` with provenance + checksums.

## Fail-fast guards

- Abort on missing required cycle fields for a requested figure.
- Abort on mixed schema versions without migration map.
- Warn clearly when genealogy figure is downgraded due to missing lineage telemetry.

---

## Bottom line

V3 can already auto-generate a useful subset of scaffold diagnostics, but it **cannot yet automatically produce the full publication figure set** for the listed dynamical claims in a robust, reviewer-ready way. The main gap is a **run/regime-level unified plotting pipeline** plus **targeted lineage/persistence telemetry upgrades**.
