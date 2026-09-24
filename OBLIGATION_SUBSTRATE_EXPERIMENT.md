# DependencyGap Obligation Substrate v0.4

Status: **implemented-experimental** on `test/obligation-substrate-v0`.

This branch implements the first deliberately narrow endogenous-inquiry
nucleus. It does not establish semantic understanding, general endogenous goal
generation, or safe autonomous policy revision.

## Implemented boundary

- One obligation family: `DependencyGap`.
- An immutable, deterministically identified `DependencyGapObligationKernel`.
- An append-only, checkpointed `ObligationHistoryEvent` chain with typed
  authorities and payload hashes.
- A non-authoritative `ObligationView` rebuilt by a pure fold over Kernel +
  History. The View is never checkpointed.
- Typed stall certificates containing bounded exhaustion claims, dependency
  cuts, attempt-equivalence signatures, lineage exclusions, version refs, and
  answer-agnostic reopen predicates.
- A two-stage `Stalled -> MayWake -> Recheck_Pending -> Reopened/Stalled`
  path. Irrelevant deltas cause no canonical write; wake storms collapse while
  an obligation is already `MayWake`. An `AuditPing` grants recheck eligibility
  only; it cannot itself satisfy the reopen predicate.
- Atomic canonical commits through a validated state copy and ordinary VDK
  checkpoint serialization.
- A deterministic `DependencyGapDetector` that scans canonical directed
  dependency edges without parsing concept labels. When a policy-declared
  dependency target lacks policy-declared canonical input evidence, the
  detector derives the action/input refs, local context hash, lineage roots,
  scope key, and source-event identity before appending the obligation.
- Pure inspection is fingerprint-invariant. Repeating an unchanged detection
  replays at zero canonical cost; newly accumulated non-qualifying local
  evidence retriggers the same obligation rather than fragmenting identity.
- A bounded `AttentionPortfolio` records one typed bid for every eligible
  obligation, computes a multidimensional Pareto frontier, protects a separate
  exploration reserve, and rotates starvation micro-probes using checkpointed
  selection history. Every grant and deferral is stored in a content-addressed
  `ObligationAttentionDecisionRecord` with a canonical transition.
- Attention decisions have no epistemic authority. Replaying the same decision
  request is a zero-cycle no-op, while reusing its source key with changed
  metrics is rejected.
- A causally non-committing `CounterfactualRuntime` now requires a canonical
  Attention allocation before it will reserve simulation budget. It exposes
  canonical mapping records through read-through access while retaining every
  upsert/delete only as a typed copy-on-write overlay patch.
- Simulation reservations and settlements live in a separately serializable
  `SimulationLedgerState`, not `KernelState`. Cumulative consumption is bounded
  by the originating Attention allocation, unused reservation is returned on
  settlement, identical requests replay without new cost, and changed reuse of
  a source key is rejected.
- Every settlement requires exact equality of the complete canonical kernel
  fingerprint before and after the dry run. Discarded, cancelled, and failed
  runs all remain non-authoritative and cannot commit their overlay.
- A paired-checkpoint test executes 100 mixed discarded/cancelled/failed
  simulations on one arm, then applies the same canonical event to both arms.
  Canonical fingerprints and obligation histories remain identical while only
  the simulation ledger differs.

## Explicit exclusions

- The v0.2 detector is endogenous only relative to canonical dependency edges:
  it derives obligation inputs from graph topology, but its visible, versioned
  policy still declares which relation types mean dependency and which evidence
  kinds count as available input. Verdant has not yet earned or revised that
  operator grammar.
- The detector heartbeat is explicitly invoked by the experimental pipeline;
  it is not yet attached to an autonomous Attention Portfolio scheduler.
- The Attention Portfolio and counterfactual runtime are explicitly invoked.
  The runtime consumes separately accounted simulation budget, but it does not
  yet move a `MayWake` obligation into `Recheck_Pending` or append an
  `AttemptRecord` to canonical obligation history.
- Expected gain, uncertainty, urgency, novelty, and cost arrive through typed,
  provenance-visible bids, but v0.3 does not claim Verdant has learned their
  calibration. The scheduler's ordering policy remains falsifiable machinery.
- Cut partitions and initial reopen predicates are still supplied through the
  typed stall API. Automatic cut derivation is not a v0.2 claim.
- No scheduler loop or background clock yet; probes, audit pings, and graph
  deltas are explicitly submitted through the experimental pipeline.
- No `Resolved` API until a Resolution Contract and matched-control validator
  exist. The model contains future event/status types, but v0.1 does not grant
  resolution authority.
- Simulation consumption is declared by the typed plan and bounded by its
  reservation; v0.4 does not yet meter physical CPU, memory, or wall-clock use.
- The separate ledger has a deterministic snapshot/reload model but is not yet
  packaged into `.vdk` or another crash-durable archive. Abrupt process-loss
  recovery and concurrent reservations remain outside this increment.
- The overlay supports a deliberately bounded set of canonical mapping
  collections and JSON hypothesis values. It does not validate those values as
  promotable canonical records and exposes no commit path.
- No compositional hypothesis generator, functional outcome partition,
  Equivalence Lens registry, Resolution Contract, Council tournament, or
  Paradigm Challenge implementation yet.
- The paired-checkpoint isolation result covers declared in-process kernel
  state and tested future behavior. The runtime currently performs no external
  I/O; it does not claim a general operating-system side-effect sandbox.
- No thermodynamic control authority. `T_g` remains observer-only.

## Access-pressure integration

Pre-admission access pressure is now a typed v2 observation and a distinct
Workbench event (`ACCESS_PRESSURE_OBSERVED`). An unknown cue produces an
explicit `incomplete` record with no partial candidate counts. It is not `T_g`,
not a semantic truth judgement, and has no behavioral authority.

## Falsification focus

The tests target deterministic identity and replay, checkpoint/View rebuild
equality, pure detector inspection, native action/input derivation, qualifying
evidence suppression, irrelevant and rejected edge rejection, explicit policy
grammar, local-evidence retriggering, Pareto membership, protected exploration,
complete eligible-set accounting, deterministic replay, starvation rotation,
checkpointed decision history, decision tamper rejection, irrelevant-delta
silence, remote cut crossing, wake-storm deduplication, multi-causal stall
supersession, source laundering, and budget renewal that does not create a new
search space. Counterfactual tests additionally target copy-on-write read
isolation, canonical-allocation enforcement, cumulative budget bounds,
separate-ledger reload, zero-cost request replay, changed-request rejection,
cancelled/failed partial settlement, explicit leak detection, and paired
checkpoint equivalence after 100 discarded simulations.
