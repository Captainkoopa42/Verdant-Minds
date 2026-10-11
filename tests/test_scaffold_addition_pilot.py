from __future__ import annotations

import json
from pathlib import Path

import pytest

from verdant_claims import ClaimLearningPipeline
from verdant_kernel import ClaimPolarity, ClaimSourceClass, VerdantKernel, load_checkpoint, save_checkpoint
from verdant_kernel.models import canonical_json_bytes
from verdant_math import teaching_pilot as baseline
from verdant_math.counting import pilot as counting
from verdant_math.addition import pilot as m
from verdant_math.addition.cli import main as cli


@pytest.fixture(scope="module")
def pilot():
    return m.run_addition_pilot()


@pytest.fixture(scope="module")
def saved(pilot, tmp_path_factory):
    path = tmp_path_factory.mktemp("addition") / "pilot.vadd"
    m.save_addition_pilot(path, pilot)
    return path


def _private(pilot, index=0):
    arm = pilot.receipt.arms[index]
    return baseline._checkpoint(arm.checkpoint_base64, arm.checkpoint_sha256)


def _request(left=9, right=3):
    return m.AdditionRequest(left=left, right=right)


def _claim(kernel, subject, predicate, target, key, *, polarity=ClaimPolarity.AFFIRMED,
           source_class=ClaimSourceClass.HUMAN_TESTIMONY):
    return ClaimLearningPipeline().record_claim(kernel, event_key=key,
        native_description=f"Declared addition test lesson: {subject} {predicate} {target}.",
        subject_label=subject, predicate=predicate, object_label=target,
        polarity=polarity, source_class=source_class, source_ref="declared-addition-test").kernel_result


def _partial(edges=(), *, addition_rule=m._LEFT, counting_rule=counting._ONCE,
             token="math:tokens:tick,tick,tick", token_number=3):
    kernel = m.fresh_addition_kernel()
    if addition_rule is not None:
        _claim(kernel, m._PROCEDURE, "math_uses_addition_rule", addition_rule, "addition-rule")
    if counting_rule is not None:
        _claim(kernel, counting._PROCEDURE, "math_uses_counting_rule", counting_rule, "counting-rule")
    if token is not None:
        _claim(kernel, f"math:integer:{token_number}", "math_counting_tokens", token, "tokens")
    for index, (a, b) in enumerate(edges):
        _claim(kernel, f"math:integer:{a}", "math_successor", f"math:integer:{b}", f"edge:{index}")
    return kernel


def _rehash(raw):
    raw["receipt_sha256"] = baseline._sha(canonical_json_bytes(raw["receipt"]))
    return canonical_json_bytes(raw)


def test_all_64_cases_and_controls_are_frozen_disjoint_and_retained(pilot):
    summary = m.addition_summary(pilot)["arms"]
    for split, n in (("zero_identity", 4), ("short_composition", 4), ("held_out_composition", 8)):
        for role in ("taught", "valid_null"):
            assert summary[role][split] == dict(correct=n, incorrect=0, abstained=0)
        assert summary["no_rule_control"][split] == dict(correct=0, incorrect=0, abstained=n)
        assert summary["incorrect_rule_control"][split] == dict(correct=0, incorrect=n, abstained=0)
    assert len(set(m._CASES)) == 16
    assert set(m._CASES).isdisjoint((*baseline._TRAINING, *baseline._HELD_OUT, *counting._CASES))
    assert sum(len(a.observations) for a in pilot.receipt.arms) == 64
    assert pilot.receipt.arms[0].model_dump(exclude={"role"}) == pilot.receipt.arms[2].model_dump(exclude={"role"})
    for arm in pilot.receipt.arms:
        assert len(arm.lessons) == 25
        assert arm.lessons[:24] == pilot.receipt.arms[0].lessons[:24]


