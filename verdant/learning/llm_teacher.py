"""Optional LLM teacher for parallel expression learning."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from verdant.pipeline.blocks.language import LanguageContext


class LLMTeacher:
    """Teacher/translator layer that never replaces template generation."""

    _CORPORATE_FLUFF_MARKERS = (
        "peppa pig",
        "corporate synergy",
        "stakeholder alignment",
        "value proposition",
        "brand uplift",
    )

    def __init__(
        self,
        model: str = "llama3",
        *,
        dataset_path: str = "data/akiku_expression_dataset.jsonl",
        timeout_s: float = 30.0,
        temperature: float = 0.45,
    ) -> None:
        self.model = model
        self.dataset_path = Path(dataset_path)
        self.timeout_s = max(5.0, float(timeout_s))
        self.temperature = float(temperature)

    def teach(self, context: LanguageContext, raw_output: str) -> dict[str, Any]:
        controls = context.extra.get("generation_controls", {}) if isinstance(context.extra, dict) else {}
        t_g = float(context.extra.get("glass_transition_temp", 0.5)) if isinstance(context.extra, dict) else 0.5
        f_c = float(context.cognitive_free_energy)
        entropy = float(context.wave_entropy)

        prompt = self._build_prompt(
            raw_output=raw_output,
            context=context,
            t_g=t_g,
            f_c=f_c,
            entropy=entropy,
        )
        llm_output = self._run_ollama(prompt, controls=controls)
        if self._is_fluff(llm_output):
            llm_output = self._run_ollama(
                prompt
                + "\n\nRegenerate with stricter grounding: no corporate language, no mascot fluff, no invented facts.",
                controls=controls,
            )

        return {
            "llm_output": llm_output.strip(),
            "meta": {
                "model": self.model,
                "temperature": float(controls.get("temperature", self.temperature)),
                "top_p": float(controls.get("top_p", 0.9)),
                "frequency_penalty": float(controls.get("frequency_penalty", 0.2)),
                "phase": str(controls.get("phase", context.phase_state)),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

    def log_example(
        self,
        *,
        cycle: int,
        state: dict[str, Any],
        template_output: str,
        llm_output: str,
        t_g: float,
        f_c: float,
        entropy: float,
        concepts: list[str],
    ) -> None:
        payload = {
            "cycle": int(cycle),
            "state": state,
            "template_output": template_output,
            "llm_output": llm_output,
            "t_g": float(t_g),
            "f_c": float(f_c),
            "entropy": float(entropy),
            "concepts": list(concepts),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)
        with self.dataset_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _build_prompt(
        self,
        *,
        raw_output: str,
        context: LanguageContext,
        t_g: float,
        f_c: float,
        entropy: float,
    ) -> str:
        concepts = ", ".join(context.key_concepts[:8]) if context.key_concepts else "none"
        reasoning = context.reasoning_summary or "none"
        return (
            "You are a teacher/translator for Verdant.\n"
            "Rewrite the template response into natural language while preserving meaning exactly.\n"
            "Do not invent facts, claims, or entities. Avoid corporate fluff.\n"
            f"Template response:\n{raw_output}\n\n"
            f"Key concepts: {concepts}\n"
            f"Reasoning summary: {reasoning}\n"
            f"Thermodynamic state: T_g={t_g:.4f}, F_c={f_c:.4f}, entropy={entropy:.4f}\n"
            "Return only the rewritten response."
        )

    def _run_ollama(self, prompt: str, *, controls: dict[str, Any]) -> str:
        temp = f"{float(controls.get('temperature', self.temperature)):.4f}"
        top_p = f"{float(controls.get('top_p', 0.9)):.4f}"
        freq = f"{float(controls.get('frequency_penalty', 0.2)):.4f}"
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
            proc = subprocess.run(primary, check=False, capture_output=True, text=True, timeout=self.timeout_s)
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip()
        except Exception:
            pass
        proc2 = subprocess.run(fallback, check=True, capture_output=True, text=True, timeout=self.timeout_s)
        return proc2.stdout.strip()

    def _is_fluff(self, text: str) -> bool:
        lowered = text.lower()
        return any(marker in lowered for marker in self._CORPORATE_FLUFF_MARKERS)
