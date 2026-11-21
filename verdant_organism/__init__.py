"""The Verdant organism: one place where a whole Verdant life is put together.

Until 2026-11-20 every developmental improvement since V5 lived in a separate opt-in sidecar and
a runner chose which ones to stack. ``verdant_organism`` folds the parts that earned their place
into one organism, with every part individually switchable and its evidence recorded beside it.
Nothing under the other ``verdant_*`` packages is modified: the stock heartbeat
(``VerdantDevelopmentPipeline``) and every pinned file stay exactly as they were, so old results
reproduce and the preregistered math line is untouched.

    from verdant_organism import Organism, Parts
    organism = Organism(Parts())              # the default organism (every validated part)
    kernel = organism.new_kernel(seed=2301, state_dim=128)
    for command in lessons:
        organism.advance(kernel, command)

Parts and their evidence (docs named in each line). "default" = on unless switched off.

  heartbeat (default)
    recurrence       structures count recurrence from experience itself   REHEARSAL_SIDECAR_V0
    bond_clock       a bond fades by how often it was really met             BOND_CLOCK_IN_ENGINE_DESIGN_V0
    surprise         the organism's own prediction error drives binding      SURPRISE_SIDECAR_V0
    reunion          familiar-but-forgotten is consulted with surprise       SURPRISE_SIDECAR_V0
    sleep            rehearsal of fading, really-met bonds                    REHEARSAL_SIDECAR_V0
    horizon in experiences (76): memory spans cannot be eaten by bookkeeping MEMORY_SPANS_AND_QUESTION_SLEEP_V0
  self-direction (default)
    council_ready    the Council sits when something is ready                SELF_CONVENING_COUNCIL_V0
    heat_revision    stale folds heat, are challenged and revised (M18 + Council, departure-aware,
                     never while in mind, no twins)                           LOCAL_HEAT_AND_REVISION_V0
    question_sleep   stored questions whose only gap is weak bonds choose what sleep practises
                                                                             OPEN_QUESTIONS_SHADOW_V0, MEMORY_SPANS_AND_QUESTION_SLEEP_V0
  watching (default, read-only, proved fingerprint-neutral)
    gear_watch       temperature against its own Tg, hot / cruise             LOCAL_HEAT_AND_REVISION_V0
  speed (default, byte-exact)
    acceleration     long-life accelerators, identical fingerprints           LONG_LIFE_ACCELERATION_V0
  senses and meaning (default since the four-life test in ORGANISM_V0)
    senses           ringing + adaptation, binding by moment, reminding, measured attention, signed
                     (quarter-turn) conflict                                  SENSES_READINESS_V0, ETHOMORPHIC_FIELD_ROADMAP_V0
    fine_ear         48-band ear inside the sensory pipeline                  SENSES_READINESS_V0
    reader           words seen separately                                    SENSES_READINESS_V0
    wave_fold        the wave's phase given a job, and folding at any depth   RECURSIVE_FOLD_V0
    profiles         two-speed (recent beside lifelong) concept profiles      STANCE_AND_UNKNOWN_V0
    stance           what the field was told about a proposition, and tension STANCE_AND_UNKNOWN_V0
  kept out, with reasons
    carry-everything   bound neighbouring lessons into 5 wrong structures (SENSES_READINESS_V0)
    gear sleep control no better than the organism's own forgetting span, which the clock already
                       is (LOCAL_HEAT_AND_REVISION_V0); the gear stays a measurement
    motor              removed by decision; returns only under FUTURE_MOTOR_IMPLEMENTATION_DESIGN
    obligation authority beyond the developmental bridge: William's firewall stands

Read-only capabilities that belong to the organism and change nothing: ``sidecar_recall``
(recall, relive, imagine), ``sidecar_looks``, ``sidecar_recognize``, ``sidecar_inquiry``'s
substrate detectors. They are exposed as methods so a caller never has to know they are sidecars.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

ORGANISM_REVISION = "verdant_organism_v0"


@dataclass(frozen=True)
class Parts:
    # heartbeat
    recurrence: bool = True
    bond_clock: bool = True
    surprise: bool = True
    reunion: bool = True
    sleep: bool = True
    horizon_experiences: int | None = 76
    # self-direction
    council: str | None = "ready"          # "ready" | "steady" | "clock" | None (caller promotes)
    council_limit: int = 4
    heat: str | None = "revise"             # "revise" | "watch" | None
    question_sleep: bool = True
    # watching
    gear: str | None = "watch"              # "watch" | None   ("drive" exists for experiments only)
    # speed
    acceleration: bool = True
    # senses and meaning (validated on four full lives with everything else, ORGANISM_V0)
    senses: bool = True
    fine_ear: bool = True
    reader: bool = True
    wave_fold: bool = True
    profiles: bool = True
    stance: bool = True

    def lean(self) -> "Parts":
        """Without the process-global senses / wave / profiles / stance / reader / ear patches."""
        return Parts(**{**asdict(self), "senses": False, "fine_ear": False, "reader": False, "wave_fold": False,
                        "profiles": False, "stance": False})

    def everything(self) -> "Parts":
        return Parts(**{**asdict(self), "senses": True, "fine_ear": True, "reader": True, "wave_fold": True,
                        "profiles": True, "stance": True})


_INSTALLED: dict = {}


def _install_globals(parts: Parts) -> None:
    """Global installers (they wrap kernel/pipeline methods). Idempotent; conflicting re-installs refused."""
    key = (parts.acceleration, parts.senses, parts.fine_ear, parts.reader, parts.wave_fold, parts.profiles, parts.stance)
    if _INSTALLED.get("key") not in (None, key):
        raise RuntimeError("A different organism configuration is already installed in this process.")
    if _INSTALLED.get("key") == key:
        return
    if parts.wave_fold:
        from sidecar_wave import install_wave
        install_wave()
    if parts.profiles:
        from sidecar_profiles import install_profiles
        install_profiles()
    if parts.stance:
        from sidecar_stance import install_stance
        install_stance()
    if parts.senses:
        import sidecar_ring as ring
        ring.install_ring(adapt=True, signed="quarter")
        ring.install_inferred_association(); ring.install_attention(); ring.install_moment_carry()
    if parts.fine_ear:
        from sidecar_ear import install_fine_ear
        install_fine_ear()
    if parts.reader:
        from sidecar_reader import install_reader
        install_reader()
    if parts.acceleration:
        from sidecar_acceleration import install_long_life_acceleration
        install_long_life_acceleration()
    _INSTALLED["key"] = key


class Organism:
    """A Verdant life: the heartbeat, its self-direction, and its read-only capabilities."""

    def __init__(self, parts: Parts | None = None):
        self.parts = parts = parts or Parts()
        _install_globals(parts)
        from verdant_structures import VerdantStructurePipeline
        stages: dict = {}
        self.structures = VerdantStructurePipeline()
        if parts.recurrence:
            from sidecar_recurrence import ExperienceRecurrenceStructurePipeline
            self.structures = ExperienceRecurrenceStructurePipeline(); stages["structures"] = self.structures
        plasticity_base = None
        if parts.bond_clock:
            from sidecar_bond_clock import BondClockPlasticityPipeline
            plasticity_base = BondClockPlasticityPipeline
        if parts.surprise:
            from sidecar_surprise import SurpriseDevelopmentPipeline, surprise_plasticity
            from verdant_plasticity import VerdantPlasticityPipeline
            plasticity = surprise_plasticity(plasticity_base or VerdantPlasticityPipeline, reunion=parts.reunion)
            if parts.wave_fold:
                from sidecar_fold import FoldingDevelopmentPipeline, folding_plasticity
                stages["plasticity"] = folding_plasticity(plasticity)()
                beat = FoldingDevelopmentPipeline(**stages)
            else:
                stages["plasticity"] = plasticity()
                beat = SurpriseDevelopmentPipeline(**stages)
        else:
            from verdant_development import VerdantDevelopmentPipeline
            if plasticity_base is not None:
                stages["plasticity"] = plasticity_base()
            beat = VerdantDevelopmentPipeline(**stages)
        if parts.sleep:
            from sidecar_rehearsal import RehearsalConfig, RehearsingDevelopmentPipeline
            beat = RehearsingDevelopmentPipeline(beat, RehearsalConfig(min_real_exposures=1,
                                                                       horizon_experiences=parts.horizon_experiences))
        if parts.gear:
            from sidecar_gear import GearPipeline
            beat = GearPipeline(beat, mode=parts.gear)
        if parts.council:
            from sidecar_council import ConveningDevelopmentPipeline
            beat = ConveningDevelopmentPipeline(beat, self.structures, mode=parts.council, limit=parts.council_limit,
                                                reify=parts.wave_fold)
        if parts.heat:
            from sidecar_heat import HeatDevelopmentPipeline
            beat = HeatDevelopmentPipeline(beat, mode=parts.heat)
        if parts.question_sleep:
            if not parts.sleep:
                raise ValueError("question_sleep needs sleep")
            from sidecar_inquiry import InquiringDevelopmentPipeline
            beat = InquiringDevelopmentPipeline(beat, authority="sleep")
        self.pipeline = beat

    # -- the life -----------------------------------------------------------------------
    @staticmethod
    def new_kernel(*, seed: int, state_dim: int, run_label: str = "verdant-organism"):
        from verdant_kernel import VerdantKernel
        return VerdantKernel(seed=seed, state_dim=state_dim, run_label=run_label)

    def advance(self, kernel, command):
        return self.pipeline.advance(kernel, command)

    def layer(self, name: str):
        """The named layer of the heartbeat (e.g. 'ConveningDevelopmentPipeline'), or None."""
        node = self.pipeline
        while node is not None:
            if type(node).__name__ == name:
                return node
            node = getattr(node, "__dict__", {}).get("inner")
        return None

    def report(self) -> dict:
        out: dict = {"revision": ORGANISM_REVISION, "parts": asdict(self.parts)}
        council = self.layer("ConveningDevelopmentPipeline")
        if council is not None:
            lags = council.log.lags()
            out["council"] = {"sittings": council.log.sittings, "promoted": len(lags), "refusals": council.log.refusals[-3:]}
        heat = self.layer("HeatDevelopmentPipeline")
        if heat is not None:
            out["heat"] = {"challenges": len(heat.heat_log.challenges), "refolds": [list(x[:3]) for x in heat.heat_log.refolds],
                           "refusals": heat.heat_log.refusals[-3:]}
        gear = self.layer("GearPipeline")
        if gear is not None:
            out["gear"] = gear.summary()
        inquiry = self.layer("InquiringDevelopmentPipeline")
        if inquiry is not None:
            out["questions"] = inquiry.shadow.summary()
        sleep = self.layer("RehearsingDevelopmentPipeline")
        if sleep is not None:
            out["sleep_beats_committed"] = sum(r.committed for r in sleep.reports)
        return out

    # -- read-only capabilities (change nothing) --------------------------------------------
    @staticmethod
    def imagine(kernel, *args, **kwargs):
        from sidecar_recall import imagine
        return imagine(kernel, *args, **kwargs)

    @staticmethod
    def recognise(kernel, features, modality: str, **kwargs):
        from sidecar_recognize import read_wave
        return read_wave(kernel, features, modality, **kwargs)

    def open_questions(self) -> dict:
        inquiry = self.layer("InquiringDevelopmentPipeline")
        return {} if inquiry is None else dict(inquiry.shadow.questions)


__all__ = ["ORGANISM_REVISION", "Organism", "Parts"]
