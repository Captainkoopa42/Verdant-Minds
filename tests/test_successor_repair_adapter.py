from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from verdant_claims import ClaimLearningPipeline
from verdant_kernel import ClaimPolarity, ClaimSourceClass, VerdantKernel
from verdant_kernel.models import canonical_json_bytes
from verdant_math import teaching_pilot as baseline
from verdant_math.addition import pilot as addition
from verdant_math.counting import pilot as counting
from verdant_math.ordering_adapter import adapter as ordering_adapter
from verdant_math.ordering_evaluation import evaluation
from verdant_math.successor_repair_adapter import adapter as m
from verdant_math.successor_repair_adapter.cli import main as cli
from verdant_math.successor_repair_protocol import protocol as repair_protocol


PROTOCOL_PATH = m._ROOT / "artifacts/terminal_successor_v063/protocol.vsrp"
IMPLEMENTATION_PATH = m._ROOT / "artifacts/terminal_successor_v064/implementation.vsri"
CONSUMED_ANCHORS = (
    (18, 3), (17, 3), (16, 4), (17, 4),
    (3, 18), (3, 17), (4, 16), (4, 17),
)
CONSUMED_PROBES = ((9, 3), (3, 9), (13, 1), (1, 13), (6, 6), (16, 3), (18, 1), (9, 5))


@pytest.fixture(scope="module")
def protocol():
    return repair_protocol.load_successor_repair_protocol(PROTOCOL_PATH)


@pytest.fixture(scope="module")
def implementation():
    return m.freeze_successor_repair_adapter(PROTOCOL_PATH)


def _request(left=18, right=3):
    return m.BoundedAdditionRequestV064(left=left, right=right)


def _private(role="taught_repair"):
    return m.prepare_private_successor_repair_kernel(role)[0]


def _reply(kernel, left=18, right=3, suffix="test"):
    request = _request(left, right)
    return m.derive_successor_repaired_addition(
        kernel,
        request,
        local_run_ref=f"consumed-run-{suffix}",
        case_ref=f"consumed-case-{left}-{right}-{suffix}",
    )


def _claim(
    kernel,
    subject,
    predicate,
    target,
    key,
    *,
    polarity=ClaimPolarity.AFFIRMED,
    source_class=ClaimSourceClass.HUMAN_TESTIMONY,
):
    return ClaimLearningPipeline().record_claim(
        kernel,
        event_key=f"repair-test:{key}",
        native_description=f"Declared repair test: {subject} {predicate} {target}.",
        subject_label=subject,
        predicate=predicate,
        object_label=target,
        polarity=polarity,
        source_class=source_class,
        source_ref="declared-repair-adversary",
    ).kernel_result


def _rehash(raw):
    raw["receipt_sha256"] = baseline._sha(canonical_json_bytes(raw["receipt"]))
    return canonical_json_bytes(raw)


def _private_without_order():
    source = repair_protocol.fresh_successor_repair_kernel()
    private = VerdantKernel.from_state(source.snapshot())
    addition._teach(private, "taught")
    m._install_repair_slots(private, "taught_repair")
    return private


def test_all_adapter_vectors_are_consumed_or_recorded_and_never_v063_prospective(protocol):
    excluded = set(protocol.declaration.excluded_raw_requests)
    prospective = {case.raw_request_json for case in protocol.declaration.cases}
    assert len(prospective) == 40
    for left, right in (*CONSUMED_ANCHORS, *CONSUMED_PROBES):
        raw = canonical_json_bytes({"left": left, "right": right}).decode()
        assert raw in excluded
        assert raw not in prospective


def test_old_types_remain_bounded_to_18_while_new_sibling_is_exactly_0_through_21():
    for number in (19, 20, 21):
        with pytest.raises(ValueError):
            addition.AdditionRequest(left=number, right=0)
        with pytest.raises(ValueError):
            counting.CountingRequest(start=number, ticks=())
        assert _request(number, 0).left == number
        assert m.BoundedCountingRequestV064(start=number, ticks=()).start == number
    for model, raw in (
        (m.BoundedAdditionRequestV064, {"left": 22, "right": 0}),
        (m.BoundedCountingRequestV064, {"start": 22, "ticks": []}),
    ):
        with pytest.raises(ValueError):
            model.model_validate(raw)


