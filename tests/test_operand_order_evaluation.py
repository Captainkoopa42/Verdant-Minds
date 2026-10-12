from __future__ import annotations

import json
from pathlib import Path

import pytest

from verdant_kernel import VerdantKernel
from verdant_kernel.models import canonical_json_bytes
from verdant_math import teaching_pilot as baseline
from verdant_math.addition import pilot as addition
from verdant_math.counting import pilot as counting
from verdant_math.ordering_adapter import adapter
from verdant_math.ordering_evaluation import evaluation as m
from verdant_math.ordering_evaluation.cli import main as cli
from verdant_math.ordering_protocol import protocol as ordering


_ROOT = Path(__file__).resolve().parent.parent
_PROTOCOL = _ROOT / "artifacts/operand_order_v060/protocol.vaop"
_IMPLEMENTATION = _ROOT / "artifacts/operand_order_v061/implementation.vaoi"
_RESPONSES = _ROOT / "artifacts/operand_order_v062/responses.vaob"
_RESULT = _ROOT / "artifacts/operand_order_v062/evaluation.vaor"


@pytest.fixture(scope="module")
def response_batch():
    return m.load_response_batch(_PROTOCOL, _IMPLEMENTATION, _RESPONSES)


@pytest.fixture(scope="module")
def evaluation():
    return m.load_evaluation(_PROTOCOL, _IMPLEMENTATION, _RESPONSES, _RESULT)


def _private(arm):
    return baseline._checkpoint(arm.checkpoint_base64, arm.checkpoint_sha256)


def _rehash_response(raw):
    raw["receipt_sha256"] = baseline._sha(canonical_json_bytes(raw["receipt"]))
    return canonical_json_bytes(raw)


def _rehash_result(raw):
    raw["receipt_sha256"] = baseline._sha(canonical_json_bytes(raw["receipt"]))
    return canonical_json_bytes(raw)


def test_checked_artifacts_are_exact_and_replay(response_batch, evaluation):
    assert len(_RESPONSES.read_bytes()) == 1_308_964
    assert baseline._sha(_RESPONSES.read_bytes()) == (
        "25f75c01332bff48e46c521eb966f9c8634620542aa6e2126236d378126f70e4"
    )
    assert len(_RESULT.read_bytes()) == 36_282
    assert baseline._sha(_RESULT.read_bytes()) == (
        "2ec22c550b17e1f7a3ca91df21ba06ab8dc7d1d11f8d70e3e2117d8c7f419bd1"
    )
    assert response_batch.receipt_sha256 == (
        "eb29e9b3a80d246bd23bd7e80408678642d7fdd99ed16ced896f0c056b2019db"
    )
    assert evaluation.receipt_sha256 == (
        "be49243269d65bbe0673c4e57402a20660a3817b0de6b657674d00f439323acd"
    )


def test_complete_observed_outcomes_and_full_denominators(response_batch, evaluation):
    summary = m.evaluation_summary(response_batch, evaluation)
    assert summary["responses"] == 160 and summary["grades"] == 128
    assert summary["enrolled_per_role"] == 40
    assert summary["valid_inputs_per_role"] == 32
    expected = {
        "taught": dict(correct=16, incorrect=0, abstained=16, invalid_input=8),
        "valid_null": dict(correct=16, incorrect=0, abstained=16, invalid_input=8),
        "no_instruction_control": dict(correct=8, incorrect=0, abstained=24, invalid_input=8),
        "incorrect_instruction_control": dict(
            correct=0, incorrect=0, abstained=32, invalid_input=8
        ),
    }
    assert {role: arm["total"] for role, arm in summary["arms"].items()} == expected
    assert summary["taught_null_exact"] is True
    assert sum(len(arm.responses) for arm in response_batch.receipt.arms) == 160
    assert len(evaluation.receipt.grades) == 128
    for arm in response_batch.receipt.arms:
        assert sum(summary["arms"][arm.role]["total"].values()) == 40
        assert tuple(response.case for response in arm.responses) == ordering._cases()


