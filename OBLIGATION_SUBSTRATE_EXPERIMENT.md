# Obligation Substrate v0.12

Status: **implemented-experimental** on `test/obligation-substrate-v0`.

This branch implements the first deliberately narrow endogenous-inquiry
nucleus. It does not establish semantic understanding, general endogenous goal
generation, or safe autonomous policy revision.

## Implemented boundary

- Four obligation families at different maturity levels: the complete
  experimental `DependencyGap` vertical slice described below, and a bounded
  `Contradiction`, `PredictionFailure`, and `IdentityAmbiguity`
  detection/continuity substrate.
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
- A pure `DependencyGapResolutionValidator` evaluates replicated, preregistered
  baseline/treatment pairs from the same canonical checkpoint, cue, context,
  seed, horizon, and active family-local lens. Every observation cites a real,
  discarded simulation settlement and every candidate carries content-addressed
  simulation and lens-governance lineage.
- The v0.7 Resolution Contract checks matched controls, canonical evidence
  preservation, absence of edge/slot suppression, a changed outgoing action,
  operational explanatory gain, traceable lineage, active governance,
  DependencyGap path completion, and cross-seed replication. A completed path
  must run from the obligation's action node to canonical `ACTION` or `OUTCOME`
  evidence; a noncanonical dummy endpoint cannot satisfy the contract.
- Contract evaluation is fingerprint-pure across the kernel, simulation ledger,
  and lens sidecar. A passing `ResolutionContractVerdict` is explicitly
  non-authoritative and cannot append `Resolved`, promote the hypothetical
  structure, or otherwise mutate canonical state.
- A separately serialized `DiagnosticLedgerState` now holds immutable
  `DiagnosticObligation` and terminal `DiagnosticResult` records. Opening a
  diagnostic verifies the parent DependencyGap, canonical Attention decision,
  isolated failed-inquiry settlement, family-local lens binding, hypothesis
  lineage, and complete causal evidence references.
- Diagnostic reverse probes are capped by both count and simulation budget.
  Each typed primitive-baseline, adjacent-context, generator-coherence, or
  cost-calibration observation must cite a distinct isolated settlement whose
  result lineage includes the diagnostic and its declared basis evidence.
- The deterministic diagnostic reducer distinguishes a valid epistemic null,
  lens over-smoothing, lens hyper-discrimination, binding miscalibration,
  generator fault, scheduler misalignment, a multi-component interaction, and
  an inconclusive terminal result. Valid nulls attribute no component fault.
- The diagnostic circuit breaker is constitutional in the typed result: every
  result is terminal, has no epistemic authority, and cannot spawn a second
  diagnostic. The engine rejects direct attempts to diagnose a diagnostic
  result, including inconclusive and interaction-suspected outcomes.
- A separately serialized, non-executing `CouncilLeastRegretTournament` accepts
  two to eight typed intervention candidates only after a terminal diagnostic
  has attributed a component or interaction fault. Candidate kinds constrain
  their targets to the causal lens definition/binding, Attention decision,
  hypothesis generator, or a coordinated subset of that stack.
- Each intervention requires an isolated, successfully completed counterfactual
  settlement from the parent obligation. Its preservation observation records
  whether repair was restored, which known obligations would be reopened,
  integer wave-state/`c_memory`/observer-only `T_g` deviations, and exact
  before/after fingerprints for unrelated validation contexts.
- Failed repair, changed orthogonal fingerprints, checkpoint mismatch, broken
  simulation lineage, and unknown blast-radius references exclude a candidate.
  Surviving candidates form a Pareto frontier over blast radius and the three
  ripple measures. A scale-free minimax rank of preservation regret selects the
  recommendation; component footprint is only a final tiebreaker.
- High blast radius is therefore an auditable cost, not a permanent veto. The
  resulting `CouncilTournamentDecision` is content-addressed, replay-safe, and
  explicitly has no intervention authority; it cannot apply its recommendation.
- A deterministic `ContradictionObligationDetector` now consumes Verdant's
  existing canonical `ContradictionRecord` objects. It performs no text parsing
  and makes no new truth judgement: both opposed claims, their native claim key,
  preserved evidence, and source-lineage roots define the detection context.
- Each contradiction produces an immutable, content-addressed
  `ContradictionObligationKernel`. Identity excludes the detection cycle and
  transient workspace state. Unchanged scans replay at zero canonical cost;
  changed canonical claim/evidence context appends a `Retriggered` event to the
  same anchor, while distinct claim keys remain separate.
- Contradiction kernels and histories use the same checkpointed canonical
  ledger and pure rebuildable `ObligationView` as DependencyGap. Kernel
  validation fails closed if the native contradiction, either opposed claim,
  or its canonical evidence disappears.
