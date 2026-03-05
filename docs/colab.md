# Colab Startup Kit (Drive-Persistent)

Use this guide to run Verdant-Minds in Google Colab with persistent state and outputs in Google Drive.

## What you get

- Idempotent clone/update into `/content/Verdant-Minds`
- Dependency installation for Verdant + analysis tools
- Google Drive mount + persistent folder setup
- Resume-if-state-exists, otherwise fresh initialization
- Multi-run cultivation loop
- Post-run quick summary and scaffolding plots

Notebook: `notebooks/colab_startup_kit.ipynb`

---

## 1) Open the notebook in Colab

1. In GitHub, open `notebooks/colab_startup_kit.ipynb`.
2. Click **Open in Colab** (or copy notebook into Colab manually).
3. Run cells top-to-bottom.

The notebook uses `scripts/colab_bootstrap.py` so setup logic stays centralized.

---

## 2) Configure API keys safely (no hardcoded secrets)

Do **not** place keys directly in notebook cells.

Use one of these:

- **Colab Secrets** (recommended), or
- Runtime prompt via `getpass`:

```python
import getpass, os
os.environ["MISTRAL_API_KEY"] = getpass.getpass("MISTRAL_API_KEY: ")
```

The notebook prompts only for missing keys and supports:

- `MISTRAL_API_KEY`
- `GROQ_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`

Provider ordering is controlled by:

- `VERDANT_PROVIDER_CHAIN` (example: `mistral,groq,anthropic,openai,local`)

---

## 3) Drive persistence layout

Base folder:

- `/content/drive/MyDrive/Verdant`

Default files/folders:

- State: `/content/drive/MyDrive/Verdant/verdant_persistent_state.json`
- Optional baseline reference: `/content/drive/MyDrive/Verdant/verdant_v1_baseline_verified_16emergents.json`
- Outputs root: `/content/drive/MyDrive/Verdant/outputs/<timestamp>/`

If the folder does not exist, bootstrap creates it.

---

## 4) Resume vs fresh behavior

Each run always writes:

- `--save-state /content/drive/MyDrive/Verdant/verdant_persistent_state.json`

Startup mode is automatic:

- If state exists: uses `--load-state <state>` (resume)
- If state does not exist: uses `--initialize-knowledge --fresh` (new run)

This makes reruns safe and idempotent.

---

## 5) Run loop settings

Notebook exposes these settings (env-driven):

- `VERDANT_N_RUNS` (default `2`)
- `VERDANT_CYCLES` (default `40`)
- `VERDANT_SEED_TOPIC` (default `contradiction`)
- `VERDANT_PERTURB_INTERVAL` (default `10`)

Underlying command per run:

```bash
python /content/Verdant-Minds/scripts/verdant_llm_cultivator.py \
  --cycles 40 \
  --seed-topic contradiction \
  --perturbation-interval 10 \
  [--load-state <state> OR --initialize-knowledge --fresh] \
  --save-state /content/drive/MyDrive/Verdant/verdant_persistent_state.json \
  --output-dir /content/drive/MyDrive/Verdant/outputs/<timestamp>
```

---

## 6) Quick checks and analysis

After runs, notebook helper prints:

- total memory concepts
- top `access_count` concepts
- wave-emergent concept list ordered by `creation_time`

For scaffolding metrics + plots:

```bash
python scripts/analysis/scaffolding_from_state.py --state <path-to-state> --topk 6 --trials 500
```

Outputs saved near the state file by default:

- `emergent_scaffolding.png`
- `link_age_gaps.png`

---

## 7) Troubleshooting

### Drive mount fails or disconnects

- Re-run the mount/configure cell.
- Ensure Colab has permission to access your Google Drive.
- If mount seems stale, restart runtime and run setup cells again.

### `pip` dependency conflicts

- Re-run dependency cell once.
- If still conflicted, use a fresh runtime and run cells from the top.

### Repo already exists errors

- Bootstrap checks `/content/Verdant-Minds`.
- If it is a valid git repo, it runs `git pull --ff-only`.
- If the directory exists but is not a repo, remove/rename the folder and rerun clone/update cell.

### Missing baseline warning

- The baseline file is optional.
- Place `verdant_v1_baseline_verified_16emergents.json` in `MyDrive/Verdant/` if you need baseline comparisons.
