# Contributing to V1

V1 is an inspectable research generation. Contributions should make its current behavior clearer, safer, or more reproducible without rewriting the historical research record.

## Before changing code

1. Read [STATUS.md](STATUS.md) and [docs/architecture.md](docs/architecture.md).
2. Identify whether the change repairs current V1 behavior, adds a new experiment, or updates documentation.
3. State which claim or behavior the change is intended to test.

## Local checks

```bash
python -m pytest -q
python -m compileall -q "Verdant Source Codes/src" verdant_monolithic_test_runner.py verdant_loop_controller.py
python verdant_monolithic_test_runner.py
```

If a change affects output or research claims, include the input, configuration, random seed, dependency versions, raw result, and acceptance rule.

## Repository conventions

- Treat `Verdant Source Codes/src/core/system.py` as the runnable orchestrator unless a change explicitly establishes another implementation.
- Preserve the lowercase import wrappers while they remain part of the canonical import path.
- Do not describe placeholders as completed subsystems.
- Separate observed results from hypotheses and interpretation.
- Add focused regression tests for defects you repair.
- Never commit passwords, tokens, generated logs, cache directories, or report images.

## Documentation rules

- Root documents answer repository-wide questions.
- `docs/` contains the canonical engineering reference.
- Directory READMEs explain only their directory's role.
- `Verdant Outline/` remains the research/concept record and must be labeled accordingly.
- Replace outdated statements rather than adding a second competing explanation.

## Suggested first repairs

The highest-value repairs are listed in [STATUS.md](STATUS.md): memory-stage wiring, integration attribute consistency, King metrics, and persistence rebinding.
