# Verdant Workbench 1.0
## Engineering Architecture & Implementation Specification

**Status:** Draft v0.1 — Architecture Baseline / Pre-Implementation  
**Date:** 2026-08-02  
**Project:** Verdant Minds  
**Baseline:** Independent Rebuild through Milestone 19  

---

## 0. Document Purpose

This document converts the Verdant Workbench discussion into an implementable engineering specification. The Workbench is not a visualization wrapper and it is not a replacement for the Verdant engine. It is the laboratory and engineering environment around the engine: the place where a user can create or load an organism, teach it, compile curricula, run or pause development, inspect live cognition, reproduce experiments, branch checkpoints, ablate mechanisms, connect optional external curriculum assistants, and verify every displayed claim against engine records.

The central architectural rule is:

> **Anything the UI claims must be traceable to something the engine actually did.**

A second rule is equally important:

> **The UI commands the engine; the UI does not contain cognition.**

The Workbench must therefore remain replaceable. A future robotics interface, remote laboratory client, or headless batch service should be able to use the same engine contracts without changing Verdant's cognitive implementation.

---

## 1. Executive Summary

Verdant Minds now has a local, deterministic experimental engine with canonical evidence, claims and contradiction, governance, shards, objecthood, bounded workspace, ECWF, plasticity, earned relational structures, cognitive compilation, cross-symbolic interaction, higher-order structures, lineage-preserving refolding, native media handling, and a four-arm Ethomorphism benchmark harness.

The next engineering phase is to build a **local-first scientific control plane** around that engine.

The recommended Workbench architecture is:

```text
Human / Researcher / Engineer
            |
            v
+-----------------------------+
|      Verdant Workbench UI   |
| React + TypeScript          |
| Studio / Explorer / Lab     |
+--------------+--------------+
               | REST + WebSocket
               v
+-----------------------------+
|   Workbench Control Plane   |
| FastAPI                     |
| projects / runs / compiler  |
| experiments / providers     |
| event indexing / exports    |
+--------------+--------------+
               | typed commands
               v
+-----------------------------+
|      Isolated Engine Worker |
| existing Verdant Python     |
| one authoritative organism  |
+--------------+--------------+
               | checkpoints + immutable events
               v
+-----------------------------+
|    Artifact / Run Storage   |
| .vdk / .vrun.zip / .vcurr  |
| .vexp / telemetry / hashes  |
+-----------------------------+
```

The first implementation objective is not a polished visualization. It is a stable **Engine Adapter + Run Service + Event Stream**. Every later feature depends on those contracts.

---

## 2. Current Engine Baseline

The Workbench is designed against the current Milestone 19 rebuild, not the retired V4 architecture.

### 2.1 Active engine subsystems

The current repository exposes these major packages:

- `verdant_kernel` — canonical state, evidence, concepts, relations, claims, policies, checkpoints, invariants.
- `verdant_language` — controlled grammar analysis and language-learning path.
- `verdant_claims` — claim, contradiction, revision pipeline.
- `verdant_ecwf` — persistent continuous possibility field and resonance.
- `verdant_governance` — Three Kings / Council inspection and authorization.
- `verdant_shards` — bounded shard formation and routing.
- `verdant_objects` — earned proto-object observation and promotion.
- `verdant_workspace` — bounded active workspace.
- `verdant_sensory`, `verdant_perception`, `verdant_media` — native media preservation, translation, perception, run packages.
- `verdant_development` — unified developmental heartbeat.
- `verdant_plasticity` — bounded competitive local associations.
- `verdant_structures` — nonsemantic `StructureCandidate` and promoted `P` structures.
- `verdant_compilation` — structure use, compilation probes, ablation/restoration.
- `verdant_interaction` — continuous structure retrieval followed by symbolic verification.
- `verdant_hierarchy` — higher-order `Q` candidate formation, promotion and use.
- `verdant_refolding` — structural challenge and lineage-preserving revise/split/unresolved behavior.
- `verdant_benchmarks` — current four-arm Ethomorphism benchmark harness.

### 2.2 Existing user surfaces

The repository already contains headless or CLI surfaces that the Workbench should wrap rather than duplicate semantically:

- `run_verdant_cultivation.py`
- `run_ethomorphism_benchmark.py`
- `run_verdant_media.py`
- existing `.vdk` checkpoints
- existing `.vrun.zip` portable run packages
- existing media/sensory archives

### 2.3 Baseline test condition

The Milestone 19 baseline reports **189 passing tests** when run in fresh pytest partitions. Workbench integration must not weaken those engine invariants. The Workbench adds integration and UI tests on top; it does not redefine engine correctness.

---

## 3. Product Definition

### 3.1 What Verdant Workbench is

Verdant Workbench is a local-first laboratory application for operating, observing, teaching, reproducing, extending and testing Verdant Minds.

It combines the functions of:

- an IDE for curricula and grammar;
- a laboratory control panel for developmental runs;
- an oscilloscope for live cognitive activity;
- a forensic inspector for evidence and provenance;
- an experiment manager for baselines, ablations and repeated runs;
- a timeline and branching system for developmental checkpoints;
- a provider host for optional external teaching assistants;
- an extension host for research adapters and metrics.

### 3.2 What it is not

The Workbench is not:

