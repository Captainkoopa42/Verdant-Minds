"""Native P/Q v2.1 gap -> explicit observation -> retention adversarial tests."""
from __future__ import annotations

from copy import deepcopy
import json

import pytest

from verdant_kernel import VerdantKernel, load_checkpoint, save_checkpoint
from verdant_pockets import PocketIntegrityError, cultivate_pocket
from verdant_pockets.composition import CompositionQuery, inspect_composition
from verdant_pockets.research_demo import make_native_teaching_corpus
from verdant_pockets.evidence_retention import (
    new_ledger, observation_from_testimony, validate_ledger,
    acquire_observation, compose_with_evidence, flat_graph_control,
    gap_certificate, save_ledger, load_ledger,
)


@pytest.fixture(scope="module")
def prebridge_fixture():
    native, family, qid, names, primitive_ids = make_native_teaching_corpus(include_cross_p_bridge=False)
    assert len(primitive_ids) == 9
    assert len(native.state.relations) == 9
    before = native.fingerprint()
    pocket = cultivate_pocket(native, family, q_id=qid, rounds=1)
    assert native.fingerprint() == before
    return native.snapshot(), family, qid, names, pocket


@pytest.fixture
def case(prebridge_fixture):
    state, family, qid, names, ignored = prebridge_fixture
    kernel = VerdantKernel.from_state(state.model_copy(deep=True))
    pocket = cultivate_pocket(kernel, family, q_id=qid, rounds=1)
    return kernel, pocket, names, family, qid


def _observation(names, source="r4", target="s1", predicate="precedes"):
    return observation_from_testimony(
        source=names[source], target=names[target],
        relation_type=predicate, source_ref="independent:controlled-curriculum-stage-2",
    )


def _full(names):
    return CompositionQuery(names["r1"], names["s4"], maximum_hops=9)


def test_native_gap_then_external_observation_then_conditional_composition(case):
    kernel, pocket, names, family, qid = case
    before = kernel.fingerprint()
    query = _full(names)
    gap = gap_certificate(pocket, query)
    assert gap["disposition"] == "abstain_missing_supported_path"
    assert gap["native_route_candidates"] == 0
    assert gap["candidate_bridge_guessed"] is False
    initial = new_ledger(pocket)
    assert compose_with_evidence(pocket, initial, query)["disposition"] == "abstain_missing_supported_path"
    updated = acquire_observation(pocket, initial, _observation(names))
    assert initial["events"] == [] and len(updated["events"]) == 1
    outcome = compose_with_evidence(pocket, updated, query)
    assert outcome["disposition"] == "supported_experimental_composition"
    assert outcome["selected_p_ids"] == list(family[:2])
    assert len(outcome["witness_native_relation_ids"]) == 6
    assert len(outcome["witness_external_observation_ids"]) == 1
    assert len(outcome["witness_path"]) == 8
    assert outcome["candidate_composite"]["external_ground_truth_independently_verified"] is False
    assert not outcome["candidate_composite"]["native_canonical_claim_created"]
    assert inspect_composition(pocket, query)["disposition"] == "abstain_missing_supported_path"
    assert len(kernel.state.relations) == 9
    assert kernel.fingerprint() == before


def test_heldout_query_reuses_same_recorded_bridge_without_answer_training(case):
    kernel, pocket, names, family, qid = case
    journal = acquire_observation(pocket, new_ledger(pocket), _observation(names))
    heldout = CompositionQuery(names["r3"], names["s2"], maximum_hops=9)
    result = compose_with_evidence(pocket, journal, heldout)
    assert result["disposition"] == "supported_experimental_composition"
    assert len(result["witness_native_relation_ids"]) == 2
    assert len(result["witness_external_observation_ids"]) == 1
    assert result == compose_with_evidence(pocket, journal, heldout)


