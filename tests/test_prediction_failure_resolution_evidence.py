from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from verdant_kernel import EvidenceKind, VerdantKernel, load_checkpoint, save_checkpoint
from verdant_kernel.models import canonical_json_bytes, stable_id
from verdant_obligations import (
    PREDICTION_FAILURE_UNPROVEN_RESOLUTION_REQUIREMENTS,
    PredictionFailureResolutionEvidenceDeriver,
    PredictionFailureResolutionEvidenceRecorder,
    PredictionFailureResolutionEvidenceIntegrityError,
    PredictionFailureResolutionRequirement as Requirement,
    PredictionFailureRiskReceiptRecorder, PredictionFailureTrialArmRuntime,
    PredictionFailureTrialRunner, SimulationLedger,
    load_prediction_failure_resolution_evidence,
    prediction_failure_resolution_evidence_bytes,
    read_prediction_failure_resolution_evidence,
    save_prediction_failure_resolution_evidence,
)
from test_prediction_failure_hypotheses import _evidence, _risk_prior_fixture
from test_prediction_failure_trial_runner import _inputs, _positive_inputs, _rehash


def _completed(tmp_path: Path, mode="insufficient", seed=7601):
    if mode == "improved":
        kernel, bundle, _, _, prereg, plan, _ = _risk_prior_fixture(
            tmp_path, seed, prior_harm_score=0.2, declared_harm_risk=0.3,
            target_harm_score=0.0)
        risk = tmp_path / "improved.vfr"
        PredictionFailureRiskReceiptRecorder().record(
            risk, kernel=kernel, plan_path=plan, preregistration_path=prereg)
        kwargs = dict(kernel=kernel, risk_receipt_path=risk, plan_path=plan,
                      preregistration_path=prereg)
    elif mode == "worsened":
        kernel, bundle, kwargs = _positive_inputs(tmp_path, seed)
    else:
        kernel, bundle, kwargs = _inputs(tmp_path, seed, supported=mode == "unchanged")
    ledgers = tuple(SimulationLedger() for _ in range(3))
    path = tmp_path / "completed.vft"
    completed = PredictionFailureTrialRunner().run(path, ledgers=ledgers, **kwargs)
    return kernel, bundle, {**kwargs, "completed_result_path": path}, completed, ledgers


@pytest.mark.parametrize("mode,changed,improved,reduction", (
    ("insufficient", False, False, None),
    ("unchanged", False, False, 0.0),
    ("worsened", True, False, -0.14),
    ("improved", True, True, 0.14),
))
def test_resolution_coverage_keeps_native_outcomes_and_missing_proof_explicit(
    tmp_path, mode, changed, improved, reduction,
):
    kernel, bundle, kwargs, completed, ledgers = _completed(tmp_path, mode)
    canonical_before = kernel.fingerprint()
    source_bytes = {str(p): p.read_bytes() for k, p in kwargs.items() if k != "kernel"}
    ledger_before = tuple(l.fingerprint() for l in ledgers)
    receipt = PredictionFailureResolutionEvidenceDeriver().derive(**kwargs)
    path = tmp_path / "coverage.vfe"
    envelope = PredictionFailureResolutionEvidenceRecorder().record(path, **kwargs)
    assert receipt == envelope.receipt
    assert receipt.completed_result == completed.result
    assert receipt.completed_result_sha256 == hashlib.sha256(
        kwargs["completed_result_path"].read_bytes()).hexdigest()
    assert receipt.target_error_change_observed == changed
    assert receipt.proxy_error_reduction_observed == improved
    if reduction is None:
        assert receipt.signed_proxy_error_reduction is None
    else:
        assert receipt.signed_proxy_error_reduction == pytest.approx(reduction)
    if improved:
        assert completed.result.observed_harm_score == 0.0
        assert completed.result.absolute_errors == pytest.approx((0.3, 0.16, 0.3))
    grounded, missing = set(receipt.grounded_requirements), set(receipt.missing_requirements)
    assert grounded.isdisjoint(missing) and grounded | missing == set(Requirement)
    assert set(PREDICTION_FAILURE_UNPROVEN_RESOLUTION_REQUIREMENTS).issubset(missing)
    assert (Requirement.TARGET_SPECIFIC_ERROR_CHANGE in grounded) == changed
    assert (Requirement.ERROR_REDUCTION in grounded) == improved
    assert (Requirement.SUFFICIENT_PREDICTION_EVIDENCE in grounded) == (mode != "insufficient")
    assert Requirement.VALID_NULL in grounded
    assert receipt.protected_evidence_refs == bundle.evidence_receipt.protected_evidence_refs
    assert set(receipt.protected_evidence_refs).issubset(kernel.state.evidence)
    assert receipt.trace_refs == tuple(t.trace_id for t in completed.result.traces)
    assert receipt.settlement_refs == tuple(t.native_trace.settlement_id for t in completed.result.traces)
    assert receipt.reservation_refs == tuple(t.native_trace.reservation_id for t in completed.result.traces)
    assert receipt.observation_refs == tuple(
        t.prediction_failure_trial_observation.observation_id for t in completed.result.traces)
    assert not receipt.resolution_contract_satisfied and not receipt.resolution_trial_ready
    assert receipt.simulated_only and not receipt.causal_attribution_enabled
    assert not receipt.observed_outcome_authority_enabled and not receipt.resolution_authority_enabled
    assert not receipt.canonical_commit_permitted and not receipt.policy_rewrite_authority_enabled
    assert not receipt.declaration.trial_executed
    assert not receipt.completed_result.risk_receipt.matched_trial_executed
    assert len(receipt.declaration.hypothesis_bundle.hypotheses) == 3
    assert kernel.fingerprint() == canonical_before
    assert tuple(l.fingerprint() for l in ledgers) == ledger_before
    assert source_bytes == {str(p): p.read_bytes() for k, p in kwargs.items() if k != "kernel"}
    assert load_prediction_failure_resolution_evidence(path, **kwargs) == envelope


