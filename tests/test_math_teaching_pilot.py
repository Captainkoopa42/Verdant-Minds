from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from verdant_claims import ClaimLearningPipeline
from verdant_kernel import (
    ClaimPolarity, ClaimSourceClass, EvidenceKind, VerdantKernel,
    checkpoint_bytes, load_checkpoint, save_checkpoint,
)
from verdant_kernel.models import canonical_json_bytes
from verdant_math import teaching_pilot as m
from verdant_math.pilot_cli import main as cli


@pytest.fixture(scope="module")
def pilot():
    return m.run_math_teaching_pilot()


@pytest.fixture(scope="module")
def saved(pilot, tmp_path_factory):
    path = tmp_path_factory.mktemp("math-pilot") / "pilot.vmp"
    m.save_math_teaching_pilot(path, pilot)
    return path


def _rehash(raw):
    raw["receipt_sha256"] = m._sha(canonical_json_bytes(raw["receipt"]))
    return canonical_json_bytes(raw)


def _arm_kernel(pilot, index=0):
    arm = pilot.receipt.arms[index]
    return m._checkpoint(arm.checkpoint_base64, arm.checkpoint_sha256)


def _teach_one(kernel, answer, *, key="lesson", polarity=ClaimPolarity.AFFIRMED,
               source_class=ClaimSourceClass.HUMAN_TESTIMONY):
    return ClaimLearningPipeline().record_claim(kernel, event_key=key,
        native_description=f"Teacher claims one plus one equals {answer}.",
        subject_label="math:sum:left:1:right:1", predicate="math_sum_equals",
        object_label=f"math:integer:{answer}", polarity=polarity,
        source_class=source_class, source_ref="self-reported-teacher")


def test_fixed_cases_controls_and_all_abstentions_are_retained(pilot):
    r = pilot.receipt
    assert tuple(a.role for a in r.arms) == m._ROLES
    assert len({p for p in (*m._TRAINING, *m._HELD_OUT)}) == 16
    assert set(m._TRAINING).isdisjoint(m._HELD_OUT)
    assert all(len(a.lessons) == 8 and len(a.observations) == 16 for a in r.arms)
    summary = m.math_teaching_summary(pilot)["arms"]
    assert summary["taught"]["retention"] == dict(correct=8, incorrect=0, abstained=0)
    assert summary["valid_null"] == summary["taught"]
    assert summary["no_answer_control"]["retention"] == dict(correct=0, incorrect=0, abstained=8)
    assert summary["incorrect_teacher_control"]["retention"] == dict(correct=0, incorrect=8, abstained=0)
    for role in m._ROLES:
        for split in ("held_out_reversed", "held_out_new"):
            assert summary[role][split] == dict(correct=0, incorrect=0, abstained=4)
    assert r.arms[0].model_dump(exclude={"role"}) == r.arms[2].model_dump(exclude={"role"})


def test_learning_is_private_and_no_outcomes_attention_or_simulations_are_created(pilot, monkeypatch):
    from verdant_obligations import CounterfactualRuntime, SimulationLedger

    def forbidden(*args, **kwargs):
        raise AssertionError("Math fact teaching must not execute simulations or create harm outcomes")

    monkeypatch.setattr(CounterfactualRuntime, "execute", forbidden)
    monkeypatch.setattr(SimulationLedger, "reserve", forbidden)
    monkeypatch.setattr(VerdantKernel, "record_governance_outcome", forbidden)
    source = m.fresh_math_kernel()
    before = source.snapshot()
    observed = m.run_math_teaching_pilot(source)
    assert observed == pilot
    assert source.snapshot() == before
    for index in range(4):
        arm = _arm_kernel(pilot, index)
        assert arm.state.cycle == 8
        assert not arm.state.obligation_kernels
        assert not arm.state.obligation_attention_decisions
        assert not arm.state.council_decisions
        assert not arm.state.governance_outcomes
        assert not arm.state.revisions
        assert len(arm.state.claims) == (0 if index == 1 else 8)


def test_query_has_no_answer_oracle_and_remains_pure(pilot, monkeypatch):
    kernel = _arm_kernel(pilot)
    before = kernel.fingerprint()

    def forbidden(*args, **kwargs):
        raise AssertionError("Query called an answer oracle or teacher table")

    class ForbiddenTable:
        __getitem__ = forbidden
        __iter__ = forbidden

    monkeypatch.setattr(m, "_grade", forbidden)
    monkeypatch.setattr(m, "_TEACHER_ANSWERS", ForbiddenTable())
    monkeypatch.setattr(m, "_INCORRECT_ANSWERS", ForbiddenTable())
    assert m.recall_addition_fact(kernel, m.AdditionProblem(left=2, right=3)).answer == 5
    assert m.recall_addition_fact(kernel, m.AdditionProblem(left=3, right=2)).answer is None
    assert kernel.fingerprint() == before


