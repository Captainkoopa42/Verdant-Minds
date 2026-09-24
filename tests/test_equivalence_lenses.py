from __future__ import annotations

import hashlib

import pytest

from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    ObligationFamily,
    RelationProposal,
    VerdantKernel,
)
from verdant_obligations import (
    DependencyGapDetector,
    DependencyGapHypothesisGenerator,
    EquivalenceLensDefinition,
    EquivalenceLensSystem,
    LensBindingLedgerState,
    LensBindingStatus,
    LensEvidenceResult,
    LensIntegrityError,
    LensOpcode,
    LensUnavailableError,
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


def _hypotheses():
    kernel = VerdantKernel(seed=5601, state_dim=16, run_label="lens-tests")
    kernel.apply_experience(
        _experience(
            "lens-dependency",
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
            "lens-route",
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
            "lens-outcome",
            labels=("canonical reading",),
            evidence_kind=EvidenceKind.OUTCOME,
        )
    )
    report = DependencyGapDetector().detect_and_record(kernel)
    obligation_id = report.mutations[0].obligation.kernel_id
    hypotheses = DependencyGapHypothesisGenerator().generate(kernel, obligation_id)
    return kernel, obligation_id, hypotheses


def _definition(
    system: EquivalenceLensSystem,
    *,
    action_only: bool,
    parent_definition_id: str | None = None,
):
    operators = (
        (LensOpcode.SELECT_ACTION,)
        if action_only
        else (
            LensOpcode.SELECT_ACTION,
            LensOpcode.SELECT_ACTIVATED_REFS,
            LensOpcode.SELECT_EDGE_ENDPOINTS,
            LensOpcode.SELECT_EDGE_TYPES,
        )
    )
    return system.register_definition(
        operators=operators,
        provenance_refs=("test:matched-controls",),
        parent_definition_id=parent_definition_id,
    )


def _approve(
    system: EquivalenceLensSystem,
    definition_id: str,
    *,
    key: str,
    cycle: int,
    tripwire: int = 2,
):
    return system.approve_binding(
        definition_id=definition_id,
        obligation_family=ObligationFamily.DEPENDENCY_GAP,
        failure_tripwire_count=tripwire,
        calibration_refs=("test:held-out-a", "test:held-out-b"),
        source_event_key=key,
        cycle=cycle,
    )


def test_definitions_are_content_addressed_immutable_and_lineaged() -> None:
    system = EquivalenceLensSystem()
    first = _definition(system, action_only=True)
    replay = system.register_definition(
        operators=(LensOpcode.SELECT_ACTION, LensOpcode.SELECT_ACTION),
        provenance_refs=("test:matched-controls",),
    )
    child = _definition(
        system,
        action_only=False,
        parent_definition_id=first.definition_id,
    )

    assert replay == first
    assert child.definition_id != first.definition_id
    assert child.parent_definition_id == first.definition_id
    assert len(system.registry.definitions) == 2

    before = system.fingerprint()
    with pytest.raises(ValueError, match="parent lineage"):
        system.register_definition(
            operators=(LensOpcode.SELECT_EDGE_TYPES,),
            provenance_refs=("test:invalid-parent",),
            parent_definition_id="lens:missing",
        )
    assert system.fingerprint() == before


def test_lens_application_is_read_only_and_collapses_by_selected_dimensions() -> None:
    kernel, obligation_id, hypotheses = _hypotheses()
    system = EquivalenceLensSystem()
    definition = _definition(system, action_only=True)
    binding = _approve(system, definition.definition_id, key="lens:approve:v1", cycle=1)
    system_before = system.fingerprint()
    canonical_before = kernel.fingerprint()

    first = system.partition(
        obligation_id=obligation_id,
        family=ObligationFamily.DEPENDENCY_GAP,
        hypotheses=hypotheses,
    )
    second = system.partition(
        obligation_id=obligation_id,
        family=ObligationFamily.DEPENDENCY_GAP,
        hypotheses=hypotheses,
    )

    assert first == second
    assert first.binding_id == binding.binding_id
    assert len(first.equivalence_classes) == 3
    assert first.duplicate_outcome_ids
    assert system.fingerprint() == system_before
    assert kernel.fingerprint() == canonical_before


def test_binding_approval_replays_exactly_and_rejects_changed_reuse() -> None:
    system = EquivalenceLensSystem()
    definition = _definition(system, action_only=True)
    first = _approve(system, definition.definition_id, key="lens:approve", cycle=1)
    fingerprint = system.fingerprint()
    replay = _approve(system, definition.definition_id, key="lens:approve", cycle=1)

    assert replay == first
    assert system.fingerprint() == fingerprint
    with pytest.raises(LensIntegrityError, match="changed request"):
        system.approve_binding(
            definition_id=definition.definition_id,
            obligation_family=ObligationFamily.DEPENDENCY_GAP,
            failure_tripwire_count=7,
            calibration_refs=("test:held-out-a", "test:held-out-b"),
            source_event_key="lens:approve",
            cycle=1,
        )
    assert system.fingerprint() == fingerprint


def test_evidence_replay_is_idempotent_and_changed_reuse_is_rejected() -> None:
    system = EquivalenceLensSystem()
    definition = _definition(system, action_only=True)
    binding = _approve(system, definition.definition_id, key="lens:approve", cycle=1)
    first = system.record_evidence(
        binding_id=binding.binding_id,
        result=LensEvidenceResult.SUPPORTED,
        independent_consequence_refs=("control:outcome-a",),
        source_event_key="lens:evidence:one",
        cycle=2,
        hypothesis_refs=("hypothesis:a",),
        outcome_refs=("outcome:a",),
    )
    fingerprint = system.fingerprint()
    replay = system.record_evidence(
        binding_id=binding.binding_id,
        result=LensEvidenceResult.SUPPORTED,
        independent_consequence_refs=("control:outcome-a",),
        source_event_key="lens:evidence:one",
        cycle=2,
        hypothesis_refs=("hypothesis:a",),
        outcome_refs=("outcome:a",),
    )

    assert not first.replayed
    assert replay.replayed
    assert replay.evidence == first.evidence
    assert system.fingerprint() == fingerprint

    with pytest.raises(LensIntegrityError, match="changed evidence"):
        system.record_evidence(
            binding_id=binding.binding_id,
            result=LensEvidenceResult.HYPER_DISCRIMINATION,
            independent_consequence_refs=("control:outcome-a",),
            source_event_key="lens:evidence:one",
            cycle=2,
        )
    assert system.fingerprint() == fingerprint


def test_tripwire_suspends_failing_binding_without_penalizing_valid_nulls() -> None:
    system = EquivalenceLensSystem()
    definition = _definition(system, action_only=True)
    binding = _approve(
        system,
        definition.definition_id,
        key="lens:approve:tripwire",
        cycle=1,
        tripwire=2,
    )
    null = system.record_evidence(
        binding_id=binding.binding_id,
        result=LensEvidenceResult.VALID_NULL,
        independent_consequence_refs=("control:null",),
        source_event_key="lens:evidence:null",
        cycle=2,
    )
    first_failure = system.record_evidence(
        binding_id=binding.binding_id,
        result=LensEvidenceResult.OVER_SMOOTHING,
        independent_consequence_refs=("control:hidden-signal",),
        source_event_key="lens:evidence:failure-1",
        cycle=3,
    )
    second_failure = system.record_evidence(
        binding_id=binding.binding_id,
        result=LensEvidenceResult.NO_EXPLANATORY_GAIN,
        independent_consequence_refs=("control:no-gain",),
        source_event_key="lens:evidence:failure-2",
        cycle=4,
    )

    view = system.binding_view(binding.binding_id)
    assert not null.suspended
    assert not first_failure.suspended
    assert second_failure.suspended
    assert view.valid_null_count == 1
    assert view.failure_count == 2
    assert view.status == LensBindingStatus.SUSPENDED
    with pytest.raises(LensUnavailableError, match="exactly one active"):
        system.active_binding(ObligationFamily.DEPENDENCY_GAP)


def test_tripwire_collision_cannot_leave_half_committed_failure_evidence() -> None:
    system = EquivalenceLensSystem()
    definition = _definition(system, action_only=True)
    binding = _approve(
        system,
        definition.definition_id,
        key="lens:approve:atomic",
        cycle=1,
        tripwire=1,
    )
    system.record_evidence(
        binding_id=binding.binding_id,
        result=LensEvidenceResult.SUPPORTED,
        independent_consequence_refs=("control:occupied-key",),
        source_event_key="lens:evidence:failing:tripwire",
        cycle=2,
    )
    fingerprint = system.fingerprint()

    with pytest.raises(LensIntegrityError, match="tripwire source event key"):
        system.record_evidence(
            binding_id=binding.binding_id,
            result=LensEvidenceResult.OVER_SMOOTHING,
            independent_consequence_refs=("control:hidden-signal",),
            source_event_key="lens:evidence:failing",
            cycle=3,
        )

    assert system.fingerprint() == fingerprint
    assert system.binding_view(binding.binding_id).failure_count == 0
    assert system.binding_view(binding.binding_id).status == LensBindingStatus.ACTIVE


def test_explicit_rollback_reactivates_only_direct_predecessor() -> None:
    _, obligation_id, hypotheses = _hypotheses()
    system = EquivalenceLensSystem()
    broad = _definition(system, action_only=False)
    narrow = _definition(
        system,
        action_only=True,
        parent_definition_id=broad.definition_id,
    )
    v1 = _approve(system, broad.definition_id, key="lens:approve:v1", cycle=1)
    v2 = _approve(
        system,
        narrow.definition_id,
        key="lens:approve:v2",
        cycle=2,
        tripwire=1,
    )
    assert system.binding_view(v1.binding_id).status == LensBindingStatus.SUPERSEDED
    assert system.active_binding(ObligationFamily.DEPENDENCY_GAP).binding == v2
    system.record_evidence(
        binding_id=v2.binding_id,
        result=LensEvidenceResult.HYPER_DISCRIMINATION,
        independent_consequence_refs=("control:same-consequence",),
        source_event_key="lens:evidence:trip-v2",
        cycle=3,
    )

    restored = system.rollback(
        binding_id=v2.binding_id,
        target_binding_id=v1.binding_id,
        source_event_key="lens:rollback:v2-to-v1",
        cycle=4,
        basis_refs=("diagnostic:v2-failure",),
    )
    fingerprint = system.fingerprint()
    replay = system.rollback(
        binding_id=v2.binding_id,
        target_binding_id=v1.binding_id,
        source_event_key="lens:rollback:v2-to-v1",
        cycle=4,
        basis_refs=("diagnostic:v2-failure",),
    )

    assert restored.status == LensBindingStatus.ACTIVE
    assert replay == restored
    assert system.fingerprint() == fingerprint
    assert system.binding_view(v2.binding_id).status == LensBindingStatus.ROLLED_BACK
    partition = system.partition(
        obligation_id=obligation_id,
        family=ObligationFamily.DEPENDENCY_GAP,
        hypotheses=hypotheses,
    )
    assert partition.binding_id == v1.binding_id
    assert partition.definition_id == broad.definition_id


def test_registry_and_ledger_reload_deterministically_and_detect_tampering() -> None:
    system = EquivalenceLensSystem()
    definition = _definition(system, action_only=True)
    binding = _approve(system, definition.definition_id, key="lens:approve", cycle=1)
    system.record_evidence(
        binding_id=binding.binding_id,
        result=LensEvidenceResult.SUPPORTED,
        independent_consequence_refs=("control:held-out",),
        source_event_key="lens:evidence:supported",
        cycle=2,
    )
    registry, ledger = system.snapshot()
    restored = EquivalenceLensSystem(registry=registry, ledger=ledger)

    assert restored.fingerprint() == system.fingerprint()
    assert restored.snapshot() == system.snapshot()

    event = ledger.governance_events[0]
    tampered_event = event.model_copy(update={"sequence": 2})
    with pytest.raises(ValueError, match="checksum"):
        LensBindingLedgerState.model_validate(
            ledger.model_copy(
                update={"governance_events": (tampered_event,)},
                deep=True,
            ).model_dump(mode="json")
        )

    tampered_definition = definition.model_copy(
        update={"operators": (LensOpcode.SELECT_EDGE_TYPES,)}
    )
    with pytest.raises(ValueError, match="checksum"):
        EquivalenceLensDefinition.model_validate(
            tampered_definition.model_dump(mode="json")
        )
