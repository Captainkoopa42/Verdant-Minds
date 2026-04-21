from __future__ import annotations

from verdant_memory import Memory


def test_memory_api_observe_retrieve_update_snapshot_load_roundtrip() -> None:
    mem = Memory()

    observed = mem.observe("hello world")
    assert observed.memory_size >= 0

    updated = mem.update(
        {
            "concepts": [{"label": "hello", "stability": 0.7, "metadata": {"source": "test"}}],
            "edges": [{"source": "hello", "target": "world", "weight": 0.4}],
            "reinforce": [{"label": "hello", "amount": 0.2}],
        }
    )
    assert updated.concepts_added >= 0

    retrieved = mem.retrieve("hello")
    assert retrieved.query == "hello"

    snap = mem.snapshot()
    assert snap.schema_version == "verdant-memory.v1"
    assert isinstance(snap.internal_state, dict)

    mem2 = Memory()
    mem2.load(snap)
    retrieved2 = mem2.retrieve("hello")
    assert retrieved2.query == "hello"
