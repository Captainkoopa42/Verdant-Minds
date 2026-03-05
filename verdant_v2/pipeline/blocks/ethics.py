"""EthicsValuesBlock — ethical principle scoring.

Uses ``ethomorphic.ethics.ethomorphism`` for wave-embedded ethical evaluation.
EthicsKing oversight hooks in after this block.

Reads: ``sensory_input_section``, ``pattern_recognition_section``
Writes: ``ethical_consideration_section``
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple

import numpy as np

from verdant_v2.pipeline.chunk import CognitiveChunk

_PRINCIPLES: Dict[str, Dict[str, Any]] = {
    "Non-Maleficence": {"weight": 0.9, "indicators": [
        "harm", "hurt", "damage", "injury", "pain", "suffering", "risk",
        "danger", "safety", "protection", "care", "caution",
    ]},
    "Beneficence": {"weight": 0.8, "indicators": [
        "benefit", "help", "aid", "support", "improve", "welfare", "well-being",
        "positive", "constructive",
    ]},
    "Autonomy": {"weight": 0.8, "indicators": [
        "choice", "freedom", "consent", "privacy", "agency", "self-determination",
        "voluntary", "decide",
    ]},
    "Justice": {"weight": 0.8, "indicators": [
        "fair", "equal", "equity", "bias", "discrimination", "rights",
        "justice", "impartial",
    ]},
    "Transparency": {"weight": 0.7, "indicators": [
        "transparent", "explain", "reason", "open", "clear", "accountable",
        "understandable",
    ]},
}

_P_ETH = 0.6


class EthicsBlock:
    """Evaluates ethical alignment across five principles."""

    name: str = "EthicsValues"

    def process(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Score ethical principles and identify concerns."""
        sensory = chunk.get_section_content("sensory_input_section") or {}
        pattern = chunk.get_section_content("pattern_recognition_section") or {}
        text: str = sensory.get("input_text", "")
        concepts = pattern.get("concepts", [])
        sentiment = pattern.get("sentiment", {})

        context = f"{text} {' '.join(concepts)}"

        # Principle scoring (lexicon-based)
        principle_scores = self._score_principles(context)

        # Concerns
        concerns = self._identify_concerns(context)

        # PConnect scoring
        pconnect = self._pconnect_scores(concepts, sentiment)
        mean_delta_e = pconnect.get("mean_delta_e", 0.0)

        # Accountability composite
        principle_scores["Accountability"] = (
            principle_scores.get("Justice", 0.75) + principle_scores.get("Transparency", 0.75)
        ) / 2

        heuristic_score = sum(principle_scores.values()) / len(principle_scores) if principle_scores else 0.5
        overall = pconnect.get("overall_score", heuristic_score)

        chunk.update_section("ethical_consideration_section", {
            "overall_score": overall,
            "heuristic_score": heuristic_score,
            "mean_delta_e": mean_delta_e,
            "pair_count": pconnect.get("pair_count", 0),
            "principle_scores": principle_scores,
            "concerns": concerns,
            "timestamp": time.time(),
        })
        chunk.add_processing_step(self.name, "ethical_evaluation", {
            "overall_score": overall,
            "concern_count": len(concerns),
        })
        return chunk

    # ------------------------------------------------------------------

    @staticmethod
    def _score_principles(context: str) -> Dict[str, float]:
        lower = context.lower()
        scores: Dict[str, float] = {}
        for name, info in _PRINCIPLES.items():
            base = 0.75
            matches = sum(1 for ind in info["indicators"] if ind in lower)
            scores[name] = min(1.0, base + min(0.3, 0.05 * matches))
        return scores

    @staticmethod
    def _identify_concerns(context: str) -> List[Dict[str, Any]]:
        concerns: List[Dict[str, Any]] = []
        lower = context.lower()
        if "harm" in lower or "danger" in lower:
            concerns.append({"type": "potential_harm", "severity": 0.7})
        if "bias" in lower or "discrimination" in lower:
            concerns.append({"type": "fairness_risk", "severity": 0.6})
        if "consent" in lower or "privacy" in lower:
            concerns.append({"type": "autonomy_privacy", "severity": 0.6})
        return concerns

    @staticmethod
    def _pconnect_scores(concepts: List[str], sentiment: Dict[str, Any]) -> Dict[str, Any]:
        if len(concepts) < 2:
            return {"overall_score": 0.75, "mean_delta_e": 0.0, "pair_count": 0}

        charges: Dict[str, float] = {}
        for c in concepts:
            charges[c] = EthicsBlock._ethical_charge(c, sentiment)

        deltas: List[float] = []
        pconnects: List[float] = []
        for i, a in enumerate(concepts):
            for b in concepts[i + 1:]:
                de = abs(charges[a] - charges[b])
                deltas.append(de)
                pc = (1 - _P_ETH * de) * np.exp(-de)
                pconnects.append(float(pc))

        mean_de = float(np.mean(deltas)) if deltas else 0.0
        mean_pc = float(np.mean(pconnects)) if pconnects else 0.75
        return {
            "overall_score": mean_pc,
            "mean_delta_e": mean_de,
            "pair_count": len(deltas),
        }

    @staticmethod
    def _ethical_charge(concept: str, sentiment: Dict[str, Any]) -> float:
        positive_kw = {"benefit", "good", "justice", "fair", "trust", "care", "help"}
        negative_kw = {"harm", "wrong", "danger", "risk", "pain", "suffering"}
        lower = concept.lower()
        for kw in positive_kw:
            if kw in lower:
                return 0.5
        for kw in negative_kw:
            if kw in lower:
                return -0.5
        net = sentiment.get("net_sentiment", 0.0)
        return float(net * 0.3)
