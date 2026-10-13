from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from verdant_kernel import VerdantKernel
from verdant_kernel.models import canonical_json_bytes
from verdant_math import teaching_pilot as baseline
from verdant_math.addition import pilot as addition
from verdant_math.counting import pilot as counting
from verdant_math.successor_repair_adapter import adapter
from verdant_math.successor_repair_evaluation import evaluation as m
from verdant_math.successor_repair_evaluation.cli import main as cli
from verdant_math.successor_repair_protocol import protocol as repair_protocol


_ROOT = Path(__file__).resolve().parent.parent
_PROTOCOL = _ROOT / "artifacts/terminal_successor_v063/protocol.vsrp"
_IMPLEMENTATION = _ROOT / "artifacts/terminal_successor_v064/implementation.vsri"
_RESPONSES = _ROOT / "artifacts/terminal_successor_v065/responses.vsrb"
_RESULT = _ROOT / "artifacts/terminal_successor_v065/evaluation.vsrr"
_EXPECTED_RESPONSE_SIZE = 1_484_088
_EXPECTED_RESPONSE_FILE_SHA256 = "6f7fc01cfa4f380fd3b7f09e10fb0de4631cc1b5c1071823e59e864b6aad7f26"
_EXPECTED_RESPONSE_RECEIPT_SHA256 = "c184c060a72e2e310ee1a929d54ccaa11bf0a0a3babe924f291c282f354dd31e"
_EXPECTED_RESULT_SIZE = 37_357
_EXPECTED_RESULT_FILE_SHA256 = "e704ee573b92f6bd9979502ae92d73f9f7f75a6928e1eb6e3a63d4900cfbea0f"
_EXPECTED_RESULT_RECEIPT_SHA256 = "f7d9ee00425eaed98ef0e3f55d582d12aea60266d1053435e52b2493565a3b72"


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


def _grade_map(evaluation, role):
    return {
        grade.case_ref: grade
        for grade in evaluation.receipt.grades
        if grade.role == role
    }


def test_checked_artifacts_are_exact_and_replay(response_batch, evaluation):
    assert len(_RESPONSES.read_bytes()) == _EXPECTED_RESPONSE_SIZE
    assert baseline._sha(_RESPONSES.read_bytes()) == _EXPECTED_RESPONSE_FILE_SHA256
    assert response_batch.receipt_sha256 == _EXPECTED_RESPONSE_RECEIPT_SHA256
    assert len(_RESULT.read_bytes()) == _EXPECTED_RESULT_SIZE
    assert baseline._sha(_RESULT.read_bytes()) == _EXPECTED_RESULT_FILE_SHA256
    assert evaluation.receipt_sha256 == _EXPECTED_RESULT_RECEIPT_SHA256


def test_complete_prospective_outcomes_and_full_denominators(response_batch, evaluation):
    summary = m.evaluation_summary(response_batch, evaluation)
    assert summary["responses"] == 160 and summary["grades"] == 128
    assert summary["enrolled_per_role"] == 40
    assert summary["valid_inputs_per_role"] == 32
    expected = {
        "taught_repair": dict(correct=20, incorrect=0, abstained=12, invalid_input=8),
        "valid_null": dict(correct=20, incorrect=0, abstained=12, invalid_input=8),
        "no_repair_control": dict(correct=16, incorrect=0, abstained=16, invalid_input=8),
        "wrong_link_control": dict(correct=16, incorrect=2, abstained=14, invalid_input=8),
    }
    assert {role: arm["total"] for role, arm in summary["arms"].items()} == expected
    assert summary["taught_null_exact"] is True
    assert summary["repair_supported_correct_delta_over_no_repair"] == 4
    assert summary["supplied_repair_effect_observed"] is True
    assert sum(len(arm.responses) for arm in response_batch.receipt.arms) == 160
    assert len(evaluation.receipt.grades) == 128
    for arm in response_batch.receipt.arms:
        assert sum(summary["arms"][arm.role]["total"].values()) == 40
        assert tuple(response.case for response in arm.responses) == repair_protocol._cases()


