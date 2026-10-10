from __future__ import annotations

import base64
import itertools
import json
from pathlib import Path

import pytest

from verdant_kernel import VerdantKernel, load_checkpoint, save_checkpoint
from verdant_kernel.models import canonical_json_bytes, stable_id
from verdant_obligations import (
    PredictionFailureForecastPreregistrar, PredictionFailureTimingPilot,
    PredictionFailureTimingPilotIntegrityError, PredictionFailureTrialArmRuntime,
    SimulationLedger, load_prediction_failure_timing_pilot,
    prediction_failure_timing_pilot_bytes, read_prediction_failure_timing_pilot,
)
from verdant_obligations import prediction_failure_timing_pilot as module
from verdant_obligations.timing_pilot_cli import main as cli
from test_prediction_failure_forecast_preregistration import _inputs


def _prepared(tmp_path, monkeypatch, seed=7902):
    kernel, _, inputs, _, _, ledgers = _inputs(tmp_path, seed, "unchanged")
    study = tmp_path / "study.vfs"
    PredictionFailureForecastPreregistrar().register(study, **inputs)
    clock = itertools.count(1_000_000, 1_000_000)
    # Synthetic clock values exercise arithmetic; only the separate pilot uses real readings.
    monkeypatch.setattr(module.time, "perf_counter_ns", lambda: next(clock))
    return {**inputs, "forecast_study_path": study}, ledgers


def _forbidden(*args, **kwargs):
    raise AssertionError("Timing replay/intake cannot sample clocks or execute/reserve/settle simulations")


def test_timing_capture_has_fixed_matched_controls_exact_intake_and_zero_leakage(tmp_path, monkeypatch):
    sources, ledgers = _prepared(tmp_path, monkeypatch)
    before = sources["kernel"].fingerprint(), tuple(l.fingerprint() for l in ledgers)
    inputs = {str(p): p.read_bytes() for k, p in sources.items() if k != "kernel"}
    monkeypatch.setattr(PredictionFailureTrialArmRuntime, "execute", _forbidden)
    monkeypatch.setattr(SimulationLedger, "reserve", _forbidden)
    monkeypatch.setattr(SimulationLedger, "settle", _forbidden)
    invoke = module._invoke
    calls, copies = [], {}

    def spy(kernel, plan, prereg):
        calls.append(id(kernel))
        copies[id(kernel)] = kernel
        assert kernel is not sources["kernel"]
        return invoke(kernel, plan, prereg)

    monkeypatch.setattr(module, "_invoke", spy)
    path = tmp_path / "timing.vtp"
    envelope = PredictionFailureTimingPilot().acquire(path, **sources)
    r = envelope.receipt
    assert len(calls) == 14 and len(copies) == 2  # one warmup/role, then twelve timed calls
    assert all(c.fingerprint() == before[0] for c in copies.values())
    assert tuple((s.block, s.role) for s in r.samples) == module._ORDER
    assert all(s.elapsed_ms == 1.0 for s in r.samples)
    assert len({(s.evaluation_ref, s.evaluation_sha256) for s in r.samples}) == 1
    assert r.protocol["duration_equality_required"] is False
    assert r.intake.receipt.historical_sample_decision_refs == (r.source_decision_ref,)
    assert not r.intake.receipt.unverified_sample_decision_refs
    raw = base64.b64decode(r.intake.receipt.raw_capture_base64)
    capture = json.loads(raw)
    assert capture["source"]["unit"] == "ms" and capture["source"]["reported_origin"] == "unknown"
    assert [s["value"] for s in capture["samples"]] == [s.elapsed_ms for s in r.samples]
    assert r.quarantined and not r.source_authenticated and not r.physical_evidence_admissible
    assert not r.study_executed and not r.calibration_observed and not r.resolution_contract_satisfied
    assert not r.simulation_budget_authorized and not r.canonical_commit_permitted
    assert path.read_bytes() == prediction_failure_timing_pilot_bytes(envelope)
    assert before == (sources["kernel"].fingerprint(), tuple(l.fingerprint() for l in ledgers))
    assert inputs == {str(p): p.read_bytes() for k, p in sources.items() if k != "kernel"}


