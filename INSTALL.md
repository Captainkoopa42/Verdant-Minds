# Installing Verdant-V0

The reliable installation model for this branch is a checked-out source tree plus an editable install. Do not rely on the current wheel as a standalone package: it omits the `Verdant Source Codes` directory used by `usm`.

## Supported baseline

- Linux, macOS, or Windows
- a current Python 3 environment; the audit was performed with Python 3.12
- a virtual environment is strongly recommended
- no GPU is required for the canonical V0 runtime or tests

## Exact branch setup

```bash
git clone --branch Verdant-V0 --single-branch \
  https://github.com/captainkoopa42/Verdant-Minds.git
cd Verdant-Minds

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

On Windows PowerShell, activate with:

```powershell
.venv\Scripts\Activate.ps1
```

Why both steps? `requirements.txt` describes the branch runtime, while `-e . --no-deps` registers the `usm` entry point without forcing the inconsistent dependency list declared by the packaging metadata.

## Verify the installation

```bash
python -c "from usm import UnifiedSyntheticMind; print(UnifiedSyntheticMind)"
python -m usm
```

The second command should initialize the system and display a `>` prompt. Type `exit` to leave.

Run the full verification suite:

```bash
python -m pytest -q
```

The documentation audit observed 121 passing tests. See [TESTING.md](TESTING.md) for scope and warnings.

## Lighter local setup

If the full requirements file is too heavy, the core architecture and tests can be brought up with the packages exercised by the branch, then installed editable:

```bash
python -m pip install numpy scipy networkx python-louvain pyyaml psutil \
  matplotlib pytest groq
python -m pip install -e . --no-deps
```

Some paths may require additional provider-specific packages. `sentence-transformers` and scikit-learn improve semantic concept mapping but are optional at runtime; without them the bridge uses its fallback mapping.

## Provider-backed cultivation

The cultivation runner can use external model providers. Install the adapter you plan to use and provide keys through environment variables, not source files.

```bash
python scripts/verdant_llm_cultivator.py --help
```

Common keys include `GROQ_API_KEY`, `MISTRAL_API_KEY`, `ANTHROPIC_API_KEY`, and `OPENAI_API_KEY`. Provider selection is controlled by `VERDANT_PROVIDER_CHAIN` and runner configuration. A local fallback path also exists.

## Packaging warning

The branch currently has three metadata sources with inconsistent version/dependency declarations:

- `pyproject.toml`
- `setup.cfg`
- `setup.py`

A wheel built during the audit contained `usm` and package metadata, but not the canonical core under `Verdant Source Codes`. Editable installation works because it refers back to the checkout. This is a packaging defect, not a failure of the checked-out runtime.

## Troubleshooting

### `No module named src`

Confirm you are using the checkout and that `usm/__init__.py` is present. Re-run:

```bash
python -m pip install -e . --no-deps
```

### Semantic mapper warning

Install the optional stack if you need embedding/PCA mapping:

```bash
python -m pip install sentence-transformers scikit-learn
```

Otherwise the warning is expected and the fallback mapper remains usable.

### Provider import or authentication failure

Install the matching provider SDK, confirm its environment variable is set in the current shell, and use `--help` to verify the runner’s available flags. Never commit an API key.

### Graph community detection import error

The import name is `community`, but the package installed from PyPI is `python-louvain`:

```bash
python -m pip install python-louvain
```
