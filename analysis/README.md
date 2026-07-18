# Analysis Scripts for Temporal Scaffolding

These scripts operate on persisted Verdant state JSON files (example: `verdant_persistent_state.json`).

## Expected output files
- `metrics.json`
- `null_models.json`
- `two_timescale_mixture.json`
- `basins.json`
- `backbone_edges.csv`
- `emergent_edges.csv`
- Figure PNGs/PDFs:
  - `fig_scaffold_directed`
  - `fig_null_distributions`
  - `fig_age_gap_mixture`
  - `fig_access_concentration`
  - `fig_basin_size_distribution`
  - `fig_basin_density_vs_emergent`

## One-command pipeline
```bash
python analysis/run_all.py --state path/to/state.json --orientation older_to_newer
```

## Manual run
```bash
python analysis/extract_scaffolding_metrics.py --state path/to/state.json --outdir results/run1/ --orientation older_to_newer
python analysis/compute_null_models.py --state path/to/state.json --outdir results/run1/ --n 1000 --orientation older_to_newer
python analysis/fit_two_timescale_mixture.py --state path/to/state.json --outdir results/run1/
python analysis/export_backbone_graph.py --state path/to/state.json --outdir results/run1/ --k 6
python analysis/make_figures.py --state path/to/state.json --metrics results/run1/metrics.json --nulls results/run1/null_models.json --mixture results/run1/two_timescale_mixture.json --basins results/run1/basins.json --outdir results/run1/
```

## Basin persistence over time
To capture longitudinal ECWF + concept-graph snapshots during cultivation, run the CLI with a basin snapshot interval:

```bash
python -m cultivation.cli run --cycles 100 --seeds 0-0 --provider local --basin-snapshot-interval 10 --outdir outputs
```

This writes `seed_*/basin_snapshots.jsonl`. You can then analyze basin persistence trajectories with:

```bash
python analysis/basin_persistence_analysis.py --snapshots-jsonl outputs/run_*/seed_0/basin_snapshots.jsonl --outdir outputs/run_*/seed_0/analysis
```

Outputs include:
- `basin_persistence_summary.json`
- `basin_persistence_summary.md`
- `fig_basin_persistence_trajectories.png` (when `matplotlib` is available)


## Quick node/edge count (streaming-aware)
```bash
python analysis/count_graph_size.py --state path/to/state.json
```

The script uses `ijson` when available (true streaming) and falls back to stdlib JSON loading with a warning if `ijson` is missing.

## State schema assumptions
The scripts try multiple field aliases:
- nodes: `nodes`, `concepts`
- edges: `edges`, `relations`, `links`
- node id: `id`, `name`, `key`
- timestamp: `timestamp`, `created_at`, `time`
- edge endpoints: `source/src/from`, `target/dst/to`
- edge weight: `weight`, `w`, default `1.0`
- access counts (optional): `access_count`, `access` (fallback is weighted in-degree)


## Orientation modes
Use `--orientation older_to_newer` (default, Verdant v2 serialization) when edges encode parent→child.
Use `--orientation newer_to_older` only for reverse-orientation comparisons (e.g., legacy v1 analyses).


## Metrics orientation fields
`metrics.json` always includes `older_to_newer_share`, `newer_to_older_share`, `scaffolding_share` (v2 default: older→newer), and backward-compatible `earlier_share` (equal to `scaffolding_share`).

`null_models.json` always includes `observed_older_to_newer_share`, `observed_newer_to_older_share`, and `observed` (equal to `scaffolding_share`).