def test_timing_replay_after_checkpoint_mapping_reload_has_no_new_measurement_or_charge(tmp_path, monkeypatch):
    sources, ledgers = _prepared(tmp_path, monkeypatch)
    path = tmp_path / "replay.vtp"
    expected = PredictionFailureTimingPilot().acquire(path, **sources)
    before = path.read_bytes(), tuple(l.fingerprint() for l in ledgers)
    checkpoint = tmp_path / "source.vdk"
    save_checkpoint(checkpoint, sources["kernel"].snapshot())
    state = load_checkpoint(checkpoint)
    state.evidence = dict(reversed(tuple(state.evidence.items())))
    state.governance.learned_action_risk = dict(reversed(tuple(state.governance.learned_action_risk.items())))
    sources["kernel"] = VerdantKernel.from_state(state)
    for target in ("_invoke", "_clock", "_environment"):
        monkeypatch.setattr(module, target, _forbidden)
    monkeypatch.setattr(module.time, "perf_counter_ns", _forbidden)
    monkeypatch.setattr(SimulationLedger, "reserve", _forbidden)
    monkeypatch.setattr(SimulationLedger, "settle", _forbidden)
    monkeypatch.setattr(PredictionFailureTrialArmRuntime, "execute", _forbidden)
    assert load_prediction_failure_timing_pilot(path, **sources) == expected
    assert PredictionFailureTimingPilot().acquire(path, **sources) == expected
    assert before == (path.read_bytes(), tuple(l.fingerprint() for l in ledgers))


def _rehash(payload, refresh_intake=False):
    r = payload["receipt"]
    values = {k: v for k, v in r.items() if k not in ("pilot_id", "acquisition_id", "intake")}
    r["acquisition_id"] = stable_id("prediction_failure_timing_acquisition", values)
    if refresh_intake:
        raw = module._raw(values, r["acquisition_id"])
        i = r["intake"]["receipt"]
        i.update(raw_capture_base64=base64.b64encode(raw).decode("ascii"), raw_capture_size=len(raw),
                 raw_capture_sha256=module._sha(raw), capture=json.loads(raw))
        i["receipt_id"] = stable_id("prediction_failure_measurement_intake",
                                    {k: v for k, v in i.items() if k != "receipt_id"})
        r["intake"]["receipt_sha256"] = module._sha(canonical_json_bytes(i))
    r["pilot_id"] = stable_id("prediction_failure_timing_pilot", {k: v for k, v in r.items() if k != "pilot_id"})
    payload["receipt_sha256"] = module._sha(canonical_json_bytes(r))
    return canonical_json_bytes(payload)


@pytest.mark.parametrize("attack", (
    "elapsed", "overlap", "order", "missing_pair", "boolean_time", "unit", "clock",
    "protocol", "canonical_leak", "authenticate", "admit", "calibrate", "authority", "budget",
))
def test_rehashed_timing_control_arithmetic_and_authority_attacks_fail(tmp_path, monkeypatch, attack):
    sources, _ = _prepared(tmp_path, monkeypatch)
    original = PredictionFailureTimingPilot().acquire(tmp_path / "original.vtp", **sources)
    payload = original.model_dump(mode="json")
    r = payload["receipt"]
    if attack == "elapsed": r["samples"][0]["elapsed_ms"] = 2.0
    elif attack == "overlap":
        r["samples"][1].update(start_ns=1_500_000, end_ns=2_500_000)
    elif attack == "order": r["samples"].reverse()
    elif attack == "missing_pair": r["samples"].pop()
    elif attack == "boolean_time": r["samples"][0]["start_ns"] = True
    elif attack == "unit":
        intake = r["intake"]["receipt"]
        raw = json.loads(base64.b64decode(intake["raw_capture_base64"]))
        raw["source"]["unit"] = "s"
        for sample in raw["samples"]: sample["unit"] = "s"
        data = canonical_json_bytes(raw)
        intake.update(raw_capture_base64=base64.b64encode(data).decode("ascii"),
                      raw_capture_sha256=module._sha(data), raw_capture_size=len(data), capture=raw)
        intake["receipt_id"] = stable_id("prediction_failure_measurement_intake",
                                        {k: v for k, v in intake.items() if k != "receipt_id"})
        r["intake"]["receipt_sha256"] = module._sha(canonical_json_bytes(intake))
    elif attack == "clock": r["clock"]["monotonic"] = False
    elif attack == "protocol": r["protocol"]["pair_count"] = 5
    elif attack == "canonical_leak": r["samples"][0]["canonical_after"] = "0" * 64
    else:
        field = dict(authenticate="source_authenticated", admit="physical_evidence_admissible",
                     calibrate="calibration_observed", authority="resolution_authority_enabled",
                     budget="simulation_budget_authorized")[attack]
        r[field] = True
    path = tmp_path / "forged.vtp"
    path.write_bytes(_rehash(payload))
    with pytest.raises(PredictionFailureTimingPilotIntegrityError):
        load_prediction_failure_timing_pilot(path, **sources)


