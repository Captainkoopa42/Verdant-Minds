# V2 implementation and evidence status

This table reports what is present and what was directly verified on the current `V2` branch.

| Area | Status | Evidence or limitation |
| --- | --- | --- |
| V2 source implementation | Substantial | `verdant/`, `ethomorphic/`, and `cultivation/` contain the active V2 system. |
| Clean-checkout import | Broken | Source imports `verdant_v2`; the tracked directory is `verdant`. |
| Root installation | Broken | Root packaging targets an absent `usm` package and stale console commands. |
| Subpackage installation | Broken | Both package-local configurations search for nested packages that are not present. |
| Tests as checked out | Collection failure | Thirteen modules fail to import because `verdant_v2` is absent. |
| Tests with import alias | Passing | All 125 tests pass using a temporary `verdant_v2 -> verdant` import alias. |
| Nine-stage pipeline | Working under alias | A real input produced 17 sections including memory, wave, governance, coherence, and basin telemetry. |
| Default initialization | Working | Creates 82 seeded concepts, 294 initial edges, and 82 bridge mappings. |
| Emergent-concept generation | Working | Direct and cultivation cycles created emergent nodes. |
| Three Kings governance | Working on tested paths | Unit and integration coverage passes. |
| Basin detection/routing | Working on tested paths | Basin, micro-pipeline, arbitration, and telemetry tests pass. |
| Interventions | Working on tested paths | Oldest-node ablation, edge scrambling, and comparison flow are tested. |
| JSON persistence | Working | Save/load preserved state and correctly rebound the memory block, learning block, and pipeline to restored objects. |
| Local cultivation | Working under alias | Two-seed smoke and 20-seed audit runs completed. |
| Hosted cultivation | Not audited | Requires external SDKs, credentials, and changing provider output. |
| Analysis pipeline | Executes | Metrics, nulls, mixture output, backbone CSV, and six figure pairs were generated in audit. |
| Null-model repeatability | Incomplete | `random` is not seeded or exposed as a CLI option; repeated runs gave different null means/z-scores. |
| Temporal direction result | Not valid as directed evidence | The source graph is undirected, but serializer endpoint order is analyzed as source→target direction. |
| Tracked representative results | Internally readable | The deep-run JSON/CSV figures support their recorded values, subject to the directionality flaw. |
| Tracked 20-seed artifacts | Partial | Per-seed metrics/edges/basins exist; source states and per-seed null distributions do not. |
| Paper replication table | Not reproduced | Present code at 20 cycles/20 seeds produced 18–29 emergents, not the paper's 5–14. |
| Paper packages | Conflicting | The earlier `paper/` draft and later standalone paper report different deep-run values. |
| Colab notebooks | Broken | Installation paths are wrong; the quickstart calls an absent analysis module. |
| Root scripts | Mostly obsolete | Most import the absent V1-style `usm` API. |

## Audit execution results

Using the import alias documented in [INSTALL.md](INSTALL.md):

- 125/125 tests passed;
- tracked Python outside notebook-cell fragments compiled;
- a two-seed, five-cycle cultivation run completed;
- the full analysis pipeline completed on its state output;
- a 20-seed, 20-cycle local-provider run completed;
- persistence restored 83 concepts and one emergent node, then completed another full cycle.

The audit's 20-seed run produced:

| Metric | Observed |
| --- | ---: |
| Emergent count | mean `23.95`, range `18–29` |
| Final memory size | mean `147.55`, range `142–154` |
| Final `T_g` | mean `0.5723`, range `0.5627–0.5830` |
| Serialized older-to-newer share | `1.0` for all 20 seeds |

That final row is expected from current undirected serialization order and is not independent confirmation of causal lineage.

## Highest-priority engineering work

1. Make package directories and metadata agree on `verdant_v2`, `ethomorphic`, and `cultivation`.
2. Replace or remove the stale root `usm` packaging and old scripts.
3. Decide whether conceptual relations are undirected associations or directed lineage, then store that distinction explicitly.
4. Rebuild direction-sensitive analysis from directed event/parent records rather than endpoint order.
5. Add explicit RNG seeds to bridge mappings, emergence mapping, and null-model analysis.
6. Attach exact source states and per-seed null outputs to every aggregate claim.
7. Reconcile the two manuscript packages and the run scale each describes.
8. Repair both Colab notebooks only after the package layout is canonical.
