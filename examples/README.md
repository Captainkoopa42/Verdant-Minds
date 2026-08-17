# Verdant-V0 Examples

`basic_usage.py` uses the real canonical runtime through:

```python
from usm import UnifiedSyntheticMind
```

Run it from the repository root:

```bash
python examples/basic_usage.py
```

The example demonstrates:

- default and custom initialization;
- `get_response()` for template-based output;
- `process_input()` for direct `CognitiveChunk` inspection;
- MemoryWeb node and edge inspection;
- ethical/governance sections;
- system metrics;
- repeated interaction and learning state.

The example intentionally works without a trained language model. Its prose responses come from V0’s built-in templates. The graph, wave, governance, processing, and telemetry paths are real runtime behavior.

For a shorter starting point:

```python
from usm import UnifiedSyntheticMind

mind = UnifiedSyntheticMind(seed=42)
chunk = mind.process_input("What should the system inspect?")

print(chunk.get_section_content("memory_section"))
print(chunk.get_section_content("action_selection_section"))
print(chunk.get_section_content("coherence_invariants_section"))
```

Read [../docs/walkthrough.md](../docs/walkthrough.md) for the order in which these sections are produced.
