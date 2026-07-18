from __future__ import annotations
from pathlib import Path
from verdant.system import VerdantSystem
from verdant.memory.graph import MemoryWeb, ShardedMemoryWeb
from verdant.memory.basin_dynamics import regulate_density


def test_checkpoint_path_and_council_persist(tmp_path: Path) -> None:
    path = tmp_path / "verdant_latest.json"
    s = VerdantSystem()
    s.council.influence_weights["ethics"] = 2.5
    s.council.interaction_history.append({"turn": 1})
    s.save_state(str(path))
    restored = VerdantSystem()
    restored.load_state(str(path))
    assert restored._checkpoint_path == str(path)
    assert restored.council.influence_weights["ethics"] == 2.5
    assert restored.council.interaction_history == [{"turn": 1}]


def test_thaw_uses_manifest_lru_and_recovers_missing_shard(tmp_path: Path) -> None:
    web = MemoryWeb(); web.add_concept("a"); facade = ShardedMemoryWeb.monolith(web)
    facade.manifest["defaults"]["lru_cache_size"] = 1
    facade.manifest["shards"]["missing"] = {"state": "active", "path": "shards/missing.json"}
    facade.manifest["concept_index"] = {"ghost": ["missing"]}
    facade.thaw("missing", tmp_path)
    assert facade.manifest["shards"]["missing"]["state"] == "split"
    assert "ghost" not in facade.manifest["concept_index"]


def test_graph_cache_synced_after_density_regulation() -> None:
    web = MemoryWeb()
    for n in ["a", "b", "c"]: web.add_concept(n)
    web.connect("a", "b", 0.1); web.connect("a", "c", 0.1); web.connect("b", "c", 0.1)
    regulate_density(web, max_density=0.1)
    for node, data in web.memory_store.items():
        assert {x[0] for x in data["connections"]} == set(web.graph.neighbors(node))
