from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import pytest

from verdant_claims import ClaimLearningPipeline
from verdant_kernel import VerdantKernel, checkpoint_bytes, load_checkpoint, save_checkpoint
from verdant_kernel.models import canonical_json_bytes
from verdant_math import teaching_pilot as baseline
from verdant_math.successor_repair_adapter import adapter as repair_adapter
from verdant_math.successor_repair_evaluation import evaluation as repair_evaluation
from verdant_math.successor_repair_protocol import protocol as repair_protocol
from verdant_math.successor_retention_protocol import protocol as m
from verdant_math.successor_retention_protocol.cli import main as cli

_PUBLISHED = m._ROOT / "artifacts/terminal_successor_v066/protocol.vsrt"


@pytest.fixture(scope="module")
def protocol():
    return m.freeze_successor_retention_protocol()


def _rehash(raw):
    raw["declaration_sha256"] = baseline._sha(canonical_json_bytes(raw["declaration"]))
    return canonical_json_bytes(raw)


def test_freeze_reload_and_summary_never_load_private_checkpoint_teach_answer_grade_or_simulate(
    protocol, tmp_path, monkeypatch
):
    from verdant_obligations import AttentionPortfolio, CounterfactualRuntime, SimulationLedger

    def forbidden(*args, **kwargs):
        raise AssertionError("A retention protocol cannot load a role, teach, answer, grade or simulate")

    for module, names in (
        (repair_protocol, ("load_successor_repair_protocol",)),
        (repair_adapter, (
            "load_successor_repair_adapter", "prepare_private_successor_repair_kernel",
            "derive_successor_repaired_addition", "verify_successor_repair_derivation",
        )),
        (repair_evaluation, (
            "load_response_batch", "load_evaluation", "capture_successor_repair_responses",
            "evaluate_response_batch", "_external_grade",
        )),
    ):
        for name in names:
            if hasattr(module, name):
                monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(ClaimLearningPipeline, "record_claim", forbidden)
    monkeypatch.setattr(VerdantKernel, "apply_experience", forbidden)
    monkeypatch.setattr(VerdantKernel, "record_governance_outcome", forbidden)
    monkeypatch.setattr(CounterfactualRuntime, "execute", forbidden)
    monkeypatch.setattr(SimulationLedger, "reserve", forbidden)
    for name in ("allocate", "decide"):
        if hasattr(AttentionPortfolio, name):
            monkeypatch.setattr(AttentionPortfolio, name, forbidden)

    source = m.fresh_successor_retention_kernel()
    before = source.snapshot()
    history = tuple((m._ROOT / path).read_bytes() for path, _ in m._HISTORY)
    assert m.freeze_successor_retention_protocol(source) == protocol
    path = tmp_path / "protocol.vsrt"
    first = m.save_successor_retention_protocol(path, protocol)
    assert m.save_successor_retention_protocol(path, protocol) == first
    assert m.load_successor_retention_protocol(path) == protocol
    summary = m.protocol_summary(protocol)
    assert summary["fresh_unordered_pairs"] == 6
    assert summary["fresh_completion_bearing_cases"] == 0
    assert summary["new_successor_lessons_per_role"] == 0
    assert summary["cases_per_role"] == 20 and summary["valid_inputs_per_role"] == 12
    assert not summary["prospective_checkpoint_loaded"] and not summary["responses_observed"]
    assert source.snapshot() == before
    assert history == tuple((m._ROOT / path).read_bytes() for path, _ in m._HISTORY)