def test_predeclared_groups_are_retained_without_outcome_reclassification(
    response_batch, evaluation
):
    summary = m.evaluation_summary(response_batch, evaluation)["arms"]
    correct10 = dict(correct=10, incorrect=0, abstained=0, invalid_input=0)
    correct6 = dict(correct=6, incorrect=0, abstained=0, invalid_input=0)
    correct4 = dict(correct=4, incorrect=0, abstained=0, invalid_input=0)
    abstain4 = dict(correct=0, incorrect=0, abstained=4, invalid_input=0)
    wrong_repair = dict(correct=0, incorrect=2, abstained=2, invalid_input=0)
    abstain12 = dict(correct=0, incorrect=0, abstained=12, invalid_input=0)
    invalid8 = dict(correct=0, incorrect=0, abstained=0, invalid_input=8)
    for role in m._ROLES:
        assert summary[role]["groups"]["pre_boundary_control"] == correct10
        assert summary[role]["groups"]["new_domain_zero_identity"] == correct6
        assert summary[role]["groups"]["declared_domain_ceiling"] == abstain12
        assert summary[role]["groups"]["invalid_input"] == invalid8
    assert summary["taught_repair"]["groups"]["repair_supported"] == correct4
    assert summary["valid_null"]["groups"] == summary["taught_repair"]["groups"]
    assert summary["no_repair_control"]["groups"]["repair_supported"] == abstain4
    assert summary["wrong_link_control"]["groups"]["repair_supported"] == wrong_repair


def test_original_effective_requests_and_native_order_routes_are_preserved(response_batch):
    taught = response_batch.receipt.arms[0]
    for response in taught.responses[:32]:
        reply = response.reply
        assert reply.original_request == response.request
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
        assert reply.addition_reply is not None
        assert reply.order_instruction.status == "valid"


def test_correct_repair_uses_only_supplied_native_successors(response_batch):
    taught = response_batch.receipt.arms[0]
    repaired = taught.responses[16:20]
    expected_steps = {
        (20, 1): ((20, 21),),
        (1, 20): ((20, 21),),
        (19, 2): ((19, 20), (20, 21)),
        (2, 19): ((19, 20), (20, 21)),
    }
    for response in repaired:
        counted = response.reply.addition_reply.counting_reply
        assert response.reply.answer == response.request.left + response.request.right
        assert tuple((step.from_number, step.to_number) for step in counted.steps) == (
            expected_steps[(response.request.left, response.request.right)]
        )
        assert all(step.claim_ref and step.evidence_refs for step in counted.steps)
        assert counted.blocked_claim_refs == counted.blocked_evidence_refs == ()


def test_declared_ceiling_preserves_partial_walk_and_missing_21(response_batch):
    taught = response_batch.receipt.arms[0]
    for response in taught.responses[20:32]:
        counted = response.reply.addition_reply.counting_reply
        assert response.reply.answer is None
        assert counted.reason == "missing_successor"
        assert counted.steps == tuple(counted.steps)
        assert counted.steps[-1].to_number == 21 if counted.steps else (
            response.reply.effective_request.left == 21
        )
        assert counted.blocked_claim_refs == ()
        assert counted.blocked_evidence_refs == ()


def test_no_repair_control_preserves_missing_slots_without_oracle_repair(response_batch):
    arm = response_batch.receipt.arms[1]
    private = _private(arm)
    for source in (18, 19, 20):
        assert counting._lookup(
            private, f"math:integer:{source}", "math_successor"
        ).status == "missing"
    for response in arm.responses[16:20]:
        counted = response.reply.addition_reply.counting_reply
        assert counted.reason == "missing_successor"
        assert response.reply.answer is None
        assert counted.blocked_claim_refs == counted.blocked_evidence_refs == ()


