"""Three Kings Council — coordination, conflict detection, and resolution.

Combines oversight from DataKing, ForefrontKing, and EthicsKing with
weighted voting and consensus mechanisms.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from verdant.governance.data_king import DataKing
from verdant.governance.ethics_king import EthicsKing
from verdant.governance.forefront_king import ForefrontKing
from verdant.pipeline.chunk import CognitiveChunk


class ThreeKingsCouncil:
    """Coordinates the three governance kings, detects conflicts, and resolves them."""

    name: str = "ThreeKingsCouncil"

    def __init__(
        self,
        data_king: DataKing,
        forefront_king: ForefrontKing,
        ethics_king: EthicsKing,
    ) -> None:
        self.data_king = data_king
        self.forefront_king = forefront_king
        self.ethics_king = ethics_king
        self.influence_weights: Dict[str, float] = {
            "DataKing": 1.0,
            "ForefrontKing": 1.0,
            "EthicsKing": 1.0,
        }
        self.majority_threshold: float = 0.66
        self.conflict_history: List[Dict[str, Any]] = []
        self.interaction_history: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = {
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
            "council_votes": 0,
        }

    def oversee(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Full Three-Kings coordination pass."""
        initial_action = (chunk.get_section_content("action_selection_section") or {}).get(
            "selected_action", ""
        )

        # Detect conflicts
        conflicts = self._detect_conflicts(chunk, initial_action)

        # Resolve conflicts if any
        if conflicts:
            chunk = self._resolve_conflicts(chunk, conflicts)
            self.metrics["conflicts_detected"] += len(conflicts)

        # Criticality assessment → council vote if needed
        criticality = self._assess_criticality(chunk)
        if criticality > 0.7:
            chunk = self._council_vote(chunk)
            self.metrics["council_votes"] += 1

        # Record interaction
        self.interaction_history.append({
            "timestamp": time.time(),
            "conflicts": len(conflicts),
            "criticality": criticality,
            "weights": dict(self.influence_weights),
        })
        if len(self.interaction_history) > 200:
            self.interaction_history = self.interaction_history[-200:]

        self._update_influence()

        # Write council section
        chunk.update_section("three_kings_layer_section", {
            "conflicts": conflicts,
            "criticality": criticality,
            "influence_weights": dict(self.influence_weights),
            "timestamp": time.time(),
        })
        chunk.add_processing_step(self.name, "council_oversight", {
            "conflicts": len(conflicts),
            "criticality": criticality,
        })
        return chunk

    # ------------------------------------------------------------------

    def _detect_conflicts(
        self, chunk: CognitiveChunk, initial_action: str,
    ) -> List[Dict[str, Any]]:
        conflicts: List[Dict[str, Any]] = []
        current_action = (chunk.get_section_content("action_selection_section") or {}).get(
            "selected_action", ""
        )
        if current_action and current_action != initial_action:
            conflicts.append({
                "type": "action_override",
                "initial": initial_action,
                "current": current_action,
                "criticality": 0.8,
            })

        # Confidence disagreement
        dk = chunk.get_section_content("data_king_section") or {}
        fk = chunk.get_section_content("forefront_king_section") or {}
        ek = chunk.get_section_content("ethics_king_section") or {}

        assessments = {
            "DataKing": dk.get("assessment_confidence", 0.5),
            "ForefrontKing": 1.0 - fk.get("cognitive_load", 0.5),
            "EthicsKing": ek.get("evaluation", {}).get("overall_score", 0.5),
        }
        vals = list(assessments.values())
        spread = max(vals) - min(vals)
        if spread > 0.3:
            conflicts.append({
                "type": "confidence_disagreement",
                "assessments": assessments,
                "spread": spread,
                "criticality": 0.6 * spread,
            })

        return conflicts

    def _resolve_conflicts(
        self, chunk: CognitiveChunk, conflicts: List[Dict[str, Any]],
    ) -> CognitiveChunk:
        for conflict in conflicts:
            if conflict["type"] == "action_override":
                chunk = self._resolve_override(chunk, conflict)
            elif conflict["type"] == "confidence_disagreement":
                self._resolve_confidence(conflict)
            self.metrics["conflicts_resolved"] += 1
        return chunk

    def _resolve_override(
        self, chunk: CognitiveChunk, conflict: Dict[str, Any],
    ) -> CognitiveChunk:
        # Weighted override strength
        total_w = sum(self.influence_weights.values())
        ethics_w = self.influence_weights["EthicsKing"]
        override_strength = ethics_w / total_w
        if override_strength < self.majority_threshold:
            # Revert action
            action = chunk.get_section_content("action_selection_section") or {}
            action["selected_action"] = conflict["initial"]
            action["override_rejected"] = True
            chunk.update_section("action_selection_section", action)
        return chunk

    def _resolve_confidence(self, conflict: Dict[str, Any]) -> None:
        assessments = conflict.get("assessments", {})
        total_w = 0.0
        weighted_sum = 0.0
        for king, assessment in assessments.items():
            w = self.influence_weights.get(king, 1.0)
            weighted_sum += assessment * w
            total_w += w
        # Consensus stored for threshold blending
        if total_w > 0:
            _ = weighted_sum / total_w

    def _assess_criticality(self, chunk: CognitiveChunk) -> float:
        base = 0.5
        ethics = chunk.get_section_content("ethics_king_section") or {}
        concerns = ethics.get("evaluation", {}).get("concerns", [])
        base += 0.1 * min(len(concerns), 3)

        action = chunk.get_section_content("action_selection_section") or {}
        selected = action.get("selected_action", "")
        if selected == "defer_decision":
            base += 0.2
        elif selected == "trigger_system_action":
            base += 0.15

        conf = float(action.get("action_confidence", 0.5))
        if conf < 0.4 or conf > 0.9:
            base += 0.1

        return min(1.0, base)

    def _council_vote(self, chunk: CognitiveChunk) -> CognitiveChunk:
        action = chunk.get_section_content("action_selection_section") or {}
        current = action.get("selected_action", "provide_partial_answer")
        ethics = chunk.get_section_content("ethics_king_section") or {}
        dk = chunk.get_section_content("data_king_section") or {}

        votes: Dict[str, str] = {}
        eval_status = ethics.get("evaluation", {}).get("status", "good")
        if eval_status == "review_needed":
            votes["EthicsKing"] = "defer_decision"
        else:
            votes["EthicsKing"] = current

        quality = float(dk.get("quality_score", 0.5))
        if quality < 0.4:
            votes["DataKing"] = "ask_clarification"
        elif quality > 0.8:
            votes["DataKing"] = "answer_query"
        else:
            votes["DataKing"] = current

        votes["ForefrontKing"] = current

        # Weighted vote tally
        vote_counts: Dict[str, float] = {}
        total_w = sum(self.influence_weights.values())
        for king, vote in votes.items():
            w = self.influence_weights.get(king, 1.0)
            vote_counts[vote] = vote_counts.get(vote, 0.0) + w / total_w

        winner = max(vote_counts, key=vote_counts.get)  # type: ignore[arg-type]
        if vote_counts[winner] >= self.majority_threshold and winner != current:
            action["selected_action"] = winner
            action["council_override"] = True
            action["council_votes"] = votes
            chunk.update_section("action_selection_section", action)

        return chunk

    def ethics_ratio(self) -> float:
        """Normalized EthicsKing share of total influence (0–1)."""
        total = sum(float(v) for v in self.influence_weights.values())
        if total <= 0.0:
            return 0.0
        return float(self.influence_weights.get("EthicsKing", 0.0)) / total

    def to_state_dict(self) -> Dict[str, Any]:
        """Serialise council coordination state for checkpointing.

        Without this, every ``VerdantSystem()`` reconstructs a fresh Council
        with equal weights and empty history, discarding EthicsKing adaptation
        across sessions (mandatory-bridge salience plateau root cause A).
        """
        return {
            "influence_weights": dict(self.influence_weights),
            "interaction_history": list(self.interaction_history[-200:]),
            "conflict_history": list(self.conflict_history[-50:]),
            "metrics": dict(self.metrics),
            "majority_threshold": float(self.majority_threshold),
        }

    def from_state_dict(self, state: Dict[str, Any]) -> None:
        """Restore council state previously written by :meth:`to_state_dict`."""
        if not isinstance(state, dict):
            return
        weights = state.get("influence_weights", {})
        if isinstance(weights, dict):
            for king, w in weights.items():
                if king in self.influence_weights:
                    self.influence_weights[king] = float(w)
        history = state.get("interaction_history", [])
        if isinstance(history, list):
            self.interaction_history = list(history[-200:])
        conflicts = state.get("conflict_history", [])
        if isinstance(conflicts, list):
            self.conflict_history = list(conflicts[-50:])
        metrics = state.get("metrics", {})
        if isinstance(metrics, dict):
            self.metrics.update(metrics)
        if "majority_threshold" in state:
            self.majority_threshold = float(state["majority_threshold"])
        # Clamp after restore so corrupt/hand-edited sidecars cannot explode
        for king in self.influence_weights:
            self.influence_weights[king] = max(
                0.5, min(1.5, float(self.influence_weights[king])),
            )

    def _update_influence(self) -> None:
        if len(self.interaction_history) < 10:
            return
        # Gradually adapt weights based on recent conflict patterns
        recent = self.interaction_history[-20:]
        avg_conflicts = sum(r["conflicts"] for r in recent) / len(recent)
        # High conflict: raise EthicsKing and slightly lower peers so the
        # normalized ethics ratio can exceed ~0.50 (needed for
        # ratio * activation_0.7 >= ETHICS_ANCHOR_THRESHOLD 0.35).
        # Without peer downweight, Ethics=1.5 with peers stuck at 1.0 caps
        # the ratio at 0.4286 → max salience 0.300 (structural ceiling).
        if avg_conflicts > 0.5:
            self.influence_weights["EthicsKing"] = min(
                1.5, self.influence_weights["EthicsKing"] + 0.01,
            )
            for peer in ("DataKing", "ForefrontKing"):
                self.influence_weights[peer] = max(
                    0.5, self.influence_weights[peer] - 0.005,
                )
        for king in self.influence_weights:
            self.influence_weights[king] = max(0.5, min(1.5, self.influence_weights[king]))
