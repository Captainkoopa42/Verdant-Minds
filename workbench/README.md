# Verdant Workbench

Workbench is V5's local-first laboratory and control plane. It creates and operates engine runs, preserves laboratory history, exposes evidence-backed views, and packages reproducible experiments without becoming a second cognitive substrate.

## Directory map

| Path | Role |
| --- | --- |
| `backend/verdant_workbench/` | FastAPI control plane, durable service, isolated worker, repository, artifacts, curricula, explorers, experiments, providers, and plugins |
| `backend/tests/` | 67 Workbench integration/contract tests |
| `frontend/dist/` | Checked-in dependency-free browser runtime |
| `frontend/src/` | React/TypeScript development source |
| `schemas/` | JSON contracts for curricula, teaching bundles, events, experiments, plugins, and provider captures |
| `plugins/example_metric/` | Bundled capability-limited metric plugin example |
| `artifacts/` | Historical Workbench proof fixtures and packages |

## Run

From the repository root:

```bash
PYTHONPATH=.:workbench/backend python run_verdant_workbench.py --check
PYTHONPATH=.:workbench/backend python run_verdant_workbench.py --open-browser
```

See [../INSTALL.md](../INSTALL.md) and [../docs/workbench/WORKBENCH_1_0_OPERATIONS.md](../docs/workbench/WORKBENCH_1_0_OPERATIONS.md).

## State ownership

- `.vdk` checkpoint state is canonical cognition.
- SQLite records projects, organisms, runs, checkpoints, curricula, experiments, queues, and artifact indexes.
- append-only event ledgers record Workbench-observed activity;
- content-addressed blobs preserve checkpoints and laboratory artifacts;
- UI frames/timelines are projections of recorded state/events.

If Workbench crashes, stale run metadata is closed and the user reopens from the last verified checkpoint. Unsaved in-memory development is not invented.

## Current branch boundary

The historical Workbench 1.0.1 release layer contains 61 tests. The continuing V5 branch adds six more for WB-11 curriculum packs and worker timeout policy, for 67 current Workbench tests. The root `verify_release.py` does not list those two newer files; use [../TESTING.md](../TESTING.md) for complete verification.

## Security

Keep Workbench on loopback. It has no production multi-user authentication. Provider secret values should remain in environment variables and are referenced by name. Plugins execute out of process with declared capabilities, but this is not an OS sandbox; do not run untrusted plugin code.
