from __future__ import annotations

import json
from pathlib import Path

import pytest

from verdant_claims import ClaimLearningPipeline
from verdant_kernel import ClaimPolarity, ClaimSourceClass, VerdantKernel, load_checkpoint, save_checkpoint
from verdant_kernel.models import canonical_json_bytes
from verdant_math import teaching_pilot as baseline
from verdant_math.counting import pilot as counting
from verdant_math.addition import pilot as addition
from verdant_math.coverage import challenge as m
from verdant_math.coverage.cli import main as cli

_ROOT = Path(__file__).resolve().parent.parent
_PLAN = _ROOT / "artifacts/addition_coverage_v059/challenge.vacp"
_RESULT = _ROOT / "artifacts/addition_coverage_v059/evaluation.vacr"


@pytest.fixture(scope="module")
def plan():
    return m.load_coverage_plan(_PLAN)


@pytest.fixture(scope="module")
def evaluation():
    return m.load_coverage_challenge(_PLAN, _RESULT)


def _private(evaluation, index=0):
    arm = evaluation.receipt.arms[index]
    return baseline._checkpoint(arm.checkpoint_base64, arm.checkpoint_sha256)


def _rehash(raw):
    if "receipt" in raw:
        nested = raw["receipt"]["frozen_plan"]
        nested["plan_sha256"] = baseline._sha(canonical_json_bytes(nested["plan"]))
        raw["receipt_sha256"] = baseline._sha(canonical_json_bytes(raw["receipt"]))
    else:
        raw["plan_sha256"] = baseline._sha(canonical_json_bytes(raw["plan"]))
    return canonical_json_bytes(raw)


def _claim(kernel, key="drift"):
    ClaimLearningPipeline().record_claim(kernel, event_key=key,
        native_description="Adversarial runtime state drift.", subject_label="test:drift",
        predicate="test_changed", object_label="test:value", polarity=ClaimPolarity.AFFIRMED,
        source_class=ClaimSourceClass.HUMAN_TESTIMONY, source_ref="declared-coverage-test")