def test_taught_repair_replays_all_eight_consumed_terminal_anchors_without_grader(protocol):
    kernel = _private()
    before = kernel.fingerprint()
    expected = {anchor.case_ref: anchor for anchor in protocol.declaration.failure_anchors}
    for index, (left, right) in enumerate(CONSUMED_ANCHORS, 24):
        reply = _reply(kernel, left, right, f"anchor-{index}")
        anchor = expected[f"math-v060:case:{index}"]
        assert reply.original_request == _request(left, right)
        assert reply.answer == anchor.expected_answer
        assert reply.status == "derived"
        assert reply.addition_reply.reason == "teacher_scaffold_addition"
        assert reply.addition_reply.counting_reply.reason == "teacher_scaffold_walk"
        assert any(step.from_number >= 18 for step in reply.addition_reply.counting_reply.steps)
        m.verify_successor_repair_derivation(kernel, reply.original_request, reply)
    assert kernel.fingerprint() == before


def test_reversed_consumed_anchor_preserves_original_and_one_authorized_transposition():
    kernel = _private()
    reply = _reply(kernel, 3, 18, "reversed-anchor")
    assert reply.route_disposition == "swapped_missing_original_right"
    assert reply.original_request == _request(3, 18)
    assert reply.effective_request == _request(18, 3)
    assert reply.original_right_lookup.status == "missing"
    assert reply.original_left_lookup.status == "valid"
    assert reply.answer == 21
    assert [(step.from_number, step.to_number) for step in reply.addition_reply.counting_reply.steps] == [
        (18, 19), (19, 20), (20, 21),
    ]


def test_no_repair_control_retains_each_original_v062_partial_walk(protocol):
    kernel = _private("no_repair_control")
    for index, (left, right) in enumerate(CONSUMED_ANCHORS, 24):
        reply = _reply(kernel, left, right, f"no-repair-{index}")
        anchor = protocol.declaration.failure_anchors[index - 24]
        counted = reply.addition_reply.counting_reply
        assert reply.answer is None and reply.status == "abstained"
        assert counted.reason == "missing_successor"
        assert tuple((step.from_number, step.to_number) for step in counted.steps) == tuple(
            (step.from_number, step.to_number) for step in anchor.partial_steps
        )
        assert not counted.blocked_claim_refs and not counted.blocked_evidence_refs
        m.verify_successor_repair_derivation(kernel, reply.original_request, reply)


def test_wrong_link_control_follows_fixed_testimony_and_retains_cycle_without_oracle_repair():
    kernel = _private("wrong_link_control")
    reply = _reply(kernel, 18, 3, "wrong-chain")
    counted = reply.addition_reply.counting_reply
    assert reply.answer is None and reply.addition_reply.reason == "counting_abstained"
    assert counted.reason == "cyclic_successor"
    assert [(step.from_number, step.to_number) for step in counted.steps] == [(18, 20)]
    assert counted.blocked_claim_refs and counted.blocked_evidence_refs
    claim = kernel.state.claims[counted.blocked_claim_refs[0]]
    assert kernel.state.concepts[claim.subject_concept_id].label == "math:integer:20"
    assert kernel.state.concepts[claim.object_concept_id].label == "math:integer:18"
    m.verify_successor_repair_derivation(kernel, reply.original_request, reply)


def test_taught_and_valid_null_private_installations_and_consumed_replies_are_exact():
    source = repair_protocol.fresh_successor_repair_kernel()
    before = source.snapshot()
    taught, taught_lessons = m.prepare_private_successor_repair_kernel("taught_repair", source)
    null, null_lessons = m.prepare_private_successor_repair_kernel("valid_null", source)
    assert source.snapshot() == before
    assert taught is not null and taught.fingerprint() == null.fingerprint()
    assert taught_lessons == null_lessons and len(taught_lessons) == 29
    for left, right in CONSUMED_ANCHORS:
        taught_reply = _reply(taught, left, right, "exact-null")
        null_reply = _reply(null, left, right, "exact-null")
        assert taught_reply == null_reply


@pytest.mark.parametrize("role", m._ROLES)
def test_all_roles_share_exact_25_addition_lessons_and_correct_order_instruction(role):
    _, reference = m.prepare_private_successor_repair_kernel("taught_repair")
    _, lessons = m.prepare_private_successor_repair_kernel(role)
    assert len(lessons) == 29
    assert lessons[:26] == reference[:26]
    assert all(lesson.object_label is not None for lesson in lessons[:26])
    assert lessons[25].subject_label == ordering_adapter._PROCEDURE
    assert lessons[25].object_label == ordering_adapter._CORRECT
    assert tuple(lesson.subject_label for lesson in lessons[26:]) == (
        "math:integer:18", "math:integer:19", "math:integer:20",
    )


