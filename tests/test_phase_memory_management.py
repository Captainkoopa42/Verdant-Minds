from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
verdant_src_root = project_root / "Verdant Source Codes"
if str(verdant_src_root) not in sys.path:
    sys.path.insert(0, str(verdant_src_root))

from src.blocks.memory_storage_block import MemoryStorageBlock
from src.core.cognitive_chunk import CognitiveChunk


class _DummyMemoryWeb:
    def __init__(self):
        self.decay_calls = []
        self.reinforce_calls = []
        self.memory_store = {}

    def decay_memories(self, decay_factor=0.01, time_threshold=86400):
        self.decay_calls.append(decay_factor)
        return 0

    def reinforce_memory(self, label: str, amount: float = 0.1):
        self.reinforce_calls.append((label, amount))
        self.memory_store.setdefault(label, {"stability": 0.5})
        return 0.6


class _DummyBridge:
    def __init__(self):
        self.memory_web = _DummyMemoryWeb()

    def update_ecwf_from_memory(self, concepts):
        return {"processed_concepts": list(concepts), "cognitive_influence": [], "ethical_influence": []}


def _build_chunk(tg: float):
    chunk = CognitiveChunk()
    chunk.update_section("pattern_recognition_section", {
        "extracted_concepts": ["alpha", "beta"],
        "keywords": ["gamma"]
    })
    chunk.update_section("processing_metrics_section", {
        "glass_transition_temp": tg
    })
    return chunk


def test_phase_memory_management_uses_tg_for_decay_and_reinforcement():
    bridge = _DummyBridge()
    block = MemoryStorageBlock(memory_bridge=bridge)

    low_chunk = _build_chunk(0.2)
    low_out = block.process_chunk(low_chunk)
    low_section = low_out.get_section_content("memory_section")

    assert low_section["phase_memory_management"]["phase"] == "Rigid"
    assert low_section["phase_memory_management"]["decay_factor_applied"] == 0.005
    assert low_section["phase_memory_management"]["reinforcement_applied"] == 0.05
    assert low_section["phase_memory_management"]["concepts_reinforced"] > 0

    high_chunk = _build_chunk(0.8)
    high_out = block.process_chunk(high_chunk)
    high_section = high_out.get_section_content("memory_section")

    assert high_section["phase_memory_management"]["phase"] == "Chaotic"
    assert high_section["phase_memory_management"]["decay_factor_applied"] == 0.02
    assert high_section["phase_memory_management"]["reinforcement_applied"] == 0.15
    assert high_section["phase_memory_management"]["concepts_reinforced"] > 0

    assert 0.005 in bridge.memory_web.decay_calls
    assert 0.02 in bridge.memory_web.decay_calls

    reinforce_amounts = [amount for _, amount in bridge.memory_web.reinforce_calls]
    assert 0.05 in reinforce_amounts
    assert 0.15 in reinforce_amounts
