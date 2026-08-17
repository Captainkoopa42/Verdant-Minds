# Testing Verdant-V0

## Audited result

From a clean temporary Python 3.12 environment, the branch produced:

```text
121 passed, 38 warnings in 5.80s
```

The warnings came from deprecated `datetime.utcnow()` calls in the cultivation runner. They were warnings, not test failures.

## Run the suite

```bash
python -m pytest -q
```

For names and individual cases:

```bash
python -m pytest -v
```

The repository also includes wrapper scripts:

```bash
./run_tests.sh --no-cov
python run_tests.py --no-cov
```

Direct `pytest` is the clearest source of truth when investigating a failure.

## Test inventory

Use collection output rather than a hard-coded total when the suite changes:

```bash
python -m pytest --collect-only -q
```

The tests cover the canonical system and adjacent behavior including:

- `CognitiveChunk` construction and section updates;
- system initialization and nine-block processing;
- MemoryWeb graph operations;
- ECWF and Memory–ECWF coupling;
- pconnect edge behavior;
- Three Kings oversight and coordination;
- coherence-invariant calculation and feedback;
- state serialization and restoration;
- cultivation helpers and telemetry;
- emergent scaffolding analysis behavior.

See [tests/README.md](tests/README.md) for the test-file map.

## Engineering smoke checks

### Import and initialize

```bash
python - <<'PY'
from usm import UnifiedSyntheticMind
mind = UnifiedSyntheticMind(config={"initialize_knowledge": False})
print(type(mind).__name__)
PY
```

### Process one real input

```bash
python - <<'PY'
from usm import UnifiedSyntheticMind
mind = UnifiedSyntheticMind(config={"initialize_knowledge": True})
chunk = mind.process_input("How should memory and ethics influence a decision?")
print(chunk.get_section_content("action_selection_section"))
print(chunk.get_section_content("coherence_invariants_section"))
PY
```

### Run the real kernel demo

```bash
python scripts/kernel_loop.py --demo
```

This writes `outputs/demo_trajectory.json` and `outputs/demo_summary.txt`. Those files are generated run artifacts, not source documentation.

### Generate default figures

```bash
python visualization/plot_processing.py --all --output /tmp/verdant-v0-figures
```

The default plotting path uses sample data. Successful figure creation tests plotting mechanics, not a scientific result.

## What passing tests establish

Passing tests establish that the implemented interfaces and expected mechanics behave as asserted in the suite. They do not establish that:

- the architecture is conscious or generally intelligent;
- its internal metrics correspond to accepted biological measurements;
- a representative cultivation result will reproduce under every provider or seed;
- the incomplete top-level `verdant/` tree is runnable.

## Failure triage

1. Confirm the current branch is `Verdant-V0`.
2. Confirm imports resolve to the checkout: `python -c "import usm; print(usm.__file__)"`.
3. Reinstall the declared dependencies and editable source.
4. Run the failing test alone with `-vv -s`.
5. Record Python version, platform, command, seed/configuration, and full traceback.

For experiment reporting rather than code testing, use [docs/reproducibility.md](docs/reproducibility.md).
