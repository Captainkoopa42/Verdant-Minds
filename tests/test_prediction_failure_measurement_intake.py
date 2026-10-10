from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

from verdant_kernel import VerdantKernel, load_checkpoint, save_checkpoint
from verdant_kernel.models import canonical_json_bytes, stable_id
from verdant_obligations import (
    PredictionFailureForecastPreregistrar, PredictionFailureMeasurementIntake,
    PredictionFailureMeasurementIntakeIntegrityError, PredictionFailureTrialArmRuntime,
    SimulationLedger, load_prediction_failure_measurement_intake,
    prediction_failure_measurement_intake_bytes, read_prediction_failure_measurement_intake,
    read_prediction_failure_raw_capture, save_prediction_failure_measurement_intake,
)
from verdant_obligations.measurement_intake_cli import main as inspect_capture
from test_prediction_failure_forecast_preregistration import _inputs


def _raw(action_class="guarded-risk", historical="old-decision", origin="simulated"):
    return dict(
        capture_format="verdant-prediction-failure-raw-capture-v1",
        source=dict(source_ref="fixture://synthetic-position", acquisition_id="fixture-acquisition-1",
            acquisition_method="explicitly synthetic test fixture", clock_ref="fixture-clock-1",
            reported_origin=origin, action_class=action_class, quantity="fixture_position", unit="mm"),
        capture_start_ns=100, capture_end_ns=300, expected_sample_count=2,
        samples=[dict(sample_id="s1", decision_event_ref=historical, captured_at_ns=100, unit="mm", value=1.25),
                 dict(sample_id="s2", decision_event_ref="unverified-later-decision", captured_at_ns=300, unit="mm", value=2.5)],
    )


def _prepared(tmp_path: Path, origin="simulated", seed=7801):
    kernel, _, kwargs, _, _, ledgers = _inputs(tmp_path, seed, "unchanged")
    study_path = tmp_path / "study.vfs"
    study = PredictionFailureForecastPreregistrar().register(study_path, **kwargs).declaration
    raw_path = tmp_path / "candidate.json"
    raw_path.write_text(json.dumps(_raw(study.action_class, study.excluded_decision_refs[0], origin), indent=2) + "\n")
    return {**kwargs, "forecast_study_path": study_path, "raw_capture_path": raw_path}, study, ledgers


@pytest.mark.parametrize("origin", ("simulated", "physical_reported", "unknown"))
def test_intake_preserves_raw_bytes_and_never_authenticates_reported_origin(tmp_path, monkeypatch, origin):
    sources, study, ledgers = _prepared(tmp_path, origin)
    kernel = sources["kernel"]
    before = kernel.fingerprint(), tuple(l.fingerprint() for l in ledgers)
    inputs = {str(p): p.read_bytes() for k, p in sources.items() if k != "kernel"}

    def forbidden(*args, **kwargs):
        raise AssertionError("Measurement intake cannot execute, reserve or settle")

    monkeypatch.setattr(PredictionFailureTrialArmRuntime, "execute", forbidden)
    monkeypatch.setattr(SimulationLedger, "reserve", forbidden)
    monkeypatch.setattr(SimulationLedger, "settle", forbidden)
    path = tmp_path / "pilot.vmi"
    envelope = PredictionFailureMeasurementIntake().ingest(path, **sources)
    r = envelope.receipt
    raw = sources["raw_capture_path"].read_bytes()
    assert base64.b64decode(r.raw_capture_base64) == raw
    assert r.raw_capture_sha256 == hashlib.sha256(raw).hexdigest()
    assert r.raw_capture_size == len(raw)
    assert r.capture == read_prediction_failure_raw_capture(sources["raw_capture_path"])
    assert r.study_ref == study.declaration_id
    assert r.study_sha256 == hashlib.sha256(sources["forecast_study_path"].read_bytes()).hexdigest()
    assert r.excluded_historical_decision_refs == study.excluded_decision_refs
    assert r.historical_sample_decision_refs == (study.excluded_decision_refs[0],)
    assert r.unverified_sample_decision_refs == ("unverified-later-decision",)
    assert r.quarantined and r.purpose == "measurement_protocol_pilot_only"
    assert not r.source_authenticated and not r.decision_links_authenticated
    assert not r.physical_evidence_admissible and not r.harm_scoring_implemented
    assert not r.calibration_observed and not r.resolution_contract_satisfied
    assert not r.canonical_commit_permitted and not r.simulation_budget_authorized
    assert r.missing_prerequisites == ("authenticated_acquisition_source", "operational_measurement_protocol", "prospective_forecast_adapter")
    assert load_prediction_failure_measurement_intake(path, **sources) == envelope
    assert PredictionFailureMeasurementIntake().ingest(path, **sources) == envelope
    assert inputs == {str(p): p.read_bytes() for k, p in sources.items() if k != "kernel"}
    assert (kernel.fingerprint(), tuple(l.fingerprint() for l in ledgers)) == before
    assert path.read_bytes() == prediction_failure_measurement_intake_bytes(envelope)


