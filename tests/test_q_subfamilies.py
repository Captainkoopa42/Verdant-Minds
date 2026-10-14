"""Bounded Q subfamily discovery: adversarial, deterministic, evidence-only graphs.

These are PURE graph-level tests. They deliberately do not fake native P,
Council, hierarchy observation or Q-promotion events. Native end-to-end
coverage remains in test_hierarchy_phase.py and test_vast_integrated.py.
"""
from __future__ import annotations

from verdant_hierarchy import VerdantHierarchyPipeline


def _group_graph(sizes=(4, 4, 4), *, internal=0.99, bridges=0.91,
                 complete_cross=False, reverse=False):
    names = [f"p{i:02d}" for i in range(sum(sizes))]
    groups = []
    cursor = 0
    for size in sizes:
        groups.append(tuple(names[cursor: cursor+size]))
        cursor += size

    graph = {node: set() for node in names}
    scores = {}

    def connect(a, b, strength):
        pair = tuple(sorted((a, b)))
        graph[a].add(b)
        graph[b].add(a)
        scores[pair] = [strength]

    for group in groups:
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                connect(a, b, internal)
    if complete_cross:
        for i, left in enumerate(groups):
            for right in groups[i+1:]:
                for a in left:
                    for b in right:
                        connect(a, b, bridges)
    else:
        for left, right in zip(groups, groups[1:]):
            connect(left[-1], right[0], bridges)
    if reverse:
        # Same evidence, different input dictionary/set insertion orders.
        graph = {key: set(sorted(value, reverse=True))
                 for key, value in reversed(list(graph.items()))}
        scores = dict(reversed(list(scores.items())))
    return graph, scores, tuple(groups)


def _discover(graph, scores, *, min_members=3, max_members=8):
    components = VerdantHierarchyPipeline._components(graph)
    assert len(components) == 1
    return VerdantHierarchyPipeline._bounded_subfamilies(
        components[0], graph, scores,
        minimum_members=min_members,
        maximum_members=max_members,
    )


def test_preserve_original_four_and_eight_member_components():
    for n in (4, 8):
        graph, scores, groups = _group_graph((n,))
        assert _discover(graph, scores) == groups


def test_resolve_twelve_as_three_bounded_communities_with_real_margin():
    graph, scores, groups = _group_graph()
    result = _discover(graph, scores)
    assert result == groups
    assert all(3 <= len(group) <= 8 for group in result)
    assert len(set().union(*(set(g) for g in result))) == 12
    assert len(set().union(*(set(g) for g in result))) == sum(len(g) for g in result)


def test_resolve_twelve_as_two_six_member_communities():
    graph, scores, groups = _group_graph((6, 6))
    assert _discover(graph, scores) == groups


def test_refuse_indistinguishable_twelve_clique_no_arbitrary_chopping():
    graph, scores, _ = _group_graph((4, 4, 4), complete_cross=True,
                                    internal=0.99, bridges=0.99)
    assert _discover(graph, scores) == ()


def test_refuse_near_equal_external_links_no_false_boundary():
    graph, scores, _ = _group_graph((4, 4, 4), internal=0.99,
                                    bridges=0.975)
    assert _discover(graph, scores) == ()


def test_connected_dense_weak_cross_edges_need_native_boundary_quality():
    graph, scores, groups = _group_graph((4, 4, 4), internal=0.99,
                                         bridges=0.91, complete_cross=True)
    # Pure discovery nominates groups; native _candidate_from_component must
    # additionally count each outgoing verified link as boundary pressure.
    assert _discover(graph, scores) == groups
    first = set(groups[0])
    cross = [(a, b) for a, b in scores if (a in first) != (b in first)]
    assert len(cross) == 32  # pressure is not silently dropped as "not a member"


def test_deterministic_evidence_order_and_label_permutation():
    graph, scores, groups = _group_graph(reverse=False)
    reversed_graph, reversed_scores, _ = _group_graph(reverse=True)
    assert _discover(graph, scores) == groups
    assert _discover(reversed_graph, reversed_scores) == groups


def test_oversized_clique_128_node_search_cap_is_fail_closed():
    graph, scores, _ = _group_graph((129,))
    assert _discover(graph, scores) == ()


def test_crosslinks_do_not_create_fake_three_member_group():
    graph, scores, groups = _group_graph((2, 5, 5))
    assert _discover(graph, scores) == groups[1:]


def test_no_subgroup_from_unweighted_missing_paper_evidence():
    graph, scores, _ = _group_graph((4, 4, 4))
    assert _discover(graph, {}) == ()



def test_checkpoint_audit_read_only_with_no_promoted_p(tmp_path):
    from verdant_integrated.q_subfamily_audit import audit_checkpoint
    from verdant_kernel import VerdantKernel, save_checkpoint

    original = VerdantKernel(seed=91802, state_dim=16,
                             run_label="bounded-q-read-only")
    p = tmp_path / "empty.vdk"
    save_checkpoint(p, original.snapshot())
    frozen = p.read_bytes()
    report = audit_checkpoint(p)
    assert report["promoted_p"] == 0
    assert report["promoted_q"] == 0
    assert report["component_reports"] == []
    assert report["no_native_mutation"] is True
    assert p.read_bytes() == frozen


def test_hierarchy_code_is_in_study_manifest_source_lock():
    from verdant_integrated import vast
    assert "verdant_hierarchy/pipeline.py" in vast._SOURCE_FILES
    assert "verdant_interaction/pipeline.py" in vast._SOURCE_FILES
    assert "verdant_integrated/q_subfamily_audit.py" in vast._SOURCE_FILES