def test_no_repair_slots_are_visible_prompt_evidence_without_successor_claims():
    kernel, lessons = m.prepare_private_successor_repair_kernel("no_repair_control")
    assert all(lesson.object_label is None and not lesson.claim_refs for lesson in lessons[26:])
    assert all(lesson.evidence_refs for lesson in lessons[26:])
    for number in (18, 19, 20, 21):
        match = counting._lookup(kernel, f"math:integer:{number}", "math_successor")
        assert match.status == "missing" and not match.claim_refs and not match.evidence_refs


@pytest.mark.parametrize(
    "role,expected",
    (("taught_repair", m._CORRECT_SUCCESSORS),
     ("valid_null", m._CORRECT_SUCCESSORS),
     ("wrong_link_control", m._WRONG_SUCCESSORS)),
)
def test_supplied_successor_slots_are_exact_native_human_testimony(role, expected):
    kernel, lessons = m.prepare_private_successor_repair_kernel(role)
    assert tuple(
        (int(lesson.subject_label.rsplit(":", 1)[1]), int(lesson.object_label.rsplit(":", 1)[1]))
        for lesson in lessons[26:]
    ) == expected
    for source_number, target_number in expected:
        match = counting._lookup(kernel, f"math:integer:{source_number}", "math_successor")
        assert match.status == "found" and match.label == f"math:integer:{target_number}"
        claim = kernel.state.claims[match.claim_refs[0]]
        assert len(claim.support_ledger) == 1
        assert claim.support_ledger[0].source_class == ClaimSourceClass.HUMAN_TESTIMONY
        assert match.evidence_refs


@pytest.mark.parametrize("role", m._ROLES)
def test_private_teaching_never_mutates_source_or_grants_other_authority(role):
    source = repair_protocol.fresh_successor_repair_kernel()
    before = source.snapshot()
    private, _ = m.prepare_private_successor_repair_kernel(role, source)
    assert source.snapshot() == before
    assert private is not source
    assert not private.state.council_decisions and not private.state.governance_outcomes
    assert not private.state.obligation_attention_decisions and not private.state.obligation_kernels
    assert not private.state.revisions


@pytest.mark.parametrize("role", ("foreign", "", None, 1))
def test_unknown_role_fails_before_private_teaching(role):
    source = repair_protocol.fresh_successor_repair_kernel()
    before = source.snapshot()
    with pytest.raises(ValueError, match="role"):
        m.prepare_private_successor_repair_kernel(role, source)
    assert source.snapshot() == before


@pytest.mark.parametrize("kind", ("foreign", "drifted", "historical"))
def test_private_installer_rejects_noncanonical_source(kind):
    if kind == "foreign":
        source = VerdantKernel(seed=79064, state_dim=16, run_label="foreign")
    elif kind == "drifted":
        source = repair_protocol.fresh_successor_repair_kernel()
        source.state.cycle = 1
    else:
        source = _private()
    before = source.snapshot()
    with pytest.raises(ValueError, match="fresh"):
        m.prepare_private_successor_repair_kernel("taught_repair", source)
    assert source.snapshot() == before


def test_math_integer_21_has_no_silent_successor_or_fabricated_evidence():
    kernel = _private()
    match = counting._lookup(kernel, "math:integer:21", "math_successor")
    assert match.status == "missing"
    assert match.label is None and not match.claim_refs and not match.evidence_refs
    assert m._IMPLEMENTATION["terminal_ceiling"].startswith("math_integer_21_has_no_declared_successor")


@pytest.mark.parametrize("mode", ("missing", "conflicting", "invalid", "unsupported"))
def test_missing_or_blocked_terminal_successor_retains_native_provenance(mode):
    kernel = _private("no_repair_control")
    if mode == "conflicting":
        _claim(kernel, "math:integer:18", "math_successor", "math:integer:19", "edge-a")
        _claim(kernel, "math:integer:18", "math_successor", "math:integer:20", "edge-b")
    elif mode == "invalid":
        _claim(
            kernel,
            "math:integer:18",
            "math_successor",
            "math:integer:19",
            "edge-invalid",
            source_class=ClaimSourceClass.SYSTEM_INFERENCE,
        )
    elif mode == "unsupported":
        _claim(kernel, "math:integer:18", "math_successor", "math:integer:22", "edge-wide")
    reply = _reply(kernel, 18, 3, f"edge-{mode}")
    counted = reply.addition_reply.counting_reply
    expected = "invalid_successor" if mode == "unsupported" else f"{mode}_successor"
    assert counted.reason == expected and reply.answer is None
    if mode == "missing":
        assert not counted.blocked_claim_refs and not counted.blocked_evidence_refs
    else:
        assert counted.blocked_claim_refs and counted.blocked_evidence_refs