def test_wrong_link_control_retains_wrong_answers_cycles_and_missing_edges(response_batch):
    arm = response_batch.receipt.arms[3]
    grades = []
    for response in arm.responses[16:20]:
        counted = response.reply.addition_reply.counting_reply
        if response.request in (
            adapter.BoundedAdditionRequestV064(left=20, right=1),
            adapter.BoundedAdditionRequestV064(left=1, right=20),
        ):
            assert response.reply.answer == 18
            assert counted.reason == "teacher_scaffold_walk"
            grades.append("incorrect")
        else:
            assert response.reply.answer is None
            assert counted.reason == "missing_successor"
            assert tuple((step.from_number, step.to_number) for step in counted.steps) == (
                (19, 21),
            )
            grades.append("abstained")
    assert grades.count("incorrect") == grades.count("abstained") == 2
    cyclic = [
        response.reply.addition_reply.counting_reply
        for response in arm.responses[20:32]
        if response.reply.addition_reply.counting_reply.reason == "cyclic_successor"
    ]
    assert cyclic
    assert all(reply.blocked_claim_refs and reply.blocked_evidence_refs for reply in cyclic)


def test_invalid_inputs_retain_raw_types_errors_and_no_grades(response_batch, evaluation):
    expected = (
        (("right",), "int_type"),
        (("left",), "int_type"),
        (("right",), "int_type"),
        (("right",), "int_type"),
        (("left",), "less_than_equal"),
        (("right",), "missing"),
        (("answer",), "extra_forbidden"),
        (("left",), "int_type"),
    )
    graded = {(grade.role, grade.case_ref) for grade in evaluation.receipt.grades}
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
                repair_protocol._cases()[32 + index].raw_request_json
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


def test_response_sidecar_is_complete_before_first_external_grade(
    response_batch, tmp_path, monkeypatch
):
    path = tmp_path / "responses.vsrb"
    m.save_response_batch(_PROTOCOL, _IMPLEMENTATION, path, response_batch)
    original, calls = m._external_grade, []

    def grade(response):
        raw = json.loads(path.read_bytes())
        assert sum(len(arm["responses"]) for arm in raw["receipt"]["arms"]) == 160
        assert "grades" not in raw["receipt"]
        assert raw["receipt"]["evaluation_completed"] is False
        calls.append(response.case_ref)
        return original(response)

    monkeypatch.setattr(m, "_external_grade", grade)
    result = m.evaluate_response_batch(_PROTOCOL, _IMPLEMENTATION, path)
    assert len(calls) == 128 and len(result.receipt.grades) == 128


def test_capture_has_no_grader_or_behavioral_group_input(monkeypatch):
    original, calls = adapter.derive_successor_repaired_addition, []

    def forbidden(*args, **kwargs):
        raise AssertionError("Response capture consulted an external grader")

    def derive(kernel, request, *, local_run_ref, case_ref):
        assert set(request.model_dump()) == {"left", "right"}
        assert case_ref.startswith("math-v063:case:")
        assert local_run_ref.startswith("math-v065:run:")
        calls.append((request, local_run_ref, case_ref))
        return original(
            kernel,
            request,
            local_run_ref=local_run_ref,
            case_ref=case_ref,
        )

    monkeypatch.setattr(m, "_external_grade", forbidden)
    monkeypatch.setattr(addition, "_grade", forbidden)
    monkeypatch.setattr(baseline, "_grade", forbidden)
    monkeypatch.setattr(counting, "_grade", forbidden)
    monkeypatch.setattr(adapter, "derive_successor_repaired_addition", derive)
    batch = m.capture_successor_repair_responses(_PROTOCOL, _IMPLEMENTATION)
    assert len(calls) == 128
    assert sum(
        response.request is None
        for arm in batch.receipt.arms
        for response in arm.responses
    ) == 32
    source = inspect.getsource(m._respond)
    assert ".group" not in source and "expected_answer" not in source and "grade" not in source


