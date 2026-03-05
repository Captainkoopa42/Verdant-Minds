#!/usr/bin/env python3
"""Tests for MemoryStorageBlock wave property derivation from memory bridge state."""

import math
import sys
from pathlib import Path


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "Verdant Source Codes" / "src"))

from blocks.MemoryStorageBlock import MemoryStorageBlock
from core.CognitiveChunk import CognitiveChunk


class MockMemoryBridge:
    """Simple bridge stub returning deterministic cognitive influence values."""

    def __init__(self):
        self.edge_policy = "default"

    def update_ecwf_from_memory(self, concepts):
        return {
            "processed_concepts": list(concepts),
            "cognitive_influence": [0.2, 0.8],
            "ethical_influence": [0.1, 0.9],
        }


def test_process_chunk_derives_entropy_and_magnitude_from_bridge():
    block = MemoryStorageBlock(max_size=100)
    block.set_memory_bridge(MockMemoryBridge())

    chunk = CognitiveChunk()
    chunk.update_section(
        "pattern_recognition_section",
        {
            "concepts": ["hci", "emergence"],
            "extracted_concepts": [],
            "keywords": [],
        },
    )

    processed = block.process_chunk(chunk)

    wave_function_section = processed.get_section_content("wave_function_section")
    assert wave_function_section is not None

    expected_entropy = -(
        (0.2 * math.log2(0.2)) + (0.8 * math.log2(0.8))
    ) / math.log2(2)

    assert wave_function_section["entropy"] != 0.5
    assert wave_function_section["magnitude"] != 0.0
    assert wave_function_section["magnitude"] == 0.5
    assert wave_function_section["entropy"] == expected_entropy
