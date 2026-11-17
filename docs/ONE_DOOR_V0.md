# One door v0: lessons and sight through the same heartbeat (observer, seed 2301)

`run_observer_one_door.py`. Eye: synthetic 8-frame videos of a moving shape through the ordinary
media gateway and perception pipeline; only the tracked region's appearance numbers are kept.
Mind: one kernel. 8 made-up words each belong to a 3-word family taught by 5 text lessons; each
word is also the name given to one shape on 3 video episodes ("a parent pointing"). 64 lessons.
Seeing: 5 new episodes per shape (new path, size +-15%, brightness, noise) as numbers only, read
through `inspect_resonance` and then `VerdantCompilationPipeline.inspect`. 24 concepts, chance 4.2%.

| mind | named from sight | whole family recalled from sight | P promoted |
|---|---|---|---|
| stock, raw eye numbers | 25% (profile term alone: 75%) | 25% | 0 |
| stock + adaptation | 75% (profile alone: 90%) | 57.5% | 0 |
| wave, raw eye numbers | 10% | 22.5% | 0 |
| wave + adaptation + recurrence + bond clock | 90% | 90% | 8 |
Eye-only baseline (nearest average appearance of the named episodes): 100% in every arm.

Adaptation = each sight described relative to the mean and spread of the named episodes only.
Without it the wave scoring is worse than stock: the best match stands only 1.75 SD above the
crowd, under the 2 SD the wave rule asks for, so recognition scores zero.

NOT WORKING: telling a never-shown shape from a known one. Never-shown shapes stood out MORE
(3.41 SD vs 2.92 with adaptation; told apart 30-60%). The mind names them as something it knows.

Limits: 8 clean shapes on black, synthetic video, one seed. The eye alone matches better than
the mind does; what the mind adds is the name and everything attached to it.

## Follow-up (Opus, 2026-11-17): the unknown on sight, and a correction
"Leftover" = share of a sight's field effect the known concepts' resonance profiles cannot
explain (least-squares projection; `run_observer_unknown_residual.unknown_share`). Read-only.
Separation = share of (known sight, never-shown sight) pairs where the never-shown one is more unknown.

| run | named from sight | stand-out separation | leftover separation (all known) | leftover known / never-shown |
|---|---|---|---|---|
| seed 2301, adapted | 75% | 0.23 | 0.975 | 0.10 / 0.72 |
| seed 7, adapted | 47% | 0.95 | 0.953 | 0.08 / 0.85 |
| seed 99, adapted | 53% | 0.96 | 1.000 | 0.05 / 0.76 |
| seed 2301, raw eye numbers | 25% | 0.88 | 0.917 | 0.01 / 0.04 |

The leftover detects never-shown shapes on every seed; the stand-out measure does not.
CORRECTION: naming from sight with the stock mind + adaptation is 47-75% across seeds, not 75%;
the 90% reported for the stacked mind was measured on seed 2301 only and is likely also seed-favoured.
Still 2 never-shown shapes (10 sights) per seed.