@pytest.mark.parametrize("mode", ("missing", "conflicting", "invalid", "unsupported"))
def test_missing_or_blocked_order_instruction_prevents_dispatch(mode):
    kernel = _private_without_order()
    if mode == "conflicting":
        _claim(kernel, ordering_adapter._PROCEDURE, ordering_adapter._PREDICATE,
               ordering_adapter._CORRECT, "order-a")
        _claim(kernel, ordering_adapter._PROCEDURE, ordering_adapter._PREDICATE,
               ordering_adapter._INCORRECT, "order-b")
    elif mode == "invalid":
        _claim(kernel, ordering_adapter._PROCEDURE, ordering_adapter._PREDICATE,
               ordering_adapter._CORRECT, "order-invalid",
               source_class=ClaimSourceClass.PHYSICAL_OUTCOME)
    elif mode == "unsupported":
        _claim(kernel, ordering_adapter._PROCEDURE, ordering_adapter._PREDICATE,
               ordering_adapter._INCORRECT, "order-unsupported")
    reply = _reply(kernel, 18, 3, f"order-{mode}")
    assert reply.route_disposition == "blocked_order_instruction"
    assert reply.order_instruction.status == mode
    assert reply.effective_request is None and reply.addition_reply is None


@pytest.mark.parametrize("mode", ("conflicting", "invalid", "unsupported"))
def test_nonmissing_original_right_mapping_blocks_and_remains_visible(mode):
    kernel = _private()
    if mode == "conflicting":
        _claim(kernel, "math:integer:3", "math_counting_tokens", "math:tokens:tick", "right-conflict")
        request = (18, 3)
    elif mode == "invalid":
        _claim(kernel, "math:integer:18", "math_counting_tokens", "math:tokens:tick", "right-invalid",
               source_class=ClaimSourceClass.SYSTEM_INFERENCE)
        request = (3, 18)
    else:
        _claim(kernel, "math:integer:18", "math_counting_tokens", "untrusted:tokens", "right-unsupported")
        request = (3, 18)
    reply = _reply(kernel, *request, suffix=f"right-{mode}")
    assert reply.route_disposition == "blocked_original_right_mapping"
    assert reply.original_right_lookup.status == mode
    assert reply.original_right_lookup.claim_refs and reply.original_right_lookup.evidence_refs
    assert reply.original_left_lookup is None and reply.addition_reply is None


@pytest.mark.parametrize("mode", ("missing", "conflicting", "invalid", "unsupported"))
def test_failed_original_left_authorization_retains_both_lookups(mode):
    kernel = _private()
    if mode == "missing":
        request = (9, 5)
    elif mode == "conflicting":
        _claim(kernel, "math:integer:3", "math_counting_tokens", "math:tokens:tick", "left-conflict")
        request = (3, 18)
    elif mode == "invalid":
        _claim(kernel, "math:integer:9", "math_counting_tokens", "math:tokens:tick", "left-invalid",
               source_class=ClaimSourceClass.SYSTEM_INFERENCE)
        request = (9, 5)
    else:
        _claim(kernel, "math:integer:9", "math_counting_tokens", "untrusted:tokens", "left-unsupported")
        request = (9, 5)
    reply = _reply(kernel, *request, suffix=f"left-{mode}")
    assert reply.route_disposition == "blocked_original_left_mapping"
    assert reply.original_right_lookup.status == "missing"
    assert reply.original_left_lookup.status == mode
    assert reply.effective_request is None and reply.addition_reply is None


def test_native_mapping_not_integer_value_controls_route_and_answer():
    kernel = _private()
    _claim(kernel, "math:integer:18", "math_counting_tokens", "math:tokens:tick,tick", "eighteen-two")
    reply = _reply(kernel, 3, 18, "native-not-numeric")
    assert reply.route_disposition == "kept_valid_original_right"
    assert reply.original_right_lookup.tokens == ("tick", "tick")
    assert reply.effective_request == _request(3, 18)
    assert reply.answer == 5
    assert [(step.from_number, step.to_number) for step in reply.addition_reply.counting_reply.steps] == [
        (3, 4), (4, 5),
    ]


