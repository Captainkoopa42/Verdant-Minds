from __future__ import annotations

import json
from pathlib import Path

import pytest

from verdant_claims import ClaimLearningPipeline
from verdant_kernel import ClaimPolarity, ClaimSourceClass, VerdantKernel, load_checkpoint, save_checkpoint
from verdant_kernel.models import canonical_json_bytes
from verdant_math import teaching_pilot as baseline
from verdant_math.counting import pilot as m
from verdant_math.counting.cli import main as cli


@pytest.fixture(scope="module")
def pilot():
    return m.run_counting_pilot()


@pytest.fixture(scope="module")
def saved(pilot, tmp_path_factory):
    path = tmp_path_factory.mktemp("counting") / "pilot.vcount"
    m.save_counting_pilot(path, pilot)
    return path


def _private(pilot, index=0):
    arm = pilot.receipt.arms[index]
    return baseline._checkpoint(arm.checkpoint_base64, arm.checkpoint_sha256)


def _request(start=5, count=3):
    return m.CountingRequest(start=start, ticks=("tick",) * count)


def _claim(kernel, subject, predicate, target, key, *, polarity=ClaimPolarity.AFFIRMED,
           source_class=ClaimSourceClass.HUMAN_TESTIMONY):
    return ClaimLearningPipeline().record_claim(kernel, event_key=key,
        native_description=f"Declared counting test lesson: {subject} {predicate} {target}.",
        subject_label=subject, predicate=predicate, object_label=target,
        polarity=polarity, source_class=source_class, source_ref="declared-counting-test").kernel_result


def _partial(edges, rule=m._ONCE):
    kernel = m.fresh_counting_kernel()
    if rule is not None:
        _claim(kernel, m._PROCEDURE, "math_uses_counting_rule", rule, "rule")
    for index, (a, b) in enumerate(edges):
        _claim(kernel, f"math:integer:{a}", "math_successor", f"math:integer:{b}", f"edge:{index}")
    return kernel


def _rehash(raw):
    raw["receipt_sha256"] = baseline._sha(canonical_json_bytes(raw["receipt"]))
    return canonical_json_bytes(raw)


def test_recorded_scaffold_composes_facts_and_controls_all_64_cases(pilot):
    summary = m.counting_summary(pilot)["arms"]
    for role in ("taught", "valid_null"):
        assert summary[role]["direct_successor"] == dict(correct=4, incorrect=0, abstained=0)
        assert summary[role]["short_composition"] == dict(correct=4, incorrect=0, abstained=0)
        assert summary[role]["held_out_composition"] == dict(correct=8, incorrect=0, abstained=0)
    for split, count in (("direct_successor", 4), ("short_composition", 4), ("held_out_composition", 8)):
        assert summary["no_rule_control"][split] == dict(correct=0, incorrect=0, abstained=count)
        assert summary["incorrect_rule_control"][split] == dict(correct=0, incorrect=count, abstained=0)
    assert sum(len(a.observations) for a in pilot.receipt.arms) == 64
    assert len(set(m._CASES)) == 16
    assert set(m._CASES).isdisjoint((*baseline._TRAINING, *baseline._HELD_OUT))
    assert pilot.receipt.arms[0].model_dump(exclude={"role"}) == pilot.receipt.arms[2].model_dump(exclude={"role"})
    for arm in pilot.receipt.arms:
        assert arm.lessons[:18] == pilot.receipt.arms[0].lessons[:18]
        assert len(arm.lessons) == 19


def test_each_derived_step_names_the_actual_native_edge_and_testimony(pilot):
    kernel = _private(pilot)
    for observation in pilot.receipt.arms[0].observations:
        reply = observation.reply
        assert len(reply.steps) == len(observation.request.ticks)
        prior = observation.request.start
        for index, step in enumerate(reply.steps):
            assert (step.tick_index, step.application_index, step.from_number) == (index, 0, prior)
            claim = kernel.state.claims[step.claim_ref]
            assert claim.predicate == "math_successor"
            assert kernel.state.concepts[claim.subject_concept_id].label == f"math:integer:{step.from_number}"
            assert kernel.state.concepts[claim.object_concept_id].label == f"math:integer:{step.to_number}"
            assert step.evidence_refs == tuple(sorted(e.evidence_id for e in claim.support_ledger))
            assert all(e.source_class == ClaimSourceClass.HUMAN_TESTIMONY for e in claim.support_ledger)
            prior = step.to_number
        assert reply.answer == prior
        m.verify_counting_derivation(kernel, observation.request, reply)
    assert {c.predicate for c in kernel.state.claims.values()} == {"math_successor", "math_uses_counting_rule"}
    assert set(pilot.receipt.arms[0].observations[8].request.model_dump()) == {"start", "ticks"}


