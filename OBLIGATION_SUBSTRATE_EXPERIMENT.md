# Obligation Substrate v0.40

Status: **implemented-experimental** on `test/obligation-substrate-v0`.

This branch implements the first deliberately narrow endogenous-inquiry
nucleus. It does not establish semantic understanding, general endogenous goal
generation, or safe autonomous policy revision.

## Implemented boundary

- Five obligation families at different maturity levels: the complete
  experimental `DependencyGap` vertical slice described below, and a bounded
  `Contradiction`, `PredictionFailure`, `IdentityAmbiguity`, and `FailedPolicy`
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
- Every executed or replayed settlement now returns a content-addressed
  `CounterfactualExecutionTrace` reconstructed from the actual plan, canonical
  checkpoint, reservation, settlement, and materialized copy-on-write overlay.
  It covers every authorized overlay collection and records complete before/
  after collection hashes plus added, removed, and changed record keys.
- A paired-checkpoint test executes 100 mixed discarded/cancelled/failed
  simulations on one arm, then applies the same canonical event to both arms.
  Canonical fingerprints and obligation histories remain identical while only
  the simulation ledger differs.
- An explicitly invoked `.vob` experiment archive now pairs an unchanged VDK
  canonical checkpoint with the separately serialized simulation ledger and a
  versioned, content-addressed manifest. Writing the pair uses one temporary
  file, a synced replace, and a POSIX directory sync where available. Loading
  validates member hashes, both rebuilt fingerprints, and the reservation-to-
  canonical-Attention links before returning either reconstructed ledger.
- Controlled POSIX child termination now exercises the archive write boundary
  after temporary-file sync but before replacement, and after replacement but
  before directory sync. The visible path remains the complete prior archive
  in the first case and the complete candidate archive in the second.
- Six coordinated process writers and a live reader exercise whole-file atomic
  visibility. Every sampled byte sequence is one complete known archive, the
  final file reloads and serializes exactly, and successful writers leave no
  temporary member. This is last-successful-replace behavior, not writer
  ordering, locking, or merge semantics.
- The paired-archive test exercises `DependencyGap` and `Contradiction` in the
  same snapshot, then applies the same future canonical event to original and
  restored kernels. Both retain equal fingerprints and obligation Views while
  discarded simulation settlements remain in the isolated ledger. All 17
  existing VDK checkpoints also load and embed in an empty-ledger archive.
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
- An explicitly invoked `DependencyGapInquiryCoordinator` now stages the
  existing detector, hypothesis generator, functional partitioner, Attention
  Portfolio, and counterfactual runtime as one transaction. It publishes only
  after detector candidates are exactly the eligible `DependencyGap` set and
  every simulated arm leaves the post-Attention canonical fingerprint intact.
- The coordinator supplies one complete bid per eligible detected obligation,
  with provenance linking the detector candidate and canonical history event
  to every generated hypothesis and its functional partition. Each allocation
  funds a bounded, deterministic representative from at most three functional
  outcome classes; all plans remain discarded copy-on-write simulations.
- A content-addressed integration trace links candidate, obligation event,
  hypothesis, outcome, partition, Attention decision/allocation, plan,
  reservation, and settlement identifiers together with hashes of every
  visible component policy. Saving the resulting canonical and simulation
  state in an existing `.vob`, reloading it, and explicitly rerunning the same
  request reconstructs the identical trace at zero additional canonical or
  simulation cost.
- An explicitly invoked `MatchedCounterfactualObserver` compares a real
  zero-intervention baseline and full-patch treatment only when their canonical
  checkpoint, Attention decision/allocation, operator, budgets, declared
  patches, disposition, and result lineage share the same derived match
  signature. It derives additive, valid-null, or canonical-record-mutation
  structural effects from the materialized traces rather than accepting an
  outcome label from the caller.
- The matched structural receipt reports whether any pre-existing canonical
  overlay record was removed or changed. Both arms remain discarded
  simulations, and the receipt hard-codes simulated-only status with no
  observed-outcome, resolution, promotion, or commit authority.
- The opt-in coordinator now reserves two additional simulation slots per
  allocated `DependencyGap`: one zero-intervention baseline and one full-patch
  treatment built from a deterministic patch-bearing evidence-path hypothesis.
  It will run the pair only when the same Attention grant can also fund at
  least one of the existing preregistered outcome arms.
- Exactly one reconstructed `MatchedStructuralObservation` per allocation is
  embedded in the content-addressed integration trace. The coordinator checks
  the pair against its actual plans, reservations, settlements, runtime
  traces, obligation, Attention decision/allocation, hypothesis, and canonical
  checkpoint before publishing either staged state object.
- Exactly one content-addressed `TraceResolutionEvidenceReceipt` per matched
  observation now records the subset of Resolution Contract inputs that the
  actual structural trace can ground: cue and context, canonical checkpoint,
  settlement lineage, candidate structure and path provenance, structural
  delta, protected canonical references, and canonical-record preservation.
- The same receipt enumerates every input the structural trace does not
  observe: retrieved and admitted references, outgoing action, executed
  dependency path, seed, horizon, active Lens binding, slot budget, and
  held-out replication. Those absences are immutable and make
  `resolution_trial_ready` constitutionally false.
- Coverage is reconstructed from the actual paired simulation ledger and
  embedded one-for-one in the integration trace. Foreign-ledger substitution,
  missing coverage, changed requirement sets, and attempts to grant observed-
  outcome, resolution, or canonical-commit authority fail validation.
- A versioned `OverlayOperationalProbe` now reconstructs each settled matched
  arm from its actual plan and isolated simulation ledger, materializes the
  copy-on-write relation overlay, and performs one deterministic bounded graph
  walk from the canonical obligation action node.
- The probe traverses only policy-declared counterfactual relation types whose
  endpoints remain canonical concepts. It retrieves qualifying `ACTION` or
  `OUTCOME` evidence from the actual canonical terminal concept; evidence IDs
  merely claimed inside a hypothetical patch have no authority.
- A `MatchedOverlayOperationalObservation` compares the zero-patch baseline
  with the full-patch treatment and distinguishes access gain, access loss,
  path change, and valid operational null. An additive structural delta whose
  relation is outside the visible traversal grammar remains a valid null.
- Exactly one operational observation is cross-linked to each matched
  structural observation and Resolution-evidence receipt in the integrated
  trace. Reconstruction rejects foreign ledgers, noncanonical endpoints,
  changed probe results, missing observations, and forged authority flags
  before either staged state object is published.
- Overlay-local retrieval and path observations are now trace-grounded coverage
  categories. The distinct Resolution Contract requirements for retrieved and
  admitted workspace references, outgoing action, and an executed canonical
  dependency path remain missing, so `resolution_trial_ready` remains false.
- A standalone `OperationalTrialContext` now snapshots a declared calibration
  or held-out split, seed, bounded overlay-probe horizon, supplied slot budget,
  canonical checkpoint, and the exact active family-local Lens binding,
  definition, policy, and complete Lens-sidecar fingerprint before execution.
  Its content-addressed ID is included in both plans' result references and is
  therefore covered by plan, reservation, settlement, and execution-trace
  identities rather than attached after an outcome is known.
- A `ControlledOperationalTrialObserver` reconstructs both arms from their
  actual simulation ledger, verifies the exact hypothesis patch sequence and
  active Lens state, and reruns the operational probe with the declared horizon
  as its maximum relation-hop bound. Changed controls, a replaced Lens,
  unregistered hypothesis patches, missing result lineage, or a foreign ledger
  fail closed.
- A `HeldOutOperationalReplicationObserver` requires exactly one calibration
  trial and at least one held-out trial, distinct declared seeds, and identical
  horizon, slot budget, checkpoint, hypothesis, and Lens controls. It accepts
  only exact reproduction of both the materialized structural-effect signature
  and the ID-independent operational access signature.
- Saving the already durable canonical, simulation, and Lens sidecars and then
  reloading them reconstructs byte-equivalent trial contexts and the identical
  held-out replication receipt without new reservations or settlements. The
  contexts and derived receipts remain reconstructable artifacts, not new
  canonical records or archive members.
- An `IntegratedInquiryTrialControlRequest` now commits one calibration seed,
  one distinct held-out seed, relation-hop horizon, supplied slot budget, and
  the exact active `DependencyGap` Lens state before Attention runs. Its
  content-addressed ID and Lens lineage are carried by the bid's metric
  provenance and by the Attention source identity, so changing a control
  cannot reuse the prior allocation.
- The explicitly invoked `DependencyGapInquiryCoordinator` now requests budget
  for four matched-control simulations plus its bounded preregistered outcome
  arms. Under the default Attention micro-grant it executes exactly one
  preregistered representative and both predeclared zero/full pairs; it cannot
  spend beyond that one allocation.
- After Attention fixes the canonical checkpoint, the coordinator derives the
  calibration and held-out contexts before either pair executes, commits each
  context ID into both plans, and reconstructs every controlled structural and
  overlay-operational observation from the isolated simulation ledger. One
  held-out replication receipt per allocation must exactly cover those two
  pairs.
- The integrated trace now content-addresses the pre-Attention request, both
  controlled observations, and the held-out receipt. Dropped receipts,
  post-declaration Lens replacement, reused seeds, altered controls, observer
  tampering, or insufficient Attention fail the staged transaction without
  publishing canonical or simulation changes. Explicit archive reload replays
  the same allocation, contexts, settlements, and integrated trace at zero new
  cost.
- Underfunded allocations, absent projected interventions, altered receipts,
  canonical-record mutation, supplied outcome refs in a matched arm, and
  missing per-allocation receipts fail the whole staged invocation. A valid
  receipt remains a structural simulation result rather than evidence that a
  preregistered outcome occurred.
- A versioned `NativeWorkspaceAdmissionObserver` now revalidates each
  controlled observation against its actual simulation ledger and active Lens
  state, then maps only the canonical evidence references actually retrieved
  by that arm into native `RECALLED_EVIDENCE` workspace candidates.
- Each arm runs one real `VerdantWorkspacePipeline` cycle on an isolated clone
  of the post-Attention canonical checkpoint. The declared slot budget may
  tighten but never relax the canonical workspace maximum; the native report,
  committed shadow event, candidate dispositions, policy hashes, and complete
  shadow input/output fingerprints are retained in a content-addressed arm
  observation.
- A matched workspace observation distinguishes admission gain, loss, change,
  and valid null from the two native reports. An ID-independent effect
  signature must reproduce across the predeclared calibration and held-out
  seeds before a held-out workspace-admission receipt is accepted.
- Workspace observations and their held-out receipt are linked one-for-one to
  controlled trials and operational replication in the integrated trace.
  Missing receipts, foreign simulation ledgers, relaxed slot caps, rehashed
  authority claims, injected observer changes, or lineage substitution fail
  the staged transaction.
- Native workspace execution remains shadow-only: no workspace item, cycle,
  policy revision, semantic record, or action is published to the canonical
  kernel. Archive reload reconstructs the identical native workspace receipts
  from the already durable canonical, simulation, and Lens sidecars without
  another reservation or settlement.
- A versioned `NativeOutgoingActionObserver` now revalidates the complete
  controlled and native-workspace lineage before taking any action-side step.
  An arm with no admitted evidence records an explicit grounded no-action; an
  evidence-bearing arm creates a supplied reversible `INVESTIGATE` proposal
  whose evidence is exactly the arm's shadow-admitted canonical set.
- Verdant's real `VerdantGovernancePipeline` evaluates and commits that
  proposal only on the reconstructed workspace clone. The exact authorized
  operation and Council decision are then submitted as a native
  `AUTHORIZED_ACTION` workspace candidate, whose native admission report and
  event are retained with the proposal, three-King assessments, Council
  report, and decision.
- Matched action observations distinguish action gain, loss, change, and valid
  null. Their ID-independent action-effect signature must reproduce across the
  predeclared calibration and held-out seeds before an outgoing-action
  replication receipt is accepted.
- Action observations and held-out receipts are linked one-for-one through the
  controlled, operational, and workspace receipts in the integrated trace.
  Default recomputation rejects injected policies, altered authority flags,
  missing receipts, foreign simulation ledgers, or cross-lineage substitution
  before staged canonical or simulation state is published.
- The outgoing action is a shadow signature only. No operation is dispatched,
  no governance decision or workspace cycle is published to the canonical
  kernel, no governance outcome is recorded, and no action result is supplied
  to Resolution, Diagnostic, Council-intervention, or Paradigm ledgers.
