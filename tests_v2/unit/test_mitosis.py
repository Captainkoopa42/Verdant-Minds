from __future__ import annotations

from pathlib import Path
from copy import deepcopy

from verdant.memory.graph import MemoryWeb, ShardedMemoryWeb
from verdant.memory.mitosis import DaughterShard, _updated_manifest, split_and_persist


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


def _daughter(shard_id: str, labels: list[str]) -> DaughterShard:
    return DaughterShard(
        shard_id=shard_id,
        anchors=labels[:1],
        node_ids=labels,
        state={
            "memory_store": {
                label: {
                    "stability": 0.8,
                    "connections": [],
                    "first_seen": 0,
                    "last_accessed": 0,
                    "access_count": 1,
                    "metadata": {},
                }
                for label in labels
            },
            "edges": [],
        },
    )


def _base_manifest() -> dict:
    return {
        "shards": {
            "parent": {"shard_id": "parent", "path": "shards/parent.json", "state": "active"},
            "old": {"shard_id": "old", "path": "shards/old.json", "state": "inactive"},
            "old2": {"shard_id": "old2", "path": "shards/old2.json", "state": "inactive"},
        },
        "active_shards": ["parent"],
        "concept_index": {
            "alpha": ["parent"],
            "beta": ["old"],
            "gamma": ["old2"],
            "shared": ["parent", "old"],
        },
        "weak_bridge_edges": [],
    }


def test_updated_manifest_preserves_inactive_shard_routing() -> None:
    manifest = _base_manifest()
    updated = _updated_manifest(
        manifest=manifest,
        parent_shard_id="parent",
        parent_meta=manifest["shards"]["parent"],
        daughters=(_daughter("daughter_a", ["alpha"]), _daughter("daughter_b", [])),
        weak_edges=[],
    )

    assert updated["concept_index"]["alpha"] == ["daughter_a"]
    assert updated["concept_index"]["beta"] == ["old"]


def test_updated_manifest_remaps_parent_side_mandatory_bridge() -> None:
    manifest = _base_manifest()
    manifest["weak_bridge_edges"] = [{
        "source": "alpha",
        "target": "beta",
        "source_shard": "parent",
        "target_shard": "old",
        "weight": 0.9,
        "mandatory": True,
        "status": "active",
    }]

    updated = _updated_manifest(
        manifest=manifest,
        parent_shard_id="parent",
        parent_meta=manifest["shards"]["parent"],
        daughters=(_daughter("daughter_a", ["alpha"]), _daughter("daughter_b", [])),
        weak_edges=[],
    )

    assert updated["weak_bridge_edges"] == [{
        "source": "alpha",
        "target": "beta",
        "source_shard": "daughter_a",
        "target_shard": "old",
        "weight": 0.9,
        "mandatory": True,
        "status": "active",
    }]


def test_updated_manifest_preserves_unrelated_bridge() -> None:
    bridge = {
        "source": "beta",
        "target": "gamma",
        "source_shard": "old",
        "target_shard": "old2",
        "weight": 0.4,
        "mandatory": False,
        "status": "ghost",
    }
    manifest = _base_manifest()
    manifest["weak_bridge_edges"] = [bridge]

    updated = _updated_manifest(
        manifest=manifest,
        parent_shard_id="parent",
        parent_meta=manifest["shards"]["parent"],
        daughters=(_daughter("daughter_a", ["alpha"]), _daughter("daughter_b", [])),
        weak_edges=[],
    )

    assert updated["concept_index"]["beta"] == ["old"]
    assert updated["concept_index"]["gamma"] == ["old2"]
    assert updated["weak_bridge_edges"] == [bridge]


def test_updated_manifest_quarantines_missing_endpoint_bridge() -> None:
    bridge = {
        "source": "alpha",
        "target": "missing",
        "source_shard": "parent",
        "target_shard": "old",
        "weight": 0.9,
        "mandatory": True,
    }
    manifest = _base_manifest()
    manifest["weak_bridge_edges"] = [bridge]

    updated = _updated_manifest(
        manifest=manifest,
        parent_shard_id="parent",
        parent_meta=manifest["shards"]["parent"],
        daughters=(_daughter("daughter_a", ["alpha"]), _daughter("daughter_b", [])),
        weak_edges=[],
    )

    assert updated["weak_bridge_edges"] == []
    assert len(updated["orphaned_bridge_edges"]) == 1
    orphan = updated["orphaned_bridge_edges"][0]
    assert orphan["source"] == "alpha"
    assert orphan["target"] == "missing"
    assert orphan["mandatory"] is True
    assert orphan["orphaned_reason"] == "missing_target_home"


def test_updated_manifest_removes_all_parent_homes_and_does_not_mutate_input() -> None:
    manifest = _base_manifest()
    original = deepcopy(manifest)

    updated = _updated_manifest(
        manifest=manifest,
        parent_shard_id="parent",
        parent_meta=manifest["shards"]["parent"],
        daughters=(_daughter("daughter_a", ["alpha"]), _daughter("daughter_b", ["shared"])),
        weak_edges=[],
    )

    assert manifest == original
    assert all(
        "parent" not in homes
        for homes in updated["concept_index"].values()
    )
    assert updated["concept_index"]["shared"] == ["old", "daughter_b"]


def test_split_and_persist_preserves_global_index_and_remaps_mandatory_bridge(tmp_path: Path) -> None:
    web = MemoryWeb()
    for label in ["alpha", "delta", "epsilon", "zeta"]:
        web.add_concept(label, stability=0.8)
    web.connect("alpha", "delta", 0.9)
    web.connect("delta", "epsilon", 0.9)
    web.connect("epsilon", "zeta", 0.9)

    manifest = {
        "defaults": {"max_nodes_per_shard": 2, "max_edges_per_shard": 1000},
        "runtime": {"cycle": 10},
        "shards": {
            "parent": {"shard_id": "parent", "path": "shards/parent.json", "state": "active"},
            "old": {"shard_id": "old", "path": "shards/old.json", "state": "inactive"},
        },
        "active_shards": ["parent"],
        "concept_index": {
            "alpha": ["parent"],
            "delta": ["parent"],
            "epsilon": ["parent"],
            "zeta": ["parent"],
            "beta": ["old"],
        },
        "weak_bridge_edges": [{
            "source": "alpha",
            "target": "beta",
            "source_shard": "parent",
            "target_shard": "old",
            "weight": 0.9,
            "mandatory": True,
            "status": "active",
        }],
    }

    result = split_and_persist(
        memory_web=web,
        manifest=manifest,
        parent_shard_id="parent",
        memory_root=tmp_path,
    )

    assert result is not None
    updated = result.manifest
    assert updated["concept_index"]["beta"] == ["old"]
    remapped = [
        edge for edge in updated["weak_bridge_edges"]
        if edge.get("source") == "alpha" and edge.get("target") == "beta"
    ]
    assert len(remapped) == 1
    assert remapped[0]["mandatory"] is True
    assert remapped[0]["source_shard"] in updated["concept_index"]["alpha"]
    assert remapped[0]["target_shard"] == "old"
