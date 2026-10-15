"""Adversarial checks for the frozen v0.67 successor-retention evaluation."""
from __future__ import annotations

import base64
import inspect
import json
from pathlib import Path

import pytest

from verdant_kernel import checkpoint_bytes
from verdant_kernel.models import canonical_json_bytes
from verdant_math import teaching_pilot as baseline
from verdant_math.successor_repair_adapter import adapter
from verdant_math.successor_repair_evaluation import evaluation as repair_evaluation
from verdant_math.successor_retention_evaluation import evaluation as m
from verdant_math.successor_retention_evaluation.cli import main as cli
from verdant_math.successor_retention_protocol import protocol as retention_protocol


_ROOT = Path(__file__).resolve().parent.parent
_PROTOCOL = _ROOT / "artifacts/terminal_successor_v066/protocol.vsrt"
_HISTORY_RESPONSES = _ROOT / "artifacts/terminal_successor_v065/responses.vsrb"
_HISTORY_EVALUATION = _ROOT / "artifacts/terminal_successor_v065/evaluation.vsrr"
_RESPONSES = _ROOT / "artifacts/terminal_successor_v067/responses.vstrb"
_RESULT = _ROOT / "artifacts/terminal_successor_v067/evaluation.vstrr"
_EXPECTED_RESPONSE_SIZE = 1_252_824
_EXPECTED_RESPONSE_FILE_SHA256 = "2a74ffe901eb8c718b3fc9bf1707cf7a2ec29b9eb31ec61caa34c40b9167f43d"
_EXPECTED_RESPONSE_RECEIPT_SHA256 = "d46f2eef22ba5534046bcc889e5fde4bf0babbdd21116cacfb43db40d940957f"
_EXPECTED_RESULT_SIZE = 21_185
_EXPECTED_RESULT_FILE_SHA256 = "cfcc40f75ca7d03d823748b167907275059c58e2c97c804ee17cf4b2cf369f23"
_EXPECTED_RESULT_RECEIPT_SHA256 = "31b1838ab9dd259da38d27fcf2d8c748216b8af5a26965f8f16aa6fe94de5bbb"


@pytest.fixture(scope="module")
def response_batch():
    return m.load_response_batch(
        _PROTOCOL, _HISTORY_RESPONSES, _HISTORY_EVALUATION, _RESPONSES
    )


@pytest.fixture(scope="module")
def evaluation():
    return m.load_evaluation(
        _PROTOCOL,
        _HISTORY_RESPONSES,
        _HISTORY_EVALUATION,
        _RESPONSES,
        _RESULT,
    )


@pytest.fixture(scope="module")
def history_response():
    return repair_evaluation.ResponseBatchEnvelope.model_validate_json(
        _HISTORY_RESPONSES.read_bytes()
    )


def _arm(batch, role):
    return next(arm for arm in batch.receipt.arms if arm.role == role)


def _grades(evaluation, role):
    return {
        grade.case_ref: grade
        for grade in evaluation.receipt.grades
        if grade.role == role
    }


def _rehash(raw):
    raw["receipt_sha256"] = baseline._sha(canonical_json_bytes(raw["receipt"]))
    return canonical_json_bytes(raw)


def _write(path, data):
    path.write_bytes(data)
    return path


def test_checked_artifacts_are_exact_and_replay(response_batch, evaluation):
    assert len(_RESPONSES.read_bytes()) == _EXPECTED_RESPONSE_SIZE
    assert baseline._sha(_RESPONSES.read_bytes()) == _EXPECTED_RESPONSE_FILE_SHA256
    assert response_batch.receipt_sha256 == _EXPECTED_RESPONSE_RECEIPT_SHA256
    assert len(_RESULT.read_bytes()) == _EXPECTED_RESULT_SIZE
    assert baseline._sha(_RESULT.read_bytes()) == _EXPECTED_RESULT_FILE_SHA256
    assert evaluation.receipt_sha256 == _EXPECTED_RESULT_RECEIPT_SHA256


