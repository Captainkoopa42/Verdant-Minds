from __future__ import annotations

import re

from cultivation.providers.local import LocalProvider
from verdant_v2.system import VerdantConfig, VerdantSystem


NUMERIC_RE = re.compile(r"^\d+$")
BASIN_RE = re.compile(r"^basin_\d+$")
HEX_ID_RE = re.compile(r"^[a-f0-9]{6,}$")


def _is_noise_label(label: str) -> bool:
    lowered = label.lower()
    return bool(NUMERIC_RE.fullmatch(lowered) or BASIN_RE.fullmatch(lowered) or HEX_ID_RE.fullmatch(lowered))


def test_20_cycle_run_filters_noise_and_produces_ee_edges() -> None:
    cfg = VerdantConfig(seed=11, initialize_knowledge=True)
    system = VerdantSystem(cfg)
    provider = LocalProvider()

    for cycle in range(20):
        prompt = f"Cycle {cycle}: identity memory ethics emergence coherence"
        text = provider.generate(prompt, seed=cycle)
        system.process_input(text, metadata={"cycle": cycle})

    concepts = system.memory_web.list_concepts()
    noise_nodes = [c for c in concepts if _is_noise_label(c)]
    assert noise_nodes == []

    emergents = system.memory_web.get_emergent_nodes()
    assert emergents
    for emergent in emergents:
        metadata = system.memory_web.get_concept(emergent).get("metadata", {})
        parents = metadata.get("parent_concepts", [])
        assert parents
        assert all(not _is_noise_label(parent) for parent in parents)

    edge_classification = system.memory_web.get_edge_classification()
    assert edge_classification["emergent_emergent"] > 0