def test_predeclared_group_results_are_retained_without_reclassification(response_batch, evaluation):
    summary = m.evaluation_summary(response_batch, evaluation)["arms"]
    zero = dict(correct=0, incorrect=0, abstained=8, invalid_input=0)
    invalid = dict(correct=0, incorrect=0, abstained=0, invalid_input=8)
    correct = dict(correct=8, incorrect=0, abstained=0, invalid_input=0)
    assert summary["taught"]["groups"] == {
        "original_mapping": correct,
        "swap_candidate": correct,
        "both_mappings_absent": zero,
        "terminal_link": zero,
        "invalid_input": invalid,
    }
    assert summary["valid_null"]["groups"] == summary["taught"]["groups"]
    assert summary["no_instruction_control"]["groups"]["original_mapping"] == correct
    assert summary["no_instruction_control"]["groups"]["swap_candidate"] == zero
    for group in ("original_mapping", "swap_candidate", "both_mappings_absent", "terminal_link"):
        assert summary["incorrect_instruction_control"]["groups"][group] == zero
    assert summary["incorrect_instruction_control"]["groups"]["invalid_input"] == invalid


def test_original_effective_requests_and_complete_native_routes_are_preserved(response_batch):
    taught = response_batch.receipt.arms[0]
    for response in taught.responses[:8]:
        assert response.reply.route_disposition == "kept_valid_original_right"
        assert response.reply.original_request == response.reply.effective_request == response.request
        assert response.reply.original_right_lookup.status == "valid"
        assert response.reply.original_left_lookup is None
        assert response.reply.addition_reply is not None
    for response in taught.responses[8:16]:
        assert response.reply.route_disposition == "swapped_missing_original_right"
        assert response.reply.original_request == response.request
        assert response.reply.effective_request == addition.AdditionRequest(
            left=response.request.right, right=response.request.left
        )
        assert response.reply.original_right_lookup.status == "missing"
        assert response.reply.original_left_lookup.status == "valid"
        assert response.reply.addition_reply is not None
    for response in taught.responses[16:24]:
        assert response.reply.route_disposition == "blocked_original_left_mapping"
        assert response.reply.original_right_lookup.status == "missing"
        assert response.reply.original_left_lookup.status == "missing"
        assert response.reply.effective_request is None
        assert response.reply.addition_reply is None
    for response in taught.responses[24:32]:
        assert response.reply.route_disposition in (
            "kept_valid_original_right", "swapped_missing_original_right"
        )
        nested = response.reply.addition_reply
        assert nested.reason == "counting_abstained"
        assert nested.counting_reply.reason == "missing_successor"
        assert nested.counting_reply.steps == tuple(nested.counting_reply.steps)
        assert response.reply.answer is None


def test_controls_follow_only_their_frozen_instruction(response_batch):
    no_instruction = response_batch.receipt.arms[1]
    wrong = response_batch.receipt.arms[3]
    assert all(r.reply.order_instruction.status == "missing" for r in no_instruction.responses[:32])
    assert all(
        r.reply.route_disposition == "no_instruction_original_order"
        and r.reply.effective_request == r.request
        for r in no_instruction.responses[:32]
    )
    assert all(r.reply.order_instruction.label == adapter._INCORRECT for r in wrong.responses[:32])
    assert all(
        r.reply.route_disposition == "incorrect_swapped_valid_original_right"
        for r in wrong.responses[:8]
    )
    assert all(
        r.reply.route_disposition == "incorrect_kept_missing_original_right"
        for r in wrong.responses[8:24]
    )
    assert all(r.reply.answer is None for r in wrong.responses[:32])


