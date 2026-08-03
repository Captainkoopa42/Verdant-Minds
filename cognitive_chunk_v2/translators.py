from __future__ import annotations

import hashlib
import io
import math
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .models import Modality


FEATURE_DIM = 512


def _normalize(vector: np.ndarray) -> np.ndarray:
    vector = np.nan_to_num(
        np.asarray(vector, dtype=np.float64),
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )
    norm = np.linalg.norm(vector)
    return vector if norm == 0 else vector / norm


def _pad(vector: np.ndarray, size: int = FEATURE_DIM) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float64).reshape(-1)
    output = np.zeros(size, dtype=np.float64)
    output[: min(size, vector.size)] = vector[:size]
    return _normalize(output)


@dataclass(frozen=True)
class TranslationOutput:
    features: np.ndarray
    metadata: dict[str, Any]
    uncertainty: float
    translator_id: str
    translator_version: str


class TextTranslator:
    translator_id = "native_text_hashgram"
    translator_version = "1.0"

    def translate(self, payload: bytes) -> TranslationOutput:
        text = payload.decode("utf-8")
        vector = np.zeros(FEATURE_DIM, dtype=np.float64)

        normalized = text.lower()
        encoded = normalized.encode("utf-8")
        for n in (1, 2, 3, 4):
            if len(encoded) < n:
                continue
            for index in range(len(encoded) - n + 1):
                gram = encoded[index:index + n]
                digest = hashlib.blake2b(
                    gram,
                    digest_size=8,
                    person=f"txt{n}".encode("ascii"),
                ).digest()
                bucket = int.from_bytes(digest, "little") % (FEATURE_DIM - 16)
                vector[bucket] += 1.0 / n

        stats = np.array(
            [
                len(text),
                len(text.split()),
                len(set(normalized)),
                sum(character.isalpha() for character in text),
                sum(character.isdigit() for character in text),
                sum(character.isspace() for character in text),
                sum(character in ".,!?;:" for character in text),
                text.count("\n"),
            ],
            dtype=np.float64,
        )
        vector[-len(stats):] = np.log1p(stats)
        return TranslationOutput(
            features=_normalize(np.log1p(vector)),
            metadata={
                "character_count": len(text),
                "word_count": len(text.split()),
                "encoding": "utf-8",
            },
            uncertainty=0.0,
            translator_id=self.translator_id,
            translator_version=self.translator_version,
        )


class ImageTranslator:
    translator_id = "native_visual_geometry"
    translator_version = "1.0"

    def translate(self, payload: bytes) -> TranslationOutput:
        image = Image.open(io.BytesIO(payload)).convert("RGB")
        resized = image.resize((64, 64), Image.Resampling.LANCZOS)
        rgb = np.asarray(resized, dtype=np.float64) / 255.0
        gray = (
            0.2126 * rgb[:, :, 0]
            + 0.7152 * rgb[:, :, 1]
            + 0.0722 * rgb[:, :, 2]
        )

        features: list[float] = []
        for grid in (1, 2, 4, 8):
            height = 64 // grid
            width = 64 // grid
            for row in range(grid):
                for column in range(grid):
                    cell = rgb[
                        row * height:(row + 1) * height,
                        column * width:(column + 1) * width,
                    ]
                    features.extend(cell.mean(axis=(0, 1)))
                    features.extend(cell.std(axis=(0, 1)))

        for channel in range(3):
            histogram, _ = np.histogram(
                rgb[:, :, channel],
                bins=24,
                range=(0.0, 1.0),
            )
            features.extend(
                histogram / (histogram.sum() + 1e-12)
            )

        grad_y, grad_x = np.gradient(gray)
        magnitude = np.sqrt(grad_x**2 + grad_y**2)
        orientation = np.mod(np.arctan2(grad_y, grad_x), np.pi)
        orientation_histogram, _ = np.histogram(
            orientation,
            bins=24,
            range=(0.0, np.pi),
            weights=magnitude,
        )
        features.extend(
            orientation_histogram
            / (orientation_histogram.sum() + 1e-12)
        )

        low = Image.fromarray(
            np.clip(gray * 255.0, 0, 255).astype(np.uint8)
        ).resize((16, 16), Image.Resampling.BILINEAR)
        features.extend(np.asarray(low, dtype=np.float64).reshape(-1) / 255.0)

        return TranslationOutput(
            features=_pad(np.asarray(features)),
            metadata={
                "width": image.width,
                "height": image.height,
                "mode": "RGB",
                "feature_families": [
                    "spatial_color",
                    "color_histogram",
                    "edge_orientation",
                    "low_resolution_geometry",
                ],
            },
            uncertainty=0.02,
            translator_id=self.translator_id,
            translator_version=self.translator_version,
        )