- a second cognitive system;
- a hidden semantic layer that repairs or interprets Verdant results;
- a direct graph editor in normal use;
- an LLM wrapper around Verdant;
- a visualization that invents activity not recorded by the engine;
- a replacement for canonical engine checkpoints or provenance.

---

## 4. Design Principles and Architecture Decisions

### ADR-001 — The Workbench is a control plane

All cognitive state and cognitive transitions remain in the engine. The UI and Workbench backend issue typed commands and consume typed results/events.

### ADR-002 — Local-first by default

The complete engine, checkpoint store and core Workbench must run without cloud services. External APIs are optional providers.

### ADR-003 — Engine process isolation

Run each active organism in a dedicated Python worker process supervised by the Workbench backend. This prevents long developmental cycles, crashes or experiments from freezing the UI/control server and creates a clean boundary for pause/terminate/restart.

### ADR-004 — Canonical state is not Workbench state

Workbench metadata (window layout, project notes, run index, graph camera position) must never be written into `KernelState`. Engine checkpoints remain cognitive artifacts; Workbench metadata lives separately.

### ADR-005 — Events are observational, not an alternate truth store

The Workbench event ledger is an immutable observational/indexing layer over committed engine activity. Canonical truth remains in the checkpointed engine state.

### ADR-006 — External LLMs are curriculum providers, not cognition

LLMs may propose curricula, parsing, lesson decomposition or explanatory text. Their output must be captured, reviewable, versioned and compiled before it enters Verdant. Provider output must never silently modify engine state.

### ADR-007 — Compiled curricula and experiments are immutable artifacts

Editing creates a new version/hash. A run always records the exact compiled curriculum and experiment manifest it consumed.

### ADR-008 — Plugins are capability-limited

Plugins implement declared interfaces such as `CurriculumProvider`, `SensorAdapter`, `MetricProvider` or `VisualizationLayer`. Unrestricted mutation of kernel internals is not part of the normal plugin contract.

### ADR-009 — Visualization must be evidence-driven

Every node appearance, activation pulse, fold formation, promotion, ablation, split, refold, dormancy or interaction shown as cognitive activity must map to a committed engine record or measured state transition.

### ADR-010 — Direct state mutation is developer-only

A debug-only state editor may exist later, but it must be visually separated and mark the run as provenance-compromised or externally mutated.

---

## 5. User Roles

### 5.1 Operator

Needs to create/load a Verdant, teach material, run/pause/step, inspect status, save checkpoints and view the Explorer without understanding internal Python APIs.

### 5.2 Researcher

Needs repeatable experiments, multiple arms, fixed seeds, curriculum versioning, ablation/restoration, branching, metrics, comparison views, replay and exportable evidence.

### 5.3 Engineer

Needs raw event records, state hashes, subsystem timing, memory usage, API traces, errors, plugin diagnostics, profiler integration, contract tests and explicit low-level hooks.

The UI may expose role-based modes, but the underlying data model should remain identical.

---

## 6. Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-001 | Create a new organism with explicit seed and policy configuration. | P0 |
| FR-002 | Load, verify and continue an existing `.vdk` / `.vrun.zip`. | P0 |
| FR-003 | Branch an existing run without rewriting parent history. | P0 |
| FR-004 | Run, pause, single-step and stop the engine worker. | P0 |
| FR-005 | Submit human-authored primitive teaching events. | P0 |
| FR-006 | Display committed engine activity through a live event stream. | P0 |
| FR-007 | Inspect evidence, concepts, relations, claims, contradictions, workspace, plasticity, P/Q structures and refolding lineage. | P0 |
| FR-008 | Save and restore checkpoints from the UI. | P0 |
| FR-009 | Provide a Curriculum Studio with source, parse, compiled IR and diff views. | P0 |
| FR-010 | Compile curriculum source into deterministic native engine commands. | P0 |
| FR-011 | Preview compilation before any teaching commit. | P0 |
| FR-012 | Run cultivation scripts/curricula without writing Python. | P0 |
| FR-013 | Provide Living Explorer and Forensic Overlay views driven by real events. | P1 |
| FR-014 | Inspect a structure's formation, promotion gates, evidence, uses and revision lineage. | P0 |
| FR-015 | Replay the event window that produced a structure or claimed result. | P1 |
| FR-016 | Run controlled ablation/restoration from the UI. | P0 |
| FR-017 | Create multi-arm experiments with common curricula, seeds and resource budgets. | P1 |
| FR-018 | Compare run metrics and export machine-readable results. | P1 |
| FR-019 | Support optional external curriculum assistants through provider adapters. | P1 |
| FR-020 | Capture provider request/response artifacts for deterministic replay. | P1 |
| FR-021 | Provide grammar/lexicon editing and parse-testing workflows. | P1 |
| FR-022 | Import media through existing Verdant media gateways. | P1 |
| FR-023 | Load plugins implementing approved Workbench extension contracts. | P2 |
| FR-024 | Export a self-contained experiment verification package. | P1 |
| FR-025 | Show a result claim with direct links to supporting run/event/checkpoint artifacts. | P1 |

---

