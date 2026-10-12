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
from verdant_math.ordering_adapter import adapter as m
from verdant_math.ordering_adapter.cli import main as cli
from verdant_math.ordering_protocol import protocol as ordering


PROTOCOL_PATH = m._ROOT / "artifacts/operand_order_v060/protocol.vaop"
IMPLEMENTATION_PATH = m._ROOT / "artifacts/operand_order_v061/implementation.vaoi"
CONSUMED = ((9, 3), (3, 9), (13, 1), (1, 13), (6, 6), (16, 3), (18, 1), (9, 5))


@pytest.fixture(scope="module")
def protocol():
    return ordering.load_operand_order_protocol(PROTOCOL_PATH)


@pytest.fixture(scope="module")
def implementation():
    return m.freeze_operand_order_adapter(PROTOCOL_PATH)


def _request(left=9, right=3):
    return addition.AdditionRequest(left=left, right=right)


def _private(role="taught"):
    return m.prepare_private_operand_order_kernel(role)[0]


def _reply(kernel, left=9, right=3, suffix="test"):
    return m.derive_ordered_addition(kernel, _request(left, right),
        local_run_ref=f"consumed-run-{suffix}", case_ref=f"consumed-case-{left}-{right}-{suffix}")


def _claim(kernel, subject, predicate, target, key, *, polarity=ClaimPolarity.AFFIRMED,
           source_class=ClaimSourceClass.HUMAN_TESTIMONY):
    return ClaimLearningPipeline().record_claim(kernel, event_key=f"order-test:{key}",
        native_description=f"Declared order test: {subject} {predicate} {target}.",
        subject_label=subject, predicate=predicate, object_label=target,
        polarity=polarity, source_class=source_class, source_ref="declared-order-adversary").kernel_result


def _rehash(raw):
    raw["receipt_sha256"] = baseline._sha(canonical_json_bytes(raw["receipt"]))
    return canonical_json_bytes(raw)


def test_test_vectors_are_consumed_or_recorded_and_never_v060_prospective(protocol):
    excluded = set(protocol.declaration.excluded_raw_requests)
    prospective = {c.raw_request_json for c in protocol.declaration.cases}
    assert len(prospective) == 40
    for left, right in CONSUMED:
        raw = canonical_json_bytes(dict(left=left, right=right)).decode()
        assert raw in excluded
        assert raw not in prospective


def test_correct_instruction_keeps_valid_right_and_swaps_once_on_native_absence():
    kernel = _private()
    before = kernel.fingerprint()
    kept = _reply(kernel, 9, 3, "kept")
    swapped = _reply(kernel, 3, 9, "swapped")
    assert kept.route_disposition == "kept_valid_original_right"
    assert kept.original_request == kept.effective_request == _request(9, 3)
    assert kept.answer == 12 and kept.original_right_lookup.tokens == ("tick",) * 3
    assert kept.original_left_lookup is None
    assert swapped.route_disposition == "swapped_missing_original_right"
    assert swapped.original_request == _request(3, 9)
    assert swapped.effective_request == _request(9, 3)
    assert swapped.original_right_lookup.status == "missing"
    assert swapped.original_left_lookup.status == "valid"
    assert swapped.original_left_lookup.tokens == ("tick",) * 3
    assert swapped.answer == 12
    for reply in (kept, swapped):
        m.verify_order_derivation(kernel, reply.original_request, reply)
        assert reply.addition_reply.counting_reply.answer == 12
    assert kernel.fingerprint() == before


def test_asymmetric_consumed_pair_is_corrected_only_by_the_supplied_order_rule():
    taught = _private()
    forward = _reply(taught, 13, 1, "forward")
    reverse = _reply(taught, 1, 13, "reverse")
    assert forward.route_disposition == "kept_valid_original_right" and forward.answer == 14
    assert reverse.route_disposition == "swapped_missing_original_right" and reverse.answer == 14
    assert reverse.original_request == _request(1, 13)
    assert reverse.effective_request == _request(13, 1)
    no_instruction = _private("no_instruction_control")
    original = _reply(no_instruction, 1, 13, "no-rule")
    assert original.route_disposition == "no_instruction_original_order"
    assert original.effective_request == original.original_request
    assert original.answer is None and original.addition_reply.reason == "missing_operand_tokens"