def test_intake_checkpoint_and_mapping_order_replay_without_cost(tmp_path, monkeypatch):
    sources, _, ledgers = _prepared(tmp_path)
    path = tmp_path / "replay.vmi"
    envelope = PredictionFailureMeasurementIntake().ingest(path, **sources)
    before = path.read_bytes(), tuple(l.fingerprint() for l in ledgers)
    checkpoint = tmp_path / "pilot.vdk"
    save_checkpoint(checkpoint, sources["kernel"].snapshot())
    state = load_checkpoint(checkpoint)
    state.evidence = dict(reversed(tuple(state.evidence.items())))
    sources["kernel"] = VerdantKernel.from_state(state)
    monkeypatch.setattr(SimulationLedger, "reserve", lambda *a, **k: pytest.fail("replay reservation"))
    assert load_prediction_failure_measurement_intake(path, **sources) == envelope
    assert PredictionFailureMeasurementIntake().ingest(path, **sources) == envelope
    assert path.read_bytes() == before[0]
    assert tuple(l.fingerprint() for l in ledgers) == before[1]


@pytest.mark.parametrize("attack", (
    "harm_score", "source_authentication", "mixed_unit", "unknown_unit", "reversed_time", "outside_window",
    "duplicate_sample", "missing_sample", "boolean_time", "numeric_string", "boolean_value", "nonfinite",
    "blank_source", "unsupported_format",
))
def test_capture_parser_rejects_ambiguous_supplied_scores_and_incomplete_structure(tmp_path, attack):
    payload = _raw()
    if attack == "harm_score": payload["harm_score"] = 0.8
    elif attack == "source_authentication": payload["source"]["source_authenticated"] = True
    elif attack == "mixed_unit": payload["samples"][1]["unit"] = "m"
    elif attack == "unknown_unit": payload["source"]["unit"] = "unrecognized-unit"
    elif attack == "reversed_time": payload["samples"][1]["captured_at_ns"] = 99
    elif attack == "outside_window": payload["samples"][1]["captured_at_ns"] = 301
    elif attack == "duplicate_sample": payload["samples"][1]["sample_id"] = "s1"
    elif attack == "missing_sample": payload["samples"].pop()
    elif attack == "boolean_time": payload["samples"][0]["captured_at_ns"] = True
    elif attack == "numeric_string": payload["samples"][0]["value"] = "1.25"
    elif attack == "boolean_value": payload["samples"][0]["value"] = True
    elif attack == "nonfinite": payload["samples"][0]["value"] = float("nan")
    elif attack == "blank_source": payload["source"]["source_ref"] = " "
    else: payload["capture_format"] = "caller-owned-unchecked-format"
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload))
    before = path.read_bytes()
    with pytest.raises(PredictionFailureMeasurementIntakeIntegrityError):
        read_prediction_failure_raw_capture(path)
    assert path.read_bytes() == before


def _rehash(payload):
    r = payload["receipt"]
    r["receipt_id"] = stable_id("prediction_failure_measurement_intake", {k: v for k, v in r.items() if k != "receipt_id"})
    payload["receipt_sha256"] = hashlib.sha256(canonical_json_bytes(r)).hexdigest()
    return canonical_json_bytes(payload)


