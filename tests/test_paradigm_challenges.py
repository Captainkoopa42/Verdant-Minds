from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from verdant_governance import VerdantGovernancePipeline
from verdant_kernel import (
    CouncilDisposition,
    ExperienceCommand,
    GovernanceProposalKind,
    ObligationEventType,
    RelationProposal,
    VerdantKernel,
)
from verdant_obligations import (
    AttentionBidInput,
    AttentionPortfolio,
    CounterfactualPlan,
    CounterfactualRuntime,
    DependencyGapDetectionPolicy,
    DependencyGapDetector,
    FailedPolicyDetectionPolicy,
    FailedPolicyDetector,
    OrthogonalFingerprintObservation,
    ParadigmAnomalySignal,
    ParadigmChallengeDisposition,
    ParadigmChallengeIntegrityError,
    ParadigmChallengeLane,
    ParadigmChallengeLedgerState,
    ParadigmShadowTrial,
)


SHARED_ASSUMPTION = "shared_representational_assumption_v1"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ParadigmFixture:
    kernel: VerdantKernel
    lane: ParadigmChallengeLane
    runtime: CounterfactualRuntime
    signals: tuple[ParadigmAnomalySignal, ...]
    allocations: dict[str, str]


def _denial(kernel: VerdantKernel, evidence_ref: str) -> None:
    governance = VerdantGovernancePipeline()
    proposal = governance.propose(
        kernel,
        proposal_kind=GovernanceProposalKind.ACT,
        operation="shared_assumption_actuation",
        action_class="high_risk_assumption_action",
        description="Exercise the shared assumption under a governed test.",
        evidence_refs=(evidence_ref,),
        relevance=1.0,
        urgency=0.8,
        novelty=0.2,
        predicted_information_gain=0.3,
        harm_risk=0.95,
        reversibility=0.10,
        safe_alternatives=("inspect_shared_assumption",),
    )
    report = governance.inspect(kernel, proposal)
    assert report.disposition == CouncilDisposition.DENY
    governance.commit(kernel, report)


def _fixture(*, shared_root: bool = False) -> ParadigmFixture:
    kernel = VerdantKernel(seed=6501, state_dim=16, run_label="paradigm-lane")
    dependency_root = "lineage:shared" if shared_root else "lineage:dependency"
    policy_root = "lineage:shared" if shared_root else "lineage:policy"
    kernel.apply_experience(
        ExperienceCommand(
            event_key="paradigm-dependency",
            source_ref=dependency_root,
            modality="structural_test",
            payload_sha256=_digest("paradigm-dependency"),
            feature_vector=(0.1, 0.2, 0.3),
            relation_proposals=(
                RelationProposal(
                    source_label="paradigm action",
                    target_label="missing paradigm input",
                    relation_type="requires",
                ),
            ),
        )
    )
    dependency = DependencyGapDetector().detect_and_record(kernel).mutations[0]
    dependency_retrigger = DependencyGapDetector(
        policy=DependencyGapDetectionPolicy(policy_version=SHARED_ASSUMPTION)
    ).detect_and_record(kernel).mutations[0]
    assert dependency_retrigger.event.event_type == ObligationEventType.RETRIGGERED

    evidence = kernel.apply_experience(
        ExperienceCommand(
            event_key="paradigm-policy-evidence",
            source_ref=policy_root,
            modality="governance_test",
            payload_sha256=_digest("paradigm-policy-evidence"),
            feature_vector=(0.4, 0.5, 0.6),
        )
    ).observation_evidence_id
    _denial(kernel, evidence)
    _denial(kernel, evidence)
    failed_policy = FailedPolicyDetector().detect_and_record(kernel).mutations[0]
    policy_retrigger = FailedPolicyDetector(
        FailedPolicyDetectionPolicy(policy_version=SHARED_ASSUMPTION)
    ).detect_and_record(kernel).mutations[0]
    assert policy_retrigger.event.event_type == ObligationEventType.RETRIGGERED

    signals = tuple(
        ParadigmAnomalySignal.build(
            obligation_id=mutation.obligation.kernel_id,
            obligation_family=mutation.obligation.family,
            history_event_id=mutation.event.event_id,
            target_assumption_ref=SHARED_ASSUMPTION,
            provenance_root=mutation.event.source_lineage_roots[0],
            evidence_refs=(mutation.event.triggering_refs[0],),
        )
        for mutation in (dependency_retrigger, policy_retrigger)
    )
    bids = tuple(
        AttentionBidInput(
            obligation_id=obligation_id,
            action_operator="paradigm_shadow_replay",
            requested_budget=0.15,
            estimated_cost=0.08,
            expected_gain=0.7,
            uncertainty=0.9,
            urgency=0.6,
            novelty=0.8,
            generator_version="paradigm-test-generator-v1",
        )
        for obligation_id in sorted(
            (dependency.obligation.kernel_id, failed_policy.obligation.kernel_id)
        )
    )
    decision = AttentionPortfolio().decide(
        kernel, bids, source_event_key="attention:paradigm"
    ).decision
    allocations = {
        item.obligation_id: item.allocation_id for item in decision.allocations
    }
    assert set(allocations) == {item.obligation_id for item in signals}
    return ParadigmFixture(
        kernel=kernel,
        lane=ParadigmChallengeLane(),
        runtime=CounterfactualRuntime(),
        signals=signals,
        allocations=allocations,
    )


