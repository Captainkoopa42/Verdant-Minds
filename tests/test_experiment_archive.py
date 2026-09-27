from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from verdant_claims import ClaimLearningPipeline
from verdant_kernel import (
    ClaimPolarity, ClaimSourceClass, ObligationFamily, VerdantKernel,
    checkpoint_bytes, load_checkpoint,
)
from verdant_kernel.models import canonical_json_bytes
from verdant_obligations import (
    AttentionBidInput, AttentionPortfolio, ContradictionObligationDetector,
    CounterfactualPatch, CounterfactualPlan, CounterfactualRuntime,
    CouncilEvidenceLedgerState, CouncilInterventionCandidate,
    CouncilInterventionPolicy,
    CouncilLeastRegretTournament,
    CouncilTournamentDisposition, CouncilTournamentEvidenceRecord,
    DependencyGapPipeline, DiagnosticConclusion, DiagnosticEngine,
    DiagnosticLedgerState, DiagnosticProbeFinding, DiagnosticProbeKind,
    DiagnosticProbeObservation, DiagnosticResult, DiagnosticTriggerKind,
    EpistemicPreservationObservation, EquivalenceLensSystem,
    ExperimentArchiveIntegrityError,
    EXPERIMENT_ARCHIVE_COUNCIL_EVIDENCE_FORMAT,
    EXPERIMENT_ARCHIVE_COUNCIL_FORMAT,
    EXPERIMENT_ARCHIVE_DIAGNOSTIC_FORMAT, EXPERIMENT_ARCHIVE_FORMAT,
    EXPERIMENT_ARCHIVE_LEGACY_FORMAT, InquiryFailureEvidence, LensEvidenceResult,
    InterventionKind, LensOpcode, OrthogonalFingerprintObservation,
    SimulationLedger, SimulationLedgerState, SimulationSettlement,
    derive_obligation_view, experiment_archive_bytes, load_experiment_archive,
    load_experiment_archive_bundle, save_experiment_archive,
)


def _experiment() -> tuple[VerdantKernel, CounterfactualRuntime]:
    kernel = VerdantKernel(seed=7101, state_dim=16, run_label="paired-archive")
    DependencyGapPipeline().observe_gap(
        kernel, target_action_node="action:safety-check",
        missing_input_signature="input:pressure", trigger_relation="requires",
        triggering_refs=("action:safety-check", "input:pressure"),
        source_event_key="archive:gap", context_snapshot_hash="archive:context",
    )
    claims = ClaimLearningPipeline()
    for polarity in (ClaimPolarity.AFFIRMED, ClaimPolarity.NEGATED):
        claims.record_claim(
            kernel, event_key=f"archive:claim:{polarity.value}",
            native_description=f"Observed {polarity.value}.",
            subject_label="gate", predicate="has_property", object_label="open",
            polarity=polarity, source_class=ClaimSourceClass.DIRECT_OBSERVATION,
        )
    ContradictionObligationDetector().detect_and_record(kernel)
    ids = tuple(sorted(kernel.state.obligation_kernels))
    assert len(ids) == 2
    assert {kernel.state.obligation_kernels[key].family for key in ids} == {
        ObligationFamily.DEPENDENCY_GAP, ObligationFamily.CONTRADICTION,
    }
    decision = AttentionPortfolio().decide(
        kernel,
        tuple(AttentionBidInput(
            obligation_id=key, action_operator="paired_archive_probe",
            requested_budget=0.05, estimated_cost=0.02, expected_gain=0.7,
            uncertainty=0.8, urgency=0.6, novelty=0.5,
            generator_version="archive-test-v1",
        ) for key in ids),
        source_event_key="archive:attention",
    ).decision
    assert len(decision.allocations) == 2
    runtime = CounterfactualRuntime()
    for allocation in decision.allocations:
        runtime.execute(kernel, allocation_id=allocation.allocation_id, plan=
            CounterfactualPlan.build(
                source_event_key=f"archive:simulation:{allocation.obligation_id}",
                operator_version="archive-test-v1", requested_budget=0.02,
                consumed_budget=0.01,
                patches=(CounterfactualPatch.delete(
                    "obligation_kernels", allocation.obligation_id,
                ),),
                result_refs=(f"archive:result:{allocation.obligation_id}",),
            ),
        )
    return kernel, runtime


