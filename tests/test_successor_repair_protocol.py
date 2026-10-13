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
from verdant_math.addition import pilot as addition
from verdant_math.counting import pilot as counting
from verdant_math.ordering_adapter import adapter
from verdant_math.ordering_evaluation import evaluation
from verdant_math.ordering_protocol import protocol as ordering
from verdant_math.successor_repair_protocol import protocol as m
from verdant_math.successor_repair_protocol.cli import main as cli

_PUBLISHED = m._ROOT / "artifacts/terminal_successor_v063/protocol.vsrp"


@pytest.fixture(scope="module")
def protocol():
    return m.freeze_successor_repair_protocol()


def _rehash(raw):
    raw["declaration_sha256"] = baseline._sha(canonical_json_bytes(raw["declaration"]))
    return canonical_json_bytes(raw)


def test_freeze_reload_and_summary_never_teach_answer_grade_or_simulate(protocol, tmp_path, monkeypatch):
    from verdant_obligations import AttentionPortfolio, CounterfactualRuntime, SimulationLedger

    def forbidden(*args, **kwargs):
        raise AssertionError("A protocol-only repair declaration cannot teach, answer, grade or simulate")

    for module, names in (
        (baseline, ("_teach", "recall_addition_fact", "_grade", "run_math_teaching_pilot")),
        (counting, ("_teach", "count_forward", "_grade", "run_counting_pilot")),
        (addition, ("_teach", "derive_addition", "_grade", "run_addition_pilot")),
        (adapter, ("prepare_private_operand_order_kernel", "derive_ordered_addition")),
        (evaluation, ("capture_operand_order_responses", "evaluate_response_batch", "_score")),
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

    source = m.fresh_successor_repair_kernel()
    before = source.snapshot()
    old_bytes = tuple((m._ROOT / path).read_bytes() for path, _ in m._HISTORY)
    assert m.freeze_successor_repair_protocol(source) == protocol
    path = tmp_path / "protocol.vsrp"
    first = m.save_successor_repair_protocol(path, protocol)
    assert m.save_successor_repair_protocol(path, protocol) == first
    assert m.load_successor_repair_protocol(path) == protocol
    summary = m.protocol_summary(protocol)
    assert summary["historical_missing_successor_anchors"] == 8
    assert summary["proposed_domain_maximum"] == 21
    assert summary["cases_per_role"] == 40 and summary["valid_inputs_per_role"] == 32
    assert not summary["repair_adapter_implemented"] and not summary["responses_observed"]
    assert source.snapshot() == before
    assert old_bytes == tuple((m._ROOT / path).read_bytes() for path, _ in m._HISTORY)


def test_exact_v060_v061_v062_bytes_pairing_and_old_manifests_are_preserved(protocol):
    history = m._validated_history()
    assert [baseline._sha(data) for data in history[0]] == [digest for _, digest in m._HISTORY]
    frozen, implementation, responses, result = history[2:]
    assert implementation.receipt.frozen_protocol == frozen
    assert responses.receipt.frozen_protocol == frozen
    assert responses.receipt.frozen_implementation == implementation
    assert result.receipt.response_batch_receipt_sha256 == responses.receipt_sha256
    assert len(frozen.declaration.code_sources) == 34
    assert len(implementation.receipt.code_sources) == 37
    assert len(responses.receipt.code_sources) == 40
    assert len(protocol.declaration.code_sources) == 43
    prior = {source.path: source for source in responses.receipt.code_sources}
    current = {source.path: source for source in protocol.declaration.code_sources}
    assert all(current[path] == source for path, source in prior.items())
    assert set(current) - set(prior) == {
        "verdant_math/successor_repair_protocol/__init__.py",
        "verdant_math/successor_repair_protocol/cli.py",
        "verdant_math/successor_repair_protocol/protocol.py",
    }


def test_published_protocol_is_exact_immutable_and_replayable(protocol):
    data = _PUBLISHED.read_bytes()
    assert len(data) == 39_943
    assert baseline._sha(data) == "ee8f37cb145704fbb9ff753a5416b2ba473d276c96813a194465ca5960883081"
    assert protocol.declaration_sha256 == (
        "b680c4b5eb50abd80b422df2cdf1ba8504af08045f9e1b7d52a99e68a8cfa98a"
    )
    assert m.load_successor_repair_protocol(_PUBLISHED) == protocol


def test_eight_actual_terminal_failures_are_exact_immutable_anchors(protocol):
    anchors = protocol.declaration.failure_anchors
    assert len(anchors) == 8
    assert tuple(anchor.case_ref for anchor in anchors) == tuple(
        f"math-v060:case:{index}" for index in range(24, 32)
    )
    assert {anchor.missing_subject for anchor in anchors} == {"math:integer:18"}
    assert {anchor.expected_answer for anchor in anchors} == {20, 21}
    assert all(anchor.grade == "abstained" for anchor in anchors)
    assert all(not anchor.blocking_claim_refs and not anchor.blocking_evidence_refs for anchor in anchors)
    assert {anchor.route_disposition for anchor in anchors} == {
        "kept_valid_original_right", "swapped_missing_original_right"
    }
    assert {tuple((step.from_number, step.to_number) for step in anchor.partial_steps)
            for anchor in anchors} == {(), ((17, 18),), ((16, 17), (17, 18))}
    assert anchors == m._failure_anchors(m._validated_history())


def test_domain_is_exactly_0_through_21_with_three_supplied_links_and_no_synthesis(protocol):
    domain = protocol.declaration.protocol["bounded_domain"]
    assert domain["integer_minimum"] == 0 and domain["integer_maximum"] == 21
    assert domain["predecessor_schema_maximum"] == 18
    assert tuple(map(tuple, domain["exact_teacher_successors"])) == m._CORRECT_SUCCESSORS
    assert tuple(map(tuple, domain["wrong_link_control_successors"])) == m._WRONG_SUCCESSORS
    assert domain["successor_at_21"] == "missing_and_visible_no_silent_domain_widening"
    assert not domain["old_type_or_manifest_modification_permitted"]
    assert not domain["numeric_successor_synthesis_permitted"]
    assert m.BoundedAdditionRequestV063(left=21, right=0).left == 21
    for field in ("left", "right"):
        with pytest.raises(ValueError):
            m.BoundedAdditionRequestV063.model_validate({"left": 0, "right": 0, field: 22})


def test_controls_change_only_three_successor_slots_and_keep_order_addition_prerequisites(protocol):
    spec = protocol.declaration.protocol
    assert tuple(spec["roles"]) == m._ROLES
    assert spec["shared_prerequisite"] == (
        "same_25_correct_v058_lessons_plus_same_correct_v061_operand_order_instruction_in_every_private_role"
    )
    assert spec["repair_slots"] == "three_teacher_successor_claims_or_three_matched_prompt_slots_only"
    assert "18_to_19_19_to_20_20_to_21" in spec["taught_repair"]
    assert "no_successor_claims" in spec["no_repair_control"]
    assert "18_to_20_19_to_21_20_to_18" in spec["wrong_link_control"]
    assert spec["control_difference"].startswith("only_the_three_terminal_successor_slots")
    assert spec["teacher_source_class"] == "human_testimony"
    assert spec["response_order"] == (
        "all_160_native_response_or_rejection_records_saved_before_any_of_128_external_grades"
    )


def test_all_40_cases_are_fresh_typed_fixed_and_keep_full_denominators(protocol):
    declaration = protocol.declaration
    excluded = set(declaration.excluded_raw_requests)
    cases = declaration.cases
    assert len(cases) == 40 and len({case.raw_request_json for case in cases}) == 40
    assert {group: sum(case.group == group for case in cases)
            for group in m._SPEC["prospective_groups"]} == {
        "pre_boundary_control": 10,
        "new_domain_zero_identity": 6,
        "repair_supported": 4,
        "declared_domain_ceiling": 12,
        "invalid_input": 8,
    }
    valid = invalid = 0
    for case in cases:
        raw = json.loads(case.raw_request_json)
        assert case.raw_request_json not in excluded
        try:
            request = m.BoundedAdditionRequestV063.model_validate(raw)
            valid += 1
            reversed_raw = canonical_json_bytes(
                {"left": request.right, "right": request.left}
            ).decode()
            assert reversed_raw not in excluded
        except ValueError:
            invalid += 1
            assert case.group == "invalid_input"
    assert (valid, invalid) == (32, 8)
    assert m._SPEC["full_denominators"].startswith("40_enrolled_and_32_valid_per_role")


def test_fresh_repair_cases_cover_only_needed_19_to_21_links_and_ceiling_is_visible(protocol):
    by_group = {}
    for case in protocol.declaration.cases:
        by_group.setdefault(case.group, []).append(json.loads(case.raw_request_json))
    repair = {(raw["left"], raw["right"]) for raw in by_group["repair_supported"]}
    assert repair == {(20, 1), (1, 20), (19, 2), (2, 19)}
    assert {raw["left"] + raw["right"] for raw in by_group["repair_supported"]} == {21}
    assert all(raw["left"] + raw["right"] > 21 for raw in by_group["declared_domain_ceiling"])
    assert {(raw["left"], raw["right"]) for raw in by_group["new_domain_zero_identity"]} == {
        (19, 0), (0, 19), (20, 0), (0, 20), (21, 0), (0, 21)
    }


def test_no_unused_legacy_domain_case_can_freshly_cross_18_under_unchanged_tokens(protocol):
    excluded = set(protocol.declaration.excluded_raw_requests)
    for total in (19, 20, 21):
        for right in range(1, 5):
            left = total - right
            if not 0 <= left <= 18:
                continue
            original = canonical_json_bytes({"left": left, "right": right}).decode()
            swapped = canonical_json_bytes({"left": right, "right": left}).decode()
            assert original in excluded or swapped in excluded
    assert "every_unchanged_v058_addition_request" in protocol.declaration.protocol["freshness_limit"]


def test_probe_closure_includes_all_old_and_adapter_vectors_and_hashes_sources(protocol):
    assert len(protocol.declaration.probe_exclusions) == 31
    excluded = {(probe.api, probe.raw_request_json) for probe in protocol.declaration.probe_exclusions}
    for left, right in m._ADAPTER_PROBES:
        raw = canonical_json_bytes({"left": left, "right": right}).decode()
        assert ("addition", raw) in excluded
        assert raw in protocol.declaration.excluded_raw_requests
    assert [source.path for source in protocol.declaration.probe_sources] == list(m._PROBE_FILES)
    for source in protocol.declaration.probe_sources:
        assert source.sha256 == baseline._sha((m._ROOT / source.path).read_bytes())


def test_native_checkpoint_and_mapping_order_reload_are_exact(protocol, tmp_path):
    source = m.fresh_successor_repair_kernel()
    path = tmp_path / "fresh.vdk"
    save_checkpoint(path, source.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))
    for name in ("concepts", "claims", "evidence"):
        setattr(restored.state, name, dict(reversed(tuple(getattr(restored.state, name).items()))))
    assert m.freeze_successor_repair_protocol(restored) == protocol
    assert not restored.state.claims and not restored.state.governance_outcomes
    assert not restored.state.obligation_attention_decisions and not restored.state.obligation_kernels
    assert not restored.state.revisions


