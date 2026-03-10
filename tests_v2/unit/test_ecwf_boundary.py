"""Unit tests for ECWF-native boundary candidate emergence."""

from __future__ import annotations

from verdant_v2.memory.basin_dynamics import BoundaryCandidate
from verdant_v2.system import VerdantConfig, VerdantSystem


def test_boundary_candidate_uses_ecwf_timestamp_and_metadata() -> None:
    system = VerdantSystem(
        VerdantConfig(
            seed=7,
            boundary_emergence_enabled=True,
            boundary_use_ecwf=True,
            boundary_emergence_threshold=0.0,
        )
    )
    for i in range(5):
        system.process_input(f"Cycle {i}: memory ethics identity boundary emergence")

    parents = [
        "identity",
        "continuity",
        "selfhood",
        "persistence",
        "transformation",
        "boundary",
    ]
    candidate = BoundaryCandidate(parent_concepts=parents, basin_pair=("basin_0", "basin_1"), overlap_score=1.0)
    label = system._evaluate_candidate_emergence(candidate)

    assert label is not None
    concept = system.memory_web.get_concept(label)
    assert concept is not None
    metadata = concept["metadata"]
    assert metadata["origin"] == "boundary_emergence"
    assert metadata["boundary"] is True
    assert metadata["ecwf_candidate"] is True

    creation_time = float(metadata["creation_time"])
    assert creation_time > 1_000_000_000
    assert creation_time != int(creation_time)
