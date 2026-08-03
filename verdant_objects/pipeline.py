from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from verdant_governance import VerdantGovernancePipeline
from verdant_kernel import (
    CouncilDecisionEvent,
    GovernanceProposalKind,
    ObjectAssociationCandidate,
    ObjectAssociationDisposition,
    ObjectCandidateRecord,
    ObjectCandidateStatus,
    ObjectObservationEvent,
    ObjectObservationInput,
    ObjectObservationKind,
    ObjectObservationReport,
    ObjectPromotionDisposition,
    ObjectPromotionEvent,
    ObjectPromotionReport,
    ObjectStaleError,
    VerdantKernel,
)
from verdant_kernel.models import (
    ObjectSupportComponents,
    normalize_label,
    stable_id,
)


@dataclass(frozen=True)
class ObjectObservationResult:
    report: ObjectObservationReport
    event: ObjectObservationEvent


@dataclass(frozen=True)
class ObjectPromotionResult:
    report: ObjectPromotionReport
    council_decision: CouncilDecisionEvent
    promotion_event: ObjectPromotionEvent


def _distance(left: Iterable[float], right: Iterable[float]) -> float:
    a = np.asarray(tuple(left), dtype=np.float64)
    b = np.asarray(tuple(right), dtype=np.float64)
    if a.shape != b.shape:
        return math.inf
    if a.size == 0:
        return 0.0
    return float(np.linalg.norm(a - b) / math.sqrt(a.size))


def _point_error(left: tuple[float, float], right: tuple[float, float]) -> float:
    return float(math.dist(left, right))