## 7. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-001 | Identical deterministic experiment inputs must yield identical final engine hashes, subject to declared platform-independent numeric rules. |
| NFR-002 | The UI must remain responsive while an engine run is active. |
| NFR-003 | A worker crash must not corrupt the last committed checkpoint or Workbench project metadata. |
| NFR-004 | No API key or secret may enter kernel state, exported checkpoints, telemetry or experiment packages. |
| NFR-005 | Every command must have a command ID; every committed effect must be traceable to a command and engine event range. |
| NFR-006 | Run artifacts must be content-hashed and integrity-checkable. |
| NFR-007 | The Workbench must operate completely offline when no external provider is configured. |
| NFR-008 | External providers must be optional and replaceable without changing engine code. |
| NFR-009 | Visualization must degrade gracefully for large graphs using aggregation/level-of-detail rather than requiring all nodes in the DOM. |
| NFR-010 | Long experiments must be recoverable after UI restart by reconnecting to or reopening run metadata/checkpoints. |
| NFR-011 | Normal operation must never mutate engine state by directly editing Python objects from the UI layer. |
| NFR-012 | Workbench APIs and artifact schemas must be versioned. |

---

## 8. Recommended Technology Stack

### 8.1 Backend / control plane

**Python + FastAPI** is the recommended initial choice because the existing Verdant engine is Python/Pydantic and the Workbench needs typed local integration rather than a language bridge.

Recommended components:

- FastAPI — REST control surface and local server.
- Pydantic — API contracts; reuse or adapt engine models without exposing mutable internals directly.
- WebSocket — live event stream and run status.
- SQLite — Workbench project/index metadata only, never canonical Verdant cognition.
- `asyncio` + supervised subprocess/multiprocessing workers — run isolation.
- filesystem artifact store — checkpoints, run packages, curricula, experiments, telemetry and provider captures.

### 8.2 Frontend

Recommended initial stack:

- React + TypeScript + Vite.
- Monaco Editor for curriculum/grammar/manifest editing.
- TanStack Query for request state and caching.
- Zustand or equivalent small local store for UI-only state.
- WebSocket client for live event updates.
- Canvas/WebGL-based visualization layer for the Explorer; do not bind the design to SVG for large dynamic graphs.
- A conventional charting library for scientific plots; plots consume recorded metrics, not hidden frontend calculations.

### 8.3 Packaging

Phase 1 should be a **local web application** launched by a single command. This minimizes packaging complexity and remains cross-platform.

Desktop packaging can follow after the contracts stabilize. A Tauri or similar shell is acceptable later, but should wrap the same local API instead of creating a second application architecture.

---

## 9. Runtime Process Architecture

```text
+-------------------------+       +----------------------------+
| Browser / Desktop UI    |<----->| Workbench API Server       |
| React / TypeScript      | REST  | project/run control        |
|                         | WS    | compiler/provider host     |
+-------------------------+       +-------------+--------------+
                                                |
                                       typed IPC commands
                                                |
                              +-----------------+------------------+
                              |                                    |
                              v                                    v
                     +----------------+                    +----------------+
                     | Engine Worker A|                    | Engine Worker B|
                     | one organism   |                    | experiment arm |
                     +--------+-------+                    +--------+-------+
                              |                                     |
                              +-----------------+-------------------+
                                                |
                                                v
                                      +---------------------+
                                      | Artifact Store      |
                                      | checkpoints/events  |
                                      | curricula/results   |
                                      +---------------------+
```

A run service is responsible for worker lifecycle. The UI must never hold the authoritative engine instance.

---

## 10. Engine Adapter Contract

Create one Workbench-facing package that wraps all existing subsystem calls:

```text
verdant_workbench_engine/
    adapter.py
    commands.py
    events.py
    snapshots.py
    capabilities.py
```

The Workbench should not import every cognitive pipeline from route handlers. Instead, `VerdantEngineAdapter` becomes the stable facade.

### 10.1 Proposed command surface

```python
class VerdantEngineAdapter:
    create(config) -> OrganismDescriptor
    load(checkpoint_ref) -> OrganismDescriptor
    submit_experience(command) -> CommandReceipt
    step(cycles=1) -> RunReceipt
    probe(request) -> ProbeResult
    promote_structure(candidate_id) -> PromotionResult
    ablate_structure(structure_id) -> AvailabilityResult
    restore_structure(structure_id) -> AvailabilityResult
    interact(structure_id, request) -> InteractionResult
    promote_hierarchy(candidate_id) -> PromotionResult
    challenge(request) -> ChallengeResult
    refold(structure_id) -> RefoldResult
    snapshot(scope) -> Snapshot
    metrics() -> EngineMetrics
    save(path_or_store_ref) -> CheckpointDescriptor
```

This facade may internally call `VerdantDevelopmentPipeline`, `VerdantStructurePipeline`, `VerdantCompilationPipeline`, `VerdantStructureInteractionPipeline`, `VerdantHierarchyPipeline`, `VerdantRefoldingPipeline`, etc., but those details remain behind the adapter.

### 10.2 Command semantics

Every command must include:

```text
command_id
run_id
organism_id
expected_state_revision (where applicable)
issued_at
actor
payload
```

Mutating commands should use optimistic revision checks or the engine's existing stale-report protections to prevent race conditions between UI actions.

---

## 11. Event and Telemetry Contract

### 11.1 Event envelope

```json
{
  "schema": "verdant.workbench.event.v1",
  "event_id": "evt_...",
  "run_id": "run_...",
  "organism_id": "org_...",
  "engine_cycle": 18442,
  "state_revision": 55120,
  "event_type": "STRUCTURE_PROMOTED",
  "source_command_id": "cmd_...",
  "timestamp_utc": "...",
  "payload": {},
  "payload_sha256": "..."
}
```

