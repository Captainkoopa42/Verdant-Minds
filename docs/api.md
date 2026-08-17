# V1 Python interface reference

V1 is not packaged. Add `Verdant Source Codes` to `PYTHONPATH` before using these imports.

## UnifiedSystem

```python
from src.core.system import UnifiedSystem
```

### Constructor

```python
UnifiedSystem(seed: int = 42, config: dict | None = None)
```

Recognized configuration keys:

| Key | Default | Purpose |
| --- | ---: | --- |
| `cognitive_dimensions` | `5` | ECWF cognitive vector size |
| `ethical_dimensions` | `5` | ECWF ethical vector size |
| `wave_facets` | `7` | ECWF facet count |
| `bridge_influence_factor` | `0.3` | Strength of memory/ECWF transfer |
| `learning_rate` | `0.05` | Stored system setting |
| `decision_threshold` | `0.7` | Stored decision setting |
| `ethical_sensitivity` | `0.6` | Stored ethics setting |
| `initialize_knowledge` | `True` | Populate 17 default concepts |
| `log_level` | `"INFO"` | Stored setting; logger construction currently uses INFO directly |

Unknown keys are retained in the merged configuration but are not necessarily consumed.

### `process_input()`

```python
chunk = system.process_input(input_text: str, metadata: dict | None = None)
```

Runs the fixed block/governance sequence and returns a mutable `CognitiveChunk`.

### `get_response()`

```python
text = system.get_response(input_text: str, metadata: dict | None = None)
```

Runs a complete cycle and returns template-generated text.

### `initialize_knowledge()`

Populates the built-in ethical and general concepts, connects them through `MemoryWeb`, and maps them to ECWF dimensions. Repeated calls may reinforce existing concepts rather than create a clean replacement.

### `save_system_state()` / `load_system_state()`

```python
ok = system.save_system_state("state.pkl")
restored = UnifiedSystem.load_system_state("state.pkl")
```

Uses Python pickle. Never load an untrusted pickle. The V1 loader does not rebind bridge-dependent blocks to the restored bridge; see [walkthrough.md](walkthrough.md#7-persistence-caveat).

### Known-broken methods

Do not present these as operational V1 APIs:

- `get_system_metrics()` fails when it accesses missing `EthicsKing.influence_history`.
- `run_integration_tests()` refers to `integration_test_suite`, while the installer creates `integration_tests`.
- `generate_integration_report()` refers to missing `integration_tools` and also invokes the broken test method.

The underlying integration helper objects are installed as `integration_manager`, `integration_framework`, and `integration_tests`, but they are not documented here as stable public interfaces.

## CognitiveChunk

```python
from src.core.cognitive_chunk import CognitiveChunk
```

Useful methods:

| Method | Behavior |
| --- | --- |
| `add_section(name, content)` | Adds a section; raises if it already exists. |
| `update_section(name, content)` | Replaces or creates a section. |
| `get_section_content(name, default=None)` | Returns section content or the default. |
| `add_processing_step(processor, operation, details)` | Appends a timestamped log entry. |
| `get_processing_history(processor_name=None)` | Returns all or filtered processing steps. |
| `merge_chunk(other)` | Adds missing section keys and appends processing history. |

## MemoryWeb

```python
from src.memory.memory_web import MemoryWeb
```

The graph-memory API includes concept insertion, weighted connections, related-thought retrieval, spreading activation, reinforcement, decay, clustering, and metrics. It uses NetworkX and stores metadata separately in `memory_store`.

`python-louvain` is optional for community detection; other memory operations use NetworkX alone.

## MemoryStorageBlock

```python
from src.blocks.memory_storage_block import MemoryStorageBlock
```

As a standalone class, this is a thread-safe TTL/LRU key-value cache with `set`, `get`, `delete`, `clear`, `keys`, `size`, and `get_stats`. In the `UnifiedSystem` pipeline it is incorrectly constructed and its `process_chunk()` is only a compatibility no-op.

## Authentication prototype

```python
from src.auth.system import UserManager, UserRole, PermissionType
```

This module provides in-memory users, role checks, password hashing, and JWT creation/verification. It is not integrated with the main system. Set `JWT_SECRET_KEY` before any experiment; the built-in fallback is not suitable for deployment.

## Root command interfaces

```bash
python verdant_monolithic_test_runner.py [--user-input TEXT]
python verdant_loop_controller.py
```

The first is a diagnostic harness. The second is an interactive loop that exits when the user types `exit`.
