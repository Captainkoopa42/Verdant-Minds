from __future__ import annotations

from pathlib import Path

import pytest

from verdant_claims import ClaimLearningPipeline
from verdant_kernel import (
    ClaimPolarity,
    ClaimSourceClass,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_obligations import (
    CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION,
    CONTRADICTION_PROVENANCE_ACTION_OPERATOR,
    AttentionBidInput,
    AttentionPortfolio,
    ContradictionEvidenceReceipt,
    ContradictionHypothesis,
    ContradictionHypothesisBundle,
    ContradictionHypothesisIntegrityError,
    ContradictionHypothesisKind,
    ContradictionHypothesisProtocol,
    ContradictionObligationDetector,
)


def _claim(
    kernel: VerdantKernel,
    *,
    event_key: str,
    subject: str,
    polarity: ClaimPolarity,
    source: ClaimSourceClass,
) -> None:
    ClaimLearningPipeline().record_claim(
        kernel,
        event_key=event_key,
        native_description=f"Controlled evidence {event_key}.",
        subject_label=subject,
        predicate="has_property",
        object_label="open",
        polarity=polarity,
        source_class=source,
    )


def _contradict(
    kernel: VerdantKernel,
    stem: str = "door",
    *,
    affirmed_source: ClaimSourceClass = ClaimSourceClass.DIRECT_OBSERVATION,
    negated_source: ClaimSourceClass = ClaimSourceClass.HUMAN_TESTIMONY,
) -> None:
    _claim(
        kernel,
        event_key=f"{stem}-affirmed",
        subject=stem,
        polarity=ClaimPolarity.AFFIRMED,
        source=affirmed_source,
    )
    _claim(
        kernel,
        event_key=f"{stem}-negated",
        subject=stem,
        polarity=ClaimPolarity.NEGATED,
        source=negated_source,
    )


def _authorize(
    kernel: VerdantKernel,
    obligation_ids: tuple[str, ...],
    *,
    action_operator: str = CONTRADICTION_PROVENANCE_ACTION_OPERATOR,
    generator_version: str = CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION,
    requested_budget: float = 0.05,
    source_event_key: str = "contradiction-hypothesis-attention",
):
    latest_events = {
        obligation_id: next(
            item
            for item in reversed(kernel.state.obligation_history)
            if item.obligation_id == obligation_id
        )
        for obligation_id in obligation_ids
    }
    decision = AttentionPortfolio().decide(
        kernel,
        tuple(
            AttentionBidInput(
                obligation_id=obligation_id,
                action_operator=action_operator,
                requested_budget=requested_budget,
                estimated_cost=requested_budget,
                expected_gain=0.55,
                uncertainty=0.85,
                urgency=0.50,
                novelty=0.75,
                metric_provenance_refs=latest_events[
                    obligation_id
                ].triggering_refs,
                generator_version=generator_version,
            )
            for obligation_id in sorted(obligation_ids)
        ),
        source_event_key=source_event_key,
    ).decision
    return {
        item.obligation_id: item
        for item in decision.allocations
    }


def _prepared(
    *,
    seed: int = 6301,
    action_operator: str = CONTRADICTION_PROVENANCE_ACTION_OPERATOR,
    generator_version: str = CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION,
    requested_budget: float = 0.05,
):
    kernel = VerdantKernel(
        seed=seed,
        state_dim=16,
        run_label=f"contradiction-hypothesis-{seed}",
    )
    _contradict(kernel)
    obligation = ContradictionObligationDetector().detect_and_record(
        kernel
    ).mutations[0].obligation
    allocations = _authorize(
        kernel,
        (obligation.kernel_id,),
        action_operator=action_operator,
        generator_version=generator_version,
        requested_budget=requested_budget,
        source_event_key=f"contradiction-hypothesis-attention-{seed}",
    )
    return kernel, obligation, allocations[obligation.kernel_id]


def test_protocol_preserves_both_claims_and_mandatory_alternatives() -> None:
    kernel, obligation, allocation = _prepared()
    protocol = ContradictionHypothesisProtocol()
    before = kernel.fingerprint()

    bundle = protocol.generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )

    assert kernel.fingerprint() == before
    assert protocol.validate(kernel, bundle) == bundle
    receipt = bundle.evidence_receipt
    contradiction = kernel.state.contradictions[obligation.contradiction_ref]
    assert receipt.protected_claim_refs == obligation.claim_refs
    assert receipt.protected_evidence_refs == tuple(
        sorted(contradiction.evidence_refs)
    )
    assert {item.kind for item in bundle.hypotheses} == set(
        ContradictionHypothesisKind
    )
    assert bundle.selected_hypothesis_ref is None
    assert not bundle.truth_selection_authority_enabled
    assert not bundle.resolution_authority_enabled
    assert not bundle.canonical_commit_permitted
    for side in receipt.claim_sides:
        other = next(
            item for item in receipt.claim_sides if item.claim_ref != side.claim_ref
        )
        assert side.support_evidence_refs == other.refutation_evidence_refs
    for hypothesis in bundle.hypotheses:
        assert hypothesis.claim_refs == obligation.claim_refs
        assert hypothesis.protected_evidence_refs == receipt.protected_evidence_refs
        assert hypothesis.preferred_claim_ref is None
        assert not hypothesis.evidence_suppression_permitted


