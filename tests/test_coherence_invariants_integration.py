#!/usr/bin/env python3
"""Fast integration test for coherence invariants telemetry."""

import math
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path for proper package imports
project_root = Path(__file__).parent.parent
verdant_src_root = project_root / "Verdant Source Codes"
if str(verdant_src_root) not in sys.path:
    sys.path.insert(0, str(verdant_src_root))

from src.core.system import UnifiedSystem


class _NoOpKing:
    def oversee_processing(self, chunk):
        return chunk


class _NoOpThreeKingsLayer:
    def __init__(self):
        self.data_king = _NoOpKing()
        self.ethics_king = _NoOpKing()
        self.forefront_king = _NoOpKing()

    def oversee_processing(self, chunk):
        return chunk


def _ensure_block_has_process_chunk(system: UnifiedSystem, block_name: str):
    """Attach a no-op process_chunk for known non-processing blocks in tests."""
    block = system.blocks[block_name]
    block.process_chunk = lambda chunk: chunk


def test_process_input_writes_coherence_invariants_sections():
    """process_input should emit first-class coherence invariant telemetry sections."""
    config = {
        "cognitive_dimensions": 3,
        "ethical_dimensions": 3,
        "wave_facets": 5,
        "bridge_influence_factor": 0.3,
        "learning_rate": 0.05,
        "decision_threshold": 0.7,
        "ethical_sensitivity": 0.6,
        "initialize_knowledge": False,
        "log_level": "WARNING",
    }

    # Mirror existing test strategy for heavy deps and patch kings with no-op layer.
    with patch.dict("sys.modules", {"tensorflow": MagicMock(), "torch": MagicMock()}):
        with patch("src.core.system.ThreeKingsLayer", _NoOpThreeKingsLayer):
            system = UnifiedSystem(seed=42, config=config)

    # Keep continual-learning out of this fast telemetry test path.
    _ensure_block_has_process_chunk(system, "ContinualLearning")

    chunk = system.process_input("Hello, can you summarize this topic?")

    coherence = chunk.get_section_content("coherence_invariants_section")
    assert coherence is not None

    processing_metrics = chunk.get_section_content("processing_metrics_section")
    assert processing_metrics is not None
    assert "coherence_invariants" in processing_metrics

    wave_function = chunk.get_section_content("wave_function_section")
    assert isinstance(wave_function, dict)
    assert "magnitude" in wave_function
    assert "phase" in wave_function
    assert "entropy" in wave_function

    assert "alpha_grid_used" in coherence
    assert "alpha_crit_estimate" in coherence
    assert "triangle_valid_at_alpha1" in coherence
    assert "triple_pqr" in coherence
    assert "housed_contradiction_index" in coherence
    assert math.isfinite(coherence["housed_contradiction_index"])
    assert "violation_rate" in coherence
    assert 0.0 <= coherence["violation_rate"] <= 1.0

    assert isinstance(coherence["triangle_valid_at_alpha1"], bool)

    alpha_crit = coherence["alpha_crit_estimate"]
    assert (
        alpha_crit is None
        or isinstance(alpha_crit, (int, float))
        or (isinstance(alpha_crit, float) and math.isnan(alpha_crit))
    )

    triple = coherence["triple_pqr"]
    assert hasattr(triple, "__len__")
    assert len(triple) == 3
