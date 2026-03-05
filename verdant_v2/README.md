# Verdant-Minds v2

Production cognitive architecture built on the Ethomorphic AI core.

## Architecture

```
Input → PipelineOrchestrator → [9 Blocks + Governance] → Output

Blocks: Sensory → Pattern → Memory → Communication → Reasoning →
        Ethics → Action → Language → Learning

Governance: DataKing + EthicsKing + ForefrontKing → Council

Memory: MemoryWeb (NetworkX) ↔ EthomorphicBridge ↔ ECWF

Phase Control: T_g → Rigid / Flexible / Chaotic
```

## Quick start

```python
from verdant_v2.system import VerdantSystem, VerdantConfig

config = VerdantConfig(
    seed=42,
    cognitive_dimensions=5,
    ethical_dimensions=5,
    initialize_knowledge=True,
)
mind = VerdantSystem(config)
chunk = mind.process_input("What stays identical when everything changes?")
```

## Install

```bash
pip install -e ./ethomorphic
pip install -e ./verdant_v2
```

## Test

```bash
pytest tests_v2/ -v
```

## Status

- 114/114 tests passing
- 10 cultivation cycles produce 3 emergent concepts
- Chunked persistence: in progress
- API server: planned

## Compared to v1

| Aspect | v1 (`Verdant Source Codes/`) | v2 (`verdant_v2/`) |
|--------|-----------------------------|--------------------|
| ECWF dims | Hardcoded 5+5 | Configurable up to 64+64 |
| Memory backend | Tightly coupled NetworkX | Protocol-based |
| Ethomorphic core | Embedded | Separable package |
| Persistence | Monolithic JSON | Chunked (snapshots + diffs) |
| Naming | Timestamp suffix | Hash suffix (no collisions) |
| Packaging | sys.path manipulation | pip install -e |
| Governance | Inline | Protocol-based Kings |

## DOI

Part of Verdant-Minds: [10.5281/zenodo.18870656](https://doi.org/10.5281/zenodo.18870656)