@pytest.mark.parametrize("kind", ("foreign", "historical", "drifted"))
def test_foreign_exposed_or_stale_source_cannot_be_frozen(kind):
    if kind == "foreign":
        source = VerdantKernel(seed=63, state_dim=16)
    elif kind == "historical":
        history = m._validated_history()
        source = baseline._checkpoint(
            history[2].declaration.source_checkpoint_base64,
            history[2].declaration.source_checkpoint_sha256,
        )
    else:
        source = m.fresh_successor_repair_kernel()
        source.state.cycle = 1
    before = source.snapshot()
    with pytest.raises(ValueError, match="fresh"):
        m.freeze_successor_repair_protocol(source)
    assert source.snapshot() == before


@pytest.mark.parametrize("attack", (
    "version", "parent", "tree", "domain_max", "old_schema", "correct_link", "wrong_link",
    "synthesis", "ceiling", "prerequisite", "taught", "no_repair", "wrong_control", "control_difference",
    "source_class", "response_input", "response_evidence", "behavioral_targets", "numeric_fallback",
    "response_order", "scoring", "denominator", "invalid", "missing", "retune", "attention", "simulation",
    "case", "case_order", "case_group", "case_pair", "case_type", "drop_invalid", "duplicate",
    "anchor", "anchor_step", "anchor_expected", "anchor_hash", "exclusions", "probe", "probe_source",
    "artifact_hash", "artifact_path", "manifest", "fingerprint", "checkpoint", "future_answers", "future_grades",
))
def test_fully_rehashed_domain_control_case_anchor_source_or_authority_forgery_fails(
    protocol, tmp_path, attack
):
    raw = protocol.model_dump(mode="json")
    declaration = raw["declaration"]
    spec = declaration["protocol"]
    domain = spec["bounded_domain"]
    contract = spec["response_contract"]
    if attack == "version": spec["version"] = "retuned"
    elif attack == "parent": spec["grounded_parent_commit"] = "0" * 40
    elif attack == "tree": spec["grounded_parent_tree"] = "0" * 40
    elif attack == "domain_max": domain["integer_maximum"] = 22
    elif attack == "old_schema": domain["old_type_or_manifest_modification_permitted"] = True
    elif attack == "correct_link": domain["exact_teacher_successors"][0] = [18, 20]
    elif attack == "wrong_link": domain["wrong_link_control_successors"][1] = [19, 20]
    elif attack == "synthesis": domain["numeric_successor_synthesis_permitted"] = True
    elif attack == "ceiling": domain["successor_at_21"] = "auto_extend_to_22"
    elif attack == "prerequisite": spec["shared_prerequisite"] = "changed_addition_rule"
    elif attack == "taught": spec["taught_repair"] = "derive_links_from_integers"
    elif attack == "no_repair": spec["no_repair_control"] = "remove_order_instruction"
    elif attack == "wrong_control": spec["wrong_link_control"] = "choose_after_results"
    elif attack == "control_difference": spec["control_difference"] = "change_all_rules"
    elif attack == "source_class": spec["teacher_source_class"] = "physical_outcome"
    elif attack == "response_input": spec["input_contract"] = "include_expected_answer"
    elif attack == "response_evidence": contract["native_evidence"] = []
    elif attack == "behavioral_targets": contract[
        "case_group_expected_answer_grade_or_historical_anchor_as_behavioral_inputs"
    ] = True
    elif attack == "numeric_fallback": contract["numeric_token_or_successor_reconstruction"] = True
    elif attack == "response_order": spec["response_order"] = "grade_each_response_immediately"
    elif attack == "scoring": spec["scoring"] = "feed_expected_answer_to_adapter"
    elif attack == "denominator": spec["full_denominators"] = "successful_only"
    elif attack == "invalid": spec["invalid_handling"] = "drop_invalid"
    elif attack == "missing": spec["missing_handling"] = "replace_missing"
    elif attack == "retune": spec["outcome_conditioned_selection_tuning_or_replacement_permitted"] = True
    elif attack == "attention": spec["attention_allocation_permitted"] = True
    elif attack == "simulation": spec["obligation_simulation_permitted"] = True
    elif attack == "case": declaration["cases"][0]["raw_request_json"] = '{"left":10,"right":1}'
    elif attack == "case_order": declaration["cases"].reverse()
    elif attack == "case_group": declaration["cases"][0]["group"] = "repair_supported"
    elif attack == "case_pair": declaration["cases"][10]["order_pair"] = "foreign"
    elif attack == "case_type": declaration["cases"][-1]["raw_request_json"] = '{"left":21,"right":0}'
    elif attack == "drop_invalid": declaration["cases"].pop()
    elif attack == "duplicate": declaration["cases"][1] = declaration["cases"][0]
    elif attack == "anchor": declaration["failure_anchors"][0]["case_ref"] = "foreign"
    elif attack == "anchor_step": declaration["failure_anchors"][1]["partial_steps"][0]["to_number"] = 17
    elif attack == "anchor_expected": declaration["failure_anchors"][0]["expected_answer"] = 20
    elif attack == "anchor_hash": declaration["failure_anchors"][0]["response_sha256"] = "0" * 64
    elif attack == "exclusions": declaration["excluded_raw_requests"].pop()
    elif attack == "probe": declaration["probe_exclusions"].pop()
    elif attack == "probe_source": declaration["probe_sources"][0]["sha256"] = "0" * 64
    elif attack == "artifact_hash": declaration["prior_artifacts"][0]["sha256"] = "0" * 64
    elif attack == "artifact_path": declaration["prior_artifacts"][0]["path"] = declaration["prior_artifacts"][1]["path"]
    elif attack == "manifest": declaration["code_sources"][-1]["sha256"] = "0" * 64
    elif attack == "fingerprint": declaration["source_kernel_fingerprint"] = "0" * 64
    elif attack == "checkpoint":
        data = checkpoint_bytes(VerdantKernel(seed=123, state_dim=16).snapshot())
        declaration["source_checkpoint_base64"] = base64.b64encode(data).decode()
        declaration["source_checkpoint_sha256"] = baseline._sha(data)
    elif attack == "future_answers": declaration["answers"] = [21] * 40
    elif attack == "future_grades": declaration["grades"] = ["correct"] * 40
    path = tmp_path / "forged.vsrp"
    path.write_bytes(_rehash(raw))
    with pytest.raises((ValueError, RuntimeError)):
        m.load_successor_repair_protocol(path)


