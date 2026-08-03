from __future__ import annotations

from cognitive_chunk_v2.archive import ResourceStore
from cognitive_chunk_v2.models import CognitiveChunkV2

from .kernel import ExperienceResult, VerdantKernel
from .models import ExperienceCommand


def ingest_cognitive_chunk(
    kernel: VerdantKernel,
    chunk: CognitiveChunkV2,
    store: ResourceStore,
    *,
    event_key: str | None = None,
) -> tuple[ExperienceResult, ...]:
    """
    Safely imports native CognitiveChunk v2 payload/translation evidence.

    This adapter intentionally does not promote semantic concepts from chunk
    summaries or claims. Semantic promotion belongs to the later grammar and
    evidence-safe MemoryWeb migration.
    """

    observations_by_payload = {
        observation.payload_id: observation for observation in chunk.observations
    }
    translations_by_payload = {
        translation.payload_id: translation for translation in chunk.translations
    }
    results: list[ExperienceResult] = []

    for index, payload in enumerate(chunk.payloads):
        translation = translations_by_payload.get(payload.payload_id)
        if translation is None:
            raise ValueError(
                f"Payload '{payload.payload_id}' has no translation record."
            )
        observation = observations_by_payload.get(payload.payload_id)
        source_ref = (
            observation.source_id if observation is not None else payload.source_name
        ) or payload.payload_id
        features = store.get_array(translation.feature_ref)
        command = ExperienceCommand(
            event_key=(
                f"{event_key}:{index}"
                if event_key is not None
                else f"chunk:{chunk.identity.chunk_id}:{payload.payload_id}"
            ),
            source_ref=source_ref,
            modality=payload.modality.value,
            payload_sha256=payload.source_sha256,
            feature_vector=tuple(float(value) for value in features.reshape(-1)),
            confidence=(
                observation.confidence if observation is not None else 1.0
            ),
            metadata={
                # Deliberately exclude random chunk/payload/translation IDs from
                # the canonical command. The source hash and storage path retain
                # the native-data link while deterministic replay remains exact.
                "payload_storage_path": payload.storage_path,
                "translator_id": translation.translator_id,
                "translator_version": translation.translator_version,
                "source_name": payload.source_name,
                "media_type": payload.media_type,
            },
        )
        results.append(kernel.apply_experience(command))
    return tuple(results)
