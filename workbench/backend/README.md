# Verdant Workbench Backend — 1.0.1 / V5

This is the local-first control plane for the Verdant Minds V5 research release. It wraps the M19 cognitive engine through stable adapter, worker, persistence, curriculum, forensic, explorer, experiment, provider, and plugin contracts.

Core rule: **the UI commands the engine; the UI does not contain cognition.**

Launch from the repository root:

```bash
PYTHONPATH=.:workbench/backend python run_verdant_workbench.py
```

Release diagnostic:

```bash
PYTHONPATH=.:workbench/backend python run_verdant_workbench.py --check
```

Full release verification:

```bash
python verify_release.py
```

The canonical cognitive state remains in Verdant `.vdk` checkpoints. Workbench SQLite and event ledgers are laboratory metadata/indexing layers, not alternate cognition stores.