@pytest.mark.parametrize("attack", ("source_bytes", "foreign_kernel", "foreign_study", "manifest", "lineage", "output"))
def test_timing_requires_exact_external_source_code_and_output_provenance(tmp_path, monkeypatch, attack):
    sources, _ = _prepared(tmp_path, monkeypatch)
    path = tmp_path / "bound.vtp"
    original = PredictionFailureTimingPilot().acquire(path, **sources)
    if attack == "source_bytes": sources["forecast_study_path"].write_bytes(sources["forecast_study_path"].read_bytes() + b"\n")
    elif attack == "foreign_kernel": sources["kernel"].state.cycle += 1
    elif attack == "foreign_study":
        other, _ = _prepared(tmp_path / "other", monkeypatch, 7903)
        sources["forecast_study_path"] = other["forecast_study_path"]
    else:
        p = original.model_dump(mode="json")
        if attack == "manifest": p["receipt"]["code_sources"][-1]["sha256"] = "0" * 64
        elif attack == "lineage": p["receipt"]["source_report_ref"] = "forged-native-report"
        else:
            p["receipt"]["evaluation_sha256"] = "0" * 64
            for s in p["receipt"]["samples"]: s["evaluation_sha256"] = "0" * 64
        path.write_bytes(_rehash(p, refresh_intake=True))
        # Self-consistent checksums alone cannot establish external provenance.
        read_prediction_failure_timing_pilot(path)
    with pytest.raises(PredictionFailureTimingPilotIntegrityError):
        load_prediction_failure_timing_pilot(path, **sources)


@pytest.mark.parametrize("failure", ("private_mutation", "output_drift", "source_drift", "code_drift", "clock_reverse", "replace"))
def test_failed_acquisition_publishes_no_partial_pilot_or_caller_mutation(tmp_path, monkeypatch, failure):
    sources, ledgers = _prepared(tmp_path, monkeypatch)
    before = sources["kernel"].fingerprint(), tuple(l.fingerprint() for l in ledgers)
    original = module._invoke
    manifest = module._code_manifest()
    drifted = False

    def code_manifest():
        if drifted:
            return (*manifest[:-1], manifest[-1].model_copy(update={"sha256": "0" * 64}))
        return manifest

    monkeypatch.setattr(module, "_code_manifest", code_manifest)

    def injected(kernel, plan, prereg):
        nonlocal drifted
        value = original(kernel, plan, prereg)
        if failure == "private_mutation": kernel.state.cycle += 1
        if failure == "output_drift": return value.model_copy(update={"evaluation_id": "forged"})
        if failure == "source_drift": sources["forecast_study_path"].write_bytes(sources["forecast_study_path"].read_bytes() + b"\n")
        if failure == "code_drift": drifted = True
        return value

    monkeypatch.setattr(module, "_invoke", injected)
    if failure == "clock_reverse":
        clock = itertools.cycle((2_000_000, 1_000_000))
        monkeypatch.setattr(module.time, "perf_counter_ns", lambda: next(clock))
    if failure == "replace":
        replace = module._write_immutable.__globals__["os"].replace
        def fail(source, destination):
            if Path(destination) == path: raise OSError("injected final pilot pre-replace failure")
            return replace(source, destination)
        monkeypatch.setattr("verdant_obligations.prediction_failure_trial_plans.os.replace", fail)
    path = tmp_path / "failed.vtp"
    with pytest.raises(PredictionFailureTimingPilotIntegrityError):
        PredictionFailureTimingPilot().acquire(path, **sources)
    assert not path.exists() and not list(tmp_path.glob(".failed.vtp.*.tmp"))
    assert before == (sources["kernel"].fingerprint(), tuple(l.fingerprint() for l in ledgers))


def test_valid_null_matches_outputs_while_elapsed_times_can_differ(tmp_path, monkeypatch):
    sources, _ = _prepared(tmp_path, monkeypatch)
    times = iter(t for i in range(12) for t in (10_000_000 * (i + 1), 10_000_000 * (i + 1) + (i + 1) * 100_000))
    monkeypatch.setattr(module.time, "perf_counter_ns", lambda: next(times))
    result = PredictionFailureTimingPilot().acquire(tmp_path / "varying.vtp", **sources).receipt
    assert len({s.elapsed_ms for s in result.samples}) == 12
    assert len({s.evaluation_sha256 for s in result.samples}) == 1
    assert not result.protocol["duration_equality_required"]


def test_consistent_clock_fabrication_cannot_be_promoted_even_with_all_hashes_updated(tmp_path, monkeypatch):
    sources, _ = _prepared(tmp_path, monkeypatch)
    original = PredictionFailureTimingPilot().acquire(tmp_path / "original.vtp", **sources)
    p = original.model_dump(mode="json")
    # The adapter is not a trusted clock/signature service: internally consistent
    # substituted durations cannot be authenticated from bytes alone.
    for i, s in enumerate(p["receipt"]["samples"]):
        s.update(start_ns=10_000_000 * (i + 1), end_ns=10_000_000 * (i + 1) + 2_000_000, elapsed_ms=2.0)
    path = tmp_path / "self-consistent-untrusted.vtp"
    path.write_bytes(_rehash(p, refresh_intake=True))
    result = load_prediction_failure_timing_pilot(path, **sources).receipt
    assert result.quarantined and not result.source_authenticated and not result.physical_evidence_admissible
    assert not result.calibration_observed and not result.resolution_contract_satisfied