def test_static_history_validation_binds_exact_v063_v064_and_v065_chain(protocol):
    data, frozen, implementation, responses, result = m._validated_history()
    assert tuple(baseline._sha(item) for item in data) == tuple(digest for _, digest in m._HISTORY)
    assert implementation.receipt.frozen_protocol == frozen
    assert responses.receipt.frozen_protocol == frozen
    assert responses.receipt.frozen_implementation == implementation
    assert result.receipt.response_batch_receipt_sha256 == responses.receipt_sha256
    assert (
        frozen.declaration_sha256,
        implementation.receipt_sha256,
        responses.receipt_sha256,
        result.receipt_sha256,
    ) == (
        m._INTERNAL_HASHES["protocol_declaration"],
        m._INTERNAL_HASHES["implementation_receipt"],
        m._INTERNAL_HASHES["response_receipt"],
        m._INTERNAL_HASHES["evaluation_receipt"],
    )
    assert [
        len(frozen.declaration.code_sources), len(implementation.receipt.code_sources),
        len(responses.receipt.code_sources), len(result.receipt.code_sources),
    ] == [43, 46, 49, 49]


def test_published_protocol_is_exact_immutable_and_replayable(protocol):
    data = _PUBLISHED.read_bytes()
    assert len(data) == 40_121
    assert baseline._sha(data) == "d134d2762e293d7dd1374f59e8e9d5e89b584e4171b5a1748a2c7a3726c5b302"
    assert protocol.declaration_sha256 == (
        "b7b566ea65c1f6cc78045ef3e982cad2effa0aa616a6ad207e16a97380bfb0b5"
    )
    assert m.load_successor_retention_protocol(_PUBLISHED) == protocol


def test_code_manifest_preserves_all_49_v065_sources_and_adds_only_three_siblings(protocol):
    history = m._validated_history()
    prior = {source.path: source for source in history[3].receipt.code_sources}
    current = {source.path: source for source in protocol.declaration.code_sources}
    assert len(prior) == 49 and len(current) == 52
    assert all(current[path] == source for path, source in prior.items())
    assert set(current) - set(prior) == {
        "verdant_math/successor_retention_protocol/__init__.py",
        "verdant_math/successor_retention_protocol/cli.py",
        "verdant_math/successor_retention_protocol/protocol.py",
    }


def test_exact_consumed_closure_and_six_remaining_unordered_pairs(protocol):
    excluded = protocol.declaration.excluded_raw_requests
    assert len(excluded) == 183 and excluded == tuple(sorted(set(excluded)))
    assert m._available_pairs(set(excluded)) == m._AVAILABLE_UNORDERED
    assert m._AVAILABLE_UNORDERED == ((0, 15), (0, 16), (0, 17), (1, 17), (4, 18), (4, 21))
    assert tuple(map(tuple, protocol.declaration.protocol["fresh_unordered_pairs"])) == m._AVAILABLE_UNORDERED
    assert len(protocol.declaration.probe_exclusions) == 31


@pytest.mark.parametrize("pair", m._AVAILABLE_UNORDERED)
def test_each_fresh_pair_and_both_orders_are_absent_from_consumed_closure(protocol, pair):
    excluded = set(protocol.declaration.excluded_raw_requests)
    expected = {
        canonical_json_bytes({"left": pair[0], "right": pair[1]}).decode(),
        canonical_json_bytes({"left": pair[1], "right": pair[0]}).decode(),
    }
    actual = {case.raw_request_json for case in protocol.declaration.cases if case.order_pair == f"fresh-{pair[0]}-{pair[1]}"}
    assert actual == expected
    assert not actual & excluded


def test_all_20_cases_are_fixed_typed_paired_and_preserve_denominators(protocol):
    cases = protocol.declaration.cases
    assert len(cases) == 20 and len({case.raw_request_json for case in cases}) == 20
    assert {group: sum(case.group == group for case in cases) for group in (
        "retained_prerequisite_control", "retained_partial_walk",
        "declared_domain_ceiling", "invalid_input",
    )} == {
        "retained_prerequisite_control": 8,
        "retained_partial_walk": 2,
        "declared_domain_ceiling": 2,
        "invalid_input": 8,
    }
    valid = invalid = 0
    for case in cases:
        raw = json.loads(case.raw_request_json)
        try:
            m.BoundedAdditionRequestV066.model_validate(raw)
            valid += 1
        except ValueError:
            invalid += 1
            assert case.group == "invalid_input"
    assert (valid, invalid) == (12, 8)
    assert protocol.declaration.protocol["full_denominators"].startswith("20_enrolled_and_12_valid")


