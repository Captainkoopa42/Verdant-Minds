"""Native Council-P/Q composition with independently graded negative controls.

All presented relation edges are explicit experimental teacher testimony.
The query asks an unprovided *composed* consequence. The composer never
receives a correct answer, grading labels, native write permission or
hypothetical evidence authority.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

from test_hierarchy_phase import hierarchy_fixture, fresh
from verdant_kernel import RelationStatus
from verdant_pockets import PocketIntegrityError, cultivate_pocket
from verdant_pockets.composition import (
    CompositionQuery, inspect_composition, evaluate_control_arms,
)


@pytest.fixture
def composed_case(hierarchy_fixture):
    kernel, family, q, _star, _novel, _obs = fresh(hierarchy_fixture)
    names = {c.normalized_label: cid for cid, c in kernel.state.concepts.items()}
    # Independent teacher testimony, supplied only as primitive links.
    # The requested endpoint result (a1 -> b4) is never supplied.
    for prefix, p_id in (("a", family[0]), ("b", family[1])):
        for n in range(1, 4):
            kernel.propose_relation(
                names[f"{prefix}{n}"], names[f"{prefix}{n+1}"], "precedes",
                evidence_refs=kernel.state.structures[p_id].evidence_refs,
                directed=True, status=RelationStatus.SUPPORTED, weight=0.84,
            )
    # c is a real unrelated Council-P memory with same native topology but
    # different predicate; this forces task selection to use typed evidence.
    for n in range(1, 4):
        kernel.propose_relation(
            names[f"c{n}"], names[f"c{n+1}"], "supports",
            evidence_refs=kernel.state.structures[family[2]].evidence_refs,
            directed=True, status=RelationStatus.SUPPORTED,
        )
    # Teacher adds only missing cross-P observation, NOT the answer.
    bridge = kernel.propose_relation(
        names["a4"], names["b1"], "precedes",
        evidence_refs=kernel.state.structures[family[0]].evidence_refs,
        directed=True, status=RelationStatus.SUPPORTED, weight=0.85,
    )
    before = kernel.fingerprint()
    pocket = cultivate_pocket(kernel, family, q_id=q)
    assert kernel.fingerprint() == before
    query = CompositionQuery(names["a1"], names["b4"], maximum_hops=9)
    return kernel, family, q, names, bridge, pocket, query


def _reidentify(p):
    from verdant_kernel.models import stable_id
    p = deepcopy(p)
    p.pop("pocket_id")
    p["pocket_id"] = stable_id("cognitive_pocket", p)
    return p


def test_new_grounded_composition_from_genuine_council_ps(composed_case):
    kernel, family, q, names, bridge, pocket, query = composed_case
    orig = kernel.fingerprint()
    result = inspect_composition(pocket, query)
    assert result["disposition"] == "supported_composition"
    assert result["selected_p_ids"] == list(family[:2])
    assert family[2] not in result["selected_p_ids"]
    assert len(result["witness_native_relation_ids"]) == 7
    assert bridge.relation_id in result["witness_native_relation_ids"]
    assert result["witness_concept_path"][0] == names["a1"]
    assert result["witness_concept_path"][-1] == names["b4"]
    assert result["witness_canonical_evidence_refs"]
    assert result["rule"]["transitivity_externally_declared"]
    assert not result["rule"]["learnt_by_verdant"]
    assert not result["hypothetical_analogy_evidence_used"]
    assert not result["candidate_composite"]["native_canonical_relation_created"]
    assert len(kernel.state.relations) == 10
    assert kernel.fingerprint() == orig
    assert result == inspect_composition(pocket, query)


def test_missing_or_reversed_bridge_must_abstain(composed_case):
    kernel, family, q, names, bridge, pocket, query = composed_case
    no_bridge = deepcopy(pocket)
    no_bridge["evidenced_cross_p_relations"] = []
    assert inspect_composition(_reidentify(no_bridge), query)["disposition"] == "abstain_missing_supported_path"
    reversed_bridge = deepcopy(pocket)
    for r in reversed_bridge["evidenced_cross_p_relations"]:
        r["source"], r["target"] = r["target"], r["source"]
    assert inspect_composition(_reidentify(reversed_bridge), query)["disposition"] == "abstain_missing_supported_path"


def test_wrong_p_membership_and_predicate_mismatch_controls(composed_case):
    kernel, family, q, names, bridge, pocket, query = composed_case
    wrong = inspect_composition(pocket, query, eligible_p_ids=(family[0],family[2]))
    assert wrong["disposition"] == "abstain_missing_relevant_p"
    altered = deepcopy(pocket)
    altered["evidenced_cross_p_relations"][0]["type"] = "supports"
    assert inspect_composition(_reidentify(altered), query)["disposition"] == "abstain_missing_supported_path"


def test_role_analogies_never_used_as_semantic_evidence(composed_case):
    kernel, family, q, names, bridge, pocket, query = composed_case
    assert pocket["hypothetical_role_alignments"]
    altered = deepcopy(pocket)
    altered["hypothetical_role_alignments"] = []
    assert inspect_composition(_reidentify(altered), query)["disposition"] == "supported_composition"
    no_bridge = deepcopy(altered)
    no_bridge["evidenced_cross_p_relations"] = []
    assert inspect_composition(_reidentify(no_bridge), query)["disposition"] == "abstain_missing_supported_path"


def test_unlicensed_predicates_cannot_infer_same_type_transitivity(composed_case):
    kernel, family, q, names, bridge, pocket, query = composed_case
    for predicate in ("supports", "contains", "requires", "unknown", "bounded_by"):
        result = inspect_composition(pocket, CompositionQuery(names["a1"], names["b4"], relation_type=predicate))
        assert result["disposition"] == "abstain_rule_not_licensed"


def test_missing_evidence_status_and_reflexive_fail_closed(composed_case):
    kernel, family, q, names, bridge, pocket, query = composed_case
    broken = deepcopy(pocket)
    broken["evidenced_cross_p_relations"][0]["evidence_refs"] = []
    with pytest.raises(PocketIntegrityError, match="evidence"):
        inspect_composition(_reidentify(broken), query)
    changed = deepcopy(pocket)
    changed["evidenced_cross_p_relations"][0]["status"] = "hypothesis"
    assert inspect_composition(_reidentify(changed), query)["disposition"] == "abstain_missing_supported_path"
    self_query = CompositionQuery(names["a1"], names["a1"])
    assert inspect_composition(pocket, self_query)["disposition"] == "abstain_reflexive_query"


def test_relation_contradiction_blocks_supported_witness(composed_case):
    kernel, family, q, names, bridge, pocket, query = composed_case
    contested = deepcopy(pocket)
    neg = deepcopy(contested["evidenced_cross_p_relations"][0])
    neg["id"] = "relation_conflict_harness_only"
    neg["status"] = "contradicted"
    contested["evidenced_cross_p_relations"].append(neg)
    result = inspect_composition(_reidentify(contested), query)
    assert result["disposition"] == "abstain_contested_evidence"


def test_bounded_search_abstains_without_overclaim(composed_case):
    kernel, family, q, names, bridge, pocket, query = composed_case
    qbudget = CompositionQuery(
        names["a1"], names["b4"], maximum_hops=3,
        maximum_search_expansions=2,
    )
    r = inspect_composition(pocket, qbudget)
    assert r["disposition"] in ("abstain_missing_supported_path", "abstain_budget_exhausted")
    assert not r["candidate_composite"]


def test_wrong_heldout_task_cannot_succeed_without_real_bridge(composed_case):
    kernel, family, q, names, bridge, pocket, query = composed_case
    unrelated = CompositionQuery(names["a1"], names["c4"], maximum_hops=9)
    assert inspect_composition(pocket, unrelated)["disposition"] == "abstain_missing_supported_path"
    swapped = CompositionQuery(names["b4"], names["a1"], maximum_hops=9)
    assert inspect_composition(pocket, swapped)["disposition"] == "abstain_missing_supported_path"


def test_matched_control_report_and_evidence_free_arms(composed_case):
    kernel, family, q, names, bridge, pocket, query = composed_case
    report = evaluate_control_arms(pocket, query, wrong_ps=(family[0],family[2]))
    assert report["baseline"]["disposition"] == "supported_composition"
    by_arm = {x["arm"]: x for x in report["controls"]}
    assert len(by_arm) == 5
    assert by_arm["without_cross_p_relations"]["disposition"] == "abstain_missing_supported_path"
    assert by_arm["reverse_all_cross_p_relations"]["disposition"] == "abstain_missing_supported_path"
    assert by_arm["cross_bridge_predicate_mismatch"]["disposition"] == "abstain_missing_supported_path"
    assert by_arm["wrong_p_restriction"]["disposition"] == "abstain_missing_relevant_p"
    assert by_arm["reverse_analogy_metadata"]["numeric_success"]
    assert report["is_composition_independent_of_analogy"]
    assert report["canonical_writeback"] is False


def test_changed_canonical_pocket_source_identity_rejected(composed_case):
    _, family, q, names, bridge, pocket, query = composed_case
    forged = deepcopy(pocket)
    forged["evidenced_cross_p_relations"].clear()
    with pytest.raises(PocketIntegrityError, match="identity"):
        inspect_composition(forged, query)
    with pytest.raises(PocketIntegrityError):
        inspect_composition(pocket, CompositionQuery("forged", names["b4"]))
    with pytest.raises(PocketIntegrityError):
        inspect_composition(pocket, CompositionQuery(names["a1"], names["b4"], maximum_member_ps=1))