@pytest.mark.parametrize("flag", m._FALSE_FLAGS)
def test_rehashed_execution_effect_discovery_physical_or_canonical_flags_fail(protocol, tmp_path, flag):
    raw = protocol.model_dump(mode="json")
    raw["declaration"][flag] = True
    path = tmp_path / "authority.vsrp"
    path.write_bytes(_rehash(raw))
    with pytest.raises(ValueError):
        m.load_successor_repair_protocol(path)
    bypass = protocol.model_copy(update={
        "declaration": protocol.declaration.model_copy(update={flag: True})
    })
    with pytest.raises(ValueError):
        m.save_successor_repair_protocol(tmp_path / "bypassed.vsrp", bypass)


@pytest.mark.parametrize("index", range(9))
def test_changed_historical_artifact_fails_even_when_outer_content_is_rehashed(index, monkeypatch):
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
    with pytest.raises(ValueError, match="historical artifact"):
        m.freeze_successor_repair_protocol()


@pytest.mark.parametrize("scope", ("manifest", "probe", "source", "history"))
def test_drift_during_freeze_fails_without_partial_publication(scope, monkeypatch, tmp_path):
    source = m.fresh_successor_repair_kernel()
    if scope == "manifest":
        original, calls = m._code_manifest, 0

        def changed(history):
            nonlocal calls
            calls += 1
            result = original(history)
            return result if calls == 1 else result[:-1]

        monkeypatch.setattr(m, "_code_manifest", changed)
    elif scope == "probe":
        original, calls = m._read, 0

        def changed(path):
            nonlocal calls
            result = original(path)
            if Path(path) == m._ROOT / m._PROBE_FILES[0]:
                calls += 1
                return result if calls == 1 else result + b"\n# later probe\n"
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
        m.freeze_successor_repair_protocol(source)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("kind", ("bad_hash", "duplicate_key", "noncanonical", "oversized", "missing"))
