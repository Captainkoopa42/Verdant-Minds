# Verdant Workbench — WB-02 Implementation Report

**Baseline engine:** Verdant Minds Milestone 19  
**Prior Workbench:** WB-00 / WB-01 `0.1.0-wb01`  
**Workbench spec:** Verdant Workbench Engineering Design v0.1  
**Build:** `0.2.0-wb02`

## Target

WB-02 implements the first durable laboratory history layer around the already-isolated Verdant worker:

```text
Project
  -> Organism
      -> Run
          -> immutable Checkpoint
          -> append-only Events
          -> Branches
```

The exit criterion from the engineering specification was:

> create -> run -> save -> close -> reopen -> branch yields correct canonical hashes and ancestry.

That criterion now passes.

## What was added

### SQLite Workbench repository

Added `workbench/backend/verdant_workbench/repository.py` with persistent records for:

- `ProjectRecord`;
- `OrganismRecord`;
- `RunRecord`;
- `CheckpointRecord`;
- event indexes.

SQLite is **not** a cognitive truth store. It contains laboratory metadata, ancestry, checkpoint references, and event indexes. Canonical cognition remains in Verdant `.vdk` artifacts.

### Content-addressed artifact store

Added `artifact_store.py`.

Checkpoint artifacts are ingested by SHA-256 and stored immutably under:

```text
artifacts/blobs/<sha-prefix>/<sha256>
```

The store:

- deduplicates identical bytes;
- verifies the expected SHA-256 during ingest;
- verifies stored bytes before reopening or branching;
- refuses corrupted/tampered artifacts.

### Durable run service

Added `run_service.py` as the laboratory-level facade around workers, metadata, events and artifacts.

It supports:

- create project;
- create organism/run;
- teach/probe through an isolated worker;
- save content-addressed checkpoints;
- close a worker while retaining laboratory history;
- reopen a run from its verified head checkpoint;
- branch a new run from any verified checkpoint;
- inspect run ancestry;
- recover event history after process/application restart.

A branch uses the same conceptual organism lineage but receives a new `run_id`. Its `parent_run_id` and `parent_checkpoint_id` are explicit.

### Append-only event persistence

Committed Workbench event envelopes are now appended to:

```text
runs/<run-id>/events.jsonl
```

SQLite stores byte offsets and searchable event metadata. The JSONL ledger remains the durable observational record.

This preserves the architecture rule:

```text
canonical engine state != Workbench event/index state
```

### API expansion

The FastAPI layer now exposes persistent laboratory operations including:

```text
GET  /api/v1/projects
POST /api/v1/projects
POST /api/v1/projects/{project_id}/runs

POST /api/v1/runs/{run_id}/checkpoints
GET  /api/v1/runs/{run_id}/checkpoints
POST /api/v1/runs/{run_id}/close
POST /api/v1/runs/{run_id}/reopen
GET  /api/v1/runs/{run_id}/events
GET  /api/v1/runs/{run_id}/ancestry

POST /api/v1/checkpoints/{checkpoint_id}/branch
```

The previous create/teach/probe/status/snapshot routes remain available.

## WB-02 persistence / branch proof

A machine-readable proof was generated at:

```text
workbench/artifacts/wb02_persistence_branch_proof.json
```

Protocol:

1. create a project and root organism/run;
2. submit four deterministic teaching events;
3. save a checkpoint;
4. record checkpoint bytes and event IDs;
5. close the worker and the complete Workbench service;
6. instantiate a fresh service against the same laboratory directory;
7. verify and reopen the root run;
8. branch a child run from the saved checkpoint;
9. give only the child a new experience;
10. save the child;
11. verify the parent checkpoint remained byte-identical and ancestry remained correct.

Reference result:

```text
root checkpoint SHA-256
3713d9ebc242bab0fde158986684f6db30a6fffaf42a1d710c1fcd802f360f1f

root canonical fingerprint
96c956ed045fb0abedfe15a6f7a89d732b653f8432fc56dae3438ad9e9e518aa

reopen fingerprint matches              PASS
checkpoint bytes preserved              PASS
event ledger preserved                  PASS
child starts from exact parent state    PASS
child diverges after new experience     PASS
parent checkpoint immutable             PASS
ancestry root -> child                   PASS
SQLite event index == ledger events     PASS
```

The root run produced 17 persisted Workbench events, and all 17 were recovered/indexed after reopening the laboratory.

## Integrity behavior

WB-02 checks artifact SHA-256 before loading a checkpoint. After load, it also checks the loaded Verdant canonical fingerprint against checkpoint metadata.

A dedicated test deliberately modifies stored checkpoint bytes. Reopen is refused with `ArtifactIntegrityError`.

This gives two separate checks:

```text
artifact bytes -> SHA-256 integrity
loaded Verdant state -> canonical fingerprint integrity
```

## Branch semantics

WB-02 never rewrites the parent checkpoint.

```text
root run
   |
   +-- ckpt_root  (immutable)
          |
          +-- child run
                 |
                 +-- new experience
                 +-- ckpt_child
```

The child initially has the exact parent canonical fingerprint. New child experience changes only the child run. The parent checkpoint bytes remain unchanged.

## Test state

New/updated Workbench integration suite:

```text
10 passed
```

The WB-02 tests cover:

1. content-addressed deduplication and tamper detection;
2. create/save/close/full-service-reopen with exact checkpoint and event recovery;
3. branch ancestry and parent immutability;
4. corrupted checkpoint rejection;
5. API project/checkpoint/reopen/branch/event lifecycle;
6. all WB-01 adapter/worker/API equivalence and stale-command protections.

Engine regression tests were again verified in fresh partitions without changing cognitive engine packages:

```text
124 passed — kernel/language/claims/ECWF/governance/shards/objects/sensory/perception/media/workspace/chunk
 32 passed — M12-M15 development/plasticity/structures/compilation
 16 passed — M16-M17 interaction/hierarchy
  9 passed — M18 refolding
  5 passed — first M19 benchmark partition
  3 passed — remaining M19 benchmark partition
---
189 passed — engine baseline
```

Combined verified count for this build:

```text
189 engine + 10 Workbench = 199 passing tests
```

As in the previous builds, a single monolithic engine pytest process becomes abnormally slow in this environment, so engine regression is reported from clean fresh partitions rather than treating that environmental timeout as a test failure.

## Current boundary

WB-02 is persistence infrastructure, not the live laboratory UI yet.

Not yet implemented:

- command/curriculum queue;
- WebSocket event streaming;
- graphical run/pause/step controls;
- Curriculum Studio;
- Grammar Lab;
- Structures/Forensic Explorer;
- Living Explorer;
- experiment manager;
- external provider connections.

One operational point should remain explicit: an active run can advance beyond its latest saved checkpoint. Reopening an inactive run resumes from the selected/head **saved checkpoint**, not from unsaved RAM state. WB-03 should surface that condition as a clear "unsaved/dirty run" indicator rather than hiding it.

## WB-02 exit criterion

```text
create
 -> run
 -> save
 -> close
 -> reopen from verified immutable artifact
 -> branch from exact checkpoint
 -> child diverges independently
 -> parent history unchanged
```

**PASSED.**

## Next target

**WB-03 — Live API + Cultivation Console**

The next build should turn this durable foundation into the first real Workbench operating surface:

- persistent run queue;
- RUN / PAUSE / STEP-one-item / STOP;
- live WebSocket event stream;
- teaching and probe console;
- status / dirty-state / checkpoint controls;
- save / reopen / fork UI;
- provenance-separated event log;
- first React Home + Cultivate pages connected to the real API.

At WB-03 exit, the hand-built cultivation runner's core operations should be usable without a terminal while still driving the same engine worker and durable WB-02 history layer.