def _decode_wav(payload: bytes) -> tuple[np.ndarray, int]:
    with wave.open(io.BytesIO(payload), "rb") as handle:
        if handle.getsampwidth() != 2:
            raise ValueError("Audio translator expects 16-bit PCM WAV.")
        sample_rate = handle.getframerate()
        channels = handle.getnchannels()
        samples = np.frombuffer(
            handle.readframes(handle.getnframes()),
            dtype=np.int16,
        ).astype(np.float64) / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples, sample_rate


class AudioTranslator:
    translator_id = "native_audio_temporal_spectral"
    translator_version = "1.0"

    def translate(self, payload: bytes) -> TranslationOutput:
        samples, sample_rate = _decode_wav(payload)
        if samples.size == 0:
            raise ValueError("Audio payload contains no samples.")

        window_size = 1024
        hop = 512
        window = np.hanning(window_size)
        frames = []
        for start in range(0, max(1, len(samples) - window_size + 1), hop):
            frame = samples[start:start + window_size]
            if len(frame) < window_size:
                frame = np.pad(frame, (0, window_size - len(frame)))
            frames.append(np.abs(np.fft.rfft(frame * window)))
        spectrum = np.asarray(frames).T + 1e-12

        mean_spectrum = np.log1p(spectrum.mean(axis=1))
        spectral_sample = np.interp(
            np.linspace(0, len(mean_spectrum) - 1, 160),
            np.arange(len(mean_spectrum)),
            mean_spectrum,
        )

        temporal_features = []
        for segment in np.array_split(samples, 64):
            rms = math.sqrt(float(np.mean(segment**2)) + 1e-12)
            peak = float(np.max(np.abs(segment)))
            zcr = float(
                np.mean(
                    np.signbit(segment[1:])
                    != np.signbit(segment[:-1])
                )
            ) if len(segment) > 1 else 0.0
            temporal_features.extend([rms, peak, zcr])

        log_spectrum = np.log1p(spectrum)
        time_profile = log_spectrum.mean(axis=0)
        time_sample = np.interp(
            np.linspace(0, len(time_profile) - 1, 128),
            np.arange(len(time_profile)),
            time_profile,
        )

        features = np.concatenate(
            [
                spectral_sample,
                np.asarray(temporal_features),
                time_sample,
            ]
        )

        return TranslationOutput(
            features=_pad(features),
            metadata={
                "sample_rate": sample_rate,
                "sample_count": len(samples),
                "duration_seconds": len(samples) / sample_rate,
                "feature_families": [
                    "mean_spectral_shape",
                    "temporal_rms_peak_zcr",
                    "time_frequency_profile",
                ],
            },
            uncertainty=0.03,
            translator_id=self.translator_id,
            translator_version=self.translator_version,
        )


TRANSLATORS = {
    Modality.TEXT: TextTranslator(),
    Modality.IMAGE: ImageTranslator(),
    Modality.AUDIO: AudioTranslator(),
}


def translate(modality: Modality, payload: bytes) -> TranslationOutput:
    if modality not in TRANSLATORS:
        raise NotImplementedError(
            f"No translator is implemented for modality '{modality.value}'."
        )
    return TRANSLATORS[modality].translate(payload)