def test_interpreter_does_not_read_curriculum_cases_or_arithmetic_oracles(pilot, monkeypatch):
    kernel = _private(pilot)
    before = kernel.fingerprint()

    def forbidden(*args, **kwargs):
        raise AssertionError("Counting read a curriculum table, case target or grading oracle")

    class ForbiddenTable:
        __iter__ = forbidden
        __getitem__ = forbidden

    monkeypatch.setattr(m, "_SUCCESSORS", ForbiddenTable())
    monkeypatch.setattr(m, "_CASES", ForbiddenTable())
    monkeypatch.setattr(m, "_grade", forbidden)
    monkeypatch.setattr(baseline, "_TEACHER_ANSWERS", ForbiddenTable())
    monkeypatch.setattr(baseline, "_grade", forbidden)
    monkeypatch.setattr(baseline, "recall_addition_fact", forbidden)
    assert m.count_forward(kernel, _request(5, 3)).answer == 8
    assert kernel.fingerprint() == before


def test_wrong_successor_fact_changes_output_instead_of_being_silently_repaired():
    kernel = _partial(((5, 6), (6, 7), (7, 9)))
    reply = m.count_forward(kernel, _request(5, 3))
    assert reply.answer == 9
    assert [(s.from_number, s.to_number) for s in reply.steps] == [(5, 6), (6, 7), (7, 9)]
    assert m._grade(8, _request(5, 3), reply).grade == "incorrect"


@pytest.mark.parametrize("target", ("math:integer:06", "math:integer:19", "arbitrary-target"))
def test_invalid_successor_object_abstains_with_original_evidence(target):
    kernel = _partial(())
    result = _claim(kernel, "math:integer:5", "math_successor", target, "invalid-object")
    before = kernel.fingerprint()
    reply = m.count_forward(kernel, _request(5, 1))
    assert reply.reason == "invalid_successor" and reply.answer is None
    assert reply.blocked_claim_refs == tuple(sorted(result.claim_ids))
    assert reply.blocked_evidence_refs and not reply.steps
    assert kernel.fingerprint() == before


def test_missing_successor_retains_partial_derivation_as_abstention():
    kernel = _partial(((5, 6), (6, 7)))
    before = kernel.fingerprint()
    reply = m.count_forward(kernel, _request(5, 3))
    assert reply.answer is None and reply.reason == "missing_successor"
    assert len(reply.steps) == 2 and reply.rule_claim_refs
    assert m._grade(8, _request(5, 3), reply).grade == "abstained"
    assert kernel.fingerprint() == before


@pytest.mark.parametrize("edges", (((5, 5),), ((5, 6), (6, 7), (7, 5))))
def test_cyclic_graph_abstains_with_blocking_evidence_and_no_partial_answer(edges):
    kernel = _partial(edges)
    before = kernel.snapshot()
    reply = m.count_forward(kernel, _request(5, 3))
    assert reply.reason == "cyclic_successor" and reply.answer is None
    assert reply.blocked_claim_refs and reply.blocked_evidence_refs
    assert len(reply.steps) == len(edges) - 1
    assert kernel.snapshot() == before


@pytest.mark.parametrize("scope", ("rule", "successor"))
def test_conflicting_rules_or_successors_preserve_all_relevant_claims(pilot, scope):
    kernel = _private(pilot)
    if scope == "rule":
        _claim(kernel, m._PROCEDURE, "math_uses_counting_rule", m._TWICE, "conflicting-rule")
    else:
        _claim(kernel, "math:integer:7", "math_successor", "math:integer:9", "conflicting-edge")
    before = kernel.fingerprint()
    reply = m.count_forward(kernel, _request(5, 3))
    assert reply.answer is None and reply.reason == "conflicting_" + scope
    refs = reply.rule_claim_refs if scope == "rule" else reply.blocked_claim_refs
    assert len(refs) == 2 and all(ref in kernel.state.claims for ref in refs)
    assert kernel.fingerprint() == before


