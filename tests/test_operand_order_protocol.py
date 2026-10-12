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
from verdant_math.counting import pilot as counting
from verdant_math.addition import pilot as addition
from verdant_math.coverage import challenge as coverage
from verdant_math.ordering_protocol import protocol as m
from verdant_math.ordering_protocol.cli import main as cli


@pytest.fixture(scope="module")
def protocol():
    return m.freeze_operand_order_protocol()


def _rehash(raw):
    raw["declaration_sha256"] = baseline._sha(canonical_json_bytes(raw["declaration"]))
    return canonical_json_bytes(raw)


def test_freeze_reload_and_summary_never_teach_answer_grade_or_simulate(protocol, tmp_path, monkeypatch):
    from verdant_obligations import AttentionPortfolio, CounterfactualRuntime, SimulationLedger

    def forbidden(*args, **kwargs):
        raise AssertionError("A prospective protocol cannot execute a lesson, query, grade or simulation")

    for module, names in ((baseline, ("_teach", "recall_addition_fact", "_grade", "run_math_teaching_pilot")),
        (counting, ("_teach", "count_forward", "_grade", "run_counting_pilot")),
        (addition, ("_teach", "derive_addition", "_grade", "run_addition_pilot")),
        (coverage, ("_respond", "_evaluate", "run_coverage_challenge"))):
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
    source = m.fresh_order_kernel()
    before, old_bytes = source.snapshot(), tuple((m._ROOT / p).read_bytes() for p, _ in m._HISTORY)
    assert m.freeze_operand_order_protocol(source) == protocol
    p = tmp_path / "prospective.vaop"
    first = m.save_operand_order_protocol(p, protocol)
    assert m.save_operand_order_protocol(p, protocol) == first
    assert m.load_operand_order_protocol(p) == protocol
    summary = m.protocol_summary(protocol)
    assert summary["cases_per_role"] == 40 and not summary["responses_observed"]
    assert not summary["adapter_implemented"] and not summary["evaluation_completed"]
    assert source.snapshot() == before
    assert old_bytes == tuple((m._ROOT / p).read_bytes() for p, _ in m._HISTORY)


def test_all_case_orders_are_fresh_from_all_four_cohorts_and_observed_rejections(protocol):
    p = protocol.declaration
    excluded = set(p.excluded_raw_requests)
    assert canonical_json_bytes(dict(left=10, right=1)).decode() in excluded
    assert canonical_json_bytes(dict(left=5, right=5)).decode() in excluded
    assert canonical_json_bytes(dict(left=18, right=0)).decode() in excluded
    assert len(p.probe_exclusions) == 26
    assert {c.group: sum(other.group == c.group for other in p.cases) for c in p.cases} == dict(
        original_mapping=8, swap_candidate=8, both_mappings_absent=8, terminal_link=8, invalid_input=8)
    assert len({c.raw_request_json for c in p.cases}) == 40
    for c in p.cases:
        raw = json.loads(c.raw_request_json)
        assert c.raw_request_json not in excluded
        if set(raw) == {"left", "right"}:
            assert canonical_json_bytes(dict(left=raw["right"], right=raw["left"])).decode() not in excluded
    for case, reversed_case in zip(p.cases[:8], p.cases[8:16]):
        a, b = json.loads(case.raw_request_json), json.loads(reversed_case.raw_request_json)
        assert case.order_pair == reversed_case.order_pair
        assert (a["left"], a["right"]) == (b["right"], b["left"])


def test_instructions_keep_original_order_and_gate_swap_on_absence_only(protocol):
    s = protocol.declaration.protocol
    instruction = s["instruction"]
    assert instruction["correct_trigger"] == "original_right_lookup_missing_and_original_left_mapping_valid"
    assert instruction["maximum_swaps"] == 1 and not instruction["sorting_or_recursive_retry_permitted"]
    assert "abstain_never_swap" in instruction["right_conflicting_invalid_or_unsupported"]
    assert instruction["source_class"] == "human_testimony"
    assert instruction["authority_scope"] == "read_only_private_operand_routing_only"
    assert instruction["no_instruction"] == "reuse_original_order_addition_with_existing_addition_instruction"
    assert s["control_difference"] == "only_the_26th_instruction_slot_not_the_existing_addition_rule"
    assert "original_request_only" in s["scoring"]
    assert s["response_order"] == "all_160_records_before_any_of_128_external_grades"
    contract = s["response_contract"]
    assert contract["original_request"] == "exact_validated_original_order_never_overwritten"
    assert contract["no_fallback_arithmetic"] and not contract["case_labels_expected_answers_or_grades_permitted"]
    assert "answer_none" in contract["terminal_failure"]


