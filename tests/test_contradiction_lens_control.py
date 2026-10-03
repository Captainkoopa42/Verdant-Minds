from __future__ import annotations

from pathlib import Path

import pytest

from verdant_claims import ClaimLearningPipeline
from verdant_kernel import (
    ClaimPolarity,
    ClaimSourceClass,
    ObligationFamily,
    VerdantKernel,
)
from verdant_kernel.models import stable_id
from verdant_obligations import (
    CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION,
    CONTRADICTION_LENS_GROUNDED_REQUIREMENTS,
    CONTRADICTION_LENS_MISSING_REQUIREMENTS,
    CONTRADICTION_PROVENANCE_ACTION_OPERATOR,
    AttentionBidInput,
    AttentionPortfolio,
    ContradictionHypothesisProtocol,
    ContradictionLensControlledContext,
    ContradictionLensControlledObservation,
    ContradictionLensControlledObserver,
    ContradictionLensControlledProbeRunner,
    ContradictionLensControlIntegrityError,
    ContradictionLensResolutionEvidenceReceipt,
    ContradictionObligationDetector,
    ContradictionResolutionRequirement,
    CounterfactualRuntime,
    EquivalenceLensSystem,
    LensEvidenceResult,
    LensOpcode,
    load_experiment_archive_bundle,
    save_experiment_archive,
)


def _claim(
    kernel: VerdantKernel,
    *,
    event_key: str,
    polarity: ClaimPolarity,
    source: ClaimSourceClass,
) -> None:
    ClaimLearningPipeline().record_claim(
        kernel,
        event_key=event_key,
        native_description=f"Controlled Lens evidence {event_key}.",
        subject_label="door",
        predicate="has_property",
        object_label="open",
        polarity=polarity,
        source_class=source,
    )


def _prepared(seed: int):
    kernel = VerdantKernel(
        seed=seed,
        state_dim=16,
        run_label=f"contradiction-lens-{seed}",
    )
    _claim(
        kernel,
        event_key=f"lens-affirmed-{seed}",
        polarity=ClaimPolarity.AFFIRMED,
        source=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    _claim(
        kernel,
        event_key=f"lens-negated-{seed}",
        polarity=ClaimPolarity.NEGATED,
        source=ClaimSourceClass.HUMAN_TESTIMONY,
    )
    obligation = ContradictionObligationDetector().detect_and_record(
        kernel
    ).mutations[0].obligation
    latest = next(
        item
        for item in reversed(kernel.state.obligation_history)
        if item.obligation_id == obligation.kernel_id
    )
    allocation = AttentionPortfolio().decide(
        kernel,
        (
            AttentionBidInput(
                obligation_id=obligation.kernel_id,
                action_operator=CONTRADICTION_PROVENANCE_ACTION_OPERATOR,
                requested_budget=0.05,
                estimated_cost=0.05,
                expected_gain=0.55,
                uncertainty=0.85,
                urgency=0.50,
                novelty=0.75,
                metric_provenance_refs=latest.triggering_refs,
                generator_version=CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION,
            ),
        ),
        source_event_key=f"contradiction-lens-attention-{seed}",
    ).decision.allocations[0]
    bundle = ContradictionHypothesisProtocol().generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )
    return kernel, obligation, allocation, bundle


def _lenses(
    kernel: VerdantKernel,
    bundle,
    *,
    family: ObligationFamily = ObligationFamily.CONTRADICTION,
    operators: tuple[LensOpcode, ...] = (LensOpcode.SELECT_ACTIVATED_REFS,),
    record_evidence: bool = True,
    tripwire: int = 2,
) -> EquivalenceLensSystem:
    lenses = EquivalenceLensSystem()
    definition = lenses.register_definition(
        operators=operators,
        provenance_refs=(bundle.evidence_receipt.receipt_id,),
    )
    binding = lenses.approve_binding(
        definition_id=definition.definition_id,
        obligation_family=family,
        failure_tripwire_count=tripwire,
        calibration_refs=(bundle.evidence_receipt.receipt_id,),
        source_event_key=f"contradiction-lens:approve:{bundle.bundle_id}",
        cycle=kernel.state.cycle,
    )
    if record_evidence:
        lenses.record_evidence(
            binding_id=binding.binding_id,
            result=LensEvidenceResult.VALID_NULL,
            independent_consequence_refs=(bundle.evidence_receipt.receipt_id,),
            source_event_key=f"contradiction-lens:evidence:{bundle.bundle_id}",
            cycle=kernel.state.cycle,
            hypothesis_refs=tuple(
                item.hypothesis_id for item in bundle.hypotheses
            ),
        )
    return lenses