def test_complete_result_and_full_denominators(response_batch, evaluation):
    summary = m.evaluation_summary(response_batch, evaluation)
    assert summary["responses"] == 80 and summary["grades"] == 48
    assert summary["enrolled_per_role"] == 20
    assert summary["valid_inputs_per_role"] == 12
    assert summary["new_successor_lessons_per_role"] == 0
    assert summary["retained_null_exact"] is True
    assert summary["retained_partial_trace_reuse_observed"] is True
    assert summary["fresh_correct_answer_transfer_observed"] is False
    assert sum(len(arm.responses) for arm in response_batch.receipt.arms) == 80
    assert len(evaluation.receipt.grades) == 48


@pytest.mark.parametrize("role", m._ROLES)
def test_every_role_retains_complete_outcome(role, response_batch, evaluation):
    summary = m.evaluation_summary(response_batch, evaluation)["arms"][role]["total"]
    assert summary == dict(correct=8, incorrect=0, abstained=4, invalid_input=8)
    assert sum(summary.values()) == 20


@pytest.mark.parametrize("role", m._ROLES)
def test_predeclared_groups_are_not_reclassified(role, response_batch, evaluation):
    groups = m.evaluation_summary(response_batch, evaluation)["arms"][role]["groups"]
    assert groups["retained_prerequisite_control"] == dict(
        correct=8, incorrect=0, abstained=0, invalid_input=0
    )
    assert groups["retained_partial_walk"] == dict(
        correct=0, incorrect=0, abstained=2, invalid_input=0
    )
    assert groups["declared_domain_ceiling"] == dict(
        correct=0, incorrect=0, abstained=2, invalid_input=0
    )
    assert groups["invalid_input"] == dict(
        correct=0, incorrect=0, abstained=0, invalid_input=8
    )


@pytest.mark.parametrize("role", m._ROLES)
def test_exact_saved_checkpoint_lineage(role, response_batch, history_response):
    arm = _arm(response_batch, role)
    source = next(
        item
        for item in history_response.receipt.arms
        if item.role == retention_protocol._SOURCE_ROLES[role]
    )
    assert arm.source_role == source.role
    assert arm.source_local_run_ref == source.local_run_ref
    assert arm.checkpoint_base64 == source.checkpoint_base64
    assert arm.checkpoint_sha256 == source.checkpoint_sha256
    assert arm.kernel_fingerprint == source.kernel_fingerprint
    assert arm.lessons == source.lessons
    private = baseline._checkpoint(arm.checkpoint_base64, arm.checkpoint_sha256)
    assert private.fingerprint() == arm.kernel_fingerprint
    assert checkpoint_bytes(private.snapshot()) == base64.b64decode(arm.checkpoint_base64)


@pytest.mark.parametrize("role", m._ROLES)
def test_zero_new_teaching_and_exact_29_saved_slots(role, response_batch):
    arm = _arm(response_batch, role)
    lineage = next(
        item
        for item in response_batch.receipt.frozen_protocol.declaration.checkpoint_lineage
        if item.future_role == role
    )
    assert len(arm.lessons) == lineage.saved_lesson_slots == 29
    assert lineage.new_successor_lessons == 0
    assert lineage.new_teacher_exposures == 0
    assert response_batch.receipt.new_successor_lessons_installed == 0
    assert response_batch.receipt.new_teacher_exposures == 0
    assert response_batch.receipt.new_claim_installations == 0


@pytest.mark.parametrize("case_index", range(12))
def test_original_effective_request_and_order_route(case_index, response_batch):
    for arm in response_batch.receipt.arms:
        response = arm.responses[case_index]
        reply = response.reply
        assert reply.original_request == response.request
        assert reply.order_instruction.status == "valid"
        if response.request.right <= 4:
            assert reply.route_disposition == "kept_valid_original_right"
            assert reply.effective_request == response.request
            assert reply.original_right_lookup.status == "valid"
            assert reply.original_left_lookup is None
        else:
            assert reply.route_disposition == "swapped_missing_original_right"
            assert reply.effective_request == adapter.BoundedAdditionRequestV064(
                left=response.request.right, right=response.request.left
            )
            assert reply.original_right_lookup.status == "missing"
            assert reply.original_left_lookup.status == "valid"