def test_flat_baseline_supports_same_result_no_pocket_advantage_claim(case):
    kernel, pocket, names, family, qid = case
    journal = acquire_observation(pocket, new_ledger(pocket), _observation(names))
    query = _full(names)
    pocket_result = compose_with_evidence(pocket, journal, query)
    flat = flat_graph_control(pocket, journal, query)
    assert flat["disposition"] == pocket_result["disposition"]
    assert flat["witness"] == (pocket_result["witness_native_relation_ids"][:3] +
                               ["experimental_observation_" + journal["events"][0]["observation_id"][:24]] +
                               pocket_result["witness_native_relation_ids"][3:])
    assert flat["edge_expansions"] > 0
    assert pocket_result["metrics"]["edge_expansions"] > 0


@pytest.mark.parametrize("src, dst, predicate", [
    ("s1","r4","precedes"), # reversed direction
    ("r4","t1","precedes"), # wrong target P
])
def test_wrong_direction_or_wrong_p_evidence_cannot_yield_result(case,src,dst,predicate):
    kernel, pocket, names, family, qid = case
    journal = acquire_observation(pocket, new_ledger(pocket), _observation(names,src,dst,predicate))
    query = _full(names)
    result = compose_with_evidence(pocket, journal, query)
    assert result["disposition"] == "abstain_missing_supported_path"
    assert result["candidate_composite"] is None


def test_unknown_or_unlicensed_predicate_fails_closed(case):
    _, pocket, names, _, _ = case
    with pytest.raises(PocketIntegrityError):
        acquire_observation(pocket, new_ledger(pocket), _observation(names,predicate="supports"))
    unsupported = CompositionQuery(names["r1"], names["s4"], relation_type="supports")
    assert compose_with_evidence(pocket, new_ledger(pocket), unsupported)["disposition"] == "abstain_rule_not_licensed"


def test_teacher_must_not_supply_requested_answer_directly(case):
    _, pocket, names, _, _ = case
    journal = acquire_observation(pocket, new_ledger(pocket),
                                  _observation(names, "r1", "s4"))
    q = _full(names)
    result = compose_with_evidence(pocket, journal, q)
    assert result["disposition"] == "abstain_direct_observation_not_composition"
    assert not result["witness_external_observation_ids"]


def test_ledger_does_not_make_canonical_fact_after_snapshot_reload(case, tmp_path):
    kernel, pocket, names, family, qid = case
    vdk = tmp_path / "prebridge-native.vdk"
    save_checkpoint(vdk, kernel.snapshot())
    frozen_bytes = vdk.read_bytes()
    journal = acquire_observation(pocket, new_ledger(pocket), _observation(names))
    report = tmp_path / "experiment.vpel.json"
    save_ledger(report, journal, pocket)
    with pytest.raises(FileExistsError):
        save_ledger(report, journal, pocket)
    restored_kernel = VerdantKernel.from_state(load_checkpoint(vdk))
    fresh_pocket = cultivate_pocket(restored_kernel, family, q_id=qid, rounds=1)
    reread = load_ledger(report, fresh_pocket)
    heldout = CompositionQuery(names["r2"], names["s3"], maximum_hops=9)
    assert compose_with_evidence(pocket, journal, heldout) == compose_with_evidence(fresh_pocket, reread, heldout)
    assert inspect_composition(fresh_pocket, heldout)["disposition"] == "abstain_missing_supported_path"
    assert vdk.read_bytes() == frozen_bytes
    assert len(restored_kernel.state.relations) == 9


def test_binding_and_corruption_detected_after_replay(case,tmp_path):
    _, pocket, names, _, _ = case
    original = acquire_observation(pocket, new_ledger(pocket), _observation(names))
    for attack in ("broken_hash","payload","source","event","head"):
        forged = deepcopy(original)
        if attack == "broken_hash":
            forged["events"][0]["record_hash"] = "forged"
        elif attack == "payload":
            forged["events"][0]["observation"]["observation_body"]["object"] = names["t3"]
        elif attack == "source":
            forged["source"]["canonical_fingerprint"] = "wrong"
        elif attack == "event":
            forged["events"][0]["sequence"] = 99
        else:
            forged["head_hash"] = "wrong"
        with pytest.raises(PocketIntegrityError):
            validate_ledger(forged,pocket)
    dest = tmp_path / "journal.vpel.json"
    save_ledger(dest, original, pocket)
    dest.write_bytes(dest.read_bytes() + b" ")
    with pytest.raises(PocketIntegrityError):
        load_ledger(dest, pocket)


