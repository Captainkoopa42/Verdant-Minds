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
    DependencyGapPipeline, EquivalenceLensSystem, ExperimentArchiveIntegrityError,
    EXPERIMENT_ARCHIVE_FORMAT, EXPERIMENT_ARCHIVE_LEGACY_FORMAT, LensEvidenceResult,
    LensOpcode, SimulationLedger, SimulationLedgerState, SimulationSettlement,
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
