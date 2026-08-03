from __future__ import annotations

import hashlib
import io
import json
import mimetypes
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .archive import CognitiveChunkArchive, ResourceStore, sha256_bytes
from .models import (
    ClaimRecord,
    ClaimStatus,
    CognitiveChunkV2,
    CognitiveEffectRecord,
    Modality,
    ObservationRecord,
    PayloadRecord,
    PayloadRole,
    RevisionRecord,
    TranslationRecord,
)
from .permissions import ChunkWriter
from .substrate import PlumbingTestSubstrate, complex_similarity
from .translators import translate


@dataclass(frozen=True)
class ExperienceInput:
    modality: Modality
    source_id: str
    source_name: str
    media_type: str
    payload: bytes

    @classmethod
    def from_text(
        cls,
        text: str,
        *,
        source_id: str = "user_text",
        source_name: str = "experience.txt",
    ) -> "ExperienceInput":
        return cls(
            modality=Modality.TEXT,
            source_id=source_id,
            source_name=source_name,
            media_type="text/plain; charset=utf-8",
            payload=text.encode("utf-8"),
        )

    @classmethod
    def from_file(
        cls,
        path: Path,
        modality: Modality,
        *,
        source_id: str,
        media_type: str | None = None,
    ) -> "ExperienceInput":
        guessed = media_type or mimetypes.guess_type(path.name)[0]
        return cls(
            modality=modality,
            source_id=source_id,
            source_name=path.name,
            media_type=guessed or "application/octet-stream",
            payload=path.read_bytes(),
        )


@dataclass(frozen=True)
class RecallResult:
    modality: Modality
    payload_integrity: bool
    feature_similarity: float
    current_reinterpretation_similarity: float
    historical_replay_similarity: float
    hybrid_similarity: float


def _array_path(prefix: str, identifier: str) -> str:
    return f"{prefix}/{identifier}.npy"