@pytest.mark.parametrize("scope", ("rule", "successor"))
def test_negation_is_not_suppressed(pilot, scope):
    kernel = _private(pilot)
    subject, predicate, target = ((m._PROCEDURE, "math_uses_counting_rule", m._ONCE)
        if scope == "rule" else ("math:integer:7", "math_successor", "math:integer:8"))
    _claim(kernel, subject, predicate, target, "negation", polarity=ClaimPolarity.NEGATED)
    before = kernel.fingerprint()
    reply = m.count_forward(kernel, _request(5, 3))
    assert reply.answer is None and reply.reason == "conflicting_" + scope
    refs = reply.rule_claim_refs if scope == "rule" else reply.blocked_claim_refs
    assert len(refs) == 2
    assert kernel.fingerprint() == before


@pytest.mark.parametrize("source_class", (
    ClaimSourceClass.PHYSICAL_OUTCOME, ClaimSourceClass.DIRECT_OBSERVATION, ClaimSourceClass.SYSTEM_INFERENCE,
))
def test_false_physical_or_system_source_claim_is_not_counting_teacher_evidence(source_class):
    kernel = _partial(())
    _claim(kernel, "math:integer:5", "math_successor", "math:integer:6", "origin", source_class=source_class)
    reply = m.count_forward(kernel, _request(5, 1))
    assert reply.reason == "invalid_successor" and reply.answer is None
    assert reply.blocked_claim_refs and reply.blocked_evidence_refs


def test_unknown_rule_is_not_executed_and_zero_tokens_still_require_a_rule(pilot):
    kernel = _partial(((5, 6),), rule="math:rule:arbitrary_code")
    assert m.count_forward(kernel, _request(5, 1)).reason == "unsupported_rule"
    assert m.count_forward(_private(pilot), _request(18, 0)).answer == 18
    assert m.count_forward(_private(pilot, 1), _request(18, 0)).reason == "missing_rule"
    terminal = m.count_forward(_private(pilot), _request(18, 1))
    assert terminal.reason == "missing_successor" and terminal.answer is None


@pytest.mark.parametrize("start,ticks", (
    (True, ("tick",)), (5.0, ("tick",)), ("5", ("tick",)), (-1, ("tick",)),
    (19, ("tick",)), (5, ("wrong",)), (5, ("tick",) * 5),
))
def test_strict_bounded_requests_reject_invalid_types(start, ticks):
    with pytest.raises(ValueError):
        m.CountingRequest(start=start, ticks=ticks)


def test_all_64_native_responses_precede_any_external_grading(monkeypatch):
    count, original_count, original_grade = 0, m.count_forward, m._grade

    def collect(*args):
        nonlocal count
        count += 1
        return original_count(*args)

    def grade(*args):
        assert count == 64
        return original_grade(*args)

    monkeypatch.setattr(m, "count_forward", collect)
    monkeypatch.setattr(m, "_grade", grade)
    m.run_counting_pilot()
    assert count == 64


def test_source_and_simulation_ledgers_are_isolated(pilot, monkeypatch):
    from verdant_obligations import CounterfactualRuntime, SimulationLedger

    def forbidden(*args, **kwargs):
        raise AssertionError("Counting may not create simulation grants or physical harm outcomes")

    monkeypatch.setattr(CounterfactualRuntime, "execute", forbidden)
    monkeypatch.setattr(SimulationLedger, "reserve", forbidden)
    monkeypatch.setattr(VerdantKernel, "record_governance_outcome", forbidden)
    source = m.fresh_counting_kernel()
    before = source.snapshot()
    assert m.run_counting_pilot(source) == pilot
    assert source.snapshot() == before
    for index in range(4):
        private = _private(pilot, index)
        assert private.state.cycle == 19
        assert not private.state.obligation_kernels and not private.state.obligation_attention_decisions
        assert not private.state.governance_outcomes and not private.state.council_decisions
        assert not private.state.revisions
        assert len(private.state.claims) == (18 if index == 1 else 19)


def test_native_checkpoint_mapping_order_and_new_private_copy_replay(pilot, saved, tmp_path):
    assert m.load_counting_pilot(saved) == pilot
    kernel = _private(pilot)
    path = tmp_path / "counting.vdk"
    save_checkpoint(path, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))
    for name in ("claims", "evidence", "concepts"):
        setattr(restored.state, name, dict(reversed(tuple(getattr(restored.state, name).items()))))
    assert restored.fingerprint() == kernel.fingerprint()
    for o in pilot.receipt.arms[0].observations:
        assert m.count_forward(restored, o.request) == o.reply
    copy = m.restore_counting_arm(pilot)
    _claim(copy, "math:integer:7", "math_successor", "math:integer:9", "new-conflict")
    assert m.count_forward(copy, _request(5, 3)).answer is None
    assert m.count_forward(kernel, _request(5, 3)).answer == 8


