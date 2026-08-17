# Verdant-V0 Colab and Drive Guide

The included notebook/bootstrap helpers are designed for a repository at `/content/Verdant-Minds` and persistent state under Google Drive. One branch-specific caveat matters: `ensure_repo()` clones or pulls the repository’s configured/default branch; it does not independently guarantee `Verdant-V0`.

## Pin the intended branch first

For a clean Colab session:

```bash
!git clone --branch Verdant-V0 --single-branch \
  https://github.com/captainkoopa42/Verdant-Minds.git \
  /content/Verdant-Minds
%cd /content/Verdant-Minds
!git branch --show-current
```

If the repository already exists, inspect it before switching because local notebook changes may be present:

```bash
%cd /content/Verdant-Minds
!git status --short
!git branch --show-current
```

Only switch to `Verdant-V0` when the working tree is in a state you intend to keep. The bootstrap helper’s `git pull --ff-only` updates the currently checked-out branch; it does not choose V0 for you.

## Standard paths

| Purpose | Path |
|---|---|
| repository | `/content/Verdant-Minds` |
| Drive root | `/content/drive/MyDrive/Verdant/` |
| persistent state | `/content/drive/MyDrive/Verdant/verdant_persistent_state.json` |
| outputs root | `/content/drive/MyDrive/Verdant/outputs/` |
| per-run output | `/content/drive/MyDrive/Verdant/outputs/<timestamp>/` |

These are returned by `mount_drive_and_prepare()` in `scripts/colab_bootstrap.py`.

## Bootstrap behavior

`ensure_repo()`:

- runs `git pull --ff-only` if the target is already a Git repository;
- raises an error if the target exists but is not a repository;
- otherwise clones the configured repository URL.

`install_deps()` installs `requirements.txt` and helper packages for graph analysis, configuration, providers, embedding mapping, and plotting.

`mount_drive_and_prepare()` mounts Drive in Colab, creates persistent directories, and returns the state/output paths.

## Secrets

Use Colab Secrets or runtime environment variables. Do not put values into the notebook, repository, output JSON, or documentation.

Recognized provider-key names include:

- `MISTRAL_API_KEY`
- `GROQ_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`

Provider order can be set with `VERDANT_PROVIDER_CHAIN`, for example `mistral,groq,local`.

## Fresh and resumed behavior

The bootstrap cultivation helper behaves as follows:

- if the persistent state exists, it passes `--load-state`;
- otherwise it passes `--initialize-knowledge --fresh`;
- every run passes `--save-state` and a timestamped `--output-dir`.

State loading and cycle-log resume are separate. The bootstrap’s persistent-state path continues graph/ECWF/system state. Use `--resume` explicitly when cycle-history context is also required.

## Equivalent cultivation command

```bash
!python /content/Verdant-Minds/scripts/verdant_llm_cultivator.py \
  --cycles 40 \
  --seed-topic contradiction \
  --perturbation-interval 10 \
  --save-state /content/drive/MyDrive/Verdant/verdant_persistent_state.json \
  --output-dir /content/drive/MyDrive/Verdant/outputs/<timestamp> \
  --initialize-knowledge \
  --fresh
```

For a later segment, replace the final two flags with:

```bash
--load-state /content/drive/MyDrive/Verdant/verdant_persistent_state.json
```

## Analysis in Colab

```bash
!python /content/Verdant-Minds/scripts/analysis/scaffolding_from_state.py \
  --state /content/drive/MyDrive/Verdant/verdant_persistent_state.json \
  --topk 6 \
  --trials 500 \
  --outdir /content/drive/MyDrive/Verdant/outputs/analysis
```

This writes `emergent_scaffolding.png` and `link_age_gaps.png`.

## Operational checks

Before a long provider-backed run:

```bash
!git branch --show-current
!python --version
!python -m pytest -q
!python scripts/verdant_llm_cultivator.py --help
```

Confirm Drive is mounted, the state path is correct, the output directory is writable, and the provider/model/token settings are recorded. A resumed run is trajectory-dependent and should never be reported as an equivalent fresh run.
