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

## Experimental thermodynamic observability (homeostasis fork)

In `test/thermodynamic-homeostasis-v1`, the V5-X Workbench adapter records
`THERMODYNAMIC_OBSERVED` events for committed developmental cycles. A separate
`THERMODYNAMIC_CONTROL_APPLIED` event carries previous-cycle Tg, raw phase,
hysteretic control phase, policy revision and temporary effective config only
if an experimental governor is explicitly enabled. Replays emit neither.

On `test/obligation-substrate-v0`, the adapter additionally records
`ACCESS_PRESSURE_OBSERVED` as a separate pre-admission stream. Its payload
contains the inspected pre-cycle fingerprint and an explicit
`complete`/`incomplete` status. It is not folded into Tg, and it carries no
control or semantic-truth authority. Replays do not emit it.

The frontend **Thermodynamics** page displays these durable observations and
control decisions. This page is **read-only**. Workbench teaching, curriculum,
checkpoint saving, and reopening remain observer-only by default; there is no
governor-on toggle, no plasticity authority, and no mutation from simply
viewing telemetry. These changes are provisional on the thermodynamic fork
until the Workbench regression suite and frontend build pass.

Importantly, the current experimental controller's previous Tg / hysteretic
state is held in a live pipeline object, not embedded in a VDK. Control must
not be exposed in Workbench save/reopen until that state is durably restored
with provenance; observer-only reopening is safe. Existing VDKs do not
retroactively acquire thermodynamic events: create a new developmental cycle
to see telemetry.
