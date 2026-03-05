# Verdant-Minds Colab Guide (Drive-Persistent, Code-Aligned)

This guide matches:

- `notebooks/colab_startup_kit.ipynb`
- `scripts/colab_bootstrap.py`
- `scripts/verdant_llm_cultivator.py`

---

## Table of Contents

- [1. Canonical Colab layout](#1-canonical-colab-layout)
- [2. What bootstrap does](#2-what-bootstrap-does)
- [3. Secure provider configuration](#3-secure-provider-configuration)
- [4. Resume vs fresh runtime semantics](#4-resume-vs-fresh-runtime-semantics)
- [5. Commands used by notebook/bootstrap](#5-commands-used-by-notebookbootstrap)
- [6. Output artifacts and file locations](#6-output-artifacts-and-file-locations)
- [7. Scaffolding analysis in Colab](#7-scaffolding-analysis-in-colab)
- [8. Troubleshooting and failure modes](#8-troubleshooting-and-failure-modes)

---

## 1. Canonical Colab layout

The standard layout used by helper scripts is:

- Repo: `/content/Verdant-Minds`
- Drive root: `/content/drive/MyDrive/Verdant/`
- Persistent state: `/content/drive/MyDrive/Verdant/verdant_persistent_state.json`
- Outputs root: `/content/drive/MyDrive/Verdant/outputs/`
- Per-run output directory: `/content/drive/MyDrive/Verdant/outputs/<timestamp>/`

These paths are produced by `mount_drive_and_prepare()` in `scripts/colab_bootstrap.py`.

---

## 2. What bootstrap does

### `ensure_repo()` behavior

What this does:

- If `/content/Verdant-Minds/.git` exists: runs `git pull --ff-only`.
- If directory exists but is not a repo: raises an error.
- Else: clones from repo URL into `/content/Verdant-Minds`.

### `install_deps()` behavior

What this does:

1. Installs `requirements.txt` if present.
2. Installs Colab helper dependencies:
   - `networkx`
   - `python-louvain`
   - `PyYAML`
   - `psutil`
   - `sentence-transformers`
   - `scikit-learn`
   - `groq`
   - `mistralai`
   - `matplotlib`

### `mount_drive_and_prepare()` behavior

What this does:

- Mounts Google Drive at `/content/drive` when running under Colab.
- Creates Drive root and `outputs/` directories if missing.
- Returns `drive_root`, `state_path`, `baseline_path`, and `outputs_root`.

---

## 3. Secure provider configuration

Do **not** place API keys directly in notebook source.

Recommended options:

1. Colab Secrets / runtime environment variables.
2. Runtime `getpass` prompts for missing keys.

Supported keys in notebook helper cell:

- `MISTRAL_API_KEY`
- `GROQ_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`

Provider ordering uses:

- `VERDANT_PROVIDER_CHAIN` (example: `mistral,groq,anthropic,openai,local`)

## 3) Fresh vs resume behavior

## 4. Resume vs fresh runtime semantics

Bootstrap `run_cultivator_loop()` logic:

- If persistent state file exists:
  - pass `--load-state <state_path>` (resume from state)
  - continue with existing graph/ECWF trajectory from that state file
- Else:
  - pass `--initialize-knowledge --fresh` (new run)

Implementation note: in cultivator code, initialization is only enabled when `--initialize-knowledge` is set and `--load-state` is not set.

Every run additionally passes:

- `--save-state <state_path>`
- `--output-dir <run_out_dir>`

Interpretation rule:

- A resumed 20-cycle segment is a continuation over persisted graph and history. It is **not** equivalent to a fresh 20-cycle run.

---

## 5. Commands used by notebook/bootstrap

### Cultivation command pattern

What this does: executes one run with configured cycle budget and output directory.

```bash
python /content/Verdant-Minds/scripts/verdant_llm_cultivator.py \
  --cycles 40 \
  --seed-topic contradiction \
  --perturbation-interval 10 \
  --save-state /content/drive/MyDrive/Verdant/verdant_persistent_state.json \
  --output-dir /content/drive/MyDrive/Verdant/outputs/<timestamp> \
  [--load-state /content/drive/MyDrive/Verdant/verdant_persistent_state.json \
   OR --initialize-knowledge --fresh]
```

### Optional scaffolding command

What this does: computes emergent scaffolding metrics and writes two PNGs.

```bash
python /content/Verdant-Minds/scripts/analysis/scaffolding_from_state.py \
  --state /content/drive/MyDrive/Verdant/verdant_persistent_state.json \
  --topk 6 \
  --trials 500
```

---

## 6. Output artifacts and file locations

With `--output-dir /content/drive/MyDrive/Verdant/outputs/<timestamp>`, each cultivation run writes:

- `cultivation_session_<stamp>.json`
- `cultivation_cycles_<stamp>.jsonl`
- `cultivation_state_<stamp>.json`
- `significant_events_<stamp>.json`

And also writes persistent state to:

- `/content/drive/MyDrive/Verdant/verdant_persistent_state.json` via `--save-state`

---

## 7. Scaffolding analysis in Colab

`scripts/analysis/scaffolding_from_state.py` specifics:

- Creation time source: `metadata.creation_time` first.
- Fallback: parse timestamp-like numeric suffix in concept label.
- Graph model: weighted undirected graph from memory connections.
- Backbone: top-k weighted incident edges per node, then largest connected component.
- EE selection: only emergent↔emergent edges in backbone are analyzed.
- Metric: `earlier-share` (newer→older orientation share, excluding exact ties).
- Baseline: shuffled creation-time trials with fixed edge structure.

Outputs (by default near state file unless `--outdir` is provided):

- Creation time source: `metadata.creation_time` primary; label timestamp fallback.
- Backbone construction: top-k weighted incident edges per node, then largest connected component.
- `earlier-share`: among emergent↔emergent backbone edges, share oriented from newer to older.
- Shuffling: randomizes emergent creation times across fixed edge structure to estimate baseline.

## 6) Reproducibility checklist

## 8. Troubleshooting and failure modes

### Drive mount instability

- Re-run mount cell.
- If still unstable, restart runtime and execute notebook from top.

### Dependency conflicts

- Restart runtime and rerun install cell.
- Keep notebook/install sequence unchanged to avoid partial environment drift.

### Repo folder conflict

If `/content/Verdant-Minds` exists without `.git`, remove/rename it before rerunning clone/update cell.

### Provider limits / rate limits

Cultivator has fallback handling; still record provider errors in run notes for reproducibility.
