# Verdant-Minds

**Verdant-Minds** is a modular cognitive architecture with graph memory (`MemoryWeb`), a wave-state core (`ECWFCore`), and governance (`ThreeKingsLayer`) orchestrated by `UnifiedSystem` (exported as `UnifiedSyntheticMind`).

## What this repository contains

- A runnable nine-block processing pipeline.
- Scripted modes for REPL, telemetry, demo kernel loop, and LLM-driven cultivation.
- JSON state persistence and resume support.
- Post-run structural analysis for emergent concept scaffolding.
- Whitepaper sources in `paper/`.

## Canonical component names

This repo uses these names consistently in code and docs:

- `UnifiedSystem` (`usm.UnifiedSyntheticMind` alias)
- `MemoryWeb`
- `ECWFCore`
- `MemoryECWFBridge`
- `ThreeKingsLayer`
- `CognitiveChunk`

## Quick start

### Install

What this does: installs runtime dependencies for scripts and tests.

```bash
pip install -r requirements.txt
```

### Run interactive loop

What this does: starts a local prompt loop backed by `UnifiedSyntheticMind`.

```bash
python scripts/verdant_repl.py
```

### Run telemetry loop

What this does: prints per-input structured telemetry (text table or JSON).

```bash
python scripts/verdant_telemetry.py
# or
python scripts/verdant_telemetry.py --json
```

## Cultivation loop (`scripts/verdant_llm_cultivator.py`)

What this does: runs cycle-based LLM prompting with telemetry capture, provider fallback, optional phase perturbation, and state save/load.

### Minimal example

```bash
export GROQ_API_KEY=...    # or MISTRAL_API_KEY / ANTHROPIC_API_KEY
python scripts/verdant_llm_cultivator.py --cycles 20 --seed-topic contradiction
```

### Fresh vs resume (important)

- **Fresh run**: starts a new cycle sequence and ignores prior cycle logs (`--fresh`).
- **Resume run**: continues from prior cycle logs and/or state (`--resume` and/or `--load-state`).
- **“20 cycles resumed”** means: 20 additional cycles on top of persisted state/history, **not** a from-scratch 20-cycle experiment.

## Metrics glossary (script-facing)

- `T_g`: glass-transition control signal from processing metrics.
- `T_cog` (cultivator telemetry): `1 - T_g + system_entropy`.
- `HCI`: housed contradiction index from coherence invariants.
- `pconnect`: edge acceptance probability used in ethical-distance-aware connection logic.
- `mean_delta_e`: mean ethical edge distance (logged as `mean_edge_delta_e` in `scripts/kernel_loop.py`).
- `resonance_patterns`: continual-learning resonance summary (reported as `pattern_count` in telemetry).

### Demo-only FCE note

`scripts/kernel_loop.py --demo` computes an **FCE estimate heuristic** for the demo report. Treat it as demo-only and do not conflate it with `T_cog` in cultivator telemetry.

## Emergent scaffolding analysis

What this does: analyzes emergent-to-emergent structure in a persisted `MemoryWeb` state.

```bash
python scripts/analysis/scaffolding_from_state.py \
  --state outputs/cultivation_state_YYYYMMDD_HHMMSS.json \
  --topk 6 \
  --trials 500
```

Interpretation:

- Creation time source is `metadata.creation_time` first, with label timestamp fallback.
- Backbone is built as **top-k weighted edges per node** (union), then largest connected component.
- `earlier-share` compares temporal orientation among emergent↔emergent backbone edges.
- Shuffle trials randomize emergent creation times across the same edge set to estimate a baseline.

## Reproducibility guidance

- Report seeds and run mode (`fresh` vs `resume`).
- Report provider chain (`VERDANT_PROVIDER_CHAIN`) and cycle count.
- Prefer distributions across repeated runs over single-run conclusions.
- If sharing results, label them as **example output** unless reproduced in your run artifacts.

## Limitations

- LLM provider behavior is nondeterministic and can shift results across runs.
- Some analyses depend on logging/state schema shape.
- Resume mode changes trajectory by reusing persisted memory and cycle history.

## Colab

Use `docs/colab.md` and `notebooks/colab_startup_kit.ipynb` for a Drive-persistent workflow rooted at:

- `/content/Verdant-Minds`
- `/content/drive/MyDrive/Verdant/`

## Whitepaper source

- `paper/verdant_whitepaper.tex`