def test_both_missing_mappings_retain_both_lookups_and_never_dispatch():
    kernel = _private()
    reply = _reply(kernel, 6, 6, "both-missing")
    assert reply.route_disposition == "blocked_original_left_mapping"
    assert reply.original_right_lookup.status == "missing"
    assert reply.original_left_lookup.status == "missing"
    assert reply.effective_request is None and reply.addition_reply is None and reply.answer is None
    m.verify_order_derivation(kernel, reply.original_request, reply)


def test_terminal_failure_retains_complete_old_partial_counting_reply():
    kernel = _private()
    reply = _reply(kernel, 16, 3, "terminal")
    assert reply.route_disposition == "kept_valid_original_right"
    assert reply.answer is None and reply.addition_reply.reason == "counting_abstained"
    counted = reply.addition_reply.counting_reply
    assert [(s.from_number, s.to_number) for s in counted.steps] == [(16, 17), (17, 18)]
    assert counted.reason == "missing_successor"
    m.verify_order_derivation(kernel, reply.original_request, reply)


def test_no_instruction_retains_all_addition_lessons_and_delegates_original_order():
    source = ordering.fresh_order_kernel()
    kernel, lessons = m.prepare_private_operand_order_kernel("no_instruction_control", source)
    assert len(lessons) == 26 and all(lesson.object_label is not None for lesson in lessons[:25])
    assert lessons[-1].object_label is None and not lessons[-1].claim_refs
    assert m._instruction_trace(kernel).status == "missing"
    supported = _reply(kernel, 9, 3, "no-rule-supported")
    absent = _reply(kernel, 3, 9, "no-rule-absent")
    assert supported.answer == 12 and supported.effective_request == supported.original_request
    assert absent.answer is None and absent.effective_request == absent.original_request
    assert absent.original_right_lookup.status == "missing"
    assert absent.addition_reply.reason == "missing_operand_tokens"


def test_incorrect_instruction_uses_the_frozen_opposite_trigger_without_left_precheck():
    kernel = _private("incorrect_instruction_control")
    found = _reply(kernel, 9, 3, "wrong-found")
    missing = _reply(kernel, 3, 9, "wrong-missing")
    assert found.route_disposition == "incorrect_swapped_valid_original_right"
    assert found.effective_request == _request(3, 9) and found.original_left_lookup is None
    assert found.answer is None and found.addition_reply.reason == "missing_operand_tokens"
    assert missing.route_disposition == "incorrect_kept_missing_original_right"
    assert missing.effective_request == missing.original_request and missing.original_left_lookup is None
    assert missing.answer is None and missing.addition_reply.reason == "missing_operand_tokens"


def test_taught_and_valid_null_private_installations_are_exact_and_source_is_unchanged():
    source = ordering.fresh_order_kernel()
    before = source.snapshot()
    taught, taught_lessons = m.prepare_private_operand_order_kernel("taught", source)
    null, null_lessons = m.prepare_private_operand_order_kernel("valid_null", source)
    assert source.snapshot() == before
    assert taught is not null and taught.fingerprint() == null.fingerprint()
    assert taught_lessons == null_lessons and len(taught_lessons) == 26
    for private in (taught, null):
        assert not private.state.council_decisions and not private.state.governance_outcomes
        assert not private.state.obligation_attention_decisions and not private.state.obligation_kernels
        assert not private.state.revisions


@pytest.mark.parametrize("role", m._ROLES)
def test_all_roles_share_the_exact_first_25_native_lesson_traces(role):
    _, reference = m.prepare_private_operand_order_kernel("taught")
    _, lessons = m.prepare_private_operand_order_kernel(role)
    assert lessons[:25] == reference[:25]
    assert lessons[-1].subject_label == m._PROCEDURE
    assert lessons[-1].predicate == m._PREDICATE


@pytest.mark.parametrize("role", ("foreign", "", None, 1))
def test_unknown_role_fails_before_teaching(role):
    source = ordering.fresh_order_kernel()
    before = source.snapshot()
    with pytest.raises(ValueError, match="role"):
        m.prepare_private_operand_order_kernel(role, source)
    assert source.snapshot() == before


@pytest.mark.parametrize("kind", ("foreign", "drifted", "historical"))
def test_private_installer_rejects_any_noncanonical_source(kind):
    if kind == "foreign":
        source = VerdantKernel(seed=79061, state_dim=16, run_label="foreign")
    elif kind == "drifted":
        source = ordering.fresh_order_kernel(); source.state.cycle = 1
    else:
        source = _private()
    before = source.snapshot()
    with pytest.raises(ValueError, match="fresh"):
        m.prepare_private_operand_order_kernel("taught", source)
    assert source.snapshot() == before