def test_binding_token_mapping_and_every_step_have_actual_native_provenance(pilot):
    kernel = _private(pilot)
    for o in pilot.receipt.arms[0].observations:
        reply = o.reply
        assert reply.start_operand == "left_operand" and reply.ticks_operand == "right_operand"
        rule = kernel.state.claims[reply.addition_rule_claim_refs[0]]
        assert rule.predicate == "math_uses_addition_rule"
        assert kernel.state.concepts[rule.object_concept_id].label == m._LEFT
        tokens = kernel.state.claims[reply.operand_claim_refs[0]]
        assert tokens.predicate == "math_counting_tokens"
        assert kernel.state.concepts[tokens.subject_concept_id].label == f"math:integer:{o.request.right}"
        assert reply.counting_request.start == o.request.left
        assert reply.counting_request.ticks == m._decode_tokens(kernel.state.concepts[tokens.object_concept_id].label)
        assert reply.operand_evidence_refs == tuple(sorted(e.evidence_id for e in tokens.support_ledger))
        assert len(reply.counting_reply.steps) == o.request.right
        current = o.request.left
        for step in reply.counting_reply.steps:
            edge = kernel.state.claims[step.claim_ref]
            assert edge.predicate == "math_successor" and step.from_number == current
            assert kernel.state.concepts[edge.subject_concept_id].label == f"math:integer:{current}"
            assert kernel.state.concepts[edge.object_concept_id].label == f"math:integer:{step.to_number}"
            assert step.evidence_refs == tuple(sorted(e.evidence_id for e in edge.support_ledger))
            current = step.to_number
        assert reply.answer == current
        m.verify_addition_derivation(kernel, o.request, reply)
    assert {c.predicate for c in kernel.state.claims.values()} == {
        "math_successor", "math_uses_counting_rule", "math_counting_tokens", "math_uses_addition_rule"}
    assert set(_request().model_dump()) == {"left", "right"}


