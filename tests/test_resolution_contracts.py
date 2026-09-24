from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pytest

from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    ObligationFamily,
    RelationProposal,
    VerdantKernel,
)
from verdant_obligations import (
    AttentionBidInput,
    AttentionPortfolio,
    CounterfactualPlan,
    CounterfactualRuntime,
    DependencyGapDetector,
    DependencyGapHypothesisGenerator,
    DependencyGapResolutionValidator,
    DependencyPathObservation,
    EquivalenceLensSystem,
    LensOpcode,
    MatchedResolutionPair,
    OutcomeKind,
    ResolutionCandidate,
    ResolutionContractVerdict,
    ResolutionInvariant,
    ResolutionTrialObservation,
    TrialArm,
    build_hypothesis_plan,
    dependency_evidence_edge_ref,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _experience(
    key: str,
    *,
    labels: tuple[str, ...] = (),
    relations: tuple[RelationProposal, ...] = (),
    evidence_kind: EvidenceKind | None = None,
) -> ExperienceCommand:
    return ExperienceCommand(
        event_key=key,
        source_ref=f"curriculum:{key}",
        modality="text",
        payload_sha256=_digest(key),
        feature_vector=tuple(index / 15.0 for index in range(16)),
        concept_labels=labels,
        relation_proposals=relations,
        semantic_evidence_kind=evidence_kind,
    )


@dataclass(frozen=True)
class ResolutionFixture:
    kernel: VerdantKernel
    candidate: ResolutionCandidate
    pairs: tuple[MatchedResolutionPair, ...]
    runtime: CounterfactualRuntime
    lenses: EquivalenceLensSystem


def _setup_resolution_fixture() -> ResolutionFixture:
    kernel = VerdantKernel(seed=5701, state_dim=16, run_label="resolution-contract")
    kernel.apply_experience(
        _experience(
            "resolution-dependency",
            relations=(
                RelationProposal(
                    source_label="stabilize loop",
                    target_label="pressure input",
                    relation_type="requires",
                ),
            ),
        )
    )
    kernel.apply_experience(
        _experience(
            "resolution-route",
            relations=(
                RelationProposal(
                    source_label="pressure input",
                    target_label="canonical reading",
                    relation_type="routes_to",
                ),
            ),
        )
    )
    kernel.apply_experience(
        _experience(
            "resolution-grounding",
            labels=("canonical reading",),
            evidence_kind=EvidenceKind.OUTCOME,
        )
    )
    detection = DependencyGapDetector().detect_and_record(kernel)
    obligation = detection.mutations[0].obligation
    hypotheses = DependencyGapHypothesisGenerator().generate(
        kernel, obligation.kernel_id
    )
    projected = next(item for item in hypotheses if item.patches)
    completion = next(
        item for item in projected.outcomes if item.kind == OutcomeKind.PATH_COMPLETES
    )

    lenses = EquivalenceLensSystem()
    definition = lenses.register_definition(
        operators=(
            LensOpcode.SELECT_ACTION,
            LensOpcode.SELECT_ACTIVATED_REFS,
            LensOpcode.SELECT_EDGE_ENDPOINTS,
            LensOpcode.SELECT_EDGE_TYPES,
        ),
        provenance_refs=("matched-control-suite:v0.7",),
    )
    binding = lenses.approve_binding(
        definition_id=definition.definition_id,
        obligation_family=ObligationFamily.DEPENDENCY_GAP,
        failure_tripwire_count=3,
        calibration_refs=("control:dependency-a", "control:dependency-b"),
        source_event_key="lens:resolution-contract",
        cycle=kernel.state.cycle,
    )

    decision = AttentionPortfolio().decide(
        kernel,
        (
            AttentionBidInput(
                obligation_id=obligation.kernel_id,
                action_operator="matched_resolution_contract",
                requested_budget=0.20,
                estimated_cost=0.20,
                expected_gain=0.8,
                uncertainty=0.7,
                urgency=0.5,
                novelty=0.8,
                metric_provenance_refs=projected.provenance_refs,
                generator_version=projected.grammar_version,
            ),
        ),
        source_event_key="attention:resolution-contract",
    ).decision
    allocation = decision.allocations[0]
    checkpoint_fingerprint = kernel.fingerprint()
    runtime = CounterfactualRuntime()

    actionable_evidence = next(
        ref
        for ref in completion.consequence.activated_canonical_refs
        if ref in kernel.state.evidence
        and kernel.state.evidence[ref].kind == EvidenceKind.OUTCOME
    )
    reading_concept = next(
        item
        for item in kernel.state.concepts.values()
        if actionable_evidence in item.evidence_refs
    )
    requires_relation = next(
        item.relation_id
        for item in kernel.state.relations.values()
        if item.relation_type == "requires"
    )
    route_relation = next(
        item.relation_id
        for item in kernel.state.relations.values()
        if item.relation_type == "routes_to"
    )
    protected = obligation.canonical_triggering_refs
    pairs = []
    settlement_refs = []
    for seed in (11, 29):
        baseline_result = runtime.execute(
            kernel,
            allocation_id=allocation.allocation_id,
            plan=CounterfactualPlan.build(
                source_event_key=f"simulation:resolution:baseline:{seed}",
                operator_version="matched-control-baseline-v1",
                requested_budget=0.02,
                consumed_budget=0.01,
                result_refs=(projected.hypothesis_id, f"seed:{seed}"),
            ),
        )
        treatment_result = runtime.execute(
            kernel,
            allocation_id=allocation.allocation_id,
            plan=build_hypothesis_plan(
                projected,
                completion,
                source_event_key=f"simulation:resolution:treatment:{seed}",
                requested_budget=0.02,
                consumed_budget=0.01,
            ),
        )
        settlement_refs.extend(
            (
                baseline_result.settlement.settlement_id,
                treatment_result.settlement.settlement_id,
            )
        )
        common = {
            "checkpoint_fingerprint": checkpoint_fingerprint,
            "cue_ref": "cue:resolution-dependency",
            "context_fingerprint": "context:resolution-contract",
            "seed": seed,
            "horizon": 4,
            "lens_binding_id": binding.binding_id,
            "retrieved_refs": protected,
            "slot_budget": len(protected) + 1,
        }
        baseline = ResolutionTrialObservation.build(
            arm=TrialArm.BASELINE,
            simulation_settlement_ref=baseline_result.settlement.settlement_id,
            admitted_refs=protected,
            outgoing_action_signature="defer:missing-pressure-input",
            **common,
        )
        treatment = ResolutionTrialObservation.build(
            arm=TrialArm.TREATMENT,
            simulation_settlement_ref=treatment_result.settlement.settlement_id,
            resolution_structure_ref=projected.hypothesis_id,
            admitted_refs=tuple(sorted({*protected, projected.hypothesis_id})),
            outgoing_action_signature="retrieve:canonical-reading",
            dependency_path=DependencyPathObservation(
                node_refs=(
                    obligation.target_action_node,
                    obligation.missing_input_signature,
                    reading_concept.concept_id,
                    actionable_evidence,
                ),
                edge_refs=(
                    requires_relation,
                    route_relation,
                    dependency_evidence_edge_ref(
                        reading_concept.concept_id,
                        actionable_evidence,
                    ),
                ),
                actionable_evidence_ref=actionable_evidence,
                distance=3,
            ),
            **common,
        )
        pairs.append(MatchedResolutionPair.build(baseline, treatment))

    governance_event = next(
        item
        for item in lenses.ledger.governance_events
        if item.binding_id == binding.binding_id
    )
    candidate = ResolutionCandidate.build(
        obligation_id=obligation.kernel_id,
        resolution_structure_ref=projected.hypothesis_id,
        protected_canonical_refs=protected,
        lineage_refs=tuple(sorted({projected.hypothesis_id, *settlement_refs})),
        governance_refs=(governance_event.event_id,),
    )
    return ResolutionFixture(
        kernel=kernel,
        candidate=candidate,
        pairs=tuple(pairs),
        runtime=runtime,
        lenses=lenses,
    )


def _replace_observation(
    observation: ResolutionTrialObservation,
    **updates,
) -> ResolutionTrialObservation:
    values = observation.model_dump(mode="python", exclude={"observation_id"})
    values.update(updates)
    return ResolutionTrialObservation.build(**values)


def _replace_pair(
    pair: MatchedResolutionPair,
    *,
    baseline: ResolutionTrialObservation | None = None,
    treatment: ResolutionTrialObservation | None = None,
) -> MatchedResolutionPair:
    return MatchedResolutionPair.build(
        baseline or pair.baseline,
        treatment or pair.treatment,
    )


def _validate(fixture: ResolutionFixture, **updates) -> ResolutionContractVerdict:
    values = {
        "candidate": fixture.candidate,
        "matched_pairs": fixture.pairs,
        "simulation_ledger": fixture.runtime.ledger,
        "lens_system": fixture.lenses,
    }
    values.update(updates)
    return DependencyGapResolutionValidator().validate(fixture.kernel, **values)


def _results(verdict: ResolutionContractVerdict):
    return {item.invariant: item for item in verdict.invariant_results}


def test_valid_matched_resolution_passes_without_resolution_authority() -> None:
    fixture = _setup_resolution_fixture()
    canonical_before = fixture.kernel.fingerprint()
    ledger_before = fixture.runtime.ledger.fingerprint()
    lenses_before = fixture.lenses.fingerprint()

    first = _validate(fixture)
    second = _validate(fixture)

    assert first == second
    assert first.passed
    assert not first.resolution_authority_enabled
    assert all(item.passed for item in first.invariant_results)
    assert fixture.kernel.fingerprint() == canonical_before
    assert fixture.runtime.ledger.fingerprint() == ledger_before
    assert fixture.lenses.fingerprint() == lenses_before


def test_suppression_and_slot_budget_exploit_fail_closed() -> None:
    fixture = _setup_resolution_fixture()
    pair = fixture.pairs[0]
    protected = fixture.candidate.protected_canonical_refs[0]
    admitted = tuple(
        item for item in pair.treatment.admitted_refs if item != protected
    )
    treatment = _replace_observation(
        pair.treatment,
        admitted_refs=admitted,
        suppressed_refs=(protected,),
        removed_edge_refs=("edge:protected",),
        slot_budget=pair.baseline.slot_budget - 1,
    )
    pairs = (_replace_pair(pair, treatment=treatment), fixture.pairs[1])

    verdict = _validate(fixture, matched_pairs=pairs)
    results = _results(verdict)

    assert not verdict.passed
    assert not results[ResolutionInvariant.EVIDENCE_PRESERVED].passed
    assert not results[ResolutionInvariant.NO_SUPPRESSION].passed


def test_tautological_resolution_with_identical_action_has_no_gain() -> None:
    fixture = _setup_resolution_fixture()
    pairs = tuple(
        _replace_pair(
            pair,
            treatment=_replace_observation(
                pair.treatment,
                outgoing_action_signature=pair.baseline.outgoing_action_signature,
            ),
        )
        for pair in fixture.pairs
    )

    verdict = _validate(fixture, matched_pairs=pairs)
    results = _results(verdict)

    assert not results[ResolutionInvariant.PREDICTIVE_DISCRIMINATION].passed
    assert not results[ResolutionInvariant.EXPLANATORY_GAIN].passed


def test_dummy_path_without_actionable_canonical_evidence_is_rejected() -> None:
    fixture = _setup_resolution_fixture()
    pairs = tuple(
        _replace_pair(
            pair,
            treatment=_replace_observation(
                pair.treatment,
                dependency_path=DependencyPathObservation(
                    node_refs=(
                        pair.treatment.dependency_path.node_refs[0],
                        "evidence:dummy",
                    ),
                    edge_refs=("edge:dummy",),
                    actionable_evidence_ref="evidence:dummy",
                    distance=1,
                ),
            ),
        )
        for pair in fixture.pairs
    )

    verdict = _validate(fixture, matched_pairs=pairs)
    results = _results(verdict)

    assert not results[ResolutionInvariant.DEPENDENCY_PATH_COMPLETION].passed
    assert not results[ResolutionInvariant.EXPLANATORY_GAIN].passed


def test_forged_edges_cannot_complete_a_path_to_real_evidence() -> None:
    fixture = _setup_resolution_fixture()
    pairs = tuple(
        _replace_pair(
            pair,
            treatment=_replace_observation(
                pair.treatment,
                dependency_path=pair.treatment.dependency_path.model_copy(
                    update={"edge_refs": tuple(
                        "relation:forged" for _ in pair.treatment.dependency_path.edge_refs
                    )}
                ),
            ),
        )
        for pair in fixture.pairs
    )

    verdict = _validate(fixture, matched_pairs=pairs)
    results = _results(verdict)

    assert not results[ResolutionInvariant.DEPENDENCY_PATH_COMPLETION].passed
    assert not results[ResolutionInvariant.EXPLANATORY_GAIN].passed


def test_unmatched_control_and_seed_reuse_fail_replication() -> None:
    fixture = _setup_resolution_fixture()
    first, second = fixture.pairs
    unmatched = _replace_pair(
        first,
        treatment=_replace_observation(first.treatment, horizon=first.treatment.horizon + 1),
    )
    reused_seed = _replace_pair(
        second,
        baseline=_replace_observation(second.baseline, seed=first.baseline.seed),
        treatment=_replace_observation(second.treatment, seed=first.baseline.seed),
    )

    verdict = _validate(fixture, matched_pairs=(unmatched, reused_seed))
    results = _results(verdict)

    assert not results[ResolutionInvariant.MATCHED_CONTROLS].passed
    assert not results[ResolutionInvariant.CROSS_SEED_REPLICATION].passed


def test_unknown_lineage_and_governance_refs_fail_without_throwing() -> None:
    fixture = _setup_resolution_fixture()
    candidate = ResolutionCandidate.build(
        obligation_id=fixture.candidate.obligation_id,
        resolution_structure_ref=fixture.candidate.resolution_structure_ref,
        protected_canonical_refs=fixture.candidate.protected_canonical_refs,
        lineage_refs=("simulation:invented",),
        governance_refs=("governance:invented",),
    )

    verdict = _validate(fixture, candidate=candidate)
    results = _results(verdict)

    assert not results[ResolutionInvariant.LINEAGE_TRACEABILITY].passed
    assert not results[ResolutionInvariant.GOVERNANCE_PASS].passed


def test_tampered_verdict_and_pair_are_detected() -> None:
    fixture = _setup_resolution_fixture()
    verdict = _validate(fixture)
    tampered_verdict = verdict.model_copy(update={"passed": False})
    with pytest.raises(ValueError, match="disagrees"):
        ResolutionContractVerdict.model_validate(
            tampered_verdict.model_dump(mode="json")
        )

    pair = fixture.pairs[0]
    tampered_pair = pair.model_copy(update={"pair_id": "pair:tampered"})
    with pytest.raises(ValueError, match="checksum"):
        MatchedResolutionPair.model_validate(tampered_pair.model_dump(mode="json"))