def test_instruction_and_mapping_refs_are_complete_native_claim_evidence_closures():
    kernel = _private()
    reply = _reply(kernel, 3, 9, "provenance")
    instruction = kernel.state.claims[reply.order_instruction.claim_refs[0]]
    assert instruction.predicate == m._PREDICATE
    assert kernel.state.concepts[instruction.subject_concept_id].label == m._PROCEDURE
    assert kernel.state.concepts[instruction.object_concept_id].label == m._CORRECT
    assert reply.order_instruction.evidence_refs == tuple(sorted(
        e.evidence_id for e in (*instruction.support_ledger, *instruction.refutation_ledger)))
    mapping = kernel.state.claims[reply.original_left_lookup.claim_refs[0]]
    assert mapping.predicate == "math_counting_tokens"
    assert kernel.state.concepts[mapping.subject_concept_id].label == "math:integer:3"
    assert reply.original_left_lookup.evidence_refs == tuple(sorted(
        e.evidence_id for e in (*mapping.support_ledger, *mapping.refutation_ledger)))
    assert reply.addition_reply.operand_claim_refs == reply.original_left_lookup.claim_refs


@pytest.mark.parametrize("negated", (False, True))
def test_conflicting_or_negated_order_instruction_blocks_and_retains_all_evidence(negated):
    kernel = _private()
    _claim(kernel, m._PROCEDURE, m._PREDICATE,
        m._CORRECT if negated else m._INCORRECT, "order-opposition",
        polarity=ClaimPolarity.NEGATED if negated else ClaimPolarity.AFFIRMED)
    before = kernel.fingerprint()
    reply = _reply(kernel, 9, 3, "order-conflict")
    assert reply.route_disposition == "blocked_order_instruction"
    assert reply.order_instruction.status == "conflicting"
    assert len(reply.order_instruction.claim_refs) == 2 and reply.order_instruction.evidence_refs
    assert reply.original_right_lookup.status == "valid"
    assert reply.effective_request is None and reply.addition_reply is None
    assert kernel.fingerprint() == before


@pytest.mark.parametrize("source_class", (
    ClaimSourceClass.PHYSICAL_OUTCOME, ClaimSourceClass.DIRECT_OBSERVATION,
    ClaimSourceClass.SYSTEM_INFERENCE, ClaimSourceClass.EXTERNAL_TESTIMONY,
))
def test_non_teacher_order_claim_is_invalid_and_cannot_route(source_class):
    kernel = _private("no_instruction_control")
    _claim(kernel, m._PROCEDURE, m._PREDICATE, m._CORRECT, "invalid-order-origin",
        source_class=source_class)
    reply = _reply(kernel, 3, 9, "invalid-order")
    assert reply.route_disposition == "blocked_order_instruction"
    assert reply.order_instruction.status == "invalid" and reply.order_instruction.evidence_refs
    assert reply.addition_reply is None


def test_unsupported_order_claim_is_visible_and_never_executed():
    kernel = _private("no_instruction_control")
    _claim(kernel, m._PROCEDURE, m._PREDICATE, "untrusted:sort_and_execute", "unsupported-order")
    reply = _reply(kernel, 3, 9, "unsupported-order")
    assert reply.route_disposition == "blocked_order_instruction"
    assert reply.order_instruction.status == "unsupported"
    assert reply.order_instruction.label == "untrusted:sort_and_execute"
    assert reply.order_instruction.claim_refs and reply.addition_reply is None


@pytest.mark.parametrize("mode", ("conflicting", "invalid", "unsupported"))
def test_nonmissing_original_right_evidence_blocks_swap_and_remains_visible(mode):
    kernel = _private()
    if mode == "conflicting":
        _claim(kernel, "math:integer:3", "math_counting_tokens", "math:tokens:tick", "right-conflict")
        request = (9, 3)
    elif mode == "invalid":
        _claim(kernel, "math:integer:9", "math_counting_tokens", "math:tokens:tick", "right-invalid",
            source_class=ClaimSourceClass.PHYSICAL_OUTCOME)
        request = (3, 9)
    else:
        _claim(kernel, "math:integer:9", "math_counting_tokens", "untrusted:tokens", "right-unsupported")
        request = (3, 9)
    reply = _reply(kernel, *request, suffix=f"right-{mode}")
    assert reply.route_disposition == "blocked_original_right_mapping"
    assert reply.original_right_lookup.status == mode
    assert reply.original_right_lookup.claim_refs and reply.original_right_lookup.evidence_refs
    assert reply.original_left_lookup is None and reply.addition_reply is None


