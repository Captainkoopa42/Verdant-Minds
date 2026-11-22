# The whole-life gate v0

Status: PREREGISTERED 2026-11-21 before the full runs. Results appended below.

## Why
Every part so far was tested in its own setup and never all together: the fine ear was "folded
in" without ever hearing a sound. From now on every change must pass ONE life grown by the WHOLE
organism (`verdant_organism`, every validated part on) that uses every kind of input, with every
earlier ability checked on that same mind (`run_observer_whole_life.py`). Being better at its own
task is not enough.

## The life
A changing-world text curriculum (generator v1, families, reversals with controls, claims), 8
voices taught by name through the real sensory pipeline with the fine ear, things seen and heard
(by name, at the same moment, never at the same moment), and scenes (families taught together,
a twice-taught and a one-context scene that must not fold, and the whole world). One stream.

## Gates (each seed; 9001 and 4242, text-lessons 400)
T  active wrong structures 0; every promoted 4-member reversal revised; 0 controls revised;
   0 promotions from failing groups; kept and promoted reported against the text-only organism
   (changing lives: 145/148 & 43/46 on 9001, 148/148 & 43/46 on 4242) - not lower by more than
   the knife-edge seen between runs (2 promoted).
V  known voices named >= 90%; never-heard voices over half unknown >= 90%.
B  every together-bond > every apart-bond; unnamed sound brings its moment partner 2/2, and the
   never-together partner 0/2.
L  look back >= 5/6.
F  g1, g2, g3 fold (depth >= 2); twice and one_context do not fold.
S  median tension: reversed_late and contested > affirmed_only and negated_only.
I  relive 5/5, recall works, imagine works, simulate leaves the mind unchanged.
R  the same seed grown twice ends on the same fingerprint.
All checks run after the life on the grown mind; the mind's fingerprint must be unchanged by them.

## Smoke (plumbing only; seed 7, text-lessons 30, 272 lessons, 2.9 min)
Every section ran: voices 24/24 named and 12/12 never-heard mostly unknown; binding together
bonds 0.28/0.24 vs apart 0/0, partner brought 2/2 vs 0/2; look back 6/6; folds g1-g3 depth 2,
twice and one_context not folded, world folded; stance tension reversed 0.33 and contested 0.31
vs 0 for affirmed / negated; one bug in the observer's own check code (field name), fixed.

## First full results (appended), default organism, horizon 76 experiences
| gate | 9001 | 4242 | |
|---|---|---|---|
| T active wrong / reversals / controls / failing | 0 / 5/5 / 0 / 0 | 0 / 5/5 / 0 / 0 | pass |
| T kept, promoted (text-only organism) | 135/148, 37/46 (145, 43) | 127/148, 35/46 (148, 43) | **fail** |
| V voices known / never-heard | 24/24, 12/12 | 24/24, 12/12 | pass |
| B together bonds / apart; partner brought | 0.00, 0.11 / 0, 0; 0/2 | 0.10, 0.13 / 0, 0; 0/2 | **fail** |
| L look back | 6/6 | 6/6 | pass |
| F folds g1-g3 depth 2, twice / one_context not, world | yes | yes | pass |
| S tension reversed, contested vs affirmed, negated | 0.32, 0.34 vs 0, 0 | 0.28, 0.22 vs 0, 0 | pass |
| I relive 5/5, recall, imagine, simulate unchanged | yes | yes | pass |
| checks left the mind unchanged | yes | yes | pass |
| heat AUC at end (1.0 in text-only lives) | 0.82 | 0.87 | weaker |

Diagnosis in progress. The mixed life puts ~235 other lessons between text lessons, so every
gap is ~43% longer, while sleep's horizon is a fixed 76 experiences. The "same moment" lessons
last happened 136 (9001) and 82 (4242) lessons before the end: past the horizon, so sleep had
stopped defending those bonds. Candidate cause for both failures: the last fixed number in
sleep. Control running: the same mixed life with the lean organism (no senses / wave / profiles
/ stance parts) - if it drops as much, the parts are not the cause.
Candidate fix, no number in it (`horizon_lived`): sleep defends a bond for as long as the world
kept confirming it (first to last real exposure, counted in experiences).

## Diagnosis (appended)
* R replay: 9001 grown twice ends on the same fingerprint `f5752ce5...`. Pass.
* Lean organism in the same mixed life (9001): 139/148, 38/46. It drops too, so the senses / wave
  / profiles / stance parts are not the main cause (they cost at most ~1 promotion, knife-edge size).
* `horizon_lived` (defend a bond as long as the world confirmed it): 9001 135/37 (unchanged), 4242
  123/34 (worse), binding unchanged. **Hypothesis falsified**: the fixed horizon was not the cause.
