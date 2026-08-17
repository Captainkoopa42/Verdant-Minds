# V1 execution walkthrough

This walkthrough follows the runnable Python implementation in `Verdant Source Codes/src/core/system.py`.

## 1. Initialize the system

```python
from src.core.system import UnifiedSystem

system = UnifiedSystem(seed=42)
```

Initialization performs the following work:

1. Creates a logger and seeds NumPy.
2. Merges any supplied configuration with defaults.
3. Constructs `MemoryWeb`, `ECWFCore`, and `MemoryECWFBridge`.
4. Labels the five cognitive and five ethical ECWF dimensions.
5. Constructs system-wide learning, nine blocks, Three Kings, and the visualizer.
6. Installs integration helper objects.
7. Unless disabled, inserts 17 initial concepts and 17 concept/dimension mappings.

To inspect an empty starting memory instead:

```python
system = UnifiedSystem(config={"initialize_knowledge": False})
```

## 2. Submit text

```python
chunk = system.process_input(
    "Should a system explain a risky decision?",
    metadata={"source": "walkthrough"},
)
```

The sensory block creates a `CognitiveChunk`, normalizes the text, tokenizes it, and records metadata. Before the remaining blocks run, `UnifiedSystem` calculates the glass-transition value `T_g`.

Important timing detail: `T_g` is calculated before pattern, memory, wave, or reasoning results for the current input exist. The current calculation therefore uses sensory data plus fallback values for missing memory and wave fields. It should not be interpreted as a full-cycle emergent measurement.

## 3. Traverse the blocks

The chunk passes through the configured list in order.

### Sensory input

Creates the chunk and stores the input text, token-level data, and preprocessing metadata.

### Pattern recognition

Extracts simple token-based concepts, classifies input as a question or statement, and looks for a small ethical-keyword dictionary. The five named pattern detectors currently return empty lists, so this is mostly heuristic extraction rather than learned pattern recognition.

### Memory storage

Prints a processing message and returns the chunk unchanged. Although the class separately implements a thread-safe TTL/LRU key-value cache, that cache is not used by the pipeline path.

### Internal communication

Adds coordination/communication information used by later components.

### Data King

Runs immediately after internal communication and adds data-governance analysis.

### Reasoning and planning

Builds rule-based reasoning/plan data, using the memory bridge where available, and records a confidence score.

### Ethics and values, then Ethics King

The block adds ethical evaluation data. The Ethics King then adds its governance evaluation and increments the system's ethical-evaluation count.

### Action selection, then Forefront/combined oversight

The action block chooses among actions such as answering, partially answering, asking for clarification, or deferring. The Forefront King and then the full Three Kings coordinator oversee the result.

### Language processing

Adds language-processing information. The user-facing response is not taken directly from this section; `get_response()` later selects one of several fixed response templates.

### Continual learning

Runs the system-learning adapter and adds its section. This should not be read as evidence of long-term or open-ended learning without a controlled persistence experiment.

## 4. Finalize metrics and visualization data

`process_input()` adds processing durations, current `T_g`, and system entropy to the chunk. It then logs one compact cycle record to `SystemVisualizer`.

Inspect the result:

```python
print(chunk.sections.keys())
print(chunk.get_section_content("reasoning_section"))
print(chunk.get_processing_history())
```

## 5. Generate a response

`get_response()` calls the entire processing cycle and then chooses a hand-written response template using the selected action, confidence, ethics fields, and any retrieved concepts:

```python
response = system.get_response("What should I consider?")
print(response)
```

This output is assembled from rules and templates. There is no language model, retrieval corpus, or trained generation component in V1.

## 6. Use the included runners

The monolithic runner manually executes the same stages with block-level exception capture:

```bash
python verdant_monolithic_test_runner.py
```

The interactive controller accepts terminal input until the exact word `exit`:

```bash
python verdant_loop_controller.py
```

Both can generate `verdant_test_output/` reports. The interactive controller does not handle an end-of-file signal as a normal exit.

## 7. Persistence caveat

```python
system.save_system_state("state.pkl")
restored = UnifiedSystem.load_system_state("state.pkl")
```

This restores `MemoryWeb`, `ECWFCore`, configuration, and metrics into a newly created system. It then creates a new bridge. However, the already-created reasoning, ethics, and language blocks still hold the pre-restore bridge. Processing may continue without crashing, but those blocks are not connected to the restored state as intended. Do not rely on V1 state loading for a scientifically valid continuation experiment.
