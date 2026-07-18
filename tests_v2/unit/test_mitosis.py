from __future__ import annotations

from pathlib import Path

from verdant.memory.graph import MemoryWeb, ShardedMemoryWeb


def _clustered_web() -> MemoryWeb:
    web = MemoryWeb()
    for label in ["mass", "gravity", "orbit", "planet", "ethics", "trust", "care", "justice"]:
        web.add_concept(label, stability=0.8)

    for source, target in [
        ("mass", "gravity"),
        ("gravity", "orbit"),
        ("orbit", "planet"),
        ("mass", "planet"),
        ("ethics", "trust"),
        ("trust", "care"),
        ("care", "justice"),
        ("ethics", "justice"),
    ]:
        web.connect(source, target, 0.9)
    web.connect("planet", "ethics", 0.2)
    return web


def test_flush_triggers_physical_mitosis(tmp_path: Path) -> None:
    facade = ShardedMemoryWeb.monolith(_clustered_web())
    facade.manifest["defaults"]["max_nodes_per_shard"] = 100
    facade.manifest["defaults"]["max_edges_per_shard"] = 1_000
    initial = facade.flush_shards(tmp_path)
    parent_path = tmp_path / "shards" / f"{ShardedMemoryWeb.DEFAULT_SHARD_ID}.json"
    assert initial["mitosis_performed"] is False
    assert parent_path.exists()

    facade.manifest["defaults"]["max_nodes_per_shard"] = 4
    result = facade.flush_shards(tmp_path)

    assert result["mitosis_performed"] is True
    assert not parent_path.exists()
    assert result["parent_shard_id"] == ShardedMemoryWeb.DEFAULT_SHARD_ID
    assert len(result["daughter_shard_ids"]) == 2
    assert facade.active_shard_id in result["daughter_shard_ids"]
    assert facade.graph.number_of_nodes() <= 4

    manifest = facade.manifest
    assert manifest["shards"][ShardedMemoryWeb.DEFAULT_SHARD_ID]["state"] == "split"
    assert manifest["active_shards"] == [facade.active_shard_id]
    assert manifest["weak_bridge_edges"]

    for daughter_id in result["daughter_shard_ids"]:
        shard_path = tmp_path / "shards" / f"{daughter_id}.json"
        assert shard_path.exists()
        assert manifest["shards"][daughter_id]["anchor_labels"]

    assert (tmp_path / "manifest.json").exists()