def test_external_grader_receives_original_not_effective_requests(
    response_batch, tmp_path, monkeypatch
):
    path = tmp_path / "responses.vsrb"
    m.save_response_batch(_PROTOCOL, _IMPLEMENTATION, path, response_batch)
    original, seen = m._external_grade, []

    def grade(response):
        seen.append(response.request)
        return original(response)

    monkeypatch.setattr(m, "_external_grade", grade)
    m.evaluate_response_batch(_PROTOCOL, _IMPLEMENTATION, path)
    originals = [
        response.request
        for arm in response_batch.receipt.arms
        for response in arm.responses
        if response.request is not None
    ]
    assert seen == originals
    assert any(
        response.reply.effective_request != response.request
        for response in response_batch.receipt.arms[0].responses
        if response.request is not None
    )


def test_extended_grader_preserves_v058_rule_on_shared_domain(response_batch, evaluation):
    taught = response_batch.receipt.arms[0]
    grades = _grade_map(evaluation, "taught_repair")
    for index, response in enumerate(taught.responses[:10]):
        old_request = addition.AdditionRequest.model_validate(
            response.request.model_dump(mode="json")
        )
        old_reply = addition.AdditionReply.model_validate(
            response.reply.addition_reply.model_dump(mode="json")
        )
        old_grade = addition._grade(index, old_request, old_reply)
        assert old_grade.expected_answer == grades[response.case_ref].expected_answer
        assert old_grade.grade == grades[response.case_ref].grade


def test_reload_does_not_teach_respond_walk_or_grade(
    response_batch, evaluation, monkeypatch
):
    def forbidden(*args, **kwargs):
        raise AssertionError("Reload reran teaching, response, walking, or grading")

    monkeypatch.setattr(adapter, "prepare_private_successor_repair_kernel", forbidden)
    monkeypatch.setattr(adapter, "derive_successor_repaired_addition", forbidden)
    monkeypatch.setattr(adapter, "derive_bounded_addition", forbidden)
    monkeypatch.setattr(adapter, "count_forward_bounded", forbidden)
    monkeypatch.setattr(m, "_external_grade", forbidden)
    assert m.load_response_batch(_PROTOCOL, _IMPLEMENTATION, _RESPONSES) == response_batch
    assert m.load_evaluation(_PROTOCOL, _IMPLEMENTATION, _RESPONSES, _RESULT) == evaluation


def test_source_private_canonical_simulation_attention_and_governance_isolation(monkeypatch):
    from verdant_obligations import CounterfactualRuntime, SimulationLedger

    def forbidden(*args, **kwargs):
        raise AssertionError("Math evaluation acquired simulation, Attention, or governance authority")

    monkeypatch.setattr(CounterfactualRuntime, "execute", forbidden)
    monkeypatch.setattr(SimulationLedger, "reserve", forbidden)
    monkeypatch.setattr(VerdantKernel, "record_governance_outcome", forbidden)
    source = repair_protocol.fresh_successor_repair_kernel()
    before = source.snapshot()
    batch = m.capture_successor_repair_responses(_PROTOCOL, _IMPLEMENTATION, source)
    assert source.snapshot() == before
    assert len({id(_private(arm)) for arm in batch.receipt.arms}) >= 1
    assert len({arm.checkpoint_sha256 for arm in batch.receipt.arms}) == 3
    for arm in batch.receipt.arms:
        private = _private(arm)
        assert private.state.cycle == 29
        assert not private.state.obligation_kernels
        assert not private.state.obligation_attention_decisions
        assert not private.state.governance_outcomes
        assert not private.state.council_decisions
        assert not private.state.revisions


