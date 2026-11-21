# Local heat and revision v0 (Tg for V5, part 1)

Status: PREREGISTERED 2026-11-20 before the full runs; a 220-lesson smoke run was used only to
check the plumbing and is reported below as such. Results are appended, never edited above.

## Lineage, and what is different this time
verdant-intelligence: each thought's temperature = disagreement among its neighbours
(variance/mean); hot thoughts soften and can be reshaped. July 2025: Tg from the system's own
state, moved by experience. V5x: the V4 law's inputs were stand-ins (word counts) and it
measured wordiness. Here: `temperature(P) = variance / mean of P's current internal bond
strengths`, read from the organism's own bonds; `drift(m)` locates which member the rest are
leaving. No counter, no window, no threshold.

## The practice lives (`curriculum_packs/generate_long_life_pack_v1.py`)
v0 plus a world that changes: `reversed` (4 members, one replaced after a pause), `reversed3`
(3 members; Milestone 18 cannot revise below 3, so UNRESOLVED is the honest outcome),
controls `intermittent` (later sightings alternate whole / one member missing, no
replacement) and `stable_late` (unchanged). 549 lessons, seeds 9001 and 4242.

## Smoke run (plumbing only, 220 lessons): what it exposed
* Heat sat exactly on the departed member (drift ~0.5, every other member 0, controls 0).
* Stock Milestone 18 turned the mature challenges into UNRESOLVED: removing every edge of the
  departed member leaves it alone, which stock M18 reads as an undersized split fragment. As
  built, M18 can cut edges but cannot let a member leave. The kernel's integrity checks do not
  forbid it, so `sidecar_heat.departure_aware_refolding` adds one reading: a lone member with
  every edge challenged has DEPARTED; if exactly one viable component remains (M18's own
  minimums) the outcome is REVISE, built, Council-authorised and lineage-kept exactly as M18's.
* The changing world also produced a wrong promotion under the stock structure stage: a 5-member
  fold of old + new members that never occurred together (candidates are formed from the bond
  neighbourhood). Recorded as found.

## Arms (each life; `reunion`, Council `ready`)
* `plain` (9001 only): no heat. `watch`: heat recorded, nothing written. Must end on `plain`'s
  fingerprint.
* `revise` (fork): heat challenges stale folds; departure-aware M18 + Council.

## Detector gates (from `watch`)
D1 at each late family's last lesson, AUC(reversed + reversed3 vs all controls: intermittent,
   stable_late and ordinary promoted families at their own last lesson) >= 0.9 on each life;
D2 at the change lesson (before the world changes) the same AUC <= 0.75 (no generator artefact);
D3 median heat: intermittent < reversed.

## Revision gates (from `revise`)
R1 every 4-member reversed family promoted before its change is revised to its remaining
   members by the end of its family's life (or the end of the life);
R2 no control family (intermittent, stable_late, ordinary) is revised or ablated;
R3 wrong promotions do not increase vs `watch`; kept and promoted on the passing groups do not drop;
R4 reversed3: UNRESOLVED recorded, parent kept (honest limit, not a failure).
If R1 fails, the reason is found and another Verdant-shaped route tried; if R2 fails, heat is
not a safe trigger as built.

## Results, life 9001, first pair (appended)

Detector (`watch`): D1 AUC 1.0 (reversed + reversed3, n=7, vs 43 controls). D3 met: median
heat at the end of a family's life: reversed 0.073, reversed3 0.084, intermittent 0.011,
stable_late 0.000, ordinary 0.000. D2 read 1.0, but **my scoring was wrong**: the "at change"
reading included the change lesson itself (the first contradicting sighting). Fixed to
strictly-before; D2 is re-measured on the next runs, not excused.

Revision (`revise`, fork; this run predates two fixes listed below):
* R1 met: 5/5 four-member reversals revised to their remaining members through the Council.
* R2 met: no control family revised or ablated.
* R4 met: both reversed3 parents UNRESOLVED, kept.
* Also revised, all correctly: the 5 wrong merged folds (old + new members that never occurred
  together) were revised to the changed family; active wrong structures at the end: 0
  (watch: 5). The historic "wrong" count stays 5 because retired parents are kept.
* R3 mixed: active wrong down 5 -> 0, but spaced_long promoted 6 -> 4 and kept 38 -> 32. No
  revision touched a spaced_long family, so this is an indirect trajectory effect; one
  candidate cause is the 5 duplicate structures the merged-fold revisions created.