def test_all_responses_across_all_arms_precede_grading(monkeypatch):
    original_recall, original_grade = m.recall_addition_fact, m._grade
    count = 0

    def recall(*args):
        nonlocal count
        count += 1
        return original_recall(*args)

    def grade(index, *args):
        assert count == 64
        return original_grade(index, *args)

    monkeypatch.setattr(m, "recall_addition_fact", recall)
    monkeypatch.setattr(m, "_grade", grade)
    m.run_math_teaching_pilot()
    assert count == 64


def test_native_trace_has_teacher_testimony_and_answer_free_held_out_queries(pilot):
    kernel = _arm_kernel(pilot)
    for lesson in pilot.receipt.arms[0].lessons:
        assert len(lesson.claim_refs) == 1 and len(lesson.evidence_refs) == 3
        claim = kernel.state.claims[lesson.claim_refs[0]]
        assert {e.source_class for e in claim.support_ledger} == {ClaimSourceClass.HUMAN_TESTIMONY}
        assert all(kernel.state.evidence[e.evidence_id].kind == EvidenceKind.TESTIMONY
                   for e in claim.support_ledger)
        assert lesson.transition_ref in {t.transition_id for t in kernel.state.transitions}
    for observation in pilot.receipt.arms[0].observations[8:]:
        assert observation.reply.reason == "unseen"
        assert not observation.reply.claim_refs and not observation.reply.evidence_refs
        assert set(observation.problem.model_dump()) == {"left", "right"}
    assert not pilot.receipt.source_authenticated
    assert not pilot.receipt.physical_evidence_admissible


def test_conflicting_answers_abstain_and_preserve_both_native_claims():
    kernel = m.fresh_math_kernel()
    _teach_one(kernel, 2, key="correct")
    _teach_one(kernel, 3, key="incorrect")
    before = kernel.snapshot()
    reply = m.recall_addition_fact(kernel, m.AdditionProblem(left=1, right=1))
    assert reply.answer is None and reply.reason == "conflicting_claims"
    assert len(reply.claim_refs) == len(reply.evidence_refs) == 2
    assert kernel.snapshot() == before


def test_negation_is_not_suppressed_by_retrieval():
    kernel = m.fresh_math_kernel()
    _teach_one(kernel, 2, key="positive")
    _teach_one(kernel, 2, key="negative", polarity=ClaimPolarity.NEGATED)
    before = kernel.fingerprint()
    reply = m.recall_addition_fact(kernel, m.AdditionProblem(left=1, right=1))
    assert reply.answer is None and len(reply.claim_refs) == 2
    assert kernel.fingerprint() == before


def test_incorrect_teacher_is_recalled_without_hidden_correction():
    kernel = m.fresh_math_kernel()
    _teach_one(kernel, 9)
    reply = m.recall_addition_fact(kernel, m.AdditionProblem(left=1, right=1))
    assert reply.answer == 9
    assert m._grade(0, m.AdditionProblem(left=1, right=1), reply).grade == "incorrect"


@pytest.mark.parametrize("source_class", (
    ClaimSourceClass.PHYSICAL_OUTCOME, ClaimSourceClass.DIRECT_OBSERVATION,
    ClaimSourceClass.SYSTEM_INFERENCE,
))
def test_self_reported_physical_or_system_origin_cannot_replace_teacher_testimony(source_class):
    kernel = m.fresh_math_kernel()
    _teach_one(kernel, 2, source_class=source_class)
    reply = m.recall_addition_fact(kernel, m.AdditionProblem(left=1, right=1))
    assert reply.answer is None and reply.reason == "invalid_testimony"
    assert reply.claim_refs and reply.evidence_refs


@pytest.mark.parametrize("left", (True, 1.0, "1", -1, 10))
def test_invalid_operand_types_and_ranges_fail_closed(left):
    with pytest.raises(ValueError):
        m.AdditionProblem(left=left, right=1)


@pytest.mark.parametrize("kind", ("foreign", "exposed"))
def test_nonfresh_source_rejected_without_mutation(pilot, kind):
    kernel = VerdantKernel(seed=100, state_dim=16) if kind == "foreign" else _arm_kernel(pilot)
    before = kernel.fingerprint()
    with pytest.raises(m.MathTeachingPilotIntegrityError, match="fresh"):
        m.run_math_teaching_pilot(kernel)
    assert kernel.fingerprint() == before