def test_all_legacy_source_manifests_and_exact_artifact_pairing_are_preserved(protocol):
    priors = m._prior_data()
    assert [len(priors[i]["receipt"]["code_sources"]) for i in range(3)] == [22, 25, 28]
    assert len(priors[3]["plan"]["code_sources"]) == 31
    assert priors[4]["receipt"]["frozen_plan"] == priors[3]
    assert len(protocol.declaration.code_sources) == 34
    assert len(protocol.declaration.prior_artifacts) == 5
    assert [s.path for s in protocol.declaration.probe_sources] == list(m._PROBE_FILES)
    for s in protocol.declaration.code_sources:
        assert s.sha256 == baseline._sha((m._ROOT / s.path).read_bytes())


def test_native_checkpoint_and_mapping_order_reload_are_exact(protocol, tmp_path):
    source = m.fresh_order_kernel()
    path = tmp_path / "fresh.vdk"
    save_checkpoint(path, source.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))
    for name in ("concepts", "claims", "evidence"):
        setattr(restored.state, name, dict(reversed(tuple(getattr(restored.state, name).items()))))
    assert m.freeze_operand_order_protocol(restored) == protocol
    assert not restored.state.council_decisions and not restored.state.governance_outcomes
    assert not restored.state.obligation_attention_decisions and not restored.state.obligation_kernels
    assert not restored.state.revisions and not restored.state.claims


@pytest.mark.parametrize("kind", ("foreign", "historical", "drifted"))
def test_foreign_exposed_or_stale_source_cannot_be_frozen(protocol, kind):
    if kind == "foreign":
        source = VerdantKernel(seed=11, state_dim=16)
    elif kind == "historical":
        r = m._prior_data()[2]["receipt"]
        source = baseline._checkpoint(r["arms"][0]["checkpoint_base64"], r["arms"][0]["checkpoint_sha256"])
    else:
        source = m.fresh_order_kernel()
        source.state.cycle = 1
    before = source.snapshot()
    with pytest.raises(ValueError, match="fresh"):
        m.freeze_operand_order_protocol(source)
    assert source.snapshot() == before


