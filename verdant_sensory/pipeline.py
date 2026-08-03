from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from verdant_kernel import (
    ExperienceCommand,
    NativeModality,
    SensoryArchiveRecord,
    SensoryIntegrityError,
    SensorySampleRecord,
    SensoryStaleError,
    SynchronizationGroupRecord,
    TemporalBoundaryReason,
    TemporalEventAssemblyEvent,
    TemporalEventAssemblyReport,
    TemporalEventRecord,
    VerdantKernel,
)
from verdant_kernel.models import canonical_json_bytes, stable_id

from .archive import build_archive, verify_archive


@dataclass(frozen=True)
class NativeSamplePacket:
    stream_id: str
    sequence_number: int
    timestamp_ns: int
    modality: NativeModality
    media_type: str
    payload: bytes
    clock_domain: str = "monotonic"
    shape: tuple[int, ...] = ()
    sample_rate_hz: int | None = None
    channel_names: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.stream_id.strip() or not self.clock_domain.strip() or not self.media_type.strip():
            raise ValueError("Native sample identity fields cannot be empty.")
        if self.sequence_number < 0 or self.timestamp_ns < 0:
            raise ValueError("Native sample sequence and timestamp must be nonnegative.")
        if not isinstance(self.payload, bytes) or not self.payload:
            raise ValueError("Native sample payload must be nonempty bytes.")
        if any(item <= 0 for item in self.shape):
            raise ValueError("Native sample shape dimensions must be positive.")
        if self.sample_rate_hz is not None and self.sample_rate_hz <= 0:
            raise ValueError("Native sample rate must be positive.")
        cleaned = tuple(item.strip() for item in self.channel_names)
        if cleaned != self.channel_names or any(not item for item in cleaned):
            raise ValueError("Native channel names must be nonempty and stripped.")


@dataclass(frozen=True)
class TranslationResult:
    feature_vector: tuple[float, ...]
    native_signature: tuple[float, ...]
    delta_score: float
    details: dict[str, Any]


@dataclass(frozen=True)
class SensoryIngestionResult:
    archive: SensoryArchiveRecord
    samples: tuple[SensorySampleRecord, ...]
    archive_path: Path


@dataclass(frozen=True)
class SensoryBatchResult:
    archive: SensoryArchiveRecord
    samples: tuple[SensorySampleRecord, ...]
    report: TemporalEventAssemblyReport
    assembly_event: TemporalEventAssemblyEvent
    archive_path: Path