def test_freeze_persists_before_any_teaching_response_or_evaluator(plan, tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Freeze executed teaching/query/grading")

    for name in ("_teach", "derive_addition", "_grade"):
        monkeypatch.setattr(addition, name, forbidden)
    fresh = m.freeze_coverage_plan()
    assert fresh == plan
    path = tmp_path / "frozen.vacp"
    digest = m.save_coverage_plan(path, fresh)
    assert m.save_coverage_plan(path, fresh) == digest
    assert m.load_coverage_plan(path) == fresh
    assert path.read_bytes() == _PLAN.read_bytes()


def test_all_32_cases_are_typed_fresh_disjoint_and_predeclared(plan):
    raw = tuple(c.raw_request_json.encode() for c in plan.plan.cases)
    excluded = {canonical_json_bytes({"left": a, "right": b})
                for a, b in (*m._EXCLUDED, *m._INVALID_PROBES)}
    assert len(set(raw)) == 32 and set(raw).isdisjoint(excluded)
    assert len(plan.plan.code_sources) == 31
    assert {g: sum(c.group == g for c in plan.plan.cases) for g in m._GROUPS} == dict(
        supported_small_orders=8, supported_large_left=4, reversed_missing_mapping=4,
        other_missing_mapping=4, missing_successor=4, invalid_input=8)
    pairs = {}
    for c in plan.plan.cases:
        if c.order_pair:
            pairs.setdefault(c.order_pair, []).append(json.loads(c.raw_request_json))
    assert len(pairs) == 8
    for cases in pairs.values():
        assert len(cases) == 2
        assert cases[0] == dict(left=cases[1]["right"], right=cases[1]["left"])
    assert json.loads(plan.plan.cases[24].raw_request_json)["right"] is False
    assert isinstance(json.loads(plan.plan.cases[26].raw_request_json)["right"], float)
    assert json.loads(plan.plan.cases[27].raw_request_json)["right"] == "2"


def test_all_128_records_controls_and_fixed_denominators_are_retained(evaluation):
    summary = m.coverage_summary(evaluation)
    for role in ("taught", "valid_null"):
        assert summary["arms"][role]["total"] == dict(correct=12, incorrect=0, abstained=12, invalid_input=8)
    assert summary["arms"]["no_rule_control"]["total"] == dict(correct=0, incorrect=0, abstained=24, invalid_input=8)
    assert summary["arms"]["incorrect_rule_control"]["total"] == dict(correct=0, incorrect=16, abstained=8, invalid_input=8)
    assert sum(len(a.observations) for a in evaluation.receipt.arms) == 128
    taught, _, null, _ = evaluation.receipt.arms
    assert taught.model_dump(exclude={"role"}) == null.model_dump(exclude={"role"})
    for arm in evaluation.receipt.arms:
        assert arm.lessons[:24] == taught.lessons[:24]
        assert sum(summary["arms"][arm.role]["total"].values()) == 32
        assert tuple(o.case for o in arm.observations) == evaluation.receipt.frozen_plan.plan.cases


def test_operand_orders_and_missing_dependencies_retain_native_provenance(evaluation):
    kernel = _private(evaluation)
    observations = evaluation.receipt.arms[0].observations
    for o in observations[:12]:
        assert o.grade == "correct" and o.reply.start_operand == "left_operand"
        mapping = kernel.state.claims[o.reply.operand_claim_refs[0]]
        assert kernel.state.concepts[mapping.subject_concept_id].label == f"math:integer:{o.request.right}"
        assert o.reply.counting_request.start == o.request.left
        current = o.request.left
        for step in o.reply.counting_reply.steps:
            edge = kernel.state.claims[step.claim_ref]
            assert step.from_number == current and edge.predicate == "math_successor"
            assert kernel.state.concepts[edge.object_concept_id].label == f"math:integer:{step.to_number}"
            assert step.evidence_refs == tuple(sorted(e.evidence_id for e in edge.support_ledger))
            current = step.to_number
        assert o.reply.answer == current
    assert observations[0].reply.answer == observations[1].reply.answer == 2
    for o in observations[12:20]:
        assert o.grade == "abstained" and o.reply.reason == "missing_operand_tokens"
        assert o.reply.addition_rule_claim_refs and o.reply.addition_rule_evidence_refs
        assert not o.reply.operand_claim_refs and o.reply.counting_request is None
    for o, n in zip(observations[20:24], (1, 2, 3, 0)):
        assert o.grade == "abstained" and o.reply.reason == "counting_abstained"
        assert o.reply.counting_reply.reason == "missing_successor"
        assert len(o.reply.counting_reply.steps) == n and o.reply.answer is None
        assert o.reply.operand_claim_refs and o.reply.counting_reply.rule_claim_refs
        if n:
            assert o.reply.counting_reply.steps[-1].to_number == 18
    # The wrong starting rule avoids the terminal edge. Keep its wrong
    # responses in the original missing-successor group, without relabeling.
    wrong = evaluation.receipt.arms[3].observations
    assert [o.reply.answer for o in wrong[20:24]] == [4, 6, 8, 4]
    assert all(o.grade == "incorrect" and o.case.group == "missing_successor" for o in wrong[20:24])
    assert all(o.reply.reason == "missing_addition_rule" for o in evaluation.receipt.arms[1].observations[:24])


def test_invalid_inputs_preserve_types_errors_without_targets_or_native_answers(evaluation):
    expected = (("right", "int_type"), ("left", "int_type"), ("right", "int_type"),
                ("right", "int_type"), ("left", "less_than_equal"), ("right", "missing"),
                ("answer", "extra_forbidden"), ("left", "int_type"))
    for arm in evaluation.receipt.arms:
        for o, (location, error) in zip(arm.observations[24:], expected):
            assert o.grade == "invalid_input" and o.expected_answer is None
            assert o.request is None and o.reply is None
            assert o.input_errors == (m.InputRejection(location=(location,), error_type=error),)


def test_all_response_records_precede_unchanged_external_grader(plan, monkeypatch):
    original_response, original_grade = m._respond, addition._grade
    responses, graded = [], []

    def respond(kernel, case):
        r = original_response(kernel, case)
        assert "expected_answer" not in r.model_dump() and "grade" not in r.model_dump()
        responses.append(r)
        return r

    def grade(index, request, reply):
        assert len(responses) == 128
        assert set(request.model_dump()) == {"left", "right"}
        graded.append(request)
        return original_grade(index, request, reply)

    def forbidden(*args, **kwargs):
        raise AssertionError("Coverage read another pilot's grader")

    monkeypatch.setattr(m, "_respond", respond)
    monkeypatch.setattr(addition, "_grade", grade)
    monkeypatch.setattr(baseline, "_grade", forbidden)
    monkeypatch.setattr(counting, "_grade", forbidden)
    m.run_coverage_challenge(_PLAN)
    assert len(graded) == 96 and sum(r.request is None for r in responses) == 32


def test_canonical_simulation_attention_and_governance_isolation(evaluation, monkeypatch):
    from verdant_obligations import CounterfactualRuntime, SimulationLedger

    def forbidden(*args, **kwargs):
        raise AssertionError("Coverage acquired simulation/Attention/governance authority")

    monkeypatch.setattr(CounterfactualRuntime, "execute", forbidden)
    monkeypatch.setattr(SimulationLedger, "reserve", forbidden)
    monkeypatch.setattr(VerdantKernel, "record_governance_outcome", forbidden)
    source = m.fresh_coverage_kernel()
    before = source.snapshot()
    assert m.run_coverage_challenge(_PLAN, source) == evaluation
    assert source.snapshot() == before
    for index in range(4):
        private = _private(evaluation, index)
        assert private.state.cycle == 25 and len(private.state.claims) == (24 if index == 1 else 25)
        assert not private.state.obligation_kernels and not private.state.obligation_attention_decisions
        assert not private.state.governance_outcomes and not private.state.council_decisions
        assert not private.state.revisions


def test_checkpoint_replay_mapping_order_and_private_state_are_stable(evaluation, tmp_path):
    kernel = _private(evaluation)
    path = tmp_path / "coverage.vdk"
    save_checkpoint(path, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))
    for name in ("claims", "concepts", "evidence"):
        setattr(restored.state, name, dict(reversed(tuple(getattr(restored.state, name).items()))))
    assert restored.fingerprint() == kernel.fingerprint()
    before = kernel.snapshot()
    for o in evaluation.receipt.arms[0].observations:
        assert m._respond(restored, o.case).model_dump() == o.model_dump(exclude={"expected_answer", "grade"})
    _claim(restored)
    assert kernel.snapshot() == before