def test_provenance_partition_keeps_evidence_and_source_dimensions_separate() -> None:
    kernel, obligation, allocation = _prepared(seed=6302)
    receipt = ContradictionHypothesisProtocol().generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    ).evidence_receipt

    assert receipt.shared_support_evidence_refs == ()
    assert receipt.symmetric_difference_evidence_refs == (
        receipt.protected_evidence_refs
    )
    assert set(receipt.symmetric_difference_source_roots) == {
        "controlled_direct_observation:observation",
        "controlled_human_testimony:testimony",
    }

    same_source = VerdantKernel(
        seed=6303,
        state_dim=16,
        run_label="contradiction-shared-source",
    )
    _contradict(
        same_source,
        affirmed_source=ClaimSourceClass.DIRECT_OBSERVATION,
        negated_source=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    same_obligation = ContradictionObligationDetector().detect_and_record(
        same_source
    ).mutations[0].obligation
    same_allocation = _authorize(
        same_source,
        (same_obligation.kernel_id,),
        source_event_key="shared-source-attention",
    )[same_obligation.kernel_id]
    same_receipt = ContradictionHypothesisProtocol().generate(
        same_source,
        obligation_id=same_obligation.kernel_id,
        attention_allocation_id=same_allocation.allocation_id,
    ).evidence_receipt
    assert same_receipt.symmetric_difference_evidence_refs
    assert same_receipt.symmetric_difference_source_roots == ()
    assert same_receipt.shared_support_source_roots == (
        "controlled_direct_observation:observation",
    )


def test_checkpoint_and_mapping_order_replay_exact_bundle(tmp_path: Path) -> None:
    kernel, obligation, allocation = _prepared(seed=6304)
    protocol = ContradictionHypothesisProtocol()
    expected = protocol.generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )
    checkpoint = tmp_path / "contradiction-hypothesis.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(checkpoint))
    state = restored.snapshot()
    state.claims = dict(reversed(tuple(state.claims.items())))
    state.evidence = dict(reversed(tuple(state.evidence.items())))
    reordered = VerdantKernel.from_state(state)

    assert protocol.generate(
        reordered,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    ) == expected
    assert ContradictionHypothesisBundle.model_validate(
        expected.model_dump(mode="json")
    ) == expected


@pytest.mark.parametrize(
    ("action_operator", "generator_version"),
    (
        ("generic_probe", CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION),
        (CONTRADICTION_PROVENANCE_ACTION_OPERATOR, "foreign-generator-v1"),
    ),
)
def test_wrong_attention_authorization_fails_closed(
    action_operator: str,
    generator_version: str,
) -> None:
    kernel, obligation, allocation = _prepared(
        seed=6305 if action_operator == "generic_probe" else 6306,
        action_operator=action_operator,
        generator_version=generator_version,
    )
    with pytest.raises(
        ContradictionHypothesisIntegrityError,
        match="does not authorize",
    ):
        ContradictionHypothesisProtocol().generate(
            kernel,
            obligation_id=obligation.kernel_id,
            attention_allocation_id=allocation.allocation_id,
        )


