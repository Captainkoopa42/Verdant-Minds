"""Scaffold-aware tutor provider for contextual cultivation inputs."""

from __future__ import annotations

import logging
import os

from cultivation.providers.local import LocalProvider
from cultivation.schemas import ScaffoldContext

_LOG = logging.getLogger(__name__)


class TutorProvider:
    """LLM provider that reads scaffold state to generate contextual inputs."""

    def __init__(
        self,
        backend: str = "groq",
        model: str | None = None,
        api_key_env: str | None = None,
        proposals_per_call: int = 1,
        temperature: float = 0.8,
    ) -> None:
        self.backend = backend.lower()
        self.model = model
        self.api_key_env = api_key_env
        self.proposals_per_call = max(1, int(proposals_per_call))
        self.temperature = float(temperature)
        self._local_fallback = LocalProvider()
        self._context = ScaffoldContext(
            total_nodes=0,
            emergent_count=0,
            basin_count=0,
            basin_emergent_distribution={},
            top_concepts=[],
            recent_emergents=[],
            earlier_share=0.0,
            cycle=0,
        )
        self.last_fallback: bool = False
        self.last_error: str | None = None

    def set_scaffold_context(self, context: ScaffoldContext) -> None:
        """Update the provider with current system state for next generation."""
        self._context = context

    def generate(self, prompt: str, *, seed: int | None = None) -> str:
        """Generate a cultivation input using LLM + scaffold context."""
        self.last_fallback = False
        self.last_error = None
        try:
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(prompt)
            return self._call_llm(system_prompt, user_prompt, seed=seed)
        except Exception as exc:  # pragma: no cover - tested via monkeypatched failure path
            self.last_fallback = True
            self.last_error = str(exc)
            _LOG.warning("TutorProvider backend failed; using deterministic fallback: %s", exc)
            return self._local_fallback.generate(prompt, seed=seed)

    def _build_system_prompt(self) -> str:
        """Build a system prompt that includes scaffold state summary."""
        return (
            "You are a tutor for a cognitive architecture called Verdant-Minds.\n"
            "Your job is to generate a single thought-provoking input that will stimulate\n"
            "conceptual emergence in the system.\n\n"
            "Current system state:\n"
            f"- Total concepts: {self._context.total_nodes}\n"
            f"- Emergent concepts: {self._context.emergent_count}\n"
            f"- Active basins: {self._context.basin_count}\n"
            f"- Basin emergent distribution: {self._context.basin_emergent_distribution}\n"
            f"- Top activated concepts: {self._context.top_concepts}\n"
            f"- Recent emergents: {self._context.recent_emergents}\n"
            f"- Scaffold earlier-share: {self._context.earlier_share:.3f}\n"
            f"- Current cycle: {self._context.cycle}\n"
            "\nGenerate an input that:\n"
            "1. Creates tension between existing concepts\n"
            "2. Bridges concepts from different basins when possible\n"
            "3. Introduces productive contradictions\n"
            "4. Is a question or philosophical prompt, not a statement\n"
            "\nRespond with ONLY the input text. No explanation. No preamble."
        )

    def _build_user_prompt(self, prompt: str) -> str:
        return (
            f"Base strategy prompt:\n{prompt}\n\n"
            f"Generate {self.proposals_per_call} candidate question(s), then return the single best one."
        )

    def _call_llm(self, system_prompt: str, user_prompt: str, *, seed: int | None = None) -> str:
        if self.backend == "local":
            base_prompt = user_prompt.split("Base strategy prompt:\n", 1)[-1].split("\n\n", 1)[0].strip()
            return self._local_fallback.generate(base_prompt, seed=seed)

        if self.backend == "groq":
            api_key = os.getenv(self.api_key_env or "GROQ_API_KEY")
            if not api_key:
                raise RuntimeError("Missing Groq API key")
            from groq import Groq  # type: ignore

            client = Groq(api_key=api_key)
            resp = client.chat.completions.create(
                model=self.model or "llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
            )
            return (resp.choices[0].message.content or "").strip()

        if self.backend == "mistral":
            api_key = os.getenv(self.api_key_env or "MISTRAL_API_KEY")
            if not api_key:
                raise RuntimeError("Missing Mistral API key")
            from mistralai import Mistral  # type: ignore

            client = Mistral(api_key=api_key)
            resp = client.chat.complete(
                model=self.model or "mistral-small-latest",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
            )
            return (resp.choices[0].message.content or "").strip()

        if self.backend == "anthropic":
            api_key = os.getenv(self.api_key_env or "ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError("Missing Anthropic API key")
            import anthropic  # type: ignore

            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model=self.model or "claude-3-5-haiku-latest",
                max_tokens=220,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return "".join(block.text for block in msg.content if getattr(block, "type", "") == "text").strip()

        raise ValueError(f"Unsupported tutor backend: {self.backend}")
