# Reproducibility Guide

This guide defines a minimum reporting standard for experiments run from this repository.

---

## Table of Contents

- [1. Why this is needed](#1-why-this-is-needed)
- [2. Minimum reproducibility pack](#2-minimum-reproducibility-pack)
- [3. Fresh vs resume reporting standard](#3-fresh-vs-resume-reporting-standard)
- [4. Cultivator run template](#4-cultivator-run-template)
- [5. Scaffolding analysis template](#5-scaffolding-analysis-template)
- [6. Multi-run reporting recommendations](#6-multi-run-reporting-recommendations)

---

## 1. Why this is needed

Cultivation and provider-backed runs can vary due to:

- provider nondeterminism,
- resume-state trajectory dependence,
- configuration differences across runs.

For this reason, single-run results should be labeled as example outputs unless replicated.

---

## 2. Minimum reproducibility pack

Include the following in every report:

1. **Code version**
   - `git rev-parse HEAD`
2. **Exact commands**
   - full CLI command with all flags
3. **Provider context**
   - `VERDANT_PROVIDER_CHAIN`
   - provider model names (`GROQ_MODEL`, `MISTRAL_MODEL`, etc.)
4. **Run mode**
   - whether `--fresh`, `--resume`, and/or `--load-state` were used
5. **Cycle configuration**
   - cycle count, perturbation settings, budget mode
6. **Artifacts**
   - session JSON, cycle JSONL, state JSON, significant events JSON paths
7. **Analysis configuration**
   - scaffolding `--topk` and `--trials`

---

## 3. Fresh vs resume reporting standard

Use these exact labels:

- **fresh**: no prior cycle history/state loaded for this run segment.
- **resumed-state**: `--load-state` used.
- **resumed-cycles**: `--resume` used (with `--fresh` unset).
- **resumed-state+cycles**: both used; state load and cycle-history resume are both active inputs.

Interpretation requirement:

- “N resumed cycles” means continuation over prior trajectory, not a fresh N-cycle experiment.

---

## 4. Cultivator run template

Example command template:

```bash
python scripts/verdant_llm_cultivator.py \
  --cycles 40 \
  --seed-topic contradiction \
  --perturbation-interval 10 \
  --budget-mode light \
  --output-dir outputs/run_A \
  --save-state outputs/run_A/persistent_state.json
```

Report these fields with the command:

| Field | Example |
|---|---|
| commit | `330a868...` |
| provider chain | `mistral,groq,local_fallback` |
| model flag | `--model claude-3-5-sonnet-latest` |
| run mode | `fresh` / `resumed-state` / etc. |
| artifacts dir | `outputs/run_A` |

---

## 5. Scaffolding analysis template

Example command template:

```bash
python scripts/analysis/scaffolding_from_state.py \
  --state outputs/run_A/cultivation_state_YYYYMMDD_HHMMSS.json \
  --topk 6 \
  --trials 500 \
  --outdir outputs/run_A/analysis
```

Expected generated files:

- `emergent_scaffolding.png`
- `link_age_gaps.png`

Record at least:

- state path,
- top-k value,
- trials count,
- printed `earlier-share`, shuffle mean/std, and z-score.

---

## 6. Multi-run reporting recommendations

Recommended minimum for claims:

1. Run at least 3 independent fresh runs per provider setting.
2. Run at least 3 resumed segments if resume effects are part of the study.
3. Report distribution summaries (mean ± std) for key metrics.
4. Keep single-run narratives explicitly labeled as representative examples.