@pytest.mark.parametrize("mode", ("missing", "conflicting", "invalid", "unsupported"))
def test_failed_original_left_authorization_retains_both_lookups_and_abstains(mode):
    kernel = _private()
    if mode == "missing":
        request = (9, 5)
    elif mode == "conflicting":
        _claim(kernel, "math:integer:3", "math_counting_tokens", "math:tokens:tick", "left-conflict")
        request = (3, 9)
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


@pytest.mark.parametrize("label,status", (
    ("math:tokens:", "invalid"),
    ("math:tokens:tick,wrong", "invalid"),
    ("math:tokens:tick,tick,tick,tick,tick", "invalid"),
    ("math:integer:9", "unsupported"),
    ("untrusted:code()", "unsupported"),
))
def test_invalid_or_unsupported_native_token_encoding_is_never_reconstructed(label, status):
    kernel = _private()
    _claim(kernel, "math:integer:9", "math_counting_tokens", label, f"tokens-{status}-{len(label)}")
    reply = _reply(kernel, 3, 9, f"tokens-{status}")
    assert reply.route_disposition == "blocked_original_right_mapping"
    assert reply.original_right_lookup.status == status
    assert reply.original_right_lookup.label == label
    assert reply.original_right_lookup.tokens is None and reply.addition_reply is None


def test_native_mapping_not_operand_value_determines_route_and_nested_answer():
    kernel = _private()
    _claim(kernel, "math:integer:9", "math_counting_tokens", "math:tokens:tick,tick", "nine-is-two-ticks")
    reply = _reply(kernel, 3, 9, "native-not-numeric")
    assert reply.route_disposition == "kept_valid_original_right"
    assert reply.original_right_lookup.tokens == ("tick", "tick")
    assert reply.effective_request == _request(3, 9)
    assert reply.answer == 5
    assert [(step.from_number, step.to_number) for step in reply.addition_reply.counting_reply.steps] == [(3, 4), (4, 5)]


def test_adapter_does_not_read_curriculum_cases_prospective_cases_or_evaluator(monkeypatch):
    class ForbiddenTable:
        def __iter__(self):
            raise AssertionError("Operand routing consulted a case or curriculum table")
        def __getitem__(self, key):
            raise AssertionError("Operand routing consulted a case or curriculum table")

    def forbidden(*args, **kwargs):
        raise AssertionError("Operand routing consulted an external arithmetic evaluator")

    kernel = _private()
    monkeypatch.setattr(addition, "_CASES", ForbiddenTable())
    monkeypatch.setattr(counting, "_CASES", ForbiddenTable())
    monkeypatch.setattr(addition, "_TOKEN_LESSONS", ForbiddenTable())
    monkeypatch.setattr(ordering, "_ROWS", ForbiddenTable())
    monkeypatch.setattr(addition, "_grade", forbidden)
    monkeypatch.setattr(baseline, "recall_addition_fact", forbidden)
    before = kernel.fingerprint()
    reply = _reply(kernel, 3, 9, "no-evaluator")
    assert reply.answer == 12 and reply.effective_request == _request(9, 3)
    assert kernel.fingerprint() == before


def test_adapter_invokes_unchanged_addition_at_most_once_and_never_recurses(monkeypatch):
    kernel = _private()
    original, calls = addition.derive_addition, []
    def collect(target, request):
        calls.append(request)
        return original(target, request)
    monkeypatch.setattr(addition, "derive_addition", collect)
    reply = _reply(kernel, 3, 9, "single-dispatch")
    assert reply.answer == 12 and calls == [_request(9, 3)]
    calls.clear()
    blocked = _reply(kernel, 6, 6, "zero-dispatch")
    assert blocked.answer is None and calls == []


