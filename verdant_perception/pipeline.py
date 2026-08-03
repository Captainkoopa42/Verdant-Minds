from __future__ import annotations

import hashlib
import math
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import cv2
import numpy as np

from verdant_kernel import (
    NativeModality,
    ObjectCandidateStatus,
    ObjectObservationInput,
    ObjectObservationKind,
    PerceptualBindingEvent,
    SensoryIntegrityError,
    VerdantKernel,
)
from verdant_kernel.models import canonical_json_bytes, stable_id
from verdant_objects import VerdantObjectPipeline
from verdant_sensory import verify_archive

from .models import (
    FramePerception,
    OcclusionBinding,
    PerceptualBindingReport,
    RegionCandidateBinding,
    RegionProposal,
)


class PerceptualIntegrityError(ValueError):
    pass


class PerceptualStaleError(PerceptualIntegrityError):
    pass


@dataclass(frozen=True)
class PerceptualBindingResult:
    report: PerceptualBindingReport
    event: PerceptualBindingEvent


@dataclass(frozen=True)
class _RawRegion:
    bbox_norm: tuple[float, float, float, float]
    centroid_norm: tuple[float, float]
    area_fraction: float
    appearance_features: tuple[float, ...]
    mask_area: int


class VerdantPerceptionPipeline:
    """Nonsemantic visual-region extraction and evidence-grounded continuity.

    This pipeline never names a region or promotes a concept. It converts exact
    archived frames into temporary region hypotheses and submits those hypotheses
    to the existing earned proto-object pathway.
    """

    def __init__(self, objects: VerdantObjectPipeline | None = None) -> None:
        self.objects = objects or VerdantObjectPipeline()

    @staticmethod
    def _payload_for_sample(
        kernel: VerdantKernel,
        sample_id: str,
        archive_paths: Mapping[str, Path],
    ) -> bytes:
        sample = kernel.state.sensory_samples.get(sample_id)
        if sample is None:
            raise PerceptualIntegrityError(f"Unknown visual sample {sample_id!r}.")
        path = archive_paths.get(sample.archive_id)
        if path is None:
            raise PerceptualIntegrityError(
                f"No archive path was supplied for sensory archive {sample.archive_id!r}."
            )
        verified = verify_archive(path)
        if verified.archive_id != sample.archive_id:
            raise PerceptualIntegrityError("Sensory archive path resolves to a different archive.")
        with zipfile.ZipFile(path, "r") as archive:
            try:
                payload = archive.read(sample.archive_member_path)
            except KeyError as exc:
                raise PerceptualIntegrityError("Visual sample payload is missing from its archive.") from exc
        if hashlib.sha256(payload).hexdigest() != sample.payload_sha256:
            raise PerceptualIntegrityError("Visual sample payload checksum mismatch.")
        return payload

    @staticmethod
    def _decode_frame(sample, payload: bytes) -> np.ndarray:
        if sample.modality != NativeModality.VISION:
            raise PerceptualIntegrityError("Perceptual binding accepts vision samples only.")
        if len(sample.shape) not in {2, 3}:
            raise PerceptualIntegrityError("Visual sample shape must be HxW or HxWxC.")
        expected = math.prod(sample.shape)
        if expected != len(payload):
            raise PerceptualIntegrityError("Visual sample payload length does not match shape.")
        array = np.frombuffer(payload, dtype=np.uint8).reshape(sample.shape)
        if array.ndim == 2:
            return array.copy()
        channels = array.shape[2]
        if channels == 1:
            return array[..., 0].copy()
        if channels in {3, 4}:
            rgb = array[..., :3]
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        raise PerceptualIntegrityError("Visual sample channel count is unsupported.")

    @staticmethod
    def _block_signature(image: np.ndarray, side: int) -> tuple[float, ...]:
        if image.size == 0:
            return tuple(0.0 for _ in range(side * side))
        resized = cv2.resize(image, (side, side), interpolation=cv2.INTER_AREA)
        return tuple(float(value) / 255.0 for value in resized.reshape(-1))

    def _appearance_features(
        self,
        gray: np.ndarray,
        component_mask: np.ndarray,
        bbox: tuple[int, int, int, int],
        area_fraction: float,
        side: int,
        histogram_bins: int,
    ) -> tuple[float, ...]:
        x, y, w, h = bbox
        crop = gray[y : y + h, x : x + w]
        mask = component_mask[y : y + h, x : x + w].astype(bool)
        pixels = crop[mask]
        if not pixels.size:
            pixels = crop.reshape(-1)
        normalized = pixels.astype(np.float64) / 255.0
        histogram, _ = np.histogram(
            normalized,
            bins=histogram_bins,
            range=(0.0, 1.0),
            density=False,
        )
        histogram = histogram.astype(np.float64)
        if histogram.sum():
            histogram /= histogram.sum()
        aspect = min(1.0, w / max(1.0, float(h)))
        inverse_aspect = min(1.0, h / max(1.0, float(w)))
        edges = cv2.Canny(crop, 40, 120)
        edge_fraction = float(np.mean(edges > 0)) if edges.size else 0.0
        signature = self._block_signature(crop, side)
        features = (
            float(np.mean(normalized)),
            float(np.std(normalized)),
            float(np.min(normalized)),
            float(np.max(normalized)),
            float(np.quantile(normalized, 0.25)),
            float(np.quantile(normalized, 0.50)),
            float(np.quantile(normalized, 0.75)),
            float(area_fraction),
            aspect,
            inverse_aspect,
            edge_fraction,
            *tuple(float(value) for value in histogram),
            *signature,
        )
        return tuple(max(0.0, min(1.0, value)) for value in features)

    def _detect_regions(self, kernel: VerdantKernel, gray: np.ndarray) -> tuple[_RawRegion, ...]:
        policy = kernel.state.perceptual_policy
        height, width = gray.shape
        normalized = gray.astype(np.float64) / 255.0
        median = float(np.median(normalized))
        deviation = np.abs(normalized - median)
        threshold = max(
            policy.minimum_saliency_threshold,
            float(np.mean(deviation) + policy.saliency_standard_deviations * np.std(deviation)),
        )
        binary = (deviation >= threshold).astype(np.uint8) * 255
        kernel_size = policy.morphology_kernel_size
        morphology = np.ones((kernel_size, kernel_size), dtype=np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, morphology)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, morphology)
        count, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
        regions: list[_RawRegion] = []
        frame_area = float(height * width)
        for label in range(1, count):
            x, y, w, h, area = (int(item) for item in stats[label])
            area_fraction = area / frame_area
            if not (
                policy.minimum_region_area_fraction
                <= area_fraction
                <= policy.maximum_region_area_fraction
            ):
                continue
            component_mask = labels == label
            cx, cy = centroids[label]
            bbox_norm = (
                x / width,
                y / height,
                (x + w) / width,
                (y + h) / height,
            )
            centroid_norm = (
                float(cx / max(1, width - 1)),
                float(cy / max(1, height - 1)),
            )
            features = self._appearance_features(
                gray,
                component_mask,
                (x, y, w, h),
                area_fraction,
                policy.appearance_signature_side,
                policy.histogram_bins,
            )
            regions.append(
                _RawRegion(
                    bbox_norm=tuple(float(item) for item in bbox_norm),
                    centroid_norm=centroid_norm,
                    area_fraction=float(area_fraction),
                    appearance_features=features,
                    mask_area=area,
                )
            )
        regions.sort(
            key=lambda item: (
                -item.area_fraction,
                item.centroid_norm[0],
                item.centroid_norm[1],
                item.appearance_features,
            )
        )
        return tuple(regions[: policy.maximum_regions_per_frame])

    @staticmethod
    def _feature_distance(left: Sequence[float], right: Sequence[float]) -> float:
        a = np.asarray(tuple(left), dtype=np.float64)
        b = np.asarray(tuple(right), dtype=np.float64)
        if a.shape != b.shape or not a.size:
            return 1.0
        return float(min(1.0, np.linalg.norm(a - b) / math.sqrt(a.size)))

    def _match_prior_regions(
        self,
        kernel: VerdantKernel,
        raw_regions: Sequence[_RawRegion],
        prior_regions: Sequence[RegionProposal],
    ) -> tuple[dict[int, RegionProposal], tuple[str, ...]]:
        policy = kernel.state.perceptual_policy
        if not raw_regions or not prior_regions:
            return {}, tuple(sorted(item.region_id for item in prior_regions))
        weight_sum = policy.prior_appearance_weight + policy.prior_position_weight
        scored: list[tuple[float, int, int]] = []
        for current_index, current in enumerate(raw_regions):
            for prior_index, prior in enumerate(prior_regions):
                appearance_distance = self._feature_distance(
                    current.appearance_features, prior.appearance_features
                )
                position_distance = min(
                    1.0,
                    math.dist(current.centroid_norm, prior.centroid_norm) / math.sqrt(2.0),
                )
                score = 1.0 - (
                    policy.prior_appearance_weight * appearance_distance
                    + policy.prior_position_weight * position_distance
                ) / weight_sum
                scored.append((score, current_index, prior_index))
        matches: dict[int, RegionProposal] = {}
        used_prior: set[int] = set()
        for score, current_index, prior_index in sorted(
            scored, key=lambda item: (-item[0], item[1], item[2])
        ):
            if score < policy.prior_match_threshold:
                break
            if current_index in matches or prior_index in used_prior:
                continue
            matches[current_index] = prior_regions[prior_index]
            used_prior.add(prior_index)
        unmatched = tuple(
            sorted(
                prior.region_id
                for index, prior in enumerate(prior_regions)
                if index not in used_prior
            )
        )
        return matches, unmatched

    def _frame_regions(
        self,
        kernel: VerdantKernel,
        *,
        sample,
        temporal_event_id: str,
        frame_index: int,
        gray: np.ndarray,
        prior_regions: Sequence[RegionProposal],
    ) -> FramePerception:
        raw = self._detect_regions(kernel, gray)
        matches, unmatched = self._match_prior_regions(kernel, raw, prior_regions)
        proposals: list[RegionProposal] = []
        for index, region in enumerate(raw):
            prior = matches.get(index)
            motion = (
                (region.centroid_norm[0] - prior.centroid_norm[0],
                 region.centroid_norm[1] - prior.centroid_norm[1])
                if prior is not None
                else (0.0, 0.0)
            )
            common_motion = prior is not None and math.dist(motion, (0.0, 0.0)) > 1e-5
            metadata = {
                "source_archive_id": sample.archive_id,
                "source_archive_member_path": sample.archive_member_path,
                "source_sequence_number": sample.sequence_number,
                "source_timestamp_ns": sample.timestamp_ns,
                "perceptual_region_only": True,
                "semantic_category_preinstalled": False,
                "invented_motion": False,
            }
            region_id = stable_id(
                "perceptual_region",
                sample.sample_id,
                temporal_event_id,
                frame_index,
                sample.observation_evidence_id,
                region.bbox_norm,
                region.centroid_norm,
                region.area_fraction,
                region.appearance_features,
                motion,
                prior.region_id if prior is not None else None,
                common_motion,
                metadata,
            )
            proposals.append(
                RegionProposal(
                    region_id=region_id,
                    sample_id=sample.sample_id,
                    temporal_event_id=temporal_event_id,
                    frame_index=frame_index,
                    evidence_ref=sample.observation_evidence_id,
                    bbox_norm=region.bbox_norm,
                    centroid_norm=region.centroid_norm,
                    area_fraction=region.area_fraction,
                    appearance_features=region.appearance_features,
                    motion=motion,
                    prior_region_id=prior.region_id if prior is not None else None,
                    common_motion_supported=common_motion,
                    metadata=metadata,
                )
            )
        return FramePerception(
            sample_id=sample.sample_id,
            temporal_event_id=temporal_event_id,
            frame_index=frame_index,
            region_proposals=tuple(proposals),
            unmatched_prior_region_ids=unmatched,
            image_sha256=sample.payload_sha256,
        )

    @staticmethod
    def _ordered_visual_samples(kernel: VerdantKernel, temporal_event_ids: Sequence[str]):
        events = []
        for event_id in temporal_event_ids:
            event = kernel.state.temporal_events.get(event_id)
            if event is None:
                raise PerceptualIntegrityError(f"Unknown temporal event {event_id!r}.")
            events.append(event)
        events.sort(key=lambda item: (item.start_timestamp_ns, item.event_id))
        rows = []
        for event in events:
            vision = [
                kernel.state.sensory_samples[sample_id]
                for sample_id in event.sample_ids
                if kernel.state.sensory_samples[sample_id].modality == NativeModality.VISION
            ]
            vision.sort(key=lambda item: (item.timestamp_ns, item.sequence_number, item.sample_id))
            for sample in vision:
                rows.append((event, sample))
        if not rows:
            raise PerceptualIntegrityError("Selected temporal events contain no visual samples.")
        return rows

    def _execute(
        self,
        kernel: VerdantKernel,
        temporal_event_ids: Sequence[str],
        archive_paths: Mapping[str, Path],
        *,
        record_event: bool,
    ) -> PerceptualBindingReport:
        initial_cycle = kernel.state.cycle
        structural = kernel.perceptual_structural_fingerprint()
        policy_revision = kernel.state.perceptual_policy.revision
        ordered = self._ordered_visual_samples(kernel, temporal_event_ids)
        if len(ordered) > kernel.state.perceptual_policy.maximum_tracking_frames:
            raise PerceptualIntegrityError("Selected visual sequence exceeds the perceptual frame limit.")

        frames: list[FramePerception] = []
        region_bindings: list[RegionCandidateBinding] = []
        occlusion_bindings: list[OcclusionBinding] = []
        prior_regions: tuple[RegionProposal, ...] = ()
        prior_region_to_candidate: dict[str, str] = {}
        all_samples: list[str] = []

        for global_index, (event, sample) in enumerate(ordered):
            payload = self._payload_for_sample(kernel, sample.sample_id, archive_paths)
            gray = self._decode_frame(sample, payload)
            frame = self._frame_regions(
                kernel,
                sample=sample,
                temporal_event_id=event.event_id,
                frame_index=sample.sequence_number,
                gray=gray,
                prior_regions=prior_regions,
            )
            current_region_to_candidate: dict[str, str] = {}
            matched_prior_ids = {
                item.prior_region_id
                for item in frame.region_proposals
                if item.prior_region_id is not None
            }
            for prior_region_id in frame.unmatched_prior_region_ids:
                candidate_id = prior_region_to_candidate.get(prior_region_id)
                if candidate_id is None:
                    continue
                candidate = kernel.state.object_candidates.get(candidate_id)
                if candidate is None or candidate.status in {
                    ObjectCandidateStatus.OCCLUDED,
                    ObjectCandidateStatus.PROMOTED,
                }:
                    continue
                occlusion = self.objects.observe(
                    kernel,
                    ObjectObservationInput(
                        episode_id=event.event_id,
                        frame_index=sample.sequence_number,
                        evidence_ref=sample.observation_evidence_id,
                        modality="native_vision_region",
                        kind=ObjectObservationKind.OCCLUSION,
                        target_candidate_id=candidate_id,
                        metadata={
                            "source_sample_id": sample.sample_id,
                            "missing_prior_region_id": prior_region_id,
                            "occlusion_inferred_from_missing_region": True,
                            "semantic_category_preinstalled": False,
                        },
                    ),
                )
                occlusion_bindings.append(
                    OcclusionBinding(
                        temporal_event_id=event.event_id,
                        frame_index=sample.sequence_number,
                        candidate_id=candidate_id,
                        object_observation_event_id=occlusion.event.event_id,
                        object_observation_id=occlusion.event.observation_id,
                        evidence_ref=sample.observation_evidence_id,
                    )
                )
            for region in frame.region_proposals:
                result = self.objects.observe(
                    kernel,
                    ObjectObservationInput(
                        episode_id=event.event_id,
                        frame_index=sample.sequence_number,
                        evidence_ref=region.evidence_ref,
                        modality="native_vision_region",
                        kind=ObjectObservationKind.VISIBLE,
                        appearance_features=region.appearance_features,
                        position=region.centroid_norm,
                        motion=region.motion,
                        common_motion_supported=region.common_motion_supported,
                        metadata={
                            **region.metadata,
                            "perceptual_region_id": region.region_id,
                            "bbox_norm": list(region.bbox_norm),
                            "area_fraction": region.area_fraction,
                            "prior_region_id": region.prior_region_id,
                        },
                    ),
                )
                current_region_to_candidate[region.region_id] = result.event.candidate_id
                region_bindings.append(
                    RegionCandidateBinding(
                        region_id=region.region_id,
                        object_observation_event_id=result.event.event_id,
                        object_observation_id=result.event.observation_id,
                        candidate_id=result.event.candidate_id,
                        disposition=result.report.disposition.value,
                    )
                )
            frames.append(frame)
            prior_regions = frame.region_proposals
            prior_region_to_candidate = current_region_to_candidate
            all_samples.append(sample.sample_id)

        candidate_ids = tuple(
            sorted(
                {
                    item.candidate_id for item in region_bindings
                }
                | {item.candidate_id for item in occlusion_bindings}
            )
        )
        object_event_ids = tuple(
            sorted(
                {item.object_observation_event_id for item in region_bindings}
                | {item.object_observation_event_id for item in occlusion_bindings}
            )
        )
        temporal_tuple = tuple(sorted(set(temporal_event_ids)))
        sample_tuple = tuple(sorted(set(all_samples)))
        operation = f"bind_native_perception:{stable_id('perceptual_window', temporal_tuple, sample_tuple)}"
        output_state_fingerprint = kernel.fingerprint()
        report_id = stable_id(
            "perceptual_binding_report",
            kernel.state.identity.kernel_id,
            initial_cycle,
            structural,
            temporal_tuple,
            sample_tuple,
            tuple(item.model_dump(mode="json") for item in frames),
            tuple(item.model_dump(mode="json") for item in region_bindings),
            tuple(item.model_dump(mode="json") for item in occlusion_bindings),
            candidate_ids,
            policy_revision,
            operation,
            output_state_fingerprint,
        )
        report = PerceptualBindingReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            initial_cycle=initial_cycle,
            structural_fingerprint=structural,
            temporal_event_ids=temporal_tuple,
            sample_ids=sample_tuple,
            frames=tuple(frames),
            region_bindings=tuple(region_bindings),
            occlusion_bindings=tuple(occlusion_bindings),
            resulting_candidate_ids=candidate_ids,
            policy_revision=policy_revision,
            operation=operation,
            output_state_fingerprint=output_state_fingerprint,
        )
        if record_event:
            kernel.record_perceptual_binding(
                report_id=report.report_id,
                report_sha256=report.digest(),
                temporal_event_ids=report.temporal_event_ids,
                sample_ids=report.sample_ids,
                object_observation_event_ids=object_event_ids,
                object_candidate_ids=candidate_ids,
                policy_revision=report.policy_revision,
                metadata={
                    "frame_count": len(report.frames),
                    "region_count": sum(len(item.region_proposals) for item in report.frames),
                    "occlusion_count": len(report.occlusion_bindings),
                    "semantic_categories_supplied": False,
                    "source": "native_perceptual_binding",
                },
            )
        return report

    def inspect(
        self,
        kernel: VerdantKernel,
        temporal_event_ids: Sequence[str],
        archive_paths: Mapping[str, Path],
    ) -> PerceptualBindingReport:
        before = kernel.snapshot()
        working = VerdantKernel.from_state(before)
        report = self._execute(
            working,
            temporal_event_ids,
            archive_paths,
            record_event=True,
        )
        if kernel.snapshot() != before:
            raise PerceptualIntegrityError("Perceptual inspection mutated the source kernel.")
        return report

    def commit(
        self,
        kernel: VerdantKernel,
        report: PerceptualBindingReport,
        archive_paths: Mapping[str, Path],
    ) -> PerceptualBindingEvent:
        try:
            report = PerceptualBindingReport.model_validate(report.model_dump(mode="json"))
        except ValueError as exc:
            raise PerceptualIntegrityError("Perceptual report is malformed or tampered.") from exc
        if report.kernel_id != kernel.state.identity.kernel_id:
            raise PerceptualIntegrityError("Perceptual report belongs to another kernel.")
        if report.initial_cycle != kernel.state.cycle:
            raise PerceptualStaleError("Kernel cycle changed after perceptual inspection.")
        if report.structural_fingerprint != kernel.perceptual_structural_fingerprint():
            raise PerceptualStaleError("Perceptual source state changed after inspection.")
        if report.policy_revision != kernel.state.perceptual_policy.revision:
            raise PerceptualStaleError("Perceptual policy changed after inspection.")
        working = VerdantKernel.from_state(kernel.snapshot())
        reproduced = self._execute(
            working,
            report.temporal_event_ids,
            archive_paths,
            record_event=True,
        )
        if reproduced.model_dump(mode="json") != report.model_dump(mode="json"):
            raise PerceptualStaleError("Perceptual report does not reproduce from current state.")
        event = working.state.perceptual_binding_events[-1]
        kernel.state = working.state.model_copy(deep=True)
        return event

    def process(
        self,
        kernel: VerdantKernel,
        temporal_event_ids: Sequence[str],
        archive_paths: Mapping[str, Path],
    ) -> PerceptualBindingResult:
        report = self.inspect(kernel, temporal_event_ids, archive_paths)
        event = self.commit(kernel, report, archive_paths)
        return PerceptualBindingResult(report=report, event=event)
