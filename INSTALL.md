# Install and inspect V2

## Current branch limitation

The tracked code directory is named `verdant/`, but its modules and tests import `verdant_v2`. The `verdant/pyproject.toml` also searches for a child package named `verdant_v2`, which does not exist. `ethomorphic/pyproject.toml` has the same nested-package discovery problem. The root `pyproject.toml` instead packages a nonexistent `usm` directory.

Consequences in a clean checkout:

- `pip install -e .` fails with `package directory 'usm' does not exist`;
- `pip install -e ./verdant` and `pip install -e ./ethomorphic` produce distributions without importable packages;
- `pytest tests_v2` stops during collection because `verdant_v2` is missing;
- the Colab instructions reference a nonexistent `./verdant_v2` path.

The following workaround exposes the current source under the name its imports expect without renaming tracked files.

## Requirements

- Python 3.10 or newer
- `numpy`
- `networkx`
- `pydantic` 2.x
- `pytest` for tests
- `matplotlib` for comparison/analysis figures
- `scipy` and `scikit-learn` for the complete analysis environment

TensorFlow, PyTorch, CUDA, PyJWT, and Werkzeug are not required by the V2 core.

## Linux and macOS workaround

```bash
git clone --branch V2 --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git
cd Verdant-Minds
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "numpy>=1.24" "networkx>=3" "pydantic>=2,<3" pytest matplotlib scipy scikit-learn
mkdir -p .local_import
ln -s "$PWD/verdant" .local_import/verdant_v2
export PYTHONPATH="$PWD/.local_import:$PWD"
```

If `.local_import/verdant_v2` already exists, reuse it instead of creating another link.

## Windows PowerShell workaround

```powershell
git clone --branch V2 --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git
Set-Location Verdant-Minds
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install "numpy>=1.24" "networkx>=3" "pydantic>=2,<3" pytest matplotlib scipy scikit-learn
New-Item -ItemType Directory -Force .local_import
New-Item -ItemType Junction -Path .local_import\verdant_v2 -Target "$PWD\verdant"
$env:PYTHONPATH = "$PWD\.local_import;$PWD"
```

## Verify the core

```bash
python -c "from verdant_v2.system import VerdantSystem; print(VerdantSystem().get_metrics())"
python -m pytest tests_v2 -q
```

## Run an offline cultivation experiment

```bash
python -m cultivation.cli run \
  --cycles 20 \
  --provider local \
  --seeds 0-4 \
  --basin-routing \
  --outdir outputs_v2
```

The deterministic local provider requires no API key. Hosted adapters are optional and require their SDK plus the provider's environment variable:

| Provider | Extra package | Environment variable |
| --- | --- | --- |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` |
| Groq | `groq` | `GROQ_API_KEY` |
| Mistral | `mistralai` | `MISTRAL_API_KEY` |

## Run analysis

```bash
python analysis/run_all.py \
  --state outputs_v2/run_<timestamp>/seed_0/state.json \
  --results-root analysis_output \
  --n-nulls 200 \
  --k 6
```

This command executes, but the current directionality calculation must not be interpreted as directed lineage. Null-model runs also lack a random-seed option and can vary between repetitions. See [docs/reproducibility.md](docs/reproducibility.md).

## What not to use on V2

- Do not use `from usm import UnifiedSyntheticMind`; `usm` is absent.
- Do not run the root console commands declared in `pyproject.toml`; their target is absent.
- Do not install the root heavyweight dependency list merely to inspect V2. It includes unused TensorFlow and PyTorch requirements.
- Do not expect `analysis.depth_age_analysis`; that module is described in a prompt and notebook but is not present.

The correct API is `from verdant_v2.system import VerdantSystem, VerdantConfig` after the import-name workaround.
