# Verdant Workbench 1.0.1 / V5 Operations

## Install and launch

From the repository root:

```bash
python -m pip install -r requirements-lock.txt
PYTHONPATH=.:workbench/backend python run_verdant_workbench.py --open-browser
```

Optional:

```bash
python run_verdant_workbench.py --home ./my-lab --port 8765 --open-browser
python run_verdant_workbench.py --home ./my-lab --check
```

The default bind is loopback only. Workbench is a local laboratory and does not provide production multi-user authentication. Do not expose it directly to a network.

## Release verification

```bash
python verify_release.py
```

For the final provider/plugin machine proofs as well:

```bash
python verify_release.py --with-proofs
```

The hosted validation environment can slow down across long chains of numerical pytest processes; if that occurs, run the partitions printed by `verify_release.py` in fresh terminals/processes. This is an operational environment issue, not a changed test criterion.

## Crash recovery

Canonical cognition is recoverable only from verified checkpoints. At startup, stale database rows left `active` by a crashed previous Workbench process are marked closed. Reopen explicitly from the last verified checkpoint. Unsaved in-memory development is intentionally not fabricated or silently reconstructed.

## Integrity and build identity

Engineering -> Integrity checks indexed checkpoints, curricula, experiments, and provider captures against content-addressed SHA-256 artifacts. Engineering diagnostics also report the exact V5 release ID, engine source SHA-256, Workbench source SHA-256, and dependency-lock SHA-256.

New `.vexp` experiments freeze those build identities. A build-locked experiment is rejected if the current source/dependency identity differs from the one under which it was frozen.

## External expansion

Outside researchers can add teaching providers by producing editable teaching records and can add metric plugins through the documented JSON/subprocess plugin contract without changing Verdant cognitive-engine source. Subprocess plugins are not an OS sandbox and should not be treated as safe for untrusted code.