- A separately saved, canonical-JSON `.viq` sidecar can now retain the complete
  v0.30 `IntegratedInquiryTrace`, including controlled structural, operational,
  workspace-admission, native Council/action, and held-out replication
  receipts. Its envelope binds the exact canonical, simulation-ledger, and Lens
  fingerprints plus a hash of the full nested trace.
- Loading a `.viq` requires the exact paired canonical, simulation, and Lens
  sidecars. The loader revalidates the canonical Attention decision and
  obligation events, every representative and matched-arm reservation and
  settlement, all canonical evidence references, the active family-local Lens,
  and the absence of embedded shadow Council/workspace records from canonical
  state before returning the receipt.
- Receipt writes use a synced temporary file, atomic replacement, and POSIX
  directory sync where available. Serialization is deterministic and read/write
  validation cannot reserve simulation budget, rerun an observer, dispatch an
  action, or mutate any paired state.
- Immutable `EquivalenceLensDefinition` records now hold a deterministic,
  side-effect-free operator IR in a content-addressed registry. Definitions
  preserve provenance and optional parent lineage; duplicate content reuses the
  same definition rather than creating identity churn.
- Family-local `LensBinding` records, append-only `LensEvidence`, and governance
  events occupy a separate typed ledger. Applying an active lens is a pure
  scheduler operation: it projects outcomes through the approved dimensions,
  creates discrete equivalence classes, and performs no governance write.
- An opt-in v2 `.vob` archive now makes the immutable Lens definition registry
  and append-only binding/evidence/governance ledger durable beside canonical
  VDK bytes and the isolated simulation ledger. The loader reconstructs the
  registry and ledger as one `EquivalenceLensSystem`, checks its fingerprint,
  requires every binding's definition lineage, and rejects lens events dated
  after the paired canonical checkpoint.
- Typed cross-sidecar refs are closed on archive save and load: any lens or
  simulation ref using a known Lens definition/binding/evidence/governance or
  simulation reservation/settlement identity prefix must exist in the paired
  archive. Legacy v1 canonical-plus-simulation archives remain readable and
  retain their original byte format.
- An explicit v3 `.vob` archive can additionally persist the append-only
  Diagnostic ledger. A diagnostic archive requires its Lens sidecar and
  revalidates each diagnostic's parent obligation, exact canonical Attention
  decision, failed-inquiry reservation and settlement, family-local binding and
  definition, hypothesis result lineage, causal evidence set, terminal
  attribution, available probe-settlement count, and an upper bound on
  traceable probe budget.
- Diagnostic archive loading rebuilds an independent `DiagnosticEngine` with
  the same fingerprint. v1 and v2 archive layouts remain readable and keep
  `diagnostic_engine=None`; ordinary VDK checkpoints remain unchanged.
- An explicit v4 `.vob` archive can additionally persist the Council
  intervention policy and append-only least-regret decision ledger. A Council
  archive requires the Diagnostic, Lens, simulation, and canonical layers it
  cites; loading reconstructs an independent, non-executing
  `CouncilLeastRegretTournament` with the same policy and ledger fingerprint.
- Each durable Council decision is rechecked against its exact terminal,
  actionable Diagnostic result and parent obligation. Every assessed candidate
  ID must remain present in a discarded, canonical-unchanged simulation
  settlement reserved for that same obligation. Rehashed foreign Council
  substitution and removal of candidate simulation lineage therefore fail
  closed before the bundle is returned.
- An explicit v5 `.vob` archive can additionally retain one content-addressed
  Council evidence record per decision sequence. Each record preserves the
  exact typed candidates and `EpistemicPreservationObservation` inputs used by
  the tournament. Loading rebuilds a fresh tournament from an empty ledger,
  reruns every decision in order against the recovered canonical, simulation,
  Lens, and Diagnostic state, and requires byte-model equality with the stored
  decision ledger—including its request hash, Pareto frontier, assessments,
  and selected candidate.
- Complete v5 evidence permits deterministic replay of explicitly configured
  Council candidate bounds. Incomplete decision coverage, changed evidence,
  changed request policy, or any replay result differing from the durable
  decision fails closed. The recovered tournament remains recommendation-only.
- An explicit v6 `.vob` archive can additionally retain the immutable Paradigm
  policy, append-only challenge/decision ledger, and one content-addressed
  shadow-trial evidence record per decision. The v6 envelope is cumulative: it
  requires the canonical, simulation, Lens, Diagnostic, Council, and Council-
  evidence layers already validated by v1-v5.
- v6 loading reconstructs a fresh Paradigm lane from an empty ledger, reopens
  every challenge from its preserved canonical anomaly signals, and reruns
  every decision from its exact shadow trials. Admission, complete-history
  replay, isolated-settlement lineage, cross-seed replication, evidence
  preservation, orthogonal stability, blast-radius references, and the hard
  non-promotion flags must reproduce the durable ledger exactly.
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
- An explicitly invoked `ContradictionHypothesisProtocol` now requires an
  active canonical Contradiction obligation and a current canonical Attention
  allocation whose typed operator, generator version, basis event, budget, and
  metric provenance authorize this family-local inquiry. Missing, underfunded,
  stale, foreign, or evidence-suppressing authorizations fail closed.
- Its content-addressed evidence receipt retains both claim snapshots, both
  polarities, each support and refutation ledger, every native contradiction
  evidence reference, and the supporting source roots. Evidence identity and
  source-root identity remain separate dimensions with explicit shared and
  symmetric-difference partitions.
- Every bundle contains exactly three preregistered alternatives: a provenance-
  partition test, a null encoding-artifact hypothesis, and an insufficient-
  evidence deferral. Each alternative carries the same complete protected
  claim/evidence set and canonical/Attention lineage; none may name a preferred
  claim, suppress evidence, select itself, resolve the obligation, or commit to
  canonical state.
- Generation and validation are read-only and deterministic across checkpoint
  reconstruction and mapping order. Validation rebuilds the complete expected
  bundle from canonical records, so even a fully rehashed context substitution
  is rejected rather than trusted as family-local evidence.
- An explicitly invoked `ContradictionProvenanceProbeRunner` now converts one
  validated bundle into a matched zero-patch baseline and one treatment that
  adds exactly one typed provenance projection to the copy-on-write
  `structures` overlay. Both plans retain the complete v0.33 evidence receipt,
  all three hypothesis references, both protected claims, every protected
  evidence reference, and the same canonical Attention lineage.
- The runner stages both reservations and settlements in a copied simulation
  ledger. It publishes the pair only after the existing matched observer has
  reconstructed both materialized overlays from their actual settlements and
  verified the single additive treatment delta. A stale bundle, budget failure,
  altered trace, or second-arm exception leaves the supplied simulation ledger
  unchanged; canonical state is fingerprint-invariant in every case.
- The resulting content-addressed observation classifies only the receipt's
  preserved source-root structure: disjoint nonempty roots are a distinct
  partition, identical roots are an explicit valid null, and a mixture of
  shared and distinct roots is inconclusive. These labels are deterministic
  structural descriptions rather than caller-supplied outcomes.
- The ordinary `.vob` simulation ledger is sufficient to replay both plans and
  reconstruct the identical probe and observation after archive reload. Probe
  and observation objects remain reconstructible, noncanonical artifacts; no
  new archive member or automatically saved sidecar is introduced.
- Every successfully published Contradiction probe pair now carries exactly one
  content-addressed `ContradictionResolutionEvidenceReceipt`. The receipt
  embeds the complete v0.33 hypothesis bundle and v0.34 matched observation,
  then duplicates their protected claims, protected evidence, source
  partitions, structural delta, canonical checkpoint, traces, settlements,
  and obligation lineage for fail-closed anti-suppression validation.
- The receipt marks only what those actual matched structural traces ground:
  canonical and Attention authorization, complete opposed-claim/evidence
  preservation, matched controls and settlement lineage, source-partition
  materialization, the structural delta, and the mandatory null/inconclusive
  alternatives. It explicitly records the absent family-local Lens, context-
  conditioned compatibility, dimensional separation, external outcome,
  functional consequence, held-out replication, predictive discrimination,
  and source independence.
- Coverage is reconstructed against the actual simulation ledger before the
  staged pair is published. Foreign ledgers, mismatched bundles, protected-
  evidence suppression, hidden missing requirements, or authority escalation
  fail validation. `resolution_trial_ready` remains hard-coded false.
- Each Contradiction probe now preregisters one immutable, content-addressed
  functional context before either arm executes. The context embeds the full
  hypothesis bundle, both canonical claim references, all protected evidence,
  exactly two claim-local source-root queries, their complete source-root
  union, and all three admissible distinct, valid-null, and inconclusive
  routing alternatives.
- The context ID is committed into both matched plans' result lineage and the
  complete context is committed into the treatment's typed projection. A new
  observer reconstructs both overlays from the actual simulation settlements,
  verifies that the baseline lacks the projection and the treatment contains
  the exact declared projection, then executes only the two preregistered
  source-root routes.
- The functional observation records the two before/after route signatures and
  classifies disjoint queries as distinct routing, identical queries as an
  explicit valid null, and partially overlapping queries as inconclusive. The
  Resolution coverage receipt therefore moves only context-conditioned
  compatibility and a bounded simulated functional consequence from missing
  to grounded.
- Functional contexts and observations remain deterministic reconstructible
  artifacts backed by the ordinary isolated simulation ledger; v0.36 adds no
  archive member or durable sidecar for them. Prediction, source independence,
  dimensional separation, independent held-out replication, external outcome,
  truth, readiness, resolution, promotion, and canonical commit authority all
  remain explicitly false.
- A new explicitly invoked `ContradictionLensControlledProbeRunner` requires
  its caller to build and supply one content-addressed controlled context
  before either v0.36 simulation arm can run. The context binds the exact
  functional query and source-event key to a detached snapshot of the complete
  Lens definition registry and binding/evidence/governance ledger.
- Context validation reconstructs that sidecar, requires exactly one active
  `Contradiction` binding, requires a nonempty evidence history for that
  binding, closes its last governance event, and admits only the typed
  `SELECT_ACTIVATED_REFS` operator supported by this bounded adapter. A foreign
  family, unsupported operator, suspended binding, changed sidecar, or omitted
  evidence fails before any simulation settlement is published.
- After the ordinary matched pair is reverified against the actual simulation
  ledger, the active Lens reads each actual treatment route's activated claim
  references and emits a content-addressed equivalence projection. It is a
  read-only classification: it neither changes routing nor selects either
  opposed claim. Wrapper failure leaves both staged arms unpublished and
  canonical, simulation, and Lens fingerprints protected.
- A v0.37 coverage receipt embeds the complete v0.36 receipt and Lens
  observation and moves only `active_family_local_lens` from missing to
  grounded. The existing `.vob` Lens sidecar is sufficient to reconstruct the
  identical controlled context, route projections, and coverage on exact
  replay. Dimensional separation, source independence, predictive
  discrimination, genuinely independent held-out replication, external
  outcome, truth, readiness, resolution, promotion, and canonical commit
  authority remain explicitly false.
- A separately invoked v0.38 trial controller preregisters exactly one
  calibration context and one held-out context before either matched pair is
  published. The contexts must name different canonical checkpoints,
  obligation/history/contradiction records, evidence receipts, source-event
  keys, protected claims, and protected evidence. They must simultaneously
  carry byte-identical Lens definition, binding, evidence, and governance
  histories and the same probe versions, Attention budget, bounded outcome
  alternatives, route count, and typed Lens operator.
- Calibration and held-out probes execute against different kernels and
  different simulation ledgers. Both ordinary v0.37 pairs are staged first;
  only after their complete nested evidence validates does the controller
  publish either simulation ledger. A failure in the second context therefore
  leaves both original ledgers unchanged, as well as both canonical kernels
  and the shared Lens sidecar.
- The completed v0.38 receipt compares an ID-independent structural-effect
  signature derived from the actual matched traces, source-partition and
  functional dispositions, route shapes, and read-only Lens projections. It
  records either replicated internal structure or a valid divergent null. Even
  agreement remains explicitly deterministic and simulation-local: the
  Resolution requirement named `independent_held_out_replication` stays
  missing because no dimension-specific prediction or observed outcome was
  preregistered.