@pytest.mark.parametrize(
    "drift", ("protocol", "implementation", "code", "source", "private", "null")
)
def test_mid_capture_drift_or_divergent_null_fails_before_publication(
    tmp_path, monkeypatch, drift
):
    protocol_path = tmp_path / "protocol.vsrp"
    implementation_path = tmp_path / "implementation.vsri"
    protocol_path.write_bytes(_PROTOCOL.read_bytes())
    implementation_path.write_bytes(_IMPLEMENTATION.read_bytes())
    source = repair_protocol.fresh_successor_repair_kernel()
    respond, manifest = m._respond, m._code_manifest
    calls = 0

    def changed_respond(kernel, role, case):
        nonlocal calls
        calls += 1
        result = respond(kernel, role, case)
        if calls == 1:
            if drift == "protocol":
                protocol_path.write_bytes(protocol_path.read_bytes() + b" ")
            elif drift == "implementation":
                implementation_path.write_bytes(implementation_path.read_bytes() + b" ")
            elif drift == "source":
                source.state.cycle += 1
            elif drift == "private":
                kernel.state.cycle += 1
        if drift == "null" and role == "valid_null" and case.case_id.endswith(":0"):
            raw = result.model_dump(mode="json")
            raw["reply"]["local_run_ref"] = "math-v065:run:divergent-null"
            raw["local_run_ref"] = "math-v065:run:divergent-null"
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
        m.capture_successor_repair_responses(
            protocol_path, implementation_path, source
        )
    assert not (tmp_path / "responses.vsrb").exists()


@pytest.mark.parametrize("kind", ("protocol", "implementation"))
def test_stale_foreign_or_nonexact_frozen_inputs_fail_before_response(
    tmp_path, monkeypatch, kind
):
    protocol_path = tmp_path / "protocol.vsrp"
    implementation_path = tmp_path / "implementation.vsri"
    protocol_path.write_bytes(_PROTOCOL.read_bytes())
    implementation_path.write_bytes(_IMPLEMENTATION.read_bytes())
    target = protocol_path if kind == "protocol" else implementation_path
    target.write_bytes(target.read_bytes() + b" ")

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid frozen input reached response execution")

    monkeypatch.setattr(adapter, "prepare_private_successor_repair_kernel", forbidden)
    with pytest.raises(ValueError, match="exact"):
        m.capture_successor_repair_responses(protocol_path, implementation_path)


