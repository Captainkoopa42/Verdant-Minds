from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from verdant_kernel import VerdantKernel, load_checkpoint, save_checkpoint
from verdant_kernel.models import canonical_json_bytes, stable_id
from verdant_obligations import (
    PredictionFailureGovernanceRiskOperator, PredictionFailureRiskReceiptRecorder,
    PredictionFailureTrialArmRuntime, PredictionFailureTrialDisposition,
    PredictionFailureTrialRunner, PredictionFailureTrialResultIntegrityError,
    SimulationLedger, load_prediction_failure_trial_result,
    read_prediction_failure_trial_result, prediction_failure_trial_result_bytes,
)
from test_prediction_failure_hypotheses import (
    _evidence, _risk_receipt_fixture, _risk_prior_fixture,
)


def _inputs(tmp_path: Path, seed=7502, supported=False):
    if not supported:
        kernel, bundle, prereg, plan, risk, _ = _risk_receipt_fixture(tmp_path, seed)
    else:
        kernel, bundle, _, _, prereg, plan, _ = _risk_prior_fixture(tmp_path, seed)
        risk = tmp_path / "prior.vfr"
        PredictionFailureRiskReceiptRecorder().record(
            risk, kernel=kernel, plan_path=plan, preregistration_path=prereg,
        )
    return kernel, bundle, dict(kernel=kernel, risk_receipt_path=risk,
                               plan_path=plan, preregistration_path=prereg)


def _positive_inputs(tmp_path: Path, seed=7509):
    kernel, bundle, _, _, prereg, plan, _ = _risk_prior_fixture(
        tmp_path, seed, prior_harm_score=0.2, declared_harm_risk=0.3,
    )
    risk = tmp_path / "positive.vfr"
    PredictionFailureRiskReceiptRecorder().record(
        risk, kernel=kernel, plan_path=plan, preregistration_path=prereg,
    )
    return kernel, bundle, dict(kernel=kernel, risk_receipt_path=risk,
                               plan_path=plan, preregistration_path=prereg)


def test_trial_native_declared_risk_effect_is_simulated_only(tmp_path):
    kernel, _, kwargs = _positive_inputs(tmp_path)
    before = kernel.fingerprint()
    result = PredictionFailureTrialRunner().run(tmp_path / "positive.vft", **kwargs).result
    assert result.disposition == PredictionFailureTrialDisposition.TARGET_ERROR_CHANGED
    scores = tuple(t.prediction_failure_trial_observation.predicted_harm_score for t in result.traces)
    assert scores == pytest.approx((0.3, 0.16, 0.3))
    assert result.absolute_errors == pytest.approx((0.5, 0.64, 0.5))
    assert result.target_error_delta == pytest.approx(0.14)
    assert result.valid_null_error_delta == 0
    assert not result.causal_attribution_enabled and not result.resolution_authority_enabled
    assert kernel.fingerprint() == before


def _rehash(payload):
    result = payload["result"]
    for trace in result["traces"]:
        observation = trace["prediction_failure_trial_observation"]
        projection = observation["risk_projection"]
        projection["projection_id"] = stable_id("prediction_failure_risk_projection",
            {k: v for k, v in projection.items() if k != "projection_id"})
        observation["observation_id"] = stable_id("prediction_failure_trial_observation",
            {k: v for k, v in observation.items() if k != "observation_id"})
        trace["trace_id"] = stable_id("prediction_failure_trial_execution_trace",
            {k: v for k, v in trace.items() if k != "trace_id"})
    result["result_id"] = stable_id("prediction_failure_trial_result",
        {k: v for k, v in result.items() if k != "result_id"})
    payload["result_sha256"] = hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    return canonical_json_bytes(payload)


