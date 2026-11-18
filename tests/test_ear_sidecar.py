"""sidecar_ear: the fine ear inside the real sensory pipeline."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path[:0] = [str(Path(__file__).resolve().parents[1])]
from verdant_kernel import VerdantKernel  # noqa: E402
from verdant_sensory.pipeline import NativeModality, NativeSamplePacket, VerdantSensoryPipeline  # noqa: E402

import sidecar_ear  # noqa: E402


def _packet(f0, n=1):
    t = np.arange(4800) / 8000; s = 0.5 * np.sin(2 * np.pi * f0 * t) + 0.2 * np.sin(2 * np.pi * 2 * f0 * t)
    return NativeSamplePacket(stream_id="mic", sequence_number=n, timestamp_ns=n * 10**9, modality=NativeModality.AUDIO,
                              media_type="audio/pcm", payload=(s * 32767 * 0.8).astype("<i2").tobytes(), sample_rate_hz=8000)


def test_fine_ear_replaces_only_the_description(tmp_path):
    k = VerdantKernel(seed=1, state_dim=64, run_label="ear"); pipe = VerdantSensoryPipeline()
    stock = pipe.translate(k, _packet(220), None)
    sidecar_ear.install_fine_ear(48)
    try:
        fine = pipe.translate(k, _packet(220), None)
        assert len(stock.feature_vector) == 10 and len(fine.feature_vector) == 48
        assert fine.native_signature == stock.native_signature and fine.delta_score == stock.delta_score
        assert fine.details["translation_kind"] == "fine_ear_log_bands"
        assert abs(sum(fine.feature_vector)) < 1e-9                                       # level removed
        loud = pipe.translate(k, _packet(220), None)
        assert np.allclose(fine.feature_vector, loud.feature_vector)
        assert not np.allclose(fine.feature_vector, pipe.translate(k, _packet(330), None).feature_vector)
        got = pipe.ingest_samples(k, [_packet(220)], batch_key="b1", archive_path=tmp_path / "a.tar")
        assert len(got.samples[0].feature_vector) == 48
    finally:
        sidecar_ear.uninstall_fine_ear()
    assert pipe.translate(k, _packet(220), None).feature_vector == stock.feature_vector