@pytest.mark.parametrize("attack", (
    "authenticated", "admitted", "calibrated", "authority", "budget", "hidden_missing", "quarantine",
    "study", "fingerprint", "exclusions", "raw_origin",
))
def test_rehashed_admission_and_lineage_forgery_cannot_load_or_save(tmp_path, attack):
    sources, _, _ = _prepared(tmp_path)
    envelope = PredictionFailureMeasurementIntake().ingest(tmp_path / "original.vmi", **sources)
    payload = envelope.model_dump(mode="json")
    r = payload["receipt"]
    if attack == "authenticated": r["source_authenticated"] = True
    elif attack == "admitted": r["physical_evidence_admissible"] = True
    elif attack == "calibrated": r["calibration_observed"] = True
    elif attack == "authority": r["resolution_authority_enabled"] = True
    elif attack == "budget": r["simulation_budget_authorized"] = True
    elif attack == "hidden_missing": r["missing_prerequisites"] = []
    elif attack == "quarantine": r["quarantined"] = False
    elif attack == "study": r["study_ref"] = "another-study"
    elif attack == "fingerprint": r["canonical_fingerprint"] = "0" * 64
    elif attack == "exclusions":
        r["excluded_historical_decision_refs"] = []
        r["historical_sample_decision_refs"] = []
        r["unverified_sample_decision_refs"] = sorted(s["decision_event_ref"] for s in r["capture"]["samples"])
    else:
        raw = json.loads(base64.b64decode(r["raw_capture_base64"]))
        raw["source"]["reported_origin"] = "physical_reported"
        data = canonical_json_bytes(raw)
        r["raw_capture_base64"] = base64.b64encode(data).decode("ascii")
        r["raw_capture_sha256"] = hashlib.sha256(data).hexdigest()
        r["raw_capture_size"] = len(data)
        r["capture"] = raw
    path = tmp_path / "forged.vmi"
    path.write_bytes(_rehash(payload))
    with pytest.raises(PredictionFailureMeasurementIntakeIntegrityError):
        load_prediction_failure_measurement_intake(path, **sources)
    # Save also revalidates bypassed models, including fully self-consistent raw substitutions.
    original = envelope.receipt.model_dump(mode="json")
    updates = {k: v for k, v in r.items() if v != original[k]}
    for field in ("excluded_historical_decision_refs", "historical_sample_decision_refs",
                  "unverified_sample_decision_refs", "missing_prerequisites"):
        if field in updates:
            updates[field] = tuple(updates[field])
    if "capture" in updates:
        source = envelope.receipt.capture.source.model_copy(update={"reported_origin": "physical_reported"})
        updates["capture"] = envelope.receipt.capture.model_copy(update={"source": source})
    forged_receipt = envelope.receipt.model_copy(update=updates)
    forged = envelope.model_copy(update={"receipt": forged_receipt, "receipt_sha256": payload["receipt_sha256"]})
    with pytest.raises(PredictionFailureMeasurementIntakeIntegrityError):
        save_prediction_failure_measurement_intake(tmp_path / "saved-forgery.vmi", forged, **sources)
    assert not (tmp_path / "saved-forgery.vmi").exists()


@pytest.mark.parametrize("source", ("raw_bytes", "raw_missing", "stale_kernel", "foreign_study", "action_class"))
def test_intake_requires_exact_original_sources(tmp_path, source):
    sources, _, _ = _prepared(tmp_path)
    path = tmp_path / "bound.vmi"
    envelope = PredictionFailureMeasurementIntake().ingest(path, **sources)
    if source == "raw_bytes": sources["raw_capture_path"].write_bytes(sources["raw_capture_path"].read_bytes() + b"\n")
    elif source == "raw_missing": sources["raw_capture_path"].unlink()
    elif source == "stale_kernel": sources["kernel"].state.cycle += 1
    elif source == "foreign_study":
        foreign, _, _ = _prepared(tmp_path / "foreign", seed=7802)
        sources["forecast_study_path"] = foreign["forecast_study_path"]
    else:
        raw = json.loads(sources["raw_capture_path"].read_bytes())
        raw["source"]["action_class"] = "different-action-class"
        sources["raw_capture_path"].write_bytes(canonical_json_bytes(raw))
    assert read_prediction_failure_measurement_intake(path) == envelope
    with pytest.raises(PredictionFailureMeasurementIntakeIntegrityError):
        load_prediction_failure_measurement_intake(path, **sources)


