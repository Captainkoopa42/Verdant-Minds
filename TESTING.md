# Testing and validating V2

## Important setup condition

The branch does not expose its source as `verdant_v2` even though all V2 imports use that name. Apply the local import alias in [INSTALL.md](INSTALL.md) before running tests.

## Full V2 suite

```bash
python -m pytest tests_v2 -q
```

The suite contains 125 tests:

| Area | Tests |
| --- | ---: |
| Basin micro-pipeline | 1 |
| Basin telemetry | 2 |
| Colab-style smoke | 1 |
| Cultivation cycle | 8 |
| Cultivation runner | 1 |
| Full pipeline | 8 |
| Scaffold intervention flow | 1 |
| Basin detection | 1 |
| Bridge | 12 |
| Cognitive chunk | 12 |
| Coherence | 12 |
| ECWF | 19 |
| Governance | 9 |
| Interventions | 4 |
| Memory | 21 |
| Thermodynamic phase | 13 |

During this audit, all 125 passed with the import alias. Without it, collection fails before tests run.

## Compilation

```bash
python -m compileall -q ethomorphic verdant cultivation analysis scripts tests_v2
```

Files under `colab/cells/` are notebook-cell fragments containing `%%bash`; their `.py` extension does not make them standalone Python modules, so they are excluded from this compilation check.

## Small cultivation smoke

```bash
python -m cultivation.cli run \
  --cycles 5 \
  --provider local \
  --seeds 0-1 \
  --basin-routing \
  --outdir smoke_output
```

Expected per-seed files:

- `state.json`
- `cycles.jsonl`
- `summary.json`

## Analysis smoke

```bash
python analysis/run_all.py \
  --state smoke_output/run_<timestamp>/seed_0/state.json \
  --results-root smoke_analysis \
  --n-nulls 20 \
  --k 6
```

The audit generated metrics, null-model output, mixture output, basin and edge data, a backbone CSV, and PNG/PDF figures.

## Persistence round-trip

```python
from verdant_v2.system import VerdantConfig, VerdantSystem

first = VerdantSystem(VerdantConfig(seed=7))
first.process_input("memory and identity")
first.save_state("state.json")

restored = VerdantSystem(VerdantConfig(seed=99))
restored.load_state("state.json")
restored.process_input("ethics and uncertainty")
```

The audit confirmed that restored memory/bridge objects are rebound into the dependent blocks and pipeline.

## Validity checks that should accompany future result claims

- Verify whether each analyzed edge is directed or undirected.
- Demonstrate invariance to swapping serialized endpoint labels.
- Compare against an analysis built from `parent_concepts` or an explicit lineage event table.
- Record the exact code branch state, configuration, provider, cycles, seed, input curriculum, and state file.
- Supply null RNG seeds and raw null samples.
- Keep deep-run results separate from short replication panels.

Passing the software tests establishes implementation behavior. It does not validate consciousness, AGI, ethical correctness, or the current causal-scaffolding interpretation.