@pytest.mark.parametrize(
    "attack",
    (
        "execution",
        "protocol_hash",
        "implementation_hash",
        "implementation_receipt",
        "code_hash",
        "code_drop",
        "role_order",
        "arm_drop",
        "arm_duplicate",
        "arm_role",
        "run_ref",
        "case",
        "group",
        "pair",
        "raw_request",
        "response_order",
        "response_role",
        "case_ref",
        "request",
        "input_location",
        "input_type",
        "reply_original",
        "reply_effective",
        "reply_answer",
        "route",
        "instruction_claim",
        "right_lookup",
        "left_lookup",
        "nested_answer",
        "nested_rule",
        "nested_count_request",
        "nested_step",
        "partial_steps",
        "blocked_claim",
        "lesson_transition",
        "lesson_claim",
        "repair_lesson_claim",
        "checkpoint",
        "fingerprint",
        "purpose",
        "installed",
        "evaluated",
        "extra",
    ),
)
def test_fully_rehashed_response_case_route_partial_and_lineage_attacks_fail(
    response_batch, tmp_path, attack
):
    raw = response_batch.model_dump(mode="json")
    receipt, arm = raw["receipt"], raw["receipt"]["arms"][0]
    responses = arm["responses"]
    original, swapped, repaired, ceiling, invalid = (
        responses[0],
        responses[11],
        responses[18],
        responses[24],
        responses[32],
    )
    if attack == "execution":
        receipt["execution"]["scoring"] = "credit_any_answer"
    elif attack == "protocol_hash":
        receipt["protocol_file_sha256"] = "0" * 64
    elif attack == "implementation_hash":
        receipt["implementation_file_sha256"] = "0" * 64
    elif attack == "implementation_receipt":
        receipt["frozen_implementation"]["receipt_sha256"] = "0" * 64
    elif attack == "code_hash":
        receipt["code_sources"][-1]["sha256"] = "0" * 64
    elif attack == "code_drop":
        receipt["code_sources"].pop()
    elif attack == "role_order":
        receipt["arms"].reverse()
    elif attack == "arm_drop":
        receipt["arms"].pop()
    elif attack == "arm_duplicate":
        receipt["arms"][1] = receipt["arms"][0]
    elif attack == "arm_role":
        arm["role"] = "valid_null"
    elif attack == "run_ref":
        arm["local_run_ref"] = "foreign-run"
    elif attack == "case":
        original["case"]["case_id"] = "foreign-case"
    elif attack == "group":
        original["case"]["group"] = "repair_supported"
    elif attack == "pair":
        swapped["case"]["order_pair"] = "foreign-pair"
    elif attack == "raw_request":
        original["case"]["raw_request_json"] = '{"left":8,"right":2}'
    elif attack == "response_order":
        responses.reverse()
    elif attack == "response_role":
        original["role"] = "valid_null"
    elif attack == "case_ref":
        original["case_ref"] = "foreign-case"
    elif attack == "request":
        original["request"]["left"] = 8
    elif attack == "input_location":
        invalid["input_errors"][0]["location"] = ["left"]
    elif attack == "input_type":
        invalid["input_errors"][0]["error_type"] = "missing"
    elif attack == "reply_original":
        swapped["reply"]["original_request"]["left"] = 1
    elif attack == "reply_effective":
        swapped["reply"]["effective_request"] = swapped["request"]
    elif attack == "reply_answer":
        repaired["reply"]["answer"] = 20
    elif attack == "route":
        swapped["reply"]["route_disposition"] = "kept_valid_original_right"
    elif attack == "instruction_claim":
        swapped["reply"]["order_instruction"]["claim_refs"][0] = "foreign"
    elif attack == "right_lookup":
        swapped["reply"]["original_right_lookup"]["status"] = "valid"
    elif attack == "left_lookup":
        swapped["reply"]["original_left_lookup"]["claim_refs"][0] = "foreign"
    elif attack == "nested_answer":
        repaired["reply"]["addition_reply"]["answer"] = 20
    elif attack == "nested_rule":
        repaired["reply"]["addition_reply"]["addition_rule_claim_refs"][0] = "foreign"
    elif attack == "nested_count_request":
        repaired["reply"]["addition_reply"]["counting_request"]["start"] = 18
    elif attack == "nested_step":
        repaired["reply"]["addition_reply"]["counting_reply"]["steps"][0]["to_number"] = 18
    elif attack == "partial_steps":
        ceiling["reply"]["addition_reply"]["counting_reply"]["steps"].clear()
    elif attack == "blocked_claim":
        ceiling["reply"]["addition_reply"]["counting_reply"]["blocked_claim_refs"] = ["forged"]
    elif attack == "lesson_transition":
        arm["lessons"][0]["transition_ref"] = "foreign"
    elif attack == "lesson_claim":
        arm["lessons"][0]["claim_refs"][0] = "foreign"
    elif attack == "repair_lesson_claim":
        arm["lessons"][26]["claim_refs"][0] = "foreign"
    elif attack == "checkpoint":
        arm["checkpoint_base64"] = receipt["arms"][3]["checkpoint_base64"]
    elif attack == "fingerprint":
        arm["kernel_fingerprint"] = "0" * 64
    elif attack == "purpose":
        receipt["purpose"] = "retuned_response_batch"
    elif attack == "installed":
        receipt["private_repair_testimony_installed"] = False
    elif attack == "evaluated":
        receipt["evaluation_completed"] = True
    else:
        receipt["expected_answers"] = [1]
    path = tmp_path / "forged.vsrb"
    path.write_bytes(_rehash_response(raw))
    with pytest.raises((ValueError, TypeError, RuntimeError, IndexError)):
        m.load_response_batch(_PROTOCOL, _IMPLEMENTATION, path)