def test_invalid_inputs_preserve_raw_types_and_typed_errors_without_grades(
    response_batch, evaluation
):
    expected = (
        (("right",), "int_type"), (("left",), "int_type"),
        (("right",), "int_type"), (("right",), "int_type"),
        (("left",), "less_than_equal"), (("right",), "missing"),
        (("answer",), "extra_forbidden"), (("left",), "int_type"),
    )
    graded = {(g.role, g.case_ref) for g in evaluation.receipt.grades}
    for arm in response_batch.receipt.arms:
        for index, (response, (location, error_type)) in enumerate(
            zip(arm.responses[32:], expected)
        ):
            assert response.request is None and response.reply is None
            assert response.input_errors == (
                m.InputRejection(location=location, error_type=error_type),
            )
            assert (arm.role, response.case_ref) not in graded
            assert json.loads(response.case.raw_request_json) == json.loads(
                ordering._cases()[32 + index].raw_request_json
            )


def test_taught_and_valid_null_are_complete_record_exact(response_batch):
    taught, _, null, _ = response_batch.receipt.arms
    assert taught is not null
    assert m._null_projection(taught) == m._null_projection(null)
    assert taught.checkpoint_base64 == null.checkpoint_base64
    assert taught.kernel_fingerprint == null.kernel_fingerprint
    assert taught.lessons == null.lessons
    for left, right in zip(taught.responses, null.responses):
        assert left.model_dump(exclude={"role"}) == right.model_dump(exclude={"role"})


def test_response_batch_is_saved_and_complete_before_first_external_grade(
    response_batch, tmp_path, monkeypatch
):
    path = tmp_path / "responses.vaob"
    m.save_response_batch(_PROTOCOL, _IMPLEMENTATION, path, response_batch)
    original, calls = addition._grade, []

    def grade(index, request, reply):
        raw = json.loads(path.read_bytes())
        assert sum(len(arm["responses"]) for arm in raw["receipt"]["arms"]) == 160
        assert "grades" not in raw["receipt"]
        assert raw["receipt"]["evaluation_completed"] is False
        calls.append((index, request, reply.answer))
        return original(index, request, reply)

    monkeypatch.setattr(addition, "_grade", grade)
    result = m.evaluate_response_batch(_PROTOCOL, _IMPLEMENTATION, path)
    assert len(calls) == 128 and len(result.receipt.grades) == 128


def test_capture_has_no_grader_or_behavioral_group_input(monkeypatch):
    original, calls = adapter.derive_ordered_addition, []

    def forbidden(*args, **kwargs):
        raise AssertionError("Response capture consulted an external grader")

    def derive(kernel, request, *, local_run_ref, case_ref):
        assert set(request.model_dump()) == {"left", "right"}
        assert case_ref.startswith("math-v060:case:")
        assert local_run_ref.startswith("math-v062:run:")
        calls.append((request, local_run_ref, case_ref))
        return original(kernel, request, local_run_ref=local_run_ref, case_ref=case_ref)

    monkeypatch.setattr(addition, "_grade", forbidden)
    monkeypatch.setattr(baseline, "_grade", forbidden)
    monkeypatch.setattr(counting, "_grade", forbidden)
    monkeypatch.setattr(adapter, "derive_ordered_addition", derive)
    batch = m.capture_operand_order_responses(_PROTOCOL, _IMPLEMENTATION)
    assert len(calls) == 128
    assert sum(r.request is None for arm in batch.receipt.arms for r in arm.responses) == 32


def test_external_grader_receives_original_not_effective_request(
    response_batch, tmp_path, monkeypatch
):
    path = tmp_path / "responses.vaob"
    m.save_response_batch(_PROTOCOL, _IMPLEMENTATION, path, response_batch)
    original, seen = addition._grade, []

    def grade(index, request, reply):
        seen.append(request)
        return original(index, request, reply)

    monkeypatch.setattr(addition, "_grade", grade)
    m.evaluate_response_batch(_PROTOCOL, _IMPLEMENTATION, path)
    originals = [r.request for arm in response_batch.receipt.arms for r in arm.responses if r.request]
    assert seen == originals
    assert any(
        response.reply.effective_request != response.request
        for response in response_batch.receipt.arms[0].responses
        if response.request is not None
    )


