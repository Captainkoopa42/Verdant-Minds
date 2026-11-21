"""The Council convenes itself (wiring plan step 1).

Claim boundary: IMPLEMENTED-EXPERIMENTAL. Nothing in ``verdant_*`` is modified and nothing
here runs unless a caller wraps a pipeline with :class:`ConveningDevelopmentPipeline`.

Before this, promotion of an earned structure happened because a runner said so: "every 20
lessons, up to 4 eligible candidates go to the Council". The organism's own state played no
part in *when*. Here the trigger is the organism's state:

    clock   the old rule, kept byte-for-byte so it can be compared (every N experiences)
    ready   after every real experience, the Council convenes if, and only if, a candidate
            the structure stage itself marked ELIGIBLE is waiting. Up to ``limit`` per sitting,
            in candidate-id order, through the ordinary ``promote`` (inspection, Council
            proposal, Council decision, kernel commit). Nothing about the gates changes.
    steady  like ready, but a candidate goes forward only once it has been seen eligible at
            two consecutive sittings-checks (the Council waits for the readiness to hold).

The trigger is a pure function of canonical state (plus, for ``steady``, the previous check,
which is itself a function of canonical state at the previous experience), so two runs of the
same lessons convene at the same points and end on the same fingerprint.

``log`` is a diagnostic record, outside canonical state: for each promoted candidate, the
experience at which it was first seen eligible and the experience at which it was promoted.
"""
from __future__ import annotations

from dataclasses import dataclass, field

MODES = ("clock", "ready", "steady")


@dataclass
class ConveningLog:
    first_eligible: dict = field(default_factory=dict)   # candidate_id -> experience number
    promoted_at: dict = field(default_factory=dict)      # candidate_id -> experience number
    sittings: int = 0
    refusals: list = field(default_factory=list)

    def lags(self) -> list[int]:
        return [self.promoted_at[c] - self.first_eligible.get(c, self.promoted_at[c]) for c in sorted(self.promoted_at)]


def eligible_waiting(kernel) -> list[str]:
    return [cid for cid, c in sorted(kernel.state.structure_candidates.items()) if c.status.value == "eligible"]


class ConveningDevelopmentPipeline:
    """Drop-in for ``.advance``: the inner pipeline beats, then the Council may convene."""

    def __init__(self, inner, structures, *, mode: str = "ready", limit: int = 4, every: int = 20,
                 reify: bool = False):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.inner, self.structures, self.mode, self.limit, self.every, self.reify = inner, structures, mode, limit, every, reify
        self.log = ConveningLog(); self._seen_last: set[str] = set(); self.promoted_last = 0

    def __getattr__(self, name):                       # reports, surprise_log, ... of the wrapped pipeline
        return getattr(self.inner, name)

    def _promote(self, kernel, candidate_id: str) -> None:
        if self.reify:
            from sidecar_fold import promote_and_reify
            promote_and_reify(kernel, self.structures, candidate_id)
        else:
            self.structures.promote(kernel, candidate_id)

    def advance(self, kernel, command):
        result = self.inner.advance(kernel, command)
        self.promoted_last = 0
        if getattr(result, "replayed", False):
            return result
        n = len(kernel.state.processed_event_keys)
        waiting = eligible_waiting(kernel)
        for cid in waiting:
            self.log.first_eligible.setdefault(cid, n)
        if self.mode == "clock":
            go = waiting if n % self.every == 0 else []
        elif self.mode == "ready":
            go = waiting
        else:
            go = [c for c in waiting if c in self._seen_last]
        self._seen_last = set(waiting)
        gear = self.inner
        if go and self.mode != "clock" and type(gear).__name__ == "GearPipeline" and gear.mode == "drive" and gear.hot:
            gear.gear_log.holds += 1; go = []             # the gear is hot: change is under way, commit when it settles
        if go:
            self.log.sittings += 1
        for cid in go:
            if self.promoted_last >= self.limit:
                break
            try:
                self._promote(kernel, cid); self.promoted_last += 1; self.log.promoted_at[cid] = n
            except Exception as exc:                    # reported, never hidden
                self.log.refusals.append(f"{n}: {type(exc).__name__}: {str(exc)[:80]}")
        return result