@pytest.mark.parametrize("supported", (False, True))
def test_trial_executes_separate_ledgers_and_preserves_explicit_outcomes(
    tmp_path, monkeypatch, supported,
):
    kernel, bundle, kwargs = _inputs(tmp_path, 7502, supported)
    before = kernel.fingerprint()
    sources = {str(p): p.read_bytes() for k, p in kwargs.items() if k != "kernel"}
    ledgers = tuple(SimulationLedger() for _ in range(3))
    reserve, settle = SimulationLedger.reserve, SimulationLedger.settle
    evaluate = PredictionFailureGovernanceRiskOperator.evaluate
    active, observations = [], []

    def begin(self, **kw):
        value = reserve(self, **kw)
        active.append(self)
        return value

    def observe(self, **kw):
        if active:
            assert len(active) == 1 and len(active[0].state.reservations) == 1
            assert not active[0].state.settlements
            observations.append(id(active[0]))
        return evaluate(self, **kw)

    def finish(self, **kw):
        assert active.pop() is self
        return settle(self, **kw)

    monkeypatch.setattr(SimulationLedger, "reserve", begin)
    monkeypatch.setattr(SimulationLedger, "settle", finish)
    monkeypatch.setattr(PredictionFailureGovernanceRiskOperator, "evaluate", observe)
    envelope = PredictionFailureTrialRunner().run(tmp_path / "trial.vft", ledgers=ledgers, **kwargs)
    result = envelope.result
    assert len(set(observations)) == 3
    assert result.matched_trial_executed and result.simulated_only
    assert result.total_consumed_budget == 0.045
    assert all(len(l.state.reservations) == len(l.state.settlements) == 1 for l in ledgers)
    assert len({t.native_plan.plan_id for t in result.traces}) == 3
    assert len({t.shared_design_seed for t in result.traces}) == 1
    if supported:
        assert result.disposition == PredictionFailureTrialDisposition.TARGET_ERROR_UNCHANGED
        assert result.target_error_delta == result.valid_null_error_delta == 0
        assert all(t.prediction_failure_trial_observation.predicted_harm_score
                   == pytest.approx(0.64) for t in result.traces)
    else:
        assert result.disposition == PredictionFailureTrialDisposition.INSUFFICIENT_EVIDENCE
        assert result.absolute_errors[1] is None and result.target_error_delta is None
        assert result.valid_null_error_delta == 0
    assert all(bundle.evidence_receipt.outcome_ref not in
               t.prediction_failure_trial_observation.risk_projection.supporting_refs
               for t in result.traces)
    assert kernel.fingerprint() == before
    assert sources == {str(p): p.read_bytes() for k, p in kwargs.items() if k != "kernel"}
    assert not result.canonical_commit_permitted and not result.resolution_authority_enabled


def test_trial_completed_sidecar_reload_uses_no_simulation(tmp_path, monkeypatch):
    kernel, _, kwargs = _inputs(tmp_path, 7503)
    path = tmp_path / "trial.vft"
    original = PredictionFailureTrialRunner().run(path, **kwargs)
    data = path.read_bytes()
    checkpoint = tmp_path / "trial.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    state = load_checkpoint(checkpoint)
    state.evidence = dict(reversed(tuple(state.evidence.items())))
    restored = VerdantKernel.from_state(state)
    kwargs["kernel"] = restored

    def forbidden(*args, **kw):
        raise AssertionError("Completed trial replay must not execute or reserve")

    monkeypatch.setattr(PredictionFailureTrialArmRuntime, "execute", forbidden)
    monkeypatch.setattr(SimulationLedger, "reserve", forbidden)
    assert load_prediction_failure_trial_result(path, **kwargs) == original
    assert PredictionFailureTrialRunner().run(path, **kwargs) == original
    assert path.read_bytes() == data == prediction_failure_trial_result_bytes(original)
    assert restored.fingerprint() == kernel.fingerprint()


@pytest.mark.parametrize("failure", ("second_arm", "replace", "canonical_leak"))
def test_trial_failure_publishes_no_partial_caller_state(tmp_path, monkeypatch, failure):
    kernel, _, kwargs = _inputs(tmp_path, 7504)
    before = kernel.fingerprint()
    ledgers = tuple(SimulationLedger() for _ in range(3))
    originals = tuple(l.fingerprint() for l in ledgers)
    execute = PredictionFailureTrialArmRuntime.execute
    count = 0

    def injected(self, **kw):
        nonlocal count
        count += 1
        if count == 2:
            if failure == "second_arm":
                raise RuntimeError("injected second-arm failure")
            if failure == "canonical_leak":
                from verdant_kernel import EvidenceKind
                _evidence(kw["kernel"], "injected-private-leak", EvidenceKind.OBSERVATION)
        return execute(self, **kw)

    monkeypatch.setattr(PredictionFailureTrialArmRuntime, "execute", injected)
    if failure == "replace":
        import verdant_obligations.prediction_failure_trial_plans as module
        def fail(*args, **kw):
            raise OSError("injected replace failure")
        monkeypatch.setattr(module.os, "replace", fail)
    path = tmp_path / "failed.vft"
    with pytest.raises(PredictionFailureTrialResultIntegrityError):
        PredictionFailureTrialRunner().run(path, ledgers=ledgers, **kwargs)
    assert not path.exists()
    assert tuple(l.fingerprint() for l in ledgers) == originals
    assert kernel.fingerprint() == before
    assert not tuple(tmp_path.glob(".failed.vft.*.tmp"))