def _open(fixture: ParadigmFixture):
    return fixture.lane.open(
        fixture.kernel,
        signals=fixture.signals,
        source_event_key="paradigm:open",
    )


def _trials(
    fixture: ParadigmFixture,
    challenge,
    *,
    preserved: bool = True,
    divergent: bool = False,
) -> tuple[ParadigmShadowTrial, ...]:
    trials = []
    for obligation_index, obligation_id in enumerate(
        sorted(item.obligation_id for item in fixture.signals)
    ):
        history = tuple(sorted(
            item.event_id for item in fixture.kernel.state.obligation_history
            if item.obligation_id == obligation_id
        ))
        for seed_index in range(2):
            seed = f"seed:{obligation_index}:{seed_index}"
            variant = "variant:paradigm-reframe-v1"
            result = fixture.runtime.execute(
                fixture.kernel,
                allocation_id=fixture.allocations[obligation_id],
                plan=CounterfactualPlan.build(
                    source_event_key=f"simulation:{obligation_index}:{seed_index}",
                    operator_version="paradigm-shadow-runtime-v1",
                    requested_budget=0.02,
                    consumed_budget=0.01,
                    result_refs=(challenge.challenge_id, variant, seed, *history),
                ),
            )
            fingerprint = _digest(f"orthogonal:{obligation_index}")
            trials.append(
                ParadigmShadowTrial.build(
                    challenge_id=challenge.challenge_id,
                    obligation_id=obligation_id,
                    seed_ref=seed,
                    proposed_variant_ref=variant,
                    simulation_settlement_id=result.settlement.settlement_id,
                    replayed_history_event_ids=history,
                    outcome_signature=(
                        f"outcome:{obligation_index}:{seed_index}"
                        if divergent
                        else f"outcome:{obligation_index}"
                    ),
                    improvement_observed=True,
                    evidence_preserved=preserved,
                    orthogonal_fingerprints=(
                        OrthogonalFingerprintObservation(
                            context_ref=f"unrelated:{obligation_index}",
                            before_fingerprint=fingerprint,
                            after_fingerprint=fingerprint,
                        ),
                    ),
                )
            )
    return tuple(trials)


def test_cross_family_independent_signals_open_shadow_only_challenge() -> None:
    fixture = _fixture()
    before = fixture.kernel.fingerprint()
    challenge = _open(fixture)
    assert fixture.kernel.fingerprint() == before
    assert challenge.shadow_only
    assert not challenge.canonical_mutation_permitted
    assert {item.obligation_family for item in challenge.signals} == {
        item.obligation_family for item in fixture.signals
    }


def test_single_family_cannot_trigger_paradigm_lane() -> None:
    fixture = _fixture()
    with pytest.raises(ParadigmChallengeIntegrityError, match="count|cross-family"):
        fixture.lane.open(
            fixture.kernel,
            signals=(fixture.signals[0],),
            source_event_key="paradigm:single-family",
        )


def test_dependent_provenance_cannot_masquerade_as_independent_anomalies() -> None:
    fixture = _fixture(shared_root=True)
    with pytest.raises(ParadigmChallengeIntegrityError, match="independent provenance"):
        _open(fixture)