@pytest.mark.parametrize("kind", ("missing_plan", "invalid_plan", "foreign_source", "already_taught"))
def test_unenrolled_or_nonfresh_execution_fails_before_teaching(plan, evaluation, tmp_path, monkeypatch, kind):
    path, source = tmp_path / "plan.vacp", m.fresh_coverage_kernel()
    if kind == "invalid_plan":
        path.write_text("{}")
    elif kind != "missing_plan":
        path = _PLAN
        source = VerdantKernel(seed=12, state_dim=16) if kind == "foreign_source" else _private(evaluation)
    before = source.snapshot()

    def forbidden(*args):
        raise AssertionError("Invalid enrollment started teaching")

    monkeypatch.setattr(addition, "_teach", forbidden)
    with pytest.raises((OSError, ValueError)):
        m.run_coverage_challenge(path, source)
    assert source.snapshot() == before


@pytest.mark.parametrize("drift", ("source", "code", "plan", "private", "null"))
def test_drift_or_divergent_null_rejects_completion(plan, tmp_path, monkeypatch, drift):
    path = tmp_path / "plan.vacp"
    path.write_bytes(_PLAN.read_bytes())
    source = m.fresh_coverage_kernel()
    teach, respond, manifest = addition._teach, m._respond, m._code_manifest
    changed = False

    def teaching(private, role):
        traces = teach(private, role)
        if role == "taught":
            if drift == "source": _claim(source)
            elif drift == "code": monkeypatch.setattr(m, "_code_manifest", lambda: manifest()[:-1])
        if drift == "null" and role == "valid_null": _claim(private)
        return traces

    def response(private, case):
        nonlocal changed
        r = respond(private, case)
        if not changed:
            changed = True
            if drift == "plan": path.write_bytes(path.read_bytes() + b" ")
            elif drift == "private": _claim(private)
        return r

    monkeypatch.setattr(addition, "_teach", teaching)
    monkeypatch.setattr(m, "_respond", response)
    with pytest.raises(ValueError, match="changed|diverged"):
        m.run_coverage_challenge(path, source)
    assert not (tmp_path / "evaluation.vacr").exists()


