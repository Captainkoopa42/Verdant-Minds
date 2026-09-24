from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from verdant_kernel import (
    ExperienceCommand,
    IdentityAmbiguityObligationKernel,
    KernelInvariantError,
    ObjectObservationInput,
    ObjectObservationKind,
    ObligationEventType,
    ObligationFamily,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_objects import VerdantObjectPipeline
from verdant_obligations import (
    AttentionBidInput,
    AttentionPortfolio,
    IdentityAmbiguityDetectionPolicy,
    IdentityAmbiguityDetector,
    derive_obligation_view,
)


def _visible(
    kernel: VerdantKernel,
    pipeline: VerdantObjectPipeline,
    *,
    key: str,
    episode: str,
    frame: int,
    appearance: tuple[float, ...],
):
    result = kernel.apply_experience(
        ExperienceCommand(
            event_key=key,
            source_ref=f"identity-sensor:{key}",
            modality="vision_native",
            payload_sha256=hashlib.sha256(key.encode()).hexdigest(),
            feature_vector=appearance,
        )
    )
    return pipeline.observe(
        kernel,
        ObjectObservationInput(
            episode_id=episode,
            frame_index=frame,
            evidence_ref=result.observation_evidence_id,
            modality="vision_native",
            kind=ObjectObservationKind.VISIBLE,
            appearance_features=appearance,
            position=(0.0, 0.0),
            motion=(0.1, 0.0),
            metadata={"human_identity_label": None},
        ),
    )


def _ambiguity(
    kernel: VerdantKernel,
    *,
    stem: str = "a",
    appearance: tuple[float, ...] = (0.2, 0.4, 0.6, 0.8),
) -> str:
    pipeline = VerdantObjectPipeline()
    _visible(
        kernel,
        pipeline,
        key=f"{stem}-first",
        episode=stem,
        frame=0,
        appearance=appearance,
    )
    _visible(
        kernel,
        pipeline,
        key=f"{stem}-second",
        episode=stem,
        frame=0,
        appearance=appearance,
    )
    result = _visible(
        kernel,
        pipeline,
        key=f"{stem}-ambiguous",
        episode=stem,
        frame=1,
        appearance=appearance,
    )
    return result.event.candidate_id


def test_native_candidate_competition_becomes_identity_obligation() -> None:
    kernel = VerdantKernel(seed=6301, state_dim=16, run_label="identity-anchor")
    ambiguous_id = _ambiguity(kernel)
    detector = IdentityAmbiguityDetector()
    before = kernel.fingerprint()
    inspected, candidates = detector.inspect(kernel)
    assert kernel.fingerprint() == before
    assert ambiguous_id in inspected
    assert len(candidates) == 1

    mutation = detector.detect_and_record(kernel).mutations[0]
    obligation = mutation.obligation
    native = kernel.state.object_candidates[ambiguous_id]
    assert isinstance(obligation, IdentityAmbiguityObligationKernel)
    assert obligation.family == ObligationFamily.IDENTITY_AMBIGUITY
    assert obligation.ambiguous_candidate_ref == ambiguous_id
    assert obligation.competing_candidate_refs == native.competing_candidate_ids
    assert set(native.evidence_refs).issubset(obligation.canonical_triggering_refs)
    assert derive_obligation_view(kernel, obligation.kernel_id).current_status.value == "Open"


def test_unchanged_identity_detection_is_zero_cost_replay() -> None:
    kernel = VerdantKernel(seed=6302, state_dim=16, run_label="identity-replay")
    _ambiguity(kernel)
    detector = IdentityAmbiguityDetector()
    first = detector.detect_and_record(kernel).mutations[0]
    cycle = kernel.state.cycle
    fingerprint = kernel.fingerprint()
    replay = detector.detect_and_record(kernel).mutations[0]
    assert replay.replayed
    assert replay.obligation.kernel_id == first.obligation.kernel_id
    assert kernel.state.cycle == cycle
    assert kernel.fingerprint() == fingerprint


def test_policy_revision_retriggers_same_identity_question() -> None:
    kernel = VerdantKernel(seed=6303, state_dim=16, run_label="identity-policy")
    _ambiguity(kernel)
    first = IdentityAmbiguityDetector().detect_and_record(kernel).mutations[0]
    revised = IdentityAmbiguityDetector(
        IdentityAmbiguityDetectionPolicy(
            policy_version="identity_ambiguity_detector_test_v2",
            minimum_competing_candidates=2,
        )
    ).detect_and_record(kernel).mutations[0]
    assert revised.obligation.kernel_id == first.obligation.kernel_id
    events = [
        event for event in kernel.state.obligation_history
        if event.obligation_id == first.obligation.kernel_id
    ]
    assert [event.event_type for event in events] == [
        ObligationEventType.CREATED,
        ObligationEventType.RETRIGGERED,
    ]


def test_noncontested_tracking_candidate_does_not_create_obligation() -> None:
    kernel = VerdantKernel(seed=6304, state_dim=16, run_label="identity-negative")
    _visible(
        kernel,
        VerdantObjectPipeline(),
        key="single",
        episode="single",
        frame=0,
        appearance=(0.1, 0.3, 0.5, 0.7),
    )
    report = IdentityAmbiguityDetector().detect_and_record(kernel)
    assert len(report.inspected_candidate_ids) == 1
    assert report.candidates == ()
    assert report.mutations == ()


def test_independent_ambiguities_do_not_overmerge() -> None:
    kernel = VerdantKernel(seed=6305, state_dim=16, run_label="identity-scope")
    _ambiguity(kernel, stem="near", appearance=(0.1, 0.2, 0.3, 0.4))
    _ambiguity(kernel, stem="far", appearance=(5.0, 5.1, 5.2, 5.3))
    report = IdentityAmbiguityDetector().detect_and_record(kernel)
    assert len(report.mutations) == 2
    assert len({item.obligation.kernel_id for item in report.mutations}) == 2


def test_checkpoint_roundtrip_rebuilds_identity_view(tmp_path: Path) -> None:
    kernel = VerdantKernel(seed=6306, state_dim=16, run_label="identity-checkpoint")
    _ambiguity(kernel)
    obligation = IdentityAmbiguityDetector().detect_and_record(kernel).mutations[0].obligation
    expected = derive_obligation_view(kernel, obligation.kernel_id)
    checkpoint = tmp_path / "identity-ambiguity.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(checkpoint))
    assert restored.snapshot() == kernel.snapshot()
    assert derive_obligation_view(restored, obligation.kernel_id) == expected


def test_triggering_reference_suppression_fails_closed() -> None:
    kernel = VerdantKernel(seed=6307, state_dim=16, run_label="identity-tamper")
    _ambiguity(kernel)
    obligation = IdentityAmbiguityDetector().detect_and_record(kernel).mutations[0].obligation
    state = kernel.snapshot()
    removable = next(
        ref for ref in obligation.canonical_triggering_refs
        if ref.startswith("evidence_")
    )
    state.obligation_kernels[obligation.kernel_id] = obligation.model_copy(
        update={
            "canonical_triggering_refs": tuple(
                ref for ref in obligation.canonical_triggering_refs if ref != removable
            )
        }
    )
    with pytest.raises(KernelInvariantError, match="triggering refs"):
        VerdantKernel.from_state(state)


def test_attention_allocation_cannot_decide_identity() -> None:
    kernel = VerdantKernel(seed=6308, state_dim=16, run_label="identity-attention")
    _ambiguity(kernel)
    obligation = IdentityAmbiguityDetector().detect_and_record(kernel).mutations[0].obligation
    decision = AttentionPortfolio().decide(
        kernel,
        (
            AttentionBidInput(
                obligation_id=obligation.kernel_id,
                action_operator="bounded_identity_probe",
                requested_budget=0.10,
                estimated_cost=0.05,
                expected_gain=0.6,
                uncertainty=0.9,
                urgency=0.4,
                novelty=0.7,
                generator_version="identity-bid-test-v1",
            ),
        ),
        source_event_key="identity-attention-001",
    ).decision
    assert decision.allocations[0].obligation_id == obligation.kernel_id
    assert not decision.epistemic_authority_enabled
    assert derive_obligation_view(kernel, obligation.kernel_id).current_status.value == "Open"