@pytest.mark.parametrize("kind", ("foreign", "already_taught"))
def test_nonfresh_canonical_source_rejected_without_mutation(pilot, kind):
    kernel = VerdantKernel(seed=12, state_dim=16) if kind == "foreign" else _private(pilot)
    before = kernel.snapshot()
    with pytest.raises(ValueError, match="fresh"):
        m.run_counting_pilot(kernel)
    assert kernel.snapshot() == before


@pytest.mark.parametrize("drift", ("source", "code"))
def test_source_or_implementation_drift_rejects_completion(monkeypatch, drift):
    source = m.fresh_counting_kernel()
    before = source.snapshot()
    original_teach, original_manifest = m._teach, m._code_manifest

    if drift == "source":
        def mutate(private, role):
            result = original_teach(private, role)
            if role == "taught":
                _claim(source, "untrusted:source", "altered", "untrusted:state", "source-drift")
            return result

        monkeypatch.setattr(m, "_teach", mutate)
    else:
        calls = 0

        def altered_manifest():
            nonlocal calls
            calls += 1
            manifest = original_manifest()
            return manifest if calls == 1 else manifest[:-1]

        monkeypatch.setattr(m, "_code_manifest", altered_manifest)

    with pytest.raises(ValueError, match="source or implementation changed"):
        m.run_counting_pilot(source)
    if drift == "code":
        assert source.snapshot() == before


@pytest.mark.parametrize("attack", (
    "answer", "grade", "expected", "case", "split", "request", "missing_case", "duplicate_case",
    "step_from", "step_to", "step_claim", "step_evidence", "step_order", "step_tick", "step_application",
    "rule_claim", "rule_evidence", "instruction", "lesson_target", "lesson_transition", "lesson_text",
    "code_manifest", "source_checkpoint", "arm_checkpoint", "source_fingerprint", "retuned_scoring",
))
def test_fully_rehashed_derivation_case_decision_and_scoring_substitution_fails(pilot, tmp_path, attack):
    raw = pilot.model_dump(mode="json")
    receipt, arm = raw["receipt"], raw["receipt"]["arms"][0]
    o = arm["observations"][8]
    step = o["reply"]["steps"][0]
    if attack == "answer": o["reply"]["answer"] = 9
    elif attack == "grade": o["grade"] = "incorrect"
    elif attack == "expected": o["expected_answer"] = 9
    elif attack == "case": o["case_id"] = "substituted-case"
    elif attack == "split": o["split"] = "direct_successor"
    elif attack == "request": o["request"]["start"] = 6
    elif attack == "missing_case": arm["observations"].pop()
    elif attack == "duplicate_case": arm["observations"][9] = o
    elif attack == "step_from": step["from_number"] = 6
    elif attack == "step_to": step["to_number"] = 7
    elif attack == "step_claim": step["claim_ref"] = "substituted-claim"
    elif attack == "step_evidence": step["evidence_refs"] = ["substituted-evidence"]
    elif attack == "step_order": o["reply"]["steps"].reverse()
    elif attack == "step_tick": step["tick_index"] = 1
    elif attack == "step_application": step["application_index"] = 1
    elif attack == "rule_claim": o["reply"]["rule_claim_refs"] = ["substituted-rule"]
    elif attack == "rule_evidence": o["reply"]["rule_evidence_refs"] = ["substituted-rule-evidence"]
    elif attack == "instruction": o["reply"]["instruction"] = "successor_twice_per_tick"
    elif attack == "lesson_target": arm["lessons"][0]["object_label"] = "math:integer:2"
    elif attack == "lesson_transition": arm["lessons"][0]["transition_ref"] = "substituted-transition"
    elif attack == "lesson_text": arm["lessons"][0]["native_description"] = "False teacher description."
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
    elif attack == "retuned_scoring": receipt["protocol"]["scoring"] = "credit_any_supplied_instruction"
    path = tmp_path / "forged.vcount"
    path.write_bytes(_rehash(raw))
    with pytest.raises((ValueError, RuntimeError)):
        m.load_counting_pilot(path)


