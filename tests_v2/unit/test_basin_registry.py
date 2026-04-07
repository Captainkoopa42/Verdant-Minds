from __future__ import annotations

import json

from verdant.memory.basin_registry import BasinRegistry


def test_initial_detection() -> None:
    registry = BasinRegistry()
    basins = registry.update_from_detection([
        {"a", "b", "c"},
        {"x", "y", "z"},
    ], cycle=0)

    assert len(basins) == 2
    assert {basin.basin_id for basin in basins} == {"basin_0", "basin_1"}


def test_persistent_identity() -> None:
    registry = BasinRegistry()
    first = registry.update_from_detection([
        {"a", "b", "c", "d"},
        {"x", "y", "z", "w"},
    ], cycle=0)
    first_ids = {frozenset(basin.nodes): basin.basin_id for basin in first}

    second = registry.update_from_detection([
        {"a", "b", "c", "e"},
        {"x", "y", "z", "q"},
    ], cycle=10)

    assert len(second) == 2
    assert {basin.basin_id for basin in second} == set(first_ids.values())


def test_daughter_protection() -> None:
    registry = BasinRegistry(daughter_protection_cycles=2)
    registry.update_from_detection([{"p1", "p2", "p3", "p4"}], cycle=0)
    daughter = registry.register_budded_basin({"d1", "d2"}, cycle=1, parent_id="basin_0", basin_id="basin_1")

    during = registry.update_from_detection([{"p1", "p2", "p3", "p4", "d1", "d2"}], cycle=2)
    assert {basin.basin_id for basin in during} == {"basin_0", daughter.basin_id}

    after = registry.update_from_detection([{"p1", "p2", "p3", "p4", "d1", "d2"}], cycle=5)
    assert {basin.basin_id for basin in after} == {"basin_0"}
    assert registry.get_basin(daughter.basin_id) is not None
    assert registry.get_basin(daughter.basin_id).status == "dormant"


def test_dormancy() -> None:
    registry = BasinRegistry()
    registry.update_from_detection([{"a", "b", "c"}], cycle=0)

    registry.update_from_detection([{"x", "y", "z"}], cycle=1)
    basin = registry.get_basin("basin_0")
    assert basin is not None
    assert basin.status == "dormant"

    registry.update_from_detection([{"a", "b", "c", "d"}], cycle=2)
    basin = registry.get_basin("basin_0")
    assert basin is not None
    assert basin.status == "active"


def test_registry_serialization() -> None:
    registry = BasinRegistry()
    registry.update_from_detection([{"a", "b", "c"}], cycle=0)
    registry.update_from_detection([{"a", "b", "c", "d"}], cycle=1)

    payload = registry.to_dict()
    restored = BasinRegistry.from_dict(json.loads(json.dumps(payload)))

    assert restored.to_dict() == payload
