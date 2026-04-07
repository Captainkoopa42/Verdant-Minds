# Verdant-Minds V2 — Colab Experiment Cells

Reproducible experiment cells for running Verdant V2 cultivation,
analysis, and intervention experiments in Google Colab.

## Quick Start

Open `Verdant_V2_Replication.ipynb` in Colab for the integrated notebook.

Alternatively, paste individual cells from `cells/` in order.

## Cell Order

| Cell | Purpose | ~Time |
|------|---------|-------|
| 01 | Clone repo, checkout V2 | 10s |
| 02 | Create workspace symlink | 1s |
| 03 | Install ethomorphic + verdant + cultivation + deps | 30s |
| 04 | Run V2 test suite | 30s |
| 05 | Run baseline + ablation + scramble (80 cycles × 20 seeds × 3) | 10min |
| 06 | Compare intervention runs | 30s |
| 07 | Print comparison summary | 1s |
| 08 | Bundle and download all outputs | 10s |
| 09 | Full scaffold analysis + visualization on a state file | 30s |
| 10 | Extract a previously downloaded data bundle | 5s |

## Minimum Viable Replication

1. Run cells 01–04 (setup + tests)
2. Modify cell 05: `--cycles 20 --seeds 0-4` for a fast 5-seed run
3. Run cell 09 on any produced state.json

## Output Structure

```
outputs_baseline/run_<timestamp>/
  seed_N/state.json      # Persisted V2 system state
  seed_N/cycles.jsonl    # Per-cycle telemetry
  seed_N/summary.json    # Run summary metrics
```

## Branch V3 Workflow

For a Colab-ready, ordered V3 regime workflow (quick 80-cycle and long 300-cycle runs, unified analysis pass, and final bundle download), use `colab/V3_Colab_Workflow.md`.
