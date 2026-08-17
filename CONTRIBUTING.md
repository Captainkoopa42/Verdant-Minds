# Contributing to Verdant-Minds

Verdant-Minds is organized as a sequence of browsable research-generation branches. Before changing anything, identify which generation the work belongs to and inspect that branch as a complete system.

This guide is specifically aligned with `Verdant-V0`.

## Branch and research-generation rule

Branches such as `Verdant-V0`, `V4`, `V5`, and experimental branches such as `V5-X` are not interchangeable containers. They present different generations or experimental states of the research.

When contributing:

- preserve the target branch's architecture and vocabulary;
- do not silently import claims or instructions from a later generation;
- do not assume older branches are untouched historical snapshots—later tests, research notes, and support tooling may have been added;
- document whether a change belongs to the original architecture, a later addition, or supporting research tooling;
- keep generated experiment artifacts out of documentation changes unless they are intentionally being published as evidence.

See [docs/branch-history.md](docs/branch-history.md) for how this applies to `Verdant-V0`.

## Canonical V0 code path

Use:

```python
from usm import UnifiedSyntheticMind
```

This resolves to `UnifiedSystem` in `Verdant Source Codes/src/core/system.py` and its lower-case modules.

Do not treat the top-level `verdant/` directory as the V0 runtime. It is incomplete on this branch because its required `ethomorphic` package is absent.

## Development setup

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

Windows PowerShell activation:

```powershell
.venv\Scripts\Activate.ps1
```

The editable source installation is intentional. The current standalone wheel does not include the canonical `Verdant Source Codes` runtime. Read [INSTALL.md](INSTALL.md) before changing packaging or dependencies.

## Before making a change

1. Read [README.md](README.md), [STATUS.md](STATUS.md), and [docs/architecture.md](docs/architecture.md).
2. Confirm the target behavior exists in the canonical lower-case module.
3. Search for parallel upper-case copies so you do not edit the wrong file.
4. Run the relevant existing test before changing the behavior.
5. Decide what evidence will show that the change works.

Useful searches:

```bash
rg "class UnifiedSystem|def process_input" "Verdant Source Codes/src"
rg "TargetFunctionOrClass" .
python -m pytest --collect-only -q
```

## Change categories

### Runtime changes

Runtime changes should identify:

- the affected block, memory component, King, bridge, or persistence path;
- which `CognitiveChunk` sections are read and written;
- whether the change affects current-cycle or next-cycle feedback;
- whether saved JSON state remains compatible;
- whether results depend on embedding/PCA mapping or the fallback mapper.

### Experiment changes

Experiment work should record:

- branch and local modification state;
- Python/dependency environment;
- seed and runtime configuration;
- exact command and input sequence;
- provider/model settings without secrets;
- fresh or resumed state/history;
- artifacts and analysis parameters.

Follow [docs/reproducibility.md](docs/reproducibility.md).

### Documentation changes

Documentation must distinguish:

- implemented behavior;
- behavior covered by tests;
- behavior directly rerun during an audit;
- results reported by the whitepaper;
- simulated terminal output;
- sample visualization data.

Do not convert a proposed design into a statement about working code.

## Testing

Run the complete suite:

```bash
python -m pytest -q
```

The documentation audit observed 121 passing tests and 38 `datetime.utcnow()` deprecation warnings. Test counts may grow, so collection output remains the live inventory:

```bash
python -m pytest --collect-only -q
```

For focused work:

```bash
python -m pytest tests/test_system_integration.py -vv
python -m pytest tests/test_persistence_smoke.py -vv
python -m pytest tests/test_coherence_feedback_loop.py -vv
```

See [TESTING.md](TESTING.md) and [tests/README.md](tests/README.md).

## Code expectations

- Preserve existing public interfaces unless the change explicitly includes a migration.
- Use type hints where they clarify data boundaries.
- Add tests for corrected or new behavior.
- Avoid network-dependent tests for the canonical runtime.
- Do not silently swallow state-loading or provider failures.
- Keep API keys and personal data out of source, logs, notebooks, and artifacts.
- Use the configured Black line length of 100 characters when formatting new Python.
- Avoid mechanical reformatting of unrelated historical files.

## Reporting a problem

Include:

- branch name;
- affected file and interface;
- Python/platform information;
- exact command or minimal Python example;
- expected and observed behavior;
- full traceback or relevant telemetry;
- whether optional semantic dependencies were installed;
- whether prior state or cycle history was loaded.

## Proposing a change

Explain:

1. what is changing;
2. why it belongs in this research generation;
3. which architecture boundary it affects;
4. how it was tested;
5. which documentation or walkthrough must change with it;
6. what the result does and does not establish.

For substantial documentation replacements, present the complete proposed files for review before publishing them.

## Research conduct

Critique claims and implementations directly while treating contributors respectfully. Verdant-Minds is experimental research; uncertainty, failed experiments, negative results, and branch-specific limitations should be recorded rather than hidden.
