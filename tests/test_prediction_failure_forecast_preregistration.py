from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from verdant_kernel import EvidenceKind, VerdantKernel, load_checkpoint, save_checkpoint
from verdant_kernel.models import canonical_json_bytes, stable_id
from verdant_obligations import (
    PredictionFailureForecastPreregistrar,
    PredictionFailureForecastPreregistrationIntegrityError,
    PredictionFailureForecastArm,
    PredictionFailureResolutionEvidenceRecorder,
    PredictionFailureTrialArmRuntime, SimulationLedger,
    load_prediction_failure_forecast_preregistration,
    prediction_failure_forecast_preregistration_bytes,
    read_prediction_failure_forecast_preregistration,
    save_prediction_failure_forecast_preregistration,
)
from test_prediction_failure_hypotheses import _evidence
from test_prediction_failure_resolution_evidence import _completed


def _inputs(tmp_path: Path, seed=7701, mode="insufficient"):
    kernel, bundle, kwargs, completed, ledgers = _completed(tmp_path, mode, seed)
    coverage = tmp_path / "anchor.vfe"
    anchor = PredictionFailureResolutionEvidenceRecorder().record(coverage, **kwargs)
    return kernel, bundle, {**kwargs, "resolution_evidence_path": coverage}, anchor, completed, ledgers


@pytest.mark.parametrize("mode", ("insufficient", "unchanged", "worsened", "improved"))
def test_forecast_preregistration_freezes_prospective_design_without_trial_or_score(tmp_path, monkeypatch, mode):
    kernel, _, kwargs, anchor, _, ledgers = _inputs(tmp_path, 7701, mode)
    before = kernel.fingerprint(), tuple(l.fingerprint() for l in ledgers)
    inputs = {str(p): p.read_bytes() for k, p in kwargs.items() if k != "kernel"}

    def forbidden(*args, **kw):
        raise AssertionError("Preregistration must not execute or fund a simulation")

    monkeypatch.setattr(PredictionFailureTrialArmRuntime, "execute", forbidden)
    monkeypatch.setattr(SimulationLedger, "reserve", forbidden)
    path = tmp_path / "study.vfs"
    envelope = PredictionFailureForecastPreregistrar().register(path, **kwargs)
    declaration = envelope.declaration
    policy = declaration.study_policy
    assert declaration.anchor == anchor.receipt
    assert declaration.anchor_sha256 == hashlib.sha256(kwargs["resolution_evidence_path"].read_bytes()).hexdigest()
    assert declaration.cutoff_cycle == kernel.state.cycle
    assert declaration.cutoff_event_sequence == kernel.state.event_sequence
    assert policy.calibration_case_count == policy.evaluation_case_count == 8
    assert policy.maximum_case_count == 16
    assert policy.arms == tuple(PredictionFailureForecastArm)
    assert policy.enrollment_rule == "first_authorized_same_action_class_decisions_after_cutoff"
    assert policy.all_forecasts_sealed_before_any_enrolled_outcome
    assert policy.frozen_governance_memory_required and policy.trace_derived_physical_measurement_required
    assert policy.measurement_protocol_frozen_before_forecasts_required
    assert policy.identical_measurement_protocol_across_cases_required
    assert not policy.measurement_metric_tuning_permitted
    assert policy.new_attention_allocation_per_case_required
    assert policy.maximum_total_budget == pytest.approx(16 * 0.045)
    assert not policy.governance_harm_score_alone_admissible
    assert not policy.outcome_conditioned_enrollment_permitted
    assert not policy.missing_case_replacement_permitted
    assert not policy.supplied_forecast_or_measurement_permitted
    assert not policy.calibration_curve_fitting_permitted and not policy.evaluation_outcome_fitting_permitted
    assert declaration.excluded_decision_refs == tuple(sorted(d.decision_event_id for d in kernel.state.council_decisions))
    assert declaration.excluded_outcome_refs == tuple(sorted(o.outcome_id for o in kernel.state.governance_outcomes))
    same_class = [o for o in kernel.state.governance_outcomes if o.action_class == declaration.action_class]
    assert declaration.support_outcome == max(same_class, key=lambda o: o.cycle)
    assert declaration.frozen_learned_risk == kernel.state.governance.learned_action_risk[declaration.action_class]
    assert declaration.support_outcome.cycle <= declaration.cutoff_cycle
    assert declaration.support_outcome.outcome_id in declaration.excluded_outcome_refs
    assert tuple(e.evidence_id for e in declaration.support_evidence) == declaration.support_outcome.evidence_refs
    assert any(e.kind == EvidenceKind.OUTCOME for e in declaration.support_evidence)
    root = Path(__file__).resolve().parent.parent
    for source in declaration.native_source_files:
        assert source.sha256 == hashlib.sha256((root / source.repository_path).read_bytes()).hexdigest()
    assert declaration.missing_prerequisites == ("physical_measurement_trace_observer", "prospective_forecast_adapter")
    assert declaration.prospective_only and not declaration.study_executed
    assert not declaration.forecasts_recorded and not declaration.future_outcomes_observed
    assert not declaration.calibration_observed and not declaration.resolution_contract_satisfied
    assert not declaration.simulation_budget_authorized and not declaration.canonical_commit_permitted
    assert not declaration.policy_rewrite_authority_enabled and not declaration.promotion_authority_enabled
    assert load_prediction_failure_forecast_preregistration(path, **kwargs) == envelope
    assert (kernel.fingerprint(), tuple(l.fingerprint() for l in ledgers)) == before
    assert inputs == {str(p): p.read_bytes() for k, p in kwargs.items() if k != "kernel"}