def test_noncanonical_corrupt_duplicate_oversized_or_missing_inputs_fail(protocol, tmp_path, kind):
    path = tmp_path / "bad.vsrp"
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
        m.load_successor_repair_protocol(path)


@pytest.mark.parametrize("index", range(9))
def test_publication_cannot_replace_historical_evidence(protocol, index):
    path = m._ROOT / m._HISTORY[index][0]
    before = path.read_bytes()
    with pytest.raises(ValueError, match="protocol evidence"):
        m.save_successor_repair_protocol(path, protocol)
    assert path.read_bytes() == before


def test_immutable_paths_and_failed_replace_preserve_prior_bytes(protocol, tmp_path, monkeypatch):
    occupied = tmp_path / "occupied.vsrp"
    occupied.write_bytes(b"protected prior evidence")
    with pytest.raises(RuntimeError, match="different evidence"):
        m.save_successor_repair_protocol(occupied, protocol)
    assert occupied.read_bytes() == b"protected prior evidence"
    target = tmp_path / "failure.vsrp"

    def fail(*args, **kwargs):
        raise OSError("injected pre-replace failure")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError, match="pre-replace"):
        m.save_successor_repair_protocol(target, protocol)
    assert not target.exists()
    assert not tuple(tmp_path.glob(".*.tmp"))


