# DependencyGap Obligation Substrate v0.6

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
- A deterministic `DependencyGapHypothesisGenerator` composes candidate
  inquiries only from canonical graph paths, evidence kinds, obligation
  operands, and provenance references. Its bounded evidence-path projection is
  accompanied by mandatory null-artifact and insufficient-evidence hypotheses.
- Every projected candidate preregisters mutually named completion, stall, and
  conflict arms. A primitive `FunctionalConsequence` maps each arm to discrete
  activated canonical refs, proposed topology edges, and a bounded next action;
  continuous relation weights and generator identity do not define difference.
- A `FunctionalPartitionIndex` groups prospectively equivalent outcomes before
  simulation and marks redundant outcome arms. Distinct graph paths that expose
  the same evidence, proposed bridge, and action therefore cannot manufacture
  discrimination from cosmetic derivation differences.
- A selected preregistered arm can be translated into a `CounterfactualPlan`.
  Only a path-completion arm applies its hypothetical bridge patch, and the
  existing isolated runtime still prevents any canonical commit.
- Immutable `EquivalenceLensDefinition` records now hold a deterministic,
  side-effect-free operator IR in a content-addressed registry. Definitions
  preserve provenance and optional parent lineage; duplicate content reuses the
  same definition rather than creating identity churn.
- Family-local `LensBinding` records, append-only `LensEvidence`, and governance
  events occupy a separate typed ledger. Applying an active lens is a pure
  scheduler operation: it projects outcomes through the approved dimensions,
  creates discrete equivalence classes, and performs no governance write.
- Evidence distinguishes support, valid nulls, over-smoothing,
  hyper-discrimination, and absent explanatory gain. Valid nulls do not count
  as evaluator failures. A binding suspends atomically when its declared
  cumulative failure tripwire is reached, removing scheduler authority to use
  it without changing the immutable definition.
- Explicit rollback can reactivate only the suspended binding's direct,
  superseded predecessor. Approval, evidence, suspension, and rollback requests
  replay idempotently or reject changed reuse of their source key. Registry and
  ledger snapshots rebuild with identical fingerprints.

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
  provenance-visible bids, but v0.6 does not claim Verdant has learned their
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
- The v0.5 generator is limited to DependencyGap evidence-path projection. Its
  evidence kinds, traversable relation statuses, path-depth bound, and candidate
  cap remain explicit policy machinery; Verdant has not learned that grammar.
- The prospective arms are preregistered structural possibilities, not observed
  simulation results. No outcome evaluator yet selects which arm occurred, and
  no canonical `AttemptRecord` or obligation status transition is appended.
- Lens operators are typed, deterministic, provenance-visible selectors, but
  Verdant does not yet synthesize or revise them. Approval and evidence-result
  classification are explicit experimental inputs rather than an implemented
  Council or endogenous Diagnostic Obligation.
- Binding calibration is deliberately narrow: v0.6 uses a declared cumulative
  failure count. It does not yet learn contextual activation envelopes, compare
  failure rates against matched controls, or distinguish interaction faults.
- Only `DependencyGap` exists, so borrow-before-synthesize, held-out cross-family
  adoption, representational merging, and independent per-family rollback of a
  shared lens remain proposed rather than implemented.
- The registry/ledger boundary is separately serializable and tamper checked,
  but is not yet packaged into `.vdk` or committed into the canonical graph.
  Consequently, this increment establishes sidecar replay continuity, not
  crash-durable canonical lens governance.
- Isomorphic projection of earned structures and provenance-symmetric-difference
  generation remain unimplemented because the required resolved-history and
  additional obligation-family substrates do not yet exist.
- No Resolution Contract, Council tournament, Diagnostic Obligation, or
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
Hypothesis-generation tests additionally target deterministic and fingerprint-
pure composition, mandatory null/defer counterweights, bounded path search,
canonical provenance closure, cosmetic-path equivalence collapse, invariance to
continuous relation-confidence noise, tamper rejection, cross-hypothesis arm
rejection, and end-to-end execution through the non-committing runtime.
Equivalence-Lens tests additionally target content addressing, parent lineage,
read-only application, local dimensional projection, exact approval/evidence
replay, changed-request rejection, valid-null immunity, automatic suspension,
atomic tripwire failure, direct-predecessor rollback, deterministic sidecar
reload, and checksum/sequence tamper detection.