- A new `.vct` sidecar stores either the preregistered pair alone or that pair
  plus its completed receipt as deterministic canonical JSON. Atomic replace
  and directory sync keep this experimental evidence separate from VDK and
  VOB formats. Loading revalidates both canonical checkpoints, both simulation
  fingerprints, every reservation/settlement trace, and the complete frozen
  Lens state before returning the sidecar. Serialization grants no canonical
  or epistemic authority.
- A v0.39 declaration fixes the exact `SELECT_ACTIVATED_REFS` output dimension,
  its three ID-independent cardinality profiles, the three existing bounded
  functional dispositions, and an explicit valid-null branch before either
  split executes. The concrete criterion is then derived through an API that
  accepts only the completed calibration observation: it closes the actual
  baseline/treatment traces, two Lens projections, their cardinalities, and
  the calibration functional disposition without accepting a held-out
  observation or simulation ledger.
- The v0.39 runner constructs that immutable content-addressed criterion after
  the calibration pair settles and before invoking the held-out pair. It then
  applies the criterion unchanged. The held-out result is one of a trace-local
  outcome match, an explicit valid null when the Lens-output cardinality lies
  outside the calibrated profile, or a trace-local mismatch. A failure after
  criterion derivation still publishes neither staged simulation ledger.
- A separately durable `.vdc` completed-evidence sidecar re-closes the v0.38
  pair and replication receipt, v0.39 declaration, criterion, evaluation,
  both canonical checkpoints, both simulation ledgers, every nested trace,
  and the frozen Lens lineage. This sidecar is saved only after the atomic run;
  v0.39 does not yet provide a process-restart handoff between calibration and
  held-out execution.
- An explicitly invoked v0.40 two-phase runner executes only the calibration
  split from a pristine simulation ledger, derives the same v0.39 criterion,
  and commits a canonical `.vcs` stage sidecar before its resume API will
  accept any held-out runtime. The sidecar embeds the complete calibration
  simulation ledger, observation, criterion, both preregistered contexts,
  unchanged matched-control signature, and exact frozen Lens lineage.
- `.vcs` publication uses a path-local POSIX `flock`, removes only stale
  same-path temporaries while holding that lock, fsyncs the completed file,
  atomically replaces the target, and syncs its directory. The first complete
  stage committed to a path wins; an identical write is idempotent and a
  foreign stage cannot replace it. A killed post-replace process can therefore
  be resumed from the durable evidence even though its private in-memory
  calibration runtime disappeared.
- The v0.40 resume path reloads and revalidates the stage against both
  canonical checkpoints and the Lens sidecar, reconstructs every calibration
  reservation/settlement trace, requires an exactly pristine held-out ledger,
  and only then runs the held-out split and applies the frozen criterion.
  Failed resume leaves the held-out ledger unchanged. The stage carries no
  held-out observation and cannot be built from one.
- The selected cardinality and the bounded functional disposition are both
  derived from the same internal simulated route evidence. Their held-out
  agreement is therefore only a trace-local criterion match. Resolution-level
  dimensional separation, predictive discrimination, independent held-out
  replication, source independence, and external outcome all remain missing.
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
- A deterministic `FailedPolicyDetector` now groups native Council decisions by
  stable `(operation, action_class, proposal_kind)` scope and admits a candidate
  only after at least two canonical `DENY` decisions explicitly block the same
  operation. One safety denial remains a negative control and creates nothing.
- Each admitted scope creates an immutable `FailedPolicyObligationKernel` that
  preserves its initial denied decisions, Council reports, proposals, evidence,
  and source lineage. Additional denials retrigger the same anchor; detector
  policy revisions do not fragment its identity.
- Inspection is fingerprint-pure, unchanged scans replay at zero canonical
  cost, independent governance scopes remain separate, checkpoint/View replay
  is exact, and loss of a foundational denial fails closed. Ordinary bounded
  Attention may fund a probe but cannot change the policy or any denial.
- A separately serialized `ParadigmChallengeLane` now admits a challenged
  assumption only when canonical anomaly events expose that same versioned
  assumption across at least two obligation families and two independent
  provenance roots. Created/open obligations alone cannot trigger the lane.
- Every admitted challenge is immutable, replay-safe, bound to the exact
  canonical checkpoint fingerprint, and constitutionally shadow-only. Its
  trials must replay the complete append-only history of every signaled
  obligation through verified discarded counterfactual settlements.
- Shadow evaluation requires independent simulation seeds, replicated outcome
  signatures, preserved evidence, and unchanged orthogonal fingerprints for
  every signaled obligation. Unstable or suppressive variants are rejected.
- A large declared blast radius remains visible evidence and never becomes an
  automatic veto. Even a `shadow_supported` decision has no promotion or
  canonical-mutation authority; it records bounded evidence for later human or
  separately governed work only.
- A bounded `.viqh` sidecar now retains up to 128 complete `.viq` receipts in a
  canonical, hash-chained history. Each append validates the candidate against
  its exact canonical/simulation/Lens state before entering a process-shared
  POSIX `flock`, rereads the current head under that lock, removes only stale
  same-history temporaries, and atomically replaces the complete history after
  file sync. Duplicate receipt digests are idempotent rather than duplicated.
- Every history entry records its contiguous sequence, predecessor digest, and
  canonical receipt digest. Intrinsic loading checks the complete chain and
  every embedded receipt checksum; full loading of one selected entry then
  rechecks that receipt against its exact paired sidecars. Readers require no
  lock and see only complete old or new prefixes across replacement.

## Explicit exclusions

- The v0.2 detector is endogenous only relative to canonical dependency edges:
  it derives obligation inputs from graph topology, but its visible, versioned
  policy still declares which relation types mean dependency and which evidence
  kinds count as available input. Verdant has not yet earned or revised that
  operator grammar.
- The detector heartbeat remains explicitly invoked. v0.22 adds an opt-in
  coordinator, not an autonomous Attention scheduler, background loop, or
  independent goal source.
- The coordinator supports only a closed invocation whose current detector
  candidates are exactly all eligible obligations and all are
  `DependencyGap`. Mixed-family or unrelated eligible obligations fail the
  staged transaction without publishing partial canonical or simulation
  writes. Cross-family orchestration remains unimplemented.
- Attention metrics, trial count, budget, and representative-arm ordering are
  visible supplied policy values. Verdant has not learned their calibration or
  chosen the integration request endogenously.
- Integrated trace objects are still not canonical VDK records or members of
  the existing `.vob` formats. v0.31 adds an explicitly saved, separately
  paired `.viq` receipt for exactly one complete controlled v0.30 invocation;
  v0.32 can explicitly append those immutable receipts to a separate `.viqh`
  history. Neither format is saved automatically, migrated across schema
  versions, or independently recoverable without each entry's exact paired
  `.vob` canonical/simulation/Lens state. Representative plan bodies,
  detector-candidate bodies, and hypothesis bodies are not duplicated into
  either receipt format, so they preserve the integrated evidence object and
  its durable ledger links rather than promising code-independent semantic re-
  execution.
- Coordinator atomicity is bounded to staged in-process validation before its
  two supplied Python objects are published. It adds no cross-thread or cross-
  process lock, transaction journal, or automatic archive write; callers must
  serialize invocation and explicitly save the resulting `.vob` and `.viq`
  when durable receipt recovery is required.
- The runtime consumes separately accounted simulation budget, but the
  coordinator does not move a `MayWake` obligation into `Recheck_Pending`,
  append an `AttemptRecord`, classify an arm as actually observed, or alter
  obligation status from the simulation result.
- The v0.28 control request is an explicit caller-supplied experiment input,
  not an endogenous trial-design decision. The default Attention policy grants
  its bounded `0.05` micro-probe rather than the request's `0.07` maximum, so
  one obligation runs four controlled arms and one preregistered representative
  rather than all three representatives. This is complete execution of the
  granted allocation, not evidence that the scheduler learned the budget.
- The matched observer supports only a zero-applied-patch baseline against the
  full declared patch sequence under one canonical checkpoint and one
  Attention allocation. The v0.28 integrated path records distinct declared
  seeds but the deterministic overlay runtime does not consume randomness; its
  `horizon` controls only the overlay relation-hop bound, not elapsed or
  environmental time. It does not model partial interventions, external
  environments, physical outcomes, or concurrent world changes.
- A derived `additive_overlay_effect` means only that the treatment materialized
  additional JSON records relative to its matched baseline. A
  `canonical_record_mutation` means the simulated overlay removed or changed a
  pre-existing record. Neither result establishes causal sufficiency, semantic
  correctness, predictive improvement, real-world success, or truth.
- v0.29 observes whether evidence reached by the supplied, versioned overlay-
  local walk is admitted by Verdant's native workspace pipeline on an isolated
  clone. This is not canonical Workbench retrieval or admission, an outgoing
  action, execution of the canonical dependency path, or an actually occurring
  preregistered `OutcomeKind`. The overlay path is not accepted as a
  `DependencyPathObservation`; neither the controlled nor workspace receipt
  can construct a `ResolutionTrialObservation` or feed the Resolution
  Contract, Diagnostic, Council, or Paradigm ledgers.
- The probe's start node, traversable relation grammar, evidence kinds, and hop
  limit remain supplied experimental policy. The mapping of retrieved evidence
  into workspace candidates, relevance signal, resource fraction, and one-
  cycle persistence are also fixed v0.29 policy rather than learned values.
  The native workspace cycle enforces the declared slot cap only on a shadow
  clone and cannot choose or emit an action. v0.29 verifies that the named Lens
  binding is active but does not use that Lens to change trial behavior.
  Distinct declared seeds demonstrate exact deterministic replay rather than
  stochastic or external held-out generalization.
- v0.30 observes only whether a supplied reversible investigation is approved
  by the existing native Council and whether that exact authorized operation
  is admitted by the native workspace on the reconstructed shadow clone. A
  Council authorization and an `AUTHORIZED_ACTION` workspace item are not an
  external action, motor command, environment transition, canonical governance
  decision, or observed outcome. The clone is discarded after each arm.
- The operation namespace, action class, description, requested Council
  resource, priority metrics, harm and reversibility declarations, workspace
  resource fraction, signals, and one-cycle persistence are visible supplied
  v0.30 policy. Verdant neither learned these values nor chose to initiate the
  request. An arm without admitted evidence cannot fabricate a proposal; an
  evidence-bearing proposal cannot cite evidence outside that arm's admission.
- Exact action-effect agreement across the two declared seeds establishes
  deterministic replay only. The runtime still does not consume randomness,
  the horizon is a graph-hop bound rather than elapsed experience, and the
  matched treatment does not establish causal sufficiency or external
  generalization. No governance outcome or action-success label is recorded.
- The `.viq` writer remains an opt-in, unlocked single-receipt replacement API;
  callers requiring accumulation must explicitly use `.viqh`. The v0.32
  history arbitrates only cooperating local POSIX processes opening the same
  persistent lock path. It does not cover Windows/NTFS, network filesystems,
  lock-hostile storage, hostile symlink/path replacement, kernel crash, power
  loss, controller caches, or hardware failure. Its total canonical file is
  capped at 128 MiB and 128 unique receipts; reaching either bound fails rather
  than pruning evidence.
- `.viqh` lock acquisition order is the recorded append order, not a claim
  about causal or wall-clock order. There is no distributed merge, external
  monotonic counter, signature, trusted timestamp, or remote notarization. The
  hash chain detects ordinary alteration, reordering, and unrehashed suffix
  removal, but an adversary able to rewrite the whole history can substitute a
  rehashed prefix. The lock does not make `.vob` plus `.viqh` a cross-file
  transaction and does not serialize coordinator execution. Each selected
  historical entry must still be paired and fully validated separately before
  its trace is used as experimental evidence.
- Expected gain, uncertainty, urgency, novelty, and cost arrive through typed,
  provenance-visible bids, but v0.28 does not claim Verdant has learned their
  calibration. The scheduler's ordering policy remains falsifiable machinery.
- Cut partitions and initial reopen predicates are still supplied through the
  typed stall API. Automatic cut derivation is not a v0.2 claim.
- No scheduler loop or background clock yet; probes, audit pings, and graph
  deltas are explicitly submitted through the experimental pipeline.
- The Resolution Contract accepts explicitly supplied, typed trial
  observations. v0.29 derives retrieved and shadow-admitted sets and v0.30
  derives a shadow Council/workspace action signature, but the Resolution-
  evidence coverage receipt does not consume either as an actually executed
  action. No environment-facing action or executed dependency path is derived
  automatically.
