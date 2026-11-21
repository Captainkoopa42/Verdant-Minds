"""The gear: global temperature against a drifting Tg (Tg for V5, part 2).

Claim boundary: IMPLEMENTED-EXPERIMENTAL. Nothing in ``verdant_*`` is modified. ``watch``
records only. ``drive`` replaces the clock-driven sleep trigger and lets the Council hold
promotions while the organism is hot; it is for forked organisms until William decides.

Temperature, in the physical sense: the mean motion of the parts. Here the parts are bonds:

    T = total strengthening of bonds by this experience (new bonds count their whole strength;
        fading is background, not motion)

Familiar input barely moves saturated bonds; new or contradicting input moves many.

Tg is the organism's own usual T, and it forgets at the organism's own forgetting rate:

    r      = 1 - (1 - plasticity decay_rate) ** (cycles this experience took)
    Tg    <- Tg + r (T - Tg)            spread <- spread + r (|T - Tg| - spread)

Phase, with hysteresis in the organism's own units: HOT when T > Tg + spread; back to
CRUISE when T < Tg. No other number.

``drive`` (fork only):
* sleep is not counted in experiences. The organism's own memory span is set by its bond decay:
  each experience forgets a fraction r = 1 - (1 - decay_rate) ** cycles of what it holds, hot
  or not (forgetting does not pause when the mind is busy). When the accumulated forgetting
  reaches one whole span (sum r >= 1) sleep is due; it is taken at the first CRUISING moment,
  so a busy, changing stretch postpones sleep until it settles but never cancels it. On this
  organism r ~ 0.12 per experience, a span of about 8.4 experiences: the clock's "every 8" was
  the organism's own forgetting span all along, without knowing it.
* the Council holds promotions while HOT (change is under way; commit when it settles).

Rules rejected on the way (kept as record):
  - "sleep after every hot spell": 106 sleeps vs the clock's 68 (4242 watch trace, before any run);
  - "sleep when debt exceeds the usual debt at sleep": ratchets upward (trace, before any run);
  - "loss exceeds gain since the last sleep": never drains; learning out-adds fading (341 vs 268);
  - "span always, reset to zero at sleep": 57 sleeps on both lives; forgetting accumulated past one
    span during a postponement was discarded at the reset; 4242 kept 130 vs 141, promoted 37 vs 40;
  - "count forgetting only while cruising": 44 / 46 sleeps vs 68; promoted held, but kept cues
    fell on both lives (9001 124 vs 130, 4242 134 vs 141), nearly all spaced_long;
  - "recent loss exceeds recent gain": live 9001 run slept 203 times, because sleep's own
    strengthening was not counted as gain; with it counted, 5 sleeps by lesson 400 and retention
    fell (9001 78/85 kept vs 85/85). Comparing gain with loss does not capture what sleep is for.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field


@dataclass
class GearLog:
    rows: list = field(default_factory=list)       # (experience, T, Tg, spread, phase, slept)
    sleeps: list = field(default_factory=list)      # (experience, reason, committed)
    holds: int = 0


class GearPipeline:
    def __init__(self, inner, mode: str = "watch"):
        if mode not in ("watch", "drive"):
            raise ValueError("mode must be 'watch' or 'drive'")
        self.inner, self.mode = inner, mode
        self.gear_log = GearLog()
        self.tg = None; self.spread = 0.0; self.hot = False; self.gain = None; self.loss = None; self.span = 0.0
        if mode == "drive":
            if not hasattr(inner, "rehearsal"):
                raise ValueError("drive needs a rehearsing pipeline directly inside")
            cfg = inner.rehearsal.config
            inner.rehearsal.config = dataclasses.replace(cfg, every_experiences=10 ** 9)   # the count no longer decides

    def __getattr__(self, name):
        return getattr(self.inner, name)

    @staticmethod
    def _strengths(kernel) -> dict:
        return {k: v.strength for k, v in kernel.state.plasticity_associations.items()}

    def advance(self, kernel, command):
        before = self._strengths(kernel); cycle0 = kernel.state.cycle
        result = self.inner.advance(kernel, command)
        if getattr(result, "replayed", False):
            return result
        after = self._strengths(kernel)
        t = sum(max(0.0, v - before.get(k, 0.0)) for k, v in after.items())
        loss = sum(max(0.0, v - after.get(k, 0.0)) for k, v in before.items())
        cycles = max(1, kernel.state.cycle - cycle0)
        r = 1.0 - (1.0 - kernel.state.plasticity_policy.decay_rate) ** cycles
        if self.tg is None:
            self.tg = t; self.spread = 0.0
        if not self.hot and t > self.tg + self.spread:
            self.hot = True
        elif self.hot and t < self.tg:
            self.hot = False
        self.tg += r * (t - self.tg); self.spread += r * (abs(t - self.tg) - self.spread)
        self.gain = t if self.gain is None else self.gain + r * (t - self.gain)
        self.loss = loss if self.loss is None else self.loss + r * (loss - self.loss)
        n = len(kernel.state.processed_event_keys); slept = None
        reports = getattr(self.inner, "reports", None)
        self.span += r
        if self.mode == "drive" and not self.hot and self.span >= 1.0:
            slept = "span"
            report = self.inner.rehearsal.run(kernel)
            reports.append(report)
            self.gear_log.sleeps.append((n, slept, report.committed))
            self.span -= 1.0                          # carry what was forgotten beyond one span; never discard it
        self.gear_log.rows.append((n, round(t, 4), round(self.tg, 4), round(self.spread, 4), "hot" if self.hot else "cruise", slept,
                                   round(loss, 4), round(self.gain - self.loss, 4)))   # (..., loss, recent gain - recent loss)
        return result

    def summary(self) -> dict:
        rows = self.gear_log.rows
        hot = sum(1 for r in rows if r[4] == "hot")
        spells = sum(1 for a, b in zip(rows, rows[1:]) if a[4] == "cruise" and b[4] == "hot")
        return {"experiences": len(rows), "hot_share": round(hot / max(1, len(rows)), 3), "hot_spells": spells,
                "tg_now": rows[-1][2] if rows else None, "spread_now": rows[-1][3] if rows else None,
                "sleeps": len(self.gear_log.sleeps), "sleep_reasons": _count(s[1] for s in self.gear_log.sleeps),
                "sleeps_committed": sum(1 for s in self.gear_log.sleeps if s[2]), "council_holds": self.gear_log.holds}


def _count(items) -> dict:
    out: dict = {}
    for i in items:
        out[i] = out.get(i, 0) + 1
    return out