def test_unknown_and_underfunded_allocations_fail_closed() -> None:
    kernel, obligation, _ = _prepared(seed=6307)
    with pytest.raises(
        ContradictionHypothesisIntegrityError,
        match="one canonical Attention allocation",
    ):
        ContradictionHypothesisProtocol().generate(
            kernel,
            obligation_id=obligation.kernel_id,
            attention_allocation_id="forged-allocation",
        )

    small_kernel, small_obligation, small_allocation = _prepared(
        seed=6308,
        requested_budget=0.01,
    )
    with pytest.raises(
        ContradictionHypothesisIntegrityError,
        match="below the contradiction protocol minimum",
    ):
        ContradictionHypothesisProtocol().generate(
            small_kernel,
            obligation_id=small_obligation.kernel_id,
            attention_allocation_id=small_allocation.allocation_id,
        )


def test_attention_bid_cannot_suppress_triggering_evidence() -> None:
    kernel = VerdantKernel(
        seed=6309,
        state_dim=16,
        run_label="contradiction-attention-suppression",
    )
    _contradict(kernel)
    obligation = ContradictionObligationDetector().detect_and_record(
        kernel
    ).mutations[0].obligation
    decision = AttentionPortfolio().decide(
        kernel,
        (
            AttentionBidInput(
                obligation_id=obligation.kernel_id,
                action_operator=CONTRADICTION_PROVENANCE_ACTION_OPERATOR,
                requested_budget=0.05,
                estimated_cost=0.05,
                expected_gain=0.5,
                uncertainty=0.8,
                urgency=0.5,
                novelty=0.7,
                metric_provenance_refs=(),
                generator_version=CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION,
            ),
        ),
        source_event_key="suppressed-attention-evidence",
    ).decision
    with pytest.raises(
        ContradictionHypothesisIntegrityError,
        match="suppressed current contradiction triggering evidence",
    ):
        ContradictionHypothesisProtocol().generate(
            kernel,
            obligation_id=obligation.kernel_id,
            attention_allocation_id=decision.allocations[0].allocation_id,
        )


def test_retrigger_invalidates_stale_attention_basis() -> None:
    kernel, obligation, allocation = _prepared(seed=6310)
    protocol = ContradictionHypothesisProtocol()
    protocol.generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )

    _claim(
        kernel,
        event_key="door-affirmed-independent",
        subject="door",
        polarity=ClaimPolarity.AFFIRMED,
        source=ClaimSourceClass.EXTERNAL_TESTIMONY,
    )
    retrigger = ContradictionObligationDetector().detect_and_record(
        kernel
    ).mutations[0]
    assert not retrigger.replayed
    with pytest.raises(
        ContradictionHypothesisIntegrityError,
        match="stale relative to contradiction history",
    ):
        protocol.generate(
            kernel,
            obligation_id=obligation.kernel_id,
            attention_allocation_id=allocation.allocation_id,
        )


def test_foreign_obligation_allocation_cannot_cross_contaminate_bundle() -> None:
    kernel = VerdantKernel(
        seed=6311,
        state_dim=16,
        run_label="contradiction-cross-scope",
    )
    _contradict(kernel, "door")
    _contradict(kernel, "window")
    obligations = tuple(
        item.obligation
        for item in ContradictionObligationDetector().detect_and_record(
            kernel
        ).mutations
    )
    allocations = _authorize(
        kernel,
        tuple(item.kernel_id for item in obligations),
        source_event_key="cross-scope-attention",
    )
    first, second = obligations
    assert set(allocations) == {first.kernel_id, second.kernel_id}
    with pytest.raises(
        ContradictionHypothesisIntegrityError,
        match="belongs to another obligation",
    ):
        ContradictionHypothesisProtocol().generate(
            kernel,
            obligation_id=first.kernel_id,
            attention_allocation_id=allocations[second.kernel_id].allocation_id,
        )


