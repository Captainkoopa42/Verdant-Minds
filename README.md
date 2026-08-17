# Verdant-Minds — V1

V1 is a research-prototype generation of Verdant-Minds. It implements a Python cognitive-processing pipeline built around a graph memory, a quantum-inspired Extended Cognitive Wave Function (ECWF), nine processing blocks, and the Three Kings governance layer.

This branch is best read as an inspectable research generation, not as a packaged application or a validated artificial general intelligence system. The main pipeline runs, the included unit tests pass, and the diagnostic runner completes ten cycles. Several auxiliary interfaces remain incomplete or incorrectly wired; they are recorded in [STATUS.md](STATUS.md).

## Start here

- [Install and run V1](INSTALL.md)
- [Current implementation status](STATUS.md)
- [Architecture map](docs/architecture.md)
- [End-to-end walkthrough](docs/walkthrough.md)
- [Python interface reference](docs/api.md)
- [Testing guide](TESTING.md)
- [Reproducibility and evidence boundaries](docs/reproducibility.md)
- [How to contribute](CONTRIBUTING.md)

## What is actually implemented

- A `UnifiedSystem` Python orchestrator.
- A nine-stage, text-input processing sequence.
- A `CognitiveChunk` shared data container.
- A NetworkX-backed associative `MemoryWeb`.
- A NumPy-based ECWF computation and memory/ECWF bridge.
- Data, Forefront, and Ethics “King” oversight components.
- Template-based response generation.
- Per-cycle visualization and metrics output.
- A separate in-memory authentication/authorization prototype.
- Three focused pytest tests and a ten-cycle diagnostic runner.

## What this branch does not establish

The repository does not contain experimental evidence sufficient to establish AGI, consciousness, quantum computation, general ethical correctness, cross-domain superiority, or the numerical performance claims in the research outline. ECWF is quantum-inspired numerical code running on ordinary NumPy arrays; it is not a quantum-computer implementation.

V1 also has no installable Python package metadata, dependency lockfile, trained model, external knowledge source, frontend application, production service, or complete validation suite.

## Quick run

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install numpy networkx matplotlib pytest
python verdant_monolithic_test_runner.py --user-input "How should an uncertain decision be evaluated fairly?"
```

The root runners add `Verdant Source Codes` to Python's import path automatically. For direct imports, set `PYTHONPATH`:

```bash
PYTHONPATH="Verdant Source Codes" python -c "from src.core.system import UnifiedSystem; print(UnifiedSystem().get_response('Hello Verdant'))"
```

See [INSTALL.md](INSTALL.md) for platform-specific commands and optional dependencies.

## Repository map

| Path | Role |
| --- | --- |
| `Verdant Source Codes/src/core/system.py` | Canonical runnable Python orchestrator |
| `Verdant Source Codes/src/blocks/` | Nine pipeline blocks; lowercase modules wrap uppercase implementations |
| `Verdant Source Codes/src/memory/` | Memory graph, ECWF calculation, and bidirectional bridge |
| `Verdant Source Codes/src/kings/` | Three governance components and coordinator |
| `Verdant Source Codes/src/integration/` | Instrumentation, integration helpers, and visualizer |
| `Verdant Source Codes/src/auth/system.py` | Standalone in-memory authentication prototype |
| `tests/` | Three focused unit tests |
| `verdant_monolithic_test_runner.py` | Automated and single-input diagnostic runner |
| `verdant_loop_controller.py` | Interactive terminal loop |
| `Verdant Outline/` | Concept papers and research claims; not test evidence |
| `docs/` | Canonical V1 engineering documentation |

## Branch interpretation

`V1` names this complete browsable generation. It does not imply that every file was created at one moment. Some files explicitly describe themselves as later repairs or support additions. The documentation therefore describes what is present on the branch now and separates implemented behavior from historical or aspirational writing. See [docs/branch-history.md](docs/branch-history.md).

## License

The code is licensed under the [MIT License](LICENSE). [VERDANT_LICENSE_APPENDIX.md](VERDANT_LICENSE_APPENDIX.md) states the author's non-binding ethical intent and does not replace or restrict the MIT grant.