def test_trial_rejects_shared_nonpristine_and_foreign_ledgers_or_sources(tmp_path):
    kernel, _, kwargs = _inputs(tmp_path, 7505)
    shared = SimulationLedger()
    with pytest.raises(PredictionFailureTrialResultIntegrityError, match="pristine"):
        PredictionFailureTrialRunner().run(tmp_path / "shared.vft", ledgers=(shared, shared, shared), **kwargs)
    used = tuple(SimulationLedger() for _ in range(3))
    PredictionFailureTrialRunner().run(tmp_path / "used.vft", ledgers=used, **kwargs)
    with pytest.raises(PredictionFailureTrialResultIntegrityError, match="pristine"):
        PredictionFailureTrialRunner().run(tmp_path / "again.vft", ledgers=used, **kwargs)
    foreign, _, other = _inputs(tmp_path / "foreign", 7506)
    with pytest.raises(PredictionFailureTrialResultIntegrityError):
        load_prediction_failure_trial_result(tmp_path / "used.vft", **other)
    with pytest.raises(PredictionFailureTrialResultIntegrityError):
        PredictionFailureTrialRunner().run(tmp_path / "foreign.vft", **{**kwargs, "kernel": foreign})
    assert not (tmp_path / "again.vft").exists()
    assert not (tmp_path / "foreign.vft").exists()


@pytest.mark.parametrize("attack", ("score", "observed", "seed", "arm_order", "authority", "budget"))
def test_trial_rehashed_result_forgery_fails(tmp_path, attack):
    _, _, kwargs = _inputs(tmp_path, 7507, supported=True)
    result = PredictionFailureTrialRunner().run(tmp_path / "trial.vft", **kwargs)
    payload = result.model_dump(mode="json")
    data = payload["result"]
    if attack == "score":
        observation = data["traces"][0]["prediction_failure_trial_observation"]
        observation["risk_projection"]["predicted_harm_score"] = 0.9
        observation["predicted_harm_score"] = 0.9
        data["absolute_errors"][0] = abs(0.9 - data["observed_harm_score"])
        data["target_error_delta"] = abs(data["absolute_errors"][1] - data["absolute_errors"][0])
        data["valid_null_error_delta"] = abs(data["absolute_errors"][2] - data["absolute_errors"][0])
        data["disposition"] = "invalid_valid_null"
    elif attack == "observed":
        data["observed_harm_score"] = 0.64
        data["absolute_errors"] = [0, 0, 0]
    elif attack == "seed":
        for t in data["traces"]:
            t["shared_design_seed"] += 1
    elif attack == "arm_order":
        data["traces"][0], data["traces"][2] = data["traces"][2], data["traces"][0]
    elif attack == "authority":
        data["resolution_authority_enabled"] = True
    else:
        data["total_consumed_budget"] = 0
    forged = tmp_path / "forged.vft"
    forged.write_bytes(_rehash(payload))
    with pytest.raises(PredictionFailureTrialResultIntegrityError):
        load_prediction_failure_trial_result(forged, **kwargs)


def test_trial_bytes_size_input_path_and_occupied_output_fail_closed(tmp_path, monkeypatch):
    _, _, kwargs = _inputs(tmp_path, 7508)
    path = tmp_path / "trial.vft"
    envelope = PredictionFailureTrialRunner().run(path, **kwargs)
    data = path.read_bytes()
    for value in (data[:-1] + b"!", b" " + data,
                  json.dumps(envelope.model_dump(mode="json"), indent=2).encode()):
        bad = tmp_path / "bad.vft"
        bad.write_bytes(value)
        with pytest.raises(PredictionFailureTrialResultIntegrityError):
            read_prediction_failure_trial_result(bad)
    with pytest.raises(PredictionFailureTrialResultIntegrityError, match="separate"):
        PredictionFailureTrialRunner().run(kwargs["risk_receipt_path"], **kwargs)
    occupied = tmp_path / "occupied.vft"
    occupied.write_bytes(b"occupied")
    with pytest.raises(PredictionFailureTrialResultIntegrityError):
        PredictionFailureTrialRunner().run(occupied, **kwargs)
    assert occupied.read_bytes() == b"occupied"
    import verdant_obligations.prediction_failure_trial_runner as module
    monkeypatch.setattr(module, "_MAX_SIDECAR_BYTES", 4)
    with pytest.raises(PredictionFailureTrialResultIntegrityError, match="size"):
        read_prediction_failure_trial_result(path)


def test_frozen_outcome_rule_preserves_all_dispositions_and_precedence():
    from verdant_obligations.prediction_failure_trial_runner import _metrics
    from verdant_obligations import PredictionFailureTrialOutcomePolicy
    policy = PredictionFailureTrialOutcomePolicy()
    for scores, expected in (
        ((0.1, None, 0.9), "insufficient_evidence"),
        ((0.1, 0.9, 0.2), "invalid_valid_null"),
        ((0.1, 0.9, 0.1), "target_error_changed"),
        ((0.1, 0.1, 0.1), "target_error_unchanged"),
    ):
        assert _metrics(scores, 0.8, policy)[3].value == expected