def _run(seed: int, source_event_key: str):
    kernel, obligation, allocation, bundle = _prepared(seed)
    lenses = _lenses(kernel, bundle)
    context = ContradictionLensControlledContext.build(
        bundle,
        lenses,
        source_event_key=source_event_key,
    )
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    lens_before = lenses.fingerprint()
    run = ContradictionLensControlledProbeRunner().run(
        kernel,
        runtime,
        lenses,
        bundle=bundle,
        controlled_context=context,
        source_event_key=source_event_key,
    )
    assert kernel.fingerprint() == canonical_before
    assert lenses.fingerprint() == lens_before
    return kernel, obligation, allocation, bundle, lenses, runtime, context, run


def _rehash_projection(payload: dict) -> dict:
    values = dict(payload)
    values["projection_id"] = stable_id(
        "contradiction_lens_route_projection",
        {key: value for key, value in values.items() if key != "projection_id"},
    )
    return values


def _rehash_observation(payload: dict) -> dict:
    values = dict(payload)
    values["observation_id"] = stable_id(
        "contradiction_lens_controlled_observation",
        {key: value for key, value in values.items() if key != "observation_id"},
    )
    return values


def _rehash_coverage(payload: dict) -> dict:
    values = dict(payload)
    values["receipt_id"] = stable_id(
        "contradiction_lens_resolution_evidence",
        {key: value for key, value in values.items() if key != "receipt_id"},
    )
    return values


def test_opt_in_lens_control_projects_actual_routes_and_grounds_only_lens() -> None:
    (
        kernel,
        obligation,
        _,
        _,
        lenses,
        runtime,
        context,
        run,
    ) = _run(6501, "contradiction-lens:controlled")

    assert run.controlled_context == context
    assert context.functional_context == run.probe_run.probe.functional_context
    assert context.lens_fingerprint == lenses.fingerprint()
    assert context.lens_system().fingerprint() == lenses.fingerprint()
    assert context.active_evidence_refs
    assert context.active_governance_refs
    assert len(runtime.ledger.state.settlements) == 2
    for route, projection in zip(
        run.probe_run.functional_observation.claim_routes,
        run.lens_observation.route_projections,
        strict=True,
    ):
        assert projection.functional_route_ref == route.route_id
        assert projection.projected_claim_refs == route.treatment_routed_claim_refs
        assert projection.operator == LensOpcode.SELECT_ACTIVATED_REFS
        assert not projection.truth_selection_authority_enabled
    coverage = run.resolution_evidence
    assert coverage.grounded_requirements == (
        CONTRADICTION_LENS_GROUNDED_REQUIREMENTS
    )
    assert coverage.missing_requirements == CONTRADICTION_LENS_MISSING_REQUIREMENTS
    assert (
        ContradictionResolutionRequirement.ACTIVE_FAMILY_LOCAL_LENS
        in coverage.grounded_requirements
    )
    assert {
        ContradictionResolutionRequirement.DIMENSIONAL_SEPARATION,
        ContradictionResolutionRequirement.EXTERNAL_OUTCOME,
        ContradictionResolutionRequirement.INDEPENDENT_HELD_OUT_REPLICATION,
        ContradictionResolutionRequirement.PREDICTIVE_DISCRIMINATION,
        ContradictionResolutionRequirement.SOURCE_INDEPENDENCE,
    }.issubset(coverage.missing_requirements)
    assert coverage.protected_claim_refs == obligation.claim_refs
    assert not coverage.resolution_trial_ready
    assert not coverage.resolution_authority_enabled
    assert not coverage.canonical_commit_permitted