def test_resolution_coverage_checkpoint_replay_never_executes_or_charges(tmp_path, monkeypatch):
    kernel, _, kwargs, _, ledgers = _completed(tmp_path, "improved", 7602)
    path = tmp_path / "replay.vfe"
    original = PredictionFailureResolutionEvidenceRecorder().record(path, **kwargs)
    data = path.read_bytes()
    ledger_before = tuple(l.fingerprint() for l in ledgers)
    checkpoint = tmp_path / "saved.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    state = load_checkpoint(checkpoint)
    state.evidence = dict(reversed(tuple(state.evidence.items())))
    state.obligation_kernels = dict(reversed(tuple(state.obligation_kernels.items())))
    kwargs["kernel"] = VerdantKernel.from_state(state)

    def forbidden(*args, **kw):
        raise AssertionError("Coverage replay must not execute, reserve or settle")

    monkeypatch.setattr(PredictionFailureTrialArmRuntime, "execute", forbidden)
    monkeypatch.setattr(SimulationLedger, "reserve", forbidden)
    monkeypatch.setattr(SimulationLedger, "settle", forbidden)
    assert load_prediction_failure_resolution_evidence(path, **kwargs) == original
    assert PredictionFailureResolutionEvidenceDeriver().derive(**kwargs) == original.receipt
    assert PredictionFailureResolutionEvidenceRecorder().record(path, **kwargs) == original
    assert path.read_bytes() == data == prediction_failure_resolution_evidence_bytes(original)
    assert kwargs["kernel"].fingerprint() == kernel.fingerprint()
    assert tuple(l.fingerprint() for l in ledgers) == ledger_before


def _rehash_coverage(payload):
    receipt = payload["receipt"]
    receipt["receipt_id"] = stable_id("prediction_failure_resolution_evidence_receipt",
        {k: v for k, v in receipt.items() if k != "receipt_id"})
    payload["receipt_sha256"] = hashlib.sha256(canonical_json_bytes(receipt)).hexdigest()
    return canonical_json_bytes(payload)