@pytest.mark.parametrize("index", range(8))
def test_each_invalid_payload_is_fresh_strict_and_retained(protocol, index):
    case = protocol.declaration.cases[12 + index]
    assert case.group == "invalid_input" and case.order_pair is None
    assert case.raw_request_json not in protocol.declaration.excluded_raw_requests
    with pytest.raises(ValueError):
        m.BoundedAdditionRequestV066.model_validate(json.loads(case.raw_request_json))


def test_no_fresh_completion_bearing_successor_case_exists(protocol):
    valid = [
        m.BoundedAdditionRequestV066.model_validate_json(case.raw_request_json)
        for case in protocol.declaration.cases if case.group != "invalid_input"
    ]
    pairs = {tuple(sorted((request.left, request.right))) for request in valid}
    assert pairs == set(m._AVAILABLE_UNORDERED)
    assert all(sum(pair) <= 18 for pair in pairs - {(4, 18), (4, 21)})
    # 4+18 consumes all three retained links but still has one token at 21.
    assert 18 + 4 > 21 and 21 + 4 > 21
    assert not protocol.declaration.fresh_completion_bearing_case_available
    assert "no_fresh_completion_bearing" in protocol.declaration.protocol["fresh_completion_limit"]


def test_checkpoint_lineage_reuses_exact_saved_roles_with_zero_new_lessons(protocol):
    lineage = {item.future_role: item for item in protocol.declaration.checkpoint_lineage}
    assert tuple(lineage) == m._ROLES
    assert {role: item.source_role for role, item in lineage.items()} == m._SOURCE_ROLES
    assert lineage["retained_repair"].checkpoint_sha256 == (
        "ba947a5b24512c6cd1062ccc4b19b571127a104a73974743548f42d259ccac05"
    )
    assert lineage["valid_null"].checkpoint_sha256 == lineage["retained_repair"].checkpoint_sha256
    assert lineage["no_repair_control"].checkpoint_sha256 == (
        "4f3ffe6eb3e5fd993e63666a86b3a34e3752b412eda099dff7b77b27874cc6f6"
    )
    assert lineage["wrong_link_control"].checkpoint_sha256 == (
        "de91a29db95376b2206a90f59ef671c8ea8d79a0920f326c6d5ee8fe2e7801df"
    )
    assert all(item.saved_lesson_slots == 29 for item in lineage.values())
    assert all(item.new_successor_lessons == item.new_teacher_exposures == 0 for item in lineage.values())
    assert lineage["no_repair_control"].historical_successor_claims == 0
    assert all(lineage[role].historical_successor_claims == 3 for role in (
        "retained_repair", "valid_null", "wrong_link_control"
    ))


def test_four_historical_effects_bind_native_steps_and_exact_grade_lineage(protocol):
    anchors = protocol.declaration.historical_effect_anchors
    assert len(anchors) == 4
    assert {anchor.case_ref for anchor in anchors} == {
        "math-v063:case:16", "math-v063:case:17", "math-v063:case:18", "math-v063:case:19"
    }
    assert {(anchor.original_request.left, anchor.original_request.right) for anchor in anchors} == {
        (20, 1), (1, 20), (19, 2), (2, 19)
    }
    assert {tuple((step.from_number, step.to_number) for step in anchor.retained_steps)
            for anchor in anchors} == {((20, 21),), ((19, 20), (20, 21))}
    assert all(anchor.taught_grade == "correct" and anchor.no_repair_grade == "abstained" for anchor in anchors)
    assert anchors == m._effect_anchors(m._validated_history())


def test_complete_v065_outcomes_are_preserved_without_supported_only_denominators(protocol):
    outcomes = {item.role: item for item in protocol.declaration.historical_outcomes}
    assert {role: (item.correct, item.incorrect, item.abstained, item.invalid_ungraded)
            for role, item in outcomes.items()} == {
        "taught_repair": (20, 0, 12, 8),
        "no_repair_control": (16, 0, 16, 8),
        "valid_null": (20, 0, 12, 8),
        "wrong_link_control": (16, 2, 14, 8),
    }
    assert all(item.enrolled == 40 and item.valid == 32 for item in outcomes.values())