def test_response_uses_existing_counting_and_never_reads_case_tables_or_evaluator(pilot, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Addition consulted an evaluator, curriculum or old answer lookup")

    class ForbiddenTable:
        __iter__ = forbidden
        __getitem__ = forbidden

    for module, names in ((m, ("_TOKEN_LESSONS", "_CASES")),
                          (counting, ("_SUCCESSORS", "_CASES")),
                          (baseline, ("_TEACHER_ANSWERS",))):
        for name in names:
            monkeypatch.setattr(module, name, ForbiddenTable())
        monkeypatch.setattr(module, "_grade", forbidden)
    monkeypatch.setattr(baseline, "recall_addition_fact", forbidden)
    original, calls = counting.count_forward, []

    def collect(kernel, request):
        calls.append(request)
        return original(kernel, request)

    monkeypatch.setattr(counting, "count_forward", collect)
    kernel = _private(pilot)
    before = kernel.fingerprint()
    reply = m.derive_addition(kernel, _request())
    assert reply.answer == 12
    assert calls == [counting.CountingRequest(start=9, ticks=("tick",) * 3)]
    assert kernel.fingerprint() == before


def test_wrong_token_mapping_changes_output_instead_of_being_replaced_by_right_operand():
    kernel = _partial(((9, 10), (10, 11)), token="math:tokens:tick,tick")
    reply = m.derive_addition(kernel, _request())
    assert reply.answer == 11 and len(reply.counting_request.ticks) == 2
    assert m._grade(8, _request(), reply).grade == "incorrect"


def test_wrong_successor_changes_answer_without_arithmetic_repair():
    kernel = _partial(((9, 10), (10, 11), (11, 13)))
    reply = m.derive_addition(kernel, _request())
    assert reply.answer == 13 and reply.counting_reply.steps[-1].to_number == 13
    assert m._grade(8, _request(), reply).grade == "incorrect"


@pytest.mark.parametrize("edges,reason,steps", (
    (((9, 10), (10, 11)), "missing_successor", 2),
    (((9, 10), (10, 9)), "cyclic_successor", 1),
    (((9, 19),), "invalid_successor", 0),
))
def test_broken_counting_paths_retain_partial_evidence_and_abstain(edges, reason, steps):
    kernel = _partial(edges)
    before = kernel.fingerprint()
    reply = m.derive_addition(kernel, _request())
    assert reply.reason == "counting_abstained" and reply.answer is None
    assert reply.counting_reply.reason == reason and len(reply.counting_reply.steps) == steps
    assert reply.addition_rule_claim_refs and reply.operand_claim_refs
    if reason != "missing_successor":
        assert reply.counting_reply.blocked_claim_refs and reply.counting_reply.blocked_evidence_refs
    assert m._grade(8, _request(), reply).grade == "abstained"
    assert kernel.fingerprint() == before


@pytest.mark.parametrize("scope", ("addition_rule", "operand", "counting_rule", "successor"))
@pytest.mark.parametrize("negate", (False, True))
def test_conflicting_or_negated_bindings_and_dependencies_are_not_suppressed(pilot, scope, negate):
    kernel = _private(pilot)
    subject, predicate, original, changed = {
        "addition_rule": (m._PROCEDURE, "math_uses_addition_rule", m._LEFT, m._RIGHT),
        "operand": ("math:integer:3", "math_counting_tokens", "math:tokens:tick,tick,tick", "math:tokens:tick"),
        "counting_rule": (counting._PROCEDURE, "math_uses_counting_rule", counting._ONCE, counting._TWICE),
        "successor": ("math:integer:11", "math_successor", "math:integer:12", "math:integer:13"),
    }[scope]
    _claim(kernel, subject, predicate, original if negate else changed, "opposition",
           polarity=ClaimPolarity.NEGATED if negate else ClaimPolarity.AFFIRMED)
    before = kernel.fingerprint()
    reply = m.derive_addition(kernel, _request())
    assert reply.answer is None
    refs = (reply.addition_rule_claim_refs if scope == "addition_rule" else
            reply.operand_claim_refs if scope == "operand" else
            reply.counting_reply.rule_claim_refs if scope == "counting_rule" else
            reply.counting_reply.blocked_claim_refs)
    assert len(refs) == 2 and all(r in kernel.state.claims for r in refs)
    assert kernel.fingerprint() == before


@pytest.mark.parametrize("scope", ("addition_rule", "operand"))
@pytest.mark.parametrize("source_class", (
    ClaimSourceClass.PHYSICAL_OUTCOME, ClaimSourceClass.DIRECT_OBSERVATION, ClaimSourceClass.SYSTEM_INFERENCE,
))
def test_false_physical_or_system_origin_is_not_teacher_binding_evidence(scope, source_class):
    if scope == "addition_rule":
        kernel = _partial(addition_rule=None)
        _claim(kernel, m._PROCEDURE, "math_uses_addition_rule", m._LEFT, "origin", source_class=source_class)
        expected = "invalid_addition_rule"
    else:
        kernel = _partial(token=None)
        _claim(kernel, "math:integer:3", "math_counting_tokens", "math:tokens:tick,tick,tick", "origin",
               source_class=source_class)
        expected = "invalid_operand_tokens"
    reply = m.derive_addition(kernel, _request())
    assert reply.reason == expected and reply.answer is None
    assert reply.addition_rule_evidence_refs


@pytest.mark.parametrize("label", (
    "math:tokens:", "math:tokens:tick,wrong", "math:tokens:tick,tick,tick,tick,tick",
    "math:tokens:empty,tick", "math:integer:3", "untrusted:code()",
))
def test_invalid_oversized_or_executable_token_labels_abstain_without_execution(label):
    kernel = _partial(token=label)
    reply = m.derive_addition(kernel, _request())
    assert reply.reason == "invalid_operand_tokens" and reply.answer is None
    assert reply.operand_claim_refs and reply.operand_evidence_refs
    assert reply.counting_request is None


def test_zero_identity_still_needs_mapping_addition_instruction_and_counting_instruction():
    kernel = _partial(token_number=0, token="math:tokens:empty")
    reply = m.derive_addition(kernel, _request(9, 0))
    assert reply.answer == 9 and not reply.counting_reply.steps
    assert m.derive_addition(_partial(token=None), _request(9, 0)).reason == "missing_operand_tokens"
    assert m.derive_addition(_partial(addition_rule=None), _request(9, 0)).reason == "missing_addition_rule"
    missing = _partial(token_number=0, token="math:tokens:empty", counting_rule=None)
    assert m.derive_addition(missing, _request(9, 0)).counting_reply.reason == "missing_rule"


def test_untaught_right_operand_reversed_pair_and_terminal_overflow_abstain(pilot):
    kernel = _private(pilot)
    for request in (_request(9, 5), _request(3, 9)):
        assert m.derive_addition(kernel, request).reason == "missing_operand_tokens"
    terminal = m.derive_addition(kernel, _request(18, 1))
    assert terminal.reason == "counting_abstained" and terminal.counting_reply.reason == "missing_successor"


def test_unknown_addition_instruction_is_not_executed():
    reply = m.derive_addition(_partial(addition_rule="untrusted:execute_arbitrary_code"), _request())
    assert reply.reason == "unsupported_addition_rule" and reply.answer is None
    assert reply.addition_rule_claim_refs and reply.counting_request is None


@pytest.mark.parametrize("left,right", (
    (True, 3), (9, False), (9.0, 3), (9, 3.0), ("9", 3), (9, "3"), (-1, 3), (9, -1), (19, 3), (9, 19),
))
def test_strict_operand_types_and_bounds(left, right):
    with pytest.raises(ValueError):
        m.AdditionRequest(left=left, right=right)


def test_all_64_responses_precede_any_external_arithmetic_grading(monkeypatch):
    count, original_response, original_grade = 0, m.derive_addition, m._grade

    def collect(*args):
        nonlocal count
        count += 1
        return original_response(*args)

    def grade(*args):
        assert count == 64
        return original_grade(*args)

    monkeypatch.setattr(m, "derive_addition", collect)
    monkeypatch.setattr(m, "_grade", grade)
    m.run_addition_pilot()
    assert count == 64


def test_canonical_source_simulation_ledgers_attention_and_governance_are_isolated(pilot, monkeypatch):
    from verdant_obligations import CounterfactualRuntime, SimulationLedger

    def forbidden(*args, **kwargs):
        raise AssertionError("Addition may not create simulation funding or physical harm outcomes")

    monkeypatch.setattr(CounterfactualRuntime, "execute", forbidden)
    monkeypatch.setattr(SimulationLedger, "reserve", forbidden)
    monkeypatch.setattr(VerdantKernel, "record_governance_outcome", forbidden)
    source = m.fresh_addition_kernel()
    before = source.snapshot()
    assert m.run_addition_pilot(source) == pilot
    assert source.snapshot() == before
    for index in range(4):
        private = _private(pilot, index)
        assert private.state.cycle == 25 and len(private.state.claims) == (24 if index == 1 else 25)
        assert not private.state.obligation_kernels and not private.state.obligation_attention_decisions
        assert not private.state.governance_outcomes and not private.state.council_decisions
        assert not private.state.revisions


def test_native_checkpoint_mapping_order_and_private_copy_replay(pilot, saved, tmp_path):
    assert m.load_addition_pilot(saved) == pilot
    kernel = _private(pilot)
    path = tmp_path / "addition.vdk"
    save_checkpoint(path, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))
    for name in ("claims", "concepts", "evidence"):
        setattr(restored.state, name, dict(reversed(tuple(getattr(restored.state, name).items()))))
    assert restored.fingerprint() == kernel.fingerprint()
    for o in pilot.receipt.arms[0].observations:
        assert m.derive_addition(restored, o.request) == o.reply
    copy = m.restore_addition_arm(pilot)
    _claim(copy, "math:integer:3", "math_counting_tokens", "math:tokens:tick", "later-conflict")
    assert m.derive_addition(copy, _request()).answer is None
    assert m.derive_addition(kernel, _request()).answer == 12