def test_reload_replays_without_response_teaching_or_grader_entry_points(
    response_batch, evaluation, monkeypatch
):
    def forbidden(*args, **kwargs):
        raise AssertionError("Reload reran teaching, response, or grading")

    monkeypatch.setattr(adapter, "prepare_private_operand_order_kernel", forbidden)
    monkeypatch.setattr(adapter, "derive_ordered_addition", forbidden)
    monkeypatch.setattr(addition, "derive_addition", forbidden)
    monkeypatch.setattr(counting, "count_forward", forbidden)
    monkeypatch.setattr(addition, "_grade", forbidden)
    assert m.load_response_batch(_PROTOCOL, _IMPLEMENTATION, _RESPONSES) == response_batch
    assert m.load_evaluation(_PROTOCOL, _IMPLEMENTATION, _RESPONSES, _RESULT) == evaluation


def test_source_private_canonical_simulation_attention_and_governance_isolation(monkeypatch):
    from verdant_obligations import CounterfactualRuntime, SimulationLedger

    def forbidden(*args, **kwargs):
        raise AssertionError("Math evaluation acquired simulation, Attention, or governance authority")

    monkeypatch.setattr(CounterfactualRuntime, "execute", forbidden)
    monkeypatch.setattr(SimulationLedger, "reserve", forbidden)
    monkeypatch.setattr(VerdantKernel, "record_governance_outcome", forbidden)
    source = ordering.fresh_order_kernel()
    before = source.snapshot()
    batch = m.capture_operand_order_responses(_PROTOCOL, _IMPLEMENTATION, source)
    assert source.snapshot() == before
    assert len({arm.checkpoint_sha256 for arm in batch.receipt.arms}) == 3
    for arm in batch.receipt.arms:
        private = _private(arm)
        assert private.state.cycle == 26
        assert not private.state.obligation_kernels
        assert not private.state.obligation_attention_decisions
        assert not private.state.governance_outcomes
        assert not private.state.council_decisions
        assert not private.state.revisions


@pytest.mark.parametrize("drift", ("protocol", "implementation", "code", "source", "private", "null"))
def test_any_mid_capture_drift_or_divergent_null_fails_before_publication(
    tmp_path, monkeypatch, drift
):
    protocol_path = tmp_path / "protocol.vaop"
    implementation_path = tmp_path / "implementation.vaoi"
    protocol_path.write_bytes(_PROTOCOL.read_bytes())
    implementation_path.write_bytes(_IMPLEMENTATION.read_bytes())
    source = ordering.fresh_order_kernel()
    respond, manifest = m._respond, m._code_manifest
    calls = 0

    def changed_respond(kernel, role, case):
        nonlocal calls
        calls += 1
        result = respond(kernel, role, case)
        if calls == 1:
            if drift == "protocol": protocol_path.write_bytes(protocol_path.read_bytes() + b" ")
            elif drift == "implementation": implementation_path.write_bytes(
                implementation_path.read_bytes() + b" "
            )
            elif drift == "source": source.state.cycle += 1
            elif drift == "private": kernel.state.cycle += 1
        if drift == "null" and role == "valid_null" and case.case_id.endswith(":0"):
            raw = result.model_dump(mode="json")
            raw["reply"]["local_run_ref"] = "math-v062:run:divergent-null"
            raw["local_run_ref"] = "math-v062:run:divergent-null"
            return raw
        return result

    if drift == "code":
        seen = 0
        def changed_manifest(implementation):
            nonlocal seen
            seen += 1
            value = manifest(implementation)
            return value if seen < 3 else value[:-1]
        monkeypatch.setattr(m, "_code_manifest", changed_manifest)
    monkeypatch.setattr(m, "_respond", changed_respond)
    with pytest.raises((ValueError, TypeError)):
        m.capture_operand_order_responses(protocol_path, implementation_path, source)
    assert not (tmp_path / "responses.vaob").exists()


