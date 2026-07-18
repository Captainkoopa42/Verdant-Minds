# Verdant Minds V4

Verdant Minds V4 is the canonical runtime package for the surviving Verdant Minds codebase.

## Requirements

- Python 3.10 or newer

## Install

```bash
pip install -e .
```

## Run

```bash
python run_verdant.py --checkpoint /tmp/verdant_latest.json
```

Resume from a checkpoint:

```bash
python run_verdant.py --resume --checkpoint /tmp/verdant_latest.json
```

Dry startup without writing a checkpoint:

```bash
python run_verdant.py --dry-run
```

## Cultivation

```bash
python -m cultivation.cli validate-spec --spec cultivation/specs/quick_test.vcult
```

## Validation and tests

```bash
python -m pytest tests tests_v2/unit/test_memory.py tests_v2/unit/test_mitosis.py tests_v2/unit/test_basin_dynamics.py
python analysis/spec_validation.py
```

## Source tree

- `verdant/` — canonical V4 runtime package.
- `cultivation/` — cultivation specification parsing and execution helpers.
- `analysis/` — validation and analysis smoke tools retained for runtime development.
- `tests/` — current tests and V4 runtime regressions.
- `tests_v2/` — legacy regression tests retained where they still exercise current behavior.
- `run_verdant.py` — thin canonical runner.
