# DependencyGap Obligation Substrate v0.1

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

## Explicit exclusions

- No automatic detection of DependencyGaps from semantic content yet.
- Target refs, missing-input signatures, cut partitions, and initial reopen
  predicates are supplied through the typed experimental API; endogenous graph
  derivation of those inputs is the next layer, not a v0.1 claim.
- No scheduler loop or background clock yet; probes, audit pings, and graph
  deltas are explicitly submitted through the experimental pipeline.
- No `Resolved` API until a Resolution Contract and matched-control validator
  exist. The model contains future event/status types, but v0.1 does not grant
  resolution authority.
- No Equivalence Lens registry, counterfactual micro-runtime, Council
  tournament, or Paradigm Challenge implementation yet.
- No thermodynamic control authority. `T_g` remains observer-only.

## Access-pressure integration

Pre-admission access pressure is now a typed v2 observation and a distinct
Workbench event (`ACCESS_PRESSURE_OBSERVED`). An unknown cue produces an
explicit `incomplete` record with no partial candidate counts. It is not `T_g`,
not a semantic truth judgement, and has no behavioral authority.

## Falsification focus

The initial tests target deterministic identity and replay, checkpoint/View
rebuild equality, irrelevant-delta silence, remote cut crossing, wake-storm
deduplication, multi-causal stall supersession, source laundering, and budget
renewal that does not create a new search space.