@pytest.mark.parametrize("kind", ("protocol", "implementation"))
def test_stale_foreign_or_nonexact_frozen_inputs_fail_before_response(tmp_path, monkeypatch, kind):
    protocol_path = tmp_path / "protocol.vaop"
    implementation_path = tmp_path / "implementation.vaoi"
    protocol_path.write_bytes(_PROTOCOL.read_bytes())
    implementation_path.write_bytes(_IMPLEMENTATION.read_bytes())
    target = protocol_path if kind == "protocol" else implementation_path
    target.write_bytes(target.read_bytes() + b" ")

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid frozen input reached response execution")

    monkeypatch.setattr(adapter, "prepare_private_operand_order_kernel", forbidden)
    with pytest.raises(ValueError, match="exact"):
        m.capture_operand_order_responses(protocol_path, implementation_path)


@pytest.mark.parametrize("attack", (
    "execution", "protocol_hash", "implementation_hash", "implementation_receipt",
    "code_hash", "code_drop", "role_order", "arm_drop", "arm_duplicate", "arm_role",
    "run_ref", "case", "group", "pair", "raw_request", "response_order", "response_role",
    "case_ref", "request", "input_location", "input_type", "reply_original", "reply_effective",
    "reply_answer", "route", "instruction_claim", "right_lookup", "left_lookup",
    "nested_answer", "nested_rule", "nested_step", "partial_steps", "lesson_transition",
    "lesson_claim", "checkpoint", "fingerprint", "purpose", "evaluated", "extra",
))
def test_fully_rehashed_response_case_route_partial_and_lineage_attacks_fail(
    response_batch, tmp_path, attack
):
    raw = response_batch.model_dump(mode="json")
    receipt, arm = raw["receipt"], raw["receipt"]["arms"][0]
    responses = arm["responses"]
    original, swapped, partial, invalid = responses[6], responses[14], responses[26], responses[32]
    if attack == "execution": receipt["execution"]["scoring"] = "credit_any_answer"
    elif attack == "protocol_hash": receipt["protocol_file_sha256"] = "0" * 64
    elif attack == "implementation_hash": receipt["implementation_file_sha256"] = "0" * 64
    elif attack == "implementation_receipt": receipt["frozen_implementation"]["receipt_sha256"] = "0" * 64
    elif attack == "code_hash": receipt["code_sources"][-1]["sha256"] = "0" * 64
    elif attack == "code_drop": receipt["code_sources"].pop()
    elif attack == "role_order": receipt["arms"].reverse()
    elif attack == "arm_drop": receipt["arms"].pop()
    elif attack == "arm_duplicate": receipt["arms"][1] = receipt["arms"][0]
    elif attack == "arm_role": arm["role"] = "valid_null"
    elif attack == "run_ref": arm["local_run_ref"] = "foreign-run"
    elif attack == "case": original["case"]["case_id"] = "foreign-case"
    elif attack == "group": original["case"]["group"] = "terminal_link"
    elif attack == "pair": original["case"]["order_pair"] = "terminal-0"
    elif attack == "raw_request": original["case"]["raw_request_json"] = '{"left":6,"right":0}'
    elif attack == "response_order": responses.reverse()
    elif attack == "response_role": original["role"] = "valid_null"
    elif attack == "case_ref": original["case_ref"] = "foreign-case"
    elif attack == "request": original["request"]["left"] = 12
    elif attack == "input_location": invalid["input_errors"][0]["location"] = ["left"]
    elif attack == "input_type": invalid["input_errors"][0]["error_type"] = "missing"
    elif attack == "reply_original": swapped["reply"]["original_request"]["left"] = 13
    elif attack == "reply_effective": swapped["reply"]["effective_request"] = swapped["request"]
    elif attack == "reply_answer": swapped["reply"]["answer"] = 14
    elif attack == "route": swapped["reply"]["route_disposition"] = "kept_valid_original_right"
    elif attack == "instruction_claim": swapped["reply"]["order_instruction"]["claim_refs"][0] = "foreign"
    elif attack == "right_lookup": swapped["reply"]["original_right_lookup"]["status"] = "valid"
    elif attack == "left_lookup": swapped["reply"]["original_left_lookup"]["claim_refs"][0] = "foreign"
    elif attack == "nested_answer": swapped["reply"]["addition_reply"]["answer"] = 14
    elif attack == "nested_rule": swapped["reply"]["addition_reply"]["addition_rule_claim_refs"][0] = "foreign"
    elif attack == "nested_step": swapped["reply"]["addition_reply"]["counting_reply"]["steps"][0]["to_number"] = 18
    elif attack == "partial_steps": partial["reply"]["addition_reply"]["counting_reply"]["steps"].pop()
    elif attack == "lesson_transition": arm["lessons"][0]["transition_ref"] = "foreign"
    elif attack == "lesson_claim": arm["lessons"][0]["claim_refs"][0] = "foreign"
    elif attack == "checkpoint": arm["checkpoint_base64"] = receipt["arms"][3]["checkpoint_base64"]
    elif attack == "fingerprint": arm["kernel_fingerprint"] = "0" * 64
    elif attack == "purpose": receipt["purpose"] = "retuned_response_batch"
    elif attack == "evaluated": receipt["evaluation_completed"] = True
    else: receipt["expected_answers"] = [1]
    path = tmp_path / "forged.vaob"
    path.write_bytes(_rehash_response(raw))
    with pytest.raises((ValueError, TypeError, RuntimeError)):
        m.load_response_batch(_PROTOCOL, _IMPLEMENTATION, path)