@pytest.mark.parametrize("attack", ("metric", "control", "exclusions", "group_basis", "case",
    "group", "pair", "raw_type", "missing_case", "duplicate_case", "case_order", "manifest",
    "source_checkpoint", "source_fingerprint"))
def test_fully_rehashed_plan_case_metric_and_source_substitutions_fail(plan, evaluation, tmp_path, attack):
    raw = plan.model_dump(mode="json")
    p = raw["plan"]
    if attack == "metric": p["protocol"]["scoring"] = "credit_any_answer"
    elif attack == "control": p["protocol"]["roles"][1] = "taught"
    elif attack == "exclusions": p["protocol"]["excluded_consumed_and_observed_ordered_pairs"] = []
    elif attack == "group_basis": p["protocol"]["groups_basis"] = "classify_after_results"
    elif attack == "case": p["cases"][0]["case_id"] = "foreign-case"
    elif attack == "group": p["cases"][0]["group"] = "missing_successor"
    elif attack == "pair": p["cases"][0]["order_pair"] = "large-13-1"
    elif attack == "raw_type": p["cases"][0]["raw_request_json"] = '{"left":0.0,"right":2}'
    elif attack == "missing_case": p["cases"].pop()
    elif attack == "duplicate_case": p["cases"][1] = p["cases"][0]
    elif attack == "case_order": p["cases"].reverse()
    elif attack == "manifest": p["code_sources"][0]["sha256"] = "0" * 64
    elif attack == "source_checkpoint":
        arm = evaluation.receipt.arms[0]
        p.update(source_checkpoint_base64=arm.checkpoint_base64,
            source_checkpoint_sha256=arm.checkpoint_sha256, source_kernel_fingerprint=arm.kernel_fingerprint)
    elif attack == "source_fingerprint": p["source_kernel_fingerprint"] = "0" * 64
    path = tmp_path / "forged.vacp"
    path.write_bytes(_rehash(raw))
    with pytest.raises(ValueError):
        m.load_coverage_plan(path)


@pytest.mark.parametrize("attack", ("case", "group", "pair", "raw_type", "left", "answer",
    "expected", "grade", "missing_invalid", "duplicate_invalid", "case_order", "role_order",
    "input_location", "input_type", "invalid_target", "invalid_credit", "mapping_claim", "mapping_evidence",
    "step_claim", "step_evidence", "step_target", "step_order", "partial_steps", "partial_credit",
    "instruction", "start_operand", "count_start", "count_tokens", "lesson_text", "lesson_transition",
    "lesson_target", "arm_checkpoint", "arm_fingerprint", "plan_hash", "embedded_metric", "embedded_manifest"))