@pytest.mark.parametrize("attack", (
    "hidden_missing", "synthetic_pass", "change", "direction", "signed_reduction",
    "protected", "observation_ref", "settlement_ref", "result_hash",
    "observed_authority", "resolution_authority", "canonical_authority",
))
def test_resolution_coverage_rehashed_forgery_is_not_evidence(tmp_path, attack):
    _, _, kwargs, _, _ = _completed(tmp_path, "worsened", 7603)
    original_path = tmp_path / "original.vfe"
    envelope = PredictionFailureResolutionEvidenceRecorder().record(original_path, **kwargs)
    payload = envelope.model_dump(mode="json")
    receipt = payload["receipt"]
    if attack == "hidden_missing":
        receipt["missing_requirements"].remove("calibrated_physical_prediction")
    elif attack == "synthetic_pass":
        receipt["grounded_requirements"] = sorted(item.value for item in Requirement)
        receipt["missing_requirements"] = []
        receipt["resolution_contract_satisfied"] = receipt["resolution_trial_ready"] = True
    elif attack == "change":
        receipt["target_error_change_observed"] = False
    elif attack == "direction":
        receipt["proxy_error_reduction_observed"] = True
    elif attack == "signed_reduction":
        receipt["signed_proxy_error_reduction"] = 0.14
    elif attack == "protected":
        receipt["protected_evidence_refs"] = receipt["protected_evidence_refs"][1:]
    elif attack == "observation_ref":
        receipt["observation_refs"][1] = receipt["observation_refs"][0]
    elif attack == "settlement_ref":
        receipt["settlement_refs"][1] = receipt["settlement_refs"][0]
    elif attack == "result_hash":
        receipt["completed_result_sha256"] = "0" * 64
    elif attack == "observed_authority":
        receipt["observed_outcome_authority_enabled"] = True
    elif attack == "resolution_authority":
        receipt["resolution_authority_enabled"] = True
    else:
        receipt["canonical_commit_permitted"] = True
    path = tmp_path / "forged.vfe"
    data = _rehash_coverage(payload)
    path.write_bytes(data)
    with pytest.raises(PredictionFailureResolutionEvidenceIntegrityError):
        read_prediction_failure_resolution_evidence(path)
    with pytest.raises(PredictionFailureResolutionEvidenceIntegrityError):
        load_prediction_failure_resolution_evidence(path, **kwargs)
    # model_construct cannot bypass provenance-aware save's revalidation.
    # Bypass construction with otherwise correctly typed nested records.
    original = envelope.receipt.model_dump(mode="json")
    updates = {k: v for k, v in receipt.items() if v != original[k]}
    for key in ("grounded_requirements", "missing_requirements"):
        if key in updates:
            updates[key] = tuple(Requirement(v) for v in updates[key])
    for key in ("protected_evidence_refs", "observation_refs", "settlement_refs"):
        if key in updates:
            updates[key] = tuple(updates[key])
    forged = envelope.model_copy(update={
        "receipt": envelope.receipt.model_copy(update=updates),
        "receipt_sha256": payload["receipt_sha256"],
    })
    with pytest.raises(PredictionFailureResolutionEvidenceIntegrityError):
        save_prediction_failure_resolution_evidence(tmp_path / "saved-forgery.vfe", forged, **kwargs)
    assert not (tmp_path / "saved-forgery.vfe").exists()


@pytest.mark.parametrize("attack", ("invalid_null", "arm_swap", "policy", "foreign_ledger", "missing_observation"))
def test_resolution_coverage_rejects_unvalidated_completed_trial(tmp_path, attack):
    kernel, _, kwargs, completed, ledgers = _completed(tmp_path, "unchanged", 7604)
    before = kernel.fingerprint(), tuple(l.fingerprint() for l in ledgers)
    payload = completed.model_dump(mode="json")
    result = payload["result"]
    if attack == "invalid_null":
        observation = result["traces"][2]["prediction_failure_trial_observation"]
        observation["predicted_harm_score"] = 0.5
        observation["risk_projection"]["predicted_harm_score"] = 0.5
        result["absolute_errors"][2] = 0.8 - 0.5
        result["valid_null_error_delta"] = abs(result["absolute_errors"][2] - result["absolute_errors"][0])
        result["disposition"] = "invalid_valid_null"
    elif attack == "arm_swap":
        result["traces"][1], result["traces"][2] = result["traces"][2], result["traces"][1]
    elif attack == "policy":
        result["outcome_policy"]["target_error_change_threshold"] = 0.01
    elif attack == "foreign_ledger":
        _, _, _, foreign, _ = _completed(tmp_path / "foreign", "unchanged", 7605)
        result["traces"][0]["ledger"] = foreign.result.traces[0].ledger.model_dump(mode="json")
    else:
        result["traces"][0].pop("prediction_failure_trial_observation")
    forged = tmp_path / "forged.vft"
    if attack == "missing_observation":
        # No observation exists to hash: canonical JSON cannot make it evidence.
        forged.write_bytes(canonical_json_bytes(payload))
    else:
        forged.write_bytes(_rehash(payload))
    with pytest.raises(PredictionFailureResolutionEvidenceIntegrityError):
        PredictionFailureResolutionEvidenceRecorder().record(
            tmp_path / "blocked.vfe", **{**kwargs, "completed_result_path": forged})
    assert not (tmp_path / "blocked.vfe").exists()
    assert (kernel.fingerprint(), tuple(l.fingerprint() for l in ledgers)) == before


