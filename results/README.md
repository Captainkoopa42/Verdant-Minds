# Tracked V2 results

This directory contains historical derived outputs from V2 analyses. It does not contain the source state JSON needed to recreate them end to end.

## Representative result

`20260306T045715Z/` contains metrics, null summaries, a mixture fit, basin and backbone exports, emergent-edge CSV, and six figures in PNG and PDF formats.

| Field | Recorded value |
| --- | ---: |
| Nodes | 187 |
| Edges | 17,321 |
| Emergent concepts | 62 |
| Emergent–emergent edges | 1,830 |
| Serialized older-to-newer share | 1.0 |
| Timestamp-shuffle z-score | 12.7268 |
| Degree-preserving z-score | 11.8878 |
| Basins | 3 |
| Largest/core emergent basin | 61 of 62 |
| Two-timescale delta BIC | -9,942.17 |

The 1,830 emergent–emergent edges equal `61 × 60 / 2`, a complete undirected graph among 61 emergent nodes.

## Seed directories

`seed_0/` through `seed_19/` each contain `metrics.json`, `emergent_edges.csv`, and `basins.json`. Across these tracked derived outputs:

- nodes: mean 196.35, range 177–220;
- edges: mean 19,179.75, range 15,576–24,090;
- emergent concepts: mean 71.35, range 52–95;
- emergent–emergent edges: mean 2,518.55, range 1,326–4,465;
- basins: mean 3, range 2–5;
- serialized older-to-newer share: 1.0 for every seed.

These directories are not the manuscript's reported 5–14-emergent panel.

## Interpretation and reproduction limits

The memory graph is undirected, so `source` and `target` in serialized edges are positional labels rather than causal directions. Swapping them changes the reported orientation share without changing the graph. The source states, complete run configuration, environment capture, and per-seed raw null samples are also absent.

Preserve these files as recorded V2 outputs. Do not use them alone as proof of directed lineage or as a fully reproducible run. See [../docs/reproducibility.md](../docs/reproducibility.md).