- No canonical `Resolved` API or earned-structure promotion exists. A passing
  verdict supplies bounded evidence for a later governor but grants no
  resolution authority itself.
- Simulation consumption is declared by the typed plan and bounded by its
  reservation; v0.4 does not yet meter physical CPU, memory, or wall-clock use.
- The simulation ledger is packaged only by explicit `.vob` save/load calls;
  ordinary `.vdk` checkpoints and runtime scheduling do not automatically
  include it. Process-kill and competing-writer tests cover only local POSIX
  fork/filesystem behavior at controlled userspace boundaries. They do not
  establish Windows/NTFS, network-filesystem, kernel-crash, power-loss,
  controller-cache, or hardware-failure durability. Writers have no lock,
  ordering, arbitration, or merge protocol: the last successful replace wins.
  A pre-replace kill can leave a fully written hidden temporary file, and no
  automatic stale-temp cleanup is attempted because it could delete a live
  concurrent writer's file. Archive hashes detect accidental or non-rehashed
  alteration; they are not signatures or an authenticity boundary against an
  adversary able to rewrite every member and the manifest.
- The overlay supports a deliberately bounded set of canonical mapping
  collections and JSON hypothesis values. It does not validate those values as
  promotable canonical records and exposes no commit path.
- The v0.5 generator is limited to DependencyGap evidence-path projection. Its
  evidence kinds, traversable relation statuses, path-depth bound, and candidate
  cap remain explicit policy machinery; Verdant has not learned that grammar.
- The prospective arms are preregistered structural possibilities, not observed
  world results. v0.23 derives only a matched structural overlay delta; no
  outcome evaluator selects which functional arm occurred, and no canonical
  `AttemptRecord` or obligation status transition is appended.
- Lens operators are typed, deterministic, provenance-visible selectors, but
  Verdant does not yet synthesize or revise them. Approval and evidence-result
  classification are explicit experimental inputs rather than an implemented
  Council.
- Binding calibration is deliberately narrow: v0.6 uses a declared cumulative
  failure count. It does not yet learn contextual activation envelopes, compare
  failure rates against matched controls, or automatically consume diagnostic
  interaction attributions.
- `Contradiction` now has detection, immutable identity, retrigger continuity,
  checkpoint replay, anti-suppression validation, a v0.33 provenance-partition
  hypothesis/evidence protocol, a v0.34 matched isolated projection probe, a
  v0.35 one-for-one resolution-evidence receipt, a v0.36 context-conditioned
  functional probe, a v0.37 opt-in active-Lens control, v0.38 separately
  preregistered calibration/held-out contexts with disjoint canonical evidence
  and identical Lens lineage, and a v0.39 calibration-frozen internal
  dimension/outcome criterion. v0.40 durably separates that calibration stage
  from held-out execution and permits exact process-restart resume. It does
  not yet derive an outcome through a
  channel independent of the Lens-projected route evidence, establish
  Resolution-level dimensional separation or predictive discrimination, learn
  a Lens, feed a Resolution Contract, or carry canonical resolution authority.
- Shared or different evidence IDs and source roots are structural ledger
  observations only. They do not establish source independence, causal
  relevance, contextual compatibility, semantic correctness, or which opposed
  claim is true. v0.34 materializes the already derived source-root partition
  in an isolated overlay; its `distinct`, `valid_null`, and `inconclusive`
  dispositions do not measure predictive discrimination, behavior, external
  outcome, or dimensional separation. v0.35 makes each of those absences
  explicit and immutable; v0.36 adds only an internal context-conditioned
  route effect, and v0.37 adds only an active supplied Lens applied read-only
  to that same context. v0.38 applies the unchanged Lens to a second canonical
  evidence context and can observe ID-independent structural agreement, but
  typed source-root labels may be shared across the contexts and disjoint
  record IDs do not prove that real-world sources are independent. v0.39
  freezes a calibration-derived cardinality/outcome criterion before the
  held-out run, but its cardinality and outcome still share the same simulated
  routing substrate; it is not an independent prediction. The null and defer
  hypotheses remain mandatory alternatives, not conclusions selected by the
  probe.
- Contradiction hypothesis generation remains explicitly invoked and its
  Attention metrics and `0.05` minimum budget are visible supplied policy. The
  bundle, probe, observations, controlled Lens context, and coverage receipts
  remain non-authoritative and are not canonical VDK records or new `.vob`,
  `.viq`, or `.viqh` members. Generic reservations/settlements and the
  preexisting Lens registry/ledger remain durable through explicit `.vob`
  save/load; v0.38 adds an explicitly saved `.vct` preregistration/receipt
  sidecar, v0.39 adds a completed `.vdc` criterion/evaluation sidecar, and
  v0.40 adds a calibration-stage `.vcs` sidecar paired back to both contexts.
  None is automatically scheduled, appended, merged, or loaded by VDK/VOB
  APIs. The `.vcs` stage is self-contained for calibration-ledger replay but
  deliberately accepts only pristine calibration and held-out simulation
  ledgers; it is not a migration or merge protocol. Lens
  definition, approval, calibration references, and evidence result remain
  supplied governance inputs. No learned context or Lens, autonomous
  family-local scheduler, truth test, Resolution-level independent held-out
  replication, predictive discrimination, source-independence proof,
  dimensional separation, or Resolution Contract is added.
- `.vcs` writer arbitration covers cooperating local POSIX processes opening
  one stable path. It does not cover Windows/NTFS, network or lock-hostile
  filesystems, hostile symlink/path replacement, kernel crash, power loss,
  controller caches, hardware failure, distributed merge, signatures, trusted
  timestamps, or remote notarization. Its lock does not create a transaction
  with `.vob`, `.vct`, or `.vdc`; the stage is immutable first-committer-wins
  evidence rather than an execution authority or canonical journal.
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
- `FailedPolicy` is intentionally a conservative name for a repeated-block
  obligation family, not a verdict that the Council or its safety policy is
  defective. Repetition establishes a persistent structural question only.
- The threshold of two denied decisions and the grouping scope are explicit,
  versioned experimental policy. They are not learned or self-revised.
- `DEFER`, constraints, one-off denials, and approved operations do not trigger
  this detector. No controlled policy substitution, matched policy fork,
  safety-property proof, rollback, or canonical policy mutation is implemented.
- `T_g` and thermodynamic observations are not inputs to this detector and do
  not control its behavior.
- Five family enum values now exist, but borrow-before-synthesize, held-out
  cross-family lens adoption, representational merging, and independent
  per-family rollback of a shared lens remain proposed rather than implemented.
- Lens durability remains explicitly sidecar-local: only v2 `.vob` calls that
  supply a Lens system include it. Ordinary `.vdk`, legacy v1 `.vob`, and the
  backward-compatible two-value loader do not expose recovered Lens state;
  callers must use the bundle loader. Lens governance is not committed into
  the canonical graph and receives no canonical authority from serialization.
- Free-form provenance, calibration, hypothesis, outcome, and independent-
  consequence refs remain externally namespaced strings. v0.16 closes typed
  IDs whose namespace it recognizes, but cannot prove the referent or semantic
  meaning of arbitrary strings. Resolution observations and partitions are not
  serialized by this archive.
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
- The diagnostic ledger remains a sidecar rather than canonical VDK state. It
  is durable only when a caller explicitly supplies it for a v3 `.vob`; v1,
  v2, ordinary VDK, and the backward-compatible two-value archive loader do not
  expose it or grant it authority.
- `DiagnosticProbeObservation` objects are still transient inputs rather than
  ledger members. v3 preserves terminal probe IDs and proves that enough
  isolated, parent-local simulation settlements and budget exist, but it cannot
  reconstruct each probe's finding, basis refs, or exact settlement mapping.
  Custom numeric `DiagnosticPolicy` limits are likewise not serialized beyond
  the policy version carried by durable records.
- Council durability remains explicitly opt-in sidecar state: v1-v3 `.vob`,
  ordinary `.vdk`, and the backward-compatible two-value archive loader do not
  expose the recovered tournament. The bundle loader is required, and archive
  recovery grants no intervention or canonical-write authority.
- `CouncilInterventionCandidate` and `EpistemicPreservationObservation`
  objects remain transient in v4, which therefore still fails closed on non-
  default Council policy parameters. An explicitly supplied v5 evidence ledger
  preserves them and permits full decision recomputation, but it does not make
  the observations native: repair-restored flags, blast-radius lists, wave-
  state, `c_memory`, observer-only `T_g`, and orthogonal fingerprints are still
  typed experimental inputs supplied by the harness.
- Paradigm durability remains explicit and sidecar-local. Only a cumulative v6
  `.vob` call that supplies both the lane and its complete trial-evidence ledger
  includes it; ordinary `.vdk`, v1-v5 `.vob`, and the backward-compatible two-
  value loader do not expose it. Archive tests exercise Paradigm signals across
  `DependencyGap` and `FailedPolicy`; they do not yet cover every family
  combination or make the lane a canonical scheduler.
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
  component. Applying interventions and validating post-application recovery
  remain unimplemented.
- The paired-checkpoint isolation result covers declared in-process kernel
  state and tested future behavior. The runtime currently performs no external
  I/O; it does not claim a general operating-system side-effect sandbox.
- No thermodynamic control authority. `T_g` remains observer-only.
- Native contradiction recognition still depends on the existing claim
  subsystem's explicit subject/predicate/object/polarity representation. The
  new detector does not establish semantic understanding, discover novel
  predicates, decide which claim is true, or operationalize consciousness.
- Paradigm anomaly signals currently require explicit canonical obligation
  history events whose visible `policy_version` equals the challenged
  assumption reference. Verdant does not yet discover latent shared assumptions
  across differently named policies or ontologies.
- Shadow-trial outcome signatures, improvement flags, evidence-preservation
  observations, and orthogonal fingerprints remain typed experimental inputs.
  v6 now preserves and exactly replays them, but persistence does not make the
  observations native or derive them automatically from simulated geometry.
- `shadow_supported` is not ontology replacement. No variant promotion,
  canonical replay commit, mass reopening, policy rewrite, or autonomous
  paradigm shift exists in v0.14.
- The Paradigm lane does not establish semantic understanding, consciousness,
  a mind, or complete endogenous agency.

## v0.15 claim boundary

- **OBSERVED:** Five focused paired-archive tests and the 351-test full suite
  pass. The archive test restores both `DependencyGap` and `Contradiction`
  Views, verifies a subsequent canonical transition is identical after reload,
  and loads all 17 preexisting VDK checkpoints.
- **IMPLEMENTED-EXPERIMENTAL:** Explicit `.vob` save/load pairs canonical VDK
  bytes with a separate simulation ledger, validates their internal and cross-
  ledger references, and atomically replaces the pair as a single file.
- **PROPOSED:** Durable pairing of lens, diagnostic, Council, and Paradigm
  sidecars; real process-kill and concurrent-writer proofs; an opt-in integrated
  detector-to-simulation path; and observations derived from experiment traces.
  None is established by the paired archive.

## v0.16 claim boundary

- **OBSERVED:** Nine focused archive tests and the full repository suite pass.
  A v2 round trip restores two family-local active bindings and supporting Lens
  evidence without changing canonical or simulation fingerprints. Rehashed
  registry/ledger substitution, an unresolved typed settlement ref, and future-
  dated Lens governance all fail closed; all 17 preexisting VDK checkpoints
  embed and reload through both legacy v1 and empty-Lens v2 archives.
- **IMPLEMENTED-EXPERIMENTAL:** Explicit v2 `.vob` save/load durably pairs the
  Lens registry and ledger with canonical and simulation state, validates
  deterministic replay plus typed cross-sidecar closure, and exposes recovered
  Lens state through `load_experiment_archive_bundle`.
- **PROPOSED:** Diagnostic, Council, and Paradigm sidecar pairing; full closure
  for free-form provenance and hypothesis/outcome refs; real process-kill and
  concurrent-writer proofs; and automatic scheduler use of recovered lenses.
  No canonical resolution, promotion, or policy-rewrite authority is added.

## v0.17 claim boundary