@pytest.mark.parametrize("kind", ("foreign", "already_taught"))
def test_nonfresh_sources_are_rejected_without_mutation(pilot, kind):
    kernel = VerdantKernel(seed=12, state_dim=16) if kind == "foreign" else _private(pilot)
    before = kernel.snapshot()
    with pytest.raises(ValueError, match="fresh"):
        m.run_addition_pilot(kernel)
    assert kernel.snapshot() == before


@pytest.mark.parametrize("drift", ("source", "code"))
def test_source_or_implementation_drift_rejects_completion(monkeypatch, drift):
    source, original_teach, original_manifest = m.fresh_addition_kernel(), m._teach, m._code_manifest
    before = source.snapshot()
    if drift == "source":
        def mutate(private, role):
            result = original_teach(private, role)
            if role == "taught":
                _claim(source, "untrusted:source", "altered", "untrusted:state", "source-drift")
            return result

        monkeypatch.setattr(m, "_teach", mutate)
    else:
        calls = 0

        def changed():
            nonlocal calls
            calls += 1
            manifest = original_manifest()
            return manifest if calls == 1 else manifest[:-1]

        monkeypatch.setattr(m, "_code_manifest", changed)
    with pytest.raises(ValueError, match="source or implementation changed"):
        m.run_addition_pilot(source)
    if drift == "code":
        assert source.snapshot() == before


