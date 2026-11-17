# Surprise sidecar v0 (opt-in, IMPLEMENTED-EXPERIMENTAL, 3 tests)

`sidecar_surprise`: before an experience is applied, ask the organism's own read-only resonance
which concepts the features call up; surprise = share of the experience's concepts it did not
predict. That number replaces the constant 0.15 `prediction_error` on the current-evidence item,
and binding activation becomes floor + (1 - floor) * surprise (never below the stock floor).

## OBSERVED: 406-lesson life (seed 9001), measured surprise by exposure number
| kind | 1st | 2nd | 3rd | 4th | 5th | later |
|---|---|---|---|---|---|---|
| massed | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | |
| short gaps (6-14 lessons) | 1.00 | 0.07 | 0.07 | 0.00 | 0.00 | |
| long gaps (30-90 lessons) | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 | |
| returning after 250+ lessons of silence | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 (first after the silence) | 0.00 |
| one-off | 1.00 | | | | | |
| distractor pairs (concepts reused at random) | 0.57 | | | | | |
Recognition from features is complete after one exposure and did not fade over any gap in this
life. Bonds, by contrast, need repeated exposure and decay between them.

## Outcomes, same life (46 families meet every stated gate)
| arm | promoted | long gaps | cues recalled exactly | wrong promotions |
|---|---|---|---|---|
| three sidecars (`full`) | 32/46 | 2/15 | 112/148 | 0 |
| + surprise | 34/46 | 3/15 | 123/148 | 0 |
| + surprise + wave | 33/46 | 2/15 | 123/148 | 0 |

Caveat: these lessons reuse the same generated tokens, so the features of two lessons about one
family are nearly identical. Recognition this clean is a property of the material as much as of
the organism; real sensory input will not give 0 and 1. One life seed, one kernel seed.

## Follow-up: reunion (the two memories consulted together)
`surprise_plasticity(base, reunion=True)`: reunion = familiarity (1 - surprise, from the field)
x forgetting (how far the bonds among what is now held fall short of the cohesion gate's
strength); activation = floor + (1 - floor) * max(surprise, reunion).

OBSERVED, same 406-lesson life (seed 9001), 46 families meeting every stated gate:
| arm | promoted | short gaps | long gaps (30-90) | returning | cues recalled | wrong |
|---|---|---|---|---|---|---|
| stock | 9 | 1/15 | 0/15 | 0/5 | 42/148 | 0 |
| three sidecars | 32 | 14/15 | 2/15 | 5/5 | 112/148 | 0 |
| + surprise | 34 | 15/15 | 3/15 | 5/5 | 123/148 | 0 |
| + reunion | 37 | 15/15 | 6/15 | 5/5 | 129/148 | 0 |
Under-exposed 0/14, single-context 0/6, one-off 0/28 promoted in every arm.
Long-life runner arms: `reunion` (above) and `whole` (reunion + wave + generic folding; smoke-tested
to lesson 80 only). One life seed, one kernel seed.