def test_teaching_cost_controls_and_response_barrier_are_exact(protocol):
    spec = protocol.declaration.protocol
    assert spec["teaching_cost"] == {
        "saved_lesson_slots_per_role": 29,
        "new_successor_lessons_per_role": 0,
        "new_teacher_exposures_per_role": 0,
        "new_claim_installations_per_role": 0,
        "historical_correct_successor_claims_retained_or_null": 3,
        "historical_successor_claims_no_repair": 0,
        "historical_wrong_successor_claims_wrong_control": 3,
    }
    assert spec["control_difference"] == "only_the_already_saved_three_terminal_successor_slots"
    assert spec["response_order"] == (
        "all_80_native_response_or_rejection_records_saved_before_any_of_48_external_grades"
    )
    assert spec["null"].startswith("complete_retained_repair_and_valid_null")
    assert not spec["response_contract"]["sorting_retry_numeric_reconstruction_or_evaluator_arithmetic"]


def test_audit_sources_cover_every_consumed_cohort_and_adapter_probe_file(protocol):
    assert tuple(source.path for source in protocol.declaration.audit_sources) == m._AUDIT_FILES
    for source in protocol.declaration.audit_sources:
        assert source.sha256 == baseline._sha((m._ROOT / source.path).read_bytes())
    assert tuple(protocol.declaration.probe_exclusions) == m._validated_history()[1].declaration.probe_exclusions


def test_fresh_native_checkpoint_and_mapping_order_reload_are_exact(protocol, tmp_path):
    source = m.fresh_successor_retention_kernel()
    path = tmp_path / "fresh.vdk"
    save_checkpoint(path, source.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))
    for name in ("concepts", "claims", "evidence"):
        setattr(restored.state, name, dict(reversed(tuple(getattr(restored.state, name).items()))))
    assert m.freeze_successor_retention_protocol(restored) == protocol
    assert not restored.state.claims and not restored.state.governance_outcomes
    assert not restored.state.obligation_attention_decisions and not restored.state.obligation_kernels
    assert not restored.state.revisions


@pytest.mark.parametrize("kind", ("foreign", "historical", "drifted"))
def test_foreign_historical_or_stale_source_cannot_be_frozen(kind):
    if kind == "foreign":
        source = VerdantKernel(seed=66, state_dim=16)
    elif kind == "historical":
        history = m._validated_history()
        source = baseline._checkpoint(
            history[1].declaration.source_checkpoint_base64,
            history[1].declaration.source_checkpoint_sha256,
        )
    else:
        source = m.fresh_successor_retention_kernel()
        source.state.cycle = 1
    before = source.snapshot()
    with pytest.raises(ValueError, match="fresh"):
        m.freeze_successor_retention_protocol(source)
    assert source.snapshot() == before


