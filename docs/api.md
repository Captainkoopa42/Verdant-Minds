# V2 Python interface reference

The API imports below require the current branch workaround described in [../INSTALL.md](../INSTALL.md).

## VerdantSystem and VerdantConfig

```python
from verdant_v2.system import VerdantConfig, VerdantSystem
```

### Configuration

| Field | Default | Meaning |
| --- | ---: | --- |
| `cognitive_dims` | `5` | ECWF cognitive dimensions |
| `ethical_dims` | `5` | ECWF ethical dimensions |
| `wave_facets` | `7` | ECWF facet count |
| `bridge_influence_factor` | `0.3` | Memory/ECWF coupling strength |
| `learning_rate` | `0.05` | Stored system learning setting |
| `decision_threshold` | `0.7` | Action/governance threshold |
| `ethical_sensitivity` | `0.6` | Ethics King sensitivity |
| `initialize_knowledge` | `True` | Add 82 seed concepts |
| `seed` | `42` | ECWF/global NumPy seed; not complete direct-use determinism |
| `basin_scan_interval` | `10` | Cycles between system basin scans |
| `basin_scan_k` | `6` | Backbone neighborhood size |
| `basin_min_size` | `5` | Minimum reported basin size |
| `basin_routing` | `False` | Enable basin micro-pipelines/arbitration |
| `basin_top_m` | `2` | Maximum selected basins |

### `process_input()`

```python
chunk = system.process_input(text: str, metadata: dict | None = None)
```

Runs the full pipeline, coherence, phase, metrics, and basin state update. Returns `CognitiveChunk`.

### `initialize_knowledge()`

```python
summary = system.initialize_knowledge()
```

Adds/reinforces built-in concepts and connections, then rebuilds bridge mappings. On an empty memory it reports 82 concepts, 10 ethical concepts, 72 general concepts, and 82 mappings.

### `get_metrics()`

Returns aggregate cycles, entropy/coherence averages, `T_g`, phase, memory/emergent counts, edge classification, basin summaries, and basin-state records.

### `save_state()` and `load_state()`

```python
system.save_state("state.json")
system.load_state("state.json")
```

These are instance methods. `load_state()` mutates the existing instance and rebinds restored components. State files are JSON, not pickle.

## CognitiveChunk

```python
from verdant_v2.pipeline.chunk import CognitiveChunk, ProcessingStep
```

| Method | Behavior |
| --- | --- |
| `add_section(name, content)` | Adds a new section; raises on duplicate |
| `update_section(name, content)` | Creates or replaces a section |
| `get_section_content(name)` | Returns a section or `None` |
| `get_all_sections()` | Returns a shallow copy |
| `add_processing_step(processor, operation, details=None)` | Adds timestamped log entry |
| `get_processing_history(processor_name=None)` | Returns all or filtered steps |
| `to_compact_dict()` | Creates an LLM-friendly reduced representation |

## MemoryWeb

```python
from verdant_v2.memory.graph import MemoryWeb
```

Primary operations include `add_concept`, `get_concept`, `connect`, `get_neighbors`, `list_concepts`, `reinforce`, `decay`, `retrieve_related`, `activate_concepts`, `cluster_thoughts`, `get_emergent_nodes`, `get_edge_classification`, `to_state_dict`, and `from_state_dict`.

`MemoryWeb` uses an undirected `networkx.Graph`. Serialized keys named `source` and `target` must not be treated as semantic direction.

`edge_policy="pconnect"` applies a probabilistic connection gate using weight and a simple ethical-charge heuristic. The default policy connects deterministically.

## EthomorphicBridge

```python
from ethomorphic.bridge.bridge import EthomorphicBridge, MemoryBackend
```

The bridge depends on the `MemoryBackend` protocol rather than NetworkX. It maps concepts into cognitive/ethical ECWF dimensions, derives state vectors, performs memory→ECWF and ECWF→memory updates, tracks resonance, and serializes bridge state.

Important reproducibility caveat: `assign_concept_mappings()` creates an unseeded `np.random.default_rng()` in direct system use. The cultivation runner intercepts this for deterministic local runs.

## ECWFCore

```python
from ethomorphic.ecwf.core import ECWFCore
```

Provides wave computation, entropy, sensitivity, parameter updates, dimension meanings, and state serialization/restoration. It is quantum-inspired NumPy computation, not a quantum-computer interface.

## Coherence

```python
from ethomorphic.coherence.invariants import compute_coherence
```

Returns a `CoherenceResult` containing triangle validity, estimated critical alpha, violation rate, HCI, and the evaluated triple. These are V2-defined operational metrics.

## Basin and intervention interfaces

```python
from verdant_v2.memory.basins import detect_basins
from verdant_v2.memory.interventions import (
    ablate_oldest_emergent_nodes,
    scramble_emergent_edges,
)
```

Basins are communities extracted from an undirected top-k backbone. Interventions mutate the graph and return counts describing the operation.

## Cultivation command

```bash
python -m cultivation.cli run [options]
```

Key options: `--cycles`, `--provider`, `--seeds`, `--outdir`, `--pressure-every`, `--basin-routing`, `--intervention-mode`, `--intervention-cycle`, `--ablation-fraction`, `--intervention-target`, and `--intervention-seed`.

## APIs not present in V2

The old documentation's `UnifiedSyntheticMind`, `get_response()`, `get_system_metrics()`, `run_integration_tests()`, `verdant-minds` console command, and `usm` import do not exist in the active V2 source.
