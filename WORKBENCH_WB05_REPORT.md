# Verdant Workbench WB-05
## Structures + Forensic Explorer

**Status:** Complete and verified  
**Baseline:** WB-04.1 Editable Teaching Records / Milestone 19 Verdant engine  
**Purpose:** Make earned P/Q organization inspectable, replayable, and causally testable without allowing the presentation layer to invent cognition.

## Exit criterion

WB-05 was designed around one laboratory requirement:

> A researcher must be able to select a real P/Q object, trace it back to the exact records that produced it, inspect its frozen structure and lineage, and reproduce a causal intervention from the Workbench.

The implementation now satisfies that requirement for the current P/Q mechanisms.

## 1. New forensic service

WB-05 adds `verdant_workbench.forensics`, a read-only projection layer over canonical Verdant records.

For a promoted P structure the inspector exposes:

```text
structure record
candidate record
complete candidate observation history
promotion event
Council decision
member concepts
frozen internal edge snapshots
exact evidence records
compilation/use events
verified structure interactions
availability changes
structural challenges
refolding events
parent/root/revision lineage
```

For a promoted Q structure it exposes:

```text
layered structure record
hierarchy candidate
hierarchy observation history
promotion event
Council decision
member P structures
source evidence
availability/use history
```

Workbench does not manufacture missing facts if a field or historical record does not exist.

## 2. Replay Formation is inspection, not simulation

`Replay Formation` reads the canonical observation/promotion history that already exists in the organism and converts it into ordered forensic frames.

It does **not**:

- advance the developmental heartbeat;
- submit new evidence;
- strengthen or decay associations;
- promote anything;
- change structure availability;
- rerun Council;
- modify the checkpoint.

The machine proof fingerprints the organism immediately before and after P replay and Q replay. Both remain identical.

Controlled P proof:

```text
candidate observation frames   6
promotion frame                 1
replay frames total             7
canonical state mutated         false
```

The selected Q replay contains four real hierarchy-history frames and is likewise non-mutating.

ADR-012 records this boundary permanently: forensic views are read-only projections of canonical records.

## 3. Record-backed topology

WB-05 adds the first actual Explorer topology view, but deliberately stops short of WB-06 living animation.

For P:

```text
node = recorded member concept
edge = frozen internal edge snapshot
edge measurement = recorded frozen association strength
```

For Q:

```text
center node = promoted Q
member node = recorded constituent P
edge = recorded Q membership
```

The layout coordinates are only presentation geometry. They are **not** claimed to be Verdant's cognitive geometry.

In the controlled proof the selected P has:

```text
3 member nodes
3 frozen internal edges
```

and the selected Q has:

```text
1 Q node + 3 member-P nodes = 4 nodes
3 recorded membership edges
```

No topology displayed by the graph is invented by the frontend.

## 4. Exact evidence and governance trace

The controlled P formed from seven source teaching events involving the opaque labels `kren`, `tar`, and `vel` across repeated contexts.

The forensic inspector traverses the promoted object back through:

```text
P
 -> promotion event
 -> candidate
 -> six candidate observations
 -> frozen topology
 -> exact EvidenceRecord objects
 -> source event keys
 -> Council authorization
```

The proof resolved 21 evidence records associated with the candidate/structure history and recovered the source event keys `wb05-proof-0` through `wb05-proof-6` from those canonical records.

This means the UI can answer the laboratory question:

> Where did this object come from?

without relying on a human-authored explanation of the run.

## 5. Causal ablation laboratory

The Workbench can now run an audited P causal comparison from the selected structure.

The operation performs:

```text
probe WITH P
 -> ablate exact P
 -> repeat same probe
 -> restore exact P
 -> repeat same probe
```

The lower substrate is left intact; only the promoted structure's availability is changed through the existing Verdant compilation mechanism.

Controlled result:

```text
WITH P       low-level work = 1
ABLATE P     low-level work = 6
RESTORE P    low-level work = 1
```

All three probes reconstructed the same concept set.

Therefore the measured advantage follows the exact selected P in this controlled assay, while the answer remains reconstructable from the underlying learned substrate.

The Workbench restores the object in a `finally` path so a failed comparison does not intentionally leave the selected P ablated.

## 6. Structure interventions exposed through the control plane

WB-05 adds Workbench routes for existing engine operations rather than reimplementing them in the UI:

```text
promote P candidate
ablate P
restore P
interact P
observe hierarchy
promote Q candidate
challenge P
refold P
causal compare P
```

Challenge/refold remains a typed laboratory intervention. Workbench does **not** decide from arbitrary prose which internal dependency is contradicted; it only routes the explicit challenge to the already-existing Verdant refolding machinery.

## 7. API surface

New principal endpoints include:

```text
GET  /api/v1/runs/{run_id}/structures
GET  /api/v1/runs/{run_id}/structures/{structure_id}
GET  /api/v1/runs/{run_id}/structures/{structure_id}/replay
GET  /api/v1/runs/{run_id}/structures/{structure_id}/graph

POST /api/v1/runs/{run_id}/structure-candidates/{candidate_id}/promote
POST /api/v1/runs/{run_id}/structures/{structure_id}/ablate
POST /api/v1/runs/{run_id}/structures/{structure_id}/restore
POST /api/v1/runs/{run_id}/structures/{structure_id}/interact
POST /api/v1/runs/{run_id}/structures/{structure_id}/challenge
POST /api/v1/runs/{run_id}/structures/{structure_id}/refold
POST /api/v1/runs/{run_id}/structures/{structure_id}/causal-compare

POST /api/v1/runs/{run_id}/hierarchy/observe
POST /api/v1/runs/{run_id}/hierarchy-candidates/{candidate_id}/promote
```

Mutating operations still pass through the existing command envelope, worker, revision checks, and canonical engine pipelines.

## 8. User interface

Two Workbench areas are now genuinely operational.

### Structures / Forensic Inspector

A researcher can:

- list promoted P and Q structures;
- inspect pending candidates and promote eligible candidates;
- select a structure;
- inspect quality, formation, governance and lineage;
- inspect constituent concepts/structures and frozen topology;
- inspect exact evidence records;
- replay formation;
- ablate/restore/interact;
- run the controlled P causal comparison;
- submit explicit structural challenges and refold;
- inspect raw forensic JSON.

### Explorer / Forensic Topology

The Explorer now provides a first record-backed topology view for the selected P/Q structure plus forensic overlay and replay controls.

It intentionally does **not** animate waves, activation, folds moving through space, or inferred cognitive motion yet. That is WB-06 work and will be required to consume recorded events/state rather than visual imagination.

The verified runtime UI remains the dependency-free browser client served by FastAPI. React/TypeScript source is retained and updated, but this build environment still does not provide the React/Vite packages required for a truthful production rebuild of that source.

## 9. Machine proof

Artifact:

`workbench/artifacts/wb05_forensic_explorer_proof.json`

All gates pass:

```text
graph_is_record_backed                 PASS
p_ablation_removes_advantage           PASS
p_reconstruction_unchanged             PASS
p_restoration_restores_advantage       PASS
p_traces_to_candidate_history          PASS
p_traces_to_exact_evidence             PASS
p_traces_to_governance                 PASS
q_inspector_reads_real_hierarchy       PASS
q_replay_is_non_mutating               PASS
replay_is_non_mutating                 PASS
```

Key proof objects:

```text
P structure     structure_3e12fa013bb245e3e0827451
P candidate     structure_candidate_95326e72af2ac41b42add2c9
Q structure     layered_structure_6fff321a318a9ffefae1e723
```

## 10. Verification

### Workbench

The Workbench suite now contains:

```text
29 passing tests
```

Six WB-05-specific tests cover:

1. P inspector candidate/evidence/governance/frozen-topology trace;
2. non-mutating Replay Formation;
3. P with/ablate/restore causal work comparison;
4. real M17 Q hierarchy inspection/replay;
5. structure/detail/replay/graph/causal API routes;
6. served Structures/Explorer UI surfaces.

### Engine regression

All existing Milestone 19 engine tests were reverified in fresh partitions/processes:

```text
124 passed  core/kernel/media/language/etc.
32 passed   M12-M15
16 passed   M16-M17
9 passed    M18
8 passed    M19 benchmark
--------------------------------
189 passed
```

As in previous milestones, long grouped pytest invocations can become abnormally slow in this container, so the verified total is based on clean test partitions/individual M19 processes rather than treating a process timeout as a cognitive test failure.

### Combined verified state

```text
189 engine + 29 Workbench = 218 verified passing tests
```

No Verdant cognitive subsystem was replaced by frontend logic to obtain WB-05 functionality.

## 11. Boundaries and unfinished work

WB-05 does **not** yet provide:

- continuously animated cognitive activity;
- a learned 2D/3D cognitive geometry;
- an inference that visual proximity means semantic proximity;
- arbitrary natural-language contradiction targeting;
- generalized Q ablation comparison UI equivalent to the P causal comparison;
- large-graph level-of-detail rendering;
- publication-grade timeline synchronization across all telemetry channels.

Those boundaries are intentional rather than hidden.

## 12. Next — WB-06 Living Explorer

WB-06 can now build scenery on top of a forensic substrate we trust.

The target is:

```text
recorded engine events/state
        -> time-indexed Explorer model
        -> workspace / association / P / Q / contradiction / refold layers
        -> live + replay renderer
        -> forensic overlay
```

The acceptance rule remains strict:

> No cognitive animation exists without backing recorded state/event evidence, and live/replay views must agree at recorded checkpoints.

WB-05 opens the engine-room window. WB-06 makes the real developmental history move behind the glass.