def test_forecast_preregistration_checkpoint_replay_is_byte_exact_without_new_cost(tmp_path, monkeypatch):
    kernel, _, kwargs, _, _, ledgers = _inputs(tmp_path, 7702, "improved")
    path = tmp_path / "replay.vfs"
    envelope = PredictionFailureForecastPreregistrar().register(path, **kwargs)
    before = path.read_bytes(), tuple(l.fingerprint() for l in ledgers)
    checkpoint = tmp_path / "study.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    state = load_checkpoint(checkpoint)
    state.evidence = dict(reversed(tuple(state.evidence.items())))
    state.governance.learned_action_risk = dict(reversed(tuple(state.governance.learned_action_risk.items())))
    kwargs["kernel"] = VerdantKernel.from_state(state)

    def forbidden(*args, **kw):
        raise AssertionError("Prospective replay must not execute, reserve or settle")

    monkeypatch.setattr(PredictionFailureTrialArmRuntime, "execute", forbidden)
    monkeypatch.setattr(SimulationLedger, "reserve", forbidden)
    monkeypatch.setattr(SimulationLedger, "settle", forbidden)
    assert load_prediction_failure_forecast_preregistration(path, **kwargs) == envelope
    assert PredictionFailureForecastPreregistrar().register(path, **kwargs) == envelope
    assert path.read_bytes() == before[0] == prediction_failure_forecast_preregistration_bytes(envelope)
    assert tuple(l.fingerprint() for l in ledgers) == before[1]
    assert kwargs["kernel"].fingerprint() == kernel.fingerprint()


def _rehash(payload):
    declaration = payload["declaration"]
    declaration["declaration_id"] = stable_id("prediction_failure_forecast_study_declaration",
        {k: v for k, v in declaration.items() if k != "declaration_id"})
    payload["declaration_sha256"] = hashlib.sha256(canonical_json_bytes(declaration)).hexdigest()
    return canonical_json_bytes(payload)


