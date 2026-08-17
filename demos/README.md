# Verdant-V0 Terminal Showcase

## Important evidence label

`interactive_demo.py` is a **presentation simulation**. It displays plausible architecture stages and sample/randomized metrics, but it does not instantiate `usm.UnifiedSyntheticMind` or execute the canonical V0 cognitive pipeline.

Use it to explain the design visually. Do not use its scores, node counts, timings, decisions, or ethical evaluations as experiment results.

## Run the showcase

```bash
python demos/interactive_demo.py
python demos/interactive_demo.py --query "How does AI learn?"
python demos/interactive_demo.py --showcase
python demos/interactive_demo.py --no-color
```

`rich` improves terminal formatting but is optional:

```bash
python -m pip install rich
```

## What it presents

- the nine-block architecture;
- Three Kings governance points;
- sample query progress;
- sample ethical scores;
- sample ECWF values;
- sample memory updates;
- sample system metrics.

## Run the real system instead

For a terminal interaction backed by the actual V0 runtime:

```bash
python -m usm
python scripts/verdant_repl.py
python scripts/verdant_telemetry.py --json
```

For a fixed, repeatable real-engine demonstration:

```bash
python scripts/kernel_loop.py --demo
```

That kernel command processes five inputs through `UnifiedSyntheticMind` and writes a trajectory and summary under `outputs/`. Its FCE estimate is still explicitly a demo heuristic, but the pipeline execution is real.

The distinction is simple: this directory shows what the architecture is meant to look like; `usm` and the scripts above run what this branch actually implements.