@pytest.mark.parametrize("attack", (
    "execution", "protocol_hash", "implementation_hash", "response_receipt", "response_file",
    "code_hash", "grade_drop", "grade_duplicate", "grade_order", "grade_role", "grade_case",
    "grade_request", "grade_response", "expected", "grade", "purpose", "barrier", "invalids", "extra",
))
def test_fully_rehashed_result_pairing_grade_and_authority_attacks_fail(
    evaluation, tmp_path, attack
):
    raw = evaluation.model_dump(mode="json")
    receipt, grades = raw["receipt"], raw["receipt"]["grades"]
    if attack == "execution": receipt["execution"]["denominators"] = "supported_only"
    elif attack == "protocol_hash": receipt["protocol_file_sha256"] = "0" * 64
    elif attack == "implementation_hash": receipt["implementation_file_sha256"] = "0" * 64
    elif attack == "response_receipt": receipt["response_batch_receipt_sha256"] = "0" * 64
    elif attack == "response_file": receipt["response_batch_file_sha256"] = "0" * 64
    elif attack == "code_hash": receipt["code_sources"][-1]["sha256"] = "0" * 64
    elif attack == "grade_drop": grades.pop()
    elif attack == "grade_duplicate": grades[1] = grades[0]
    elif attack == "grade_order": grades.reverse()
    elif attack == "grade_role": grades[0]["role"] = "valid_null"
    elif attack == "grade_case": grades[0]["case_ref"] = "foreign-case"
    elif attack == "grade_request": grades[0]["original_request"]["left"] = 12
    elif attack == "grade_response": grades[0]["response_sha256"] = "0" * 64
    elif attack == "expected": grades[0]["expected_answer"] += 1
    elif attack == "grade": grades[0]["grade"] = "incorrect"
    elif attack == "purpose": receipt["purpose"] = "generalized_arithmetic"
    elif attack == "barrier": receipt["responses_durable_before_grading"] = False
    elif attack == "invalids": receipt["invalid_inputs_retained_ungraded"] = False
    else: receipt["promotion"] = True
    path = tmp_path / "forged.vaor"
    path.write_bytes(_rehash_result(raw))
    with pytest.raises((ValueError, TypeError, RuntimeError)):
        m.load_evaluation(_PROTOCOL, _IMPLEMENTATION, _RESPONSES, path)


