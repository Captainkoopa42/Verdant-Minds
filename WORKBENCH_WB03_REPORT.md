# Verdant Workbench — WB-03 Engineering Report

## Live API + Cultivation Console

WB-03 is the first Workbench milestone that turns the M19 engine and WB-01/WB-02 laboratory infrastructure into an operable application surface.

The cognitive architecture is unchanged. The Workbench continues to obey two boundaries:

1. the UI/control plane commands Verdant but does not contain cognitive semantics;
2. displayed cognitive activity must be traceable to committed engine artifacts/events.

## Runtime path

```text
Home / Cultivate UI
        |
        | REST + WebSocket
        v
FastAPI Workbench control plane
        |
        | persistent queue / typed command
        v
DurableRunService
        |
        | isolated IPC
        v
VerdantEngineAdapter worker
        |
        v
Milestone 19 Verdant engine
```

Canonical cognition remains in the engine worker and `.vdk` checkpoints. The new queue, UI state and execution-control records are Workbench laboratory metadata.

## Persistent command queue

WB-03 adds a SQLite-backed `run_queue` table. Each queue item records:

```text
queue_item_id
run_id
sequence_no
command_type
payload
status
created / started / completed times
result
error
```

Current queued command types are:

- `TEACH`
- `PROBE`

Queue records survive Workbench restart. A command interrupted while marked `running` is safely returned to `queued` when the run is reopened from its verified checkpoint.

## Run-control semantics

### RUN

Processes queued commands in deterministic sequence order until:

- the queue drains;
- PAUSE is requested;
- STOP is requested; or
- a queued command fails.

### PAUSE

Stops automatic queue consumption after the currently executing item. Remaining items stay queued.

### STEP ITEM

Executes exactly one queued item.

This milestone deliberately does **not** define STEP as a no-input cognitive cycle. The current Verdant engine is event-driven; inventing an idle tick in the UI would violate the engine/control-plane boundary.

### STOP

Stops queue execution while preserving unexecuted queue items and the loaded organism.

## Dirty-state contract

The Workbench compares the active run's canonical fingerprint with its head checkpoint.

```text
live fingerprint != head checkpoint fingerprint
    -> UNSAVED DEVELOPMENT
```

A newly created organism without a checkpoint is also dirty. Saving a checkpoint clears the dirty indicator only when the saved canonical fingerprint matches the live organism.

## Live event stream

WB-03 adds cursor-based event consumption from the append-only JSONL ledger and its SQLite byte-offset index.

REST:

```text
GET /api/v1/runs/{run_id}/events?cursor=<rowid>&limit=<n>
```

WebSocket:

```text
WS /api/v1/runs/{run_id}/events?cursor=<rowid>
```

The WebSocket emits:

- persisted event batches;
- current run/worker/execution status.

Reconnect starts from a durable cursor rather than relying on transient in-memory frontend state.

## Control-plane events

The event ledger can now also contain observational Workbench control events:

```text
RUN_STARTED
RUN_PAUSED
RUN_STOPPED
RUN_QUEUE_CHANGED
CHECKPOINT_SAVED
```

They are explicitly not canonical cognitive state. They document laboratory/operator actions around the engine. Native cognitive events remain distinct, including `EVIDENCE_ACCEPTED`, `WORKSPACE_CYCLE`, `PLASTICITY_CHANGED`, structure events, and others.

## First real UI

WB-03 provides two active application surfaces.

### Organism / Lab Home

- project creation/selection;
- run listing/selection;
- explicit seed, field dimension and run label;
- organism creation;
- worker online/offline state;
- canonical fingerprint/cycle/revision metrics;
- reopen from head checkpoint.

### Cultivate

- RUN / PAUSE / STEP ITEM / STOP;
- persistent command queue;
- human-authored primitive teaching;
- manual or queued probes;
- live engine metrics;
- provenance-classified event stream;
- checkpoint save;
- fork from head checkpoint;
- explicit unsaved-development warning.

