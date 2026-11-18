"""A fine ear for the real sensory pipeline (opt-in; no file under verdant_* is edited).

The built-in audio translator hands the field 10 numbers (mean, RMS, mean |x|, peak, zero
crossings, centroid, three band shares, change). Measured in docs/RECOGNITION_IN_THE_WAVE_V0.md:
enough to tell trained voices apart, not enough to call a new voice new (7 of 8 slipped through).

install_fine_ear(bands=48) makes VerdantSensoryPipeline._translate_audio hand the field the log
energy in `bands` bands spaced evenly in pitch (80 Hz up to 0.95 of the Nyquist frequency, at most
8 kHz), with the overall level removed (the mean is subtracted), so the description says what the
sound is, not how loud it is. The pipeline's own change signature (used for change detection and
synchronisation) is kept exactly as stock. Details record translation_kind = "fine_ear_log_bands".

The field width for a modality is fixed by its description width, so an organism should not mix
sounds heard with the built-in ear and with the fine ear: they enter through different doorways.
"""
from __future__ import annotations

import dataclasses

import numpy as np

_ORIGINAL: dict = {}
_SETTINGS = {"bands": 48}


def fine_bands(pcm: np.ndarray, rate: float, bands: int = 48) -> np.ndarray:
    window = np.hanning(pcm.size) if pcm.size > 1 else np.ones(1)
    power = np.abs(np.fft.rfft(pcm * window)) ** 2; freqs = np.fft.rfftfreq(pcm.size, 1.0 / rate)
    top = min(8000.0, 0.95 * rate / 2.0); edges = np.geomspace(80.0, top, bands + 1)
    energy = np.array([power[(freqs >= lo) & (freqs < hi)].sum() for lo, hi in zip(edges[:-1], edges[1:])]) + 1e-12
    level = np.log(energy)
    return level - level.mean()


def _fine_translate_audio(self, packet, previous_signature, bins):
    stock = _ORIGINAL["_translate_audio"](self, packet, previous_signature, bins)   # keeps every stock check and the signature
    pcm = np.frombuffer(packet.payload, dtype="<i2").astype(np.float64) / 32768.0
    feats = fine_bands(pcm, float(packet.sample_rate_hz), _SETTINGS["bands"])
    return dataclasses.replace(stock, feature_vector=tuple(float(v) for v in feats),
        details={**stock.details, "translation_kind": "fine_ear_log_bands", "stock_translation_kind": stock.details.get("translation_kind"),
                 "fine_ear_bands": _SETTINGS["bands"]})


def install_fine_ear(bands: int = 48) -> None:
    from verdant_sensory.pipeline import VerdantSensoryPipeline
    _SETTINGS["bands"] = bands
    if not _ORIGINAL:
        _ORIGINAL["_translate_audio"] = VerdantSensoryPipeline._translate_audio
        VerdantSensoryPipeline._translate_audio = _fine_translate_audio


def uninstall_fine_ear() -> None:
    from verdant_sensory.pipeline import VerdantSensoryPipeline
    if _ORIGINAL:
        VerdantSensoryPipeline._translate_audio = _ORIGINAL.pop("_translate_audio")