def test_cli_has_only_freeze_and_replay_with_no_adapter_or_run(tmp_path, capsys):
    path = tmp_path / "cli.vsrp"
    assert cli(["freeze", str(path)]) == 0
    frozen = json.loads(capsys.readouterr().out)
    assert not frozen["repair_adapter_implemented"] and not frozen["responses_observed"]
    assert cli(["replay", str(path)]) == 0
    replayed = json.loads(capsys.readouterr().out)
    assert replayed["declaration_sha256"] == frozen["declaration_sha256"]
    assert cli(["replay", str(tmp_path / "missing")]) == 2
    capsys.readouterr()
    with pytest.raises(SystemExit):
        cli(["run", str(path)])


@pytest.mark.parametrize("path", (*m._PROBE_FILES,
    "verdant_math/teaching_pilot.py", "verdant_math/counting/pilot.py",
    "verdant_math/addition/pilot.py", "verdant_math/ordering_adapter/adapter.py",
    "verdant_math/ordering_evaluation/evaluation.py"))
def test_protocol_writer_protects_source_code_and_recorded_probe_files(protocol, path):
    target = m._ROOT / path
    before = target.read_bytes()
    with pytest.raises(ValueError, match="probes or code"):
        m.save_successor_repair_protocol(target, protocol)
    assert target.read_bytes() == before


def test_a_symlink_cannot_bypass_historical_input_protection(protocol, tmp_path):
    source = m._ROOT / m._HISTORY[7][0]
    before = source.read_bytes()
    alias = tmp_path / "aliased.vsrp"
    alias.symlink_to(source)
    with pytest.raises(ValueError, match="protocol evidence"):
        m.save_successor_repair_protocol(alias, protocol)
    assert alias.is_symlink() and source.read_bytes() == before
