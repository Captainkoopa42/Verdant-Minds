# V2 analysis pipeline

This directory analyzes a persisted Verdant V2 state. It does not execute the cognitive pipeline or create a state itself.

## Entry point

From the repository root, after applying the import workaround in [../INSTALL.md](../INSTALL.md):

```bash
python analysis/run_all.py \
  --state path/to/state.json \
  --results-root results \
  --n-nulls 1000 \
  --k 6 \
  --orientation older_to_newer
```

`run_all.py` creates a timestamped directory and invokes the scripts below.

| Script | Output or role |
| --- | --- |
| `extract_scaffolding_metrics.py` | Graph counts, emergent-edge table, endpoint-orientation shares, basin summary |
| `compute_null_models.py` | Timestamp-shuffle and degree-preserving null distributions |
| `fit_two_timescale_mixture.py` | One- versus two-component age-gap fit |
| `export_backbone_graph.py` | Top-k emergent-neighbor edge export |
| `make_figures.py` | PNG and PDF figures from state and derived JSON/CSV files |
| `compare_intervention_runs.py` | Comparison of cultivation output directories |

## Critical interpretation limit

`verdant_v2.memory.MemoryWeb` stores its primary memory as a NetworkX `Graph`, which is undirected. The state serializer nevertheless writes each edge using the positional field names `source` and `target`. The analysis scripts interpret those positions as a direction.

That makes the reported `older_to_newer_share` and `newer_to_older_share` dependent on undirected endpoint serialization order. Reversing the two endpoint labels changes the shares without changing the graph. These fields are therefore not valid evidence of causal or directed temporal lineage in the current V2 representation.

Use `parent_concepts` metadata for recorded emergence parents, or add a separate directed lineage-event representation before testing directional lineage claims. See [../docs/reproducibility.md](../docs/reproducibility.md).

## Randomness limit

`compute_null_models.py` currently uses Python's global `random` module without a CLI seed. Repeated runs on the same state can produce different z-scores. Archive the state, raw null samples, software environment, parameters, and an explicit RNG seed for any result intended for comparison or publication.

## Tracked outputs

The repository includes derived outputs under [../results](../results), but the source state is not tracked with those result sets. They are historical evidence, not fully self-contained reproductions.
