# Testing V1

## Unit tests

Install the core dependencies and pytest, then run from the repository root:

```bash
python -m pytest -q
```

The branch currently contains three focused tests:

| Test file | Verified behavior |
| --- | --- |
| `tests/test_logging_utils.py` | Logger setup disables propagation. |
| `tests/test_memory_storage_block.py` | Expired cache entries are removed and expiration statistics update. |
| `tests/test_memory_web.py` | Adding a thought does not create a self-connection. |

These are unit checks, not comprehensive system validation.

## Diagnostic runner

Single input:

```bash
python verdant_monolithic_test_runner.py --user-input "Evaluate an uncertain choice."
```

Ten automated cycles:

```bash
python verdant_monolithic_test_runner.py
```

The runner validates four imports, initializes the system, executes blocks with per-block error capture, reports confidence/ethics/memory summaries, and generates five visualizations.

## Syntax/import check

```bash
python -m compileall -q "Verdant Source Codes/src" verdant_monolithic_test_runner.py verdant_loop_controller.py
PYTHONPATH="Verdant Source Codes" python -c "from src.core.system import UnifiedSystem; UnifiedSystem()"
```

## Audit result

During the documentation audit:

- pytest: 3 passed;
- Python compilation: passed;
- automated diagnostic: 10 of 10 cycles completed without block-level errors;
- visualizer: five PNG files generated;
- `get_system_metrics()`: failed with a missing `EthicsKing.influence_history` attribute;
- `run_integration_tests()`: failed because `integration_test_suite` is not the name installed by the wiring helper;
- `generate_integration_report()`: failed because `integration_tools` is not installed;
- persistence: file round-trip completed, but the restored bridge was not rebound into bridge-dependent blocks.

## What passing does not mean

The current tests do not validate scientific claims in `Verdant Outline/`, general reasoning ability, ethical correctness, consciousness, security, concurrency, long-running learning, deterministic replay, or production fitness. See [docs/reproducibility.md](docs/reproducibility.md).
