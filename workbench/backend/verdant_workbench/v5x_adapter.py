from __future__ import annotations

from verdant_development.v5x import V5XDevelopmentPipeline

from .adapter import VerdantEngineAdapter
from .events import development_events
from .models import CommandEnvelope, CommandReceipt, LanguageSentenceTeachRequest


class V5XEngineAdapter(VerdantEngineAdapter):
    """Experimental Workbench adapter that routes ordinary language through cognition."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.development = V5XDevelopmentPipeline(self.development)

    def teach_language_sentence(
        self,
        envelope: CommandEnvelope,
        request: LanguageSentenceTeachRequest,
    ) -> CommandReceipt:
        self._check_envelope(envelope)
        before_revision = self.state_revision
        before_cycle = self.kernel.state.cycle
        before_fingerprint = self.kernel.fingerprint()
        planned = self.language.plan_sentence(
            self.kernel,
            request.sentence,
            event_key=request.event_key,
        )
        result = self.development.advance(self.kernel, planned.command)
        events = development_events(
            run_id=self.run_id,
            organism_id=self.organism_id,
            kernel=self.kernel,
            command_id=envelope.command_id,
            result=result,
        )
        return self._receipt(
            envelope=envelope,
            before_revision=before_revision,
            before_cycle=before_cycle,
            before_fingerprint=before_fingerprint,
            events=events,
            replayed=result.replayed,
            result={
                "experience_event_key": result.experience.event_key,
                "analysis": planned.analysis.model_dump(mode="json"),
                "language_action": "sentence",
                "semantic_firewall_held": result.semantic_firewall_held,
                "candidate_scope_ids": list(result.candidate_scope_ids),
                "developmental_submission": True,
                "thermodynamic_observation": (
                    result.thermodynamics.model_dump(mode="json")
                    if result.thermodynamics is not None
                    else None
                ),
            },
        )