@pytest.mark.parametrize("attack", (
    "version", "parent", "trigger", "right_conflict", "left_conflict", "sorting", "swap_limit",
    "incorrect_instruction", "teacher_source", "teacher_authority", "no_instruction", "control_slot",
    "null", "response_bound", "provenance", "original_order", "fallback", "target_access",
    "scoring", "denominator", "grade_timing", "missing", "invalid", "retune", "simulation",
    "cases", "case_order", "case_group", "case_pair", "case_type", "drop_invalid", "duplicate",
    "exclusions", "probe_exclusion", "probe_manifest", "manifest", "artifact_hash", "artifact_path",
    "fingerprint", "checkpoint", "future_answers", "future_grades",
))
def test_rehashed_instruction_control_case_scoring_provenance_and_source_forgery_fails(protocol, tmp_path, attack):
    raw = protocol.model_dump(mode="json")
    d, s = raw["declaration"], raw["declaration"]["protocol"]
    instruction, contract = s["instruction"], s["response_contract"]
    if attack == "version": s["version"] = "retuned"
    elif attack == "parent": s["grounded_parent_commit"] = "0" * 40
    elif attack == "trigger": instruction["correct_trigger"] = "sort_by_numeric_value"
    elif attack == "right_conflict": instruction["right_conflicting_invalid_or_unsupported"] = "swap"
    elif attack == "left_conflict": instruction["correct_left_missing_conflicting_invalid_or_unsupported"] = "default_tokens"
    elif attack == "sorting": instruction["sorting_or_recursive_retry_permitted"] = True
    elif attack == "swap_limit": instruction["maximum_swaps"] = 2
    elif attack == "incorrect_instruction": instruction["incorrect_label"] = instruction["correct_label"]
    elif attack == "teacher_source": instruction["source_class"] = "physical_outcome"
    elif attack == "teacher_authority": instruction["authority_scope"] = "canonical_policy_rewrite"
    elif attack == "no_instruction": instruction["no_instruction"] = "withhold_all_addition_lessons"
    elif attack == "control_slot": s["control_difference"] = "change_all_lessons"
    elif attack == "null": s["valid_null"] = "approximate_output_only"
    elif attack == "response_bound": contract["maximum_records_per_role"] = 39
    elif attack == "provenance": contract["provenance"] = []
    elif attack == "original_order": contract["original_request"] = "replace_with_sorted_request"
    elif attack == "fallback": contract["no_fallback_arithmetic"] = False
    elif attack == "target_access": contract["case_labels_expected_answers_or_grades_permitted"] = True
    elif attack == "scoring": s["scoring"] = "grade_effective_operands"
    elif attack == "denominator": s["full_denominators"] = "successful_answers_only"
    elif attack == "grade_timing": s["response_order"] = "grade_then_reply"
    elif attack == "missing": s["missing_handling"] = "replace_failed_cases"
    elif attack == "invalid": s["invalid_handling"] = "drop_invalid_payloads"
    elif attack == "retune": s["adaptation_replacement_or_metric_tuning_permitted"] = True
    elif attack == "simulation": s["simulation_execution_permitted"] = True
    elif attack == "cases": d["cases"][0]["raw_request_json"] = canonical_json_bytes(dict(left=13,right=1)).decode()
    elif attack == "case_order": d["cases"].reverse()
    elif attack == "case_group": d["cases"][0]["group"] = "swap_candidate"
    elif attack == "case_pair": d["cases"][0]["order_pair"] = "foreign-pair"
    elif attack == "case_type": d["cases"][32]["raw_request_json"] = canonical_json_bytes(dict(left=12,right=1)).decode()
    elif attack == "drop_invalid": d["cases"].pop()
    elif attack == "duplicate": d["cases"][1] = d["cases"][0]
    elif attack == "exclusions": d["excluded_raw_requests"].pop()
    elif attack == "probe_exclusion": d["probe_exclusions"].pop()
    elif attack == "probe_manifest": d["probe_sources"][0]["sha256"] = "0" * 64
    elif attack == "manifest": d["code_sources"][0]["sha256"] = "0" * 64
    elif attack == "artifact_hash": d["prior_artifacts"][0]["sha256"] = "0" * 64
    elif attack == "artifact_path": d["prior_artifacts"][0]["path"] = d["prior_artifacts"][1]["path"]
    elif attack == "fingerprint": d["source_kernel_fingerprint"] = "0" * 64
    elif attack == "checkpoint":
        b = checkpoint_bytes(VerdantKernel(seed=123,state_dim=16).snapshot())
        d["source_checkpoint_base64"], d["source_checkpoint_sha256"] = base64.b64encode(b).decode(), baseline._sha(b)
    elif attack == "future_answers": d["answers"] = [0] * 40
    elif attack == "future_grades": d["grades"] = ["correct"] * 40
    path = tmp_path / "forged.vaop"
    path.write_bytes(_rehash(raw))
    with pytest.raises((ValueError, RuntimeError)):
        m.load_operand_order_protocol(path)


@pytest.mark.parametrize("flag", m._FALSE_FLAGS)
def test_rehashed_execution_learning_physical_or_canonical_flags_fail(protocol, tmp_path, flag):
    raw = protocol.model_dump(mode="json")
    raw["declaration"][flag] = True
    path = tmp_path / "authority.vaop"
    path.write_bytes(_rehash(raw))
    with pytest.raises(ValueError):
        m.load_operand_order_protocol(path)
    bypass = protocol.model_copy(update={"declaration": protocol.declaration.model_copy(update={flag: True})})
    with pytest.raises(ValueError):
        m.save_operand_order_protocol(tmp_path / "bypassed.vaop", bypass)


@pytest.mark.parametrize("index", range(5))
def test_changed_historical_artifact_fails_even_if_its_inner_hash_is_recomputed(index, monkeypatch):
    target, _ = m._HISTORY[index]
    read = m._read
    def altered(path):
        data = read(path)
        if Path(path) == m._ROOT / target:
            raw = json.loads(data)
            key = "plan" if "plan" in raw else "receipt"
            raw[key]["purpose"] = "substituted_history"
            hash_key = "plan_sha256" if key == "plan" else "receipt_sha256"
            raw[hash_key] = baseline._sha(canonical_json_bytes(raw[key]))
            return canonical_json_bytes(raw)
        return data
    monkeypatch.setattr(m, "_read", altered)
    with pytest.raises(ValueError, match="historical artifact"):
        m.freeze_operand_order_protocol()