### 11.2 Initial event taxonomy

The Workbench event mapper should normalize committed engine records into categories such as:

```text
RUN_STARTED
RUN_PAUSED
RUN_STOPPED
CHECKPOINT_SAVED
EVIDENCE_ACCEPTED
CONCEPT_CREATED
RELATION_COMMITTED
CLAIM_COMMITTED
CONTRADICTION_RECORDED
RESONANCE_COMMITTED
WORKSPACE_CYCLE
PLASTICITY_CHANGED
STRUCTURE_CANDIDATE_OBSERVED
STRUCTURE_PROMOTED
STRUCTURE_AVAILABILITY_CHANGED
STRUCTURE_USED
STRUCTURE_INTERACTION_VERIFIED
HIERARCHY_CANDIDATE_OBSERVED
HIERARCHY_PROMOTED
HIERARCHY_USED
STRUCTURAL_CHALLENGE_RECORDED
STRUCTURE_REFOLDED
MEDIA_IMPORTED
ERROR
```

The event mapper should prefer existing canonical event records wherever possible rather than synthesizing semantics from state diffs.

### 11.3 Telemetry levels

- **Normal:** committed cognitive events and key metrics.
- **Research:** adds per-stage cost, candidate scores, route/workspace details.
- **Engineering:** adds timings, memory, hashes, worker diagnostics and API traces.

Telemetry level must never change cognitive behavior.

---

## 12. Project, Organism, Run and Branch Model

The Workbench needs explicit identities above the engine checkpoint:

```text
Project
  ├─ Organism
  │    ├─ Run / developmental history
  │    │    ├─ Checkpoints
  │    │    └─ Branches
  │    └─ Notes / labels (Workbench-only)
  ├─ Curricula
  ├─ Experiments
  └─ Provider captures
```

Definitions:

- **Project:** Workbench organizational container.
- **Organism:** conceptual identity associated with a Verdant lineage.
- **Run:** one execution branch with an ordered event history.
- **Checkpoint:** verified snapshot of canonical engine state.
- **Branch:** a new run whose parent checkpoint and ancestry are preserved.

Workbench naming and notes may change freely. Engine lineage hashes may not.

---

## 13. Curriculum Studio

### 13.1 Design goal

A researcher should be able to write teaching material without writing Python while still seeing exactly what will enter Verdant.

### 13.2 Compilation pipeline

```text
Source
  -> parser / optional provider proposal
  -> Curriculum AST
  -> Teaching IR
  -> validation
  -> compiled ExperienceCommand sequence
  -> immutable .vcurr artifact
```

### 13.3 Required editor views

**Source** — original human/provider-authored content.  
**Parsed** — syntax and extracted primitives.  
**Compiled** — exact Teaching IR / native event sequence.  
**Diff** — changes between curriculum versions or compiler passes.

### 13.4 Curriculum IR

The first Workbench IR should remain explicit and narrow:

```json
{
  "schema": "verdant.curriculum.v1",
  "curriculum_id": "vcurr_...",
  "title": "Alien Dynamics A",
  "compiler_version": "...",
  "source_sha256": "...",
  "items": [
    {
      "item_id": "lesson_0001",
      "context_id": "world-a",
      "labels": ["kren", "tar", "vel"],
      "feature_vector": [1,0,0,0,0,0,0,0],
      "confidence": 1.0,
      "provenance": {
        "origin": "human",
        "source_span": "..."
      }
    }
  ]
}
```

The compiler can become richer later, but v1 must not pretend to understand arbitrary prose better than it does.

### 13.5 Teaching commit workflow

```text
EDIT -> COMPILE -> REVIEW -> FREEZE VERSION -> TEACH
```

There is no normal-mode `EDIT -> DIRECT GRAPH MUTATION` path.

---

## 14. External LLM / Model Provider Architecture

### 14.1 Role

External models may help author or transform teaching material. They are outside the Verdant cognitive substrate.

```text
Human goal
   -> provider request
   -> captured provider response
   -> proposed curriculum
   -> human review/edit
   -> deterministic compiler
   -> frozen curriculum
   -> Verdant
```

### 14.2 Provider contract

```python
class CurriculumProvider(Protocol):
    provider_id: str
    def capabilities(self) -> ProviderCapabilities: ...
    def propose(self, request: CurriculumRequest) -> ProviderCapture: ...
```

Initial adapters may support hosted APIs and local models, but the application must treat them identically after capture.

### 14.3 Reproducibility rule

Provider calls are not repeatable by assumption. Therefore every accepted call stores:

```text
provider
model identifier
request body hash
relevant generation settings
raw response hash
raw captured response
timestamp
user edits after response
compiler version
final curriculum hash
```

A benchmark must be able to select **Replay Capture** instead of calling the provider again.

### 14.4 Secret handling

Secrets are stored in OS-provided or local encrypted secret storage. They are referenced by provider configuration ID and excluded from all exported run artifacts.

---

## 15. Grammar and Language Lab

The Workbench should expose the existing controlled grammar path as a first-class lab surface.

Required features:

- grammar rule browser;
- lexicon browser/editor;
- parse tester;
- token/frame inspection;
- source-to-semantic-plan preview;
- compile-to-teaching preview;
- ambiguity/failure display;
- curriculum version linkage;
- later separation of **TAUGHT GRAMMAR**, **PROPOSED GRAMMAR** and **EARNED STRUCTURAL REGULARITIES**.