def test_context_requires_active_contradiction_family_binding() -> None:
    kernel, _, _, bundle = _prepared(6502)
    lenses = _lenses(
        kernel,
        bundle,
        family=ObligationFamily.DEPENDENCY_GAP,
    )

    with pytest.raises(
        ContradictionLensControlIntegrityError,
        match="exactly one active",
    ):
        ContradictionLensControlledContext.build(
            bundle,
            lenses,
            source_event_key="contradiction-lens:wrong-family",
        )


def test_context_requires_explicit_active_binding_evidence() -> None:
    kernel, _, _, bundle = _prepared(6503)
    lenses = _lenses(kernel, bundle, record_evidence=False)

    with pytest.raises(
        ContradictionLensControlIntegrityError,
        match="explicit evidence history",
    ):
        ContradictionLensControlledContext.build(
            bundle,
            lenses,
            source_event_key="contradiction-lens:no-evidence",
        )


def test_context_rejects_unavailable_dimensions_and_suspended_binding() -> None:
    kernel, _, _, bundle = _prepared(6504)
    unsupported = _lenses(
        kernel,
        bundle,
        operators=(LensOpcode.SELECT_EDGE_TYPES,),
    )
    with pytest.raises(
        ContradictionLensControlIntegrityError,
        match="activated-reference",
    ):
        ContradictionLensControlledContext.build(
            bundle,
            unsupported,
            source_event_key="contradiction-lens:unsupported",
        )

    suspended = _lenses(kernel, bundle, record_evidence=False, tripwire=1)
    binding = suspended.active_binding(ObligationFamily.CONTRADICTION).binding
    suspended.record_evidence(
        binding_id=binding.binding_id,
        result=LensEvidenceResult.OVER_SMOOTHING,
        independent_consequence_refs=(bundle.evidence_receipt.receipt_id,),
        source_event_key="contradiction-lens:suspend",
        cycle=kernel.state.cycle,
    )
    with pytest.raises(
        ContradictionLensControlIntegrityError,
        match="exactly one active",
    ):
        ContradictionLensControlledContext.build(
            bundle,
            suspended,
            source_event_key="contradiction-lens:suspended",
        )


def test_changed_sidecar_after_preregistration_fails_before_simulation() -> None:
    kernel, _, _, bundle = _prepared(6505)
    lenses = _lenses(kernel, bundle)
    context = ContradictionLensControlledContext.build(
        bundle,
        lenses,
        source_event_key="contradiction-lens:stale",
    )
    lenses.register_definition(
        operators=(LensOpcode.SELECT_ACTION,),
        provenance_refs=("later-unrelated-definition",),
    )
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()
    lens_before = lenses.fingerprint()

    with pytest.raises(
        ContradictionLensControlIntegrityError,
        match="stale or substituted",
    ):
        ContradictionLensControlledProbeRunner().run(
            kernel,
            runtime,
            lenses,
            bundle=bundle,
            controlled_context=context,
            source_event_key="contradiction-lens:stale",
        )
    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before
    assert lenses.fingerprint() == lens_before