@pytest.mark.parametrize("flag", (
    "source_authenticated", "physical_evidence_admissible", "harm_scoring_implemented",
    "instruction_discovery_observed", "generalized_arithmetic_claim_permitted", "canonical_commit_permitted",
    "resolution_authority_enabled", "promotion_authority_enabled", "policy_rewrite_authority_enabled",
))
def test_rehashed_authority_discovery_or_physical_claim_escalation_rejected(pilot, tmp_path, flag):
    raw = pilot.model_dump(mode="json")
    raw["receipt"][flag] = True
    path = tmp_path / "authority.vcount"
    path.write_bytes(_rehash(raw))
    with pytest.raises(ValueError):
        m.load_counting_pilot(path)


def test_derivation_checker_rejects_forged_or_stale_memory(pilot):
    kernel = _private(pilot)
    q = _request(5, 3)
    reply = m.count_forward(kernel, q)
    forged = reply.model_copy(update={"answer": 9})
    with pytest.raises(ValueError, match="derivation"):
        m.verify_counting_derivation(kernel, q, forged)
    _claim(kernel, "math:integer:7", "math_successor", "math:integer:9", "later-conflict")
    with pytest.raises(ValueError, match="derivation"):
        m.verify_counting_derivation(kernel, q, reply)


def test_bad_hash_duplicate_keys_and_oversized_read_rejected(pilot, tmp_path):
    path = tmp_path / "bad.vcount"
    raw = pilot.model_dump(mode="json")
    raw["receipt_sha256"] = "0" * 64
    path.write_bytes(canonical_json_bytes(raw))
    with pytest.raises(ValueError, match="checksum"):
        m.load_counting_pilot(path)
    path.write_text('{"sidecar_format":"one","sidecar_format":"two"}')
    with pytest.raises(ValueError, match="Duplicate"):
        m.load_counting_pilot(path)
    path.write_bytes(b" " * (m._MAX_BYTES + 1))
    with pytest.raises(ValueError, match="size bound"):
        m.load_counting_pilot(path)


def test_immutable_publication_and_failure_do_not_replace_evidence(pilot, tmp_path, monkeypatch):
    path = tmp_path / "saved.vcount"
    first = m.save_counting_pilot(path, pilot)
    assert m.save_counting_pilot(path, pilot) == first
    path.write_bytes(b"occupied evidence")
    with pytest.raises(RuntimeError, match="different evidence"):
        m.save_counting_pilot(path, pilot)
    assert path.read_bytes() == b"occupied evidence"

    def fail(*args):
        raise OSError("publication failed")

    monkeypatch.setattr(baseline, "_write_immutable", fail)
    absent = tmp_path / "absent.vcount"
    with pytest.raises(OSError, match="publication failed"):
        m.save_counting_pilot(absent, pilot)
    assert not absent.exists()


@pytest.mark.parametrize("role,answer,steps", (("taught", 8, 3), ("valid_null", 8, 3),
    ("incorrect_rule_control", 11, 6), ("no_rule_control", None, 0)))
def test_cli_private_queries_emit_native_steps_and_no_evaluation_labels(saved, capsys, role, answer, steps):
    assert cli(["query", str(saved), "--start", "5", "--ticks", "3", "--role", role]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["reply"]["answer"] == answer and len(result["reply"]["steps"]) == steps
    assert "expected_answer" not in result and "grade" not in result
    assert not result["instruction_discovery_observed"] and not result["physical_evidence_admissible"]


def test_cli_run_replay_and_invalid_occupied_path(pilot, tmp_path, capsys):
    path = tmp_path / "cli.vcount"
    assert cli(["run", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == m.counting_summary(pilot)
    assert cli(["replay", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == m.counting_summary(pilot)
    path.write_text("invalid")
    assert cli(["run", str(path)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid"


def test_v056_recorded_math_pilot_keeps_its_original_code_manifest_and_replay():
    root = Path(__file__).resolve().parent.parent
    old = baseline.load_math_teaching_pilot(root / "artifacts/arithmetic_teaching_v056/pilot.vmp")
    assert old.receipt.code_sources == baseline._code_manifest()
    assert baseline.math_teaching_summary(old)["arms"]["taught"]["retention"]["correct"] == 8


def test_recorded_counting_pilot_replays_exact_native_derivations():
    path = Path(__file__).resolve().parent.parent / "artifacts/counting_teaching_v057/pilot.vcount"
    r = m.load_counting_pilot(path)
    assert m.counting_summary(r)["arms"]["taught"]["held_out_composition"]["correct"] == 8
