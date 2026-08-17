# V2 cultivation runner

The cultivation package runs deterministic, seed-scoped Verdant sessions and writes inspectable artifacts. It is the active V2 experiment runner.

## Run locally

First apply the import workaround and install the core dependencies described in [../INSTALL.md](../INSTALL.md). Then, from the repository root:

```bash
python -m cultivation.cli run \
  --cycles 120 \
  --provider local \
  --seeds 0-19 \
  --basin-routing \
  --outdir outputs
```

The `local` provider requires no external API. The `anthropic`, `groq`, and `mistral` providers require their respective credentials and dependencies.

## Run structure

The runner creates a UTC-stamped run directory containing one directory per seed. Each seed produces:

- `cycles.jsonl`: per-cycle inputs, phase, thermodynamic, coherence, memory, basin, proposal, and intervention telemetry;
- `state.json`: serialized V2 system state;
- `summary.json`: end-of-session configuration and aggregate values.

The runner seeds Python and NumPy, replaces the no-argument NumPy generator with a seed-derived generator for the run, supplies deterministic time values, and reseeds the ECWF parameters. It restores the original process state after each seed.

## Curriculum and providers

`CurriculumStrategy` alternates ordinary prompts with pressure prompts according to `--pressure-every`. `PerturbationEngine` makes seed- and cycle-scoped prompt variations. Providers convert those prompts into input text for `VerdantSystem.process_input()`.

## Interventions

Supported modes are:

- `none`;
- `ablate_oldest_nodes`;
- `scramble_ee_edges`.

Use `--intervention-cycle` to select the cycle and `--intervention-target global|largest_basin` to select scope. Node ablation also accepts `--ablation-fraction`; edge scrambling accepts `--intervention-seed`.

## Packaging status

`cultivation/pyproject.toml` contains absolute `file:///workspace/Verdant-Minds/...` dependencies and points to a nonexistent `verdant_v2` directory. Treat `python -m cultivation.cli` from the repository root as the current runnable route after the documented alias workaround; do not expect `pip install -e ./cultivation` to work portably yet.