class VerdantObjectPipeline:
    """Evidence-preserving proto-object tracking and governed promotion.

    Tracking records hypotheses outside the canonical concept graph. Only a
    threshold-satisfying, Council-authorized promotion creates a semantic concept.
    """

    def inspect_observation(
        self,
        kernel: VerdantKernel,
        observation: ObjectObservationInput,
    ) -> ObjectObservationReport:
        observation = ObjectObservationInput.model_validate(
            observation.model_dump(mode="json")
        )
        evidence = kernel.state.evidence.get(observation.evidence_ref)
        if evidence is None:
            raise KeyError(f"Unknown object evidence {observation.evidence_ref!r}.")
        if observation.kind == ObjectObservationKind.VISIBLE and evidence.kind.value != "observation":
            raise ValueError("Visible tracking requires native observation evidence.")

        structural = kernel.object_structural_fingerprint()
        policy = kernel.state.object_policy
        observation_id = self._observation_id(kernel, observation)
        if observation_id in kernel.state.object_observations:
            raise ValueError("This object observation has already been committed.")

        candidates: tuple[ObjectAssociationCandidate, ...] = ()
        selected: str | None = None
        competing: tuple[str, ...] = ()

        if observation.kind == ObjectObservationKind.VISIBLE:
            candidates = self._association_candidates(kernel, observation)
            eligible = [item for item in candidates if item.eligible]
            if eligible:
                selected = eligible[0].candidate_id
                ambiguous = (
                    len(eligible) > 1
                    and abs(eligible[0].score - eligible[1].score)
                    <= policy.ambiguity_margin
                )
                if ambiguous:
                    competing = tuple(sorted(item.candidate_id for item in eligible[:2]))
                    disposition = ObjectAssociationDisposition.CREATE
                    selected = None
                    proposed = self._create_candidate(
                        kernel, observation, observation_id, competing=competing, ambiguous=True
                    )
                else:
                    competing = tuple(
                        sorted(
                            item.candidate_id
                            for item in candidates
                            if item.candidate_id != selected
                            and item.appearance_similarity >= 0.70
                        )
                    )
                    disposition = ObjectAssociationDisposition.ASSOCIATE
                    proposed = self._update_visible_candidate(
                        kernel,
                        kernel.state.object_candidates[selected],
                        observation,
                        observation_id,
                        competing=competing,
                    )
            else:
                competing = tuple(
                    sorted(
                        item.candidate_id
                        for item in candidates
                        if item.appearance_similarity >= 0.70
                    )
                )
                disposition = ObjectAssociationDisposition.CREATE
                proposed = self._create_candidate(
                    kernel, observation, observation_id, competing=competing
                )
        else:
            selected = observation.target_candidate_id
            if selected is None or selected not in kernel.state.object_candidates:
                raise KeyError("Target object candidate does not exist.")
            disposition = ObjectAssociationDisposition.UPDATE_TARGET
            proposed = self._update_target_candidate(
                kernel,
                kernel.state.object_candidates[selected],
                observation,
                observation_id,
            )

        operation = f"track_object_candidate:{proposed.candidate_id}"
        report_id = stable_id(
            "object_observation_report",
            kernel.state.identity.kernel_id,
            kernel.state.cycle,
            structural,
            observation.model_dump(mode="json"),
            tuple(item.model_dump(mode="json") for item in candidates),
            disposition.value,
            selected,
            competing,
            proposed.model_dump(mode="json"),
            operation,
            policy.revision,
        )
        report = ObjectObservationReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            cycle=kernel.state.cycle,
            structural_fingerprint=structural,
            observation=observation,
            candidates=candidates,
            disposition=disposition,
            selected_candidate_id=selected,
            competing_candidate_ids=competing,
            proposed_candidate=proposed,
            operation=operation,
            policy_revision=policy.revision,
        )
        kernel.validate_object_observation_report(report)
        return report

    def commit_observation(
        self,
        kernel: VerdantKernel,
        report: ObjectObservationReport,
    ) -> ObjectObservationEvent:
        try:
            report = ObjectObservationReport.model_validate(report.model_dump(mode="json"))
        except ValueError as exc:
            raise ObjectStaleError("Object observation report is invalid.") from exc
        reproduced = self.inspect_observation(kernel, report.observation)
        if reproduced != report:
            raise ObjectStaleError(
                "Object observation report does not reproduce from current state."
            )
        return kernel.commit_object_observation(report)

    def observe(
        self,
        kernel: VerdantKernel,
        observation: ObjectObservationInput,
    ) -> ObjectObservationResult:
        report = self.inspect_observation(kernel, observation)
        event = self.commit_observation(kernel, report)
        return ObjectObservationResult(report, event)

    def inspect_promotion(
        self,
        kernel: VerdantKernel,
        candidate_id: str,
    ) -> ObjectPromotionReport:
        candidate = kernel.state.object_candidates.get(candidate_id)
        if candidate is None:
            raise KeyError(f"Unknown object candidate {candidate_id!r}.")
        policy = kernel.state.object_policy
        rejection: list[str] = []
        if candidate.status == ObjectCandidateStatus.PROMOTED:
            rejection.append("already_promoted")
        if candidate.visible_observation_count < policy.minimum_visible_observations:
            rejection.append("insufficient_visible_observations")
        if len(candidate.episode_ids) < policy.minimum_episode_count:
            rejection.append("insufficient_recurrence")
        if candidate.persistence_count < policy.minimum_persistence_count:
            rejection.append("insufficient_temporal_persistence")
        if candidate.transformation_count < policy.minimum_transformation_count:
            rejection.append("insufficient_transformation_continuity")
        if candidate.common_motion_count < policy.minimum_common_motion_count:
            rejection.append("insufficient_common_motion")
        if candidate.reappearance_count < policy.minimum_reappearance_count:
            rejection.append("insufficient_occlusion_reappearance")
        if candidate.ambiguity_count:
            rejection.append("unresolved_identity_ambiguity")
        if candidate.support_score < policy.minimum_support_score:
            rejection.append("support_score_below_threshold")
        rejection_codes = tuple(sorted(set(rejection)))
        disposition = (
            ObjectPromotionDisposition.PROMOTE
            if not rejection_codes
            else ObjectPromotionDisposition.DEFER
        )
        label = f"proto-object-{candidate.candidate_id.split('_')[-1][:12]}"
        proposed_concept_id = stable_id("concept", normalize_label(label))
        operation = f"promote_proto_object:{candidate.candidate_id}"
        structural = kernel.object_structural_fingerprint()
        report_id = stable_id(
            "object_promotion_report",
            kernel.state.identity.kernel_id,
            kernel.state.cycle,
            structural,
            candidate_id,
            disposition.value,
            rejection_codes,
            candidate.evidence_refs,
            label,
            proposed_concept_id,
            operation,
            policy.revision,
            candidate.model_dump(mode="json"),
        )
        report = ObjectPromotionReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            cycle=kernel.state.cycle,
            structural_fingerprint=structural,
            candidate_id=candidate_id,
            disposition=disposition,
            rejection_codes=rejection_codes,
            evidence_refs=candidate.evidence_refs,
            proposed_label=label,
            proposed_concept_id=proposed_concept_id,
            operation=operation,
            policy_revision=policy.revision,
            candidate_snapshot=candidate,
        )
        kernel.validate_object_promotion_report(report)
        return report

    def promotion_council_proposal(
        self,
        kernel: VerdantKernel,
        report: ObjectPromotionReport,
        governance: VerdantGovernancePipeline | None = None,
    ):
        if report.disposition != ObjectPromotionDisposition.PROMOTE:
            raise ValueError("An ineligible candidate cannot be proposed for promotion.")
        governance = governance or VerdantGovernancePipeline()
        candidate = report.candidate_snapshot
        return governance.propose(
            kernel,
            proposal_kind=GovernanceProposalKind.STRUCTURAL_PROMOTION,
            operation=report.operation,
            action_class="earned_proto_object_promotion",
            description=(
                "Promote an evidence-supported persistent object candidate "
                "to a canonical proto-object without installing a human category label."
            ),
            evidence_refs=report.evidence_refs,
            requested_resource=min(0.20, kernel.state.governance.attention_budget),
            relevance=0.95,
            urgency=0.25,
            novelty=0.90,
            predicted_information_gain=0.90,
            harm_risk=0.0,
            reversibility=1.0,
            metadata={
                "candidate_id": candidate.candidate_id,
                "support_score": candidate.support_score,
                "observation_count": len(candidate.observation_ids),
                "episode_count": len(candidate.episode_ids),
                "semantic_category_preinstalled": False,
            },
        )

    def promote(
        self,
        kernel: VerdantKernel,
        candidate_id: str,
        governance: VerdantGovernancePipeline | None = None,
    ) -> ObjectPromotionResult:
        governance = governance or VerdantGovernancePipeline()
        report = self.inspect_promotion(kernel, candidate_id)
        if report.disposition != ObjectPromotionDisposition.PROMOTE:
            raise ValueError(
                "Object candidate is not eligible: " + ", ".join(report.rejection_codes)
            )
        proposal = self.promotion_council_proposal(kernel, report, governance)
        decision = governance.commit(kernel, governance.inspect(kernel, proposal))
        event = kernel.commit_object_promotion(
            report,
            council_decision_event_id=decision.decision_event_id,
        )
        return ObjectPromotionResult(report, decision, event)

    def _association_candidates(
        self,
        kernel: VerdantKernel,
        observation: ObjectObservationInput,
    ) -> tuple[ObjectAssociationCandidate, ...]:
        policy = kernel.state.object_policy
        raw: list[tuple[str, float, bool, float, float, float, float, tuple[str, ...]]] = []
        for candidate_id, candidate in sorted(kernel.state.object_candidates.items()):
            if candidate.status == ObjectCandidateStatus.PROMOTED:
                continue
            appearance_distance = _distance(
                observation.appearance_features, candidate.appearance_centroid
            )
            appearance = max(
                0.0,
                1.0 - appearance_distance / policy.maximum_appearance_distance,
            )
            same_episode = observation.episode_id == candidate.last_episode_id
            frame_gap = observation.frame_index - candidate.last_frame_index
            rejection: list[str] = []
            if appearance_distance > policy.maximum_appearance_distance:
                rejection.append("appearance_distance_exceeded")

            if same_episode and frame_gap > 0 and candidate.last_position is not None:
                predicted = (
                    candidate.last_position[0]
                    + (candidate.last_motion or (0.0, 0.0))[0] * frame_gap,
                    candidate.last_position[1]
                    + (candidate.last_motion or (0.0, 0.0))[1] * frame_gap,
                )
                position_error = _point_error(predicted, observation.position or predicted)
                position_fit = max(
                    0.0, 1.0 - position_error / policy.maximum_position_error
                )
                motion_error = _point_error(
                    candidate.last_motion or (0.0, 0.0),
                    observation.motion or (0.0, 0.0),
                )
                motion_fit = max(
                    0.0, 1.0 - motion_error / policy.maximum_motion_error
                )
                continuity = max(
                    0.0, 1.0 - (frame_gap - 1) / policy.maximum_frame_gap
                )
                if position_error > policy.maximum_position_error:
                    rejection.append("predicted_position_mismatch")
                if motion_error > policy.maximum_motion_error:
                    rejection.append("motion_mismatch")
                if frame_gap > policy.maximum_frame_gap and candidate.status != ObjectCandidateStatus.OCCLUDED:
                    rejection.append("temporal_gap_exceeded")
                if candidate.status == ObjectCandidateStatus.OCCLUDED and frame_gap > policy.maximum_occlusion_gap:
                    rejection.append("occlusion_gap_exceeded")
            else:
                position_fit = 0.55
                motion_fit = 0.55
                continuity = 0.35 if not same_episode else 0.0
                if same_episode and frame_gap <= 0:
                    rejection.append("nonadvancing_frame")

            score = min(
                1.0,
                0.50 * appearance
                + 0.25 * position_fit
                + 0.15 * motion_fit
                + 0.10 * continuity,
            )
            if score < policy.association_threshold:
                rejection.append("association_score_below_threshold")
            eligible = not rejection
            raw.append(
                (
                    candidate_id,
                    score,
                    eligible,
                    appearance,
                    position_fit,
                    motion_fit,
                    continuity,
                    tuple(sorted(set(rejection))),
                )
            )
        ordered = sorted(raw, key=lambda item: (-item[1], item[0]))
        return tuple(
            ObjectAssociationCandidate(
                rank=index + 1,
                candidate_id=item[0],
                score=item[1],
                eligible=item[2],
                appearance_similarity=item[3],
                position_fit=item[4],
                motion_alignment=item[5],
                episode_continuity=item[6],
                rejection_codes=item[7],
            )
            for index, item in enumerate(ordered)
        )

    def _create_candidate(
        self,
        kernel: VerdantKernel,
        observation: ObjectObservationInput,
        observation_id: str,
        *,
        competing: tuple[str, ...] = (),
        ambiguous: bool = False,
    ) -> ObjectCandidateRecord:
        candidate_id = stable_id("object_candidate", observation_id)
        candidate = ObjectCandidateRecord(
            candidate_id=candidate_id,
            status=ObjectCandidateStatus.CONTESTED if ambiguous else ObjectCandidateStatus.TRACKING,
            created_cycle=kernel.state.cycle + 1,
            updated_cycle=kernel.state.cycle + 1,
            observation_ids=(observation_id,),
            evidence_refs=(observation.evidence_ref,),
            episode_ids=(observation.episode_id,),
            appearance_centroid=observation.appearance_features,
            last_position=observation.position,
            last_motion=observation.motion,
            last_episode_id=observation.episode_id,
            last_frame_index=observation.frame_index,
            visible_observation_count=1,
            common_motion_count=int(observation.common_motion_supported),
            ambiguity_count=int(ambiguous),
            competing_candidate_ids=tuple(sorted(set(competing))),
            support_score=0.0,
            support_components=self._empty_components(),
        )
        return self._score_candidate(kernel, candidate)

    def _update_visible_candidate(
        self,
        kernel: VerdantKernel,
        candidate: ObjectCandidateRecord,
        observation: ObjectObservationInput,
        observation_id: str,
        *,
        competing: tuple[str, ...] = (),
    ) -> ObjectCandidateRecord:
        previous_visible = candidate.visible_observation_count
        next_count = previous_visible + 1
        old = np.asarray(candidate.appearance_centroid, dtype=np.float64)
        new = np.asarray(observation.appearance_features, dtype=np.float64)
        centroid = tuple(float(value) for value in ((old * previous_visible + new) / next_count))
        same_episode = observation.episode_id == candidate.last_episode_id
        frame_gap = observation.frame_index - candidate.last_frame_index
        persistence = candidate.persistence_count + int(
            same_episode and 0 < frame_gap <= kernel.state.object_policy.maximum_frame_gap
        )
        transformation = candidate.transformation_count + int(
            _distance(observation.appearance_features, candidate.appearance_centroid)
            >= kernel.state.object_policy.transformation_novelty_distance
        )
        reappearance = candidate.reappearance_count + int(
            candidate.status == ObjectCandidateStatus.OCCLUDED
            and same_episode
            and 0 < frame_gap <= kernel.state.object_policy.maximum_occlusion_gap
        )
        updated = candidate.model_copy(
            update={
                "updated_cycle": kernel.state.cycle + 1,
                "observation_ids": tuple(sorted((*candidate.observation_ids, observation_id))),
                "evidence_refs": tuple(sorted((*candidate.evidence_refs, observation.evidence_ref))),
                "episode_ids": tuple(sorted(set((*candidate.episode_ids, observation.episode_id)))),
                "appearance_centroid": centroid,
                "last_position": observation.position,
                "last_motion": observation.motion,
                "last_episode_id": observation.episode_id,
                "last_frame_index": observation.frame_index,
                "visible_observation_count": next_count,
                "persistence_count": persistence,
                "transformation_count": transformation,
                "common_motion_count": candidate.common_motion_count + int(observation.common_motion_supported),
                "reappearance_count": reappearance,
                "competing_candidate_ids": tuple(sorted(set((*candidate.competing_candidate_ids, *competing)))),
            }
        )
        return self._score_candidate(kernel, updated)

    def _update_target_candidate(
        self,
        kernel: VerdantKernel,
        candidate: ObjectCandidateRecord,
        observation: ObjectObservationInput,
        observation_id: str,
    ) -> ObjectCandidateRecord:
        update = {
            "updated_cycle": kernel.state.cycle + 1,
            "observation_ids": tuple(sorted((*candidate.observation_ids, observation_id))),
            "evidence_refs": tuple(sorted((*candidate.evidence_refs, observation.evidence_ref))),
            "episode_ids": tuple(sorted(set((*candidate.episode_ids, observation.episode_id)))),
            "last_episode_id": observation.episode_id,
            "last_frame_index": observation.frame_index,
        }
        if observation.kind == ObjectObservationKind.OCCLUSION:
            update["occlusion_count"] = candidate.occlusion_count + 1
            update["status"] = ObjectCandidateStatus.OCCLUDED
        updated = candidate.model_copy(update=update)
        return self._score_candidate(kernel, updated, preserve_occluded=True)

    def _score_candidate(
        self,
        kernel: VerdantKernel,
        candidate: ObjectCandidateRecord,
        *,
        preserve_occluded: bool = False,
    ) -> ObjectCandidateRecord:
        p = kernel.state.object_policy
        recurrence = min(1.0, len(candidate.episode_ids) / p.minimum_episode_count)
        persistence = min(1.0, candidate.persistence_count / p.minimum_persistence_count)
        transformation = min(1.0, candidate.transformation_count / max(1, p.minimum_transformation_count))
        common_motion = min(1.0, candidate.common_motion_count / max(1, p.minimum_common_motion_count))
        reappearance = min(1.0, candidate.reappearance_count / max(1, p.minimum_reappearance_count))
        positive = (
            p.recurrence_weight * recurrence
            + p.persistence_weight * persistence
            + p.transformation_weight * transformation
            + p.common_motion_weight * common_motion
            + p.reappearance_weight * reappearance
        )
        penalty = p.ambiguity_penalty * min(1.0, candidate.ambiguity_count)
        score = max(0.0, min(1.0, positive - penalty))
        components = ObjectSupportComponents(
            recurrence=recurrence,
            persistence=persistence,
            transformation=transformation,
            common_motion=common_motion,
            reappearance=reappearance,
            ambiguity_penalty=min(1.0, candidate.ambiguity_count),
            weighted_positive=positive,
            weighted_penalty=penalty,
        )
        gates = (
            candidate.visible_observation_count >= p.minimum_visible_observations
            and len(candidate.episode_ids) >= p.minimum_episode_count
            and candidate.persistence_count >= p.minimum_persistence_count
            and candidate.transformation_count >= p.minimum_transformation_count
            and candidate.common_motion_count >= p.minimum_common_motion_count
            and candidate.reappearance_count >= p.minimum_reappearance_count
            and candidate.ambiguity_count == 0
            and score >= p.minimum_support_score
        )
        if candidate.status == ObjectCandidateStatus.PROMOTED:
            status = candidate.status
        elif preserve_occluded and candidate.status == ObjectCandidateStatus.OCCLUDED:
            status = ObjectCandidateStatus.OCCLUDED
        elif candidate.ambiguity_count:
            status = ObjectCandidateStatus.CONTESTED
        elif gates:
            status = ObjectCandidateStatus.ELIGIBLE
        else:
            status = ObjectCandidateStatus.TRACKING
        return ObjectCandidateRecord.model_validate(
            candidate.model_copy(
                update={
                    "status": status,
                    "support_score": score,
                    "support_components": components,
                }
            ).model_dump(mode="json")
        )

    @staticmethod
    def _empty_components() -> ObjectSupportComponents:
        return ObjectSupportComponents(
            recurrence=0.0,
            persistence=0.0,
            transformation=0.0,
            common_motion=0.0,
            reappearance=0.0,
            ambiguity_penalty=0.0,
            weighted_positive=0.0,
            weighted_penalty=0.0,
        )

    @staticmethod
    def _observation_id(
        kernel: VerdantKernel,
        observation: ObjectObservationInput,
    ) -> str:
        return stable_id(
            "object_observation",
            kernel.state.identity.kernel_id,
            observation.episode_id,
            observation.frame_index,
            observation.evidence_ref,
            observation.kind.value,
            observation.model_dump(mode="json"),
        )