@pytest.mark.parametrize("attack", (
    "version", "parent", "tree", "source", "cohorts", "domain", "testimony", "operation",
    "checkpoint_role", "prerequisite", "control", "cost_slots", "cost_new_lessons",
    "cost_exposures", "cost_claims", "cost_historical", "freshness", "fresh_pairs",
    "completion_limit", "input", "records", "original", "effective", "evidence",
    "behavioral_input", "fallback", "case_count", "accepted", "invalid_count",
    "response_order", "scoring", "invalid_handling", "missing_handling", "denominator",
    "null", "next", "teacher", "trust", "retune", "canonical", "attention", "simulation",
    "case", "case_order", "case_group", "case_pair", "case_type", "drop_invalid", "duplicate",
    "lineage_role", "lineage_source", "lineage_checkpoint", "lineage_fingerprint",
    "lineage_lessons", "lineage_cost", "lineage_new_lesson", "anchor_case", "anchor_request",
    "anchor_response", "anchor_grade", "anchor_step", "anchor_expected", "outcome",
    "artifact_hash", "artifact_path", "audit", "probe", "exclusions", "manifest",
    "fingerprint", "checkpoint", "completion_flag", "future_answers", "future_grades",
))
def test_fully_rehashed_cost_case_checkpoint_lineage_source_or_authority_forgery_fails(
    protocol, tmp_path, attack
):
    raw = protocol.model_dump(mode="json")
    declaration = raw["declaration"]
    spec = declaration["protocol"]
    contract = spec["response_contract"]
    cost = spec["teaching_cost"]
    if attack == "version": spec["version"] = "retuned"
    elif attack == "parent": spec["grounded_parent_commit"] = "0" * 40
    elif attack == "tree": spec["grounded_parent_tree"] = "0" * 40
    elif attack == "source": spec["source"] = "foreign"
    elif attack == "cohorts": spec["consumed_cohorts"].pop()
    elif attack == "domain": spec["bounded_domain"] = "zero_through_twenty_two"
    elif attack == "testimony": spec["retained_testimony"] = "derive_from_integers"
    elif attack == "operation": spec["retention_operation"] = "install_new_lessons"
    elif attack == "checkpoint_role": spec["checkpoint_roles"]["retained_repair"] = "foreign"
    elif attack == "prerequisite": spec["shared_prerequisites"] = "changed_addition_rule"
    elif attack == "control": spec["control_difference"] = "change_order_rule"
    elif attack == "cost_slots": cost["saved_lesson_slots_per_role"] = 28
    elif attack == "cost_new_lessons": cost["new_successor_lessons_per_role"] = 1
    elif attack == "cost_exposures": cost["new_teacher_exposures_per_role"] = 1
    elif attack == "cost_claims": cost["new_claim_installations_per_role"] = 1
    elif attack == "cost_historical": cost["historical_correct_successor_claims_retained_or_null"] = 2
    elif attack == "freshness": spec["freshness_audit"] = "partial"
    elif attack == "fresh_pairs": spec["fresh_unordered_pairs"].pop()
    elif attack == "completion_limit": spec["fresh_completion_limit"] = "fresh_success_available"
    elif attack == "input": spec["input_contract"] = "include_expected_answer"
    elif attack == "records": contract["records_per_role"] = 12
    elif attack == "original": contract["original_request"] = "sorted"
    elif attack == "effective": contract["effective_request"] = "recursive_retry"
    elif attack == "evidence": contract["native_evidence"] = []
    elif attack == "behavioral_input": contract["behavioral_inputs_excluded"].pop()
    elif attack == "fallback": contract["sorting_retry_numeric_reconstruction_or_evaluator_arithmetic"] = True
    elif attack == "case_count": spec["cases_per_role"] = 19
    elif attack == "accepted": spec["accepted_inputs_per_role"] = 11
    elif attack == "invalid_count": spec["invalid_inputs_per_role"] = 7
    elif attack == "response_order": spec["response_order"] = "grade_immediately"
    elif attack == "scoring": spec["scoring"] = "feed_answers_to_response"
    elif attack == "invalid_handling": spec["invalid_handling"] = "drop_invalid"
    elif attack == "missing_handling": spec["missing_handling"] = "retry_missing"
    elif attack == "denominator": spec["full_denominators"] = "successful_only"
    elif attack == "null": spec["null"] = "allow_divergence"
    elif attack == "next": spec["next_dependency"] = "widen_domain_now"
    elif attack == "teacher": spec["teacher_source_class"] = "authenticated"
    elif attack == "trust": spec["trust_limits"] = "hashes_authenticate_truth"
    elif attack == "retune": spec["outcome_conditioned_selection_tuning_or_replacement_permitted"] = True
    elif attack == "canonical": spec["canonical_input_mutation_permitted"] = True
    elif attack == "attention": spec["attention_allocation_permitted"] = True
    elif attack == "simulation": spec["obligation_simulation_permitted"] = True
    elif attack == "case": declaration["cases"][0]["raw_request_json"] = '{"left":9,"right":3}'
    elif attack == "case_order": declaration["cases"].reverse()
    elif attack == "case_group": declaration["cases"][0]["group"] = "retained_partial_walk"
    elif attack == "case_pair": declaration["cases"][0]["order_pair"] = "foreign"
    elif attack == "case_type": declaration["cases"][-1]["raw_request_json"] = '{"left":0,"right":15}'
    elif attack == "drop_invalid": declaration["cases"].pop()
    elif attack == "duplicate": declaration["cases"][1] = declaration["cases"][0]
    elif attack == "lineage_role": declaration["checkpoint_lineage"][0]["future_role"] = "valid_null"
    elif attack == "lineage_source": declaration["checkpoint_lineage"][0]["source_role"] = "no_repair_control"
    elif attack == "lineage_checkpoint": declaration["checkpoint_lineage"][0]["checkpoint_sha256"] = "0" * 64
    elif attack == "lineage_fingerprint": declaration["checkpoint_lineage"][0]["kernel_fingerprint"] = "0" * 64
    elif attack == "lineage_lessons": declaration["checkpoint_lineage"][0]["lesson_trace_sha256"] = "0" * 64
    elif attack == "lineage_cost": declaration["checkpoint_lineage"][0]["historical_successor_claims"] = 2
    elif attack == "lineage_new_lesson": declaration["checkpoint_lineage"][0]["new_successor_lessons"] = 1
    elif attack == "anchor_case": declaration["historical_effect_anchors"][0]["case_ref"] = "foreign"
    elif attack == "anchor_request": declaration["historical_effect_anchors"][0]["original_request"] = {"left": 18, "right": 3}
    elif attack == "anchor_response": declaration["historical_effect_anchors"][0]["taught_response_sha256"] = "0" * 64
    elif attack == "anchor_grade": declaration["historical_effect_anchors"][0]["taught_grade_sha256"] = "0" * 64
    elif attack == "anchor_step": declaration["historical_effect_anchors"][0]["retained_steps"][0]["to_number"] = 20
    elif attack == "anchor_expected": declaration["historical_effect_anchors"][0]["expected_answer"] = 20
    elif attack == "outcome": declaration["historical_outcomes"][0]["correct"] = 21
    elif attack == "artifact_hash": declaration["prior_artifacts"][0]["sha256"] = "0" * 64
    elif attack == "artifact_path": declaration["prior_artifacts"][0]["path"] = declaration["prior_artifacts"][1]["path"]
    elif attack == "audit": declaration["audit_sources"][0]["sha256"] = "0" * 64
    elif attack == "probe": declaration["probe_exclusions"].pop()
    elif attack == "exclusions": declaration["excluded_raw_requests"].pop()
    elif attack == "manifest": declaration["code_sources"][-1]["sha256"] = "0" * 64
    elif attack == "fingerprint": declaration["source_kernel_fingerprint"] = "0" * 64
    elif attack == "checkpoint":
        data = checkpoint_bytes(VerdantKernel(seed=123, state_dim=16).snapshot())
        declaration["source_checkpoint_base64"] = base64.b64encode(data).decode()
        declaration["source_checkpoint_sha256"] = baseline._sha(data)
    elif attack == "completion_flag": declaration["fresh_completion_bearing_case_available"] = True
    elif attack == "future_answers": declaration["answers"] = [18] * 20
    elif attack == "future_grades": declaration["grades"] = ["correct"] * 20
    path = tmp_path / f"forged-{attack}.vsrt"
    path.write_bytes(_rehash(raw))
    with pytest.raises((ValueError, RuntimeError)):
        m.load_successor_retention_protocol(path)