@pytest.mark.parametrize("source", ("foreign", "stale", "missing", "swapped_result"))
def test_resolution_coverage_requires_exact_recoverable_source_context(tmp_path, source):
    kernel, _, kwargs, _, _ = _completed(tmp_path, "unchanged", 7606)
    path = tmp_path / "paired.vfe"
    envelope = PredictionFailureResolutionEvidenceRecorder().record(path, **kwargs)
    data = path.read_bytes()
    if source == "foreign":
        _, _, kwargs, _, _ = _completed(tmp_path / "foreign", "unchanged", 7607)
    elif source == "stale":
        stale = VerdantKernel.from_state(kernel.snapshot())
        _evidence(stale, "later-source", EvidenceKind.OBSERVATION)
        kwargs["kernel"] = stale
    elif source == "missing":
        kwargs["risk_receipt_path"].unlink()
    else:
        _, _, foreign, _, _ = _completed(tmp_path / "foreign", "unchanged", 7607)
        kwargs["completed_result_path"] = foreign["completed_result_path"]
    assert read_prediction_failure_resolution_evidence(path) == envelope
    before = kwargs["kernel"].fingerprint()
    with pytest.raises(PredictionFailureResolutionEvidenceIntegrityError):
        load_prediction_failure_resolution_evidence(path, **kwargs)
    assert kwargs["kernel"].fingerprint() == before and path.read_bytes() == data


def test_resolution_coverage_sidecar_is_canonical_bounded_and_immutable(tmp_path, monkeypatch):
    _, _, kwargs, _, _ = _completed(tmp_path, "unchanged", 7608)
    path = tmp_path / "immutable.vfe"
    envelope = PredictionFailureResolutionEvidenceRecorder().record(path, **kwargs)
    data = path.read_bytes()
    for altered in (b" " + data, data[:-1] + b"!",
                    json.dumps(envelope.model_dump(mode="json"), indent=2).encode()):
        bad = tmp_path / "bad.vfe"
        bad.write_bytes(altered)
        with pytest.raises(PredictionFailureResolutionEvidenceIntegrityError):
            read_prediction_failure_resolution_evidence(bad)
    for key, input_path in kwargs.items():
        if key != "kernel":
            before = input_path.read_bytes()
            with pytest.raises(PredictionFailureResolutionEvidenceIntegrityError, match="separate"):
                PredictionFailureResolutionEvidenceRecorder().record(input_path, **kwargs)
            assert input_path.read_bytes() == before
    occupied = tmp_path / "occupied.vfe"
    occupied.write_bytes(b"occupied")
    with pytest.raises(PredictionFailureResolutionEvidenceIntegrityError):
        PredictionFailureResolutionEvidenceRecorder().record(occupied, **kwargs)
    assert occupied.read_bytes() == b"occupied"
    _, _, foreign, _, _ = _completed(tmp_path / "foreign", "unchanged", 7609)
    with pytest.raises(PredictionFailureResolutionEvidenceIntegrityError):
        PredictionFailureResolutionEvidenceRecorder().record(path, **foreign)
    assert path.read_bytes() == data
    import verdant_obligations.prediction_failure_resolution_evidence as module
    monkeypatch.setattr(module, "_MAX_SIDECAR_BYTES", 4)
    with pytest.raises(PredictionFailureResolutionEvidenceIntegrityError, match="size"):
        read_prediction_failure_resolution_evidence(path)


def test_resolution_coverage_failed_replace_preserves_all_input_and_ledger_state(tmp_path, monkeypatch):
    kernel, _, kwargs, _, ledgers = _completed(tmp_path, "improved", 7610)
    before = kernel.fingerprint(), tuple(l.fingerprint() for l in ledgers)
    inputs = {str(p): p.read_bytes() for k, p in kwargs.items() if k != "kernel"}
    import verdant_obligations.prediction_failure_trial_plans as module

    def fail(*args, **kw):
        raise OSError("injected coverage pre-replace failure")

    monkeypatch.setattr(module.os, "replace", fail)
    path = tmp_path / "failed.vfe"
    with pytest.raises(PredictionFailureResolutionEvidenceIntegrityError):
        PredictionFailureResolutionEvidenceRecorder().record(path, **kwargs)
    assert not path.exists() and not tuple(tmp_path.glob(".failed.vfe.*.tmp"))
    assert (kernel.fingerprint(), tuple(l.fingerprint() for l in ledgers)) == before
    assert inputs == {str(p): p.read_bytes() for k, p in kwargs.items() if k != "kernel"}