def test_adapter_does_not_call_old_bounded_interpreters_or_external_grader(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Versioned repair consulted an old bounded responder or grader")

    for module, names in (
        (counting, ("count_forward", "verify_counting_derivation", "_grade")),
        (addition, ("derive_addition", "verify_addition_derivation", "_grade")),
        (ordering_adapter, ("derive_ordered_addition", "verify_order_derivation")),
        (evaluation, ("_score", "evaluate_response_batch")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    kernel = _private()
    reply = _reply(kernel, 18, 3, "versioned-only")
    assert reply.answer == 21
    m.verify_successor_repair_derivation(kernel, reply.original_request, reply)


def test_adapter_does_not_read_prospective_cases_groups_targets_or_grades(monkeypatch):
    class ForbiddenTable:
        def __iter__(self):
            raise AssertionError("Repair adapter consulted a prospective table")
        def __getitem__(self, key):
            raise AssertionError("Repair adapter consulted a prospective table")

    def forbidden(*args, **kwargs):
        raise AssertionError("Repair adapter consulted an external arithmetic evaluator")

    kernel = _private()
    monkeypatch.setattr(repair_protocol, "_ROWS", ForbiddenTable())
    monkeypatch.setattr(repair_protocol, "_cases", forbidden)
    monkeypatch.setattr(addition, "_CASES", ForbiddenTable())
    monkeypatch.setattr(counting, "_CASES", ForbiddenTable())
    monkeypatch.setattr(addition, "_grade", forbidden)
    monkeypatch.setattr(evaluation, "_score", forbidden)
    before = kernel.fingerprint()
    reply = _reply(kernel, 3, 18, "no-prospective")
    assert reply.answer == 21
    assert kernel.fingerprint() == before


def test_adapter_dispatches_bounded_addition_at_most_once_and_never_retries(monkeypatch):
    kernel = _private()
    original, calls = m.derive_bounded_addition, []

    def collect(target, request):
        calls.append(request)
        return original(target, request)

    monkeypatch.setattr(m, "derive_bounded_addition", collect)
    reply = _reply(kernel, 3, 18, "single-dispatch")
    assert reply.answer == 21 and calls == [_request(18, 3)]
    calls.clear()
    blocked = _reply(kernel, 6, 6, "zero-dispatch")
    assert blocked.answer is None and calls == []


@pytest.mark.parametrize("field", (
    "adapter_version", "protocol", "fingerprint", "original", "effective", "status", "answer",
    "route", "instruction_status", "instruction_label", "instruction_claim", "right_operand",
    "right_status", "right_tokens", "right_claim", "left_drop", "nested_answer", "nested_rule_ref",
    "count_start", "step_from", "step_to", "step_claim", "extra",
))
def test_tampered_route_provenance_or_nested_versioned_trace_fails(field):
    kernel = _private()
    reply = _reply(kernel, 3, 18, "tamper")
    raw = reply.model_dump(mode="json")
    if field == "adapter_version": raw[field] = "retuned"
    elif field == "protocol": raw["protocol_declaration_sha256"] = "0" * 64
    elif field == "fingerprint": raw["private_kernel_fingerprint"] = "0" * 64
    elif field == "original": raw["original_request"] = {"left": 18, "right": 3}
    elif field == "effective": raw["effective_request"] = {"left": 3, "right": 18}
    elif field == "status": raw["status"] = "abstained"
    elif field == "answer": raw["answer"] = 20
    elif field == "route": raw["route_disposition"] = "kept_valid_original_right"
    elif field == "instruction_status": raw["order_instruction"]["status"] = "unsupported"
    elif field == "instruction_label": raw["order_instruction"]["label"] = ordering_adapter._INCORRECT
    elif field == "instruction_claim": raw["order_instruction"]["claim_refs"][0] = "claim_foreign"
    elif field == "right_operand": raw["original_right_lookup"]["operand"] = 17
    elif field == "right_status": raw["original_right_lookup"]["status"] = "valid"
    elif field == "right_tokens": raw["original_right_lookup"]["tokens"] = ["tick"]
    elif field == "right_claim": raw["original_right_lookup"]["claim_refs"] = ["claim_foreign"]
    elif field == "left_drop": raw["original_left_lookup"] = None
    elif field == "nested_answer": raw["addition_reply"]["answer"] = 20
    elif field == "nested_rule_ref": raw["addition_reply"]["addition_rule_claim_refs"][0] = "claim_foreign"
    elif field == "count_start": raw["addition_reply"]["counting_request"]["start"] = 17
    elif field == "step_from": raw["addition_reply"]["counting_reply"]["steps"][0]["from_number"] = 17
    elif field == "step_to": raw["addition_reply"]["counting_reply"]["steps"][0]["to_number"] = 20
    elif field == "step_claim": raw["addition_reply"]["counting_reply"]["steps"][0]["claim_ref"] = "claim_foreign"
    else: raw["expected_answer"] = 21
    try:
        forged = m.SuccessorRepairReplyV064.model_validate(raw)
    except ValueError:
        return
    with pytest.raises(ValueError):
        m.verify_successor_repair_derivation(kernel, reply.original_request, forged)


def test_trace_from_foreign_private_role_fails_before_replay():
    taught = _private()
    no_repair = _private("no_repair_control")
    reply = _reply(taught, 18, 3, "foreign-private")
    with pytest.raises(ValueError, match="another private kernel"):
        m.verify_successor_repair_derivation(no_repair, reply.original_request, reply)


def test_freeze_replay_and_summary_do_not_teach_answer_grade_allocate_or_simulate(
    protocol, tmp_path, monkeypatch,
):
    from verdant_obligations import AttentionPortfolio, CounterfactualRuntime, SimulationLedger

    def forbidden(*args, **kwargs):
        raise AssertionError("Implementation freeze cannot teach, answer, grade, allocate or simulate")

    for module, names in (
        (m, ("prepare_private_successor_repair_kernel", "derive_successor_repaired_addition")),
        (addition, ("_teach", "derive_addition", "_grade")),
        (counting, ("_teach", "count_forward", "_grade")),
        (ordering_adapter, ("_install_order_slot", "derive_ordered_addition")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(ClaimLearningPipeline, "record_claim", forbidden)
    monkeypatch.setattr(VerdantKernel, "apply_experience", forbidden)
    monkeypatch.setattr(CounterfactualRuntime, "execute", forbidden)
    monkeypatch.setattr(SimulationLedger, "reserve", forbidden)
    for name in ("allocate", "decide"):
        if hasattr(AttentionPortfolio, name):
            monkeypatch.setattr(AttentionPortfolio, name, forbidden)
    frozen = m.freeze_successor_repair_adapter(PROTOCOL_PATH)
    path = tmp_path / "implementation.vsri"
    first = m.save_successor_repair_adapter(PROTOCOL_PATH, path, frozen)
    assert m.save_successor_repair_adapter(PROTOCOL_PATH, path, frozen) == first
    assert m.load_successor_repair_adapter(PROTOCOL_PATH, path) == frozen
    assert frozen.receipt.frozen_protocol == protocol
    summary = m.adapter_summary(frozen)
    assert summary["repair_adapter_implemented"] and summary["bounded_native_trace_verifier_implemented"]
    assert not summary["prospective_cohort_executed"] and not summary["prospective_responses_observed"]
    assert not summary["repair_effect_observed"]


def test_implementation_pairs_exact_v063_bytes_and_extends_only_three_sources(implementation):
    assert PROTOCOL_PATH.stat().st_size == 39_943
    assert baseline._sha(PROTOCOL_PATH.read_bytes()) == m._PROTOCOL_FILE_SHA256
    receipt = implementation.receipt
    assert receipt.frozen_protocol.declaration_sha256 == m._PROTOCOL_DECLARATION_SHA256
    assert len(receipt.frozen_protocol.declaration.code_sources) == 43
    assert len(receipt.code_sources) == 46
    old = {source.path: source for source in receipt.frozen_protocol.declaration.code_sources}
    current = {source.path: source for source in receipt.code_sources}
    assert all(current[path] == source for path, source in old.items())
    assert set(current) - set(old) == {
        "verdant_math/successor_repair_adapter/__init__.py",
        "verdant_math/successor_repair_adapter/adapter.py",
        "verdant_math/successor_repair_adapter/cli.py",
    }
    for source in receipt.code_sources:
        assert source.sha256 == baseline._sha((m._ROOT / source.path).read_bytes())


def test_published_implementation_sidecar_is_exact_immutable_and_replayable(implementation):
    assert IMPLEMENTATION_PATH.stat().st_size == 48_633
    assert baseline._sha(IMPLEMENTATION_PATH.read_bytes()) == (
        "397231910c27b8a429551e326fc11f880d3522466438de09a57534825be9d83d"
    )
    assert implementation.receipt_sha256 == (
        "19e0363f65400308d49455b887ffb33dcdf7a3e0bbce93bc3bb0eadc320160c2"
    )
    assert m.load_successor_repair_adapter(PROTOCOL_PATH, IMPLEMENTATION_PATH) == implementation


@pytest.mark.parametrize("attack", (
    "implementation_version", "domain", "correct_slot", "wrong_slot", "protocol_hash",
    "protocol_file_hash", "protocol_case", "protocol_anchor", "manifest_hash", "manifest_drop",
    "purpose", "adapter_false", "installer_false", "verifier_false", "repair_install", "responses",
    "cohort", "evaluation", "effect", "causal", "discovery", "generalized", "understanding",
    "efficiency", "source_auth", "physical", "harm", "replication", "canonical", "resolution",
    "promotion", "rewrite", "extra",
))
def test_fully_rehashed_implementation_protocol_code_or_authority_substitution_fails(
    implementation, tmp_path, attack,
):
    raw = implementation.model_dump(mode="json")
    receipt = raw["receipt"]
    spec = receipt["implementation"]
    if attack == "implementation_version": spec["version"] = "retuned"
    elif attack == "domain": spec["bounded_domain"] = "zero_through_twenty_two"
    elif attack == "correct_slot": spec["role_slots"]["taught_repair"][0] = [18, 20]
    elif attack == "wrong_slot": spec["role_slots"]["wrong_link_control"][0] = [18, 19]
    elif attack == "protocol_hash": receipt["frozen_protocol"]["declaration_sha256"] = "0" * 64
    elif attack == "protocol_file_hash": receipt["protocol_file_sha256"] = "0" * 64
    elif attack == "protocol_case": receipt["frozen_protocol"]["declaration"]["cases"][0]["case_id"] = "changed"
    elif attack == "protocol_anchor": receipt["frozen_protocol"]["declaration"]["failure_anchors"][0]["case_ref"] = "foreign"
    elif attack == "manifest_hash": receipt["code_sources"][-1]["sha256"] = "0" * 64
    elif attack == "manifest_drop": receipt["code_sources"].pop()
    elif attack == "purpose": receipt["purpose"] = "prospective_evaluation"
    elif attack == "adapter_false": receipt["repair_adapter_implemented"] = False
    elif attack == "installer_false": receipt["private_repair_installer_implemented"] = False
    elif attack == "verifier_false": receipt["bounded_native_trace_verifier_implemented"] = False
    elif attack == "extra": receipt["responses"] = [21]
    else:
        key = {
            "repair_install": "prospective_repair_testimony_installed",
            "responses": "prospective_responses_observed",
            "cohort": "prospective_cohort_executed",
            "evaluation": "evaluation_completed",
            "effect": "repair_effect_observed",
            "causal": "causal_self_repair_observed",
            "discovery": "spontaneous_rule_discovery_observed",
            "generalized": "generalized_arithmetic_claim_permitted",
            "understanding": "mathematical_understanding_claim_permitted",
            "efficiency": "learning_efficiency_observed",
            "source_auth": "source_authenticated",
            "physical": "physical_evidence_admissible",
            "harm": "harm_scoring_implemented",
            "replication": "independent_replication_observed",
            "canonical": "canonical_commit_permitted",
            "resolution": "resolution_authority_enabled",
            "promotion": "promotion_authority_enabled",
            "rewrite": "policy_rewrite_authority_enabled",
        }[attack]
        receipt[key] = True
    path = tmp_path / "forged.vsri"
    path.write_bytes(_rehash(raw))
    with pytest.raises((ValueError, RuntimeError)):
        m.load_successor_repair_adapter(PROTOCOL_PATH, path)


@pytest.mark.parametrize("kind", ("duplicate_key", "noncanonical", "oversized", "missing", "bad_hash"))
def test_corrupt_noncanonical_oversized_or_missing_implementation_fails(implementation, tmp_path, kind):
    path = tmp_path / "bad.vsri"
    if kind == "duplicate_key":
        path.write_text('{"receipt":{},"receipt":{}}')
    elif kind == "noncanonical":
        path.write_text(json.dumps(implementation.model_dump(mode="json"), indent=2))
    elif kind == "oversized":
        path.write_bytes(b" " * (m._MAX_BYTES + 1))
    elif kind == "bad_hash":
        raw = implementation.model_dump(mode="json")
        raw["receipt_sha256"] = "0" * 64
        path.write_bytes(canonical_json_bytes(raw))
    with pytest.raises((ValueError, OSError, RuntimeError)):
        m.load_successor_repair_adapter(PROTOCOL_PATH, path)


def test_protocol_or_code_drift_during_freeze_fails_without_output(monkeypatch, tmp_path):
    original, calls = m._read, 0

    def changed(path):
        nonlocal calls
        data = original(path)
        if Path(path) == PROTOCOL_PATH:
            calls += 1
            return data if calls == 1 else data + b"\n"
        return data

    monkeypatch.setattr(m, "_read", changed)
    with pytest.raises(ValueError, match="changed during"):
        m.freeze_successor_repair_adapter(PROTOCOL_PATH)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("target_kind", ("protocol", "code", "history", "probe"))
def test_implementation_writer_cannot_replace_frozen_inputs(implementation, target_kind):
    target = {
        "protocol": PROTOCOL_PATH,
        "code": m._ROOT / "verdant_math/successor_repair_adapter/adapter.py",
        "history": m._ROOT / repair_protocol._HISTORY[0][0],
        "probe": m._ROOT / repair_protocol._PROBE_FILES[0],
    }[target_kind]
    before = target.read_bytes()
    with pytest.raises(ValueError, match="Cannot publish"):
        m.save_successor_repair_adapter(PROTOCOL_PATH, target, implementation)
    assert target.read_bytes() == before


def test_immutable_path_and_failed_replace_preserve_existing_bytes(implementation, tmp_path, monkeypatch):
    occupied = tmp_path / "occupied.vsri"
    occupied.write_bytes(b"prior implementation")
    with pytest.raises(RuntimeError, match="different evidence"):
        m.save_successor_repair_adapter(PROTOCOL_PATH, occupied, implementation)
    assert occupied.read_bytes() == b"prior implementation"
    target = tmp_path / "failure.vsri"
    monkeypatch.setattr(os, "replace", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("injected replace")))
    with pytest.raises(OSError, match="injected replace"):
        m.save_successor_repair_adapter(PROTOCOL_PATH, target, implementation)
    assert not target.exists() and not tuple(tmp_path.glob(".*.tmp"))


def test_cli_exposes_freeze_and_replay_only_without_run_query_or_evaluate(tmp_path, capsys):
    path = tmp_path / "adapter.vsri"
    assert cli(["freeze", str(PROTOCOL_PATH), str(path)]) == 0
    frozen = json.loads(capsys.readouterr().out)
    assert frozen["repair_adapter_implemented"] and not frozen["prospective_cohort_executed"]
    assert cli(["replay", str(PROTOCOL_PATH), str(path)]) == 0
    assert not json.loads(capsys.readouterr().out)["evaluation_completed"]
    for command in ("run", "query", "evaluate"):
        with pytest.raises(SystemExit):
            cli([command, str(PROTOCOL_PATH), str(path)])


def test_old_artifacts_protocol_and_source_stay_exact_during_adapter_operations():
    paths = [m._ROOT / path for path, _ in repair_protocol._HISTORY] + [PROTOCOL_PATH]
    before = tuple(path.read_bytes() for path in paths)
    source = repair_protocol.fresh_successor_repair_kernel()
    taught, _ = m.prepare_private_successor_repair_kernel("taught_repair", source)
    for index, pair in enumerate((*CONSUMED_ANCHORS, *CONSUMED_PROBES)):
        reply = m.derive_successor_repaired_addition(
            taught,
            _request(*pair),
            local_run_ref="consumed-compatibility",
            case_ref=f"consumed-{index}",
        )
        m.verify_successor_repair_derivation(taught, reply.original_request, reply)
    assert tuple(path.read_bytes() for path in paths) == before
    assert source.fingerprint() == repair_protocol.fresh_successor_repair_kernel().fingerprint()


def test_frozen_receipt_embeds_unanswered_protocol_without_responses_or_grades(protocol, implementation):
    assert implementation.receipt.frozen_protocol.declaration.cases == protocol.declaration.cases
    assert len(implementation.receipt.frozen_protocol.declaration.cases) == 40
    receipt = implementation.receipt.model_dump(mode="json")
    assert "responses" not in receipt and "grades" not in receipt and "arms" not in receipt
    assert not receipt["prospective_repair_testimony_installed"]
    assert not receipt["prospective_cohort_executed"]
    assert not receipt["prospective_responses_observed"]
    assert not receipt["evaluation_completed"]
    assert not receipt["repair_effect_observed"]
