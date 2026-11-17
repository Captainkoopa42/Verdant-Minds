"""Opt-in surprise sidecar: the organism's own prediction error, and learning that follows it.

Claim boundary: IMPLEMENTED-EXPERIMENTAL. No file under ``verdant_*`` is edited.

Stock: every current experience carries ``prediction_error = 0.15`` and binds with the same
activation floor (0.62) whether it was expected or not.

1. Measured surprise (``SurpriseDevelopmentPipeline``)
   BEFORE an experience is applied, the organism is asked, through its own read-only
   ``inspect_resonance``, which concepts this input's features call up. The prediction is
   the k concepts whose profile match stands at least 2 SD above the crowd (k = number of
   concepts the experience turns out to contain). Surprise = share of the experience's
   concepts that were NOT predicted. A concept that does not exist yet is always a miss, and
   with fewer than 8 known concepts surprise is 1. That number replaces the constant on the
   current-evidence workspace item, so it is part of canonical state and replayable.

2. Learning follows surprise (``surprise_plasticity(base)``)
   For concepts in the current experience, activation = floor + (1 - floor) * surprise.
   Refusal first: it is never below the stock floor, so an expected experience binds
   exactly as stock does; an unexpected one binds harder. Rehearsal items are untouched.

3. Reunion (``surprise_plasticity(base, reunion=True)``): the two memories consulted together
   familiarity = 1 - surprise        what the field says: "I have met this" (from features alone)
   forgetting  = how far the bonds among the things now held in mind fall short of the
                 strength the cohesion gate asks for (a missing bond counts as zero)
   reunion     = familiarity * forgetting
   activation  = floor + (1 - floor) * max(surprise, reunion)
   A first meeting has no familiarity, so reunion is zero there. Something well bonded has no
   forgetting, so reunion is zero there too. It acts only on what is recognised and has
   slipped. Occurrence, evidence and context counts are untouched, so the gates still refuse
   what real experience has not repeated.
"""
from __future__ import annotations

import numpy as np

from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel.models import WorkspaceSourceKind

__all__ = ["SurpriseDevelopmentPipeline", "surprise_plasticity", "measure_surprise"]

MIN_KNOWN_CONCEPTS = 8
STAND_OUT_SDS = 2.0


def measure_surprise(kernel, command, scope) -> tuple[float, dict]:
    """Share of this experience's concepts the organism did not predict from the features alone."""
    proposed = [p.label.strip().lower() for p in command.concept_proposals]
    if not proposed:
        return 0.0, {"reason": "no concepts"}
    if len(scope) < MIN_KNOWN_CONCEPTS:
        return 1.0, {"reason": "too little known to predict from"}
    report = kernel.inspect_resonance(command.feature_vector, command.modality, top_k=len(scope), candidate_concept_ids=scope)
    match = np.array([c.contribution.profile_alignment for c in report.candidates])
    spread = match.std()
    if spread < 1e-12:
        return 1.0, {"reason": "no concept stands out"}
    stand_out = (match - match.mean()) / spread
    order = np.argsort(-stand_out, kind="stable")[: len(proposed)]
    predicted = {report.candidates[i].concept_id for i in order if stand_out[i] >= STAND_OUT_SDS}
    labels = {kernel.state.concepts[cid].label.strip().lower() for cid in predicted}
    labels |= {kernel.state.concepts[cid].normalized_label.strip().lower() for cid in predicted}
    hits = sum(1 for label in proposed if label in labels)
    return 1.0 - hits / len(proposed), {"predicted": len(predicted), "hits": hits, "of": len(proposed)}


class SurpriseDevelopmentPipeline(VerdantDevelopmentPipeline):
    def __init__(self, **stages) -> None:
        super().__init__(**stages); self._surprise = 0.15; self.surprise_log: list[tuple[str, float]] = []

    def _advance_staged(self, kernel, command):
        if command.event_key not in kernel.state.processed_event_keys:
            self._surprise, _detail = measure_surprise(kernel, command, self._candidate_scope(kernel))
            self.surprise_log.append((command.event_key, round(self._surprise, 4)))
        return super()._advance_staged(kernel, command)

    def _workspace_candidates(self, kernel, experience, resonance_event):
        candidates = list(super()._workspace_candidates(kernel, experience, resonance_event))
        for i, candidate in enumerate(candidates):
            if candidate.source_kind == WorkspaceSourceKind.CURRENT_EVIDENCE:
                candidates[i] = candidate.model_copy(update={
                    "signals": candidate.signals.model_copy(update={"prediction_error": float(self._surprise)}),
                    "metadata": {**candidate.metadata, "prediction_error_source": "sidecar_surprise.measured",
                                 "measured_familiarity": round(1.0 - float(self._surprise), 6)}})
        return tuple(candidates)


def surprise_plasticity(base, *, reunion: bool = False):
    """Return a plasticity stage class derived from ``base`` in which binding follows measured surprise
    and, with ``reunion=True``, also the meeting of a recognised thing whose bonds have slipped."""

    class SurprisePlasticity(base):
        def _activation_state(self, kernel, event, scope):
            activation, evidence_by_concept, current = super()._activation_state(kernel, event, scope)
            floor = kernel.state.plasticity_policy.current_evidence_activation_floor
            for item_id in event.active_item_ids:
                item = kernel.state.workspace_items.get(item_id)
                if item is None or item.source_kind != WorkspaceSourceKind.CURRENT_EVIDENCE:
                    continue
                if item.metadata.get("prediction_error_source") != "sidecar_surprise.measured":
                    continue
                drive = float(item.signals.prediction_error)
                if reunion:
                    held = sorted(ref for ref in item.binding_refs if ref in kernel.state.concepts)
                    pairs = [(a, b) for i, a in enumerate(held) for b in held[i + 1:]]
                    if pairs:
                        strength = {tuple(sorted(x.concept_ids)): x.strength for x in kernel.state.plasticity_associations.values()}
                        mean = sum(strength.get(tuple(sorted(pair)), 0.0) for pair in pairs) / len(pairs)
                        wanted = kernel.state.structure_policy.minimum_internal_cohesion
                        forgetting = max(0.0, min(1.0, 1.0 - mean / wanted)) if wanted > 0 else 0.0
                        drive = max(drive, float(item.metadata.get("measured_familiarity", 0.0)) * forgetting)
                boosted = floor + (1.0 - floor) * drive
                for concept_id in item.binding_refs:
                    if concept_id in activation and concept_id in current:
                        activation[concept_id] = max(activation[concept_id], min(1.0, boosted))
            return activation, evidence_by_concept, current

    SurprisePlasticity.__name__ = f"{'Reunion' if reunion else 'Surprise'}{base.__name__}"
    return SurprisePlasticity