@pytest.mark.parametrize(
    "attack",
    (
        "execution",
        "protocol_hash",
        "implementation_hash",
        "response_receipt",
        "response_file",
        "code_hash",
        "grade_drop",
        "grade_duplicate",
        "grade_order",
        "grade_role",
        "grade_case",
        "grade_request",
        "grade_response",
        "expected",
        "grade",
        "purpose",
        "barrier",
        "invalids",
        "extra",
    ),
)
def test_fully_rehashed_result_pairing_grade_and_authority_attacks_fail(
    evaluation, tmp_path, attack
):
    raw = evaluation.model_dump(mode="json")
    receipt, grades = raw["receipt"], raw["receipt"]["grades"]
    if attack == "execution":
        receipt["execution"]["denominators"] = "supported_only"
    elif attack == "protocol_hash":
        receipt["protocol_file_sha256"] = "0" * 64
    elif attack == "implementation_hash":
        receipt["implementation_file_sha256"] = "0" * 64
    elif attack == "response_receipt":
        receipt["response_batch_receipt_sha256"] = "0" * 64
    elif attack == "response_file":
        receipt["response_batch_file_sha256"] = "0" * 64
    elif attack == "code_hash":
        receipt["code_sources"][-1]["sha256"] = "0" * 64
    elif attack == "grade_drop":
        grades.pop()
    elif attack == "grade_duplicate":
        grades[1] = grades[0]
    elif attack == "grade_order":
        grades.reverse()
    elif attack == "grade_role":
        grades[0]["role"] = "valid_null"
    elif attack == "grade_case":
        grades[0]["case_ref"] = "foreign-case"
    elif attack == "grade_request":
        grades[0]["original_request"]["left"] = 8
    elif attack == "grade_response":
        grades[0]["response_sha256"] = "0" * 64
    elif attack == "expected":
        grades[0]["expected_answer"] += 1
    elif attack == "grade":
        grades[0]["grade"] = "incorrect"
    elif attack == "purpose":
        receipt["purpose"] = "generalized_arithmetic"
    elif attack == "barrier":
        receipt["responses_durable_before_grading"] = False
    elif attack == "invalids":
        receipt["invalid_inputs_retained_ungraded"] = False
    else:
        receipt["promotion"] = True
    path = tmp_path / "forged.vsrr"
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
    path.write_bytes(
        _rehash_response(raw) if target == "response" else _rehash_result(raw)
    )
    with pytest.raises(ValueError):
        if target == "response":
            m.load_response_batch(_PROTOCOL, _IMPLEMENTATION, path)
        else:
            m.load_evaluation(_PROTOCOL, _IMPLEMENTATION, _RESPONSES, path)


@pytest.mark.parametrize("target", ("response", "result"))
@pytest.mark.parametrize(
    "attack", ("duplicate_key", "noncanonical", "oversized", "bad_hash", "missing")
)
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
    path = tmp_path / "pretty.vsrb"
    path.write_text(json.dumps(json.loads(_RESPONSES.read_bytes()), indent=2))
    with pytest.raises(ValueError, match="canonical"):
        m.load_response_batch(_PROTOCOL, _IMPLEMENTATION, path)
    with pytest.raises(ValueError):
        m.load_evaluation(_PROTOCOL, _IMPLEMENTATION, path, _RESULT)


@pytest.mark.parametrize(
    "writer,target_kind",
    (
        ("response", "protocol"),
        ("response", "implementation"),
        ("response", "code"),
        ("response", "history"),
        ("response", "probe"),
        ("result", "protocol"),
        ("result", "implementation"),
        ("result", "response"),
        ("result", "code"),
        ("result", "history"),
        ("result", "probe"),
    ),
)
def test_writers_cannot_replace_inputs_code_history_probes_or_responses(
    response_batch, evaluation, writer, target_kind
):
    target = {
        "protocol": _PROTOCOL,
        "implementation": _IMPLEMENTATION,
        "response": _RESPONSES,
        "code": _ROOT / "verdant_math/successor_repair_evaluation/evaluation.py",
        "history": _ROOT / repair_protocol._HISTORY[0][0],
        "probe": _ROOT / repair_protocol._PROBE_FILES[0],
    }[target_kind]
    before = target.read_bytes()
    with pytest.raises(ValueError, match="Cannot publish"):
        if writer == "response":
            m.save_response_batch(_PROTOCOL, _IMPLEMENTATION, target, response_batch)
        else:
            m.save_evaluation(
                _PROTOCOL, _IMPLEMENTATION, _RESPONSES, target, evaluation
            )
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


