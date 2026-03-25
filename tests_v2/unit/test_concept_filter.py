from __future__ import annotations

from ethomorphic.bridge.bridge import EthomorphicBridge
from ethomorphic.ecwf.core import ECWFCore

from verdant_v2.memory.graph import MemoryWeb
from verdant_v2.pipeline.blocks.memory import MemoryBlock


def _make_block(*, seeded: set[str] | None = None, min_len: int = 3, filter_numeric: bool = True) -> MemoryBlock:
    memory = MemoryWeb()
    bridge = EthomorphicBridge(
        memory=memory,
        ecwf=ECWFCore(num_cognitive_dims=3, num_ethical_dims=3, random_state=7),
    )
    return MemoryBlock(
        memory_web=memory,
        bridge=bridge,
        concept_min_length=min_len,
        filter_numeric_concepts=filter_numeric,
        seeded_concepts=seeded,
    )


def test_numeric_strings_are_filtered() -> None:
    block = _make_block()
    assert block._should_seed_concept("499") is False


def test_short_tokens_are_filtered() -> None:
    block = _make_block(min_len=3)
    assert block._should_seed_concept("ai") is False


def test_basin_ids_are_filtered() -> None:
    block = _make_block()
    assert block._should_seed_concept("basin_42") is False


def test_real_concepts_pass() -> None:
    block = _make_block()
    assert block._should_seed_concept("autonomy") is True


def test_seeded_concepts_are_never_filtered() -> None:
    block = _make_block(seeded={"ai"})
    assert block._should_seed_concept("ai") is True