def _parts(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _repack(
    parts: dict[str, bytes],
    *,
    canonical: VerdantKernel | None = None,
    lenses: EquivalenceLensSystem | None = None,
    diagnostics: DiagnosticEngine | None = None,
    council: CouncilLeastRegretTournament | None = None,
    council_evidence: CouncilEvidenceLedgerState | None = None,
) -> bytes:
    manifest = json.loads(parts["manifest.json"])
    for name in manifest["files"]:
        manifest["files"][name] = {
            "sha256": hashlib.sha256(parts[name]).hexdigest(),
            "bytes": len(parts[name]),
        }
    if canonical is not None:
        manifest["canonical_fingerprint"] = canonical.fingerprint()
    else:
        manifest["simulation_fingerprint"] = SimulationLedgerState.model_validate_json(
            parts["simulation.json"]
        ).fingerprint()
    if lenses is not None:
        manifest["lens_fingerprint"] = lenses.fingerprint()
    if diagnostics is not None:
        manifest["diagnostic_fingerprint"] = diagnostics.fingerprint()
    if council is not None:
        council_payload = {
            "policy": council.policy.model_dump(mode="json"),
            "ledger": council.state.model_dump(mode="json"),
        }
        manifest["council_fingerprint"] = hashlib.sha256(
            canonical_json_bytes(council_payload)
        ).hexdigest()
    if council_evidence is not None:
        manifest["council_evidence_fingerprint"] = (
            council_evidence.fingerprint()
        )
    parts["manifest.json"] = canonical_json_bytes(manifest)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    return output.getvalue()


def test_cross_family_replay_is_deterministic_and_canonically_isolated(tmp_path: Path) -> None:
    kernel, runtime = _experiment()
    before = kernel.fingerprint()
    views = {key: derive_obligation_view(kernel, key)
             for key in kernel.state.obligation_kernels}
    data = experiment_archive_bytes(kernel, runtime.ledger)
    assert data == experiment_archive_bytes(kernel, runtime.ledger)
    path = tmp_path / "experiment.vob"
    assert save_experiment_archive(path, kernel, runtime.ledger) == hashlib.sha256(data).hexdigest()
    assert path.read_bytes() == data
    restored, ledger = load_experiment_archive(path)
    assert kernel.fingerprint() == restored.fingerprint() == before
    assert ledger.fingerprint() == runtime.ledger.fingerprint()
    assert len(ledger.state.settlements) == 2
    assert all(derive_obligation_view(restored, key) == view for key, view in views.items())
    assert all(not item.canonical_commit_permitted for item in ledger.state.settlements)
    for arm in (kernel, restored):
        DependencyGapPipeline().observe_gap(
            arm, target_action_node="action:future", missing_input_signature="input:future",
            trigger_relation="requires", triggering_refs=("action:future", "input:future"),
            source_event_key="archive:future", context_snapshot_hash="archive:future",
        )
    assert kernel.fingerprint() == restored.fingerprint()
    assert len(restored.state.obligation_kernels) == 3


def test_checksum_and_rehashed_foreign_checkpoint_fail_closed(tmp_path: Path) -> None:
    kernel, runtime = _experiment()
    parts = _parts(experiment_archive_bytes(kernel, runtime.ledger))
    parts["simulation.json"] += b" "
    path = tmp_path / "altered.vob"
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    path.write_bytes(output.getvalue())
    with pytest.raises(ExperimentArchiveIntegrityError, match="checksum"):
        load_experiment_archive(path)
    foreign = VerdantKernel(seed=7102, state_dim=16, run_label="foreign")
    parts["simulation.json"] = _parts(experiment_archive_bytes(kernel, runtime.ledger))[
        "simulation.json"
    ]
    parts["canonical.vdk"] = checkpoint_bytes(foreign.snapshot())
    path.write_bytes(_repack(parts, canonical=foreign))
    with pytest.raises(ExperimentArchiveIntegrityError, match="Attention allocation"):
        load_experiment_archive(path)


def test_rehashed_false_settlement_origin_fails_closed(tmp_path: Path) -> None:
    kernel, runtime = _experiment()
    state = runtime.ledger.snapshot()
    original = state.settlements[0]
    values = original.model_dump(exclude={
        "settlement_id", "payload_sha256", "canonical_before_fingerprint",
        "canonical_after_fingerprint",
    })
    values.update(
        canonical_before_fingerprint="0" * 64,
        canonical_after_fingerprint="0" * 64,
    )
    altered = SimulationLedgerState(
        reservations=state.reservations,
        settlements=(SimulationSettlement.build(**values), *state.settlements[1:]),
    )
    parts = _parts(experiment_archive_bytes(kernel, runtime.ledger))
    parts["simulation.json"] = canonical_json_bytes(altered.model_dump(mode="json"))
    path = tmp_path / "false-origin.vob"
    path.write_bytes(_repack(parts))
    with pytest.raises(ExperimentArchiveIntegrityError, match="reserved canonical state"):
        load_experiment_archive(path)


def test_failed_atomic_replace_preserves_prior_file(tmp_path: Path, monkeypatch) -> None:
    kernel, runtime = _experiment()
    path = tmp_path / "archive.vob"
    save_experiment_archive(path, kernel, runtime.ledger)
    before = path.read_bytes()

    def fail_replace(_source: Path, _target: Path) -> None:
        raise OSError("injected failure")

    monkeypatch.setattr("verdant_obligations.experiment_archive.os.replace", fail_replace)
    with pytest.raises(OSError, match="injected failure"):
        save_experiment_archive(path, kernel, runtime.ledger)
    assert path.read_bytes() == before
    assert list(tmp_path.glob(".archive.vob.*.tmp")) == []


def test_all_17_legacy_checkpoints_load_and_embed(tmp_path: Path) -> None:
    paths = sorted((Path(__file__).resolve().parents[1] / "artifacts").glob("*.vdk"))
    assert len(paths) == 17
    for original in paths:
        kernel = VerdantKernel.from_state(load_checkpoint(original))
        legacy_path = tmp_path / f"{original.stem}-v1.vob"
        save_experiment_archive(legacy_path, kernel, SimulationLedger())
        restored, ledger = load_experiment_archive(legacy_path)
        assert restored.fingerprint() == kernel.fingerprint()
        assert ledger.state.reservations == ()
        lens_path = tmp_path / f"{original.stem}-v2.vob"
        empty_lenses = EquivalenceLensSystem()
        save_experiment_archive(
            lens_path,
            kernel,
            SimulationLedger(),
            lens_system=empty_lenses,
        )
        bundle = load_experiment_archive_bundle(lens_path)
        assert bundle.kernel.fingerprint() == kernel.fingerprint()
        assert bundle.simulation_ledger.state.reservations == ()
        assert bundle.lens_system is not None
        assert bundle.lens_system.fingerprint() == empty_lenses.fingerprint()
        diagnostic_path = tmp_path / f"{original.stem}-v3.vob"
        empty_diagnostics = DiagnosticEngine()
        save_experiment_archive(
            diagnostic_path,
            kernel,
            SimulationLedger(),
            lens_system=empty_lenses,
            diagnostic_engine=empty_diagnostics,
        )
        diagnostic_bundle = load_experiment_archive_bundle(diagnostic_path)
        assert diagnostic_bundle.kernel.fingerprint() == kernel.fingerprint()
        assert diagnostic_bundle.simulation_ledger.state.reservations == ()
        assert diagnostic_bundle.lens_system is not None
        assert diagnostic_bundle.diagnostic_engine is not None
        assert (
            diagnostic_bundle.diagnostic_engine.fingerprint()
            == empty_diagnostics.fingerprint()
        )
        council_path = tmp_path / f"{original.stem}-v4.vob"
        empty_council = CouncilLeastRegretTournament()
        save_experiment_archive(
            council_path,
            kernel,
            SimulationLedger(),
            lens_system=empty_lenses,
            diagnostic_engine=empty_diagnostics,
            council_tournament=empty_council,
        )
        council_bundle = load_experiment_archive_bundle(council_path)
        assert council_bundle.kernel.fingerprint() == kernel.fingerprint()
        assert council_bundle.council_tournament is not None
        assert (
            council_bundle.council_tournament.fingerprint()
            == empty_council.fingerprint()
        )
        evidence_path = tmp_path / f"{original.stem}-v5.vob"
        empty_evidence = CouncilEvidenceLedgerState()
        save_experiment_archive(
            evidence_path,
            kernel,
            SimulationLedger(),
            lens_system=empty_lenses,
            diagnostic_engine=empty_diagnostics,
            council_tournament=empty_council,
            council_evidence=empty_evidence,
        )
        evidence_bundle = load_experiment_archive_bundle(evidence_path)
        assert evidence_bundle.kernel.fingerprint() == kernel.fingerprint()
        assert evidence_bundle.council_evidence is not None
        assert (
            evidence_bundle.council_evidence.fingerprint()
            == empty_evidence.fingerprint()
        )


def _lenses(
    kernel: VerdantKernel,
    runtime: CounterfactualRuntime,
    *,
    suffix: str = "primary",
) -> EquivalenceLensSystem:
    lenses = EquivalenceLensSystem()
    dependency_definition = lenses.register_definition(
        operators=(LensOpcode.SELECT_ACTION, LensOpcode.SELECT_EDGE_TYPES),
        provenance_refs=(f"archive:lens:{suffix}:dependency",),
    )
    dependency_binding = lenses.approve_binding(
        definition_id=dependency_definition.definition_id,
        obligation_family=ObligationFamily.DEPENDENCY_GAP,
        failure_tripwire_count=2,
        calibration_refs=(f"archive:control:{suffix}:dependency",),
        source_event_key=f"archive:lens:{suffix}:approve:dependency",
        cycle=kernel.state.cycle,
    )
    contradiction_definition = lenses.register_definition(
        operators=(LensOpcode.SELECT_ACTION,),
        provenance_refs=(f"archive:lens:{suffix}:contradiction",),
    )
    lenses.approve_binding(
        definition_id=contradiction_definition.definition_id,
        obligation_family=ObligationFamily.CONTRADICTION,
        failure_tripwire_count=2,
        calibration_refs=(f"archive:control:{suffix}:contradiction",),
        source_event_key=f"archive:lens:{suffix}:approve:contradiction",
        cycle=kernel.state.cycle,
    )
    lenses.record_evidence(
        binding_id=dependency_binding.binding_id,
        result=LensEvidenceResult.SUPPORTED,
        independent_consequence_refs=(
            runtime.ledger.state.settlements[0].settlement_id,
        ),
        source_event_key=f"archive:lens:{suffix}:evidence",
        cycle=kernel.state.cycle,
    )
    return lenses


def _diagnostics(
    kernel: VerdantKernel,
    runtime: CounterfactualRuntime,
    lenses: EquivalenceLensSystem,
    *,
    suffix: str = "primary",
) -> DiagnosticEngine:
    obligation_id = next(
        key for key, value in kernel.state.obligation_kernels.items()
        if value.family == ObligationFamily.DEPENDENCY_GAP
    )
    decision = kernel.state.obligation_attention_decisions[0]
    allocation = next(
        item for item in decision.allocations
        if item.obligation_id == obligation_id
    )
    binding = lenses.active_binding(ObligationFamily.DEPENDENCY_GAP).binding
    hypothesis_ref = f"archive:hypothesis:{suffix}"
    failed = runtime.execute(
        kernel,
        allocation_id=allocation.allocation_id,
        plan=CounterfactualPlan.build(
            source_event_key=f"archive:diagnostic:{suffix}:failure",
            operator_version="archive-diagnostic-v1",
            requested_budget=0.01,
            consumed_budget=0.005,
            result_refs=(hypothesis_ref,),
        ),
    ).settlement
    trigger = InquiryFailureEvidence.build(
        trigger_kind=DiagnosticTriggerKind.INQUIRY_FAILURE,
        attention_decision_id=decision.decision_id,
        failed_settlement_id=failed.settlement_id,
        obligation_id=obligation_id,
        lens_binding_id=binding.binding_id,
        lens_definition_id=binding.definition_id,
        hypothesis_ref=hypothesis_ref,
        completed_within_predicted_cost=True,
        graph_traversal_valid=True,
        action_executed=False,
        explanatory_gain_observed=False,
        evidence_refs=(
            decision.decision_id,
            failed.settlement_id,
            binding.binding_id,
            binding.definition_id,
            hypothesis_ref,
        ),
    )
    diagnostics = DiagnosticEngine()
    diagnostic = diagnostics.open(
        kernel,
        trigger=trigger,
        simulation_ledger=runtime.ledger,
        lens_system=lenses,
        source_event_key=f"archive:diagnostic:{suffix}:open",
    )
    basis_ref = f"archive:diagnostic:{suffix}:basis"
    probe_settlement = runtime.execute(
        kernel,
        allocation_id=allocation.allocation_id,
        plan=CounterfactualPlan.build(
            source_event_key=f"archive:diagnostic:{suffix}:probe",
            operator_version="archive-diagnostic-probe-v1",
            requested_budget=0.01,
            consumed_budget=0.005,
            result_refs=(diagnostic.diagnostic_id, basis_ref),
        ),
    ).settlement
    probe = DiagnosticProbeObservation.build(
        diagnostic_id=diagnostic.diagnostic_id,
        kind=DiagnosticProbeKind.PRIMITIVE_BASELINE,
        finding=DiagnosticProbeFinding.LENS_COLLAPSED_DISTINCT,
        simulation_settlement_id=probe_settlement.settlement_id,
        basis_refs=(basis_ref,),
    )
    diagnostics.conclude(
        diagnostic_id=diagnostic.diagnostic_id,
        probes=(probe,),
        simulation_ledger=runtime.ledger,
        source_event_key=f"archive:diagnostic:{suffix}:conclude",
    )
    return diagnostics


def _council(
    kernel: VerdantKernel,
    runtime: CounterfactualRuntime,
    lenses: EquivalenceLensSystem,
    diagnostics: DiagnosticEngine,
    *,
    suffix: str = "primary",
    policy: CouncilInterventionPolicy | None = None,
) -> tuple[
    CouncilLeastRegretTournament,
    tuple[CouncilInterventionCandidate, ...],
    tuple[EpistemicPreservationObservation, ...],
]:
    result = diagnostics.state.results[0]
    diagnostic = diagnostics.state.obligations[0]
    trigger = diagnostic.trigger
    decision = next(
        item for item in kernel.state.obligation_attention_decisions
        if item.decision_id == trigger.attention_decision_id
    )
    allocation = next(
        item for item in decision.allocations
        if item.obligation_id == trigger.obligation_id
    )
    candidates = (
        CouncilInterventionCandidate.build(
            diagnostic_result_id=result.result_id,
            kind=InterventionKind.DEMOTE_LENS,
            target_component_refs=(trigger.lens_definition_id,),
            proposed_variant_ref=f"archive:council:{suffix}:lens-variant",
            basis_refs=(
                result.result_id,
                f"archive:council:{suffix}:lens-basis",
            ),
        ),
        CouncilInterventionCandidate.build(
            diagnostic_result_id=result.result_id,
            kind=InterventionKind.ADJUST_ATTENTION_POLICY,
            target_component_refs=(trigger.attention_decision_id,),
            proposed_variant_ref=f"archive:council:{suffix}:attention-variant",
            basis_refs=(
                result.result_id,
                f"archive:council:{suffix}:attention-basis",
            ),
        ),
    )
    evaluations = []
    for index, candidate in enumerate(candidates):
        basis_ref = f"archive:council:{suffix}:evaluation:{index}"
        settlement = runtime.execute(
            kernel,
            allocation_id=allocation.allocation_id,
            plan=CounterfactualPlan.build(
                source_event_key=f"archive:council:{suffix}:simulation:{index}",
                operator_version="archive-council-v1",
                requested_budget=0.01,
                consumed_budget=0.005,
                result_refs=(candidate.candidate_id, basis_ref),
            ),
        ).settlement
        orthogonal = hashlib.sha256(
            f"archive:council:{suffix}:orthogonal:{index}".encode()
        ).hexdigest()
        evaluations.append(EpistemicPreservationObservation.build(
            candidate_id=candidate.candidate_id,
            simulation_settlement_id=settlement.settlement_id,
            checkpoint_fingerprint=kernel.fingerprint(),
            repair_restored=True,
            would_reopen_obligation_ids=(
                () if index == 0 else (trigger.obligation_id,)
            ),
            wave_state_deviation_ppm=10 + index * 10,
            c_memory_deviation_units=10 + index * 10,
            tg_observer_deviation_ppm=10 + index * 10,
            orthogonal_fingerprints=(OrthogonalFingerprintObservation(
                context_ref="archive:council:orthogonal-suite",
                before_fingerprint=orthogonal,
                after_fingerprint=orthogonal,
            ),),
            basis_refs=(basis_ref,),
        ))
    tournament = CouncilLeastRegretTournament(policy=policy)
    council_decision = tournament.decide(
        kernel,
        diagnostic_result_id=result.result_id,
        candidates=candidates,
        evaluations=tuple(evaluations),
        diagnostics=diagnostics,
        simulation_ledger=runtime.ledger,
        lens_system=lenses,
        source_event_key=f"archive:council:{suffix}:decision",
    )
    assert council_decision.disposition == CouncilTournamentDisposition.RECOMMEND
    return tournament, candidates, tuple(evaluations)


def _council_evidence(
    council: CouncilLeastRegretTournament,
    candidates: tuple[CouncilInterventionCandidate, ...],
    evaluations: tuple[EpistemicPreservationObservation, ...],
) -> CouncilEvidenceLedgerState:
    return CouncilEvidenceLedgerState(records=(
        CouncilTournamentEvidenceRecord.build(
            decision=council.state.decisions[0],
            candidates=candidates,
            evaluations=evaluations,
        ),
    ))


def test_lens_archive_replays_both_sidecars_without_canonical_leakage(
    tmp_path: Path,
) -> None:
    kernel, runtime = _experiment()
    lenses = _lenses(kernel, runtime)
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()
    lens_before = lenses.fingerprint()

    data = experiment_archive_bytes(
        kernel, runtime.ledger, lens_system=lenses
    )
    assert data == experiment_archive_bytes(
        kernel, runtime.ledger, lens_system=lenses
    )
    assert json.loads(_parts(data)["manifest.json"])["format"] == (
        EXPERIMENT_ARCHIVE_FORMAT
    )
    path = tmp_path / "lens-paired.vob"
    save_experiment_archive(path, kernel, runtime.ledger, lens_system=lenses)
    bundle = load_experiment_archive_bundle(path)

    assert bundle.format_version == EXPERIMENT_ARCHIVE_FORMAT
    assert bundle.kernel.fingerprint() == canonical_before
    assert bundle.simulation_ledger.fingerprint() == simulation_before
    assert bundle.lens_system is not None
    assert bundle.lens_system.fingerprint() == lens_before
    assert bundle.diagnostic_engine is None
    for family in (ObligationFamily.DEPENDENCY_GAP, ObligationFamily.CONTRADICTION):
        assert bundle.lens_system.active_binding(family) == lenses.active_binding(family)

    restored_kernel, restored_simulation = load_experiment_archive(path)
    assert restored_kernel.fingerprint() == canonical_before
    assert restored_simulation.fingerprint() == simulation_before
    active = bundle.lens_system.active_binding(ObligationFamily.CONTRADICTION)
    bundle.lens_system.record_evidence(
        binding_id=active.binding.binding_id,
        result=LensEvidenceResult.VALID_NULL,
        independent_consequence_refs=("archive:post-reload:null",),
        source_event_key="archive:lens:post-reload:evidence",
        cycle=bundle.kernel.state.cycle,
    )
    assert bundle.kernel.fingerprint() == canonical_before
    assert bundle.simulation_ledger.fingerprint() == simulation_before
    assert lenses.fingerprint() == lens_before


def test_v1_archive_remains_readable_by_bundle_loader(tmp_path: Path) -> None:
    kernel, runtime = _experiment()
    path = tmp_path / "legacy.vob"
    save_experiment_archive(path, kernel, runtime.ledger)
    bundle = load_experiment_archive_bundle(path)
    assert bundle.format_version == EXPERIMENT_ARCHIVE_LEGACY_FORMAT
    assert bundle.lens_system is None
    assert bundle.diagnostic_engine is None
    assert bundle.kernel.fingerprint() == kernel.fingerprint()
    assert bundle.simulation_ledger.fingerprint() == runtime.ledger.fingerprint()


def test_rehashed_mixed_lens_registry_and_ledger_fail_closed(tmp_path: Path) -> None:
    kernel, runtime = _experiment()
    primary = _lenses(kernel, runtime, suffix="primary")
    foreign = _lenses(kernel, runtime, suffix="foreign")
    parts = _parts(experiment_archive_bytes(
        kernel, runtime.ledger, lens_system=primary
    ))
    parts["lens_ledger.json"] = _parts(experiment_archive_bytes(
        kernel, runtime.ledger, lens_system=foreign
    ))["lens_ledger.json"]
    path = tmp_path / "mixed-lens.vob"
    path.write_bytes(_repack(parts))

    with pytest.raises(ExperimentArchiveIntegrityError, match="Invalid experiment"):
        load_experiment_archive_bundle(path)


def test_unresolved_typed_lens_reference_and_future_history_are_rejected(
    tmp_path: Path,
) -> None:
    kernel, runtime = _experiment()
    lenses = _lenses(kernel, runtime)
    parts = _parts(experiment_archive_bytes(
        kernel, runtime.ledger, lens_system=lenses
    ))
    active = lenses.active_binding(ObligationFamily.CONTRADICTION)
    lenses.record_evidence(
        binding_id=active.binding.binding_id,
        result=LensEvidenceResult.SUPPORTED,
        independent_consequence_refs=("simulation_settlement_000000000000000000000000",),
        source_event_key="archive:lens:missing-settlement",
        cycle=kernel.state.cycle,
    )
    with pytest.raises(ExperimentArchiveIntegrityError, match="unresolved typed"):
        experiment_archive_bytes(kernel, runtime.ledger, lens_system=lenses)
    parts["lens_registry.json"] = canonical_json_bytes(
        lenses.registry.model_dump(mode="json")
    )
    parts["lens_ledger.json"] = canonical_json_bytes(
        lenses.ledger.model_dump(mode="json")
    )
    tampered_path = tmp_path / "missing-typed-ref.vob"
    tampered_path.write_bytes(_repack(parts, lenses=lenses))
    with pytest.raises(ExperimentArchiveIntegrityError, match="unresolved typed"):
        load_experiment_archive_bundle(tampered_path)

    future = EquivalenceLensSystem()
    definition = future.register_definition(
        operators=(LensOpcode.SELECT_ACTION,),
        provenance_refs=("archive:lens:future",),
    )
    future.approve_binding(
        definition_id=definition.definition_id,
        obligation_family=ObligationFamily.DEPENDENCY_GAP,
        failure_tripwire_count=2,
        calibration_refs=("archive:control:future",),
        source_event_key="archive:lens:future:approve",
        cycle=kernel.state.cycle + 1,
    )
    with pytest.raises(ExperimentArchiveIntegrityError, match="ahead"):
        experiment_archive_bytes(kernel, runtime.ledger, lens_system=future)


def test_diagnostic_archive_replays_three_sidecars_without_canonical_leakage(
    tmp_path: Path,
) -> None:
    kernel, runtime = _experiment()
    lenses = _lenses(kernel, runtime)
    diagnostics = _diagnostics(kernel, runtime, lenses)
    before = (
        kernel.fingerprint(),
        runtime.ledger.fingerprint(),
        lenses.fingerprint(),
        diagnostics.fingerprint(),
    )

    data = experiment_archive_bytes(
        kernel,
        runtime.ledger,
        lens_system=lenses,
        diagnostic_engine=diagnostics,
    )
    assert data == experiment_archive_bytes(
        kernel,
        runtime.ledger,
        lens_system=lenses,
        diagnostic_engine=diagnostics,
    )
    assert json.loads(_parts(data)["manifest.json"])["format"] == (
        EXPERIMENT_ARCHIVE_DIAGNOSTIC_FORMAT
    )
    path = tmp_path / "diagnostic-paired.vob"
    save_experiment_archive(
        path,
        kernel,
        runtime.ledger,
        lens_system=lenses,
        diagnostic_engine=diagnostics,
    )
    bundle = load_experiment_archive_bundle(path)

    assert bundle.format_version == EXPERIMENT_ARCHIVE_DIAGNOSTIC_FORMAT
    assert bundle.lens_system is not None
    assert bundle.diagnostic_engine is not None
    assert (
        bundle.kernel.fingerprint(),
        bundle.simulation_ledger.fingerprint(),
        bundle.lens_system.fingerprint(),
        bundle.diagnostic_engine.fingerprint(),
    ) == before
    result = bundle.diagnostic_engine.state.results[0]
    assert result.conclusion == DiagnosticConclusion.LENS_OVER_SMOOTHING
    assert result.terminal and not result.may_spawn_diagnostic
    assert not result.epistemic_authority_enabled
    assert (
        kernel.fingerprint(),
        runtime.ledger.fingerprint(),
        lenses.fingerprint(),
        diagnostics.fingerprint(),
    ) == before


def test_diagnostic_archive_requires_lens_sidecar() -> None:
    kernel, runtime = _experiment()
    lenses = _lenses(kernel, runtime)
    diagnostics = _diagnostics(kernel, runtime, lenses)

    with pytest.raises(ExperimentArchiveIntegrityError, match="require.*Lens"):
        experiment_archive_bytes(
            kernel,
            runtime.ledger,
            diagnostic_engine=diagnostics,
        )


def test_rehashed_foreign_diagnostic_ledger_fails_cross_ledger_closure(
    tmp_path: Path,
) -> None:
    kernel, runtime = _experiment()
    lenses = _lenses(kernel, runtime, suffix="primary-diagnostic")
    diagnostics = _diagnostics(
        kernel, runtime, lenses, suffix="primary-diagnostic"
    )
    parts = _parts(experiment_archive_bytes(
        kernel,
        runtime.ledger,
        lens_system=lenses,
        diagnostic_engine=diagnostics,
    ))

    foreign_kernel, foreign_runtime = _experiment()
    foreign_lenses = _lenses(
        foreign_kernel, foreign_runtime, suffix="foreign-diagnostic"
    )
    foreign_diagnostics = _diagnostics(
        foreign_kernel,
        foreign_runtime,
        foreign_lenses,
        suffix="foreign-diagnostic",
    )
    foreign_parts = _parts(experiment_archive_bytes(
        foreign_kernel,
        foreign_runtime.ledger,
        lens_system=foreign_lenses,
        diagnostic_engine=foreign_diagnostics,
    ))
    parts["diagnostic_ledger.json"] = foreign_parts["diagnostic_ledger.json"]
    path = tmp_path / "mixed-diagnostic.vob"
    path.write_bytes(_repack(parts, diagnostics=foreign_diagnostics))

    with pytest.raises(
        ExperimentArchiveIntegrityError,
        match="failed-inquiry|Lens lineage",
    ):
        load_experiment_archive_bundle(path)


def test_rehashed_diagnostic_attribution_and_missing_probe_fail_closed(
    tmp_path: Path,
) -> None:
    kernel, runtime = _experiment()
    lenses = _lenses(kernel, runtime)
    diagnostics = _diagnostics(kernel, runtime, lenses)
    data = experiment_archive_bytes(
        kernel,
        runtime.ledger,
        lens_system=lenses,
        diagnostic_engine=diagnostics,
    )

    original = diagnostics.state.results[0]
    wrong_definition = lenses.active_binding(
        ObligationFamily.CONTRADICTION
    ).binding.definition_id
    values = original.model_dump(mode="python", exclude={"result_id"})
    values["attributed_component_refs"] = (wrong_definition,)
    forged_result = DiagnosticResult.build(**values)
    forged_state = DiagnosticLedgerState(
        obligations=diagnostics.state.obligations,
        results=(forged_result,),
    )
    forged_diagnostics = DiagnosticEngine(state=forged_state)
    attribution_parts = _parts(data)
    attribution_parts["diagnostic_ledger.json"] = canonical_json_bytes(
        forged_state.model_dump(mode="json")
    )
    attribution_path = tmp_path / "forged-attribution.vob"
    attribution_path.write_bytes(_repack(
        attribution_parts,
        diagnostics=forged_diagnostics,
    ))
    with pytest.raises(ExperimentArchiveIntegrityError, match="attribution"):
        load_experiment_archive_bundle(attribution_path)

    diagnostic_id = diagnostics.state.obligations[0].diagnostic_id
    ledger_state = runtime.ledger.snapshot()
    without_probe = SimulationLedgerState(
        reservations=ledger_state.reservations,
        settlements=tuple(
            item for item in ledger_state.settlements
            if diagnostic_id not in item.result_refs
        ),
    )
    probe_parts = _parts(data)
    probe_parts["simulation.json"] = canonical_json_bytes(
        without_probe.model_dump(mode="json")
    )
    probe_path = tmp_path / "missing-probe.vob"
    probe_path.write_bytes(_repack(probe_parts))
    with pytest.raises(ExperimentArchiveIntegrityError, match="probe settlements"):
        load_experiment_archive_bundle(probe_path)


def test_council_archive_replays_four_sidecars_without_canonical_leakage(
    tmp_path: Path,
) -> None:
    kernel, runtime = _experiment()
    lenses = _lenses(kernel, runtime)
    diagnostics = _diagnostics(kernel, runtime, lenses)
    council, candidates, evaluations = _council(
        kernel, runtime, lenses, diagnostics
    )
    before = (
        kernel.fingerprint(),
        runtime.ledger.fingerprint(),
        lenses.fingerprint(),
        diagnostics.fingerprint(),
        council.fingerprint(),
    )
    data = experiment_archive_bytes(
        kernel,
        runtime.ledger,
        lens_system=lenses,
        diagnostic_engine=diagnostics,
        council_tournament=council,
    )
    assert data == experiment_archive_bytes(
        kernel,
        runtime.ledger,
        lens_system=lenses,
        diagnostic_engine=diagnostics,
        council_tournament=council,
    )
    assert json.loads(_parts(data)["manifest.json"])["format"] == (
        EXPERIMENT_ARCHIVE_COUNCIL_FORMAT
    )
    path = tmp_path / "council-paired.vob"
    save_experiment_archive(
        path,
        kernel,
        runtime.ledger,
        lens_system=lenses,
        diagnostic_engine=diagnostics,
        council_tournament=council,
    )
    bundle = load_experiment_archive_bundle(path)
    assert bundle.format_version == EXPERIMENT_ARCHIVE_COUNCIL_FORMAT
    assert bundle.lens_system is not None
    assert bundle.diagnostic_engine is not None
    assert bundle.council_tournament is not None
    assert bundle.council_tournament.policy == council.policy
    assert (
        bundle.kernel.fingerprint(),
        bundle.simulation_ledger.fingerprint(),
        bundle.lens_system.fingerprint(),
        bundle.diagnostic_engine.fingerprint(),
        bundle.council_tournament.fingerprint(),
    ) == before
    original = council.state.decisions[0]
    replay = bundle.council_tournament.decide(
        bundle.kernel,
        diagnostic_result_id=original.diagnostic_result_id,
        candidates=candidates,
        evaluations=evaluations,
        diagnostics=bundle.diagnostic_engine,
        simulation_ledger=bundle.simulation_ledger,
        lens_system=bundle.lens_system,
        source_event_key="archive:council:primary:decision",
    )
    assert replay == original
    assert not replay.intervention_authority_enabled
    assert (
        bundle.kernel.fingerprint(),
        bundle.simulation_ledger.fingerprint(),
        bundle.lens_system.fingerprint(),
        bundle.diagnostic_engine.fingerprint(),
        bundle.council_tournament.fingerprint(),
    ) == before


def test_council_archive_requires_diagnostic_sidecar() -> None:
    kernel, runtime = _experiment()
    lenses = _lenses(kernel, runtime)
    diagnostics = _diagnostics(kernel, runtime, lenses)
    council, _, _ = _council(kernel, runtime, lenses, diagnostics)
    with pytest.raises(ExperimentArchiveIntegrityError, match="require.*Diagnostic"):
        experiment_archive_bytes(
            kernel,
            runtime.ledger,
            lens_system=lenses,
            council_tournament=council,
        )


def test_rehashed_foreign_council_ledger_fails_cross_ledger_closure(
    tmp_path: Path,
) -> None:
    kernel, runtime = _experiment()
    lenses = _lenses(kernel, runtime, suffix="primary-council")
    diagnostics = _diagnostics(
        kernel, runtime, lenses, suffix="primary-council"
    )
    council, _, _ = _council(
        kernel, runtime, lenses, diagnostics, suffix="primary-council"
    )
    parts = _parts(experiment_archive_bytes(
        kernel,
        runtime.ledger,
        lens_system=lenses,
        diagnostic_engine=diagnostics,
        council_tournament=council,
    ))

    foreign_kernel, foreign_runtime = _experiment()
    foreign_lenses = _lenses(
        foreign_kernel, foreign_runtime, suffix="foreign-council"
    )
    foreign_diagnostics = _diagnostics(
        foreign_kernel,
        foreign_runtime,
        foreign_lenses,
        suffix="foreign-council",
    )
    foreign_council, _, _ = _council(
        foreign_kernel,
        foreign_runtime,
        foreign_lenses,
        foreign_diagnostics,
        suffix="foreign-council",
    )
    foreign_parts = _parts(experiment_archive_bytes(
        foreign_kernel,
        foreign_runtime.ledger,
        lens_system=foreign_lenses,
        diagnostic_engine=foreign_diagnostics,
        council_tournament=foreign_council,
    ))
    parts["council_policy.json"] = foreign_parts["council_policy.json"]
    parts["council_ledger.json"] = foreign_parts["council_ledger.json"]
    path = tmp_path / "mixed-council.vob"
    path.write_bytes(_repack(parts, council=foreign_council))
    with pytest.raises(ExperimentArchiveIntegrityError, match="Diagnostic Result"):
        load_experiment_archive_bundle(path)

    policy_parts = _parts(experiment_archive_bytes(
        kernel,
        runtime.ledger,
        lens_system=lenses,
        diagnostic_engine=diagnostics,
        council_tournament=council,
    ))
    changed_policy = CouncilInterventionPolicy(maximum_candidates=7)
    changed_council = CouncilLeastRegretTournament(
        policy=changed_policy,
        state=council.state,
    )
    policy_parts["council_policy.json"] = canonical_json_bytes(
        changed_policy.model_dump(mode="json")
    )
    policy_path = tmp_path / "changed-council-policy.vob"
    policy_path.write_bytes(_repack(policy_parts, council=changed_council))
    with pytest.raises(ExperimentArchiveIntegrityError, match="non-default policy"):
        load_experiment_archive_bundle(policy_path)


def test_rehashed_missing_council_candidate_simulation_fails_closed(
    tmp_path: Path,
) -> None:
    kernel, runtime = _experiment()
    lenses = _lenses(kernel, runtime)
    diagnostics = _diagnostics(kernel, runtime, lenses)
    council, candidates, _ = _council(kernel, runtime, lenses, diagnostics)
    parts = _parts(experiment_archive_bytes(
        kernel,
        runtime.ledger,
        lens_system=lenses,
        diagnostic_engine=diagnostics,
        council_tournament=council,
    ))
    state = runtime.ledger.snapshot()
    missing_candidate = candidates[0].candidate_id
    altered = SimulationLedgerState(
        reservations=state.reservations,
        settlements=tuple(
            item for item in state.settlements
            if missing_candidate not in item.result_refs
        ),
    )
    parts["simulation.json"] = canonical_json_bytes(
        altered.model_dump(mode="json")
    )
    path = tmp_path / "missing-council-simulation.vob"
    path.write_bytes(_repack(parts))
    with pytest.raises(
        ExperimentArchiveIntegrityError,
        match="candidate's isolated simulation lineage",
    ):
        load_experiment_archive_bundle(path)


def test_council_evidence_archive_recomputes_custom_policy_decision(
    tmp_path: Path,
) -> None:
    kernel, runtime = _experiment()
    lenses = _lenses(kernel, runtime, suffix="evidence")
    diagnostics = _diagnostics(kernel, runtime, lenses, suffix="evidence")
    policy = CouncilInterventionPolicy(maximum_candidates=7)
    council, candidates, evaluations = _council(
        kernel,
        runtime,
        lenses,
        diagnostics,
        suffix="evidence",
        policy=policy,
    )
    evidence = _council_evidence(council, candidates, evaluations)
    before = (
        kernel.fingerprint(),
        runtime.ledger.fingerprint(),
        lenses.fingerprint(),
        diagnostics.fingerprint(),
        council.fingerprint(),
        evidence.fingerprint(),
    )
    data = experiment_archive_bytes(
        kernel,
        runtime.ledger,
        lens_system=lenses,
        diagnostic_engine=diagnostics,
        council_tournament=council,
        council_evidence=evidence,
    )
    assert data == experiment_archive_bytes(
        kernel,
        runtime.ledger,
        lens_system=lenses,
        diagnostic_engine=diagnostics,
        council_tournament=council,
        council_evidence=evidence,
    )
    assert json.loads(_parts(data)["manifest.json"])["format"] == (
        EXPERIMENT_ARCHIVE_COUNCIL_EVIDENCE_FORMAT
    )
    path = tmp_path / "council-evidence.vob"
    save_experiment_archive(
        path,
        kernel,
        runtime.ledger,
        lens_system=lenses,
        diagnostic_engine=diagnostics,
        council_tournament=council,
        council_evidence=evidence,
    )
    bundle = load_experiment_archive_bundle(path)
    assert bundle.council_tournament is not None
    assert bundle.council_evidence is not None
    assert bundle.council_tournament.policy == policy
    assert (
        bundle.kernel.fingerprint(),
        bundle.simulation_ledger.fingerprint(),
        bundle.lens_system.fingerprint(),
        bundle.diagnostic_engine.fingerprint(),
        bundle.council_tournament.fingerprint(),
        bundle.council_evidence.fingerprint(),
    ) == before
    decision = bundle.council_tournament.state.decisions[0]
    assert decision.request_sha256 == council.state.decisions[0].request_sha256
    assert not decision.intervention_authority_enabled


def test_council_evidence_archive_requires_complete_pairing() -> None:
    kernel, runtime = _experiment()
    lenses = _lenses(kernel, runtime)
    diagnostics = _diagnostics(kernel, runtime, lenses)
    council, _, _ = _council(kernel, runtime, lenses, diagnostics)
    with pytest.raises(ExperimentArchiveIntegrityError, match="cover every"):
        experiment_archive_bytes(
            kernel,
            runtime.ledger,
            lens_system=lenses,
            diagnostic_engine=diagnostics,
            council_tournament=council,
            council_evidence=CouncilEvidenceLedgerState(),
        )
    with pytest.raises(ExperimentArchiveIntegrityError, match="paired tournament"):
        experiment_archive_bytes(
            kernel,
            runtime.ledger,
            lens_system=lenses,
            diagnostic_engine=diagnostics,
            council_evidence=CouncilEvidenceLedgerState(),
        )


def test_rehashed_council_evidence_change_fails_full_recomputation(
    tmp_path: Path,
) -> None:
    kernel, runtime = _experiment()
    lenses = _lenses(kernel, runtime)
    diagnostics = _diagnostics(kernel, runtime, lenses)
    council, candidates, evaluations = _council(
        kernel, runtime, lenses, diagnostics
    )
    evidence = _council_evidence(council, candidates, evaluations)
    parts = _parts(experiment_archive_bytes(
        kernel,
        runtime.ledger,
        lens_system=lenses,
        diagnostic_engine=diagnostics,
        council_tournament=council,
        council_evidence=evidence,
    ))
    original = evaluations[0]
    values = original.model_dump(mode="python", exclude={"evaluation_id"})
    values["wave_state_deviation_ppm"] += 1
    changed = EpistemicPreservationObservation.build(**values)
    changed_evaluations = (changed, *evaluations[1:])
    altered_evidence = _council_evidence(
        council,
        candidates,
        changed_evaluations,
    )
    parts["council_evidence.json"] = canonical_json_bytes(
        altered_evidence.model_dump(mode="json")
    )
    path = tmp_path / "changed-council-evidence.vob"
    path.write_bytes(_repack(parts, council_evidence=altered_evidence))
    with pytest.raises(
        ExperimentArchiveIntegrityError,
        match="could not be reproduced",
    ):
        load_experiment_archive_bundle(path)