@pytest.mark.parametrize("field", (
    "adapter_version", "protocol", "fingerprint", "original", "effective", "status", "answer",
    "route", "instruction_status", "instruction_label", "instruction_claim", "right_operand",
    "right_status", "right_tokens", "right_claim", "left_drop", "nested_answer", "nested_rule_ref",
    "nested_step", "extra",
))
def test_tampered_route_native_provenance_or_nested_derivation_fails_replay(field):
    kernel = _private()
    reply = _reply(kernel, 3, 9, "tamper")
    raw = reply.model_dump(mode="json")
    if field == "adapter_version": raw[field] = "retuned"
    elif field == "protocol": raw["protocol_declaration_sha256"] = "0" * 64
    elif field == "fingerprint": raw["private_kernel_fingerprint"] = "0" * 64
    elif field == "original": raw["original_request"] = {"left": 9, "right": 3}
    elif field == "effective": raw["effective_request"] = {"left": 3, "right": 9}
    elif field == "status": raw["status"] = "abstained"
    elif field == "answer": raw["answer"] = 11
    elif field == "route": raw["route_disposition"] = "kept_valid_original_right"
    elif field == "instruction_status": raw["order_instruction"]["status"] = "unsupported"
    elif field == "instruction_label": raw["order_instruction"]["label"] = m._INCORRECT
    elif field == "instruction_claim": raw["order_instruction"]["claim_refs"][0] = "claim_foreign"
    elif field == "right_operand": raw["original_right_lookup"]["operand"] = 8
    elif field == "right_status": raw["original_right_lookup"]["status"] = "valid"
    elif field == "right_tokens": raw["original_right_lookup"]["tokens"] = ["tick"]
    elif field == "right_claim": raw["original_right_lookup"]["claim_refs"] = ["claim_foreign"]
    elif field == "left_drop": raw["original_left_lookup"] = None
    elif field == "nested_answer": raw["addition_reply"]["answer"] = 11
    elif field == "nested_rule_ref": raw["addition_reply"]["addition_rule_claim_refs"][0] = "claim_foreign"
    elif field == "nested_step": raw["addition_reply"]["counting_reply"]["steps"][0]["to_number"] = 17
    else: raw["expected_answer"] = 12
    try:
        forged = m.OperandOrderReply.model_validate(raw)
    except ValueError:
        return
    with pytest.raises(ValueError):
        m.verify_order_derivation(kernel, reply.original_request, forged)


def test_trace_from_foreign_private_kernel_fails_before_replay():
    taught = _private()
    no_instruction = _private("no_instruction_control")
    reply = _reply(taught, 9, 3, "foreign-kernel")
    with pytest.raises(ValueError, match="another private kernel"):
        m.verify_order_derivation(no_instruction, reply.original_request, reply)


def test_implementation_freeze_and_replay_do_not_install_query_grade_allocate_or_simulate(
    protocol, tmp_path, monkeypatch,
):
    from verdant_obligations import AttentionPortfolio, CounterfactualRuntime, SimulationLedger

    def forbidden(*args, **kwargs):
        raise AssertionError("Implementation freezing cannot teach, answer, grade, allocate or simulate")

    for module, names in ((m, ("prepare_private_operand_order_kernel", "derive_ordered_addition")),
                          (addition, ("_teach", "derive_addition", "_grade")),
                          (counting, ("_teach", "count_forward", "_grade"))):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(ClaimLearningPipeline, "record_claim", forbidden)
    monkeypatch.setattr(VerdantKernel, "apply_experience", forbidden)
    monkeypatch.setattr(CounterfactualRuntime, "execute", forbidden)
    monkeypatch.setattr(SimulationLedger, "reserve", forbidden)
    for name in ("allocate", "decide"):
        if hasattr(AttentionPortfolio, name):
            monkeypatch.setattr(AttentionPortfolio, name, forbidden)
    frozen = m.freeze_operand_order_adapter(PROTOCOL_PATH)
    path = tmp_path / "implementation.vaoi"
    first = m.save_operand_order_adapter(PROTOCOL_PATH, path, frozen)
    assert m.save_operand_order_adapter(PROTOCOL_PATH, path, frozen) == first
    assert m.load_operand_order_adapter(PROTOCOL_PATH, path) == frozen
    assert frozen.receipt.frozen_protocol == protocol
    summary = m.adapter_summary(frozen)
    assert summary["adapter_implemented"] and summary["native_trace_verifier_implemented"]
    assert not summary["prospective_cohort_executed"] and not summary["prospective_responses_observed"]