- Open contradiction anchors are eligible for the ordinary bounded Attention
  Portfolio, whose allocation remains executive-only and cannot change the
  contradiction or mark it resolved. DependencyGap-specific attempt, stall,
  wake, and recheck APIs fail closed on this new family.
- A deterministic `PredictionFailureDetector` now scans native
  `GovernanceOutcomeRecord` objects, comparing the Council proposal's declared
  harm risk with the canonical observed harm score already recorded by the
  governance outcome learner. Only outcomes meeting a visible, versioned error
  threshold become candidates.
- Each admitted mismatch produces an immutable
  `PredictionFailureObligationKernel` retaining the outcome, Council decision,
  proposal, physical outcome evidence, action class, expected value, observed
  value, exact error, and source lineage. Identity excludes detection cycle and
  workspace context; distinct prediction events remain distinct.
- Unchanged scans replay without a canonical write. A detector-policy revision
  can retrigger the same immutable mismatch without fragmenting its identity.
  Checkpoint validation fails closed if its prediction, outcome, numerical
  values, evidence, or causal lineage is missing or changed.
- Prediction-failure anchors are eligible for bounded executive Attention, but
  no allocation can resolve them. DependencyGap-specific lifecycle operations
  continue to reject every other family.
- A deterministic `IdentityAmbiguityDetector` now consumes native proto-object
  candidates only when the object tracker has already marked a candidate
  `CONTESTED`, recorded an ambiguity event, and preserved at least two competing
  candidates. It does not parse labels or accept a teacher-declared entity pair.
- Each ambiguity creates an immutable `IdentityAmbiguityObligationKernel`
  retaining the contested candidate, initial competitor set, all bounded
  observation/evidence history available at creation, and source lineage.
  Identity is scoped to the contested candidate rather than the detection cycle.
- Pure scans are fingerprint-invariant, unchanged scans replay at zero cost,
  policy-version changes retrigger the same question, and independent contested
  candidates remain separate. Checkpoint validation fails closed if the native
  competition or any immutable triggering reference disappears.
- Identity anchors can receive ordinary bounded Attention but cannot declare
  unity or distinction. A new cross-family creation invariant also requires
  every obligation's creation event to retain exactly the immutable triggering
  refs recorded by its kernel.

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
  provenance-visible bids, but v0.12 does not claim Verdant has learned their
  calibration. The scheduler's ordering policy remains falsifiable machinery.
- Cut partitions and initial reopen predicates are still supplied through the
  typed stall API. Automatic cut derivation is not a v0.2 claim.
- No scheduler loop or background clock yet; probes, audit pings, and graph
  deltas are explicitly submitted through the experimental pipeline.
- The Resolution Contract accepts explicitly supplied, typed trial observations;
  the counterfactual runtime does not yet derive retrieved/admitted sets,
  outgoing actions, or dependency paths from overlay execution automatically.
- No canonical `Resolved` API or earned-structure promotion exists. A passing
  verdict supplies bounded evidence for a later governor but grants no
  resolution authority itself.
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
  Council.
- Binding calibration is deliberately narrow: v0.6 uses a declared cumulative
  failure count. It does not yet learn contextual activation envelopes, compare
  failure rates against matched controls, or automatically consume diagnostic
  interaction attributions.
- `Contradiction` currently has detection, immutable identity, retrigger
  continuity, checkpoint replay, and anti-suppression validation only. It does
  not yet have provenance-symmetric-difference hypothesis generation,
  dimensional-separation Resolution Contracts, family-local learned lenses, or
  canonical resolution authority.
- `PredictionFailure` currently covers only the native governance prediction
  that declared harm risk for an authorized action and later received physical
  outcome evidence. It does not yet cover arbitrary workspace forecasts,
  object-motion mismatch strings, or externally supplied predictions.
- The initial prediction-error threshold is explicit developer policy. Verdant
  has not learned, calibrated, or revised this threshold, and an obligation does
  not prove that either the prediction or observation is semantically correct.
- Target-ablation hypothesis generation, matched baseline/ablation trials, and
  PredictionFailure-specific Resolution Contracts remain unimplemented. No
  routing heuristic or P-structure is identified as causal in this increment.
- `IdentityAmbiguity` currently covers only Verdant's native proto-object
  association competition. It does not cover text aliases, claim-level entity
  resolution, promoted-concept mergers, or arbitrary developer-supplied pairs.
- Attribute-exclusivity proof, complete lineage merger, provisional
  coreference, and Identity-specific Resolution Contracts remain unimplemented.
  The obligation records an unresolved structural question; it does not answer
  whether any candidates represent the same real-world entity.
