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
