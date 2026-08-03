# Verdant Workbench — WB-00 / WB-01 Implementation Report

**Baseline engine:** Verdant Minds Milestone 19  
**Workbench spec:** Verdant Workbench Engineering Design v0.1  
**Build:** `0.1.0-wb01`

## Scope completed

This build begins the Workbench implementation without changing Verdant's cognitive ontology.

### WB-00 — architecture scaffold

- Added `workbench/backend` and `workbench/frontend` beside the existing engine packages.
- Copied the approved engineering specification into `docs/workbench/`.
- Recorded ADR-001 through ADR-010.
- Added versioned command, event and snapshot schema constants.
- Added a JSON Schema for Workbench event envelopes.
- Added a React/TypeScript/Vite application shell matching the agreed laboratory navigation.

### WB-01 — stable engine facade

Added `VerdantEngineAdapter` as the single Workbench-facing facade over the M19 engine.

The adapter currently supports:

- create/load organism;
- deterministic primitive teaching -> native `ExperienceCommand`;
- compilation probe;
- P promotion;
- P ablation/restoration;
- P-to-P interaction;
- hierarchy observation/promotion;
- structural challenge/refolding;
- scoped snapshots;
- metrics;
- deterministic checkpoint save.

The adapter does not reimplement the cognitive pipelines. It delegates to the existing audited engine packages.

## Command integrity

Mutating Workbench commands carry:

- `command_id`;
- `run_id`;
- `organism_id`;
- `command_type`;
- optional `expected_state_revision`;
- actor and timestamp.

`KernelState.event_sequence` is used as the initial Workbench state revision. A stale expected revision is rejected before mutation.

## Event integrity

Committed engine activity is projected into versioned `verdant.workbench.event.v1` envelopes. Each event records:

- run and organism identity;
- engine cycle and state revision;
- event type;
- source command ID;
- native event payload;
- SHA-256 of the canonicalized payload.

This event ledger is observational only and does not replace canonical engine state.

## Isolated worker

Added a supervised multiprocessing worker. One worker owns one authoritative organism. The API/control process communicates using typed serializable requests/responses and never holds the worker's mutable kernel instance.

The initial worker supports:

- descriptor;
- metrics;
- scoped snapshot;
- teach;
- probe;
- save;
- clean shutdown.

## Minimal API

A FastAPI control plane now exposes the first integration slice:

```text
GET  /health
POST /api/v1/runs
GET  /api/v1/runs/{run_id}/status
POST /api/v1/runs/{run_id}/teach
POST /api/v1/runs/{run_id}/probe
GET  /api/v1/runs/{run_id}/snapshot
POST /api/v1/runs/{run_id}/checkpoints
```

Run locally from the repository root:

```bash
PYTHONPATH=.:workbench/backend python run_verdant_workbench.py
```

## Deliberate STEP decision

The existing Verdant engine is event-driven; the hand cultivation runner has no audited no-input cognitive tick. The Workbench therefore does **not** fabricate one merely to satisfy a UI button.

Until the engine defines an explicit idle-cycle primitive, WB-03 `STEP` will mean **execute one queued curriculum/command item**. This preserves the rule that the UI cannot invent cognitive behavior.

## First engineering proof — PASSED

A direct engine run and a Workbench-adapter run were created with the same:

- seed (`1901`);
- state dimension (`16`);
- run label;
- ordered primitive teaching commands;
- event keys;
- feature vectors and evidence metadata.

Result:

```text
canonical fingerprints equal       PASS
checkpoint archives byte-identical PASS
engine metrics equal               PASS
```

Reference checkpoint SHA-256:

```text
f1cb1b95407bdafa9b5d79ed8052faef990020b547ef212758e05ab3e5111d4a
```

Machine-readable proof: `workbench/artifacts/wb01_equivalence_proof.json`.

Because the deterministic `.vdk` archives are byte-identical, the complete canonical cognitive records embedded in those checkpoints are also identical for this proof sequence.

## Test state

New Workbench integration tests:

```text
5 passed
```

They cover:

1. direct-engine vs adapter checkpoint equivalence;
2. event payload hash/source-command traceability;
3. stale revision rejection before mutation;
4. isolated worker create/teach/snapshot/save;
5. minimal FastAPI lifecycle.

Engine regression verification was repeated without modifying engine packages:

```text
124 passed — kernel/language/claims/ECWF/governance/shards/objects/sensory/perception/media/workspace/chunk
 32 passed — M12-M15 development/plasticity/structures/compilation
 16 passed — M16-M17 interaction/hierarchy
  9 passed — M18 refolding
  8 passed — M19 benchmark (5 + 3 fresh partitions)
---
189 passed — engine baseline
```

Combined verified test count in this build: **194 passing tests**.

## Current boundary

This is not yet the polished Workbench. No Curriculum Studio, SQLite project model, durable event index, branching service, WebSocket stream or Living Explorer has been added yet.

That is intentional. The first interface contract now exists and the first equivalence gate has passed before visualization development begins.

## Next engineering target

**WB-02 — Project / Run / Checkpoint Service**

Next work should add:

- SQLite Workbench metadata;
- content-addressed filesystem artifact storage;
- Project / Organism / Run / Checkpoint records;
- append-only event persistence and indexes;
- checkpoint integrity verification on reopen;
- branch ancestry;
- create -> run -> save -> close -> reopen -> branch equivalence test.

Once WB-02 passes, WB-03 can turn this foundation into the first actual live graphical Cultivation Console.