@pytest.mark.parametrize("case_index", range(8))
def test_old_domain_prerequisite_controls_remain_correct(case_index, response_batch):
    for arm in response_batch.receipt.arms:
        response = arm.responses[case_index]
        assert response.case.group == "retained_prerequisite_control"
        assert response.reply.answer == response.request.left + response.request.right
        assert response.reply.addition_reply.counting_reply.reason == "teacher_scaffold_walk"


@pytest.mark.parametrize("role", m._ROLES)
def test_fresh_partial_walk_retains_role_specific_native_evidence(role, response_batch):
    responses = _arm(response_batch, role).responses[8:10]
    expected = {
        "retained_repair": (((18, 19), (19, 20), (20, 21)), "missing_successor"),
        "valid_null": (((18, 19), (19, 20), (20, 21)), "missing_successor"),
        "no_repair_control": ((), "missing_successor"),
        "wrong_link_control": (((18, 20),), "cyclic_successor"),
    }[role]
    for response in responses:
        counted = response.reply.addition_reply.counting_reply
        assert response.reply.answer is None
        assert m._step_pairs(response) == expected[0]
        assert counted.reason == expected[1]
        if role in ("retained_repair", "valid_null"):
            assert all(step.claim_ref and step.evidence_refs for step in counted.steps)
        if role == "wrong_link_control":
            assert counted.blocked_claim_refs and counted.blocked_evidence_refs


@pytest.mark.parametrize("role", m._ROLES)
def test_declared_ceiling_stays_visible_and_abstains(role, response_batch):
    for response in _arm(response_batch, role).responses[10:12]:
        counted = response.reply.addition_reply.counting_reply
        assert response.case.group == "declared_domain_ceiling"
        assert response.reply.answer is None
        assert counted.reason == "missing_successor"
        assert counted.steps == ()
        assert counted.blocked_claim_refs == counted.blocked_evidence_refs == ()


@pytest.mark.parametrize("invalid_index", range(8))
def test_invalid_inputs_keep_exact_raw_types_and_errors(
    invalid_index, response_batch, evaluation
):
    case_index = 12 + invalid_index
    for arm in response_batch.receipt.arms:
        response = arm.responses[case_index]
        assert response.case.group == "invalid_input"
        assert response.case.raw_request_json == retention_protocol._cases()[case_index].raw_request_json
        assert response.request is response.reply is None
        assert response.input_errors
        assert not any(
            grade.case_ref == response.case_ref and grade.role == arm.role
            for grade in evaluation.receipt.grades
        )


@pytest.mark.parametrize("role", m._ROLES)
def test_external_grades_are_complete_and_answer_level_equal(
    role, response_batch, evaluation
):
    grades = _grades(evaluation, role)
    assert len(grades) == 12
    assert sum(grade.grade == "correct" for grade in grades.values()) == 8
    assert sum(grade.grade == "incorrect" for grade in grades.values()) == 0
    assert sum(grade.grade == "abstained" for grade in grades.values()) == 4
    assert set(grades) == {
        response.case_ref
        for response in _arm(response_batch, role).responses
        if response.request is not None
    }


@pytest.mark.parametrize("case_index", range(12))
def test_grader_targets_original_never_effective_request(
    case_index, response_batch, evaluation
):
    for arm in response_batch.receipt.arms:
        response = arm.responses[case_index]
        grade = _grades(evaluation, arm.role)[response.case_ref]
        assert grade.original_request == response.request
        assert grade.expected_answer == response.request.left + response.request.right
        assert grade.response_sha256 == m._response_hash(response)


@pytest.mark.parametrize("field", m._FALSE_FLAGS)
def test_authority_and_overclaim_flags_fail_closed(field, response_batch):
    raw = response_batch.receipt.model_dump(mode="json")
    raw[field] = True
    with pytest.raises(ValueError):
        m.ResponseBatchReceipt.model_validate(raw)