The grammar editor must use the same review/freeze/teach workflow as Curriculum Studio.

---

## 16. Cultivation / Live Run Console

The live run screen is the graphical successor to `run_verdant_cultivation.py`.

### 16.1 Core controls

```text
RUN
PAUSE
STEP 1
STEP N
STOP
SAVE CHECKPOINT
FORK
TEACH ITEM
PROBE
ABLATE / RESTORE
CHALLENGE / REFOLD
```

### 16.2 Status panel

Display at minimum:

```text
cycle
state revision
concept count
relation count
claims / contradictions
plastic associations
structure candidates
promoted P structures
Q structures
workspace occupancy
field history
active shard / route
worker CPU/RAM (engineering mode)
```

### 16.3 Provenance stream

The live event stream must visually separate:

```text
PROGRAMMED
TAUGHT
OBSERVED
ASSOCIATED
PROPOSED
MANUFACTURED
PROMOTED
USED
CHALLENGED
REFOLDED
```

This is a display classification over recorded provenance, not a new learning mechanism.

---

## 17. Explorer: Living View + Forensic View

### 17.1 Living View

The Living View is the intuitive, animated representation of actual cognitive development. It may show:

- current workspace focus;
- local activation/resonance;
- plastic neighborhoods strengthening/decaying;
- structure candidates becoming coherent;
- `P` promotions;
- `P`-to-`P` interactions;
- `Q` formation;
- dormancy/reactivation;
- contradiction pressure;
- split/revision/refolding;
- shard routing and inactive/cold regions.

### 17.2 Forensic Overlay

Every visible object should be selectable. Selecting a structure should reveal:

```text
ID / opaque name
formation cycle
constituents
frozen topology
current availability
source evidence
contexts
candidate quality history
promotion report
Council decision
use events
compilation measurements
interaction events
parent/child hierarchy
challenge/refold lineage
checkpoint/event references
```

### 17.3 Replay Formation

A structure inspector should support **Replay Formation**, which replays the recorded event window around candidate formation/promotion without re-running or changing the organism.

### 17.4 Rendering rule

Animations may interpolate between committed states for readability, but they must not invent unrecorded cognitive events.

---

## 18. Evidence and Knowledge Inspector

Provide searchable views over:

- evidence records;
- concepts;
- canonical relations;
- claims;
- contradictions and revisions;
- ECWF addresses/profiles/resonance events;
- workspace records;
- plastic associations;
- P structures;
- Q structures;
- sensory/perceptual evidence;
- governance decisions;
- lineage.

Each record view should include raw JSON and human-readable presentation.

A cross-reference panel should answer: **Where did this come from, what used it, and what depends on it?**

---

## 19. Experiment Manager

### 19.1 Experiment specification

Experiments are immutable manifests plus referenced artifacts.

```yaml
schema: verdant.experiment.v1
name: alien-world-transfer-004
engine:
  commit: <git sha>
  build_id: <hash>
seed: 41823
curriculum:
  artifact: vcurr_<hash>
arms:
  - id: A
    mode: canonical
  - id: B
    mode: ecwf
  - id: C
    mode: plastic_no_folds
  - id: D
    mode: full
metrics:
  - reconstruction_work
  - structure_count
  - field_comparisons
  - plastic_density
interventions:
  - arm: D
    action: ablate_structure
    selector: <resolved during protocol>
```

### 19.2 Required experiment operations

- validate manifest;
- resolve all artifact hashes;
- launch arms in isolated workers;
- record common seed/config/curriculum;
- stream progress;
- collect final state hashes and metrics;
- run declared interventions;
- export summary, raw event references and artifacts;
- rerun/verify from the manifest.

### 19.3 Claim inspector

A reported scientific claim should be represented as a verification bundle:

```text
Claim
Metric definition
Source run(s)
Baseline value
Treatment value
Ablation value
Restoration value
Checkpoint hashes
Event ranges
Curriculum hash
Engine build hash
[REPLAY] [FORK] [EXPORT]
```

---

## 20. Timeline, Checkpoints and Branching

The Workbench should treat developmental history as a navigable tree.

```text
seed
 |
 +-- checkpoint 1000
     |
     +-- checkpoint 5000
         |
         +-- P_17 formed
             |
             +-- Q_3 formed
                 |
                 +-- branch A: contradiction curriculum
                 +-- branch B: continue original
                 +-- branch C: ablate P_17
```

Required behaviors:

- save checkpoint;
- verify checksum;
- label checkpoint in Workbench metadata;
- continue;
- branch;
- compare branch metrics;
- show parent checkpoint and ancestry;
- never rewrite a parent's historical artifact.

---

## 21. Artifact and File Formats

Existing formats should remain valid. The Workbench adds wrappers rather than replacing them.

### Existing

- `.vdk` — canonical Verdant checkpoint.
- `.vrun.zip` — portable run package.
- `.vmi.zip`, `.vsa.zip` — native media/sensory archives where applicable.

### Proposed

#### `.vcurr`
Immutable compiled curriculum package:

```text
manifest.json
source/
provider_capture/      optional
curriculum_ir.json
compiled_commands.jsonl
hashes.json
```

