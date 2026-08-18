# Testing and validating V5

V5 contains two test roots and one important discovery gap:

- `tests/`: 191 engine tests;
- `workbench/backend/tests/`: 67 Workbench tests;
- `pytest.ini` points only to the root `tests/` directory, so plain `pytest -q` does not run Workbench tests;
- `verify_release.py` explicitly lists 11 Workbench files and currently omits two newer files containing six tests.

The complete current branch therefore contains **258 tests**.

## Environment

Follow [INSTALL.md](INSTALL.md), activate the virtual environment, and run from the repository root.

To avoid numerical oversubscription during long validation runs:

```bash
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH=.:workbench/backend
```

PowerShell equivalents:

```powershell
$env:OPENBLAS_NUM_THREADS = "1"
$env:OMP_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:NUMEXPR_NUM_THREADS = "1"
$env:PYTHONPATH = ".;workbench/backend"
```

## Recommended complete validation

Run the established partitioned verifier:

```bash
python verify_release.py
```

On the current branch this exercises 191 engine tests and 61 Workbench tests, then runs the startup/artifact diagnostic: 252 tests total.

Run the two later Workbench files that are not listed by that script:

```bash
python -m pytest -q \
  workbench/backend/tests/test_explorer_worker_timeout_policy.py \
  workbench/backend/tests/test_wb11_curriculum_packs.py
```

Those files contain six tests. Together, the two commands cover all 258 current tests.

For future changes, `.github/workflows/full-suite-validation.yml` is the more complete source of discovery logic: it enumerates every `test_*.py` file under both test roots and executes every collected node in a fresh process.

## Test inventory

### Engine: 191

| Area | Tests |
| --- | ---: |
| Kernel | 9 |
| CognitiveChunk v2 | 5 |
| Language | 8 |
| Claims | 8 |
| ECWF/resonance | 11 |
| Governance | 8 |
| Shards/routing | 13 |
| Objects | 12 |
| Workspace | 12 |
| Media gateway | 10 |
| Sensory | 17 |
| Perception | 11 |
| Development | 7 |
| Plasticity | 9 |
| Earned structures | 8 |
| Compilation | 8 |
| Structure interaction | 8 |
| Hierarchy | 8 |
| Refolding | 9 |
| Oracle-free benchmark | 10 |
| **Total** | **191** |

### Workbench: 67

| Area | Tests |
| --- | ---: |
| Adapter equivalence | 3 |
| Worker/API | 3 |
| Persistence/branching | 4 |
| Live console | 3 |
| Curriculum/grammar | 10 |
| Forensic structures | 6 |
| Living explorer | 7 |
| Experiments | 7 |
| Providers | 5 |
| Plugins/hardening | 8 |
| Release polish | 5 |
| Explorer timeout policy | 3 |
| WB-11 curriculum packs | 3 |
| **Total** | **67** |

## Additional checks

### Package imports and compilation

```bash
PYTHONPATH=.:workbench/backend python -m compileall -q \
  cognitive_chunk_v2 verdant_* workbench/backend/verdant_workbench
```

### Workbench startup and content identity

```bash
PYTHONPATH=.:workbench/backend python run_verdant_workbench.py \
  --home /tmp/verdant-v5-check \
  --check
```

Use a new, empty `--home` directory so verification does not alter checked-in proof fixtures.

### Provider and plugin proofs

The proof programs write output fixtures. Run them in a disposable copy or restore their fixture directory afterward:

```bash
PYTHONPATH=.:workbench/backend python workbench/backend/wb08_proof.py
PYTHONPATH=.:workbench/backend python workbench/backend/wb09_proof.py
```

### Oracle-free benchmark

Always write audit output outside the tracked `artifacts/` directory unless you intend to update the evidence package deliberately:

```bash
python run_ethomorphism_benchmark.py \
  --output /tmp/verdant-v5-oracle-free.json \
  --seed 1901 \
  --state-dim 16 \
  --noise-concepts 16
```

The resulting schema should be `verdant.ethomorphism_benchmark.v2_oracle_free`.

## What passing tests establish

The suite provides strong evidence for deterministic state transitions, integrity checks, explicit evidence boundaries, causal ablation/restoration inside controlled protocols, local Workbench orchestration, and the tested anti-saturation and oracle-separation constraints.

It does not establish general intelligence, consciousness, universal transfer, production security, large-scale performance, real-world autonomous object understanding, or embodiment readiness.