- **OBSERVED:** Thirteen focused archive tests and the 359-test full repository
  suite pass. A v3 round trip restores a terminal, probe-backed Diagnostic result
  across canonical, simulation, Lens, and Diagnostic ledgers with unchanged
  fingerprints. Rehashed foreign Diagnostic substitution, causal-attribution
  forgery, and removal of the cited probe settlement fail closed. All 17
  preexisting VDK checkpoints embed and reload through v1, v2, and empty-
  Diagnostic v3 envelopes.
- **IMPLEMENTED-EXPERIMENTAL:** Explicit v3 `.vob` save/load durably pairs the
  Diagnostic ledger after its canonical, simulation, and Lens prerequisites,
  validates the durable cross-ledger causal closure available in the current
  schema, and exposes the reconstructed non-authoritative engine through the
  bundle loader.
- **PROPOSED:** Durable Diagnostic probe observations and policy parameters;
  Council and Paradigm sidecar pairing; real process-kill and concurrent-writer
  proofs; and an opt-in integrated detector-to-simulation path. No canonical
  diagnosis, resolution, component penalty, promotion, or policy rewrite is
  established.

## v0.18 claim boundary

- **OBSERVED:** Seventeen focused archive tests and the 363-test full repository
  suite pass. A deterministic v4 round trip restores a non-executing Council
  recommendation across canonical, simulation, Lens, Diagnostic, policy, and
  Council-ledger state with unchanged fingerprints and exact request replay.
  Rehashed foreign Council substitution and removal of a cited candidate's
  isolated settlement fail closed; a rehashed non-default policy is also
  rejected because its original request cannot yet be recomputed. All 17
  preexisting VDK checkpoints embed and reload through v1, v2, v3, and empty-
  Council v4 envelopes.
- **IMPLEMENTED-EXPERIMENTAL:** Explicit v4 `.vob` save/load durably pairs the
  Council policy and decision ledger after their Diagnostic prerequisites,
  validates the durable diagnostic-to-candidate-simulation closure represented
  by the current schema, and exposes a reconstructed recommendation-only
  tournament through the bundle loader.
- **PROPOSED:** Durable candidate and preservation-observation records that
  permit full decision recomputation; Paradigm sidecar pairing; real process-
  kill and concurrent-writer proofs; and an opt-in integrated detector-to-
  simulation path. No canonical diagnosis, intervention, resolution,
  component penalty, promotion, or policy rewrite is established.

## v0.19 claim boundary

- **OBSERVED:** Twenty focused archive tests and the 366-test full repository
  suite pass. A deterministic v5 round trip restores a Council tournament with
  non-default candidate bounds, then reproduces its request hash, assessments,
  frontier, and recommendation from the durable candidate and preservation
  records. Incomplete evidence coverage and a rehashed one-unit preservation-
  metric change fail closed. All 17 preexisting VDK checkpoints embed and
  reload through v1-v5 envelopes, including an empty-evidence v5 envelope.
- **IMPLEMENTED-EXPERIMENTAL:** A content-addressed Council evidence ledger and
  explicit v5 `.vob` format preserve every request input represented by the
  existing tournament schema. Archive loading reruns the non-executing Council
  algorithm from an empty decision ledger and requires exact equality with the
  paired durable decisions before exposing the bundle.
- **PROPOSED:** Paradigm Challenge sidecar pairing; deriving preservation and
  orthogonal observations from actual experiment traces and matched controls;
  real process-kill and concurrent-writer proofs; and an opt-in integrated
  detector-to-simulation path. No canonical diagnosis, intervention,
  resolution, component penalty, promotion, or policy rewrite is established.

## v0.20 claim boundary

- **OBSERVED:** Thirty-three focused Paradigm/archive tests and the 370-test
  full repository suite pass. A deterministic v6 round trip restores a custom
  Paradigm policy, two-family challenge, four shadow trials, and supported
  decision without changing canonical or simulation fingerprints. Rehashed
  anomaly-evidence substitution, changed trial identity/outcome, and removal of
  a cited simulation settlement fail closed. All 17 preexisting VDK
  checkpoints embed and reload through v1-v6 envelopes, including an empty-
  Paradigm v6 envelope.
- **IMPLEMENTED-EXPERIMENTAL:** A content-addressed Paradigm trial-evidence
  ledger and cumulative v6 `.vob` format preserve every decision input
  represented by the existing shadow-lane schema. Loading rebuilds the lane
  from an empty ledger and requires exact admission and decision replay against
  the recovered canonical history and isolated simulation ledger before
  exposing it through the bundle loader.
- **PROPOSED:** Process-kill and concurrent-writer durability proofs; deriving
  shadow outcomes, evidence-preservation checks, and orthogonal observations
  from actual experiment traces and matched controls; and an explicitly
  invoked detector-to-simulation integration path. v6 adds no scheduler,
  canonical resolution, variant promotion, policy rewrite, or semantic claim.

## v0.21 claim boundary

- **OBSERVED:** Twenty-six focused archive/durability tests and the 372-test
  full repository suite pass. Controlled POSIX child termination before
  replacement leaves the prior archive byte-identical and readable;
  termination after replacement exposes the complete new archive. Six
  coordinated process writers with a live reader expose only complete known
  archives. The existing archive suite still embeds and reloads all 17 legacy
  VDK checkpoints through v1-v6.
- **IMPLEMENTED-EXPERIMENTAL:** The existing unique-temporary-file, file-fsync,
  atomic-replace, and POSIX-directory-fsync write path now has direct process-
  boundary and concurrent-writer falsification coverage. No archive format or
  cognitive authority changed.
- **PROPOSED:** An explicitly invoked detector-to-Attention-to-hypothesis-to-
  isolated-simulation integration path with complete provenance and zero
  canonical leakage. Windows and power-loss durability and writer arbitration
  remain excluded. No canonical resolution, promotion, policy rewrite, or
  semantic claim is established.

## v0.22 claim boundary

- **OBSERVED:** Thirty focused detector/Attention/hypothesis/runtime/integration
  tests and the 377-test full repository suite pass. One explicit invocation
  detects a native topology gap, composes mandatory alternative hypotheses,
  records a complete Attention decision, and executes three functionally
  distinct isolated arms. Reloading its existing `.vob` state reconstructs the
  exact same integration trace with no additional canonical or simulation
  cost. An unrelated eligible obligation, a simulated canonical leak, and a
  rehashed trace with dropped provenance all fail without partial publication.
- **IMPLEMENTED-EXPERIMENTAL:** A transactional, explicitly invoked
  `DependencyGap` integration path with content-addressed provenance now joins
  the previously separate components. Detector and Attention writes remain
  canonical; hypotheses, partitions, plans, traces, and settlements retain
  their existing non-authoritative or separately ledgered boundaries.
- **PROPOSED:** Derive arm results and preservation observations from actual
  experiment traces under matched controls, then add family-local hypothesis
  and resolution-evidence protocols after their prerequisites exist. v0.22
  adds no autonomous scheduler, observed-outcome evaluator, `Resolved` path,
  structure promotion, policy rewrite, thermodynamic control, or semantic
  claim.

## v0.23 claim boundary

- **OBSERVED:** Twenty-four focused counterfactual, hypothesis, integrated-
  inquiry, and matched-trace tests and the 383-test full repository suite pass.
  A zero-patch baseline and full-patch treatment derived from the same
  `DependencyGap` hypothesis produce an additive relation delta without any
  supplied `OutcomeKind`. Exact archive reload replay adds no simulation cost.
  Different consumed budgets fail matching, a substituted in-memory trace is
  rejected by reconstruction from the actual ledger, deletion of an existing
  relation is classified as non-preserving, and an exact-value upsert is a
  valid structural null. The full suite still embeds and reloads all 17 legacy
  VDK checkpoints.
- **IMPLEMENTED-EXPERIMENTAL:** Every counterfactual run now returns a
  deterministic structural trace covering all authorized overlay collections.
  The opt-in matched observer accepts only a verified zero/full intervention
  pair with identical causal controls, then derives record additions, removals,
  changes, and canonical-record preservation from materialized overlay state.
  Its receipt is simulated-only and carries no observed-outcome, resolution,
  promotion, or commit authority.
- **PROPOSED:** Connect matched structural receipts to the v0.22 coordinator
  without weakening its transaction boundary, then derive the additional
  retrieved/admitted/action/path observations required by the existing
  Resolution Contract using held-out matched controls. Family-local protocols
  for other obligation families remain downstream. v0.23 does not establish an
  actually occurring functional outcome, causal sufficiency, semantic truth,
  autonomous inquiry, `T_g` control, or thermodynamic behavior.

## v0.24 claim boundary

- **OBSERVED:** Twenty-nine focused counterfactual, hypothesis, integrated-
  inquiry, and matched-trace tests and the 388-test full repository suite pass.
  A single explicit inquiry now executes three distinct preregistered arms and
  one real zero/full matched pair under the same bounded Attention allocation.
  The pair derives an additive structural receipt without an `OutcomeKind` and
  leaves all pre-existing canonical records unchanged. Archive reload exactly
  replays both pair settlements and reconstructs the same receipt without
  additional canonical or simulation cost. An underfunded grant, a rehashed
  receipt, a foreign matched-plan patch, a gap with no patch-bearing evidence
  path, and a trace with its matched receipt removed all fail without partial
  publication.
- **IMPLEMENTED-EXPERIMENTAL:** The explicitly invoked `DependencyGap`
  coordinator now makes matched structural observation part of its atomic
  detector-to-simulation transaction. Its visible policy requests budget for
  two control arms in addition to the bounded labeled-arm set, publishes
  exactly one verified receipt per Attention allocation, and rejects any
  treatment that removes or changes a pre-existing canonical record. The
  receipt is content-addressed, simulated-only, and non-authoritative.
- **PROPOSED:** Derive retrieved and admitted canonical references, an outgoing
  action, and dependency-path completion evidence from actual held-out traces
  so the existing Resolution Contract can consume trace-grounded typed
  observations. That later step must preserve matched controls and must not
  turn a structural delta into causal, semantic, resolution, or promotion
  authority. Family-local protocols for the other obligation families remain
  downstream. v0.24 adds no autonomous scheduler, real-world observation,
  canonical `Resolved` transition, policy rewrite, `T_g` control, or
  thermodynamic behavior.

## v0.25 claim boundary

- **OBSERVED:** Forty focused counterfactual, hypothesis, integrated-
  inquiry, matched-trace, and Resolution-Contract tests and the 391-test full
  repository suite pass. An explicit inquiry reconstructs one exact Resolution-
  evidence coverage receipt from its real zero/full matched traces and paired
  simulation ledger. Archive reload replay reproduces the receipt without new
  canonical or simulation cost. Dropped coverage, foreign-ledger substitution,
  hidden missing requirements, and forged readiness all fail closed. The full
  suite still embeds and reloads all 17 legacy VDK checkpoints.
- **IMPLEMENTED-EXPERIMENTAL:** A content-addressed coverage gate now separates
  fields grounded by the actual matched structural trace from fields that still
  require an operational probe. It binds cue, context, checkpoint, settlements,
  protected evidence, candidate lineage, structural delta, and preservation to
  the integrated trace while hard-coding simulated-only, non-authoritative,
  non-committing status.
- **PROPOSED:** Add a versioned overlay-aware operational probe that records
  retrieval, workspace admission, outgoing action, and executed dependency
  path under replicated held-out matched controls, together with explicit seed,
  horizon, Lens binding, and slot budget. Only complete trace-grounded coverage
  may construct a non-authoritative `ResolutionTrialObservation`. Family-local
  protocols for the other obligation families remain downstream. v0.25 does
  not establish an observed functional outcome, causal sufficiency, resolution,
  promotion, autonomous inquiry, semantic understanding, `T_g` control, or
  thermodynamic behavior.

## v0.26 claim boundary

- **OBSERVED:** Forty-eight focused counterfactual, hypothesis, integrated-
  inquiry, matched-trace, operational-probe, and Resolution-Contract tests and
  the 399-test full repository suite pass. A real zero/full matched pair
  reconstructs its overlays from the settled simulation ledger: the baseline
  reaches no evidence, while the treatment's declared bridge reaches the
  canonical target concept's actual `OUTCOME` evidence. Patch-carried forged
  evidence IDs are ignored, a cosmetic additive relation is a valid operational
  null, and foreign ledgers, noncanonical endpoints, removed probe receipts,
  changed observations, and authority forgeries fail closed. The full suite
  continues to embed and reload all 17 legacy VDK checkpoints.