@pytest.mark.parametrize("flag", m._FALSE_FLAGS)
def test_rehashed_execution_effect_discovery_physical_or_canonical_flags_fail(protocol, tmp_path, flag):
    raw = protocol.model_dump(mode="json")
    raw["declaration"][flag] = True
    path = tmp_path / f"authority-{flag}.vsrt"
    path.write_bytes(_rehash(raw))
    with pytest.raises(ValueError):
        m.load_successor_retention_protocol(path)
    bypass = protocol.model_copy(update={
        "declaration": protocol.declaration.model_copy(update={flag: True})
    })
    with pytest.raises(ValueError):
        m.save_successor_retention_protocol(tmp_path / f"bypass-{flag}.vsrt", bypass)


@pytest.mark.parametrize("index", range(4))
def test_changed_historical_artifact_fails_even_if_content_is_rehashed(index, monkeypatch):
    target, _ = m._HISTORY[index]
    read = m._read

    def altered(path):
        data = read(path)
        if Path(path) == m._ROOT / target:
            raw = json.loads(data)
            raw["substituted_history"] = True
            return canonical_json_bytes(raw)
        return data

    monkeypatch.setattr(m, "_read", altered)
    with pytest.raises(ValueError, match="artifact changed"):
        m.freeze_successor_retention_protocol()