def test_intake_rejects_duplicate_keys_size_path_aliases_and_noncanonical_sidecars(tmp_path):
    sources, _, _ = _prepared(tmp_path)
    raw_path = sources["raw_capture_path"]
    raw_path.write_bytes(b'{"capture_format":"a","capture_format":"b"}')
    with pytest.raises(PredictionFailureMeasurementIntakeIntegrityError): read_prediction_failure_raw_capture(raw_path)
    raw_path.write_bytes(b" " * (1024 * 1024 + 1))
    with pytest.raises(PredictionFailureMeasurementIntakeIntegrityError): read_prediction_failure_raw_capture(raw_path)
    raw_path.write_bytes(canonical_json_bytes(_raw(sources["kernel"].state.governance_outcomes[-1].action_class)))
    path = tmp_path / "valid.vmi"
    envelope = PredictionFailureMeasurementIntake().ingest(path, **sources)
    before = raw_path.read_bytes()
    for output in (raw_path, sources["forecast_study_path"], sources["completed_result_path"]):
        with pytest.raises(PredictionFailureMeasurementIntakeIntegrityError):
            PredictionFailureMeasurementIntake().ingest(output, **sources)
    assert raw_path.read_bytes() == before
    occupied = tmp_path / "occupied.vmi"
    occupied.write_bytes(b"keep")
    with pytest.raises(PredictionFailureMeasurementIntakeIntegrityError): PredictionFailureMeasurementIntake().ingest(occupied, **sources)
    assert occupied.read_bytes() == b"keep"
    path.write_bytes(json.dumps(envelope.model_dump(mode="json"), indent=2).encode())
    with pytest.raises(PredictionFailureMeasurementIntakeIntegrityError): read_prediction_failure_measurement_intake(path)
    path.write_bytes(b" " * (8 * 1024 * 1024 + 1))
    with pytest.raises(PredictionFailureMeasurementIntakeIntegrityError): read_prediction_failure_measurement_intake(path)


def test_intake_pre_replace_failure_preserves_all_sources_and_state(tmp_path, monkeypatch):
    sources, _, ledgers = _prepared(tmp_path)
    before = sources["kernel"].fingerprint(), tuple(l.fingerprint() for l in ledgers)
    inputs = {str(p): p.read_bytes() for k, p in sources.items() if k != "kernel"}

    def fail(*args): raise OSError("injected pre-replace failure")

    monkeypatch.setattr("verdant_obligations.prediction_failure_trial_plans.os.replace", fail)
    path = tmp_path / "failed.vmi"
    with pytest.raises(PredictionFailureMeasurementIntakeIntegrityError): PredictionFailureMeasurementIntake().ingest(path, **sources)
    assert not path.exists() and not list(tmp_path.glob(".failed.vmi.*.tmp"))
    assert inputs == {str(p): p.read_bytes() for k, p in sources.items() if k != "kernel"}
    assert before == (sources["kernel"].fingerprint(), tuple(l.fingerprint() for l in ledgers))


def test_capture_inspection_cli_reports_quarantine_and_invalid_exit_code(tmp_path, capsys):
    path = tmp_path / "candidate.json"
    path.write_bytes(canonical_json_bytes(_raw(origin="physical_reported")))
    assert inspect_capture([str(path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "quarantined" and report["sample_count"] == 2
    assert not report["source_authenticated"] and not report["physical_evidence_admissible"]
    assert not report["harm_scoring_implemented"] and not report["calibration_observed"]
    path.write_bytes(b"not json")
    assert inspect_capture([str(path)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid"