#### `.vexp`
Experiment verification package:

```text
manifest.yaml
curriculum/            embedded or content-addressed ref
initial_checkpoints/
provider_captures/
results/
expected_assertions.json
hashes.json
```

#### Workbench project directory
Do not invent a new cognitive checkpoint format. A project directory can contain:

```text
project.json
workbench.db
artifacts/
runs/
curricula/
experiments/
provider_captures/
exports/
```

---

## 22. Workbench REST API — Initial Map

### Projects

```text
GET    /api/v1/projects
POST   /api/v1/projects
GET    /api/v1/projects/{project_id}
```

### Organisms / Runs

```text
POST   /api/v1/organisms
POST   /api/v1/organisms/load
POST   /api/v1/runs/{run_id}/start
POST   /api/v1/runs/{run_id}/pause
POST   /api/v1/runs/{run_id}/step
POST   /api/v1/runs/{run_id}/stop
GET    /api/v1/runs/{run_id}/status
GET    /api/v1/runs/{run_id}/snapshot
WS     /api/v1/runs/{run_id}/events
```

### Teaching / Curriculum

```text
POST   /api/v1/curricula/compile
POST   /api/v1/curricula/freeze
POST   /api/v1/runs/{run_id}/teach
POST   /api/v1/runs/{run_id}/probe
```

### Structures / interventions

```text
GET    /api/v1/runs/{run_id}/structures
GET    /api/v1/runs/{run_id}/structures/{id}
POST   /api/v1/runs/{run_id}/structures/{id}/promote
POST   /api/v1/runs/{run_id}/structures/{id}/ablate
POST   /api/v1/runs/{run_id}/structures/{id}/restore
POST   /api/v1/runs/{run_id}/structures/{id}/interact
POST   /api/v1/runs/{run_id}/structures/{id}/challenge
POST   /api/v1/runs/{run_id}/structures/{id}/refold
```

### Checkpoints

```text
POST   /api/v1/runs/{run_id}/checkpoints
GET    /api/v1/runs/{run_id}/checkpoints
POST   /api/v1/checkpoints/{id}/branch
```

### Experiments

```text
POST   /api/v1/experiments/validate
POST   /api/v1/experiments/run
GET    /api/v1/experiments/{id}
WS     /api/v1/experiments/{id}/events
POST   /api/v1/experiments/{id}/verify
POST   /api/v1/experiments/{id}/fork
```

### Providers

```text
GET    /api/v1/providers
POST   /api/v1/providers/{id}/propose-curriculum
GET    /api/v1/provider-captures/{capture_id}
```

These routes are a design map, not a requirement to expose every operation in the first build.

---

## 23. Frontend Information Architecture

Recommended primary navigation:

```text
Home / Organism
Cultivate
Curriculum Studio
Language / Grammar
Explorer
Structures
Evidence
Experiments
Timeline
Connections
Engineering
```

### Home / Organism
Identity, active run, checkpoint, health, current cycle and developmental summary.

### Cultivate
Live controls, teaching box, event stream, probes and interventions.

### Curriculum Studio
Author, import, optional provider assist, parse, compile, diff, freeze and run curricula.

### Language / Grammar
Rules, lexicon, parse tests, semantic plan and language curriculum.

### Explorer
Living cognitive landscape plus forensic overlay.

### Structures
P/Q candidates, promoted structures, lineage, interaction, use and refolding.

### Evidence
Canonical evidence/knowledge/claims/contradictions/provenance.

### Experiments
Manifests, arms, seeds, repetitions, metrics, ablations and verification packages.

### Timeline
Checkpoints, branches, run history and compare.

### Connections
External curriculum providers/local models and plugin status.

### Engineering
Raw logs, worker health, timing, memory, state hashes, API/event inspector and profiling hooks.

---

## 24. Plugin / Extension SDK

Initial extension contracts should be narrow and typed.

```python
CurriculumProvider
LanguageParserProvider
FeatureEncoderProvider
SensorAdapter
MetricProvider
ExperimentProtocol
VisualizationLayer
Exporter
```

Each plugin manifest should declare:

```text
plugin ID
version
API contract version
capabilities
required permissions
configuration schema
code/package hash
```

A run using a plugin records the exact plugin/version/hash in its manifest.

Plugins that alter engine computation should be explicitly classified as **experimental engine components**, not ordinary Workbench extensions, and should create a distinct engine build identity.

---

## 25. Security and Integrity Model

### 25.1 Threat boundaries

Relevant risks include:

- provider secrets leaking into exports;
- malicious or buggy plugins;
- arbitrary file imports;
- corrupted checkpoints;
- stale UI commands applied to newer state;
- event or result files edited after a run;
- accidental direct state mutation;
- provider content being mistaken for Verdant-generated content.

### 25.2 Required controls

- verify checkpoint/archive hashes on load;
- content-hash Workbench artifacts;
- record engine build/commit;
- redact secrets from logs by construction;
- isolate provider credentials from project artifacts;
- capability-gate plugins;
- restrict file-system roots in packaged builds where practical;
- use stale-state/revision checks on mutations;
- clearly mark externally mutated/debug runs;
- sign or at minimum hash experiment verification packages.

---

## 26. Reproducibility Standard

A reproducible run should be identifiable by:

```text
engine build hash
Workbench schema version
seed
initial checkpoint hash
policy/config hash
curriculum hash
provider capture hashes (if used)
plugin hashes
ordered command/event inputs
```