def test_fully_rehashed_case_response_partial_invalid_grade_and_lineage_attacks_fail(evaluation, tmp_path, attack):
    raw = evaluation.model_dump(mode="json")
    receipt, arm = raw["receipt"], raw["receipt"]["arms"][0]
    o, invalid = arm["observations"][9], arm["observations"][24]
    reply, step = o["reply"], o["reply"]["counting_reply"]["steps"][0]
    if attack == "case": o["case"]["case_id"] = "foreign-case"
    elif attack == "group": o["case"]["group"] = "missing_successor"
    elif attack == "pair": o["case"]["order_pair"] = "small-02"
    elif attack == "raw_type": invalid["case"]["raw_request_json"] = '{"left":14,"right":0}'
    elif attack == "left": o["request"]["left"] = 13
    elif attack == "answer": reply["answer"] = 15
    elif attack == "expected": o["expected_answer"] = 15
    elif attack == "grade": o["grade"] = "incorrect"
    elif attack == "missing_invalid": arm["observations"].pop()
    elif attack == "duplicate_invalid": arm["observations"][25] = invalid
    elif attack == "case_order": arm["observations"].reverse()
    elif attack == "role_order": receipt["arms"].reverse()
    elif attack == "input_location": invalid["input_errors"][0]["location"] = ["left"]
    elif attack == "input_type": invalid["input_errors"][0]["error_type"] = "missing"
    elif attack == "invalid_target": invalid["expected_answer"] = 14
    elif attack == "invalid_credit": invalid["grade"] = "correct"
    elif attack == "mapping_claim": reply["operand_claim_refs"] = ["foreign-mapping"]
    elif attack == "mapping_evidence": reply["operand_evidence_refs"] = ["foreign-evidence"]
    elif attack == "step_claim": step["claim_ref"] = "foreign-edge"
    elif attack == "step_evidence": step["evidence_refs"] = ["foreign-evidence"]
    elif attack == "step_target": step["to_number"] = 16
    elif attack == "step_order": reply["counting_reply"]["steps"].reverse()
    elif attack == "partial_steps": arm["observations"][22]["reply"]["counting_reply"]["steps"].pop()
    elif attack == "partial_credit": arm["observations"][22]["grade"] = "correct"
    elif attack == "instruction": reply["instruction"] = "count_from_right_by_right"
    elif attack == "start_operand": reply["start_operand"] = "right_operand"
    elif attack == "count_start": reply["counting_request"]["start"] = 13
    elif attack == "count_tokens": reply["counting_request"]["ticks"] = ["tick"]
    elif attack == "lesson_text": arm["lessons"][19]["native_description"] = "Substituted teacher text."
    elif attack == "lesson_transition": arm["lessons"][19]["transition_ref"] = "foreign-transition"
    elif attack == "lesson_target": arm["lessons"][19]["object_label"] = "math:tokens:tick"
    elif attack == "arm_checkpoint":
        for key in ("checkpoint_base64", "checkpoint_sha256", "kernel_fingerprint"):
            arm[key] = receipt["arms"][3][key]
    elif attack == "arm_fingerprint": arm["kernel_fingerprint"] = "0" * 64
    elif attack == "plan_hash": receipt["plan_file_sha256"] = "0" * 64
    elif attack == "embedded_metric": receipt["frozen_plan"]["plan"]["protocol"]["scoring"] = "credit_any_answer"
    elif attack == "embedded_manifest": receipt["frozen_plan"]["plan"]["code_sources"][0]["sha256"] = "0" * 64
    path = tmp_path / "forged.vacr"
    path.write_bytes(_rehash(raw))
    with pytest.raises(ValueError):
        m.load_coverage_challenge(_PLAN, path)


@pytest.mark.parametrize("flag", m._FLAGS)
@pytest.mark.parametrize("target", ("plan", "receipt"))
def test_false_source_physical_discovery_or_authority_claims_fail(plan, evaluation, tmp_path, flag, target):
    raw = (plan if target == "plan" else evaluation).model_dump(mode="json")
    raw[target][flag] = True
    path = tmp_path / "escalation.json"
    path.write_bytes(_rehash(raw))
    with pytest.raises(ValueError):
        if target == "plan": m.load_coverage_plan(path)
        else: m.load_coverage_challenge(_PLAN, path)


def test_exact_plan_bytes_are_required_for_replay(evaluation, tmp_path):
    path = tmp_path / "pretty.vacp"
    path.write_text(json.dumps(json.loads(_PLAN.read_bytes()), indent=2))
    assert m.load_coverage_plan(path) == evaluation.receipt.frozen_plan
    with pytest.raises(ValueError, match="different frozen plan bytes"):
        m.load_coverage_challenge(path, _RESULT)