Unimplemented Workbench areas remain visible but disabled rather than being populated with fake screens.

## Frontend build constraint

The engineering target remains React + TypeScript + Vite and the React/TypeScript source is present.

The milestone execution environment's npm registry returned HTTP 404 for React, Vite, TypeScript and `@vitejs/plugin-react`, so an npm build could not be validated. WB-03 therefore also ships a dependency-free browser reference build under:

```text
workbench/frontend/dist/
```

FastAPI serves that build directly. It exercises the same API/WebSocket contracts and keeps the Workbench operable without a package install. `node --check` validates its JavaScript syntax and integration tests validate static delivery.

This is recorded as an environment/package-registry limitation, not presented as a successful React build.

## API additions

WB-03 adds or expands:

```text
GET  /api/v1/runs
GET  /api/v1/projects/{project_id}

GET  /api/v1/runs/{run_id}/queue
POST /api/v1/runs/{run_id}/queue/teach
POST /api/v1/runs/{run_id}/queue/probe

POST /api/v1/runs/{run_id}/start
POST /api/v1/runs/{run_id}/pause
POST /api/v1/runs/{run_id}/step
POST /api/v1/runs/{run_id}/stop

GET  /api/v1/runs/{run_id}/events?cursor=...
WS   /api/v1/runs/{run_id}/events?cursor=...
```

The direct teach/probe, checkpoint, reopen, close, branch, ancestry and snapshot endpoints from earlier milestones remain available.

## Machine proof

`workbench/artifacts/wb03_live_console_proof.json` performs this sequence:

```text
create organism
-> save initial checkpoint
-> enqueue three teaching items
-> close complete Workbench service
-> reopen service + organism
-> verify queue survived
-> STEP ITEM once
-> RUN remaining queue
-> verify all items completed
-> verify cognitive state changed
-> verify dirty state
-> save final checkpoint
-> branch from final checkpoint
-> verify exact branch fingerprint
-> verify cognitive + control events from durable cursor
```

All proof checks pass.

Reference proof results:

- queue survives Workbench restart: PASS
- single step executes exactly one item: PASS
- RUN drains remaining queue: PASS
- 3 teaching items produce 5 expected primitive concepts: PASS
- dirty state before final save: PASS
- final checkpoint equals live canonical fingerprint: PASS
- child branch begins at exact final parent state: PASS
- control events durable: PASS
- cognitive events durable: PASS
- event cursor durable/nonzero: PASS

## Test state

Engine regression verification remains:

```text
124 passed  core/kernel/media/workspace/etc.
 32 passed  M12-M15
 16 passed  M16-M17
  9 passed  M18
  5 passed  M19 partition A
  3 passed  M19 partition B
--------------------------------
189 engine tests
```

WB-03 Workbench suite:

```text
13 passed
```

Combined verified total:

```text
202 passing tests
```

## Exit criterion assessment

The WB-03 roadmap exit criterion was:

> all core cultivation-runner operations can be performed without a terminal.

For the cultivation-control scope assigned to WB-03, this is satisfied: an operator can create/select a run, supply and queue primitive teaching/probe items, run/pause/step/stop queue execution, view live metrics/events, save a checkpoint and fork the lineage through the browser console.

P/Q forensic intervention screens remain intentionally deferred to WB-05; curriculum compilation/grammar authoring remains WB-04.

## Next target — WB-04

**Curriculum Studio + Grammar Lab**

The next build should turn teaching itself into an inspectable engineering/compiler workflow:

```text
SOURCE
  -> PARSED
  -> CURRICULUM AST / IR
  -> COMPILED ExperienceCommand sequence
  -> REVIEW
  -> FREEZE immutable .vcurr
  -> TEACH / QUEUE
```

The decisive WB-04 proof should be that the current M19 alien-world curriculum can be authored or imported, previewed, frozen, content-hashed and run from Workbench without writing Python, while the frozen compiled command sequence remains identical on replay.