@pytest.mark.parametrize("scope", ("manifest", "probe", "source"))
def test_drift_during_freeze_fails_without_partial_publication(scope, monkeypatch, tmp_path):
    source = m.fresh_order_kernel()
    if scope == "manifest":
        original, calls = m._code_manifest, 0
        def changed():
            nonlocal calls
            calls += 1
            r = original()
            return r if calls == 1 else r[:-1]
        monkeypatch.setattr(m, "_code_manifest", changed)
    elif scope == "probe":
        original, calls = m._read, 0
        def changed(path):
            nonlocal calls
            r = original(path)
            if Path(path) == m._ROOT / m._PROBE_FILES[0]:
                calls += 1
                return r if calls == 1 else r + b"\n# later observed probe\n"
            return r
        monkeypatch.setattr(m, "_read", changed)
    else:
        original = m.checkpoint_bytes
        def changed(state):
            r = original(state)
            source.state.cycle = 1
            return r
        monkeypatch.setattr(m, "checkpoint_bytes", changed)
    with pytest.raises(ValueError, match="changed during"):
        m.freeze_operand_order_protocol(source)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("kind", ("bad_hash", "duplicate_key", "noncanonical", "oversized", "missing"))
def test_noncanonical_corrupt_duplicate_oversized_or_missing_inputs_fail(protocol, tmp_path, kind):
    path = tmp_path / "bad.vaop"
    if kind == "bad_hash":
        raw = protocol.model_dump(mode="json"); raw["declaration_sha256"] = "0" * 64
        path.write_bytes(canonical_json_bytes(raw))
    elif kind == "duplicate_key": path.write_text('{"declaration":{},"declaration":{}}')
    elif kind == "noncanonical": path.write_text(json.dumps(protocol.model_dump(mode="json"),indent=2))
    elif kind == "oversized": path.write_bytes(b" " * (m._MAX_BYTES + 1))
    with pytest.raises((ValueError, OSError, RuntimeError)):
        m.load_operand_order_protocol(path)


@pytest.mark.parametrize("index", range(5))
def test_publication_cannot_replace_historical_evidence(protocol, index):
    path = m._ROOT / m._HISTORY[index][0]
    before = path.read_bytes()
    with pytest.raises(ValueError, match="input evidence"):
        m.save_operand_order_protocol(path, protocol)
    assert path.read_bytes() == before


def test_immutable_paths_and_failed_replace_preserve_prior_bytes(protocol, tmp_path, monkeypatch):
    occupied = tmp_path / "occupied.vaop"; occupied.write_bytes(b"protected prior evidence")
    with pytest.raises(RuntimeError, match="different evidence"):
        m.save_operand_order_protocol(occupied, protocol)
    assert occupied.read_bytes() == b"protected prior evidence"
    target = tmp_path / "failure.vaop"
    def fail(*args, **kwargs):
        raise OSError("injected pre-replace failure")
    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError, match="pre-replace"):
        m.save_operand_order_protocol(target, protocol)
    assert not target.exists()
    assert not tuple(tmp_path.glob(".*.tmp"))


def test_cli_has_only_freeze_and_replay_with_no_adapter_or_run(tmp_path, capsys):
    path = tmp_path / "cli.vaop"
    assert cli(["freeze", str(path)]) == 0
    assert not json.loads(capsys.readouterr().out)["responses_observed"]
    assert cli(["replay", str(path)]) == 0
    assert not json.loads(capsys.readouterr().out)["adapter_implemented"]
    assert cli(["replay", str(tmp_path / "missing")]) == 2
    capsys.readouterr()
    with pytest.raises(SystemExit):
        cli(["run", str(path)])


@pytest.mark.parametrize("path", (*m._PROBE_FILES, "verdant_math/teaching_pilot.py",
    "verdant_math/counting/pilot.py", "verdant_math/addition/pilot.py"))
def test_protocol_writer_protects_source_code_and_recorded_probe_files(protocol, path):
    target = m._ROOT / path
    before = target.read_bytes()
    with pytest.raises(ValueError, match="input evidence or code"):
        m.save_operand_order_protocol(target, protocol)
    assert target.read_bytes() == before


def test_a_symlink_cannot_bypass_historical_input_protection(protocol, tmp_path):
    source = m._ROOT / m._HISTORY[0][0]
    before = source.read_bytes()
    alias = tmp_path / "aliased.vaop"
    alias.symlink_to(source)
    with pytest.raises(ValueError, match="input evidence"):
        m.save_operand_order_protocol(alias, protocol)
    assert alias.is_symlink() and source.read_bytes() == before


def test_each_unchanged_component_manifest_is_rechecked_without_queries(monkeypatch):
    for module in (baseline, counting, addition, coverage):
        with monkeypatch.context() as patch:
            original = module._code_manifest
            patch.setattr(module, "_code_manifest", lambda original=original: original()[:-1])
            with pytest.raises(ValueError, match="preserved math implementation"):
                m.freeze_operand_order_protocol()