@pytest.mark.parametrize("target", ("plan", "result"))
@pytest.mark.parametrize("attack", ("duplicate_json", "bad_hash", "oversized"))
def test_bounded_read_duplicate_keys_and_hash_errors_fail(plan, evaluation, tmp_path, target, attack):
    path = tmp_path / "invalid.json"
    if attack == "duplicate_json": path.write_text('{"sidecar_format":"one","sidecar_format":"two"}')
    elif attack == "oversized": path.write_bytes(b" " * (m._MAX_BYTES + 1))
    else:
        raw = (plan if target == "plan" else evaluation).model_dump(mode="json")
        raw["plan_sha256" if target == "plan" else "receipt_sha256"] = "0" * 64
        path.write_bytes(canonical_json_bytes(raw))
    with pytest.raises(ValueError):
        if target == "plan": m.load_coverage_plan(path)
        else: m.load_coverage_challenge(_PLAN, path)


def test_immutable_publication_and_failure_preserve_evidence(plan, evaluation, tmp_path, monkeypatch):
    path = tmp_path / "saved.vacr"
    first = m.save_coverage_challenge(_PLAN, path, evaluation)
    assert m.save_coverage_challenge(_PLAN, path, evaluation) == first
    assert path.read_bytes() == _RESULT.read_bytes()
    path.write_bytes(b"occupied evidence")
    with pytest.raises(RuntimeError, match="different evidence"):
        m.save_coverage_challenge(_PLAN, path, evaluation)
    assert path.read_bytes() == b"occupied evidence"
    with pytest.raises(RuntimeError, match="different evidence"):
        m.save_coverage_plan(path, plan)
    assert path.read_bytes() == b"occupied evidence"

    def fail(*args):
        raise OSError("publication failed")

    monkeypatch.setattr(baseline, "_write_immutable", fail)
    absent = tmp_path / "absent.vacr"
    with pytest.raises(OSError, match="publication failed"):
        m.save_coverage_challenge(_PLAN, absent, evaluation)
    assert not absent.exists()


def test_cli_freeze_run_replay_and_missing_or_occupied_plan(tmp_path, capsys):
    plan_path, result_path = tmp_path / "cli.vacp", tmp_path / "cli.vacr"
    assert cli(["run", str(plan_path), str(result_path)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid" and not result_path.exists()
    assert cli(["freeze", str(plan_path)]) == 0
    assert json.loads(capsys.readouterr().out)["execution_performed"] is False
    assert cli(["run", str(plan_path), str(result_path)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["arms"]["taught"]["total"]["abstained"] == 12
    assert cli(["replay", str(plan_path), str(result_path)]) == 0
    assert json.loads(capsys.readouterr().out) == summary
    plan_path.write_text("occupied evidence")
    assert cli(["freeze", str(plan_path)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid"
    assert plan_path.read_text() == "occupied evidence"


def test_all_three_prior_pilots_preserve_original_bytes_manifests_and_replay():
    old = baseline.load_math_teaching_pilot(_ROOT / "artifacts/arithmetic_teaching_v056/pilot.vmp")
    middle = counting.load_counting_pilot(_ROOT / "artifacts/counting_teaching_v057/pilot.vcount")
    previous = addition.load_addition_pilot(_ROOT / "artifacts/scaffold_addition_v058/pilot.vadd")
    for result, manifest, size in ((old, baseline._code_manifest(), 22),
                                  (middle, counting._code_manifest(), 25),
                                  (previous, addition._code_manifest(), 28)):
        assert result.receipt.code_sources == manifest and len(manifest) == size
    assert old.receipt_sha256 == "c27e284f2dd85ba861a3076e63b8f663ba9fa102c72bd69eb86522aaabe257ea"
    assert middle.receipt_sha256 == "deacf11110f39b7d04b42d5ef201f0c4a0fd0c038c303234c59ee5cf36895611"
    assert previous.receipt_sha256 == "922618a11646e29d0e96707fa9c6c0d28adbc1fcc4b8b7eb4adfeb5bf3d74c88"