def test_bundle_rejects_evidence_suppression_and_missing_counterweights() -> None:
    kernel, obligation, allocation = _prepared(seed=6312)
    bundle = ContradictionHypothesisProtocol().generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )
    receipt_payload = bundle.evidence_receipt.model_dump(
        mode="json",
        exclude={"receipt_id"},
    )
    receipt_payload["claim_sides"] = bundle.evidence_receipt.claim_sides
    receipt_payload["protected_evidence_refs"] = receipt_payload[
        "protected_evidence_refs"
    ][:-1]
    with pytest.raises(ValueError, match="suppressed canonical evidence"):
        ContradictionEvidenceReceipt.build(**receipt_payload)

    bundle_payload = bundle.model_dump(mode="json")
    bundle_payload["hypotheses"] = bundle_payload["hypotheses"][:-1]
    with pytest.raises(ValueError):
        ContradictionHypothesisBundle.model_validate(bundle_payload)


def test_hypothesis_cannot_encode_a_preferred_claim() -> None:
    kernel, obligation, allocation = _prepared(seed=6313)
    bundle = ContradictionHypothesisProtocol().generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )
    hypothesis = bundle.hypotheses[0]
    payload = hypothesis.model_dump(mode="json", exclude={"hypothesis_id"})
    payload["preferred_claim_ref"] = obligation.claim_refs[0]
    with pytest.raises(ValueError, match="cannot select a preferred claim"):
        ContradictionHypothesis.build(**payload)


def test_fully_rehashed_context_forgery_fails_canonical_validation() -> None:
    kernel, obligation, allocation = _prepared(seed=6314)
    protocol = ContradictionHypothesisProtocol()
    bundle = protocol.generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )
    receipt = bundle.evidence_receipt
    forged_context = "0" * 64
    forged_receipt = ContradictionEvidenceReceipt.build(
        obligation_id=receipt.obligation_id,
        obligation_event_ref=receipt.obligation_event_ref,
        contradiction_ref=receipt.contradiction_ref,
        claim_key=receipt.claim_key,
        claim_sides=receipt.claim_sides,
        protected_evidence_refs=receipt.protected_evidence_refs,
        attention_decision_ref=receipt.attention_decision_ref,
        attention_bid_ref=receipt.attention_bid_ref,
        attention_allocation_ref=receipt.attention_allocation_ref,
        authorized_budget=receipt.authorized_budget,
        context_snapshot_sha256=forged_context,
    )
    forged_provenance = tuple(
        sorted(
            {
                obligation.kernel_id,
                bundle.obligation_event_ref,
                bundle.attention_decision_ref,
                bundle.attention_bid_ref,
                bundle.attention_allocation_ref,
                forged_receipt.receipt_id,
                forged_receipt.contradiction_ref,
                *forged_receipt.protected_claim_refs,
                *forged_receipt.protected_evidence_refs,
            }
        )
    )
    forged_hypotheses = tuple(
        ContradictionHypothesis.build(
            obligation_id=obligation.kernel_id,
            contradiction_ref=forged_receipt.contradiction_ref,
            kind=kind,
            claim_refs=forged_receipt.protected_claim_refs,
            evidence_receipt_ref=forged_receipt.receipt_id,
            protected_evidence_refs=forged_receipt.protected_evidence_refs,
            candidate_discriminating_refs=(
                forged_receipt.symmetric_difference_evidence_refs
                if kind
                == ContradictionHypothesisKind.PROVENANCE_PARTITION_TEST
                else ()
            ),
            provenance_refs=forged_provenance,
        )
        for kind in ContradictionHypothesisKind
    )
    forged_bundle = ContradictionHypothesisBundle.build(
        obligation_id=obligation.kernel_id,
        obligation_event_ref=bundle.obligation_event_ref,
        attention_decision_ref=bundle.attention_decision_ref,
        attention_bid_ref=bundle.attention_bid_ref,
        attention_allocation_ref=bundle.attention_allocation_ref,
        context_snapshot_sha256=forged_context,
        evidence_receipt=forged_receipt,
        hypotheses=forged_hypotheses,
    )
    assert forged_bundle.bundle_id != bundle.bundle_id
    with pytest.raises(
        ContradictionHypothesisIntegrityError,
        match="does not match canonical provenance",
    ):
        protocol.validate(kernel, forged_bundle)