def test_cli_run_replay_and_response_barrier_failure_modes(
    tmp_path, capsys, monkeypatch
):
    response_path = tmp_path / "responses.vsrb"
    result_path = tmp_path / "evaluation.vsrr"
    assert cli(
        [
            "run",
            str(_PROTOCOL),
            str(_IMPLEMENTATION),
            str(response_path),
            str(result_path),
        ]
    ) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["responses"] == 160 and summary["grades"] == 128
    assert cli(
        [
            "replay",
            str(_PROTOCOL),
            str(_IMPLEMENTATION),
            str(response_path),
            str(result_path),
        ]
    ) == 0
    assert json.loads(capsys.readouterr().out) == summary

    response_after_failure = tmp_path / "complete-before-grade.vsrb"
    no_result = tmp_path / "no-result.vsrr"

    def failed_grade(*args, **kwargs):
        raise RuntimeError("injected grader failure")

    monkeypatch.setattr(m, "_external_grade", failed_grade)
    assert cli(
        [
            "run",
            str(_PROTOCOL),
            str(_IMPLEMENTATION),
            str(response_after_failure),
            str(no_result),
        ]
    ) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid"
    assert len(
        m.load_response_batch(
            _PROTOCOL, _IMPLEMENTATION, response_after_failure
        ).receipt.arms
    ) == 4
    assert not no_result.exists()


def test_capture_failure_never_publishes_partial_role_batch(
    tmp_path, capsys, monkeypatch
):
    response_path = tmp_path / "partial.vsrb"
    result_path = tmp_path / "partial.vsrr"
    original, calls = m._respond, 0

    def fail(kernel, role, case):
        nonlocal calls
        calls += 1
        if calls == 101:
            raise RuntimeError("injected role-three failure")
        return original(kernel, role, case)

    monkeypatch.setattr(m, "_respond", fail)
    assert cli(
        [
            "run",
            str(_PROTOCOL),
            str(_IMPLEMENTATION),
            str(response_path),
            str(result_path),
        ]
    ) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid"
    assert not response_path.exists() and not result_path.exists()


def test_manifest_and_all_older_artifacts_remain_byte_exact(response_batch):
    historical = [_ROOT / path for path, _ in repair_protocol._HISTORY]
    paths = [*historical, _PROTOCOL, _IMPLEMENTATION]
    before = tuple(path.read_bytes() for path in paths)
    assert len(response_batch.receipt.code_sources) == 49
    protocol = repair_protocol.load_successor_repair_protocol(_PROTOCOL)
    implementation = adapter.load_successor_repair_adapter(
        _PROTOCOL, _IMPLEMENTATION
    )
    assert len(protocol.declaration.code_sources) == 43
    assert len(implementation.receipt.code_sources) == 46
    assert response_batch.receipt.frozen_protocol == protocol
    assert response_batch.receipt.frozen_implementation == implementation
    assert tuple(path.read_bytes() for path in paths) == before


def test_claim_boundaries_and_physical_track_remain_untouched(
    response_batch, evaluation
):
    for receipt in (response_batch.receipt, evaluation.receipt):
        for flag in m._FALSE_FLAGS:
            assert getattr(receipt, flag) is False
    assert response_batch.receipt.private_repair_testimony_installed is True
    assert response_batch.receipt.prospective_cohort_executed is True
    assert response_batch.receipt.prospective_responses_observed is True
    assert response_batch.receipt.evaluation_completed is False
    assert evaluation.receipt.responses_durable_before_grading is True
    assert evaluation.receipt.invalid_inputs_retained_ungraded is True
    assert evaluation.receipt.evaluation_completed is True