def test_implementation_pairs_exact_v060_bytes_and_extends_manifest_without_old_drift(implementation):
    assert PROTOCOL_PATH.stat().st_size == 30761
    assert baseline._sha(PROTOCOL_PATH.read_bytes()) == m._PROTOCOL_FILE_SHA256
    receipt = implementation.receipt
    assert receipt.frozen_protocol.declaration_sha256 == m._PROTOCOL_DECLARATION_SHA256
    assert len(receipt.frozen_protocol.declaration.code_sources) == 34
    assert len(receipt.code_sources) == 37
    old = receipt.frozen_protocol.declaration.code_sources
    assert receipt.code_sources[:len(old)] != old  # canonical path sorting interleaves the sibling
    old_by_path = {source.path: source for source in old}
    for source in receipt.code_sources:
        assert source.sha256 == baseline._sha((m._ROOT / source.path).read_bytes())
        if source.path in old_by_path:
            assert source == old_by_path[source.path]
    assert {s.path for s in receipt.code_sources} - set(old_by_path) == {
        "verdant_math/ordering_adapter/__init__.py",
        "verdant_math/ordering_adapter/adapter.py",
        "verdant_math/ordering_adapter/cli.py",
    }


def test_published_implementation_sidecar_is_exact_and_replayable(implementation):
    assert IMPLEMENTATION_PATH.stat().st_size == 37694
    assert baseline._sha(IMPLEMENTATION_PATH.read_bytes()) == (
        "05e8878f7a87c8be748e00c25608688f7ec87ab9345cc17e5caf24666699e64f"
    )
    assert implementation.receipt_sha256 == (
        "96820d6281822859ece17fc29e335ec1f543d6702f5a6ff80bc49b7d925c305a"
    )
    assert m.load_operand_order_adapter(PROTOCOL_PATH, IMPLEMENTATION_PATH) == implementation


@pytest.mark.parametrize("attack", (
    "implementation_version", "protocol_hash", "protocol_file_hash", "protocol_case", "manifest_hash",
    "manifest_drop", "purpose", "adapter_false", "installer_false", "verifier_false", "responses",
    "cohort", "evaluation", "source_auth", "physical", "harm", "discovery", "generalized",
    "efficiency", "replication", "canonical", "resolution", "promotion", "rewrite", "extra",
))
def test_fully_rehashed_implementation_protocol_code_or_authority_substitution_fails(
    implementation, tmp_path, attack,
):
    raw = implementation.model_dump(mode="json")
    receipt = raw["receipt"]
    if attack == "implementation_version": receipt["implementation"]["version"] = "retuned"
    elif attack == "protocol_hash": receipt["frozen_protocol"]["declaration_sha256"] = "0" * 64
    elif attack == "protocol_file_hash": receipt["protocol_file_sha256"] = "0" * 64
    elif attack == "protocol_case": receipt["frozen_protocol"]["declaration"]["cases"][0]["case_id"] = "changed"
    elif attack == "manifest_hash": receipt["code_sources"][-1]["sha256"] = "0" * 64
    elif attack == "manifest_drop": receipt["code_sources"].pop()
    elif attack == "purpose": receipt["purpose"] = "prospective_evaluation"
    elif attack == "adapter_false": receipt["adapter_implemented"] = False
    elif attack == "installer_false": receipt["private_instruction_installer_implemented"] = False
    elif attack == "verifier_false": receipt["native_trace_verifier_implemented"] = False
    elif attack == "extra": receipt["responses"] = [12]
    else:
        key = {
            "responses": "prospective_responses_observed", "cohort": "prospective_cohort_executed",
            "evaluation": "evaluation_completed", "source_auth": "source_authenticated",
            "physical": "physical_evidence_admissible", "harm": "harm_scoring_implemented",
            "discovery": "instruction_discovery_observed", "generalized": "generalized_arithmetic_claim_permitted",
            "efficiency": "learning_efficiency_observed", "replication": "independent_replication_observed",
            "canonical": "canonical_commit_permitted", "resolution": "resolution_authority_enabled",
            "promotion": "promotion_authority_enabled", "rewrite": "policy_rewrite_authority_enabled",
        }[attack]
        receipt[key] = True
    path = tmp_path / "forged.vaoi"
    path.write_bytes(_rehash(raw))
    with pytest.raises((ValueError, RuntimeError)):
        m.load_operand_order_adapter(PROTOCOL_PATH, path)