def test_archive_replay_reconstructs_exact_lens_control(tmp_path: Path) -> None:
    (
        kernel,
        _,
        allocation,
        bundle,
        lenses,
        runtime,
        context,
        first,
    ) = _run(6506, "contradiction-lens:archive")
    path = tmp_path / "contradiction-lens.vob"
    save_experiment_archive(
        path,
        kernel,
        runtime.ledger,
        lens_system=lenses,
    )

    restored = load_experiment_archive_bundle(path)
    assert restored.lens_system is not None
    restored_bundle = ContradictionHypothesisProtocol().generate(
        restored.kernel,
        obligation_id=bundle.obligation_id,
        attention_allocation_id=allocation.allocation_id,
    )
    restored_context = ContradictionLensControlledContext.build(
        restored_bundle,
        restored.lens_system,
        source_event_key="contradiction-lens:archive",
    )
    canonical_before = restored.kernel.fingerprint()
    simulation_before = restored.simulation_ledger.fingerprint()
    lens_before = restored.lens_system.fingerprint()
    replay = ContradictionLensControlledProbeRunner().run(
        restored.kernel,
        CounterfactualRuntime(restored.simulation_ledger),
        restored.lens_system,
        bundle=restored_bundle,
        controlled_context=restored_context,
        source_event_key="contradiction-lens:archive",
    )

    assert replay.replayed
    assert restored_context == context
    assert replay.lens_observation == first.lens_observation
    assert replay.resolution_evidence == first.resolution_evidence
    assert restored.kernel.fingerprint() == canonical_before
    assert restored.simulation_ledger.fingerprint() == simulation_before
    assert restored.lens_system.fingerprint() == lens_before


def test_observer_rejects_foreign_simulation_ledger() -> None:
    kernel, _, _, bundle, lenses, _, context, run = _run(
        6507,
        "contradiction-lens:foreign-ledger",
    )
    foreign = CounterfactualRuntime().ledger
    foreign_before = foreign.fingerprint()

    with pytest.raises(ContradictionLensControlIntegrityError):
        ContradictionLensControlledObserver().observe(
            kernel,
            foreign,
            lenses,
            bundle=bundle,
            controlled_context=context,
            probe_run=run.probe_run,
        )
    assert foreign.fingerprint() == foreign_before


def test_fully_rehashed_projection_cannot_replace_actual_route() -> None:
    _, _, _, _, _, _, _, run = _run(
        6508,
        "contradiction-lens:route-tamper",
    )
    payload = run.lens_observation.model_dump(mode="json")
    projection = dict(payload["route_projections"][0])
    projection["projected_claim_refs"] = ["forged-claim"]
    projection["equivalence_signature"] = stable_id(
        "contradiction_lens_route_equivalence",
        projection["projection_version"],
        projection["definition_ref"],
        projection["operator"],
        ("forged-claim",),
    )
    payload["route_projections"][0] = _rehash_projection(projection)

    with pytest.raises(ValueError, match="route projections were altered"):
        ContradictionLensControlledObservation.model_validate(
            _rehash_observation(payload)
        )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("missing_requirements", (), "hid or invented"),
        ("resolution_trial_ready", True, "cannot claim truth or resolution"),
        ("resolution_authority_enabled", True, "cannot claim truth or resolution"),
    ),
)
def test_fully_rehashed_coverage_cannot_hide_gaps_or_grant_authority(
    field: str,
    value: object,
    match: str,
) -> None:
    _, _, _, _, _, _, _, run = _run(
        6509,
        "contradiction-lens:coverage-tamper",
    )
    payload = run.resolution_evidence.model_dump(mode="json")
    payload[field] = value

    with pytest.raises(ValueError, match=match):
        ContradictionLensResolutionEvidenceReceipt.model_validate(
            _rehash_coverage(payload)
        )


def test_observer_failure_cannot_publish_either_simulation_arm() -> None:
    kernel, _, _, bundle = _prepared(6510)
    lenses = _lenses(kernel, bundle)
    context = ContradictionLensControlledContext.build(
        bundle,
        lenses,
        source_event_key="contradiction-lens:atomic-failure",
    )
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()
    lens_before = lenses.fingerprint()

    class FailingObserver:
        def observe(self, *args, **kwargs):
            raise ContradictionLensControlIntegrityError(
                "injected Lens-control observer failure"
            )

    with pytest.raises(
        ContradictionLensControlIntegrityError,
        match="injected Lens-control observer failure",
    ):
        ContradictionLensControlledProbeRunner(observer=FailingObserver()).run(
            kernel,
            runtime,
            lenses,
            bundle=bundle,
            controlled_context=context,
            source_event_key="contradiction-lens:atomic-failure",
        )
    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before
    assert lenses.fingerprint() == lens_before
