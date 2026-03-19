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

    def generate_self_referential_input(self, scaffold_context: ScaffoldContext | None = None) -> str:
        """Format the system's own developmental state as cultivation input."""
        context = scaffold_context or self._context
        templates = [
            self._template_growth_reflection,
            self._template_boundary_reflection,
            self._template_consolidation_reflection,
            self._template_identity_reflection,
        ]
        return templates[context.cycle % len(templates)](context)

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

    @staticmethod
    def _join_terms(items: list[str]) -> str:
        cleaned = [item.strip() for item in items if item and item.strip()]
        if not cleaned:
            return "coherence, emergence, and bounded autonomy"
        if len(cleaned) == 1:
            return cleaned[0]
        if len(cleaned) == 2:
            return f"{cleaned[0]} and {cleaned[1]}"
        return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"

    def _bud_clause(self, context: ScaffoldContext) -> str:
        if not context.recent_bud_events:
            return "No recent budding event has broken the current boundary, so growth remains concentrated within existing basins."
        event = context.recent_bud_events[-1]
        parent_id = str(event.get("parent_id") or context.largest_basin_id or "the largest basin")
        basin_id = str(event.get("basin_id") or "a daughter basin")
        cycle = int(event.get("cycle", context.cycle))
        return (
            f"Recent growth produced {basin_id} from {parent_id} at cycle {cycle}, "
            "turning local pressure into a new boundary for emergence."
        )

    def _dormancy_clause(self, context: ScaffoldContext) -> str:
        if not context.recent_dormancy_events:
            return "Dormancy is absent in the latest window, so consolidation and activation remain in active balance."
        count = len(context.recent_dormancy_events)
        latest = context.recent_dormancy_events[-1]
        return (
            f"{count} recent dormancy events mark rest and consolidation; "
            f"the latest boundary softened around {latest.get('basin_id', 'a basin')} at cycle {latest.get('cycle', context.cycle)}."
        )

    def _template_growth_reflection(self, context: ScaffoldContext) -> str:
        latest_terms = self._join_terms(context.latest_emergent_names[:4])
        return (
            f"The cognitive system has developed {context.total_emergent_count} emergent concepts across "
            f"{context.active_basin_count} active basins and {context.dormant_basin_count} dormant basins over "
            f"{context.cycle} developmental cycles. The thermodynamic flexibility T_g is {context.t_g:.4f}, "
            f"so coherence and constraint remain in dynamic tension. The largest basin "
            f"({context.largest_basin_id or 'no dominant basin'}) holds {context.largest_basin_emergent_count} emergent concepts, "
            f"while the latest self-description links {latest_terms}. {self._bud_clause(context)} {self._dormancy_clause(context)}"
        )

    def _template_boundary_reflection(self, context: ScaffoldContext) -> str:
        top_terms = self._join_terms(context.top_concepts[:3])
        latest_terms = self._join_terms(context.latest_emergent_names[:3])
        return (
            f"At cycle {context.cycle}, identity in the scaffold is distributed across {context.node_count} nodes and "
            f"{context.edge_count} edges, with {context.total_emergent_count} emergent structures preserving autonomy within "
            f"{context.active_basin_count} active basins. T_g={context.t_g:.4f} signals flexible boundary control rather than rigid closure. "
            f"The most activated concepts are {top_terms}, and the newest emergent bridges are {latest_terms}. "
            f"{self._bud_clause(context)} {self._dormancy_clause(context)}"
        )

    def _template_consolidation_reflection(self, context: ScaffoldContext) -> str:
        recent = self._join_terms(context.recent_emergents[:4])
        return (
            f"Developmental cycle {context.cycle} reveals a scaffold balancing emergence with consolidation: "
            f"{context.total_emergent_count} emergent concepts persist, {context.active_basin_count} basins remain active, "
            f"and {context.dormant_basin_count} basins rest in dormancy. The current flexibility value T_g={context.t_g:.4f} "
            f"keeps growth bounded while allowing boundary-crossing synthesis. Recent emergents such as {recent} "
            f"trace coherence, identity, and adaptive constraint through the memory web. "
            f"The largest basin {context.largest_basin_id or 'is unresolved'} contains {context.largest_basin_emergent_count} emergent concepts. "
            f"{self._dormancy_clause(context)} {self._bud_clause(context)}"
        )

    def _template_identity_reflection(self, context: ScaffoldContext) -> str:
        basin_terms = self._join_terms(sorted(context.basin_emergent_distribution)[:3])
        return (
            f"The system is processing its own structure as input: {context.total_emergent_count} emergent concepts, "
            f"{context.active_basin_count} active basins, {context.dormant_basin_count} dormant basins, and an earlier-share of "
            f"{context.earlier_share:.3f} across {context.cycle} cycles. T_g={context.t_g:.4f} indicates how much flexibility identity can tolerate "
            f"without losing coherence. Basin patterns now center on {basin_terms}, and the dominant basin "
            f"{context.largest_basin_id or 'remains diffuse'} carries {context.largest_basin_emergent_count} emergent concepts. "
            f"{self._bud_clause(context)} {self._dormancy_clause(context)}"
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