@pytest.mark.parametrize("flag", m._FALSE_FLAGS)
@pytest.mark.parametrize("target", ("response", "result"))
def test_rehashed_source_physical_discovery_or_authority_claims_fail(
    response_batch, evaluation, tmp_path, flag, target
):
    envelope = response_batch if target == "response" else evaluation
    raw = envelope.model_dump(mode="json")
    raw["receipt"][flag] = True
    path = tmp_path / f"escalated-{target}.json"
    path.write_bytes(_rehash_response(raw) if target == "response" else _rehash_result(raw))
    with pytest.raises(ValueError):
        if target == "response":
            m.load_response_batch(_PROTOCOL, _IMPLEMENTATION, path)
        else:
            m.load_evaluation(_PROTOCOL, _IMPLEMENTATION, _RESPONSES, path)


@pytest.mark.parametrize("target", ("response", "result"))
@pytest.mark.parametrize("attack", ("duplicate_key", "noncanonical", "oversized", "bad_hash", "missing"))
def test_corrupt_noncanonical_oversized_hash_or_missing_artifacts_fail(
    response_batch, evaluation, tmp_path, target, attack
):
    path = tmp_path / f"bad-{target}.json"
    envelope = response_batch if target == "response" else evaluation
    if attack == "duplicate_key":
        path.write_text('{"receipt":{},"receipt":{}}')
    elif attack == "noncanonical":
        path.write_text(json.dumps(envelope.model_dump(mode="json"), indent=2))
    elif attack == "oversized":
        path.write_bytes(b" " * (m._MAX_BYTES + 1))
    elif attack == "bad_hash":
        raw = envelope.model_dump(mode="json")
        raw["receipt_sha256"] = "0" * 64
        path.write_bytes(canonical_json_bytes(raw))
    with pytest.raises((ValueError, OSError, RuntimeError)):
        if target == "response":
            m.load_response_batch(_PROTOCOL, _IMPLEMENTATION, path)
        else:
            m.load_evaluation(_PROTOCOL, _IMPLEMENTATION, _RESPONSES, path)


def test_result_is_bound_to_exact_saved_response_bytes(evaluation, tmp_path):
    path = tmp_path / "pretty.vaob"
    path.write_text(json.dumps(json.loads(_RESPONSES.read_bytes()), indent=2))
    with pytest.raises(ValueError, match="canonical"):
        m.load_response_batch(_PROTOCOL, _IMPLEMENTATION, path)
    with pytest.raises(ValueError):
        m.load_evaluation(_PROTOCOL, _IMPLEMENTATION, path, _RESULT)


@pytest.mark.parametrize("writer,target_kind", (
    ("response", "protocol"), ("response", "implementation"), ("response", "code"),
    ("response", "history"), ("result", "protocol"), ("result", "implementation"),
    ("result", "response"), ("result", "code"), ("result", "history"),
))
def test_writers_cannot_replace_frozen_inputs_code_history_or_responses(
    response_batch, evaluation, writer, target_kind
):
    target = {
        "protocol": _PROTOCOL,
        "implementation": _IMPLEMENTATION,
        "response": _RESPONSES,
        "code": _ROOT / "verdant_math/ordering_evaluation/evaluation.py",
        "history": _ROOT / ordering._HISTORY[0][0],
    }[target_kind]
    before = target.read_bytes()
    with pytest.raises(ValueError, match="Cannot publish"):
        if writer == "response":
            m.save_response_batch(_PROTOCOL, _IMPLEMENTATION, target, response_batch)
        else:
            m.save_evaluation(_PROTOCOL, _IMPLEMENTATION, _RESPONSES, target, evaluation)
    assert target.read_bytes() == before


