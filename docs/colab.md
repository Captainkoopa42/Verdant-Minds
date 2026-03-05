# Colab startup guide (Drive-persistent)

This guide matches `notebooks/colab_startup_kit.ipynb` and `scripts/colab_bootstrap.py`.

## Paths used by default

- Repo path: `/content/Verdant-Minds`
- Drive root: `/content/drive/MyDrive/Verdant/`
- Persistent state file: `/content/drive/MyDrive/Verdant/verdant_persistent_state.json`
- Per-run outputs: `/content/drive/MyDrive/Verdant/outputs/<timestamp>/`

## 1) Open notebook and run top-to-bottom

What this does: clones/updates the repo, installs dependencies, mounts Drive, runs cultivator loops, and prints a post-run summary.

Notebook: `notebooks/colab_startup_kit.ipynb`

## 2) Configure API keys safely

What this does: reads keys from environment/Colab Secrets and prompts only for missing keys.

Do **not** put keys in plain text notebook cells.

Supported keys:

- `MISTRAL_API_KEY`
- `GROQ_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`

Provider order is controlled by `VERDANT_PROVIDER_CHAIN` (example: `mistral,groq,anthropic,openai,local`).

## 3) Fresh vs resume behavior

What this does: decides whether each run starts from existing state.

- If state file exists: run uses `--load-state <state>` (resume).
- If state file is missing: run uses `--initialize-knowledge --fresh`.
- Every run writes `--save-state /content/drive/MyDrive/Verdant/verdant_persistent_state.json`.

Important interpretation note:

- A resumed 20-cycle segment analyzes the persisted graph and history. It is **not** equivalent to a new 20-cycle from-scratch experiment.

## 4) Cultivator command used

What this does: runs one cycle loop and writes outputs/state.

```bash
python /content/Verdant-Minds/scripts/verdant_llm_cultivator.py \
  --cycles 40 \
  --seed-topic contradiction \
  --perturbation-interval 10 \
  --save-state /content/drive/MyDrive/Verdant/verdant_persistent_state.json \
  --output-dir /content/drive/MyDrive/Verdant/outputs/<timestamp> \
  [--load-state <state> OR --initialize-knowledge --fresh]
```

## 5) Scaffolding analysis command

What this does: measures temporal orientation in emergent↔emergent backbone edges and generates two plots.

```bash
python /content/Verdant-Minds/scripts/analysis/scaffolding_from_state.py \
  --state /content/drive/MyDrive/Verdant/verdant_persistent_state.json \
  --topk 6 \
  --trials 500
```

Method details:

- Creation time source: `metadata.creation_time` primary; label timestamp fallback.
- Backbone construction: top-k weighted incident edges per node, then largest connected component.
- `earlier-share`: among emergent↔emergent backbone edges, share oriented from newer to older.
- Shuffling: randomizes emergent creation times across fixed edge structure to estimate baseline.

## 6) Reproducibility checklist

When reporting outcomes, include:

- run mode (`fresh` or `resume`)
- cycle count
- provider chain
- `topk` and shuffle `trials` for scaffolding analysis
- whether results are single-run examples or distribution summaries

## 7) Troubleshooting

- Re-run mount cell if Drive disconnects.
- If dependencies conflict, restart runtime and rerun from cell 1.
- If `/content/Verdant-Minds` exists but is not a git repo, remove/rename it before rerunning.