@pytest.mark.parametrize("index", range(10))
def test_rehashed_audit_source_substitution_fails_exact_reconstruction(protocol, tmp_path, index):
    raw = protocol.model_dump(mode="json")
    raw["declaration"]["audit_sources"][index]["sha256"] = "0" * 64
    path = tmp_path / f"audit-{index}.vsrt"
    path.write_bytes(_rehash(raw))
    with pytest.raises(ValueError):
        m.load_successor_retention_protocol(path)


@pytest.mark.parametrize("scope", ("manifest", "audit", "source", "history"))
def test_drift_during_freeze_fails_without_partial_publication(scope, monkeypatch, tmp_path):
    source = m.fresh_successor_retention_kernel()
    if scope == "manifest":
        original, calls = m._code_manifest, 0

        def changed(history):
            nonlocal calls
            calls += 1
            result = original(history)
            return result if calls == 1 else result[:-1]

        monkeypatch.setattr(m, "_code_manifest", changed)
    elif scope == "audit":
        original, calls = m._read, 0

        def changed(path):
            nonlocal calls
            result = original(path)
            if Path(path) == m._ROOT / m._AUDIT_FILES[0]:
                calls += 1
                return result if calls == 1 else result + b"\n# later audit drift\n"
            return result

        monkeypatch.setattr(m, "_read", changed)
    elif scope == "source":
        original = m.checkpoint_bytes

        def changed(state):
            result = original(state)
            source.state.cycle = 1
            return result

        monkeypatch.setattr(m, "checkpoint_bytes", changed)
    else:
        original, calls = m._validated_history, 0

        def changed():
            nonlocal calls
            calls += 1
            result = original()
            if calls == 1:
                return result
            return ((result[0][0] + b" ", *result[0][1:]), *result[1:])

        monkeypatch.setattr(m, "_validated_history", changed)
    with pytest.raises(ValueError, match="changed during"):
        m.freeze_successor_retention_protocol(source)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("kind", ("bad_hash", "duplicate_key", "noncanonical", "oversized", "missing"))
def test_noncanonical_corrupt_duplicate_oversized_or_missing_inputs_fail(protocol, tmp_path, kind):
    path = tmp_path / f"bad-{kind}.vsrt"
    if kind == "bad_hash":
        raw = protocol.model_dump(mode="json")
        raw["declaration_sha256"] = "0" * 64
        path.write_bytes(canonical_json_bytes(raw))
    elif kind == "duplicate_key":
        path.write_text('{"declaration":{},"declaration":{}}')
    elif kind == "noncanonical":
        path.write_text(json.dumps(protocol.model_dump(mode="json"), indent=2))
    elif kind == "oversized":
        path.write_bytes(b" " * (m._MAX_BYTES + 1))
    with pytest.raises((ValueError, OSError, RuntimeError)):
        m.load_successor_retention_protocol(path)