_RESPONSE_TAMPERS = (
    "execution",
    "protocol_hash",
    "history_hash",
    "arm_role",
    "source_role",
    "checkpoint_hash",
    "case_order",
    "raw_request",
    "route",
    "partial_step",
    "input_error",
    "code_hash",
)


@pytest.mark.parametrize("tamper", _RESPONSE_TAMPERS)
def test_rehashed_response_substitutions_fail_closed(tamper, tmp_path):
    raw = json.loads(_RESPONSES.read_text())
    receipt = raw["receipt"]
    if tamper == "execution":
        receipt["execution"]["cases_per_role"] = 21
    elif tamper == "protocol_hash":
        receipt["protocol_file_sha256"] = "0" * 64
    elif tamper == "history_hash":
        receipt["history_response_file_sha256"] = "0" * 64
    elif tamper == "arm_role":
        receipt["arms"][0]["role"] = "valid_null"
    elif tamper == "source_role":
        receipt["arms"][0]["source_role"] = "no_repair_control"
    elif tamper == "checkpoint_hash":
        receipt["arms"][0]["checkpoint_sha256"] = "0" * 64
    elif tamper == "case_order":
        receipt["arms"][0]["responses"][0:2] = reversed(
            receipt["arms"][0]["responses"][0:2]
        )
    elif tamper == "raw_request":
        receipt["arms"][0]["responses"][0]["case"]["raw_request_json"] = (
            '{"left":0,"right":14}'
        )
    elif tamper == "route":
        receipt["arms"][0]["responses"][8]["reply"]["route_disposition"] = (
            "blocked_original_right_mapping"
        )
    elif tamper == "partial_step":
        receipt["arms"][0]["responses"][8]["reply"]["addition_reply"][
            "counting_reply"
        ]["steps"][0]["to_number"] = 20
    elif tamper == "input_error":
        receipt["arms"][0]["responses"][12]["input_errors"][0][
            "error_type"
        ] = "missing"
    elif tamper == "code_hash":
        receipt["code_sources"][0]["sha256"] = "0" * 64
    path = _write(tmp_path / "tampered.vstrb", _rehash(raw))
    with pytest.raises((ValueError, TypeError, RuntimeError)):
        m.load_response_batch(
            _PROTOCOL, _HISTORY_RESPONSES, _HISTORY_EVALUATION, path
        )


_EVALUATION_TAMPERS = (
    "expected_answer",
    "grade",
    "response_hash",
    "role",
    "batch_hash",
    "authority",
)


@pytest.mark.parametrize("tamper", _EVALUATION_TAMPERS)
def test_rehashed_evaluation_substitutions_fail_closed(tamper, tmp_path):
    raw = json.loads(_RESULT.read_text())
    receipt = raw["receipt"]
    if tamper == "expected_answer":
        receipt["grades"][0]["expected_answer"] += 1
    elif tamper == "grade":
        receipt["grades"][0]["grade"] = "incorrect"
    elif tamper == "response_hash":
        receipt["grades"][0]["response_sha256"] = "0" * 64
    elif tamper == "role":
        receipt["grades"][0]["role"] = "valid_null"
    elif tamper == "batch_hash":
        receipt["response_batch_file_sha256"] = "0" * 64
    elif tamper == "authority":
        receipt["canonical_commit_permitted"] = True
    path = _write(tmp_path / "tampered.vstrr", _rehash(raw))
    with pytest.raises((ValueError, TypeError, RuntimeError)):
        m.load_evaluation(
            _PROTOCOL,
            _HISTORY_RESPONSES,
            _HISTORY_EVALUATION,
            _RESPONSES,
            path,
        )


def test_behavioral_signature_excludes_group_answer_grade_and_history():
    assert tuple(inspect.signature(m._respond).parameters) == (
        "kernel",
        "role",
        "local_run_ref",
        "case_ref",
        "raw_request_json",
    )
    source = inspect.getsource(m._respond)
    for forbidden in ("case.group", "freshness", "expected_answer", "_external_grade", "effect_anchor"):
        assert forbidden not in source
    assert "_external_grade" not in inspect.getsource(m.capture_successor_retention_responses)


