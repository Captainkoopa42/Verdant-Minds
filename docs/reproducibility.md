# V2 reproducibility and results audit

## Evidence categories

This documentation distinguishes:

- **code-present** — a path exists;
- **test-passing** — an automated assertion passed under the documented import workaround;
- **audit-executed** — this pass ran the command and recorded its result;
- **tracked artifact** — a derived file exists on the branch;
- **manuscript claim** — prose reports a conclusion that may require additional source artifacts;
- **valid interpretation** — the measurement actually tests the stated property.

The final category is where V2's current temporal-scaffolding result fails.

## Software audit

With a temporary `verdant_v2 -> verdant` import alias:

- 125 tests passed;
- a full cycle produced 17 normal sections;
- initialization produced 82 concepts and 294 initial edges;
- a JSON save/load round-trip preserved state, rebound live dependencies, and continued processing;
- two-seed/five-cycle cultivation completed;
- the analysis pipeline generated all expected outputs;
- 20 seeds × 20 cycles completed with the deterministic local provider.

Without the alias, tests fail during import collection and installation instructions fail.

## Tracked results inventory

### Representative directory

`results/20260306T045715Z/` contains derived JSON, CSV, PNG, and PDF files but not its source state. Its metrics report:

| Metric | Value |
| --- | ---: |
| Nodes | 187 |
| Edges | 17,321 |
| Emergent nodes | 62 |
| EE edge rows | 1,830 |
| Serialized older-to-newer share | 1.0 |
| Shuffle-null z | 12.7268 |
| Degree-preserving-null z | 11.8878 |
| Basins | 3 |
| Two-minus-one component BIC | -9,942.17 |

The basin artifact places 61 emergents in one basin, one in another, and none in the third.

### Tracked seed directories

`results/seed_0/` through `results/seed_19/` contain metrics, emergent-edge CSV, and basin JSON. Across those files:

| Metric | Mean | Range |
| --- | ---: | ---: |
| Nodes | 196.35 | 177–220 |
| Edges | 19,179.75 | 15,576–24,090 |
| Emergent nodes | 71.35 | 52–95 |
| EE edge rows | 2,518.55 | 1,326–4,465 |
| Basin count | 3.0 | 2–5 |
| Serialized older-to-newer share | 1.0 | 1.0–1.0 |

These directories do not contain source state or per-seed null outputs, so the paper's cross-seed null aggregate cannot be independently regenerated from the tracked seed folders alone.

## Directionality validity failure

`MemoryWeb` uses `nx.Graph`, an undirected graph. Its state serializer emits:

```python
{"source": u, "target": v, "weight": ...}
```

for each undirected pair. `source` and `target` are serialization positions, not stored causal roles. The analysis nevertheless counts `timestamp[source] < timestamp[target]` as a directed older→newer edge.

The audit performed three direct checks:

1. All ten EE pairs in a generated five-cycle state serialized with the older node first.
2. Swapping the endpoint labels on the identical undirected edge set changed the reported shares from `(1.0, 0.0)` to `(0.0, 1.0)`.
3. Calling `connect("newer", "older")` on a two-node graph serialized as `source="older", target="newer"`.

Therefore the `1.0` share measures node/serialization order, not directed causal scaffolding.

The representative 1,830 EE rows equal exactly \(61 \times 60 / 2\): a complete undirected graph on 61 participating emergent nodes. One of the 62 emergents has no EE edge in that component. A complete undirected association graph is not a directed DAG or a selective lineage spine.

## Parent evidence

Emergent nodes do store `parent_concepts` in metadata. In the audit's five-cycle state, all six emergents listed only seeded concepts as parents; there were zero emergent→emergent parent links even though the serialized association analysis reported ten EE edges.

A corrected lineage analysis should use explicit parent records or newly stored directed events. Co-activation edges can still be studied as undirected topology, density, age assortativity, or temporal proximity.

## Manuscript/result mismatch

Both manuscript layers report a 20-seed panel with emergent count `6.7 ± 3.1` and range `5–14`. The current code, run exactly at 20 cycles with seeds 0–19, local provider, and basin routing, produced:

- emergent mean `23.95`;
- range `18–29`;
- final memory mean `147.55`;
- final `T_g` mean `0.5723`.

This does not reproduce the manuscript count table. The tracked seed directories describe a still larger run scale (52–95 emergents). The exact states and run code behind the manuscript's 5–14 panel are absent.

The two manuscript packages also report conflicting deep-run numbers. See [whitepaper_summary.md](whitepaper_summary.md).

## Null-model repeatability

`analysis/compute_null_models.py` uses Python's global `random` without setting or accepting a seed. Two audit executions on the same state with 20 trials produced different values, including shuffle z-scores of approximately `2.704` and `2.073`.

Future output must record an explicit null seed and preferably save every sampled statistic, not only mean, standard deviation, and z.

## Minimum repair for a publishable temporal result

1. Define the relation: undirected association, temporal precedence, parentage, influence, or causality.
2. Store directed lineage as data at event creation time.
3. Keep association edges separate from lineage edges.
4. Re-run the analysis with endpoint-swap and insertion-order controls.
5. Add a null that preserves node ages, degree, and event opportunity.
6. Seed all randomness and record package/platform versions.
7. Archive source state for every seed plus raw null samples.
8. Regenerate all tables from one scripted aggregation path.
9. Reconcile the manuscript conclusion with the corrected measurement.

This issue does not erase V2's graph growth, emergence mechanism, basin behavior, interventions, coherence instrumentation, or working pipeline. It changes what the current edge-orientation result can legitimately mean.
