from __future__ import annotations

import numpy as np

from ethomorphic.bridge.bridge import EthomorphicBridge
from ethomorphic.ecwf.core import ECWFCore

from verdant_v2.ethomorphic_config import detect_and_create_emergent_concepts_with_params
from verdant_v2.memory.graph import MemoryWeb


def test_emergent_connects_to_existing_emergent_with_shared_parents() -> None:
    memory = MemoryWeb()
    ecwf = ECWFCore(num_cognitive_dims=3, num_ethical_dims=3, random_state=1)
    bridge = EthomorphicBridge(memory=memory, ecwf=ecwf)

    for label in ["autonomy", "boundary", "contradiction"]:
        memory.add_concept(label, stability=0.8)
    memory.add_concept(
        "Emergent_old_scaffold",
        stability=0.5,
        metadata={"parent_concepts": ["autonomy", "boundary"]},
    )

    bridge.concept_dimension_mapping = {
        "autonomy": [("cognitive", 2, 1.0)],
        "boundary": [("ethical", 2, 1.0)],
        "contradiction": [("cognitive", 1, 1.0)],
    }

    bridge.ecwf.compute_sensitivities = lambda *_args, **_kwargs: (
        np.array([0.2, 0.8, 1.0]),
        np.array([0.1, 0.6, 0.9]),
    )

    created = detect_and_create_emergent_concepts_with_params(bridge, np.zeros((1, 1, 1)), 1.0)

    assert len(created) == 1
    new_label = created[0]
    assert memory.graph.has_edge(new_label, "Emergent_old_scaffold")


def test_ee_edge_weight_scales_with_parent_overlap_and_is_in_graph() -> None:
    memory = MemoryWeb()
    ecwf = ECWFCore(num_cognitive_dims=3, num_ethical_dims=3, random_state=2)
    bridge = EthomorphicBridge(memory=memory, ecwf=ecwf)

    for label in ["autonomy", "boundary", "contradiction"]:
        memory.add_concept(label, stability=0.8)
    memory.add_concept(
        "Emergent_shared",
        stability=0.5,
        metadata={"parent_concepts": ["autonomy", "other_parent"]},
    )

    bridge.concept_dimension_mapping = {
        "autonomy": [("cognitive", 2, 1.0)],
        "boundary": [("ethical", 2, 1.0)],
        "contradiction": [("cognitive", 1, 1.0)],
    }
    bridge.ecwf.compute_sensitivities = lambda *_args, **_kwargs: (
        np.array([0.2, 0.8, 1.0]),
        np.array([0.1, 0.6, 0.9]),
    )

    new_label = detect_and_create_emergent_concepts_with_params(bridge, np.zeros((1, 1, 1)), 1.0)[0]

    parent_count = len(memory.get_concept(new_label)["metadata"]["parent_concepts"])
    expected_raw = 0.6 * (1 / parent_count)
    # MemoryWeb.connect scales by average stability of the endpoints (both 0.5 at creation).
    expected_weight = expected_raw * 0.5
    ee_weight = memory.graph[new_label]["Emergent_shared"]["weight"]
    assert np.isclose(ee_weight, expected_weight, atol=1e-6)

    ee_edges = [
        (u, v)
        for u, v in memory.graph.edges()
        if u.startswith("Emergent_") and v.startswith("Emergent_")
    ]
    assert any(new_label in edge for edge in ee_edges)
