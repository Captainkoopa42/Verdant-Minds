# Verdant-Minds

Verdant-Minds is a research-oriented cognitive architecture implemented in Python. The runtime entry point is `UnifiedSystem` (exported as `usm.UnifiedSyntheticMind`) and composes a nine-block processing pipeline, `MemoryWeb` graph memory, `ECWFCore` wave-state dynamics, and `ThreeKingsLayer` governance.

---

## Table of Contents

- [Repository goals and current status](#repository-goals-and-current-status)
- [Docs index](#docs-index)
- [Quick start](#quick-start)
- [Primary execution modes](#primary-execution-modes)
- [Cultivator CLI reference](#cultivator-cli-reference)
- [Output artifacts and where they are written](#output-artifacts-and-where-they-are-written)
- [Metric definitions used in repo docs](#metric-definitions-used-in-repo-docs)
- [Reproducibility minimum pack](#reproducibility-minimum-pack)
- [Project layout](#project-layout)

---

## Repository goals and current status

The repository focuses on:

1. A full nine-stage cognitive processing loop (sensory → pattern → memory → communication → reasoning → ethics → action → language → learning).
2. State-bearing operation with JSON save/load for long runs.
3. Instrumentation (telemetry, cycle logs, coherence and wave/memory metrics).
4. Post-run structural analysis (`scripts/analysis/scaffolding_from_state.py`) for emergent temporal scaffolding behavior.

The codebase includes both:

- a **demo kernel mode** (`scripts/kernel_loop.py --demo`) with a demo-only FCE estimate heuristic, and
- a **canonical cultivation mode** (`scripts/verdant_llm_cultivator.py`) used for longer telemetry/state runs.

---

## Docs index

- **Architecture deep dive**: `docs/architecture.md`
- **Colab + Drive persistence guide**: `docs/colab.md`
- **API/entry-point reference**: `docs/api.md`
- **Reproducibility checklist and templates**: `docs/reproducibility.md`

If you are new to the repo, read in this order: `README.md` → `docs/architecture.md` → `docs/colab.md`.

---

## Quick start

### 1) Install

What this does: installs runtime dependencies needed by scripts in this repository.

```bash
pip install -r requirements.txt
```

### 2) Interactive REPL

What this does: starts a terminal prompt loop over `UnifiedSyntheticMind`.

```bash
python scripts/verdant_repl.py
```

### 3) Telemetry loop

What this does: processes interactive inputs and prints structured telemetry.

```bash
python scripts/verdant_telemetry.py
# JSON output mode
python scripts/verdant_telemetry.py --json
```

---

## Primary execution modes

| Mode | Command | What it does | Typical artifacts |
|---|---|---|---|
| REPL | `python scripts/verdant_repl.py` | interactive response loop with optional state load/save | user-provided state path |
| Telemetry loop | `python scripts/verdant_telemetry.py` | per-input thermodynamic/coherence/memory telemetry | terminal output |
| Kernel loop | `python scripts/kernel_loop.py` | repeated baseline loop with CSV logging | `artifacts/kernel_log.csv` |
| Demo kernel | `python scripts/kernel_loop.py --demo` | fixed 5-step structured demo | `outputs/demo_trajectory.json`, `outputs/demo_summary.txt` |
| Cultivation runner | `python scripts/verdant_llm_cultivator.py ...` | multi-cycle provider-driven run with cycle/session/state artifacts | `outputs/*` or custom `--output-dir` |
| Scaffolding analysis | `python scripts/analysis/scaffolding_from_state.py --state ...` | emergent temporal scaffolding metrics and plots | `emergent_scaffolding.png`, `link_age_gaps.png` |

---

## Cultivator CLI reference

Source of truth: `scripts/verdant_llm_cultivator.py` argparse definitions.

### Core flags

- `--cycles` / `--max-cycles` (default `50`)
- `--seed-topic`
- `--resume [latest|PATH]`
- `--fresh`
- `--model` (default `claude-3-5-sonnet-latest`)
- `--temperature` (default `0.8`)
- `--max-tokens` / `--max-tokens-per-call` (default from `VERDANT_MAX_TOKENS_PER_CALL`, fallback `128`)
- `--budget-mode {off,light,aggressive}`
- `--perturbation-interval` (default `15`)
- `--no-perturbation`
- `--initialize-knowledge`
- `--load-state PATH`
- `--save-state PATH`
- `--output-dir PATH`
- `--cycle-sleep`

### Fresh vs resume semantics

- **Fresh run** (`--fresh`) skips cycle-log resume behavior.
- **Resume run** (`--resume latest` or `--resume PATH`) rehydrates prior cycle context from JSONL when `--fresh` is not set.
- **State resume** (`--load-state PATH`) loads persisted MemoryWeb/ECWF/system state before cycles.
- **Initialize knowledge gate**: initialization is applied only when `--initialize-knowledge` is set and `--load-state` is not set.

Interpretation note for reporting: “20 cycles resumed” means 20 additional cycles over persisted trajectory; it is not equivalent to a fresh 20-cycle run from initialization.

---

## Output artifacts and where they are written

In cultivation mode, artifacts are written to:

- default: `outputs/`
- or custom: `--output-dir <dir>`

Per run, filenames are timestamped:

- `cultivation_session_<stamp>.json`
- `cultivation_cycles_<stamp>.jsonl`
- `cultivation_state_<stamp>.json`
- `significant_events_<stamp>.json`

If `--save-state PATH` is provided, an additional explicit state file is saved at that path.

---

## Metric definitions used in repo docs

These names are used consistently in docs/scripts:

- `T_g`: glass transition temperature.
- `T_cog` (cultivator telemetry): `1 - T_g + system_entropy`.
- `HCI`: housed contradiction index (`housed_contradiction_index`).
- `pconnect`: edge policy / acceptance probability model used in memory connection handling.
- `mean_edge_delta_e`: periodic edge ethical-distance summary in `kernel_loop.py` CSV.
- `resonance_patterns`: continual-learning resonance telemetry structure.

Important distinction:

- **Demo-only FCE estimate heuristic** is produced by `scripts/kernel_loop.py --demo` and should not be conflated with cultivator `T_cog` telemetry.

---

## Reproducibility minimum pack

When sharing results, include at minimum:

1. `git rev-parse HEAD` commit SHA.
2. Command used (full CLI flags).
3. Provider/model setup (`VERDANT_PROVIDER_CHAIN`, API-backed provider names/models).
4. Run mode (`fresh`, `resume`, `load-state` usage).
5. Cycle count and perturbation settings.
6. For scaffolding analysis: `--topk`, `--trials`, state file path.

Prefer distributions across repeated runs (multi-seed and/or multi-provider) over single-run claims.

- Creation time source is `metadata.creation_time` first, with label timestamp fallback.
- Backbone is built as **top-k weighted edges per node** (union), then largest connected component.
- `earlier-share` compares temporal orientation among emergent↔emergent backbone edges.
- Shuffle trials randomize emergent creation times across the same edge set to estimate a baseline.

## Project layout

| Path | Purpose |
|---|---|
| `Verdant Source Codes/src/core/system.py` | `UnifiedSystem` orchestration and pipeline |
| `Verdant Source Codes/src/blocks/` | Nine processing blocks |
| `Verdant Source Codes/src/memory/` | `MemoryWeb`, `ECWFCore`, `MemoryECWFBridge` |
| `Verdant Source Codes/src/kings/` | `ThreeKingsLayer`, Data/Forefront/Ethics Kings |
| `scripts/verdant_llm_cultivator.py` | multi-cycle cultivation runner |
| `scripts/colab_bootstrap.py` | Colab helper utilities (clone/install/mount/run) |
| `scripts/analysis/scaffolding_from_state.py` | emergent scaffolding analysis |
| `docs/` | end-user documentation |
| `paper/verdant_whitepaper.tex` | primary whitepaper source |