@pytest.mark.parametrize("index", range(4))
def test_publication_cannot_replace_historical_evidence(protocol, index):
    path = m._ROOT / m._HISTORY[index][0]
    before = path.read_bytes()
    with pytest.raises(ValueError, match="retention evidence"):
        m.save_successor_retention_protocol(path, protocol)
    assert path.read_bytes() == before


@pytest.mark.parametrize("path", (*m._AUDIT_FILES,
    "verdant_math/successor_retention_protocol/__init__.py",
    "verdant_math/successor_retention_protocol/cli.py",
    "verdant_math/successor_retention_protocol/protocol.py",
))
def test_protocol_writer_protects_audit_and_code_files(protocol, path):
    target = m._ROOT / path
    before = target.read_bytes()
    with pytest.raises(ValueError, match="audit or code"):
        m.save_successor_retention_protocol(target, protocol)
    assert target.read_bytes() == before


def test_immutable_paths_and_failed_replace_preserve_prior_bytes(protocol, tmp_path, monkeypatch):
    occupied = tmp_path / "occupied.vsrt"
    occupied.write_bytes(b"protected prior evidence")
    with pytest.raises(RuntimeError, match="different evidence"):
        m.save_successor_retention_protocol(occupied, protocol)
    assert occupied.read_bytes() == b"protected prior evidence"
    target = tmp_path / "failure.vsrt"

    def fail(*args, **kwargs):
        raise OSError("injected pre-replace failure")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError, match="pre-replace"):
        m.save_successor_retention_protocol(target, protocol)
    assert not target.exists() and not tuple(tmp_path.glob(".*.tmp"))


def test_symlink_cannot_bypass_historical_input_protection(protocol, tmp_path):
    source = m._ROOT / m._HISTORY[2][0]
    before = source.read_bytes()
    alias = tmp_path / "aliased.vsrt"
    alias.symlink_to(source)
    with pytest.raises(ValueError, match="retention evidence"):
        m.save_successor_retention_protocol(alias, protocol)
    assert alias.is_symlink() and source.read_bytes() == before


def test_cli_has_only_freeze_and_replay_without_run_query_evaluate_or_grade(tmp_path, capsys):
    path = tmp_path / "cli.vsrt"
    assert cli(["freeze", str(path)]) == 0
    frozen = json.loads(capsys.readouterr().out)
    assert frozen["fresh_completion_bearing_cases"] == 0
    assert not frozen["prospective_runner_implemented"] and not frozen["responses_observed"]
    assert cli(["replay", str(path)]) == 0
    replayed = json.loads(capsys.readouterr().out)
    assert replayed["declaration_sha256"] == frozen["declaration_sha256"]
    assert cli(["replay", str(tmp_path / "missing")]) == 2
    capsys.readouterr()
    for command in ("run", "query", "respond", "evaluate", "grade"):
        with pytest.raises(SystemExit):
            cli([command, str(path)])


def test_frozen_protocol_contains_no_responses_grades_or_new_lessons(protocol):
    raw = protocol.declaration.model_dump(mode="json")
    assert "responses" not in raw and "grades" not in raw and "answers" not in raw
    assert raw["protocol"]["teaching_cost"]["new_successor_lessons_per_role"] == 0
    assert not raw["prospective_checkpoint_loaded"]
    assert not raw["prospective_cohort_executed"]
    assert not raw["retained_reuse_observed"]


def test_physical_and_negative_boundaries_remain_explicitly_absent(protocol):
    declaration = protocol.declaration
    assert not declaration.physical_evidence_admissible
    assert not declaration.harm_scoring_implemented
    assert not declaration.causal_self_repair_observed
    assert not declaration.independent_replication_observed
    assert not declaration.resolution_authority_enabled
    assert not declaration.promotion_authority_enabled
    assert not declaration.policy_rewrite_authority_enabled


def test_next_dependency_cannot_silently_widen_or_recycle(protocol):
    next_dependency = protocol.declaration.protocol["next_dependency"]
    assert "partial_trace_retention_only" in next_dependency
    assert "pause" in next_dependency
    assert "without_recycling_or_widening" in next_dependency