def test_timing_cli_and_immutable_path_guards(tmp_path, monkeypatch, capsys):
    sources, _ = _prepared(tmp_path, monkeypatch)
    path = tmp_path / "pilot.vtp"
    original = PredictionFailureTimingPilot().acquire(path, **sources)
    assert cli(["inspect", str(path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["roles"]["baseline"]["count"] == report["roles"]["valid_null"]["count"] == 6
    assert report["status"] == "quarantined_performance_pilot"
    assert not report["performance_improvement_claim_permitted"]
    checkpoint = tmp_path / "input.vdk"
    save_checkpoint(checkpoint, sources["kernel"].snapshot())
    args = ["replay", str(path), "--checkpoint", str(checkpoint)]
    for name, value in sources.items():
        if name != "kernel": args.extend(("--" + name.removesuffix("_path").replace("_", "-"), str(value)))
    monkeypatch.setattr(module.time, "perf_counter_ns", _forbidden)
    monkeypatch.setattr(module, "_invoke", _forbidden)
    assert cli(args) == 0
    capsys.readouterr()
    args[0] = "acquire"
    assert cli(args) == 0  # occupied valid result replays, never resamples
    capsys.readouterr()
    for output in (sources["forecast_study_path"], sources["plan_path"]):
        before = output.read_bytes()
        with pytest.raises(PredictionFailureTimingPilotIntegrityError): PredictionFailureTimingPilot().acquire(output, **sources)
        assert output.read_bytes() == before
    occupied = tmp_path / "occupied.vtp"
    occupied.write_bytes(b"keep")
    with pytest.raises(PredictionFailureTimingPilotIntegrityError): PredictionFailureTimingPilot().acquire(occupied, **sources)
    assert occupied.read_bytes() == b"keep"
    path.write_bytes(json.dumps(original.model_dump(mode="json"), indent=2).encode())
    assert cli(["inspect", str(path)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid"
    path.write_bytes(b" " * (8 * 1024 * 1024 + 1))
    with pytest.raises(PredictionFailureTimingPilotIntegrityError): read_prediction_failure_timing_pilot(path)


def test_timing_serialization_revalidates_bypassed_models(tmp_path, monkeypatch):
    sources, _ = _prepared(tmp_path, monkeypatch)
    original = PredictionFailureTimingPilot().acquire(tmp_path / "original.vtp", **sources)
    forged = original.model_copy(update={"receipt": original.receipt.model_copy(update={"calibration_observed": True})})
    with pytest.raises(ValueError): prediction_failure_timing_pilot_bytes(forged)


def test_recorded_real_clock_pilot_replays_from_preserved_sources_without_resampling(monkeypatch):
    p = Path(__file__).resolve().parents[1] / "artifacts" / "prediction_failure_timing_v055"
    sources = dict(kernel=VerdantKernel.from_state(load_checkpoint(p / "source.vdk")),
        forecast_study_path=p / "study.vfs", resolution_evidence_path=p / "anchor.vfe",
        completed_result_path=p / "completed.vft", risk_receipt_path=p / "prior.vfr",
        plan_path=p / "prior.vpp", preregistration_path=p / "prior.vfp")
    monkeypatch.setattr(module.time, "perf_counter_ns", _forbidden)
    monkeypatch.setattr(module, "_invoke", _forbidden)
    monkeypatch.setattr(SimulationLedger, "reserve", _forbidden)
    monkeypatch.setattr(SimulationLedger, "settle", _forbidden)
    monkeypatch.setattr(PredictionFailureTrialArmRuntime, "execute", _forbidden)
    expected = read_prediction_failure_timing_pilot(p / "pilot.vtp")
    assert load_prediction_failure_timing_pilot(p / "pilot.vtp", **sources) == expected
    assert PredictionFailureTimingPilot().acquire(p / "pilot.vtp", **sources) == expected
    assert base64.b64decode(expected.receipt.intake.receipt.raw_capture_base64) == (p / "capture.json").read_bytes()
    assert canonical_json_bytes(expected.receipt.intake.model_dump(mode="json")) == (p / "intake.vmi").read_bytes()
    report = json.loads((p / "run.json").read_bytes())
    assert report["canonical_before"] == report["canonical_after"] == sources["kernel"].fingerprint()
    assert report["old_simulation_ledger_fingerprints_before"] == report["old_simulation_ledger_fingerprints_after"]
    assert report["readings_origin"] == "actual_local_time.perf_counter_ns_calls"
    assert report["workload_origin"] == "synthetic_existing_test_fixture"
    assert not report["physical_harm_measured"] and not report["prospective_study_executed"]
