"""LanguageProcessingBlock — response generation with wave modulation.

Reads: ``action_selection_section``, ``reasoning_section``, ``memory_section``,
       ``ethics_king_section``, ``sensory_input_section``, ``wave_function_section``
Writes: ``language_processing_section``
"""

from __future__ import annotations

import json
import subprocess
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Protocol, runtime_checkable

import numpy as np

from verdant.pipeline.language.thermal_bridge import map_runtime_generation_controls
from verdant.pipeline.chunk import CognitiveChunk


# ---------------------------------------------------------------------------
# LanguageBackend protocol
# ---------------------------------------------------------------------------

class LanguageContext:
    """Context passed to a language backend for generation."""

    def __init__(
        self,
        selected_action: str,
        ethical_tone: str,
        phase_state: str,
        wave_entropy: float,
        cognitive_free_energy: float,
        key_concepts: List[str],
        reasoning_summary: str,
        reflection_loop_state: Optional[List[Dict[str, Any]]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.selected_action = selected_action
        self.ethical_tone = ethical_tone
        self.phase_state = phase_state
        self.wave_entropy = wave_entropy
        self.cognitive_free_energy = cognitive_free_energy
        self.key_concepts = key_concepts
        self.reasoning_summary = reasoning_summary
        self.reflection_loop_state = reflection_loop_state or []
        self.extra = extra or {}


@runtime_checkable
class LanguageBackend(Protocol):
    """Protocol for pluggable language generation backends."""

    def generate(self, context: LanguageContext) -> str:
        """Generate a response from *context*."""
        ...


# ---------------------------------------------------------------------------
# Template backend (default — v1 behaviour)
# ---------------------------------------------------------------------------

class TemplateBackend:
    """Simple template-based response generation (v1 behaviour)."""

    def generate(self, context: LanguageContext) -> str:
        """Generate a response using templates."""
        action = context.selected_action
        concepts = context.key_concepts
        reasoning = context.reasoning_summary

        if action == "answer_query":
            return self._direct_answer(concepts, reasoning)
        if action == "provide_partial_answer":
            return self._partial_answer(concepts, reasoning)
        if action == "ask_clarification":
            return self._clarification(concepts)
        if action == "defer_decision":
            return self._deferral(concepts)
        return f"I've processed your input about {', '.join(concepts[:3]) or 'this topic'}."

    @staticmethod
    def _direct_answer(concepts: List[str], reasoning: str) -> str:
        topic = ", ".join(concepts[:3]) or "this topic"
        return (
            f"Based on my analysis of {topic}: {reasoning} "
            f"This conclusion reflects the integrated assessment of the relevant concepts."
        )

    @staticmethod
    def _partial_answer(concepts: List[str], reasoning: str) -> str:
        topic = ", ".join(concepts[:3]) or "this topic"
        return (
            f"I have a preliminary understanding of {topic}. {reasoning} "
            f"However, I'd like to explore this further before reaching a definitive conclusion."
        )

    @staticmethod
    def _clarification(concepts: List[str]) -> str:
        topic = concepts[0] if concepts else "your query"
        return (
            f"I'd like to understand more about {topic}. "
            f"Could you provide additional context or clarify your main intent?"
        )

    @staticmethod
    def _deferral(concepts: List[str]) -> str:
        topic = ", ".join(concepts[:2]) or "this matter"
        return (
            f"This involves important ethical considerations around {topic}. "
            f"I want to be thoughtful here — could you provide more context?"
        )


# ---------------------------------------------------------------------------
# LLM backend (stub)
# ---------------------------------------------------------------------------

class LLMBackend:
    """Ollama-backed LLM response generation."""

    _CORPORATE_FLUFF_MARKERS = (
        "peppa pig",
        "corporate synergy",
        "stakeholder alignment",
        "value proposition",
        "brand uplift",
    )

    def __init__(self, model: str = "llama3", timeout_s: float = 30.0) -> None:
        self.model = model
        self.timeout_s = max(5.0, float(timeout_s))

    def generate(self, context: LanguageContext) -> str:
        controls = map_runtime_generation_controls(
            t_g=float(context.extra.get("glass_transition_temp", 0.5725)),
            f_c=context.cognitive_free_energy,
            entropy=context.wave_entropy,
        )
        h1_ok = bool(context.extra.get("h1_triangle_valid", True))
        hci = float(context.extra.get("housed_contradiction_index", 0.0))
        thermo_cost_penalty = 0.0 if h1_ok else (1.0 + max(0.0, 0.5 - hci))

        prompt = self._build_prompt(context, controls, thermo_cost_penalty)
        response = self._run_ollama(prompt, controls, timeout=self.timeout_s)
        if self._needs_regeneration(response, h1_ok):
            regen_prompt = (
                prompt
                + "\n\nREGENERATION CONSTRAINT:\n"
                "Prior output violated coherence constraints. "
                "Eliminate corporate fluff and satisfy U = (M + -M)^i explicitly."
            )
            response = self._run_ollama(regen_prompt, controls, timeout=self.timeout_s + 10.0)
        return response.strip()

    def _build_prompt(self, context: LanguageContext, controls: Dict[str, Any], thermo_cost_penalty: float) -> str:
        reflection_state = context.reflection_loop_state[-25:]
        reflection_blob = json.dumps(reflection_state, ensure_ascii=False)
        key_terms = ", ".join(context.key_concepts[:8]) if context.key_concepts else "identity, coherence, contradiction"
        return (
            "You are Verdant's internal language emergence module.\n"
            "Produce one concise response grounded in current thermodynamic cognition.\n"
            "Constraint: satisfy Soul Equation U = (M + -M)^i via explicit contradiction-housing.\n"
            f"Action: {context.selected_action}\n"
            f"Phase: {context.phase_state}\n"
            f"Ethical tone: {context.ethical_tone or 'balanced'}\n"
            f"Wave entropy: {context.wave_entropy:.4f}\n"
            f"Cognitive Free Energy F_c: {context.cognitive_free_energy:.4f}\n"
            f"Thermo controls: temperature={controls['temperature']:.4f}, top_p={controls['top_p']:.4f}, "
            f"frequency_penalty={controls['frequency_penalty']:.4f}, phase={controls['phase']}\n"
            f"Thermo-cost penalty: {thermo_cost_penalty:.4f}\n"
            f"Key concepts: {key_terms}\n"
            f"Reasoning summary: {context.reasoning_summary or 'none'}\n"
            "25-cycle reflection loop state (JSON):\n"
            f"{reflection_blob}\n"
            "Return only the response text."
        )

    def _run_ollama(self, prompt: str, controls: Dict[str, Any], *, timeout: float) -> str:
        temp = f"{float(controls['temperature']):.4f}"
        top_p = f"{float(controls['top_p']):.4f}"
        freq = f"{float(controls['frequency_penalty']):.4f}"
        primary = [
            "ollama",
            "run",
            self.model,
            "--temperature",
            temp,
            "--top-p",
            top_p,
            "--frequency-penalty",
            freq,
            prompt,
        ]
        fallback = ["ollama", "run", self.model, prompt]
        try:
            proc = subprocess.run(primary, check=False, capture_output=True, text=True, timeout=timeout)
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip()
        except Exception:
            pass
        proc2 = subprocess.run(fallback, check=True, capture_output=True, text=True, timeout=timeout)
        return proc2.stdout.strip()

    def _needs_regeneration(self, text: str, h1_ok: bool) -> bool:
        lowered = text.lower()
        fluff = any(marker in lowered for marker in self._CORPORATE_FLUFF_MARKERS)
        soul_missing = "(m + -m)^i" not in lowered and "contradiction" not in lowered
        return fluff or soul_missing or (not h1_ok)


# ---------------------------------------------------------------------------
# Interference signature
# ---------------------------------------------------------------------------

_ETHICAL_TONE_MAP = {
    0: "explicitly consider potential harms",
    1: "frame toward constructive outcomes",
    2: "offer options for choice",
    3: "account for multiple stakeholders",
    4: "explicit reasoning shown",
}


def _interference_signature(coherence: float, entropy: float, magnitude: float) -> str:
    if coherence > 0.75 and magnitude >= 0.6:
        return "convergent"
    if coherence < 0.35 and entropy > 0.6:
        return "divergent"
    if entropy >= 0.55:
        return "exploratory"
    return "stable"


def _apply_wave_modulation(text: str, sig: str, tone: str) -> str:
    suffix = ""
    if sig == "convergent":
        text = text.replace("might", "will").replace("could", "can")
        suffix = " The direct path is clear."
    elif sig == "exploratory":
        suffix = " Multiple plausible angles here; conditional framing helps compare them."
    elif sig == "divergent":
        suffix = " Both perspectives can be valid here; I want to house that tension explicitly."
    else:
        suffix = " Balanced and measured."
    if tone:
        suffix += f" (Ethical tone: {tone})"
    return text + suffix


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------

class LanguageBlock:
    """Generates language output with wave-modulation and ethical tone."""

    name: str = "LanguageProcessing"

    def __init__(self, backend: Optional[LanguageBackend] = None) -> None:
        self.backend: LanguageBackend = backend or TemplateBackend()
        self._reflection_loop: Deque[Dict[str, Any]] = deque(maxlen=25)

    def process(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Generate the response."""
        action_sec = chunk.get_section_content("action_selection_section") or {}
        reasoning = chunk.get_section_content("reasoning_section") or {}
        ethics_k = chunk.get_section_content("ethics_king_section") or {}
        wave = chunk.get_section_content("wave_function_section") or {}
        pattern = chunk.get_section_content("pattern_recognition_section") or {}
        forefront = chunk.get_section_content("forefront_king_section") or {}

        selected_action = action_sec.get("selected_action", "provide_partial_answer")
        concepts = pattern.get("concepts", [])[:7]
        conf = float(reasoning.get("confidence_score", 0.5))
        entropy = float(wave.get("entropy", 0.0))
        magnitude = float(wave.get("magnitude", 0.5))
        phase_val = float(wave.get("phase", 0.0))
        processing_metrics = chunk.get_section_content("processing_metrics_section") or {}
        t_g = float(processing_metrics.get("glass_transition_temp", 0.5725))
        cognitive_free_energy = float(processing_metrics.get("cognitive_free_energy", max(0.0, 1.0 - conf)))
        coherence_sec = chunk.get_section_content("coherence_invariants_section") or {}

        # Ethical tone
        ethical_eval = ethics_k.get("evaluation", {})
        tone_marker = ""
        ps = ethical_eval.get("principle_scores", {})
        if ps:
            worst_idx = min(range(min(len(ps), 5)), key=lambda i: list(ps.values())[i])
            tone_marker = _ETHICAL_TONE_MAP.get(worst_idx, "")

        # Phase state
        phase_state = forefront.get("phase_state", "Flexible")

        # Reasoning summary
        plan = reasoning.get("reasoning_plan", [])
        conclusions = plan[-1].get("items", []) if plan else []
        reasoning_summary = ""
        if conclusions:
            first = conclusions[0]
            reasoning_summary = first.get("content", "") if isinstance(first, dict) else str(first)

        # Interference
        coherence = 1.0 - abs(phase_val) / (np.pi + 1e-10)
        sig = _interference_signature(coherence, entropy, magnitude)

        ctx = LanguageContext(
            selected_action=selected_action,
            ethical_tone=tone_marker,
            phase_state=phase_state,
            wave_entropy=entropy,
            cognitive_free_energy=cognitive_free_energy,
            key_concepts=concepts,
            reasoning_summary=reasoning_summary,
            reflection_loop_state=list(self._reflection_loop),
            extra={
                "glass_transition_temp": t_g,
                "h1_triangle_valid": bool(coherence_sec.get("triangle_valid_at_alpha1", True)),
                "housed_contradiction_index": float(coherence_sec.get("housed_contradiction_index", 0.0)),
            },
        )
        raw_response = self.backend.generate(ctx)
        response = _apply_wave_modulation(raw_response, sig, tone_marker)

        self._reflection_loop.append(
            {
                "cycle": int(processing_metrics.get("cycle", 0)),
                "phase": phase_state,
                "t_g": t_g,
                "f_c": cognitive_free_energy,
                "action": selected_action,
                "sig": sig,
                "h1_triangle_valid": bool(coherence_sec.get("triangle_valid_at_alpha1", True)),
                "hci": float(coherence_sec.get("housed_contradiction_index", 0.0)),
                "key_concepts": concepts[:5],
            }
        )

        chunk.update_section("language_processing_section", {
            "generated_response": response,
            "language_style": {
                "formality": 0.7 if selected_action in ("answer_query", "defer_decision") else 0.5,
                "complexity": max(0.3, min(0.8, conf + 0.1)),
                "precision": max(0.4, min(0.9, conf + 0.2)),
            },
            "interference_signature": sig,
            "ethical_tone": tone_marker,
            "wave_response_parameters": {
                "entropy": entropy,
                "magnitude": magnitude,
                "phase_coherence": coherence,
            },
            "processed_timestamp": time.time(),
        })
        chunk.add_processing_step(self.name, "language_generation", {
            "action": selected_action,
            "signature": sig,
        })
        return chunk