class VerdantSensoryPipeline:
    """Minimal, deterministic, nonsemantic sensor translation and event memory."""

    _MODALITY_ORDER = {
        NativeModality.VISION: 0,
        NativeModality.AUDIO: 1,
    }

    def _sample_id(self, packet: NativeSamplePacket, translator_revision: int) -> str:
        digest = hashlib.sha256(packet.payload).hexdigest()
        return stable_id(
            "sensory_sample",
            packet.stream_id,
            packet.sequence_number,
            packet.timestamp_ns,
            packet.clock_domain,
            packet.modality.value,
            packet.media_type,
            digest,
            len(packet.payload),
            packet.shape,
            packet.sample_rate_hz,
            packet.channel_names,
            translator_revision,
        )

    @staticmethod
    def _delta(current: Sequence[float], previous: Sequence[float] | None) -> float:
        if previous is None:
            return 0.0
        a = np.asarray(tuple(current), dtype=np.float64)
        b = np.asarray(tuple(previous), dtype=np.float64)
        if a.shape != b.shape or a.size == 0:
            return 1.0
        return float(min(1.0, np.linalg.norm(a - b) / math.sqrt(a.size)))

    @staticmethod
    def _block_signature(image: np.ndarray, side: int) -> np.ndarray:
        rows = np.array_split(image, side, axis=0)
        values: list[float] = []
        for row in rows:
            for block in np.array_split(row, side, axis=1):
                values.append(float(np.mean(block)) if block.size else 0.0)
        return np.asarray(values, dtype=np.float64)

    def _translate_vision(
        self,
        packet: NativeSamplePacket,
        previous_signature: Sequence[float] | None,
        side: int,
    ) -> TranslationResult:
        if len(packet.shape) not in {2, 3}:
            raise SensoryIntegrityError("Vision payload shape must be HxW or HxWxC.")
        expected = math.prod(packet.shape)
        if len(packet.payload) != expected:
            raise SensoryIntegrityError("Vision payload length does not match its shape.")
        array = np.frombuffer(packet.payload, dtype=np.uint8).reshape(packet.shape)
        if array.ndim == 3:
            if array.shape[2] not in {1, 3, 4}:
                raise SensoryIntegrityError("Vision channels must be 1, 3, or 4.")
            gray = np.mean(array[..., :3], axis=2) / 255.0
        else:
            gray = array.astype(np.float64) / 255.0
        signature = self._block_signature(gray, side)
        total = float(np.sum(gray))
        if total > 1e-12:
            yy, xx = np.indices(gray.shape)
            cx = float(np.sum(xx * gray) / total / max(1, gray.shape[1] - 1))
            cy = float(np.sum(yy * gray) / total / max(1, gray.shape[0] - 1))
        else:
            cx = cy = 0.5
        gx = float(np.mean(np.abs(np.diff(gray, axis=1)))) if gray.shape[1] > 1 else 0.0
        gy = float(np.mean(np.abs(np.diff(gray, axis=0)))) if gray.shape[0] > 1 else 0.0
        delta = self._delta(signature, previous_signature)
        features = (
            float(np.mean(gray)),
            float(np.std(gray)),
            float(np.min(gray)),
            float(np.max(gray)),
            cx,
            cy,
            gx,
            gy,
            delta,
        )
        return TranslationResult(
            feature_vector=features,
            native_signature=tuple(float(item) for item in signature),
            delta_score=delta,
            details={
                "translation_kind": "low_level_luminance_geometry",
                "semantic_categories_supplied": False,
                "signature_side": side,
            },
        )

    def _translate_audio(
        self,
        packet: NativeSamplePacket,
        previous_signature: Sequence[float] | None,
        bins: int,
    ) -> TranslationResult:
        if packet.sample_rate_hz is None:
            raise SensoryIntegrityError("PCM audio requires a sample rate.")
        if len(packet.payload) % 2:
            raise SensoryIntegrityError("PCM16 audio payload must contain whole samples.")
        pcm = np.frombuffer(packet.payload, dtype="<i2").astype(np.float64) / 32768.0
        if not pcm.size:
            raise SensoryIntegrityError("Audio payload contains no samples.")
        spectrum = np.abs(np.fft.rfft(pcm))
        spectrum_total = float(np.sum(spectrum))
        frequencies = np.fft.rfftfreq(pcm.size, d=1.0 / packet.sample_rate_hz)
        centroid = (
            float(np.sum(frequencies * spectrum) / spectrum_total)
            / max(1.0, packet.sample_rate_hz / 2.0)
            if spectrum_total > 1e-12
            else 0.0
        )
        signature = np.asarray(
            [float(np.mean(chunk)) if chunk.size else 0.0 for chunk in np.array_split(spectrum, bins)],
            dtype=np.float64,
        )
        norm = float(np.linalg.norm(signature))
        if norm > 1e-12:
            signature /= norm
        zcr = float(np.mean(np.signbit(pcm[1:]) != np.signbit(pcm[:-1]))) if pcm.size > 1 else 0.0
        thirds = np.array_split(spectrum, 3)
        band_energy = [float(np.sum(part) / spectrum_total) if spectrum_total else 0.0 for part in thirds]
        delta = self._delta(signature, previous_signature)
        features = (
            float(np.mean(pcm)),
            float(np.sqrt(np.mean(pcm**2))),
            float(np.mean(np.abs(pcm))),
            float(np.max(np.abs(pcm))),
            zcr,
            centroid,
            *band_energy,
            delta,
        )
        return TranslationResult(
            feature_vector=tuple(features),
            native_signature=tuple(float(item) for item in signature),
            delta_score=delta,
            details={
                "translation_kind": "pcm_energy_zero_crossing_spectrum",
                "semantic_categories_supplied": False,
                "signature_bins": bins,
            },
        )


    def translate(
        self,
        kernel: VerdantKernel,
        packet: NativeSamplePacket,
        previous_signature: Sequence[float] | None,
    ) -> TranslationResult:
        policy = kernel.state.sensory_policy
        if packet.modality == NativeModality.VISION:
            return self._translate_vision(packet, previous_signature, policy.vision_signature_side)
        if packet.modality == NativeModality.AUDIO:
            return self._translate_audio(packet, previous_signature, policy.audio_signature_bins)
        raise SensoryIntegrityError(f"Unsupported native modality {packet.modality!r}.")

    def _descriptor(self, packet: NativeSamplePacket, sample_id: str) -> dict[str, object]:
        digest = hashlib.sha256(packet.payload).hexdigest()
        return {
            "sample_id": sample_id,
            "member_path": f"samples/{sample_id}.bin",
            "stream_id": packet.stream_id,
            "sequence_number": packet.sequence_number,
            "timestamp_ns": packet.timestamp_ns,
            "clock_domain": packet.clock_domain,
            "modality": packet.modality.value,
            "media_type": packet.media_type,
            "payload_sha256": digest,
            "payload_nbytes": len(packet.payload),
            "shape": list(packet.shape),
            "sample_rate_hz": packet.sample_rate_hz,
            "channel_names": list(packet.channel_names),
            "native_metadata": packet.metadata,
        }

    def ingest_samples(
        self,
        kernel: VerdantKernel,
        packets: Sequence[NativeSamplePacket],
        *,
        batch_key: str,
        archive_path: Path,
    ) -> SensoryIngestionResult:
        if not batch_key.strip():
            raise ValueError("Sensory batch key cannot be empty.")
        if not packets:
            raise ValueError("Sensory batch cannot be empty.")
        policy = kernel.state.sensory_policy
        ordered = sorted(
            packets,
            key=lambda item: (
                item.timestamp_ns,
                self._MODALITY_ORDER[item.modality],
                item.stream_id,
                item.sequence_number,
            ),
        )
        existing_latest: dict[str, SensorySampleRecord] = {}
        for existing in kernel.state.sensory_samples.values():
            prior = existing_latest.get(existing.stream_id)
            if prior is None or existing.sequence_number > prior.sequence_number:
                existing_latest[existing.stream_id] = existing
        first_by_stream: dict[str, NativeSamplePacket] = {}
        for packet in ordered:
            first_by_stream.setdefault(packet.stream_id, packet)
        for stream_id, first_packet in first_by_stream.items():
            prior = existing_latest.get(stream_id)
            if prior is None:
                continue
            if first_packet.sequence_number <= prior.sequence_number:
                raise SensoryIntegrityError(
                    "Sensory batch would roll back an existing stream sequence."
                )
            if first_packet.timestamp_ns < prior.timestamp_ns:
                raise SensoryIntegrityError(
                    "Sensory batch would move an existing stream timestamp backward."
                )

        stream_sequence: dict[str, int] = {}
        descriptors: list[dict[str, object]] = []
        payloads: dict[str, bytes] = {}
        packet_by_id: dict[str, NativeSamplePacket] = {}
        for packet in ordered:
            prior_sequence = stream_sequence.get(packet.stream_id)
            if prior_sequence is not None and packet.sequence_number <= prior_sequence:
                raise SensoryIntegrityError("Batch stream sequence must advance monotonically.")
            stream_sequence[packet.stream_id] = packet.sequence_number
            sample_id = self._sample_id(packet, policy.translator_revision)
            if sample_id in packet_by_id:
                raise SensoryIntegrityError("Duplicate native sample detected in batch.")
            packet_by_id[sample_id] = packet
            descriptors.append(self._descriptor(packet, sample_id))
            payloads[sample_id] = packet.payload
        archive_record = build_archive(
            archive_path,
            batch_key=batch_key,
            entries=descriptors,
            payloads=payloads,
        )
        verified = verify_archive(archive_path)
        if verified.model_copy(update={"created_cycle": archive_record.created_cycle}) != archive_record:
            raise SensoryIntegrityError("Written sensory archive failed deterministic verification.")
        registered = kernel.register_sensory_archive(archive_record)

        committed: list[SensorySampleRecord] = []
        for descriptor in sorted(descriptors, key=lambda item: (
            int(item["timestamp_ns"]),
            self._MODALITY_ORDER[NativeModality(str(item["modality"]))],
            str(item["stream_id"]),
        )):
            sample_id = str(descriptor["sample_id"])
            packet = packet_by_id[sample_id]
            prior = max(
                (
                    item
                    for item in kernel.state.sensory_samples.values()
                    if item.stream_id == packet.stream_id
                ),
                key=lambda item: item.sequence_number,
                default=None,
            )
            translated = self.translate(
                kernel,
                packet,
                prior.native_signature if prior is not None else None,
            )
            payload_digest = str(descriptor["payload_sha256"])
            member_path = str(descriptor["member_path"])
            source_ref = f"sensory://{registered.archive_id}/{member_path}"
            experience = kernel.apply_experience(
                ExperienceCommand(
                    event_key=f"sensory:{sample_id}",
                    source_ref=source_ref,
                    modality=f"native_{packet.modality.value}",
                    payload_sha256=payload_digest,
                    feature_vector=translated.feature_vector,
                    metadata={
                        "native_sensory": True,
                        "sample_id": sample_id,
                        "stream_id": packet.stream_id,
                        "sequence_number": packet.sequence_number,
                        "timestamp_ns": packet.timestamp_ns,
                        "clock_domain": packet.clock_domain,
                        "media_type": packet.media_type,
                        "archive_id": registered.archive_id,
                        "archive_member_path": member_path,
                        "semantic_categories_supplied": False,
                        **translated.details,
                    },
                )
            )
            record = SensorySampleRecord(
                sample_id=sample_id,
                archive_id=registered.archive_id,
                archive_member_path=member_path,
                stream_id=packet.stream_id,
                sequence_number=packet.sequence_number,
                timestamp_ns=packet.timestamp_ns,
                clock_domain=packet.clock_domain,
                modality=packet.modality,
                media_type=packet.media_type,
                payload_sha256=payload_digest,
                payload_nbytes=len(packet.payload),
                shape=packet.shape,
                sample_rate_hz=packet.sample_rate_hz,
                channel_names=packet.channel_names,
                feature_vector=translated.feature_vector,
                native_signature=translated.native_signature,
                delta_score=translated.delta_score,
                previous_sample_id=prior.sample_id if prior is not None else None,
                observation_evidence_id=experience.observation_evidence_id,
                translation_evidence_id=experience.translation_evidence_id,
                committed_cycle=kernel.state.cycle + 1,
                translator_revision=policy.translator_revision,
                metadata={
                    "semantic_categories_supplied": False,
                    **packet.metadata,
                    **translated.details,
                },
            )
            committed.append(kernel.commit_sensory_sample(record))
        return SensoryIngestionResult(
            archive=registered,
            samples=tuple(committed),
            archive_path=Path(archive_path),
        )

    def ingest_batch(
        self,
        kernel: VerdantKernel,
        packets: Sequence[NativeSamplePacket],
        *,
        batch_key: str,
        archive_path: Path,
    ) -> SensoryBatchResult:
        ingestion = self.ingest_samples(
            kernel,
            packets,
            batch_key=batch_key,
            archive_path=archive_path,
        )
        sample_ids = tuple(sorted(item.sample_id for item in ingestion.samples))
        report = self.inspect_temporal_events(kernel, sample_ids)
        assembly = self.commit_temporal_events(kernel, report)
        return SensoryBatchResult(
            archive=ingestion.archive,
            samples=ingestion.samples,
            report=report,
            assembly_event=assembly,
            archive_path=ingestion.archive_path,
        )

    @staticmethod
    def _sample_summary(sample: SensorySampleRecord) -> tuple[float, float, float, float]:
        vector = np.asarray(sample.feature_vector, dtype=np.float64)
        return (
            float(np.mean(vector)),
            float(np.std(vector)),
            float(np.linalg.norm(vector) / math.sqrt(vector.size)),
            float(np.max(np.abs(vector))),
        )

    def _group_summary(
        self,
        samples: Iterable[SensorySampleRecord],
    ) -> tuple[float, ...]:
        by_modality = {item.modality: item for item in samples}
        values: list[float] = []
        for modality in (NativeModality.VISION, NativeModality.AUDIO):
            sample = by_modality.get(modality)
            values.extend(self._sample_summary(sample) if sample is not None else (0.0, 0.0, 0.0, 0.0))
        return tuple(values)

    @staticmethod
    def _summary_change(left: Sequence[float], right: Sequence[float]) -> float:
        a = np.asarray(left, dtype=np.float64)
        b = np.asarray(right, dtype=np.float64)
        return float(min(1.0, np.linalg.norm(a - b) / math.sqrt(a.size)))

    def _synchronize(
        self,
        kernel: VerdantKernel,
        sample_ids: Sequence[str],
    ) -> tuple[SynchronizationGroupRecord, ...]:
        tolerance = kernel.state.sensory_policy.synchronization_tolerance_ns
        records = sorted(
            (kernel.state.sensory_samples[item] for item in sample_ids),
            key=lambda item: (
                item.timestamp_ns,
                self._MODALITY_ORDER[item.modality],
                item.stream_id,
                item.sequence_number,
            ),
        )
        groups: list[SynchronizationGroupRecord] = []
        index = 0
        while index < len(records):
            anchor = records[index]
            selected = [anchor]
            modalities = {anchor.modality}
            index += 1
            while index < len(records):
                candidate = records[index]
                if candidate.timestamp_ns - anchor.timestamp_ns > tolerance:
                    break
                if candidate.modality in modalities:
                    break
                selected.append(candidate)
                modalities.add(candidate.modality)
                index += 1
            timestamps = [item.timestamp_ns for item in selected]
            sample_tuple = tuple(sorted(item.sample_id for item in selected))
            modality_tuple = tuple(
                NativeModality(value)
                for value in sorted(item.value for item in modalities)
            )
            evidence = tuple(
                sorted(
                    {
                        ref
                        for item in selected
                        for ref in (item.observation_evidence_id, item.translation_evidence_id)
                    }
                )
            )
            summary = self._group_summary(selected)
            anchor_timestamp = int(round(sum(timestamps) / len(timestamps)))
            skew = max(timestamps) - min(timestamps)
            complete = len(modalities) >= kernel.state.sensory_policy.minimum_modalities_per_group
            group_id = stable_id(
                "sensory_sync_group",
                anchor_timestamp,
                sample_tuple,
                tuple(item.value for item in modality_tuple),
                skew,
                complete,
                evidence,
                summary,
            )
            groups.append(
                SynchronizationGroupRecord(
                    group_id=group_id,
                    anchor_timestamp_ns=anchor_timestamp,
                    sample_ids=sample_tuple,
                    modalities=modality_tuple,
                    maximum_skew_ns=skew,
                    complete=complete,
                    evidence_refs=evidence,
                    summary_vector=summary,
                )
            )
        return tuple(groups)

    def _make_event(
        self,
        kernel: VerdantKernel,
        groups: Sequence[SynchronizationGroupRecord],
        boundary_reason: TemporalBoundaryReason,
    ) -> TemporalEventRecord:
        sample_ids = tuple(sorted({item for group in groups for item in group.sample_ids}))
        group_ids = tuple(sorted(group.group_id for group in groups))
        records = [kernel.state.sensory_samples[item] for item in sample_ids]
        modalities = tuple(
            NativeModality(value)
            for value in sorted({item.modality.value for item in records})
        )
        evidence = tuple(sorted({item for group in groups for item in group.evidence_refs}))
        summaries = np.asarray([group.summary_vector for group in groups], dtype=np.float64)
        feature_summary = tuple(float(item) for item in np.mean(summaries, axis=0))
        changes = [
            self._summary_change(groups[index - 1].summary_vector, groups[index].summary_vector)
            for index in range(1, len(groups))
        ]
        maximum_change = max(changes, default=0.0)
        archives = tuple(sorted({item.archive_id for item in records}))
        start = min(item.timestamp_ns for item in records)
        end = max(item.timestamp_ns for item in records)
        event_id = stable_id(
            "temporal_event",
            start,
            end,
            sample_ids,
            group_ids,
            tuple(item.value for item in modalities),
            evidence,
            feature_summary,
            maximum_change,
            boundary_reason.value,
            archives,
        )
        ordered_sample_ids = tuple(
            item.sample_id
            for item in sorted(records, key=lambda item: (item.timestamp_ns, self._MODALITY_ORDER[item.modality]))
        )
        return TemporalEventRecord(
            event_id=event_id,
            start_timestamp_ns=start,
            end_timestamp_ns=end,
            sample_ids=sample_ids,
            synchronization_group_ids=group_ids,
            modalities=modalities,
            evidence_refs=evidence,
            feature_summary=feature_summary,
            maximum_change_score=maximum_change,
            boundary_reason=boundary_reason,
            archive_ids=archives,
            committed_cycle=kernel.state.cycle + 1,
            metadata={
                "ordered_sample_ids": ordered_sample_ids,
                "semantic_categories_supplied": False,
                "native_payload_replay_available": True,
            },
        )

    def inspect_temporal_events(
        self,
        kernel: VerdantKernel,
        sample_ids: Sequence[str],
    ) -> TemporalEventAssemblyReport:
        sample_tuple = tuple(sorted(set(sample_ids)))
        if not sample_tuple:
            raise SensoryIntegrityError("Temporal event inspection requires samples.")
        if len(sample_tuple) != len(sample_ids):
            raise SensoryIntegrityError("Temporal event inspection sample IDs must be unique.")
        if any(item not in kernel.state.sensory_samples for item in sample_tuple):
            raise SensoryIntegrityError("Temporal event inspection references unknown samples.")
        already_assigned = {
            sample_id
            for event in kernel.state.temporal_events.values()
            for sample_id in event.sample_ids
        }
        if already_assigned.intersection(sample_tuple):
            raise SensoryIntegrityError("Temporal event inspection includes an assigned sample.")
        groups = self._synchronize(kernel, sample_tuple)
        policy = kernel.state.sensory_policy
        events: list[TemporalEventRecord] = []
        current: list[SynchronizationGroupRecord] = []
        current_sample_count = 0
        for group in groups:
            if not current:
                current = [group]
                current_sample_count = len(group.sample_ids)
                continue
            previous = current[-1]
            gap = group.anchor_timestamp_ns - previous.anchor_timestamp_ns
            change = self._summary_change(previous.summary_vector, group.summary_vector)
            reason: TemporalBoundaryReason | None = None
            if gap > policy.maximum_event_gap_ns:
                reason = TemporalBoundaryReason.TIME_GAP
            elif change > policy.feature_change_threshold:
                reason = TemporalBoundaryReason.FEATURE_CHANGE
            elif current_sample_count + len(group.sample_ids) > policy.maximum_samples_per_event:
                reason = TemporalBoundaryReason.SAMPLE_LIMIT
            if reason is not None:
                events.append(self._make_event(kernel, current, reason))
                current = [group]
                current_sample_count = len(group.sample_ids)
            else:
                current.append(group)
                current_sample_count += len(group.sample_ids)
        if current:
            events.append(self._make_event(kernel, current, TemporalBoundaryReason.STREAM_END))
        structural = kernel.sensory_structural_fingerprint()
        operation = f"assemble_temporal_events:{stable_id('sensory_window', sample_tuple)}"
        report_id = stable_id(
            "temporal_event_report",
            kernel.state.identity.kernel_id,
            kernel.state.cycle,
            structural,
            sample_tuple,
            tuple(item.model_dump(mode="json") for item in groups),
            tuple(item.model_dump(mode="json") for item in events),
            operation,
            policy.revision,
        )
        report = TemporalEventAssemblyReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            cycle=kernel.state.cycle,
            structural_fingerprint=structural,
            sample_ids=sample_tuple,
            synchronization_groups=groups,
            proposed_events=tuple(events),
            operation=operation,
            policy_revision=policy.revision,
        )
        kernel.validate_temporal_event_report(report)
        return report

    def commit_temporal_events(
        self,
        kernel: VerdantKernel,
        report: TemporalEventAssemblyReport,
    ) -> TemporalEventAssemblyEvent:
        try:
            report = TemporalEventAssemblyReport.model_validate(report.model_dump(mode="json"))
        except ValueError as exc:
            raise SensoryIntegrityError("Temporal event report is malformed.") from exc
        reproduced = self.inspect_temporal_events(kernel, report.sample_ids)
        if reproduced.model_dump(mode="json") != report.model_dump(mode="json"):
            raise SensoryStaleError("Temporal event report does not reproduce from current state.")
        return kernel.commit_temporal_event_report(report)
