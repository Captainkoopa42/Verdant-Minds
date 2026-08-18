# Install and run Verdant Minds V5

This guide supplements the existing V5 README without changing it. V5 runs directly from the repository source tree; the branch does not contain a `pyproject.toml` or another installable project definition.

## Requirements

- Python 3.11 or newer
- A local filesystem location for checkpoints, imported media, and Workbench data
- The pinned direct Python dependencies in `requirements-lock.txt`

The checked-in Workbench browser build does not require Node.js or npm. Node tooling is only relevant if you intend to rebuild the React/TypeScript frontend from `workbench/frontend/src/`.

## Linux and macOS

```bash
git clone --branch V5 --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git
cd Verdant-Minds
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
```

Verify imports and start the local laboratory:

```bash
PYTHONPATH=.:workbench/backend python run_verdant_workbench.py --check
PYTHONPATH=.:workbench/backend python run_verdant_workbench.py --open-browser
```

The default URL is `http://127.0.0.1:8765/`.

## Windows PowerShell

```powershell
git clone --branch V5 --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git
Set-Location Verdant-Minds
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
$env:PYTHONPATH = ".;workbench/backend"
python run_verdant_workbench.py --check
python run_verdant_workbench.py --open-browser
```

## Why `PYTHONPATH` is used

The engine packages such as `verdant_kernel`, `verdant_sensory`, and `verdant_structures` live directly at the repository root. The Workbench package lives at `workbench/backend/verdant_workbench`. Adding the root and backend directories to `PYTHONPATH` exposes both package groups without changing the source tree.

Root engine commands already see the repository root when launched from it. Workbench commands need the additional backend path.

## Main entry points

| Command | Purpose |
| --- | --- |
| `PYTHONPATH=.:workbench/backend python run_verdant_workbench.py --open-browser` | Launch the local Workbench UI and API |
| `PYTHONPATH=.:workbench/backend python run_verdant_workbench.py --check` | Run startup, source-identity, provider/plugin, and artifact diagnostics |
| `python run_verdant_media.py --input PATH --output-dir DIR` | Preserve and, when supported, translate user media |
| `python run_verdant_cultivation.py` | Open the hand-driven Milestone 14–18 cultivation shell |
| `python run_ethomorphism_benchmark.py --output PATH` | Run the current oracle-free Milestone 19 benchmark |
| `python verify_release.py` | Run the historical release verifier and startup diagnostic |

See [TESTING.md](TESTING.md) before relying on `verify_release.py` alone: the current branch contains six later Workbench tests that script does not discover.

## Workbench data location

By default, Workbench writes local laboratory data to `.verdant-workbench/`. Use an explicit location when you want isolation or easy cleanup:

```bash
PYTHONPATH=.:workbench/backend python run_verdant_workbench.py \
  --home ./my-verdant-lab \
  --port 8765 \
  --open-browser
```

The Workbench database and event ledger organize laboratory activity. Canonical cognitive state is stored in verified `.vdk` checkpoints.

## Security boundary

Keep the default loopback host unless you are deliberately building a protected deployment. Workbench has no production multi-user authentication layer. Provider secrets are referenced through environment variables, and plugins run in subprocesses, but the plugin system is not an operating-system sandbox. Do not expose the server publicly or run untrusted plugins.

## Full verification

The current checked-out branch contains 258 tests: 191 engine tests and 67 Workbench tests. Use [TESTING.md](TESTING.md) for the exact verified procedure and the distinction between current branch evidence and historical release records.
