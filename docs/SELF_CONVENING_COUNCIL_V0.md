# The Council convenes itself v0 (wiring plan step 1)

Status: PREREGISTERED 2026-11-20, before any run. Results appended below, never edited above.

## Question
Promotion has always happened on a runner's clock (every 20 lessons, up to 4 eligible
candidates). Can the organism's own state decide when the Council sits, without losing what
the clock achieved?

## Arms (same 406-lesson life, seed 9001, kernel seed 2301, `reunion` arm, accelerated)
* `clock`  - `sidecar_council` in clock mode. Must reproduce the old run's final fingerprint
  `1abd88f7...` exactly (proves the wrapper changes nothing by itself).
* `ready`  - the Council sits after any experience at which an eligible candidate is waiting.
* `steady` - as ready, but a candidate must be eligible at two consecutive experiences.

## Gates (each arm, final checkpoint)
1. kept >= 145/148 and promoted >= 43/46 on the passing groups;
2. wrong promotions = 0 (no promotion of a family that fails a stated gate);
3. replay: running the arm twice gives the same fingerprint (checked on `ready`).

## Predictions
* `clock` reproduces `1abd88f7...`.
* `ready` and `steady` pass the gates. Mean lag from first eligibility to promotion drops
  from about 10 experiences (clock) to 0 (`ready`) and 1 (`steady`).
* Risk named in advance: eligibility is re-judged at every observation, and the clock's wait
  may have been hiding candidates that are eligible only briefly. If `ready` promotes a wrong
  family, that is the reason, and `steady` is the remedy to test.

## Results, life 9001 (appended 2026-11-20)

| arm | kept | promoted | wrong | sittings | lag mean / max (experiences) | final fingerprint |
|---|---|---|---|---|---|---|
| old runner clock (reference) | 145/148 | 43/46 | 0 | - | - | `1abd88f7...` |
| `clock` | 145/148 | 43/46 | 0 | 18 | 10.2 / 39 | `1abd88f7...` (identical) |
| `ready` | 145/148 | 43/46 | 0 | 43 | 0 / 0 | `b164fe51...` |
| `steady` | **148/148** | **44/46** | 0 | 44 | 1 / 1 | `766ddd20...` |

All three pass the gates; `clock` reproduces the reference exactly, as predicted; the lags are
as predicted. Not predicted: `steady` keeps all 148 cues and promotes one more spaced-long
family. `steady` gives each candidate *fewer* chances than `ready` (two consecutive eligible
checks instead of one), so this cannot be "more promotion opportunities"; promotion timing
changes the later trajectory (a promoted structure enters the workspace as an operand), and
on this life that change happened to favour one family. One life cannot tell a mechanism from
luck.

## Addendum, preregistered before running: a second life (seed 4242)
Reference on that life (old runner clock): kept 148/148, promoted 45/46, wrong 0.
Prediction: `ready` and `steady` both pass (kept >= 148, promoted >= 45, wrong 0). If `steady`
is better than `ready` again, that is a pattern worth a third life; if not, the 9001 gain is
recorded as trajectory luck and `ready` vs `steady` is decided on simplicity.

## Results, life 4242 (appended)

| arm | kept | promoted | wrong | sittings | lag mean / max | final fingerprint |
|---|---|---|---|---|---|---|
| old runner clock (reference) | 148/148 | 45/46 | 0 | - | - | - |
| `ready` | 148/148 | **46/46** | 0 | 46 | 0 / 0 | `0f76a341...` |
| `steady` | 148/148 | **46/46** | 0 | 46 | 1 / 1 | `253dc05a...` |

Both pass; both promote one family more than the clock did. `steady` is not better than
`ready` here, so the 9001 difference between them is recorded as trajectory luck, not a
mechanism. Across the two lives, self-convening is never worse than the clock and is better by
one family in three of four comparisons. Decision: `ready` (simplest: the Council sits exactly
when something is waiting), with `steady` kept as an option.