* New suspect, from reading sleep's choice rule: fading memories are practised most-met first.
  In the mixed life the scene families are met up to 15 times (alone, in their scene, in the
  world), so they take sleep's 5 places every night and the text families and same-moment pairs
  never get a turn: the most practised get more practice. Test: `priority="neglected"` (the
  memory longest without any reinforcement first, so every really-met memory gets a turn).

## Sleep's choice rule (appended)
| seed | most-met first | longest-neglected first | neglected + lived horizon | text-only organism |
|---|---|---|---|---|
| 9001 kept / promoted | 135 / 37 | **144 / 41** | 131 / 37 | 145 / 43 |
| 4242 kept / promoted | 127 / 35 | **135 / 38** | 123 / 34 | 148 / 43 |

Every other gate passed in every one of these runs (voices, look back, folds, stance,
imagination, revision 5/5 with 0 controls, 0 active wrong, checks leave the mind unchanged).
* Longest-neglected first recovers most of the loss: confirmed. The most-practised memories
  were taking every sleep.
* Adding the lived horizon makes it worse (defending many old memories thins the turns again):
  rejected a second time; the 76-experience horizon stays.
* What is still missing on 4242: 8 spaced_long families, each failing only internal cohesion.
* Binding, explained: pair 1's moments were up to 244 lessons apart; its bond was pruned in a gap,
  rebuilt, and faded again (last moment 137 lessons before the end); pair 2's bond exists (9
  exposures) at the floor, 0.1. Binding forms and links only things that met (short life: 0.28 /
  0.24 vs 0 / 0, 2/2 vs 0/2); a pair met 6 times across 500 lessons is forgotten like any sparse
  memory. Design gap found: stored questions exist only for candidates of 3+ members, so a
  two-thing memory (this sound goes with that sight) has nothing asking sleep to keep it.
* Decision pending its text-life check: `sleep_priority="neglected"` as the organism default.

## Longest-neglected first on the text-only lives (appended)
| life | most-met first | longest-neglected first |
|---|---|---|
| changing 9001 | 145 / 43, active wrong 0 | 145 / **44**, active wrong **1** |
| changing 4242 | 148 / 43, active wrong 0 | **145** / 43, active wrong 0 |

The one wrong structure in use is the merged fold of a 3-member reversal (old + new member,
promoted at lesson 348 while the changed family was still being shown). Its old and new members
have drifted almost equally (0.23 vs 0.24: the new member's bonds faded too after the family's
last lesson), so the evidence does not say which one left and heat rightly does not act; its
3-member parent is UNRESOLVED (M18's 3-member minimum, the known limit).

Two Verdant-shaped couplings added on the way, both principled, neither of which fired in these
lives (fingerprints identical): sleep does not practise a bond heat revision currently suspects
(a run of absences waiting); and absence alone starts a suspicion (drift only sets its strength).

Decision: `sleep_priority="neglected"` becomes the organism default. On the whole life (the
standard now) it is clearly better on both seeds (+4 / +3 promoted, +9 / +8 kept); on the
text-only lives it is even (+1 promoted on one, -3 kept on the other) with one ambiguous
3-member case. Recorded as a trade-off, not hidden.

## Final organism through the whole life (appended)
| gate | 9001 | 4242 | verdict |
|---|---|---|---|
| T active wrong / reversals / controls / failing | 0 / 5/5 / 0 / 0 | 0 / 5/5 / 0 / 0 | pass |
| T kept, promoted (text-only organism) | 144/148, 41/46 (145, 43) | 135/148, 38/46 (148, 43) | 9001 pass; **4242 fail** (-5 promoted, 8 spaced_long families short of the cohesion gate) |
| V voices | 24/24, 12/12 | 24/24, 12/12 | pass |
| B binding | 0.00, 0.10 vs 0, 0; 0/2 | 0.00, 0.12 vs 0, 0; 0/2 | **fail** (sparse pairs forgotten; no questions for two-thing memories) |
| L look back | 6/6 | 6/6 | pass |
| F folds of folds | g1-g3 depth 2, world; twice / one_context not | same | pass |
| S stance | 0.32, 0.34 vs 0, 0 | 0.28, 0.22 vs 0, 0 | pass |
| I imagination | all | all | pass |
| R replay | identical | - | pass |

What the gate found that no single-part test could: sleep practised the most-met memories
first, so in a rich life a few heavily taught families took every night (fixed: every
really-met memory now gets a turn); the fixed horizon was NOT the cause (tested twice,
rejected twice); and two-thing memories (this sound with that sight) have no stored question
to protect them. Open: the 4242 shortfall (long-gap families at the cohesion edge, the same gap
the questions address, now competing with a much richer life) and binding over long sparse gaps.
