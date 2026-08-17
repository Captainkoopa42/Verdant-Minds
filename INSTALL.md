# Install and run V1

## Requirements

- Python 3.10 or newer is recommended.
- A CPU is sufficient. V1 does not import TensorFlow, PyTorch, CUDA, or a quantum-computing runtime.

Core runtime packages:

- `numpy`
- `networkx`
- `matplotlib` for reports produced by the runners

Additional packages by feature:

- `pytest` for the included tests
- `python-louvain` for optional community detection in `MemoryWeb`
- `PyJWT` and `Werkzeug` for the isolated authentication prototype

The branch has no dependency manifest, so these commands install the dependencies directly.

## Linux and macOS

```bash
git clone --branch V1 --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git
cd Verdant-Minds
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install numpy networkx matplotlib pytest
```

Optional features:

```bash
python -m pip install python-louvain PyJWT Werkzeug
```

## Windows PowerShell

```powershell
git clone --branch V1 --single-branch https://github.com/Captainkoopa42/Verdant-Minds.git
Set-Location Verdant-Minds
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install numpy networkx matplotlib pytest
```

## Run the diagnostic entry point

The root runner configures the repository import path itself:

```bash
python verdant_monolithic_test_runner.py --user-input "What makes a decision fair?"
```

Run its ten automated cycles:

```bash
python verdant_monolithic_test_runner.py
```

Run the interactive loop and type `exit` when finished:

```bash
python verdant_loop_controller.py
```

Both runners write reports to `verdant_test_output/`. The interactive loop also writes metrics through `VerdantMetricsLogger`.

## Import the Python API directly

The import root is the directory named `Verdant Source Codes`.

Linux or macOS:

```bash
PYTHONPATH="Verdant Source Codes" python -c "from src.core.system import UnifiedSystem; print(UnifiedSystem().get_response('Hello'))"
```

Windows PowerShell:

```powershell
$env:PYTHONPATH = "$PWD\Verdant Source Codes"
python -c "from src.core.system import UnifiedSystem; print(UnifiedSystem().get_response('Hello'))"
```

## Not supported by this branch

Do not use `pip install -r requirements.txt` or `pip install -e .`; the required files are absent. There is no `config.py` to edit and no `usm` package or `UnifiedSyntheticMind.initialize()` API.