def test_checkpoint_roundtrip_and_mapping_order_replay(pilot, saved, tmp_path):
    assert m.load_math_teaching_pilot(saved) == pilot
    for index in range(4):
        kernel = _arm_kernel(pilot, index)
        path = tmp_path / f"arm-{index}.vdk"
        save_checkpoint(path, kernel.snapshot())
        restored = VerdantKernel.from_state(load_checkpoint(path))
        assert checkpoint_bytes(restored.snapshot()) == checkpoint_bytes(kernel.snapshot())
        for name in ("claims", "concepts", "evidence"):
            setattr(restored.state, name, dict(reversed(tuple(getattr(restored.state, name).items()))))
        assert restored.fingerprint() == kernel.fingerprint()
        for o in pilot.receipt.arms[index].observations:
            assert m.recall_addition_fact(restored, o.problem) == o.reply


@pytest.mark.parametrize("attack", (
    "answer", "grade", "expected", "case", "split", "query", "claim_ref", "evidence_ref",
    "missing_case", "duplicate_case", "lesson_answer", "lesson_transition", "code_manifest",
    "arm_checkpoint", "source_checkpoint", "source_fingerprint",
))
def test_rehashed_substitutions_and_outcome_dependent_scoring_fail_replay(pilot, tmp_path, attack):
    raw = pilot.model_dump(mode="json")
    r, arm = raw["receipt"], raw["receipt"]["arms"][0]
    o = arm["observations"][0]
    if attack == "answer": o["reply"]["answer"] = 1
    elif attack == "grade": o["grade"] = "incorrect"
    elif attack == "expected": o["expected_answer"] = 1
    elif attack == "case": o["case_id"] = "substituted-case"
    elif attack == "split": o["split"] = "held_out_new"
    elif attack == "query": o["problem"]["left"] = 1
    elif attack == "claim_ref": o["reply"]["claim_refs"] = ["substituted-claim"]
    elif attack == "evidence_ref": o["reply"]["evidence_refs"] = ["substituted-evidence"]
    elif attack == "missing_case": arm["observations"].pop()
    elif attack == "duplicate_case": arm["observations"][1] = o
    elif attack == "lesson_answer": arm["lessons"][0]["declared_answer"] = 1
    elif attack == "lesson_transition": arm["lessons"][0]["transition_ref"] = "substituted-transition"
    elif attack == "code_manifest": r["code_sources"][0]["sha256"] = "0" * 64
    elif attack == "arm_checkpoint":
        for key in ("checkpoint_base64", "checkpoint_sha256", "kernel_fingerprint"):
            arm[key] = r["arms"][3][key]
    elif attack == "source_checkpoint":
        data = checkpoint_bytes(_arm_kernel(pilot).snapshot())
        r["source_checkpoint_base64"] = base64.b64encode(data).decode("ascii")
        r["source_checkpoint_sha256"] = m._sha(data)
        r["source_kernel_fingerprint"] = _arm_kernel(pilot).fingerprint()
    elif attack == "source_fingerprint": r["source_kernel_fingerprint"] = "0" * 64
    path = tmp_path / "forged.vmp"
    path.write_bytes(_rehash(raw))
    with pytest.raises((ValueError, RuntimeError)):
        m.load_math_teaching_pilot(path)


@pytest.mark.parametrize("flag", (
    "source_authenticated", "physical_evidence_admissible", "harm_scoring_implemented",
    "generalized_arithmetic_claim_permitted", "canonical_commit_permitted",
    "resolution_authority_enabled", "promotion_authority_enabled", "policy_rewrite_authority_enabled",
))
def test_rehashed_authority_and_truth_claim_escalations_are_rejected(pilot, tmp_path, flag):
    raw = pilot.model_dump(mode="json")
    raw["receipt"][flag] = True
    path = tmp_path / "authority.vmp"
    path.write_bytes(_rehash(raw))
    with pytest.raises(ValueError):
        m.load_math_teaching_pilot(path)


def test_frozen_protocol_cannot_retune_metric_or_replace_cases(pilot, tmp_path):
    raw = pilot.model_dump(mode="json")
    raw["receipt"]["protocol"]["scoring"] = "reward_any_teacher_answer"
    path = tmp_path / "retuned.vmp"
    path.write_bytes(_rehash(raw))
    with pytest.raises(ValueError, match="frozen"):
        m.load_math_teaching_pilot(path)


