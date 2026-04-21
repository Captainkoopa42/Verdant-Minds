# Verdant-Memory Pivot Mapping

This document defines the product boundary for the pivot from
research-oriented Verdant-Minds internals to a developer-facing memory API.

## New public module structure

```text
verdant_memory/
  api/
    memory.py      # public API entry point
  schema.py        # versioned state + API result schemas
  core/
    engine.py      # internal wrapper around VerdantSystem
  sdk/
    client.py      # optional Python client abstraction
  internal/
    __init__.py    # internal compatibility namespace
```

## Public API surface (stable)

- `Memory.observe(text, metadata=None)`
- `Memory.retrieve(query)`
- `Memory.update(delta)`
- `Memory.snapshot()`
- `Memory.load(snapshot)`

## Old -> New responsibilities

| Old responsibility | New boundary |
|---|---|
| `VerdantSystem.process_input` | `Memory.observe` |
| `QueryEngine.query` | `Memory.retrieve` |
| direct `MemoryWeb` mutations | `Memory.update` |
| `VerdantSystem.save_state` | `Memory.snapshot` |
| `VerdantSystem.load_state` | `Memory.load` |

## Internal-only mechanics (no direct public exposure)

- ECWF dynamics
- Basin lifecycle and routing
- Three Kings governance
- Cultivation runners/providers

## Minimal example

```python
from verdant_memory import Memory

m = Memory()
m.observe("hello world")
print(m.retrieve("hello"))
```