Fixes found on the way, each a property of the existing system exposed by a changing world:
1. Stock M18 cannot let a member leave (lone member = undersized fragment = UNRESOLVED).
   Departure-aware reading added in the sidecar.
2. Committing a refold while the parent is active in the workspace leaves the kernel in a
   state it refuses ("Ablated structure remains active in workspace"): neither M18 nor M15
   ablation checks the workspace. Revision now waits until the fold is not in mind.
3. Revising a merged fold recreated an existing structure (twins). Now, when the revision
   already exists, the stale fold is retired through the availability switch (reason and
   challenge ids recorded) and no twin is made.

## Results, life 4242 (appended; departure-aware, workspace-wait and no-twin fixes in place)

| | D1 AUC at end | D2 AUC before change | median heat rev / intermittent | revised correctly | controls revised | active wrong | twins |
|---|---|---|---|---|---|---|---|
| watch | 1.0 | 0.38 | 0.057 / 0.004 | - | - | 7 | 0 |
| revise | 1.0 | 0.41 | 0.050 / 0.004 | **5/5** | **0** | **0** | 0 |

Passing groups, watch -> revise: spaced_long promoted 8 -> 9, kept 41 -> 43; everything else
equal. reversed3: UNRESOLVED, parents kept (R4). All detector and revision gates met on 4242.

# The gear (Tg for V5, part 2): PREREGISTERED before any drive run

`sidecar_gear`: T = total bond strengthening per experience; Tg and spread = the organism's
own running norm, forgetting at its own plasticity decay rate; HOT when T > Tg + spread, back
to CRUISE when T < Tg. Watch traces (4242): first meetings run hot (4-member firsts 1.58,
3-member 0.79), familiar repeats cool (0.1-0.4), changed sightings warmer than repeats
(0.52, hot 33% vs 5-20%). Hot share 20%.

Drive (fork only): sleep while cruising when, since the last sleep, bond strength lost to
fading exceeds strength gained by learning; Council holds promotions while hot. Two rules
were rejected on the trace before any drive run (see the module docstring).

Arms: `drive` = Council ready + heat revise + gear drive, on the two changing lives and the
two old lives (no reversals).
G1 no harm: kept and promoted on the passing groups >= the same life without the gear
   (changing: the `revise` runs; old: Council-ready references 145/148, 43/46 and 148/148,
   46/46); active wrong structures 0.
G2 the gear follows the world: drain sleeps fall in quieter stretches (median T of the
   experience that triggered sleep < median T overall); sleep count is reported against the
   clock's (68 on changing lives, 50 on old lives).
G3 on the old lives heat-revision must find nothing to revise (no reversals exist); any refold
   there is examined as a possible false alarm.

## Results, life 9001 second pair (appended; all fixes in place)
* Read-only, proved: `watch` with and without the gear watcher end on the same fingerprint
  `2fb42f5c...`.
* D2 re-measured with the corrected scoring: 0.41 (passes). D1 1.0, D3 met. **All detector gates
  met on both lives.**
* `revise` (with no-twin, and with mature challenges no longer re-recorded): 5/5 revised,
  0 controls touched, active wrong 0 (watch 5), 0 twins. spaced_long again 6 -> 4.
* Why spaced_long moves: every spaced_long family the arms disagree on fails one gate only,
  internal cohesion, at 0.33-0.38 against 0.38, and the arms differ by 0.01-0.02. No revision
  touches these families. It is a knife edge (9001: -2 under revision; 4242: +1), the same weak
  -bond gap that "stored questions direct sleep" closed in the earlier fork.
* Cost found: each recorded challenge advances the kernel's cycle (142 challenges), and some of
  Verdant's memory is clocked in cycles (sleep's horizon, 400 cycles). Most challenges are
  first sightings, including low-confidence ones on intermittent controls that never mature.
  Recorded as a coupling to remove: horizons should be in the organism's own experience, not
  in kernel cycles.

## Gear drive, first live run (9001), and the rule change it forced
203 sleeps against the clock's 68; kept 130/148, promoted 36/46 (revise-only: 130, 35).
The pattern was lifelike: no sleep in the first 150 lessons (a growing mind), then rising as
input became familiar; sleep fell on quiet experiences (median T 0.26 asleep vs 0.54 awake).
The excess was a bookkeeping error: strength added by sleep was not counted as gain, but its
later fading was counted as loss, so each sleep set up the next. Fixed (sleep's strengthening
counts as gain); re-run on both changing lives.