@pytest.mark.parametrize("attack", (
    "answer", "grade", "expected", "case", "split", "left", "right", "missing_case", "duplicate_case",
    "instruction", "start_operand", "ticks_operand", "addition_rule_claim", "addition_rule_evidence",
    "operand_claim", "operand_evidence", "count_start", "count_tokens", "count_answer", "count_rule",
    "step_from", "step_to", "step_claim", "step_evidence", "step_order", "step_tick", "step_application",
    "lesson_target", "lesson_transition", "lesson_text", "code_manifest", "source_checkpoint",
    "arm_checkpoint", "source_fingerprint", "retuned_scoring",
))
def test_fully_rehashed_operand_binding_derivation_case_and_scoring_attacks_fail(pilot, tmp_path, attack):
    raw = pilot.model_dump(mode="json")
    receipt, arm = raw["receipt"], raw["receipt"]["arms"][0]
    o = arm["observations"][8]
    reply, step = o["reply"], o["reply"]["counting_reply"]["steps"][0]
    if attack == "answer": reply["answer"] = 13
    elif attack == "grade": o["grade"] = "incorrect"
    elif attack == "expected": o["expected_answer"] = 13
    elif attack == "case": o["case_id"] = "substituted-case"
    elif attack == "split": o["split"] = "short_composition"
    elif attack == "left": o["request"]["left"] = 10
    elif attack == "right": o["request"]["right"] = 4
    elif attack == "missing_case": arm["observations"].pop()
    elif attack == "duplicate_case": arm["observations"][9] = o
    elif attack == "instruction": reply["instruction"] = "count_from_right_by_right"
    elif attack == "start_operand": reply["start_operand"] = "right_operand"
    elif attack == "ticks_operand": reply["ticks_operand"] = "left_operand"
    elif attack == "addition_rule_claim": reply["addition_rule_claim_refs"] = ["substituted-rule"]
    elif attack == "addition_rule_evidence": reply["addition_rule_evidence_refs"] = ["substituted-evidence"]
    elif attack == "operand_claim": reply["operand_claim_refs"] = ["substituted-mapping"]
    elif attack == "operand_evidence": reply["operand_evidence_refs"] = ["substituted-evidence"]
    elif attack == "count_start": reply["counting_request"]["start"] = 10
    elif attack == "count_tokens": reply["counting_request"]["ticks"] = ["tick"] * 2
    elif attack == "count_answer": reply["counting_reply"]["answer"] = 13
    elif attack == "count_rule": reply["counting_reply"]["rule_claim_refs"] = ["substituted-rule"]
    elif attack == "step_from": step["from_number"] = 10
    elif attack == "step_to": step["to_number"] = 11
    elif attack == "step_claim": step["claim_ref"] = "substituted-edge"
    elif attack == "step_evidence": step["evidence_refs"] = ["substituted-evidence"]
    elif attack == "step_order": reply["counting_reply"]["steps"].reverse()
    elif attack == "step_tick": step["tick_index"] = 1
    elif attack == "step_application": step["application_index"] = 1
    elif attack == "lesson_target": arm["lessons"][19]["object_label"] = "math:tokens:tick"
    elif attack == "lesson_transition": arm["lessons"][19]["transition_ref"] = "substituted-transition"
    elif attack == "lesson_text": arm["lessons"][19]["native_description"] = "False teacher description."
    elif attack == "code_manifest": receipt["code_sources"][0]["sha256"] = "0" * 64
    elif attack == "source_checkpoint":
        for dst, src in (("source_checkpoint_base64", "checkpoint_base64"),
                         ("source_checkpoint_sha256", "checkpoint_sha256"),
                         ("source_kernel_fingerprint", "kernel_fingerprint")):
            receipt[dst] = arm[src]
    elif attack == "arm_checkpoint":
        for key in ("checkpoint_base64", "checkpoint_sha256", "kernel_fingerprint"):
            arm[key] = receipt["arms"][3][key]
    elif attack == "source_fingerprint": receipt["source_kernel_fingerprint"] = "0" * 64
    elif attack == "retuned_scoring": receipt["protocol"]["scoring"] = "credit_any_counted_result"
    path = tmp_path / "forged.vadd"
    path.write_bytes(_rehash(raw))
    with pytest.raises((ValueError, RuntimeError)):
        m.load_addition_pilot(path)


@pytest.mark.parametrize("flag", (
    "source_authenticated", "physical_evidence_admissible", "harm_scoring_implemented",
    "instruction_discovery_observed", "generalized_arithmetic_claim_permitted", "canonical_commit_permitted",
    "resolution_authority_enabled", "promotion_authority_enabled", "policy_rewrite_authority_enabled",
))
def test_rehashed_authority_discovery_or_physical_admission_escalation_rejected(pilot, tmp_path, flag):
    raw = pilot.model_dump(mode="json")
    raw["receipt"][flag] = True
    path = tmp_path / "authority.vadd"
    path.write_bytes(_rehash(raw))
    with pytest.raises(ValueError):
        m.load_addition_pilot(path)