- **IMPLEMENTED-EXPERIMENTAL:** A deterministic, versioned overlay-local graph
  probe is now part of the explicitly invoked `DependencyGap` matched-control
  transaction. Its content-addressed observation distinguishes structural
  change from evidence access, is reconstructed from actual discarded arms,
  and extends the coverage receipt without weakening canonical/simulation
  isolation or anti-suppression boundaries.
- **PROPOSED:** Add explicit seeds, horizons, active Lens bindings, identical
  workspace slot budgets, and held-out matched replications; then derive native
  workspace admission and outgoing-action signatures from those executions.
  Only after a canonical dependency path is actually executed and every
  Resolution Contract field is grounded may the integration construct a non-
  authoritative `ResolutionTrialObservation`. Family-local protocols for the
  other obligation families remain downstream. v0.26 adds no autonomous
  scheduler, real-world observation, canonical resolution or promotion,
  policy rewrite, semantic understanding, `T_g` control, or thermodynamic
  behavior.

## v0.27 claim boundary

- **OBSERVED:** Fifty-seven focused counterfactual, hypothesis, integrated-
  inquiry, matched-trace, operational-probe, trial-control, and Resolution-
  Contract tests and the 408-test full repository suite pass. One calibration
  and one held-out zero/full pair commit their controls into both settled trace
  lineages before execution and reproduce the same structural and operational
  access signatures. Archive reload reconstructs the same contexts and receipt
  with no new simulation cost. Post-hoc control or hypothesis changes, missing
  context lineage, active-Lens replacement, reused seeds, mismatched horizon or
  slot controls, foreign ledgers, and authority forgeries fail closed. All 17
  legacy VDK checkpoints still load and embed successfully.
- **IMPLEMENTED-EXPERIMENTAL:** A content-addressed trial-control envelope now
  binds the canonical checkpoint and active family-local Lens state to declared
  seed, overlay-hop horizon, slot budget, and calibration/held-out split. A
  standalone observer rederives real matched structural and operational
  receipts, and a second observer accepts only exact effect reproduction across
  distinct declared seeds. Every receipt remains simulated-only,
  non-authoritative, non-committing, and reconstructable from the existing
  durable canonical, simulation, and Lens sidecars.
- **PROPOSED:** Integrate two predeclared controlled pairs into the explicitly
  invoked `DependencyGapInquiryCoordinator` with bounded Attention and
  simulation accounting. Then derive native workspace admission and outgoing-
  action signatures under those controls before attempting an actually
  executed canonical dependency path or a non-authoritative
  `ResolutionTrialObservation`. The deterministic runtime still does not
  consume the seed; the slot budget is not enforced by a native workspace; the
  horizon is a relation-hop bound rather than temporal experience; and the
  declared held-out replay is not stochastic or external generalization. v0.27
  establishes no causal sufficiency, real-world outcome, autonomous inquiry,
  resolution or promotion authority, policy rewrite, semantic understanding,
  `T_g` control, or thermodynamic behavior.

## v0.28 claim boundary

- **OBSERVED:** Sixty-eight focused counterfactual, hypothesis, integrated-
  inquiry, matched-trace, operational-probe, trial-control, and Resolution-
  Contract tests and the 419-test full repository suite pass. One opt-in
  coordinator invocation uses a single bounded Attention allocation to settle
  a calibration zero/full pair, a held-out zero/full pair, and one
  preregistered representative. Both context IDs occur in their plans,
  reservations, settlements, and execution traces before observation. Archive
  reload reproduces the exact request, allocation, contexts, controlled
  receipts, held-out receipt, and integrated trace without new canonical or
  simulation cost. Underfunding, request tampering, post-declaration Lens
  replacement, dropped controlled evidence, forged observer authority, and
  canonical leakage fail without partial publication. All 17 legacy VDK
  checkpoints remain compatible.
- **IMPLEMENTED-EXPERIMENTAL:** The predeclared two-pair control protocol is now
  part of the explicitly invoked `DependencyGapInquiryCoordinator`. Attention
  provenance contains the immutable control request and active Lens lineage;
  each allocation is checked against its exact four controlled arms and one
  held-out-replication receipt. Integrated trace validation closes every
  request/context/observation/allocation edge while the simulation ledger
  remains separate and all receipts remain non-authoritative.
- **PROPOSED:** Derive a native workspace-admission signature from actual
  controlled executions, then derive outgoing-action signatures and finally an
  actually executed canonical dependency path. Only after those operational
  prerequisites and every Resolution Contract input are trace-grounded may a
  non-authoritative `ResolutionTrialObservation` be constructed. The seed is
  still unconsumed provenance, the slot budget is not native enforcement, the
  horizon is not temporal experience, and exact deterministic held-out replay
  is not stochastic or external generalization. v0.28 adds no autonomous
  inquiry, real-world outcome, resolution or promotion authority, policy
  rewrite, semantic understanding, `T_g` control, or thermodynamic behavior.

## v0.29 claim boundary

- **OBSERVED:** Seventy-five focused counterfactual, hypothesis, integrated-
  inquiry, matched-trace, operational-probe, trial-control, and Resolution-
  Contract tests and the 426-test full repository suite pass. The controlled
  baseline submits no retrieved evidence while the treatment submits the
  canonical `OUTCOME` evidence actually reached through its materialized
  overlay; a real native workspace cycle admits it on each shadow arm. With
  two retrieved evidence records and a declared one-slot budget, the native
  report admits exactly one and suppresses one. Archive reload reconstructs
  byte-equivalent workspace observations and held-out replication without new
  simulation cost. Foreign ledgers, relaxed slot caps, missing trace receipts,
  rehashed authority, and injected observer tampering fail atomically. All 17
  legacy VDK checkpoints still load and embed successfully.
- **IMPLEMENTED-EXPERIMENTAL:** A versioned observer now bridges actual
  controlled overlay retrieval into Verdant's native workspace pipeline under
  the predeclared slot cap. It records content-addressed arm reports, matched
  effects, and held-out exact-replay evidence, and closes their complete
  lineage in the integrated trace. Each native workspace cycle runs only on a
  fresh canonical clone; the canonical workspace, semantic records, simulation
  ledger boundary, and Lens sidecar remain unchanged.
- **PROPOSED:** Derive an outgoing-action signature from Verdant's existing
  native Council-authorized action pathway under the same matched controls and
  isolated accounting. Only then attempt an actually executed canonical
  dependency path, and only after every Resolution Contract input is grounded
  construct a non-authoritative `ResolutionTrialObservation`. The workspace
  candidate mapping remains supplied policy, the seed remains unconsumed by
  the deterministic runtime, the horizon is not temporal experience, and the
  workspace cycle is shadow rather than canonical admission. v0.29 establishes
  no real-world outcome, causal sufficiency, autonomous inquiry, resolution or
  promotion authority, policy rewrite, semantic understanding, `T_g` control,
  or thermodynamic behavior.

## v0.30 claim boundary

- **OBSERVED:** Sixty-eight focused integrated-inquiry, trial-control, native-
  workspace, and native-Council tests and the 432-test full repository suite
  pass. Under both predeclared split contexts, the baseline's empty admitted-
  evidence set produces an explicit no-action record while the treatment's
  native workspace admission produces a reversible investigation proposal.
  The real three-King Council approves that proposal on the clone, and the
  native workspace admits the exact `AUTHORIZED_ACTION` candidate linked to
  the resulting decision. The same ID-independent action-effect signature
  reproduces across the distinct declared seeds. Archive reload reconstructs
  byte-equivalent action observations and held-out receipt with zero new
  reservations or settlements. Foreign ledgers, missing integrated receipts,
  rehashed authority claims, supplied-policy substitution, and injected
  observer tampering fail without partial publication. The dedicated legacy
  compatibility test loads and embeds all 17 preexisting VDK checkpoints.
- **IMPLEMENTED-EXPERIMENTAL:** The explicitly invoked
  `DependencyGapInquiryCoordinator` now carries complete native Council and
  action-workspace receipts after each v0.29 workspace observation, plus one
  held-out action replication per Attention allocation. Validation closes the
  controlled-trial, workspace, Council-decision, authorized-operation, action-
  candidate, split, and replication edges. All native Council and workspace
  mutation occurs on discarded clones; canonical semantic, governance, and
  workspace state, the isolated simulation ledger, and the Lens sidecar remain
  unchanged by action-signature derivation.
- **PROPOSED:** Derive an actually executed dependency-path observation from a
  controlled experiment trace with matched controls and preserved physical
  evidence; do not infer it from Council authorization or workspace admission.
  Only after execution, outcomes, admitted/retrieved evidence, controls, and
  held-out lineage are all grounded may the Resolution-evidence protocol be
  extended toward a non-authoritative `ResolutionTrialObservation`. Separately
  durable integrated receipts and family-local hypothesis/evidence protocols
  remain later work. v0.30 adds no external action, causal success claim,
  autonomous inquiry, canonical resolution or promotion, policy rewrite,
  semantic understanding, `T_g` control, or thermodynamic behavior.

## v0.31 claim boundary

- **OBSERVED:** Forty-four focused integrated-inquiry tests and the 437-test
  full repository suite pass. A complete controlled v0.30 trace serializes to
  deterministic `.viq` bytes, reloads against its separately restored `.vob`
  canonical/simulation/Lens state, and reproduces the identical nested receipt
  without new reservations, settlements, Council decisions, or workspace
  events. Rehashed external-action authority, removed controlled evidence,
  foreign canonical/simulation/Lens pairings, uncontrolled pre-v0.30 traces,
  and an injected atomic-replace failure all fail closed while preserving the
  prior complete file. The dedicated compatibility test still loads and embeds
  all 17 preexisting VDK checkpoints.
- **IMPLEMENTED-EXPERIMENTAL:** The complete integrated inquiry receipt is now
  independently durable under a versioned canonical-JSON envelope. Save and
  load close its canonical Attention/obligation, isolated-simulation,
  canonical-evidence, active-Lens, controlled-trial, native-workspace, and
  shadow-Council/action lineage against exact paired sidecars. The API remains
  explicitly invoked, single-receipt, non-authoritative, and outside canonical
  VDK state and existing `.vob` schemas.
- **PROPOSED:** Do not synthesize execution from the durable authorization
  receipt. An actually executed dependency-path observation still requires an
  external or hardware-backed command boundary, native result telemetry,
  synchronized physical evidence, matched controls, and emergency-stop/safety
  validation that this repository does not implement. Until that prerequisite
  exists, the next safe durability dependency is cumulative receipt history
  with process-kill and concurrent-writer tests; family-local hypothesis and
  evidence protocols remain downstream. v0.31 adds no actuator, environment
  transition, observed outcome, causal-success claim, autonomous inquiry,
  resolution or promotion authority, policy rewrite, semantic understanding,
  `T_g` control, or thermodynamic behavior.

## v0.32 claim boundary

- **OBSERVED:** Forty-eight focused integrated-inquiry tests and the 441-test
  full repository suite pass. Two receipts produced against distinct exact
  sidecar triples append cumulatively, duplicate append is a no-op, and either
  entry reloads with no new reservation or settlement. Reordering, unrehashed
  truncation, a fully rehashed external-action-authority mutation, and foreign
  sidecar substitution fail closed. Controlled child death before replacement
  exposes the prior complete prefix; death after replacement exposes the new
  complete prefix and releases the writer lock. Six simultaneously released
  process writers retain all six distinct receipts, while a live reader sees
  only complete prefixes of the final chain. A later append recovers the lock
  and removes a killed pre-replace writer's stale temporary. The dedicated
  compatibility test still loads and embeds all 17 preexisting VDK
  checkpoints.
- **IMPLEMENTED-EXPERIMENTAL:** The separately durable integrated-receipt
  surface now includes an explicitly invoked, bounded `.viqh` cumulative
  history. A persistent same-path POSIX advisory lock serializes cooperating
  read-modify-replace writers, and the canonical chain commits to every prior
  complete receipt in lock-acquisition order. Intrinsic history reads validate
  canonical encoding, bounds, contiguous sequences, predecessor links, unique
  receipt digests, each nested v0.31 envelope, and the head. Loading a selected
  entry additionally closes its full canonical/simulation/Lens provenance
  against the exact separately supplied sidecars. Neither append nor load can
  publish canonical, simulation, Lens, Council, or workspace mutation.