## Gear drive: the sleep rule, tried and replaced on the evidence
| rule | where judged | sleeps | outcome |
|---|---|---|---|
| sleep after every hot spell | 4242 trace | 106 | rejected before running |
| debt > usual debt at sleep | 4242 trace | ratchets | rejected before running |
| loss > gain since last sleep | 9001 trace | ~0 | never drains (learning out-adds fading) |
| recent loss > recent gain, sleep gain uncounted | live 9001 | 203 | sleep begets sleep |
| same, sleep gain counted | live, both | 5 by lesson 400 | retention fell (85 -> 78 of 85) |
| own forgetting span, cruising only | live, both | 44 / 46 | promoted held; kept fell 130 -> 124, 141 -> 134 |
| own forgetting span, always; hot postpones; reset to 0 | live, both | 57 / 57 | 4242 kept 130 vs 141, promoted 37 vs 40 (forgetting past one span discarded at reset) |
| **own forgetting span, always; hot postpones; remainder carried** | live, all four | 63 / 63 / 46 / 46 | see below |

What the failures teach: comparing gain with loss does not capture what sleep is for; and the
clock's "every 8" was the organism's own forgetting span (r ~ 0.12 per experience, span ~ 8.4)
all along. A rule that lets busy stretches skip forgetting loses memory, because forgetting
does not pause when the mind is busy.

## Final results (appended)

No false alarms, proved: on the two old lives (no reversals) heat revision ends byte-identical
to the same life without it (9001 `b164fe51...`, 4242 `0f76a341...`): not one challenge recorded.

| life | arm | kept | promoted | active wrong | revised correctly | controls revised | sleeps |
|---|---|---|---|---|---|---|---|
| changing 9001 | watch | 136 | 37 | 5 | - | - | 68 (clock) |
| changing 9001 | revise | 130 | 35 | **0** | **5/5** | 0 | 68 (clock) |
| changing 9001 | revise + gear | 130 | 36 | **0** | **5/5** | 0 | 63 |
| changing 4242 | watch | 139 | 39 | 7 | - | - | 68 (clock) |
| changing 4242 | revise | 141 | 40 | **0** | **5/5** | 0 | 68 (clock) |
| changing 4242 | revise + gear | 141 | 40 | **0** | **5/5** | 0 | 63 |
| old 9001 | revise | 145 | 43 | 0 | - | 0 | 50 (clock), identical to reference |
| old 9001 | revise + gear | 145 | 42 | 0 | - | 0 | 46 |
| old 4242 | revise | 148 | 46 | 0 | - | 0 | 50 (clock), identical to reference |
| old 4242 | revise + gear | 148 | 45 | 0 | - | 0 | 46 |

(kept / promoted on the passing groups: massed, spaced_short, spaced_long, returning.)

## Verdict
* **Local heat is an answer.** Read only from the organism's own bonds (your 2024 formula), it
  found every changed pattern and no unchanged one on two lives (AUC 1.0, no heat before the
  change), located the departed member, and, given the power to challenge through Milestone 18
  and the Council, revised all 10 four-member reversals correctly, retired every wrong merged
  fold the changing world produced (active wrong 5 -> 0, 7 -> 0), touched no control, and on
  lives with no change did literally nothing. The 3-member reversals stay UNRESOLVED (M18's own
  minimum of 3 members); that is a known limit, recorded.
* **The gear is not yet an answer, but it explained the number it was meant to replace.** Six
  sleep rules failed for stated reasons; the seventh (sleep once per the organism's own
  forgetting span, computed from its decay rate; busy stretches postpone sleep, never cancel it)
  matches the clock on the changing lives (130/36 vs 130/35; 141/40 vs 141/40) with 63 sleeps
  instead of 68, sleeping in quieter moments, but loses one knife-edge spaced_long promotion on
  each old life (46 sleeps vs 50). The clock's 8 turned out to be the organism's own span
  (~8.4). The gear's real gain over a fixed 8 is that it follows the organism: change the decay
  rate or the cycles an experience takes and its sleep moves with it.
* What revision costs: each challenge advances the kernel's cycle, and parts of memory are
  clocked in cycles (sleep's 400-cycle horizon). That coupling, and the knife-edge cohesion gate
  on long-gap families, are the next things to remove; stored questions directing sleep (the
  earlier fork) already closed the cohesion gap.