@pytest.mark.parametrize("attack", (
    "counts", "threshold", "outcome_selection", "replacement", "forecast_timing", "measurement_bypass",
    "fit_on_evaluation", "measurement_timing", "measurement_tuning", "arm_swap", "grant", "calibrated", "authority", "hidden_missing",
    "cutoff", "event_sequence", "source_manifest", "historical_exclusion", "anchor_hash", "support",
))
def test_forecast_preregistration_rehashed_design_or_provenance_changes_fail_closed(tmp_path, attack):
    _, _, kwargs, _, _, _ = _inputs(tmp_path, 7703, "unchanged")
    envelope = PredictionFailureForecastPreregistrar().register(tmp_path / "original.vfs", **kwargs)
    payload = envelope.model_dump(mode="json")
    data, policy = payload["declaration"], payload["declaration"]["study_policy"]
    if attack == "counts":
        policy["calibration_case_count"] = policy["evaluation_case_count"] = 1
        policy["maximum_case_count"] = 2
    elif attack == "threshold":
        policy["evaluation_improvement_threshold"] = 0.001
    elif attack == "outcome_selection":
        policy["outcome_conditioned_enrollment_permitted"] = True
    elif attack == "replacement":
        policy["missing_case_replacement_permitted"] = True
    elif attack == "forecast_timing":
        policy["all_forecasts_sealed_before_any_enrolled_outcome"] = False
    elif attack == "measurement_bypass":
        policy["governance_harm_score_alone_admissible"] = True
    elif attack == "fit_on_evaluation":
        policy["evaluation_outcome_fitting_permitted"] = True
    elif attack == "measurement_timing":
        policy["measurement_protocol_frozen_before_forecasts_required"] = False
    elif attack == "measurement_tuning":
        policy["measurement_metric_tuning_permitted"] = True
    elif attack == "arm_swap":
        policy["arms"][0], policy["arms"][1] = policy["arms"][1], policy["arms"][0]
    elif attack == "grant":
        data["simulation_budget_authorized"] = True
    elif attack == "calibrated":
        data["calibration_observed"] = True
    elif attack == "authority":
        data["resolution_authority_enabled"] = True
    elif attack == "hidden_missing":
        data["missing_prerequisites"] = []
    elif attack == "cutoff":
        data["cutoff_cycle"] += 1
    elif attack == "event_sequence":
        data["cutoff_event_sequence"] += 1
    elif attack == "source_manifest":
        data["native_source_files"][0]["sha256"] = "0" * 64
    elif attack == "historical_exclusion":
        # Remove another canonical decision, preserving direct support/target.
        data["excluded_decision_refs"] = [data["support_decision"]["decision_event_id"]]
    elif attack == "anchor_hash":
        data["anchor_sha256"] = "0" * 64
    else:
        data["frozen_learned_risk"] = 0.99
    forged = tmp_path / "forged.vfs"
    forged.write_bytes(_rehash(payload))
    with pytest.raises(PredictionFailureForecastPreregistrationIntegrityError):
        load_prediction_failure_forecast_preregistration(forged, **kwargs)
    # Fully rehashed values and bypassed models still cannot enter durable save.
    original = envelope.declaration.model_dump(mode="json")
    updates = {k: v for k, v in data.items() if v != original[k]}
    if "study_policy" in updates:
        changes = {k: v for k, v in policy.items() if v != original["study_policy"][k]}
        if "arms" in changes:
            changes["arms"] = tuple(PredictionFailureForecastArm(v) for v in changes["arms"])
        updates["study_policy"] = envelope.declaration.study_policy.model_copy(update=changes)
    for key in ("excluded_decision_refs", "missing_prerequisites"):
        if key in updates:
            updates[key] = tuple(updates[key])
    if "native_source_files" in updates:
        updates["native_source_files"] = tuple(s.model_copy(update={"sha256": d["sha256"]})
            for s, d in zip(envelope.declaration.native_source_files, data["native_source_files"], strict=True))
    bypassed = envelope.model_copy(update={"declaration": envelope.declaration.model_copy(update=updates),
                                           "declaration_sha256": payload["declaration_sha256"]})
    with pytest.raises(PredictionFailureForecastPreregistrationIntegrityError):
        save_prediction_failure_forecast_preregistration(tmp_path / "saved-forgery.vfs", bypassed, **kwargs)
    assert not (tmp_path / "saved-forgery.vfs").exists()


