from __future__ import annotations

import hashlib

import pytest

from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    RelationProposal,
    VerdantKernel,
)
from verdant_obligations import (
    AttentionBidInput,
    AttentionPortfolio,
    CounterfactualPatch,
    CounterfactualPlan,
    CounterfactualRuntime,
    DependencyGapDetector,
    DependencyGapHypothesisGenerator,
    MatchedCounterfactualObserver,
    OperationalProbeIntegrityError,
    OverlayAccessEffect,
    OverlayOperationalProbe,
    OverlayOperationalProbeObservation,
    SimulationDisposition,
    SimulationLedger,
    StructuralTraceEffect,
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


def _fixture():
    kernel = VerdantKernel(seed=7601, state_dim=16, run_label="operational-probe")
    kernel.apply_experience(
        _experience(
            "operational-dependency",
            relations=(
                RelationProposal(
                    source_label="stabilize loop",
                    target_label="pressure input",
                    relation_type="requires",
                    confidence=0.9,
                ),
            ),
        )
    )
    kernel.apply_experience(
        _experience(
            "operational-route",
            relations=(
                RelationProposal(
                    source_label="pressure input",
                    target_label="grounded reading",
                    relation_type="routes_to",
                    confidence=0.9,
                ),
            ),
        )
    )
    kernel.apply_experience(
        _experience(
            "operational-grounding",
            labels=("grounded reading",),
            evidence_kind=EvidenceKind.OUTCOME,
        )
    )
    obligation = DependencyGapDetector().detect_and_record(kernel).mutations[0].obligation
    hypothesis = next(
        item
        for item in DependencyGapHypothesisGenerator().generate(
            kernel, obligation.kernel_id
        )
        if item.patches
    )
    decision = AttentionPortfolio().decide(
        kernel,
        (
            AttentionBidInput(
                obligation_id=obligation.kernel_id,
                action_operator="overlay_operational_probe",
                requested_budget=0.05,
                estimated_cost=0.02,
                expected_gain=0.7,
                uncertainty=0.8,
                urgency=0.5,
                novelty=0.8,
                metric_provenance_refs=hypothesis.provenance_refs,
                generator_version=hypothesis.grammar_version,
            ),
        ),
        source_event_key="attention:overlay-operational-probe",
    ).decision
    return kernel, hypothesis, decision.allocations[0].allocation_id


def _run_pair(kernel, hypothesis, allocation_id, patch, *, key):
    common = {
        "operator_version": hypothesis.grammar_version,
        "requested_budget": 0.02,
        "consumed_budget": 0.01,
        "patches": (patch,),
        "disposition": SimulationDisposition.DISCARDED,
        "result_refs": (hypothesis.hypothesis_id,),
    }
    baseline_plan = CounterfactualPlan.build(
        source_event_key=f"{key}:baseline",
        apply_patch_count=0,
        **common,
    )
    treatment_plan = CounterfactualPlan.build(
        source_event_key=f"{key}:treatment",
        apply_patch_count=1,
        **common,
    )
    runtime = CounterfactualRuntime()
    baseline = runtime.execute(
        kernel,
        allocation_id=allocation_id,
        plan=baseline_plan,
    )
    treatment = runtime.execute(
        kernel,
        allocation_id=allocation_id,
        plan=treatment_plan,
    )
    structural = MatchedCounterfactualObserver().observe(
        kernel,
        runtime.ledger,
        hypothesis_ref=hypothesis.hypothesis_id,
        baseline_plan=baseline_plan,
        baseline_result=baseline,
        treatment_plan=treatment_plan,
        treatment_result=treatment,
    )
    return (
        runtime,
        baseline_plan,
        treatment_plan,
        baseline,
        treatment,
        structural,
    )


def _observe(kernel, hypothesis, pair):
    runtime, baseline_plan, treatment_plan, baseline, treatment, structural = pair
    return OverlayOperationalProbe().observe(
        kernel,
        runtime.ledger,
        hypothesis_ref=hypothesis.hypothesis_id,
        baseline_plan=baseline_plan,
        baseline_result=baseline,
        treatment_plan=treatment_plan,
        treatment_result=treatment,
        structural_observation=structural,
    )


def test_probe_retrieves_canonical_evidence_not_patch_claims() -> None:
    kernel, hypothesis, allocation_id = _fixture()
    patch_value = dict(hypothesis.patches[0].value or {})
    patch_value["evidence_refs"] = ("evidence:forged-label",)
    patch = CounterfactualPatch.upsert(
        "relations",
        hypothesis.patches[0].record_key,
        patch_value,
    )
    canonical_before = kernel.fingerprint()
    observation = _observe(
        kernel,
        hypothesis,
        _run_pair(
            kernel,
            hypothesis,
            allocation_id,
            patch,
            key="operational-probe:ignore-patch-evidence",
        ),
    )

    target_ref = str(patch_value["target_concept_id"])
    actual = tuple(
        sorted(
            ref
            for ref in kernel.state.concepts[target_ref].evidence_refs
            if kernel.state.evidence[ref].kind
            in {EvidenceKind.ACTION, EvidenceKind.OUTCOME}
        )
    )
    assert observation.effect == OverlayAccessEffect.ACCESS_GAIN
    assert observation.baseline.retrieved_evidence_refs == ()
    assert observation.treatment.retrieved_evidence_refs == actual
    assert "evidence:forged-label" not in observation.newly_retrieved_evidence_refs
    assert observation.treatment.traversed_relation_refs == (patch.record_key,)
    assert kernel.fingerprint() == canonical_before


def test_structural_delta_without_probe_grammar_is_a_valid_null() -> None:
    kernel, hypothesis, allocation_id = _fixture()
    patch_value = dict(hypothesis.patches[0].value or {})
    patch_value["relation_type"] = "cosmetic_counterfactual_edge"
    patch = CounterfactualPatch.upsert(
        "relations",
        "counterfactual:cosmetic-only",
        patch_value,
    )
    pair = _run_pair(
        kernel,
        hypothesis,
        allocation_id,
        patch,
        key="operational-probe:structural-null",
    )
    observation = _observe(kernel, hypothesis, pair)

    assert pair[-1].effect == StructuralTraceEffect.ADDITIVE_OVERLAY_EFFECT
    assert observation.effect == OverlayAccessEffect.VALID_NULL
    assert observation.baseline.retrieved_evidence_refs == ()
    assert observation.treatment.retrieved_evidence_refs == ()
    assert observation.treatment.inspected_relation_refs == ()
    assert not observation.path_changed


def test_probe_rejects_foreign_ledger_and_noncanonical_target() -> None:
    kernel, hypothesis, allocation_id = _fixture()
    pair = _run_pair(
        kernel,
        hypothesis,
        allocation_id,
        hypothesis.patches[0],
        key="operational-probe:foreign-ledger",
    )
    _, baseline_plan, treatment_plan, baseline, treatment, structural = pair
    with pytest.raises(OperationalProbeIntegrityError):
        OverlayOperationalProbe().observe(
            kernel,
            SimulationLedger(),
            hypothesis_ref=hypothesis.hypothesis_id,
            baseline_plan=baseline_plan,
            baseline_result=baseline,
            treatment_plan=treatment_plan,
            treatment_result=treatment,
            structural_observation=structural,
        )

    patch_value = dict(hypothesis.patches[0].value or {})
    patch_value["target_concept_id"] = "concept:noncanonical"
    bad_patch = CounterfactualPatch.upsert(
        "relations",
        "counterfactual:noncanonical-target",
        patch_value,
    )
    bad_pair = _run_pair(
        kernel,
        hypothesis,
        allocation_id,
        bad_patch,
        key="operational-probe:noncanonical-target",
    )
    with pytest.raises(
        OperationalProbeIntegrityError,
        match="escaped canonical concepts",
    ):
        _observe(kernel, hypothesis, bad_pair)


@pytest.mark.parametrize(
    "authority_field",
    (
        "workspace_admission_observed",
        "outgoing_action_observed",
        "canonical_dependency_path_established",
    ),
)
def test_probe_observation_cannot_forge_downstream_authority(
    authority_field: str,
) -> None:
    kernel, hypothesis, allocation_id = _fixture()
    observation = _observe(
        kernel,
        hypothesis,
        _run_pair(
            kernel,
            hypothesis,
            allocation_id,
            hypothesis.patches[0],
            key=f"operational-probe:authority:{authority_field}",
        ),
    ).treatment
    payload = observation.model_dump(mode="python")
    payload[authority_field] = True

    with pytest.raises(ValueError, match="authority boundary"):
        OverlayOperationalProbeObservation.model_validate(payload)