@pytest.mark.parametrize("kind", ("duplicate_key", "noncanonical", "oversized", "missing", "bad_hash"))
def test_corrupt_noncanonical_oversized_or_missing_implementation_fails(implementation, tmp_path, kind):
    path = tmp_path / "bad.vaoi"
    if kind == "duplicate_key": path.write_text('{"receipt":{},"receipt":{}}')
    elif kind == "noncanonical": path.write_text(json.dumps(implementation.model_dump(mode="json"), indent=2))
    elif kind == "oversized": path.write_bytes(b" " * (m._MAX_BYTES + 1))
    elif kind == "bad_hash":
        raw = implementation.model_dump(mode="json"); raw["receipt_sha256"] = "0" * 64
        path.write_bytes(canonical_json_bytes(raw))
    with pytest.raises((ValueError, OSError, RuntimeError)):
        m.load_operand_order_adapter(PROTOCOL_PATH, path)


def test_protocol_or_implementation_drift_during_freeze_fails_without_output(monkeypatch, tmp_path):
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
        m.freeze_operand_order_adapter(PROTOCOL_PATH)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("target_kind", ("protocol", "code", "history"))
def test_implementation_writer_cannot_replace_frozen_inputs(implementation, target_kind):
    target = {
        "protocol": PROTOCOL_PATH,
        "code": m._ROOT / "verdant_math/ordering_adapter/adapter.py",
        "history": m._ROOT / ordering._HISTORY[0][0],
    }[target_kind]
    before = target.read_bytes()
    with pytest.raises(ValueError, match="Cannot publish"):
        m.save_operand_order_adapter(PROTOCOL_PATH, target, implementation)
    assert target.read_bytes() == before


def test_immutable_path_and_failed_replace_preserve_existing_bytes(implementation, tmp_path, monkeypatch):
    occupied = tmp_path / "occupied.vaoi"
    occupied.write_bytes(b"prior implementation")
    with pytest.raises(RuntimeError, match="different evidence"):
        m.save_operand_order_adapter(PROTOCOL_PATH, occupied, implementation)
    assert occupied.read_bytes() == b"prior implementation"
    target = tmp_path / "failure.vaoi"
    monkeypatch.setattr(os, "replace", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("injected replace")))
    with pytest.raises(OSError, match="injected replace"):
        m.save_operand_order_adapter(PROTOCOL_PATH, target, implementation)
    assert not target.exists() and not tuple(tmp_path.glob(".*.tmp"))


def test_cli_exposes_freeze_and_replay_only_without_run_or_query(tmp_path, capsys):
    path = tmp_path / "adapter.vaoi"
    assert cli(["freeze", str(PROTOCOL_PATH), str(path)]) == 0
    frozen = json.loads(capsys.readouterr().out)
    assert frozen["adapter_implemented"] and not frozen["prospective_cohort_executed"]
    assert cli(["replay", str(PROTOCOL_PATH), str(path)]) == 0
    assert not json.loads(capsys.readouterr().out)["evaluation_completed"]
    for command in ("run", "query", "evaluate"):
        with pytest.raises(SystemExit):
            cli([command, str(PROTOCOL_PATH), str(path)])


def test_old_artifacts_and_v060_protocol_stay_byte_exact_during_adapter_operations():
    paths = [m._ROOT / path for path, _ in ordering._HISTORY] + [PROTOCOL_PATH]
    before = tuple(path.read_bytes() for path in paths)
    source = ordering.fresh_order_kernel()
    taught, _ = m.prepare_private_operand_order_kernel("taught", source)
    for index, pair in enumerate(CONSUMED):
        reply = m.derive_ordered_addition(taught, _request(*pair),
            local_run_ref="consumed-compatibility", case_ref=f"consumed-{index}")
        m.verify_order_derivation(taught, reply.original_request, reply)
    assert tuple(path.read_bytes() for path in paths) == before
    assert source.fingerprint() == ordering.fresh_order_kernel().fingerprint()


def test_adapter_import_and_frozen_receipt_contain_no_prospective_responses(protocol, implementation):
    # The complete unanswered protocol is embedded as typed design input, but
    # there is no reply, answer or grade record and extra fields are forbidden.
    assert implementation.receipt.frozen_protocol.declaration.cases == protocol.declaration.cases
    assert len(implementation.receipt.frozen_protocol.declaration.cases) == 40
    receipt = implementation.receipt.model_dump(mode="json")
    assert "responses" not in receipt and "grades" not in receipt and "arms" not in receipt
    assert not receipt["prospective_cohort_executed"]
    assert not receipt["prospective_responses_observed"]
    assert not receipt["evaluation_completed"]