- **PROPOSED:** The history is durability evidence, not an execution log or
  authenticity root. Actually executed dependency-path evidence remains
  blocked on an external or hardware-backed command boundary, native result
  telemetry, synchronized physical evidence, matched controls, and validated
  safety stops. With the safe local durability prerequisite now present, the
  next bounded in-repository dependency is a family-local `Contradiction`
  hypothesis/evidence protocol grounded only in its preserved opposed claims;
  it must retain explicit null/inconclusive alternatives and grant no truth,
  suppression, resolution, or promotion authority. v0.32 adds no actuator,
  outcome, causal-success claim, autonomous inquiry, policy rewrite, semantic
  understanding, `T_g` control, or thermodynamic behavior.

## v0.33 claim boundary

- **OBSERVED:** Twenty-one focused Contradiction tests and the 453-test full
  repository suite pass. The new bundle replays identically after a VDK
  checkpoint round trip and mapping-order reversal; the dedicated compatibility
  test still loads and embeds all 17 preexisting checkpoints. Wrong operators
  and generator versions, missing or underfunded allocations, suppressed bid
  provenance, stale post-retrigger bases, cross-obligation allocations,
  protected-evidence removal, missing null/defer arms, preferred-claim
  injection, and a fully rehashed context forgery all fail closed.
- **IMPLEMENTED-EXPERIMENTAL:** A bounded family-local Contradiction protocol
  now derives a complete content-addressed evidence partition and exactly three
  answer-agnostic hypotheses from native claims, evidence ledgers, obligation
  history, and canonical Attention lineage. Generation is fingerprint-pure;
  validation deterministically reconstructs the expected bundle. Every arm
  protects both claims and all evidence, while typed authority fields prohibit
  truth selection, evidence suppression, resolution, and canonical commit.
- **PROPOSED:** The next dependency is a matched, isolated Contradiction
  provenance probe that preserves the complete receipt in every arm, varies
  only a typed sidecar-local provenance partition, and derives its observation
  from actual settled simulation traces. It must admit null and inconclusive
  outcomes and cannot become a truth test or Resolution Contract until that
  trace evidence exists. v0.33 adds no external action, causal-success claim,
  autonomous inquiry, canonical resolution or promotion, policy rewrite,
  semantic understanding, `T_g` control, or thermodynamic behavior.

## v0.34 claim boundary

- **OBSERVED:** Thirty-two focused Contradiction tests and the 464-test full
  repository suite pass. Distinct-root, same-root valid-null, and overlapping-
  root inconclusive fixtures produce their preregistered structural
  dispositions from actual matched settlements. Exact `.vob` reload replays
  both arms and reconstructs the identical observation without a new ledger
  entry. Replaced traces, foreign-ledger substitution, a fully rehashed
  evidence-suppressing projection, stale evidence, injected second-arm
  failure, partial-budget exhaustion, and authority mutation fail closed; the
  dedicated compatibility test still loads and embeds all 17 preexisting
  checkpoints.
- **IMPLEMENTED-EXPERIMENTAL:** A bounded family-local runner now spends one
  canonical Contradiction Attention allocation on two discarded, isolated
  simulations: a zero-patch control and one additive provenance projection.
  It atomically publishes only a complete verified simulation pair, then
  derives a content-addressed structural disposition through the existing
  ledger-backed matched observer. Every arm and observation retains the full
  v0.33 receipt and carries no truth-selection, observed-outcome, resolution,
  or canonical-commit authority.
- **PROPOSED:** Before any Contradiction Resolution Contract, derive an explicit
  family-local coverage receipt from the actual matched ledger. It should mark
  source-partition materialization and evidence preservation as grounded while
  keeping predictive discrimination, context-conditioned compatibility,
  functional consequence, independent held-out replication, and dimensional-
  separation evidence missing. `resolution_trial_ready` must therefore remain
  false. v0.34 adds no external action, source-independence proof, truth test,
  causal-success claim, autonomous inquiry, canonical resolution or promotion,
  policy rewrite, semantic understanding, `T_g` control, or thermodynamic
  behavior.

## v0.35 claim boundary

- **OBSERVED:** Forty focused Contradiction tests and the 472-test full
  repository suite pass. Each distinct, valid-null, or inconclusive matched
  probe produces one exact coverage receipt; archive replay reconstructs it
  identically. Direct derivation is canonical- and simulation-fingerprint
  invariant. Foreign-ledger substitution, a mismatched bundle, fully rehashed
  protected-evidence suppression, fully rehashed missing-requirement removal,
  and fully rehashed readiness or resolution-authority escalation fail closed.
  The dedicated compatibility test still loads and embeds all 17 preexisting
  checkpoints.
- **IMPLEMENTED-EXPERIMENTAL:** One self-validating family-local receipt now
  accounts for every declared Contradiction Resolution requirement exactly
  once as grounded or missing. It is derived from the complete canonical
  bundle and actual matched simulation pair before staged settlements are
  published, preserves the nested records as anti-suppression evidence, and
  remains simulated-only with `resolution_trial_ready=False` and no truth,
  outcome, resolution, or canonical-commit authority.
- **PROPOSED:** The next dependency is a preregistered, context-conditioned
  matched functional probe that tests whether the source-partition projection
  changes a bounded trace-derived operation while preserving both claims and
  all evidence. It must retain valid-null and inconclusive alternatives and
  cannot mark predictive discrimination, source independence, dimensional
  separation, or held-out replication grounded until those are separately
  observed. v0.35 adds no family-local Lens, external action, observed outcome,
  truth test, causal-success claim, autonomous inquiry, canonical resolution
  or promotion, policy rewrite, semantic understanding, `T_g` control, or
  thermodynamic behavior.

## v0.36 claim boundary

- **OBSERVED:** Forty-seven focused Contradiction tests and the 479-test full
  repository suite pass. All 17 preexisting checkpoints still load and embed.
  Actual settled overlays reconstruct identical context, route, functional,
  and coverage records across archive replay. Foreign-ledger substitution,
  fully rehashed query-root changes, fully rehashed route changes, forged
  prediction/readiness flags, and an injected functional-observer failure all
  fail closed; the latter leaves both staged arms unpublished.
- **IMPLEMENTED-EXPERIMENTAL:** One bounded context-conditioned operation now
  reads the exact preregistered source-partition projection from the treatment
  overlay and derives a discrete routing change relative to its zero-patch
  baseline. This grounds only context-conditioned compatibility and functional
  consequence inside that supplied context. The context is derived from the
  same canonical evidence receipt, so the result is deterministic internal
  functional evidence rather than an independent predictor or causal-success
  test. Every result preserves both claims and all evidence and remains
  simulated-only with `resolution_trial_ready=False`.
- **PROPOSED:** The next dependency is an explicitly active, family-local
  Equivalence Lens bound into a predeclared controlled Contradiction context,
  with exact Lens definition, binding, evidence, and governance lineage. Only
  after that lineage exists may separately declared calibration and genuinely
  independent held-out contexts test dimensional separation, source
  independence, or predictive discrimination. v0.36 adds no active Lens,
  external action or outcome, learned context, truth selection, canonical
  resolution or promotion, autonomous scheduling, policy rewrite, semantic
  understanding, `T_g` control, or thermodynamic behavior.

## v0.37 claim boundary

- **OBSERVED:** Fifty-eight focused Lens/Contradiction tests and the 491-test
  full repository suite pass. All 17 preexisting checkpoints still load and
  embed. Exact `.vob` replay reconstructs the same controlled context, active
  Lens lineage, route projections, and coverage without a new reservation or
  settlement. Wrong-family and suspended bindings, missing Lens evidence,
  unsupported dimensions, sidecar changes after preregistration, foreign-
  simulation-ledger substitution, fully rehashed route-projection changes,
  hidden gaps, forged authority, and an injected wrapper-observer failure all
  fail closed; the failure leaves both staged arms unpublished.
- **IMPLEMENTED-EXPERIMENTAL:** One opt-in wrapper now binds the exact active
  `Contradiction` Lens definition, binding, evidence history, and governance
  history into a caller-supplied controlled context before executing the
  existing matched pair. After revalidating the real settlements, the Lens
  applies only `SELECT_ACTIVATED_REFS` read-only to each actual treatment
  route. A nested coverage receipt grounds only the existence and use of that
  active family-local Lens. It preserves both claims and all evidence and
  remains simulated-only with `resolution_trial_ready=False`.
- **PROPOSED:** The next dependency is a separately preregistered calibration
  context and a genuinely independent held-out context, each with matched
  controls and identical Lens lineage. Their observations must test whether
  the selected dimension separates outcomes across sources rather than merely
  reproducing the same receipt-derived routes. Only such evidence may ground
  dimensional separation, source independence, predictive discrimination, or
  held-out replication. v0.37 adds no learned Lens or context, external action
  or outcome, truth selection, causal-success claim, canonical resolution or
  promotion, autonomous scheduling, policy rewrite, semantic understanding,
  `T_g` control, or thermodynamic behavior.

## v0.38 claim boundary

- **OBSERVED:** Sixty-seven focused Contradiction/Lens tests and the 500-test
  full repository suite pass. All 17 preexisting checkpoints still load and
  embed. Dual `.vob` plus `.vct` replay reconstructs the exact calibration and
  held-out controls, nested observations, structural-effect classification,
  and receipt at zero additional simulation cost. Reused canonical contexts,
  mismatched Lens histories, Lens changes after preregistration, fully rehashed
  checkpoint overlap, forged predictive authority, crossed simulation ledgers,
  and an injected second-context failure all fail closed; the injected failure
  publishes neither staged simulation pair.
- **IMPLEMENTED-EXPERIMENTAL:** One opt-in controller now runs the existing
  v0.37 matched probe in two separately preregistered, canonically disjoint
  evidence contexts under one exact frozen Lens lineage and matched policy
  controls. A content-addressed receipt classifies equality of an
  ID-independent, trace-derived structural-effect signature, retaining a valid
  divergent-null disposition. A separately durable `.vct` sidecar can preserve
  either the preregistration or completed receipt and re-closes both canonical,
  simulation, and Lens lineages on load. This establishes only independently
  constructed canonical contexts and deterministic internal structural
  replication; every previously missing Resolution requirement remains
  missing and `resolution_trial_ready=False`.
- **PROPOSED:** The next dependency is a calibration-only, preregistered
  dimension/outcome criterion derived from actual experiment traces, frozen
  before the held-out run, and then applied unchanged to the held-out context
  alongside an identical matched control. It must admit an explicit valid null
  and test whether the selected Lens dimension separates a bounded functional
  outcome without consulting held-out evidence during calibration. Until that
  exists, v0.38 does not establish dimensional separation, predictive
  discrimination, Resolution-level held-out replication, real-world source
  independence, external outcome, learned Lens or context, truth selection,
  causal success, canonical resolution or promotion, autonomous scheduling,
  policy rewrite, semantic understanding, `T_g` control, or thermodynamic
  behavior.

## v0.39 claim boundary

- **OBSERVED:** Eighty-three focused Contradiction/Lens tests and the 507-test
  full repository suite pass. All 17 preexisting checkpoints still load and
  embed. An instrumented runner observes the immutable criterion before the
  held-out probe is invoked. The matched fixture produces a trace-local
  cardinality/outcome match, while a held-out context outside the calibration
  cardinality profile produces the declared valid null. A held-out
  observation cannot be supplied to the calibration-only deriver. Fully
  rehashed declaration-grammar, calibration-outcome, and authority changes,
  crossed simulation ledgers, completed-sidecar tampering, and an injected
  post-criterion held-out failure all fail closed; the injected failure
  publishes neither simulation pair. Dual `.vob` plus `.vdc` replay
  reconstructs the exact criterion and evaluation at zero additional cost.
- **IMPLEMENTED-EXPERIMENTAL:** One opt-in declaration now fixes the typed
  `SELECT_ACTIVATED_REFS` cardinality profile and bounded functional outcomes
  before execution. The controller settles the calibration pair in a private
  ledger, derives a content-addressed criterion solely through the calibration
  observation API, and only then invokes the held-out pair and applies that
  criterion unchanged. The evaluation retains match, out-of-profile valid
  null, and mismatch branches. A completed `.vdc` sidecar atomically preserves
  the full pair/declaration/criterion/evaluation lineage. This establishes only
  ordering, replay, and an internal trace-local correspondence; the
  Resolution coverage remains unchanged and `resolution_trial_ready=False`.