- Four family enum values now exist, but borrow-before-synthesize, held-out
  cross-family lens adoption, representational merging, and independent
  per-family rollback of a shared lens remain proposed rather than implemented.
- The registry/ledger boundary is separately serializable and tamper checked,
  but is not yet packaged into `.vdk` or committed into the canonical graph.
  Consequently, this increment establishes sidecar replay continuity, not
  crash-durable canonical lens governance.
- Isomorphic projection of earned structures and provenance-symmetric-difference
  generation remain unimplemented because the required resolved-history and
  additional obligation-family substrates do not yet exist.
- Governance validation proves that cited lens events exist and that the
  family-local binding is active; it is not a complete Council review.
- Resolution validation tests operational structure, not semantic truth. It
  does not establish that a completed path means what an external researcher
  interprets it to mean.
- Diagnostic probe findings are explicit, typed experimental observations. The
  engine verifies their simulation lineage and structural consistency but does
  not yet generate or execute reverse ablations autonomously.
- A diagnostic attribution does not penalize, suspend, revise, or roll back a
  scheduler, generator, binding, or lens. It is bounded evidence for the future
  Council intervention layer, not authority to edit evaluator machinery.
- The diagnostic ledger is a tamper-checked sidecar rather than canonical VDK
  state. It establishes deterministic in-process/snapshot replay, not durable
  canonical self-diagnosis across abrupt process loss.
- Candidate interventions and preservation measurements are explicit, typed
  experimental inputs. The Council does not yet generate a complete spanning
  intervention set or execute the standard-load simulations autonomously.
- Blast radius currently validates references against existing obligation
  kernels, but canonical resolution/promotion is still disabled. It therefore
  cannot yet prove that every listed obligation was historically closed or
  derive all obligations that would truly reopen after an edit.
- Wave-state, `c_memory`, and observer-only `T_g` deviations are reported by the
  counterfactual harness as deterministic integer observations; this increment
  does not independently derive them from physical resource use. `T_g` remains
  non-authoritative and cannot influence behavior.
- A Council recommendation cannot mutate, demote, roll back, or substitute any
  component. Applying interventions, validating post-application recovery, and
  the governed Paradigm Challenge lane remain unimplemented.
- The paired-checkpoint isolation result covers declared in-process kernel
  state and tested future behavior. The runtime currently performs no external
  I/O; it does not claim a general operating-system side-effect sandbox.
- No thermodynamic control authority. `T_g` remains observer-only.
- Native contradiction recognition still depends on the existing claim
  subsystem's explicit subject/predicate/object/polarity representation. The
  new detector does not establish semantic understanding, discover novel
  predicates, decide which claim is true, or operationalize consciousness.
- The `FailedPolicy` obligation family and governed Paradigm Challenge lane
  remain proposed.

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
Resolution-Contract tests additionally target replicated matched controls,
non-authoritative passing verdicts, kernel/ledger/lens purity, evidence-slot and
edge-suppression attacks, tautological unchanged actions, noncanonical dummy
paths, seed reuse, mismatched controls, unknown lineage/governance references,
simulation-budget enforcement, and checksum tampering.
Diagnostic-Obligation tests additionally target valid-null immunity, each
single-component attribution, multi-component interaction outcomes,
inconclusive termination, strict probe-kind typing, causal-lineage closure,
probe and budget ceilings, exact replay, sidecar reconstruction, tamper
rejection, and the non-recursive terminal circuit breaker.
Council-intervention tests additionally target Pareto dominance, scale-free
minimax regret, footprint-only tiebreaking, high-blast eligibility, orthogonal
fingerprint and failed-repair exclusion, cancelled/missing simulation lineage,
typed component targets, null-diagnostic rejection, all-candidate abstention,
exact request replay, sidecar reconstruction, decision tampering, and the hard
absence of intervention authority.
Contradiction-family tests additionally target fingerprint-pure inspection,
native-record anchoring, exact replay, evidence-driven retriggering, claim-key
scope separation, preserved claim/evidence references, checkpoint/View rebuild,
canonical-claim deletion rejection, and silence when no contradiction exists.
PredictionFailure-family tests additionally target native expected/observed
value derivation, threshold rejection, fingerprint-pure inspection, exact
replay, policy-version retriggering without identity fragmentation, event-scope
separation, checkpoint/View rebuild, numerical and lineage tamper rejection,
and executive Attention without resolution authority.
IdentityAmbiguity-family tests additionally target native contested-candidate
derivation, label-free evidence closure, fingerprint-pure inspection, exact
replay, policy-version retriggering, independent-scope separation, negative
noncontested controls, checkpoint/View rebuild, triggering-reference
suppression rejection, and executive Attention without identity authority.
