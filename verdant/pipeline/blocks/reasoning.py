"""ReasoningPlanningBlock — deductive, inductive, abductive inference.

Reads: ``pattern_recognition_section``, ``memory_section``, ``ethics_king_section``
Writes: ``reasoning_section``
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

import numpy as np

from verdant_v2.pipeline.chunk import CognitiveChunk


class ReasoningBlock:
    """Generates template-based inferences across multiple reasoning types."""

    name: str = "ReasoningPlanning"

    def process(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Apply reasoning to pattern and memory data."""
        pattern = chunk.get_section_content("pattern_recognition_section") or {}
        memory = chunk.get_section_content("memory_section") or {}

        concepts = pattern.get("concepts", [])
        keywords = pattern.get("keywords", [])
        tensions = pattern.get("tension_coefficients", {})
        wave = chunk.get_section_content("wave_function_section") or {}
        entropy = float(wave.get("entropy", 0.0))

        # Build premises
        premises = self._build_premises(concepts, keywords, memory)

        # Apply reasoning types
        deductive = self._deductive(premises, concepts, entropy)
        inductive = self._inductive(premises, concepts, memory, entropy)
        abductive = self._abductive(premises, concepts, tensions, entropy)
        analogical = self._analogical(concepts, entropy)

        all_inferences = deductive + inductive + abductive + analogical

        # Wave uncertainty integration
        magnitude = float(wave.get("magnitude", 0.5))
        phase = float(wave.get("phase", 0.0))
        adjustments = self._wave_uncertainty(all_inferences, magnitude, phase, entropy)

        # Inconsistencies
        inconsistencies = self._detect_inconsistencies(all_inferences)

        # Confidence
        confidence = self._compute_confidence(
            deductive, inductive, abductive, analogical, inconsistencies, entropy,
        )

        # Plan
        plan = self._build_plan(premises, all_inferences, inconsistencies, adjustments)

        chunk.update_section("reasoning_section", {
            "premises": premises,
            "inferences": {
                "deductive": deductive,
                "inductive": inductive,
                "abductive": abductive,
                "analogical": analogical,
            },
            "reasoning_plan": plan,
            "inconsistencies": inconsistencies,
            "uncertainty_adjustments": adjustments,
            "confidence_score": confidence,
            "processed_timestamp": time.time(),
        })
        chunk.add_processing_step(self.name, "reasoning", {
            "inference_count": len(all_inferences),
            "confidence": confidence,
        })
        return chunk

    # ------------------------------------------------------------------

    @staticmethod
    def _build_premises(
        concepts: List[str],
        keywords: List[str],
        memory: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        premises: List[Dict[str, Any]] = []
        for c in concepts[:5]:
            premises.append({
                "type": "concept_presence",
                "content": f"The input involves the concept '{c}'.",
                "confidence": 0.8,
            })
        activated = memory.get("activated_concepts", {})
        for c, level in list(activated.items())[:3]:
            premises.append({
                "type": "memory_relevance",
                "content": f"Memory concept '{c}' is activated at {level:.2f}.",
                "confidence": min(1.0, level + 0.2),
            })
        return premises

    @staticmethod
    def _deductive(
        premises: List[Dict[str, Any]],
        concepts: List[str],
        entropy: float,
    ) -> List[Dict[str, Any]]:
        inferences: List[Dict[str, Any]] = []
        if len(concepts) >= 2:
            inferences.append({
                "type": "deductive",
                "content": f"Given '{concepts[0]}' and '{concepts[1]}', "
                           f"we can deduce a relationship between them.",
                "confidence": max(0.3, 0.9 - entropy * 0.15),
                "rule": "categorical_syllogism",
            })
        if entropy > 1.0 and len(inferences) > 1:
            inferences = inferences[:1]
        return inferences

    @staticmethod
    def _inductive(
        premises: List[Dict[str, Any]],
        concepts: List[str],
        memory: Dict[str, Any],
        entropy: float,
    ) -> List[Dict[str, Any]]:
        inferences: List[Dict[str, Any]] = []
        activated = memory.get("activated_concepts", {})
        for c in concepts[:3]:
            level = activated.get(c, 0.0)
            if level < 0.7:
                inferences.append({
                    "type": "inductive",
                    "content": f"The concept '{c}' appears related to the broader theme.",
                    "confidence": max(0.3, 0.7 - entropy * 0.1),
                    "rule": "generalization",
                })
        return inferences

    @staticmethod
    def _abductive(
        premises: List[Dict[str, Any]],
        concepts: List[str],
        tensions: Dict[str, float],
        entropy: float,
    ) -> List[Dict[str, Any]]:
        inferences: List[Dict[str, Any]] = []
        if tensions:
            top = max(tensions, key=tensions.get)  # type: ignore[arg-type]
            inferences.append({
                "type": "abductive",
                "content": f"The tension '{top}' suggests an underlying conflict "
                           f"worth exploring.",
                "confidence": max(0.3, 0.6 - entropy * 0.1),
                "rule": "inference_to_best_explanation",
            })
        return inferences

    @staticmethod
    def _analogical(concepts: List[str], entropy: float) -> List[Dict[str, Any]]:
        if len(concepts) < 2:
            return []
        # Optimal at entropy ~1.5
        factor = max(0.3, 1.0 - abs(entropy - 1.5) * 0.3)
        return [{
            "type": "analogical",
            "content": f"'{concepts[0]}' may relate to '{concepts[1]}' by analogy.",
            "confidence": 0.65 * factor,
            "rule": "property_transfer",
        }]

    @staticmethod
    def _wave_uncertainty(
        inferences: List[Dict[str, Any]],
        magnitude: float,
        phase: float,
        entropy: float,
    ) -> List[Dict[str, Any]]:
        adjustments: List[Dict[str, Any]] = []
        phase_factor = 0.5 + 0.5 * np.cos(phase)
        for inf in inferences:
            raw = magnitude * (1 - entropy / 5.0)
            adjusted = float(raw * phase_factor)
            delta = adjusted - inf["confidence"]
            if abs(delta) > 0.1:
                adjustments.append({
                    "inference": inf["content"][:60],
                    "original": inf["confidence"],
                    "adjusted": adjusted,
                    "delta": delta,
                })
        return adjustments

    @staticmethod
    def _detect_inconsistencies(inferences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        found: List[Dict[str, Any]] = []
        contents = [inf["content"] for inf in inferences]
        for i, a in enumerate(contents):
            for b in contents[i + 1:]:
                if "not" in a and a.replace("not ", "") in b:
                    found.append({"type": "contradiction", "a": a[:60], "b": b[:60]})
        return found

    @staticmethod
    def _compute_confidence(
        deductive: list,
        inductive: list,
        abductive: list,
        analogical: list,
        inconsistencies: list,
        entropy: float,
    ) -> float:
        total = len(deductive) + len(inductive) + len(abductive) + len(analogical)
        base = 0.5
        base += min(0.3, 0.05 * total)
        if deductive:
            base += 0.2 * min(1.0, len(deductive) / 3)
        if inconsistencies:
            base -= 0.1 * min(1.0, len(inconsistencies) / 2)
        if deductive and len(deductive) > len(inductive):
            base += max(0.0, 0.2 - 0.04 * entropy)
        else:
            base += 0.1 - 0.02 * abs(entropy - 2.0)
        return max(0.1, min(0.95, base))

    @staticmethod
    def _build_plan(
        premises: list,
        inferences: list,
        inconsistencies: list,
        adjustments: list,
    ) -> List[Dict[str, Any]]:
        return [
            {"step": 1, "name": "Premise Identification", "items": premises[:5]},
            {"step": 2, "name": "Inference Generation", "items": inferences[:3]},
            {"step": 3, "name": "Uncertainty Evaluation", "items": adjustments[:3]},
            {"step": 4, "name": "Inconsistency Resolution", "items": inconsistencies},
            {"step": 5, "name": "Conclusion Formation", "items": [
                inf for inf in inferences if inf.get("confidence", 0) > 0.5
            ][:3]},
        ]