For a deterministic protocol:

```text
same reproducibility tuple
    -> same final canonical checkpoint hash
```

Any known source of nondeterminism must be declared in the manifest rather than hidden.

---

## 27. Performance and Scaling Targets

These are initial engineering targets, not scientific claims.

### UI

- command acknowledgement should normally appear within 100 ms when the engine is idle;
- event batching should prevent UI lockups during high-frequency runs;
- visual rendering should be decoupled from engine event ingestion;
- graph rendering should use level-of-detail and aggregation for large states.

### Backend

- engine workers must not execute in the FastAPI request thread;
- event persistence should be append-oriented and batched;
- large raw payloads should be stored as artifacts and referenced by hash instead of duplicated in SQLite;
- snapshots should offer scopes such as `summary`, `workspace`, `structure`, `full_debug`.

### Engine integration

The Workbench should not optimize or change cognitive algorithms merely to improve UI performance. Engine performance work remains separately benchmarked.

---

## 28. Testing Strategy

### 28.1 Engine regression

Existing engine tests remain mandatory and must pass unchanged.

### 28.2 Adapter contract tests

For every Workbench command:

- validate request;
- perform operation through adapter;
- verify expected canonical state/event;
- verify event envelope;
- verify stale command rejection;
- verify persistence/reload.

### 28.3 Golden replay tests

Store small deterministic fixtures where:

```text
manifest + curriculum + seed
-> known final checkpoint hash
-> known event summary
```

### 28.4 API integration tests

Test worker start/stop, event streaming, save/load, branch, curriculum freeze, experiment launch and recovery.

### 28.5 UI end-to-end

Use Playwright or equivalent to verify:

- create organism;
- compile/teach curriculum;
- run/pause/step;
- inspect P formation;
- save/fork;
- execute ablation/restoration;
- replay a claimed result.

### 28.6 Soak tests

Run long developmental sessions while monitoring:

```text
worker memory
Workbench DB growth
event queue lag
WebSocket reconnect behavior
checkpoint integrity
UI responsiveness
```

---

## 29. Proposed Repository Layout

Do not bury the Workbench inside the engine packages. Suggested monorepo structure:

```text
verdant/
  engine/                         # current rebuild packages
    verdant_kernel/
    verdant_development/
    ...

  workbench/
    backend/
      verdant_workbench/
        api/
        engine_adapter/
        runs/
        projects/
        curriculum/
        experiments/
        providers/
        plugins/
        telemetry/
        artifacts/
        security/
      tests/

    frontend/
      src/
        app/
        api/
        pages/
        components/
        explorer/
        curriculum/
        structures/
        experiments/
        timeline/
        engineering/
      tests/

    schemas/
      curriculum/
      experiment/
      events/
      plugins/

  docs/
    workbench/
    architecture/
    experiments/
```

If retaining the current repository root is preferable, the same logical separation can be introduced as `verdant_workbench/` and `workbench-ui/` beside the existing engine packages.

---

## 30. Implementation Roadmap

### WB-00 — Architecture Freeze and Scaffold

**Purpose:** establish directory structure, schema versioning, project conventions and dependency boundaries.

**Exit criteria:**

- Workbench backend/frontend skeletons start locally;
- engine imports remain untouched;
- first ADR set committed;
- API/event schema version constants exist;
- CI can run engine tests and empty Workbench tests.

### WB-01 — Engine Adapter + Isolated Run Worker

**Purpose:** make one Verdant controllable through a stable headless facade.

**Build:**

- `VerdantEngineAdapter`;
- worker supervisor;
- create/load/save;
- submit experience;
- step/probe;
- metrics/snapshot;
- command IDs and state revisions.

**Exit criterion:** CLI test client can operate M19 functionality without importing cognitive subsystem pipelines directly.

### WB-02 — Project / Run / Checkpoint Service

**Purpose:** persistent laboratory identity and history management.

**Build:** SQLite metadata, artifact store, project/run/branch/checkpoint models, integrity verification.

**Exit criterion:** create -> run -> save -> close -> reopen -> branch yields correct canonical hashes and ancestry.

### WB-03 — Live API + Cultivation Console

**Purpose:** replace the hand-built cultivation runner with the first real UI.

**Build:** REST endpoints, WebSocket event stream, run/pause/step, teach/probe, status metrics, event log, save/fork.

**Exit criterion:** all core cultivation-runner operations can be performed without a terminal.

### WB-04 — Curriculum Studio + Grammar Lab

**Purpose:** deterministic teaching authoring and compilation.

**Build:** source/parsed/compiled/diff editors, `.vcurr`, compiler, JSONL import, grammar/lexicon/parse views.

**Exit criterion:** a user can author, review, freeze and run the M19 alien curriculum entirely through the Workbench.

### WB-05 — Structures + Forensic Explorer

**Purpose:** make learned organization inspectable and replayable.

**Build:** P/Q inspectors, lineage, promotion gates, event references, ablate/restore/challenge/refold UI, initial graph view, Replay Formation.

**Exit criterion:** a researcher can trace a visible P/Q object back to the exact evidence/events that produced it and reproduce its causal ablation.

### WB-06 — Living Explorer

**Purpose:** scientific animation of actual cognitive dynamics.

