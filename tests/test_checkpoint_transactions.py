from __future__ import annotations

from pathlib import Path

import pytest

from verdant.memory.graph import MemoryWeb, ShardedMemoryWeb
from verdant.system import VerdantSystem


MITOSIS_FAILPOINTS = [
    "mitosis_after_first_daughter_temp",
    "mitosis_after_all_daughter_temps",
    "mitosis_after_staged_manifest",
    "mitosis_after_daughter_replacements",
    "mitosis_after_manifest_commit",
    "primary_checkpoint_before_temp",
    "primary_checkpoint_temp_written",
    "primary_checkpoint_committed",
    "mitosis_before_parent_retirement",
    "mitosis_during_cleanup",
]


def _web(node_count: int = 8) -> MemoryWeb:
    web = MemoryWeb()
    labels = [f"concept_{i}" for i in range(node_count)]
    for label in labels:
        web.add_concept(label, stability=0.8)
    for left, right in zip(labels, labels[1:]):
        web.connect(left, right, 0.9)
    web.connect(labels[0], labels[-1], 0.2)
    return web


def _system_for_mitosis() -> VerdantSystem:
    system = VerdantSystem()
    system.memory_web = ShardedMemoryWeb.monolith(_web())
    system._memory_block.memory_web = system.memory_web
    system.pipeline.memory_web = system.memory_web
    return system


def _assert_loaded(path: Path) -> VerdantSystem:
    loaded = VerdantSystem()
    loaded.load_state(str(path))
    assert loaded.memory_web.graph.number_of_nodes() >= 1
    return loaded


def _assert_manifest_valid(system: VerdantSystem) -> None:
    manifest = system.memory_web.manifest
    shards = manifest.get("shards", {})
    for concept, homes in manifest.get("concept_index", {}).items():
        home_list = homes if isinstance(homes, list) else [homes]
        for shard_id in home_list:
            assert shard_id in shards, (concept, shard_id)
            assert shards[shard_id].get("state") != "split"
    for edge in manifest.get("weak_bridge_edges", []):
        assert edge["source"] in manifest.get("concept_index", {})
        assert edge["target"] in manifest.get("concept_index", {})


def test_non_mitosis_save_load_roundtrip_has_generation(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    system = VerdantSystem()
    system.save_state(str(path))

    loaded = _assert_loaded(path)
    generation = loaded.memory_web.manifest.get("manifest_generation")
    assert generation
    assert loaded._last_checkpoint_recovery["checkpoint_generation"] == generation


def test_repeated_save_and_moved_checkpoint_directory(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    path = source / "state.json"
    system = VerdantSystem()
    system.save_state(str(path))
    system.save_state(str(path))

    moved = tmp_path / "moved"
    source.rename(moved)
    loaded = _assert_loaded(moved / "state.json")
    assert loaded._checkpoint_path == str(moved / "state.json")


def test_legacy_checkpoint_loads_without_generation(tmp_path: Path) -> None:
    path = tmp_path / "legacy.json"
    system = VerdantSystem()
    system.save_state(str(path))
    state = path.read_text(encoding="utf-8")
    state = state.replace('"checkpoint_generation":', '"legacy_removed":')
    path.write_text(state, encoding="utf-8")

    loaded = _assert_loaded(path)
    assert loaded._last_checkpoint_recovery["checkpoint_generation"] == "legacy-0"


@pytest.mark.parametrize("failpoint", MITOSIS_FAILPOINTS)
def test_mitosis_transaction_failure_retry_is_recoverable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failpoint: str) -> None:
    path = tmp_path / "state.json"
    system = _system_for_mitosis()
    system.memory_web.manifest["defaults"]["max_nodes_per_shard"] = 100
    system.save_state(str(path))

    system.memory_web.manifest["defaults"]["max_nodes_per_shard"] = 4
    monkeypatch.setenv("VERDANT_TX_FAILPOINT", failpoint)
    with pytest.raises(RuntimeError):
        system.save_state(str(path))

    _assert_loaded(path)
    monkeypatch.delenv("VERDANT_TX_FAILPOINT")
    system.save_state(str(path))
    loaded = _assert_loaded(path)
    assert loaded.memory_web.manifest["active_shards"] == [loaded.memory_web.active_shard_id]
    _assert_manifest_valid(loaded)


def test_normal_mitosis_save_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    system = _system_for_mitosis()
    system.memory_web.manifest["defaults"]["max_nodes_per_shard"] = 4
    system.save_state(str(path))

    loaded = _assert_loaded(path)
    assert loaded.memory_web.manifest["manifest_generation"]
    assert len(loaded.memory_web.manifest["shards"]) >= 3
    _assert_manifest_valid(loaded)