class PipelineOrchestrator:
    BLOCK_ORDER = [
        "SensoryInput",
        "PatternRecognition",
        "MemoryStorage",
        "InternalCommunication",
        "ReasoningPlanning",
        "EthicsValues",
        "ActionSelection",
        "LanguageProcessing",
        "ContinualLearning",
    ]

    def __init__(self, substrate: PlumbingTestSubstrate | None = None):
        self.substrate = substrate or PlumbingTestSubstrate()

    def process(
        self,
        experience: ExperienceInput,
    ) -> tuple[CognitiveChunkV2, ResourceStore]:
        chunk = CognitiveChunkV2()
        store = ResourceStore()

        payload, observation, translation = self._sensory_input(
            chunk,
            store,
            experience,
        )
        self._pattern_recognition(chunk, translation)
        effect = self._memory_storage(
            chunk,
            store,
            payload,
            translation,
        )
        self._internal_communication(
            chunk,
            payload,
            translation,
            effect,
        )
        self._reasoning(chunk, payload, translation)
        self._ethics(chunk, observation, translation)
        self._action(chunk, payload)
        self._language(chunk, experience, payload, translation)
        self._learning(chunk, translation)

        return chunk, store

    def _sensory_input(
        self,
        chunk: CognitiveChunkV2,
        store: ResourceStore,
        experience: ExperienceInput,
    ) -> tuple[PayloadRecord, ObservationRecord, TranslationRecord]:
        writer = ChunkWriter(chunk, "SensoryInput")
        started = time.time()
        before = chunk.fingerprint()

        source_hash = sha256_bytes(experience.payload)
        extension = Path(experience.source_name).suffix or ".bin"
        payload_path = store.put_bytes(
            f"payloads/{source_hash}{extension}",
            experience.payload,
        )
        payload = PayloadRecord(
            modality=experience.modality,
            role=PayloadRole.PRIMARY,
            source_sha256=source_hash,
            media_type=experience.media_type,
            byte_length=len(experience.payload),
            storage_path=payload_path,
            source_name=experience.source_name,
        )
        writer.append("payloads", payload)

        translated = translate(
            experience.modality,
            experience.payload,
        )
        feature_path = store.put_array(
            _array_path("features", payload.payload_id),
            translated.features,
        )

        observation = ObservationRecord(
            payload_id=payload.payload_id,
            source_id=experience.source_id,
            measurement_type=f"{experience.modality.value}_payload_received",
            data={
                "byte_length": len(experience.payload),
                "media_type": experience.media_type,
                **translated.metadata,
            },
            confidence=1.0,
        )
        writer.append("observations", observation)

        translation = TranslationRecord(
            payload_id=payload.payload_id,
            modality=experience.modality,
            translator_id=translated.translator_id,
            translator_version=translated.translator_version,
            feature_ref=feature_path,
            feature_dim=int(translated.features.size),
            uncertainty=translated.uncertainty,
            assumptions=[
                "Translation is modality-native and non-semantic.",
                "The payload remains authoritative over the translation.",
            ],
        )
        writer.append("translations", translation)
        writer.set_section(
            "sensory_input_section",
            {
                "payload_ids": [payload.payload_id],
                "observation_ids": [observation.observation_id],
                "translation_ids": [translation.translation_id],
            },
        )
        writer.log(
            "receive_translate",
            input_refs=[experience.source_name],
            output_refs=[
                payload.payload_id,
                observation.observation_id,
                translation.translation_id,
            ],
            before_fingerprint=before,
            started_unix=started,
        )
        return payload, observation, translation

    def _pattern_recognition(
        self,
        chunk: CognitiveChunkV2,
        translation: TranslationRecord,
    ) -> None:
        writer = ChunkWriter(chunk, "PatternRecognition")
        started = time.time()
        before = chunk.fingerprint()
        claim = ClaimRecord(
            scope=f"native_signature:{translation.modality.value}",
            value={
                "translation_id": translation.translation_id,
                "feature_dim": translation.feature_dim,
            },
            status=ClaimStatus.SUPPORTED,
            evidence_refs=[translation.translation_id],
            created_by="PatternRecognition",
            confidence=1.0 - translation.uncertainty,
        )
        writer.append("claims", claim)
        writer.set_section(
            "pattern_recognition_section",
            {
                "claim_ids": [claim.claim_id],
                "semantic_labels_added": False,
            },
        )
        writer.log(
            "register_native_signature",
            input_refs=[translation.translation_id],
            output_refs=[claim.claim_id],
            before_fingerprint=before,
            started_unix=started,
        )

    def _memory_storage(
        self,
        chunk: CognitiveChunkV2,
        store: ResourceStore,
        payload: PayloadRecord,
        translation: TranslationRecord,
    ) -> CognitiveEffectRecord:
        writer = ChunkWriter(chunk, "MemoryStorage")
        started = time.time()
        before_fingerprint = chunk.fingerprint()

        features = store.get_array(translation.feature_ref)
        before, after, delta = self.substrate.apply_experience(
            features,
            payload.modality,
            payload.source_sha256,
        )
        before_ref = store.put_array(
            _array_path("effects", f"{payload.payload_id}_before"),
            before,
        )
        after_ref = store.put_array(
            _array_path("effects", f"{payload.payload_id}_after"),
            after,
        )
        delta_ref = store.put_array(
            _array_path("effects", f"{payload.payload_id}_delta"),
            delta,
        )
        effect = CognitiveEffectRecord(
            caused_by_refs=[
                payload.payload_id,
                translation.translation_id,
            ],
            subsystem="PlumbingTestSubstrate",
            state_before_ref=before_ref,
            state_after_ref=after_ref,
            state_delta_ref=delta_ref,
            effect_norm=float(np.linalg.norm(delta)),
        )
        writer.append("cognitive_effects", effect)
        writer.set_section(
            "memory_section",
            {
                "effect_ids": [effect.effect_id],
                "payload_sha256": payload.source_sha256,
                "substrate": "PlumbingTestSubstrate",
            },
        )
        writer.log(
            "apply_experience",
            input_refs=[
                payload.payload_id,
                translation.translation_id,
            ],
            output_refs=[effect.effect_id],
            before_fingerprint=before_fingerprint,
            started_unix=started,
        )
        return effect

    def _internal_communication(
        self,
        chunk: CognitiveChunkV2,
        payload: PayloadRecord,
        translation: TranslationRecord,
        effect: CognitiveEffectRecord,
    ) -> None:
        writer = ChunkWriter(chunk, "InternalCommunication")
        started = time.time()
        before = chunk.fingerprint()
        writer.set_section(
            "internal_communication_section",
            {
                "shared_refs": [
                    payload.payload_id,
                    translation.translation_id,
                    effect.effect_id,
                ],
                "priority": "preserve_native_experience",
            },
        )
        writer.log(
            "route_shared_references",
            input_refs=[
                payload.payload_id,
                translation.translation_id,
                effect.effect_id,
            ],
            output_refs=["internal_communication_section"],
            before_fingerprint=before,
            started_unix=started,
        )

    def _reasoning(
        self,
        chunk: CognitiveChunkV2,
        payload: PayloadRecord,
        translation: TranslationRecord,
    ) -> None:
        writer = ChunkWriter(chunk, "ReasoningPlanning")
        started = time.time()
        before = chunk.fingerprint()
        claim = ClaimRecord(
            scope="payload_reconstructable",
            value=True,
            status=ClaimStatus.HYPOTHESIS,
            evidence_refs=[
                payload.payload_id,
                translation.translation_id,
            ],
            created_by="ReasoningPlanning",
            confidence=0.75,
        )
        writer.append("claims", claim)
        writer.set_section(
            "reasoning_section",
            {
                "claim_ids": [claim.claim_id],
                "next_test": "round_trip_recall",
            },
        )
        writer.log(
            "form_round_trip_prediction",
            input_refs=[payload.payload_id],
            output_refs=[claim.claim_id],
            before_fingerprint=before,
            started_unix=started,
        )

    def _ethics(
        self,
        chunk: CognitiveChunkV2,
        observation: ObservationRecord,
        translation: TranslationRecord,
    ) -> None:
        writer = ChunkWriter(chunk, "EthicsValues")
        started = time.time()
        before = chunk.fingerprint()
        writer.set_section(
            "ethical_consideration_section",
            {
                "truth_policy": "translation_cannot_overwrite_observation",
                "observation_ids": [observation.observation_id],
                "translation_ids": [translation.translation_id],
                "commitment_threshold_adjustment": 0.0,
            },
        )
        writer.log(
            "enforce_epistemic_boundary",
            input_refs=[
                observation.observation_id,
                translation.translation_id,
            ],
            output_refs=["ethical_consideration_section"],
            before_fingerprint=before,
            started_unix=started,
        )

    def _action(
        self,
        chunk: CognitiveChunkV2,
        payload: PayloadRecord,
    ) -> None:
        writer = ChunkWriter(chunk, "ActionSelection")
        started = time.time()
        before = chunk.fingerprint()
        writer.set_section(
            "action_selection_section",
            {
                "selected_action": "persist_chunk",
                "payload_ids": [payload.payload_id],
            },
        )
        writer.log(
            "select_persistence",
            input_refs=[payload.payload_id],
            output_refs=["action_selection_section"],
            before_fingerprint=before,
            started_unix=started,
        )

    def _language(
        self,
        chunk: CognitiveChunkV2,
        experience: ExperienceInput,
        payload: PayloadRecord,
        translation: TranslationRecord,
    ) -> None:
        writer = ChunkWriter(chunk, "LanguageProcessing")
        started = time.time()
        before = chunk.fingerprint()
        writer.set_section(
            "language_processing_section",
            {
                "summary": (
                    f"Stored one {experience.modality.value} experience "
                    f"with {translation.feature_dim} native features."
                ),
                "canonical_representation": False,
                "payload_id": payload.payload_id,
            },
        )
        writer.log(
            "create_noncanonical_summary",
            input_refs=[
                payload.payload_id,
                translation.translation_id,
            ],
            output_refs=["language_processing_section"],
            before_fingerprint=before,
            started_unix=started,
        )

    def _learning(
        self,
        chunk: CognitiveChunkV2,
        translation: TranslationRecord,
    ) -> None:
        writer = ChunkWriter(chunk, "ContinualLearning")
        started = time.time()
        before = chunk.fingerprint()
        writer.set_section(
            "continual_learning_section",
            {
                "translator_id": translation.translator_id,
                "round_trip_validation": "pending_recall",
                "reliability_update": 0.0,
            },
        )
        writer.log(
            "register_pending_validation",
            input_refs=[translation.translation_id],
            output_refs=["continual_learning_section"],
            before_fingerprint=before,
            started_unix=started,
        )

    def save(
        self,
        path: Path,
        chunk: CognitiveChunkV2,
        store: ResourceStore,
    ) -> None:
        CognitiveChunkArchive.save(path, chunk, store)

    def recall(
        self,
        path: Path,
    ) -> RecallResult:
        chunk, store = CognitiveChunkArchive.load(path)
        if len(chunk.payloads) != 1:
            raise ValueError("The plumbing recall test expects one primary payload.")

        payload = chunk.payloads[0]
        translation_record = chunk.translations[0]
        effect_record = chunk.cognitive_effects[0]

        payload_bytes = store.get_bytes(payload.storage_path)
        payload_integrity = (
            sha256_bytes(payload_bytes) == payload.source_sha256
        )

        current_translation = translate(payload.modality, payload_bytes)
        stored_features = store.get_array(translation_record.feature_ref)
        feature_similarity = float(
            np.dot(stored_features, current_translation.features)
            / (
                np.linalg.norm(stored_features)
                * np.linalg.norm(current_translation.features)
                + 1e-12
            )
        )

        historical_after = store.get_array(effect_record.state_after_ref)
        historical_delta = store.get_array(effect_record.state_delta_ref)

        fresh_substrate = PlumbingTestSubstrate()
        current_effect = fresh_substrate.experience_effect(
            current_translation.features,
            payload.modality,
        )
        historical_effect = historical_after
        hybrid = historical_effect * 0.55 + current_effect * 0.45
        hybrid /= np.linalg.norm(hybrid) + 1e-12

        return RecallResult(
            modality=payload.modality,
            payload_integrity=payload_integrity,
            feature_similarity=feature_similarity,
            current_reinterpretation_similarity=complex_similarity(
                historical_effect,
                current_effect,
            ),
            historical_replay_similarity=complex_similarity(
                historical_effect,
                historical_after,
            ),
            hybrid_similarity=complex_similarity(
                historical_effect,
                hybrid,
            ),
        )
