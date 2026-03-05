# Verdant-Minds v2

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18870656.svg)](https://doi.org/10.5281/zenodo.18870656)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**A thermodynamic cognitive architecture built on the Ethomorphic AI
principle: ethical reasoning geometrically embedded in cognitive state
space.**

## Architecture

```
Input → PipelineOrchestrator → [9 Blocks + Governance] → Output

Blocks: Sensory → Pattern → Memory → Communication → Reasoning →
        Ethics → Action → Language → Learning

Governance: DataKing + EthicsKing + ForefrontKing → Council

Memory: MemoryWeb (NetworkX) ↔ EthomorphicBridge ↔ ECWF

Phase Control: T_g → Rigid / Flexible / Chaotic
```

## Packages

| Package | Purpose | Dependencies |
|---------|---------|--------------|
| [`ethomorphic/`](ethomorphic/) | Core IP: ECWF engine, bridge, coherence, ethics | numpy only |
| [`verdant_v2/`](verdant_v2/) | Cognitive architecture | ethomorphic + networkx |
| [`tests_v2/`](tests_v2/) | All tests (114 passing) | pytest |

## Quick start

```bash
pip install -e ./ethomorphic
pip install -e ./verdant_v2
pytest tests_v2/ -v
```

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

## Research

The first Verdant-Minds whitepaper is in [`paper/`](paper/):

**Verdant-Minds: A Hybrid Cognitive Architecture with Graph Memory,
Wave-State Dynamics, and Measurable Emergent Concept Scaffolding**

Key finding: Emergent concepts show temporal scaffolding — newer
emergents preferentially link to older emergents (z=7.20, p<0.001).

DOI: [10.5281/zenodo.18870656](https://doi.org/10.5281/zenodo.18870656)

## v1

The published research prototype (v1) is preserved on the
[`codex/main`](https://github.com/Captainkoopa42/Verdant-Minds/tree/codex/main)
branch.

## License

MIT — see [LICENSE](LICENSE) and
[VERDANT_LICENSE_APPENDIX.md](VERDANT_LICENSE_APPENDIX.md)