@pytest.mark.parametrize("source", ("foreign", "stale", "missing", "swapped_anchor", "code_drift"))
def test_forecast_preregistration_requires_original_checkpoint_and_all_sources(tmp_path, monkeypatch, source):
    kernel, _, kwargs, _, _, _ = _inputs(tmp_path, 7704, "unchanged")
    path = tmp_path / "paired.vfs"
    envelope = PredictionFailureForecastPreregistrar().register(path, **kwargs)
    data = path.read_bytes()
    if source in ("foreign", "swapped_anchor"):
        _, _, foreign, _, _, _ = _inputs(tmp_path / "foreign", 7705, "unchanged")
        kwargs = foreign if source == "foreign" else {**kwargs, "resolution_evidence_path": foreign["resolution_evidence_path"]}
    elif source == "stale":
        stale = VerdantKernel.from_state(kernel.snapshot())
        _evidence(stale, "later-physical-record", EvidenceKind.OUTCOME)
        kwargs["kernel"] = stale
    elif source == "missing":
        kwargs["completed_result_path"].unlink()
    else:
        import verdant_obligations.prediction_failure_forecast_preregistration as module
        original = module._source_manifest
        def changed():
            return tuple(s.model_copy(update={"sha256": "0" * 64}) for s in original())
        monkeypatch.setattr(module, "_source_manifest", changed)
    assert read_prediction_failure_forecast_preregistration(path) == envelope
    before = kwargs["kernel"].fingerprint()
    with pytest.raises(PredictionFailureForecastPreregistrationIntegrityError):
        load_prediction_failure_forecast_preregistration(path, **kwargs)
    assert kwargs["kernel"].fingerprint() == before and path.read_bytes() == data


def test_forecast_preregistration_rejects_noncanonical_bytes_size_and_input_or_occupied_paths(tmp_path, monkeypatch):
    _, _, kwargs, _, _, _ = _inputs(tmp_path, 7706)
    path = tmp_path / "immutable.vfs"
    envelope = PredictionFailureForecastPreregistrar().register(path, **kwargs)
    original = path.read_bytes()
    for altered in (b" " + original, original[:-1] + b"!",
                    json.dumps(envelope.model_dump(mode="json"), indent=2).encode()):
        bad = tmp_path / "bad.vfs"
        bad.write_bytes(altered)
        with pytest.raises(PredictionFailureForecastPreregistrationIntegrityError):
            read_prediction_failure_forecast_preregistration(bad)
    for key, p in kwargs.items():
        if key != "kernel":
            before = p.read_bytes()
            with pytest.raises(PredictionFailureForecastPreregistrationIntegrityError, match="separate"):
                PredictionFailureForecastPreregistrar().register(p, **kwargs)
            assert p.read_bytes() == before
    occupied = tmp_path / "occupied.vfs"
    occupied.write_bytes(b"occupied")
    with pytest.raises(PredictionFailureForecastPreregistrationIntegrityError):
        PredictionFailureForecastPreregistrar().register(occupied, **kwargs)
    assert occupied.read_bytes() == b"occupied"
    _, _, other, _, _, _ = _inputs(tmp_path / "other", 7707)
    with pytest.raises(PredictionFailureForecastPreregistrationIntegrityError):
        PredictionFailureForecastPreregistrar().register(path, **other)
    assert path.read_bytes() == original
    import verdant_obligations.prediction_failure_forecast_preregistration as module
    monkeypatch.setattr(module, "_MAX_SIDECAR_BYTES", 4)
    with pytest.raises(PredictionFailureForecastPreregistrationIntegrityError, match="size"):
        read_prediction_failure_forecast_preregistration(path)


def test_forecast_preregistration_failed_replace_leaves_no_partial_state(tmp_path, monkeypatch):
    kernel, _, kwargs, _, _, ledgers = _inputs(tmp_path, 7708, "improved")
    before = kernel.fingerprint(), tuple(l.fingerprint() for l in ledgers)
    source_bytes = {str(p): p.read_bytes() for k, p in kwargs.items() if k != "kernel"}
    import verdant_obligations.prediction_failure_trial_plans as module
    def fail(*args, **kw):
        raise OSError("injected forecast-preregistration replace failure")
    monkeypatch.setattr(module.os, "replace", fail)
    path = tmp_path / "failed.vfs"
    with pytest.raises(PredictionFailureForecastPreregistrationIntegrityError):
        PredictionFailureForecastPreregistrar().register(path, **kwargs)
    assert not path.exists() and not tuple(tmp_path.glob(".failed.vfs.*.tmp"))
    assert (kernel.fingerprint(), tuple(l.fingerprint() for l in ledgers)) == before
    assert source_bytes == {str(p): p.read_bytes() for k, p in kwargs.items() if k != "kernel"}
