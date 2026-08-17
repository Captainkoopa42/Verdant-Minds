# V2 execution walkthrough

This walkthrough assumes the import alias in [../INSTALL.md](../INSTALL.md) is active.

## 1. Construct the system

```python
from verdant_v2.system import VerdantConfig, VerdantSystem

system = VerdantSystem(VerdantConfig(seed=42))
```

Construction creates ECWF, the undirected memory graph, bridge, nine blocks, Three Kings, pipeline, phase/coherence state, and basin state. Default knowledge initialization then adds 82 concepts, 294 graph edges, and 82 concept/dimension mappings.

`seed=42` seeds NumPy's legacy global RNG and ECWF. It does not fully control every `np.random.default_rng()` call used by bridge and emergence mapping. The cultivation runner patches that generator for its local deterministic sessions.

## 2. Process one input

```python
chunk = system.process_input(
    "How does memory support ethical reasoning?",
    metadata={"source": "walkthrough"},
)
```

`VerdantSystem` creates a `CognitiveChunk`, adds raw text/metadata, inserts the current `T_g` and cycle count, then gives the chunk to `PipelineOrchestrator`.

### Sensory

Normalizes/tokenizes text and writes token count, complexity, ambiguity, and metadata.

### Pattern recognition

Extracts concepts, keywords, simple patterns, intent, and ethical dimensions using deterministic heuristics.

### Optional basin routing

If enabled, the orchestrator detects/scans candidate basins, adds priority seeds, runs local basin micro-pipelines, and stores their proposals.

### Memory and ECWF

Retrieves/activates graph concepts, performs bridge updates, computes wave properties, applies phase-sensitive memory behavior, and writes both memory and wave sections.

### Communication and Data King

Aggregates prior outputs, then adds data-quality oversight.

### Reasoning

Builds rule-based inference/hypothesis information from patterns, memory, and wave state.

### Ethics and Ethics King

The block calculates principle/energy-style ethical fields. The King converts those and other context into governance evaluation.

### Action, Forefront King, and council

The action block proposes a response behavior. Forefront oversight and the combined council may modify/annotate it. With basin routing, proposal arbitration can then replace the selected action and blend confidence.

### Language

The default `TemplateBackend` produces structured/template text. `LLMBackend` is an optional protocol adapter, not a built-in trained model.

### Learning and emergence

The block records proposed updates, adapts rates, and can create one emergent concept for a previously unseen high-magnitude concept combination.

## 3. Post-pipeline measurements

After the nine blocks, `VerdantSystem`:

1. computes coherence invariants;
2. updates `T_g` from the completed chunk;
3. increments cycle and aggregate metrics;
4. scans graph basins at the configured interval;
5. updates persistent `BasinState` records;
6. returns the enriched chunk.

```python
print(sorted(chunk.sections))
print(chunk.to_compact_dict())
print(system.get_metrics())
```

## 4. Run repeated cultivation

The local cultivation runner wraps repeated cycles in an explicitly controlled environment:

```bash
python -m cultivation.cli run \
  --cycles 20 \
  --provider local \
  --seeds 0-4 \
  --basin-routing \
  --outdir outputs_v2
```

For each seed it:

- seeds Python and NumPy;
- replaces wall-clock time with deterministic increments;
- replaces unseeded `default_rng()` creation with deterministic generators;
- generates curriculum/perturbed local input;
- optionally applies an intervention at one cycle;
- writes every cycle as JSON Lines;
- saves final system state and a summary;
- restores global time/RNG functions afterward.

## 5. Apply interventions

Available intervention modes are:

- `ablate_oldest_nodes` — remove a fraction of oldest emergent nodes;
- `scramble_ee_edges` — rewire emergent/emergent associations;
- `none` — baseline.

Example:

```bash
python -m cultivation.cli run \
  --cycles 80 --seeds 0-4 --provider local --basin-routing \
  --intervention-mode ablate_oldest_nodes \
  --intervention-cycle 40 --ablation-fraction 0.1 \
  --intervention-target global --outdir outputs_ablation
```

The comparison script consumes three completed run directories and writes summary JSON/CSV plus figures.

## 6. Analyze a saved state

```bash
python analysis/run_all.py \
  --state outputs_v2/run_<timestamp>/seed_0/state.json \
  --results-root results_local --n-nulls 200 --k 6
```

The pipeline extracts graph metrics, simulates timestamp and rewired nulls, fits one/two Gaussian components to log age gaps, exports a top-k backbone, and generates figures.

Do not read `source` and `target` in the serialized undirected graph as causal direction. The current analysis does, which invalidates its directional conclusion. The age-gap and undirected topology outputs may still be useful after their assumptions are stated correctly.

## 7. Save and restore live state

```python
system.save_state("state.json")

restored = VerdantSystem(VerdantConfig(seed=99))
restored.load_state("state.json")
next_chunk = restored.process_input("Continue from the restored graph")
```

Unlike V1's pickle path, V2 uses inspectable JSON and explicitly rebinds restored memory and bridge objects into dependent blocks. The audit confirmed continued processing after load.