def test_open_replay_is_exact_and_changed_request_is_rejected() -> None:
    fixture = _fixture()
    challenge = _open(fixture)
    assert _open(fixture) == challenge
    signal = fixture.signals[0]
    event = next(
        item for item in fixture.kernel.state.obligation_history
        if item.event_id == signal.history_event_id
    )
    alternate = next(ref for ref in event.triggering_refs if ref not in signal.evidence_refs)
    changed = ParadigmAnomalySignal.build(
        **signal.model_dump(mode="python", exclude={"signal_id", "evidence_refs"}),
        evidence_refs=(alternate,),
    )
    with pytest.raises(ParadigmChallengeIntegrityError, match="reused"):
        fixture.lane.open(
            fixture.kernel,
            signals=(changed, fixture.signals[1]),
            source_event_key="paradigm:open",
        )


def test_replicated_full_history_shadow_trial_supports_high_blast_challenge() -> None:
    fixture = _fixture()
    challenge = _open(fixture)
    before = fixture.kernel.fingerprint()
    trials = _trials(fixture, challenge)
    blast_radius = tuple(fixture.kernel.state.obligation_kernels)
    decision = fixture.lane.decide(
        fixture.kernel,
        challenge_id=challenge.challenge_id,
        trials=trials,
        simulation_ledger=fixture.runtime.ledger,
        blast_radius_obligation_ids=blast_radius,
        source_event_key="paradigm:decide",
    )
    assert decision.disposition == ParadigmChallengeDisposition.SHADOW_SUPPORTED
    assert decision.blast_radius_obligation_ids == tuple(sorted(blast_radius))
    assert not decision.promotion_authority_enabled
    assert not decision.canonical_mutation_permitted
    assert fixture.kernel.fingerprint() == before


def test_incomplete_history_replay_fails_closed() -> None:
    fixture = _fixture()
    challenge = _open(fixture)
    trials = list(_trials(fixture, challenge))
    original = trials[0]
    trials[0] = ParadigmShadowTrial.build(
        **original.model_dump(
            mode="python", exclude={"trial_id", "replayed_history_event_ids"}
        ),
        replayed_history_event_ids=original.replayed_history_event_ids[1:],
    )
    with pytest.raises(ParadigmChallengeIntegrityError, match="full immutable history"):
        fixture.lane.decide(
            fixture.kernel,
            challenge_id=challenge.challenge_id,
            trials=trials,
            simulation_ledger=fixture.runtime.ledger,
            blast_radius_obligation_ids=(),
            source_event_key="paradigm:incomplete-history",
        )


def test_evidence_suppression_rejects_without_promoting_variant() -> None:
    fixture = _fixture()
    challenge = _open(fixture)
    decision = fixture.lane.decide(
        fixture.kernel,
        challenge_id=challenge.challenge_id,
        trials=_trials(fixture, challenge, preserved=False),
        simulation_ledger=fixture.runtime.ledger,
        blast_radius_obligation_ids=tuple(fixture.kernel.state.obligation_kernels),
        source_event_key="paradigm:suppression",
    )
    assert decision.disposition == ParadigmChallengeDisposition.SHADOW_REJECTED
    assert decision.rejection_codes == ("evidence_not_preserved",)
    assert not decision.promotion_authority_enabled


def test_cross_seed_outcome_instability_rejects_noise() -> None:
    fixture = _fixture()
    challenge = _open(fixture)
    decision = fixture.lane.decide(
        fixture.kernel,
        challenge_id=challenge.challenge_id,
        trials=_trials(fixture, challenge, divergent=True),
        simulation_ledger=fixture.runtime.ledger,
        blast_radius_obligation_ids=(),
        source_event_key="paradigm:noise",
    )
    assert decision.disposition == ParadigmChallengeDisposition.SHADOW_REJECTED
    assert "outcome_not_replicated" in decision.rejection_codes


def test_sidecar_roundtrip_and_sequence_tamper_detection() -> None:
    fixture = _fixture()
    challenge = _open(fixture)
    fixture.lane.decide(
        fixture.kernel,
        challenge_id=challenge.challenge_id,
        trials=_trials(fixture, challenge),
        simulation_ledger=fixture.runtime.ledger,
        blast_radius_obligation_ids=(),
        source_event_key="paradigm:roundtrip",
    )
    restored = ParadigmChallengeLane.from_snapshot(fixture.lane.snapshot())
    assert restored.snapshot() == fixture.lane.snapshot()
    assert restored.fingerprint() == fixture.lane.fingerprint()
    payload = fixture.lane.snapshot()
    payload["challenges"][0]["sequence"] = 2
    with pytest.raises(ValidationError):
        ParadigmChallengeLedgerState.model_validate(payload)