@pytest.mark.parametrize("kind", ("response", "result"))
def test_immutable_publication_and_failure_preserve_existing_evidence(
    response_batch, evaluation, tmp_path, monkeypatch, kind
):
    path = tmp_path / f"saved-{kind}.json"
    if kind == "response":
        save = lambda target: m.save_response_batch(
            _PROTOCOL, _IMPLEMENTATION, target, response_batch
        )
        expected = _RESPONSES.read_bytes()
    else:
        save = lambda target: m.save_evaluation(
            _PROTOCOL, _IMPLEMENTATION, _RESPONSES, target, evaluation
        )
        expected = _RESULT.read_bytes()
    first = save(path)
    assert save(path) == first and path.read_bytes() == expected
    path.write_bytes(b"occupied evidence")
    with pytest.raises(RuntimeError, match="different evidence"):
        save(path)
    assert path.read_bytes() == b"occupied evidence"

    def fail(*args, **kwargs):
        raise OSError("publication failed")

    monkeypatch.setattr(baseline, "_write_immutable", fail)
    absent = tmp_path / f"absent-{kind}.json"
    with pytest.raises(OSError, match="publication failed"):
        save(absent)
    assert not absent.exists()


def test_cli_run_replay_and_response_barrier_failure_modes(tmp_path, capsys, monkeypatch):
    response_path, result_path = tmp_path / "responses.vaob", tmp_path / "evaluation.vaor"
    assert cli(["run", str(_PROTOCOL), str(_IMPLEMENTATION), str(response_path), str(result_path)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["responses"] == 160 and summary["grades"] == 128
    assert cli(["replay", str(_PROTOCOL), str(_IMPLEMENTATION), str(response_path), str(result_path)]) == 0
    assert json.loads(capsys.readouterr().out) == summary

    response_after_failure = tmp_path / "complete-before-grade.vaob"
    no_result = tmp_path / "no-result.vaor"
    def failed_grade(*args, **kwargs):
        raise RuntimeError("injected grader failure")
    monkeypatch.setattr(addition, "_grade", failed_grade)
    assert cli(["run", str(_PROTOCOL), str(_IMPLEMENTATION),
                str(response_after_failure), str(no_result)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid"
    assert len(m.load_response_batch(_PROTOCOL, _IMPLEMENTATION, response_after_failure).receipt.arms) == 4
    assert not no_result.exists()


def test_capture_failure_never_publishes_a_partial_role_batch(tmp_path, capsys, monkeypatch):
    response_path, result_path = tmp_path / "partial.vaob", tmp_path / "partial.vaor"
    original, calls = m._respond, 0
    def fail(kernel, role, case):
        nonlocal calls
        calls += 1
        if calls == 101:
            raise RuntimeError("injected role-three failure")
        return original(kernel, role, case)
    monkeypatch.setattr(m, "_respond", fail)
    assert cli(["run", str(_PROTOCOL), str(_IMPLEMENTATION),
                str(response_path), str(result_path)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid"
    assert not response_path.exists() and not result_path.exists()


def test_frozen_manifest_and_all_older_artifacts_remain_byte_exact(response_batch):
    historical = [_ROOT / path for path, _ in ordering._HISTORY]
    paths = [*historical, _PROTOCOL, _IMPLEMENTATION]
    before = tuple(path.read_bytes() for path in paths)
    assert len(response_batch.receipt.code_sources) == 40
    assert response_batch.receipt.frozen_protocol.declaration.code_sources == (
        ordering.load_operand_order_protocol(_PROTOCOL).declaration.code_sources
    )
    assert len(response_batch.receipt.frozen_protocol.declaration.code_sources) == 34
    assert len(response_batch.receipt.frozen_implementation.receipt.code_sources) == 37
    assert tuple(path.read_bytes() for path in paths) == before


def test_claim_boundaries_remain_explicit_and_physical_track_is_untouched(
    response_batch, evaluation
):
    for receipt in (response_batch.receipt, evaluation.receipt):
        for flag in m._FALSE_FLAGS:
            assert getattr(receipt, flag) is False
    assert response_batch.receipt.prospective_cohort_executed is True
    assert response_batch.receipt.prospective_responses_observed is True
    assert response_batch.receipt.evaluation_completed is False
    assert evaluation.receipt.responses_durable_before_grading is True
    assert evaluation.receipt.invalid_inputs_retained_ungraded is True
    assert evaluation.receipt.evaluation_completed is True