- **PROPOSED:** The next dependency is a durable two-phase calibration-stage
  receipt that is atomically persisted before held-out execution and can
  resume after process death without consulting held-out traces. It needs
  writer arbitration, stale-temporary recovery, exact pairing back to both
  preregistered contexts, and unchanged matched controls. Only after that
  durability boundary should a causally downstream held-out outcome channel
  that does not reuse Lens-projected references or the functional-routing
  derivation be tested. Until those layers exist, v0.39 does not establish
  Resolution-level dimensional separation, predictive discrimination,
  independent held-out replication, real-world source independence, external
  outcome, learned Lens or context, truth selection, causal success, canonical
  resolution or promotion, autonomous scheduling, policy rewrite, semantic
  understanding, `T_g` control, or thermodynamic behavior.

## v0.40 claim boundary

- **OBSERVED:** Eighty-one focused Contradiction tests and the 513-test full
  repository suite pass. The dedicated compatibility check loads and embeds
  all 17 preexisting checkpoints. Before resume, the held-out ledger remains
  empty and the canonical `.vcs` artifact carries no held-out observation.
  The artifact reconstructs the exact two-settlement calibration ledger and
  frozen criterion. Killing a writer immediately before replacement leaves no
  visible stage and its stale temporary is recovered by the next locked
  writer; killing immediately after replacement leaves a complete stage that
  a new process validates and resumes. Two simultaneously released foreign
  writers produce exactly one committed stage and one rejection. Identical
  publication is idempotent. Crossed canonical contexts, a fully rehashed
  authority escalation, injected held-out failure, and a nonpristine held-out
  ledger all fail closed without changing the stage, either canonical kernel,
  the Lens sidecar, or the supplied held-out ledger.
- **IMPLEMENTED-EXPERIMENTAL:** One opt-in POSIX two-phase API now executes the
  calibration split from a pristine private simulation ledger and atomically
  commits an immutable, content-addressed `.vcs` sidecar before exposing a
  held-out resume method. The sidecar embeds the complete calibration ledger
  and closes its observation and criterion over both preregistered canonical
  contexts, identical Lens lineage, and unchanged matched-control signature.
  Its lock gives cooperating local writers first-committer-wins arbitration,
  same-stage idempotence, and stale-temporary cleanup. Resume accepts only the
  durable artifact and a pristine held-out ledger, reconstructs every
  calibration trace, then executes held-out work and applies the criterion
  unchanged. This is a process-restart evidence boundary only;
  `resolution_trial_ready=False` and all v0.39 Resolution gaps remain.
- **PROPOSED:** The next dependency is a causally downstream held-out outcome
  channel whose observation is derived from actual experiment traces without
  reusing either the Lens-projected references or the functional-routing
  disposition that defines the criterion. It must be preregistered before the
  calibration stage, retain an unchanged matched control and explicit valid
  null, and preserve its own durable provenance before any claim of predictive
  discrimination or dimensional separation is tested. Until that independent
  channel exists, v0.40 does not establish Resolution-level dimensional
  separation, predictive discrimination, independent held-out replication,
  real-world source independence, external outcome, learned Lens or context,
  truth selection, causal success, canonical resolution or promotion,
  autonomous scheduling, policy rewrite, semantic understanding, `T_g`
  control, or thermodynamic behavior.

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
Contradiction-hypothesis tests additionally target mandatory provenance/null/
defer arms, complete support/refutation symmetry, evidence-versus-source-root
partition separation, read-only deterministic checkpoint replay, typed and
budgeted Attention authorization, triggering-evidence closure, stale-basis and
cross-obligation rejection, protected-evidence anti-suppression, preferred-
claim prohibition, missing-counterweight rejection, and fully rehashed context
substitution.
Contradiction-probe tests additionally target matched zero/full controls,
complete receipt lineage in both arms, trace-derived distinct/null/inconclusive
classification, single-record additive overlay scope, exact archive replay,
replaced-trace and foreign-ledger rejection, fully rehashed projection
suppression, stale-bundle rejection, atomic second-arm failure, staged budget
rollback, and hard absence of truth, observed-outcome, resolution, or commit
authority.
Contradiction-resolution-evidence tests additionally target one-for-one
coverage for every structural disposition, complete nested hypothesis and
observation retention, exact requirement partitioning, read-only direct
reconstruction, archive replay, foreign-ledger and mismatched-bundle rejection,
fully rehashed protected-evidence suppression, hidden missing requirements,
and forged readiness or resolution authority.
Contradiction-functional tests additionally target pre-execution context
commitment in both plans, exact treatment-only projection access, two-route
distinct/null/inconclusive classification, immutable query-root provenance,
actual-ledger reconstruction, exact archive replay, foreign-ledger rejection,
fully rehashed context and route tampering, forged prediction/readiness flags,
atomic observer-failure rollback, and the hard absence of truth, external-
outcome, resolution, or canonical-commit authority.
Contradiction-Lens-control tests additionally target explicit predeclared
invocation, exact definition/binding/evidence/governance closure, active family
scope, nonempty evidence, suspension and unsupported-operator rejection,
read-only projection of actual treatment routes, sidecar-staleness rejection,
cross-ledger archive replay, foreign-simulation-ledger rejection, fully
rehashed projection/gap/authority tampering, atomic wrapper rollback, and the
hard absence of dimensional-separation, source-independence, predictive,
held-out, truth, resolution, or canonical-commit authority.
Contradiction held-out-control tests additionally target separate canonical
checkpoints and simulation ledgers, disjoint obligation/claim/evidence
provenance, identical frozen Lens lineage, matched budgets and bounded outcome
controls, ID-independent structural-effect comparison, explicit divergent-null
support, dual-ledger atomic rollback, deterministic preregistration/completed
`.vct` bytes, dual-archive zero-cost replay, crossed-ledger rejection, fully
rehashed context-overlap and authority attacks, and the hard absence of
dimensional-separation, source-independence, predictive, Resolution-level
held-out, truth, outcome, resolution, or canonical-commit authority.
Contradiction dimension-criterion tests additionally target declaration before
execution, calibration-only derivation from actual settled traces, criterion
freeze before the held-out runner call, unchanged held-out application,
cardinality-profile outcome match, an explicit out-of-profile valid null,
fully rehashed grammar/evidence/authority tampering, post-criterion atomic
rollback, deterministic completed `.vdc` bytes, crossed-ledger rejection, and
dual-archive zero-cost replay. They also enforce the hard absence of
Resolution-level dimensional separation, predictive discrimination,
independent held-out replication, source independence, external outcome,
truth, resolution, or canonical-commit authority.
Contradiction calibration-stage tests additionally target persistence before
held-out execution, complete embedded calibration-ledger reconstruction,
process death immediately before and after atomic replacement, stale-temporary
recovery under the writer lock, idempotent same-stage publication,
first-committer-wins arbitration between foreign process writers, exact pairing
to both preregistered canonical contexts, fully rehashed authority tampering,
failed-resume rollback, immutable stage bytes during resume, and rejection of
nonpristine held-out ledgers. They retain the same hard absence of independent
outcome, predictive, truth, resolution, promotion, policy-rewrite, and
canonical-commit authority.
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
FailedPolicy-family tests additionally target the single-denial negative
control, repeated-block detection, pure inspection, exact replay, stable-scope
retriggering, policy-version continuity, independent-scope separation,
checkpoint/View rebuilding, missing-decision rejection, and executive Attention
without policy or denial mutation authority.
Paradigm-Challenge tests additionally target cross-family and independent-root
admission, rejection of ordinary open obligations, exact request replay,
complete immutable-history replay, isolated simulation lineage, cross-seed
replication, evidence and orthogonal-fingerprint preservation, high-blast-radius
eligibility, sidecar reconstruction, sequence tampering, and the hard absence
of promotion or canonical-mutation authority.
Paired-archive tests additionally target deterministic byte replay, two-family
View restoration, future canonical transition equivalence, canonical versus
simulation ledger separation, checksum alteration, rehashed cross-ledger
substitution, rehashed settlement-origin forgery, failed atomic replacement,
and embedding all 17 preexisting VDK checkpoints without changing their
format in both v1 and v2 archive envelopes.
Lens-archive tests additionally target v2 deterministic replay, two family-
local active bindings, evidence and governance restoration, post-reload
sidecar isolation, legacy v1 compatibility, rehashed registry/ledger mixing,
unresolved typed settlement refs, and future-dated governance rejection.
Diagnostic-archive tests additionally target deterministic v3 byte replay,
four-ledger fingerprint restoration, mandatory Lens pairing, v1/v2
compatibility, rehashed foreign-ledger substitution, causal-attribution
forgery, missing probe-settlement rejection, terminal non-authority, and all 17
legacy checkpoints embedded in an empty-Diagnostic v3 envelope.
Council-archive tests additionally target deterministic v4 byte replay,
six-part fingerprint restoration, mandatory Diagnostic pairing, exact decision
replay without authority, rehashed foreign-ledger rejection, missing candidate-
simulation rejection, and all 17 legacy checkpoints embedded in an empty-
Council v4 envelope.
Council-evidence archive tests additionally target deterministic v5 replay,
custom policy recovery, complete per-decision evidence coverage, exact request
and least-regret recomputation, rehashed metric-change rejection, and all 17
legacy checkpoints embedded in an empty-evidence v5 envelope.
Paradigm-evidence archive tests additionally target deterministic cumulative v6
replay, custom policy recovery, complete per-decision trial coverage, exact
admission and shadow-decision recomputation, rehashed anomaly and trial changes,
missing settlement rejection, hard non-promotion, and all 17 legacy checkpoints
embedded in an empty-Paradigm v6 envelope.
Archive-durability tests additionally target controlled pre/post-replace
process termination, old-or-new visibility, subsequent-save recovery, six
competing process writers, live-reader whole-file atomicity, final archive
validation, and successful-writer temporary-file cleanup.
Integrated-inquiry tests additionally target detector-to-settlement provenance,
mandatory hypothesis counterweights, functional-class trial selection, bounded
Attention funding, copy-on-write non-leakage, exact zero-cost replay after
archive reload, mixed-scope transactional rejection, injected-leak rollback,
rehashed internal-provenance deletion, one-for-one Resolution-evidence coverage,
foreign simulation-ledger rejection, immutable missing-field disclosure, and
the hard absence of trial-readiness or resolution authority. Overlay-operational
tests additionally target reconstruction from settled plans and ledgers,
canonical evidence retrieval instead of patch-carried labels, visible traversal
grammar, additive structural valid nulls, noncanonical endpoint rejection,
one-for-one trace embedding, exact replay, coverage cross-linking, staged
transaction rollback, and unforgeable workspace, action, path, resolution, and
commit authority boundaries. Native workspace-admission tests additionally
target mapping only actually retrieved canonical evidence, real native report
and event reconstruction, declared slot-cap suppression, semantic-record and
canonical-workspace isolation, exact held-out effect replay, zero-cost archive
reconstruction, foreign-ledger rejection, complete controlled-trace coverage,
observer tampering, and the hard absence of action, dependency-path,
resolution, or canonical-commit authority.
Native outgoing-action tests additionally target grounded no-action baselines,
real three-King authorization, exact decision-to-`AUTHORIZED_ACTION` lineage,
native action admission under the declared slot cap, ID-independent held-out
effect replay, zero-cost archive reconstruction, foreign-ledger rejection,
complete integrated-trace coverage, supplied-policy substitution, observer and
authority tampering, canonical Council/workspace isolation, and the hard
absence of external action, dependency-path, outcome, resolution, or commit
authority.
Integrated-receipt tests additionally target deterministic canonical JSON,
exact `.vob` pairing, full nested receipt recovery without replay cost,
canonical Attention and obligation closure, reservation/settlement linkage,
canonical evidence preservation, active-Lens matching, shadow-record
non-leakage, rehashed authority and omission attacks, foreign sidecar
substitution, rejection of incomplete pre-v0.30 traces, and atomic-replace
failure that leaves the prior receipt intact.
Cumulative-receipt tests additionally target bounded canonical history,
idempotent duplicate append, exact per-entry sidecar pairing, predecessor/head
chain closure, reorder and unrehashed-truncation rejection, fully rehashed
authority rejection, pre/post-replace process death, stale-temporary recovery,
lock release on process death, six-way cooperating-writer retention, live-
reader prefix atomicity, and zero canonical or simulation mutation on reload.