def test_capture_finishes_without_any_grader(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("grader leaked into response capture")

    monkeypatch.setattr(m, "_external_grade", forbidden)
    batch = m.capture_successor_retention_responses(
        _PROTOCOL, _HISTORY_RESPONSES, _HISTORY_EVALUATION
    )
    assert sum(len(arm.responses) for arm in batch.receipt.arms) == 80


def test_replay_invokes_no_teaching_response_walk_or_grader(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("dynamic behavior leaked into static replay")

    monkeypatch.setattr(m, "_respond", forbidden)
    monkeypatch.setattr(m, "_external_grade", forbidden)
    monkeypatch.setattr(adapter, "derive_successor_repaired_addition", forbidden)
    batch = m.load_response_batch(
        _PROTOCOL, _HISTORY_RESPONSES, _HISTORY_EVALUATION, _RESPONSES
    )
    result = m.load_evaluation(
        _PROTOCOL,
        _HISTORY_RESPONSES,
        _HISTORY_EVALUATION,
        _RESPONSES,
        _RESULT,
    )
    assert batch.receipt_sha256 == _EXPECTED_RESPONSE_RECEIPT_SHA256
    assert result.receipt_sha256 == _EXPECTED_RESULT_RECEIPT_SHA256


def test_manifest_extends_exact_v066_sources_by_only_three_siblings(response_batch):
    old = {source.path: source.sha256 for source in response_batch.receipt.frozen_protocol.declaration.code_sources}
    current = {source.path: source.sha256 for source in response_batch.receipt.code_sources}
    assert len(old) == 52 and len(current) == 55
    assert all(current[path] == digest for path, digest in old.items())
    assert set(current) - set(old) == {
        "verdant_math/successor_retention_evaluation/__init__.py",
        "verdant_math/successor_retention_evaluation/cli.py",
        "verdant_math/successor_retention_evaluation/evaluation.py",
    }


def test_immutable_publication_cannot_replace_any_protected_input(
    response_batch, evaluation
):
    for protected in (_PROTOCOL, _HISTORY_RESPONSES, _HISTORY_EVALUATION):
        with pytest.raises(ValueError):
            m.save_response_batch(
                _PROTOCOL,
                _HISTORY_RESPONSES,
                _HISTORY_EVALUATION,
                protected,
                response_batch,
            )
    with pytest.raises(ValueError):
        m.save_evaluation(
            _PROTOCOL,
            _HISTORY_RESPONSES,
            _HISTORY_EVALUATION,
            _RESPONSES,
            _RESPONSES,
            evaluation,
        )


def test_cli_replays_exact_artifacts_and_rejects_swapped_history(capsys):
    assert cli([
        "replay", str(_PROTOCOL), str(_HISTORY_RESPONSES),
        str(_HISTORY_EVALUATION), str(_RESPONSES), str(_RESULT),
    ]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["responses"] == 80 and output["grades"] == 48
    assert cli([
        "replay", str(_PROTOCOL), str(_HISTORY_EVALUATION),
        str(_HISTORY_RESPONSES), str(_RESPONSES), str(_RESULT),
    ]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid"


def test_noncanonical_partial_and_foreign_inputs_fail_closed(tmp_path):
    noncanonical = _write(tmp_path / "noncanonical.vstrb", _RESPONSES.read_bytes() + b"\n")
    with pytest.raises(ValueError):
        m.load_response_batch(
            _PROTOCOL, _HISTORY_RESPONSES, _HISTORY_EVALUATION, noncanonical
        )
    with pytest.raises(ValueError):
        m.capture_successor_retention_responses(
            _PROTOCOL, _HISTORY_EVALUATION, _HISTORY_RESPONSES
        )
    with pytest.raises((OSError, ValueError)):
        m.load_evaluation(
            _PROTOCOL,
            _HISTORY_RESPONSES,
            _HISTORY_EVALUATION,
            tmp_path / "missing.vstrb",
            _RESULT,
        )
