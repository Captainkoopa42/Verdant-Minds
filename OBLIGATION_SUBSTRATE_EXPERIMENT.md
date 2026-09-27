# Obligation Substrate v0.20

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
  provenance-visible bids, but v0.14 does not claim Verdant has learned their
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
- The simulation ledger is packaged only by explicit `.vob` save/load calls;
  ordinary `.vdk` checkpoints and runtime scheduling do not automatically
  include it. The atomic replace failure test and sync path support paired
  durability, but process-kill recovery and concurrent writers have not been
  exercised. Archive hashes detect accidental or non-rehashed alteration;
  they are not signatures or an authenticity boundary against an adversary
  able to rewrite every member and the manifest.
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