def test_derivation_checker_rejects_forged_and_stale_bindings(pilot):
    kernel, request = _private(pilot), _request()
    reply = m.derive_addition(kernel, request)
    with pytest.raises(ValueError, match="derivation"):
        m.verify_addition_derivation(kernel, request, reply.model_copy(update={"start_operand": "right_operand"}))
    _claim(kernel, m._PROCEDURE, "math_uses_addition_rule", m._RIGHT, "later-instruction")
    with pytest.raises(ValueError, match="derivation"):
        m.verify_addition_derivation(kernel, request, reply)


def test_bad_hash_duplicate_json_and_oversized_sidecars_rejected(pilot, tmp_path):
    path = tmp_path / "bad.vadd"
    raw = pilot.model_dump(mode="json")
    raw["receipt_sha256"] = "0" * 64
    path.write_bytes(canonical_json_bytes(raw))
    with pytest.raises(ValueError, match="checksum"):
        m.load_addition_pilot(path)
    path.write_text('{"sidecar_format":"one","sidecar_format":"two"}')
    with pytest.raises(ValueError, match="Duplicate"):
        m.load_addition_pilot(path)
    path.write_bytes(b" " * (m._MAX_BYTES + 1))
    with pytest.raises(ValueError, match="size bound"):
        m.load_addition_pilot(path)


def test_immutable_publication_conflicts_and_failure_preserve_evidence(pilot, tmp_path, monkeypatch):
    path = tmp_path / "saved.vadd"
    first = m.save_addition_pilot(path, pilot)
    assert m.save_addition_pilot(path, pilot) == first
    path.write_bytes(b"occupied evidence")
    with pytest.raises(RuntimeError, match="different evidence"):
        m.save_addition_pilot(path, pilot)
    assert path.read_bytes() == b"occupied evidence"

    def fail(*args):
        raise OSError("publication failed")

    monkeypatch.setattr(baseline, "_write_immutable", fail)
    absent = tmp_path / "absent.vadd"
    with pytest.raises(OSError, match="publication failed"):
        m.save_addition_pilot(absent, pilot)
    assert not absent.exists()


@pytest.mark.parametrize("role,answer,start", (("taught", 12, 9), ("valid_null", 12, 9),
    ("incorrect_rule_control", 6, 3), ("no_rule_control", None, None)))
def test_cli_queries_emit_native_bindings_and_no_grading_labels(saved, capsys, role, answer, start):
    assert cli(["query", str(saved), "--left", "9", "--right", "3", "--role", role]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["reply"]["answer"] == answer
    if start is not None:
        assert result["reply"]["counting_request"]["start"] == start
    assert "expected_answer" not in result and "grade" not in result
    assert not result["instruction_discovery_observed"] and not result["physical_evidence_admissible"]


def test_cli_run_replay_and_invalid_or_occupied_paths(pilot, tmp_path, capsys):
    path = tmp_path / "cli.vadd"
    assert cli(["run", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == m.addition_summary(pilot)
    assert cli(["replay", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == m.addition_summary(pilot)
    path.write_text("invalid")
    assert cli(["run", str(path)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid"


def test_both_preceding_math_pilots_keep_original_manifests_and_exact_replay():
    root = Path(__file__).resolve().parent.parent
    old = baseline.load_math_teaching_pilot(root / "artifacts/arithmetic_teaching_v056/pilot.vmp")
    previous = counting.load_counting_pilot(root / "artifacts/counting_teaching_v057/pilot.vcount")
    assert old.receipt.code_sources == baseline._code_manifest()
    assert previous.receipt.code_sources == counting._code_manifest()
    assert old.receipt_sha256 == "c27e284f2dd85ba861a3076e63b8f663ba9fa102c72bd69eb86522aaabe257ea"
    assert previous.receipt_sha256 == "deacf11110f39b7d04b42d5ef201f0c4a0fd0c038c303234c59ee5cf36895611"


def test_recorded_addition_pilot_replays_native_operand_bindings_and_derivations():
    path = Path(__file__).resolve().parent.parent / "artifacts/scaffold_addition_v058/pilot.vadd"
    envelope = m.load_addition_pilot(path)
    assert m.addition_summary(envelope)["arms"]["taught"]["held_out_composition"]["correct"] == 8