def test_unsupported_evidence_kind_and_broken_checksum_not_admitted(case):
    _, pocket, names, _, _ = case
    native = new_ledger(pocket)
    for mode in ("untrusted","wrong_hash","wrong_payload","unknown_endpoint"):
        obs = _observation(names)
        if mode == "untrusted":
            obs["evidence_kind"] = "hypothesis"
        elif mode == "wrong_hash":
            obs["observation_sha256"] = "wrong"
        elif mode == "wrong_payload":
            obs["observation_body"]["object"] = names["t4"]
        else:
            obs["source"] = "unknown"
        with pytest.raises(PocketIntegrityError):
            acquire_observation(pocket, native, obs)


def test_retained_journal_never_crosses_native_fingerprint(case):
    kernel, pocket, names, family, qid = case
    ledger = acquire_observation(pocket, new_ledger(pocket), _observation(names))
    changed = deepcopy(pocket)
    changed["canonical_fingerprint"] = "other"
    with pytest.raises(PocketIntegrityError):
        validate_ledger(ledger, changed)
    assert len(kernel.state.obligation_kernels) == 0



def test_end_to_end_disposable_native_acquisition_demo_has_separated_truth(case):
    from verdant_pockets.research_acquisition_demo import run_acquisition_demo

    report, journal, pocket = run_acquisition_demo()
    assert report["pre_observation_gap"]["disposition"] == "abstain_missing_supported_path"
    assert report["post_external_observation"]["disposition"] == "supported_experimental_composition"
    assert report["heldout_new_query"]["disposition"] == "supported_experimental_composition"
    assert report["post_reload_heldout_same_result"]
    assert report["native_primitive_relation_count"] == 9
    assert report["flat_graph_same_evidence_control"]["disposition"] == "supported_experimental_composition"
    assert report["comparison_proves_pocket_advantage_over_flat_graph"] is False
    assert report["native_memory_modified"] is False
    assert report["external_observation_truth_independently_verified"] is False
    assert report["controls"] == {
        "no_observation": "abstain_missing_supported_path",
        "reverse_observation": "abstain_missing_supported_path",
        "irrelevant_p_observation": "abstain_missing_supported_path",
        "direct_answer_leak_control": "abstain_direct_observation_not_composition",
        "unlicensed_query": "abstain_rule_not_licensed",
    }
    validate_ledger(journal, pocket)



def test_flat_control_abstains_without_bridge_and_under_reversed_observation(case):
    _kernel, pocket, names, _family, _qid = case
    query = _full(names)
    before = deepcopy(pocket)
    empty = new_ledger(pocket)
    wrong = acquire_observation(pocket, empty, _observation(names,"s1","r4"))
    assert flat_graph_control(pocket, empty, query)["disposition"] == "abstain_missing_supported_path"
    assert flat_graph_control(pocket, wrong, query)["disposition"] == "abstain_missing_supported_path"
    assert pocket == before


def test_fresh_process_cli_mode_validates_sealed_teacher_journal(case, tmp_path, capsys):
    from verdant_pockets.research_acquisition_demo import main
    output = tmp_path / "controlled.json"
    journal = tmp_path / "controlled.vpel.json"
    main(["--out", str(output), "--ledger", str(journal)])
    assert output.is_file() and journal.is_file()
    capsys.readouterr()
    main(["--verify", str(journal)])
    result = json.loads(capsys.readouterr().out)
    assert result["sidecar_verified_against_fresh_native_checkpoint"]
    assert result["original_native_relation_count"] == 9
    assert result["heldout_disposition"] == "supported_experimental_composition"
    assert result["native_memory_unchanged"]