**Build:** event-driven canvas/WebGL renderer, workspace/association/fold layers, time controls, forensic overlay, level-of-detail.

**Exit criterion:** no cognitive animation exists without a backing recorded state/event; replay and live modes visually agree at key checkpoints.

### WB-07 — Experiment Manager / Verification Packages

**Purpose:** turn M19 benchmark logic into a general laboratory feature.

**Build:** `.vexp`, multi-arm orchestration, shared curriculum/seed locking, result/claim inspector, replay/fork/export.

**Exit criterion:** the four-arm Ethomorphism benchmark can be authored/launched/verified through Workbench and exported as a self-contained verification package.

### WB-08 — Provider Connections

**Purpose:** optional external curriculum assistance without contaminating Verdant cognition.

**Build:** provider interface, secrets, captures, replay, human review flow, local-model adapter contract.

**Exit criterion:** provider-generated curriculum can be captured, frozen, replayed offline and traced separately from Verdant-generated structures.

### WB-09 — Plugin SDK, Packaging and Hardening

**Purpose:** make the platform usable by outside engineers.

**Build:** typed plugin contracts, plugin manifest/permissions, documentation, packaged launcher, crash recovery, accessibility and security review.

**Exit criterion:** an external developer can add a metric/provider/adapter from documented APIs without changing core Workbench or engine code.

---

## 31. Workbench 1.0 Acceptance Criteria

Workbench 1.0 is not complete merely because the Explorer looks good. It is complete when an independent researcher can:

1. clone/install and launch the Workbench;
2. create or load a Verdant organism;
3. inspect the exact engine version and configuration;
4. author or import a curriculum;
5. inspect and freeze what will actually be taught;
6. run, pause and single-step development;
7. watch live recorded cognitive events;
8. inspect evidence, P/Q structures and lineage;
9. save, reload and branch checkpoints;
10. run an ablation/restoration test;
11. reproduce the M19 benchmark from a manifest;
12. verify result claims from raw event/checkpoint references;
13. export a self-contained experiment package;
14. add at least one documented external provider or metric plugin;
15. perform all of the above without changing the Verdant engine source.

---

## 32. Initial Build Backlog

The first implementation sprint should remain deliberately unglamorous. Build the contracts before the scenery.

### Immediate P0 tasks

1. Add `workbench/backend` and `workbench/frontend` scaffolds beside the M19 engine.
2. Write ADR-001 through ADR-010 as repository architecture records.
3. Implement `VerdantEngineAdapter` around create/load/development/probe/save operations.
4. Define `CommandEnvelope`, `EventEnvelope`, `RunDescriptor` and `Snapshot` schemas.
5. Implement a supervised single-organism worker process.
6. Implement a tiny FastAPI server with `/health`, run create/load/status/step and WebSocket events.
7. Add a filesystem artifact store plus SQLite project/run index.
8. Build the first React shell with Home and Cultivate pages.
9. Reproduce one existing `run_verdant_cultivation.py` scenario through the API and prove checkpoint hash equivalence.
10. Only after task 9 succeeds, begin Curriculum Studio and Explorer rendering.

### First engineering proof

The first Workbench proof should be intentionally boring:

```text
terminal cultivation run
        versus
Workbench API cultivation run
```

Given the same initial state, seed and commands, both must produce:

```text
same canonical checkpoint hash
same cognitive event records
same metrics
```

If this equivalence does not hold, the Workbench integration is wrong and visualization work should stop until it is fixed.

---

## 33. Open Questions to Resolve During WB-00/WB-01

1. Should worker IPC use multiprocessing queues, localhost RPC, or a small internal message protocol? Recommendation: start with supervised subprocess + typed local IPC, keep it replaceable.
2. Should event indexing use SQLite JSON payloads or append-only JSONL plus SQLite indexes? Recommendation: append-only event artifacts plus SQLite metadata/indexes for large-run durability.
3. How much of `KernelState` is safe to expose in general snapshots? Recommendation: explicit view models, not raw unrestricted state by default.
4. What is the first supported platform set for packaged Workbench? Recommendation: develop browser-based local app first; package after API/UI contracts stabilize.
5. How should very large cognitive graphs be rendered? Recommendation: hierarchical/aggregated LOD with on-demand local expansion; do not attempt a global DOM graph.
6. Should curriculum compilation initially support arbitrary prose? Recommendation: no. Start with explicit structured lessons plus controlled grammar, then layer optional provider-assisted prose decomposition.
7. What constitutes a publication-grade experiment bundle? Recommendation: manifest, engine build/hash, all immutable inputs, provider captures, plugin hashes, initial checkpoint, expected assertions, result summaries and raw referenced telemetry.

---

## 34. Definition of the Engineering Goal

The Workbench succeeds when Verdant can be treated like a scientific instrument rather than a bespoke script collection.

A researcher should be able to ask:

> **What did this organism experience, what did it manufacture, what did that manufactured structure causally change, and can I reproduce or falsify the result?**

The application must answer that question from recorded engine artifacts, not from presentation-layer interpretation.

The resulting architecture is therefore:

```text
VERDANT ENGINE
    cognitive substrate

        +

VERDANT WORKBENCH
    operate
    teach
    observe
    inspect
    experiment
    verify
    extend

        =

A REPRODUCIBLE DEVELOPMENTAL AI LABORATORY
```

This document is the architecture baseline for beginning implementation.