def test_checksum_duplicate_json_key_and_size_bound_fail(pilot, tmp_path):
    path = tmp_path / "invalid.vmp"
    raw = pilot.model_dump(mode="json")
    raw["receipt_sha256"] = "0" * 64
    path.write_bytes(canonical_json_bytes(raw))
    with pytest.raises(ValueError, match="checksum"):
        m.load_math_teaching_pilot(path)
    path.write_text('{"sidecar_format":"first","sidecar_format":"second"}')
    with pytest.raises(ValueError, match="Duplicate"):
        m.load_math_teaching_pilot(path)
    path.write_bytes(b" " * (m._MAX_BYTES + 1))
    with pytest.raises(ValueError, match="size bound"):
        m.load_math_teaching_pilot(path)


def test_immutable_publication_rejects_conflict_and_propagates_failure(pilot, tmp_path, monkeypatch):
    path = tmp_path / "pilot.vmp"
    m.save_math_teaching_pilot(path, pilot)
    before = path.read_bytes()
    assert m.save_math_teaching_pilot(path, pilot) == m._sha(before)
    path.write_bytes(b"conflicting evidence")
    with pytest.raises(RuntimeError, match="different evidence"):
        m.save_math_teaching_pilot(path, pilot)
    assert path.read_bytes() == b"conflicting evidence"

    def fail(*args):
        raise OSError("publication failed")

    monkeypatch.setattr(m, "_write_immutable", fail)
    absent = tmp_path / "absent.vmp"
    with pytest.raises(OSError, match="publication failed"):
        m.save_math_teaching_pilot(absent, pilot)
    assert not absent.exists()


def test_source_mutation_and_code_drift_reject_completion(monkeypatch):
    source = m.fresh_math_kernel()
    original = m._teach

    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        source.state.identity = source.state.identity.model_copy(update={"run_label": "changed"})
        return result

    monkeypatch.setattr(m, "_teach", mutate)
    with pytest.raises(ValueError, match="source or implementation changed"):
        m.run_math_teaching_pilot(source)
    monkeypatch.setattr(m, "_teach", original)
    manifest = m._code_manifest()
    calls = 0

    def drift():
        nonlocal calls
        calls += 1
        return manifest if calls == 1 else ()

    monkeypatch.setattr(m, "_code_manifest", drift)
    with pytest.raises(ValueError, match="source or implementation changed"):
        m.run_math_teaching_pilot()


def test_cli_run_replay_and_conflict_report(pilot, tmp_path, capsys):
    path = tmp_path / "cli.vmp"
    assert cli(["run", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == m.math_teaching_summary(pilot)
    assert cli(["replay", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == m.math_teaching_summary(pilot)
    path.write_text("bad")
    assert cli(["run", str(path)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid"


@pytest.mark.parametrize("role,left,right,answer", (
    ("taught", 2, 3, 5), ("taught", 3, 2, None),
    ("incorrect_teacher_control", 2, 3, 6), ("no_answer_control", 2, 3, None),
))
def test_cli_query_is_explicit_native_retrieval_with_no_grading_labels(saved, capsys, role, left, right, answer):
    assert cli(["query", str(saved), "--role", role, "--left", str(left), "--right", str(right)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["reply"]["answer"] == answer
    assert "expected_answer" not in result and "grade" not in result
    assert not result["generalized_arithmetic_claim_permitted"]


def test_compressed_and_malformed_embedded_checkpoints_fail_closed(pilot, tmp_path):
    import io
    import zipfile

    raw = pilot.model_dump(mode="json")
    r = raw["receipt"]
    original = base64.b64decode(r["source_checkpoint_base64"])
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as source:
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as target:
            for name in source.namelist():
                target.writestr(name, source.read(name))
    for data in (output.getvalue(), b"invalid zip"):
        r["source_checkpoint_base64"] = base64.b64encode(data).decode("ascii")
        r["source_checkpoint_sha256"] = m._sha(data)
        path = tmp_path / "zip.vmp"
        path.write_bytes(_rehash(raw))
        assert cli(["replay", str(path)]) == 2


def test_restored_math_memory_is_an_independent_private_copy(pilot):
    first = m.restore_math_teaching_arm(pilot)
    second = m.restore_math_teaching_arm(pilot)
    before = second.fingerprint()
    _teach_one(first, 9, key="new-conflict")
    assert second.fingerprint() == before
    assert m.recall_addition_fact(first, m.AdditionProblem(left=1, right=1)).answer is None
    assert m.recall_addition_fact(second, m.AdditionProblem(left=1, right=1)).answer == 2


def test_recorded_pilot_replays_from_its_native_checkpoints():
    path = Path(__file__).resolve().parent.parent / "artifacts/arithmetic_teaching_v056/pilot.vmp"
    assert m.math_teaching_summary(m.load_math_teaching_pilot(path))["arms"]["taught"]["retention"]["correct"] == 8
