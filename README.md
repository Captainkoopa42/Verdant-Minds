# Verdant-Minds — V2

V2 is the Verdant research generation centered on a persistent concept graph, ECWF-inspired numerical dynamics, a nine-stage processing pipeline, Three Kings governance, coherence measurements, thermodynamic phase tracking, basin detection/routing, cultivation experiments, and temporal-scaffolding analysis.

The underlying V2 implementation is substantial: with the intended package name made importable, all 125 tests pass, cultivation runs complete, JSON state round-trips, and the analysis pipeline generates metrics and figures. The branch currently has a packaging/layout defect that prevents those paths from working directly after checkout. The exact defect and a non-destructive local workaround are in [INSTALL.md](INSTALL.md).

## Start here

- [Current implementation and evidence status](STATUS.md)
- [Install/work around the package-layout defect](INSTALL.md)
- [Run the tests and experiments](TESTING.md)
- [Architecture map](docs/architecture.md)
- [End-to-end walkthrough](docs/walkthrough.md)
- [Python interface reference](docs/api.md)
- [Results and reproducibility audit](docs/reproducibility.md)
- [How the V2 layers fit together](docs/branch-history.md)

## What V2 implements

- `VerdantSystem` and `VerdantConfig` orchestration.
- An 82-concept initialized graph with 294 initial edges.
- A nine-stage chunk pipeline with three governance checkpoints and council arbitration.
- An `ethomorphic` ECWF core and graph-independent memory bridge protocol.
- Coherence invariants: triangle validity, estimated critical alpha, violation rate, and HCI.
- Dynamic `T_g` and rigid/flexible/chaotic phase labels.
- Emergent-concept creation from wave magnitude and concept activation.
- Basin detection, optional basin micro-pipelines, and proposal arbitration.
- JSON persistence with live-object rebinding after load.
- Deterministic local cultivation plus optional hosted-provider adapters.
- Node/edge interventions and comparison tooling.
- State analysis, null models, mixture fitting, backbone export, and figures.

## Central results caveat

The tracked result files contain real numerical outputs, including a representative run with 187 nodes, 62 emergent nodes, 1,830 analyzed emergent-to-emergent edges, an older-to-newer share of `1.0`, and reported null-model z-scores of `12.73` and `11.89`.

However, `MemoryWeb` stores those relations in an undirected `networkx.Graph`. Its serializer writes each undirected pair using the graph's node iteration order, while the analysis treats the first endpoint as `source` and the second as `target`. In an audit experiment, reversing only those endpoint labels changed the same graph's reported share from `1.0` to `0.0`. The 1,830 edges are exactly the complete undirected graph on 61 nodes; they do not by themselves establish a directed causal spine.

The temporal-ordering statistic must therefore be treated as a serialization-order result until V2 records real directed lineage or derives direction from explicit parent metadata. See [docs/reproducibility.md](docs/reproducibility.md).

## Repository map

| Path | Role | Current status |
| --- | --- | --- |
| `verdant/` | V2 orchestrator, graph, blocks, governance, phases | Implemented, but directory/package name mismatched |
| `ethomorphic/` | ECWF, bridge, emergence, coherence, ethics | Implemented; editable package metadata is mislocated |
| `cultivation/` | Multi-seed runner and providers | Works through import workaround; package path is hard-coded |
| `tests_v2/` | 125 unit and integration tests | Pass under import workaround |
| `analysis/` | State analysis and figure generation | Executes; directional assumption and unseeded null randomness require caution |
| `results/` | Tracked deep-run and 20-seed derived artifacts | Does not contain source states or per-seed null outputs |
| `colab/` | Two notebooks plus notebook-cell fragments | Currently broken by package/path mismatches |
| `paper/` | Earlier draft manuscript package | Conflicts numerically with the later standalone paper |
| `Emergent Temporal Scaffolding.../` | Later paper, PDF, figures, and results bundle | Preserved research artifact; directional conclusion needs correction |
| `scripts/` | Older interactive/cultivation utilities | Most import the absent `usm` package and do not run on V2 |

## Quick implementation inspection

After applying the local import workaround from [INSTALL.md](INSTALL.md):

```bash
python - <<'PY'
from verdant_v2.system import VerdantSystem

system = VerdantSystem()
chunk = system.process_input("How does memory support ethical reasoning?")
print(sorted(chunk.sections))
print(system.get_metrics())
PY
```

## Branch interpretation

`V2` is a browsable research generation, not a claim that every present artifact came from one moment or one experiment. The branch currently contains the runnable V2 core, later basin/intervention work, older `usm` scripts, two manuscript layers, derived outputs from different run scales, and newer Colab material. [docs/branch-history.md](docs/branch-history.md) maps those layers directly inside the branch.

## License

Code and repository materials are provided under the [MIT License](LICENSE), subject to any separately stated terms inside external archived artifacts.
