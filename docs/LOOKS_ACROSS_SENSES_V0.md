# Looks across senses: what each piece of an experience looks, sounds and reads like (opt-in, EXPERIMENTAL)

Status: design and success criteria written **before** any test was run (2026-11-17 evening).
Results are appended below the line, never edited into the design.

## Why
The imagination reality check (docs/RECALL_RELIVE_IMAGINE_V0.md) showed imagination's model of the
organism is exact; every miss came from guessing how an unseen combination would look. The guess
used a concept's *average* look, which is mostly the look of the scenes it usually appears in.

## Finding that makes this possible (checked before the design)
The organism's memory keeps more than a blend. Reliving recovers the sensed part of an experience
exactly, and that sensed part can be turned back into **the sense organ's own description** (the
feature vector the eye, ear or reader handed in), because the projection is fixed and the field has
as many numbers as the description (2 x 128 real numbers vs 128 features for text). First check on
the 406-lesson organism: 6 lessons recovered to within 4e-4 with a coarse search. This needs the
field to be at least half as wide as the sense's description and the projection not saturated.

## Design: every sense has a space where pieces simply add up
Senses combine the pieces of a scene differently, so each sense declares its own rule:

| sense | what the organ hands in | how pieces combine | space where pieces add |
|---|---|---|---|
| reading (text) | hashed letter patterns, log counts, normalised | side by side: the words of the pieces are all there | **counts** of letter patterns (recovered exactly: counts are whole numbers) |
| hearing (48-band ear) | log energy per frequency band, loudness removed | overlapping in time and frequency: energies add | **energy** per band (exp of the log, as a share of the total) |
| sight (perception's objects) | each object's appearance, pooled over the objects seen | placed apart; perception already separates objects | **appearances average** over the objects in view |
| unknown sense | anything | assumed side by side | the description itself (flagged as an assumption) |

So "which part of this belongs to which piece" means something different per sense: in reading
the parts sit side by side, in hearing they overlap and must be unmixed, and in sight the
senses largely hand you the parts already (objecthood), so the share is close to directly seen.

### Learning each piece's own share (INFERRED, from the record only)
For one sense, over every relived experience of that sense: recover the organ's description,
move it into the sense's adding space, and solve, by least squares with a small ridge (1e-3),
`experience ~ common part + sum of the shares of the concepts present` (for sight, the average).
The common part holds what no known concept explains (templates, background); what is left after
that is the experience's **unknown**.

### Imagining a look with shares (IMAGINED)
Start from the memory's own recovered description (its real specifics, not an average), move to
the adding space, remove the swapped-out piece's share, add the newcomer's, move back, and hand it
to the organism's own projection. The imagined look feeds the existing `imagine(..., look=...)`.

## Tests and success criteria (fixed now)
Measures, as in the first reality check: the sensing (alignment of imagined vs real, 0..1) and
what came to mind (overlap of imagination's top-k readout with the organism's real top-k after
the combination is really taught; k = 6, or 3 for organisms with fewer than 20 concepts).
Predictors compared: unchanged memory, **average look (current)**, **shares (new)**, and the true
look (diagnostic ceiling).

1. **Reading, on a different organism** (life seed 4242, kernel seed 7, 400 lessons, full
   reunion stack; the first check used seed 9001), 12 trials, now and after 20 unrelated lessons.
2. **Hearing**: a small organism that hears mixtures of 2 or 3 synthetic voices (each voice a
   concept), loudness varying; imagine a never-heard mixture with one voice swapped; then play it.
3. **Sight**: a small organism that sees scenes of two shapes through the media gateway and
   perception; scene description = pooled object appearances; imagine a never-seen pair; then show it.

Success, per sense: shares beat the average look on sensing alignment in a clear majority of
trials (at least 2/3), and do not lose on what came to mind. Reported either way. Caution
already stated: text is built from letter patterns and may split into parts more neatly than
images or sounds; a good text result alone does not show the method works for real senses.

---
## Results
(appended after the runs)

### Second design correction (found by tests, before the final runs)
The first size refit for hearing collapsed: judged against an experience's total, shrinking every
sound toward flat explains anything (fitted sizes ~0.6, truth ~6.5). The fit is now judged against
the experience's contrast; hearing first picks one shared size for the sense, then lets each
experience move within a factor of two. Test: refitted sizes within a factor of two of the truth.
The recovery guard was also too loose: with the field exactly as wide as the description, the fit
can be perfect and still wrong (one number is lost to the size). It now needs strictly more room.

### Recovering what the sense handed in
Reading, 406-lesson organisms: every sampled lesson recovered to <= 6e-9, and the exact whole-number
letter-pattern counts came back 11/11. Hearing (48 bands) and sight (35 numbers) recovered to <= 8e-9.

### Imagining a never-met combination, then meeting it for real

Sensing = alignment of the imagined look with the real one (0..1). Came to mind = overlap of the
top-k readout with the organism's real top-k (k = 6 reading, 3 for the small worlds).

| sense, organism | unchanged | average look (old) | **shares (new)** | true look | shares beat average on sensing |
|---|---|---|---|---|---|
| reading, life 4242, 12 trials | 0.950 | 0.959 | 0.957 | 1 | **3/12 (fails)** |
| hearing, seed 11, 8 trials | 0.547 | 0.764 | **0.912** | 1 | **8/8** |
| hearing, seed 12, 8 trials | 0.555 | 0.803 | **0.915** | 1 | **8/8** |
| sight, seed 11, 8 trials | 0.961 | 0.987 | **0.999** | 1 | **8/8** |
| sight, seed 12, 8 trials | 0.963 | 0.985 | **0.999** | 1 | **8/8** |

| came to mind (now / later) | unchanged | average look | **shares** | true look | top-1 right, average vs shares (now) |
|---|---|---|---|---|---|
| reading, life 4242 | 0.61 / 0.53 | 0.83 / 0.72 | **0.85 / 0.74** | 1.00 / 0.74 | 11 vs 11 of 12 |
| hearing, seed 11 | 0.67 / 0.50 | 0.83 / 0.71 | **0.96 / 0.71** | 1.00 / 0.75 | **2 vs 8** of 8 |
| hearing, seed 12 | 0.58 / 0.46 | 0.92 / 0.75 | **0.92 / 0.75** | 1.00 / 0.75 | **2 vs 6** of 8 |
| sight, seed 11 | 0.63 / 0.29 | 0.96 / 0.46 | **1.00 / 0.46** | 1.00 / 0.46 | 8 vs 8 of 8 |
| sight, seed 12 | 0.63 / 0.46 | 0.92 / 0.58 | **0.96 / 0.58** | 1.00 / 0.58 | 8 vs 8 of 8 |

Against the criteria fixed beforehand: **hearing passes (both seeds), sight passes but is a weak
test, reading fails.** Shares never lost on what came to mind in any sense (per trial, hearing
seed 12 was 2 better / 4 same / 2 worse now; all others better or equal).

### What it means, plainly
* **Hearing is where this matters.** Sounds overlap, so the old guess (a voice's average sound,
  which is mostly the voices it is usually heard with) was poor. Unmixing each voice's own energy
  from the record predicts an unheard mixture far better, and puts the right thing first in mind
  far more often (8 vs 2, 6 vs 2).
* **Sight here is a weak test, and that is itself a finding.** Perception already separates the
  objects, so the parts are nearly handed over; but the pooled appearance description makes every
  scene ~96% alike before anything is swapped. Shares still won every trial. A "placed" description
  (which object is where) would make sight a real test.
* **Reading failed for a reason that is general, not a bug.** In the text life every family is
  always taught together (each tested word met with the same 2-3 companions in all 5-8 lessons).
  Nothing in the record can say which letters belong to which word; the learned shares match a
  word's own letters at r = 0.1-0.7. Test: words met apart are told apart; words always met together
  get identical shares. **A piece can only be learned as a piece if it was ever met apart.** This is
  cross-situational learning, and it applies to every sense. Reading is also only roughly additive
  (letter patterns spanning the spaces depend on the neighbours and the position).
* **"Later" is limited by the world moving on, not by imagination.** In every sense the true look
  scores no better than shares later; in the small sight worlds, new shapes seen recently take the
  top of mind (top-1 later: 0-1 of 8 for every predictor, including the true look).

### What this points to
1. A teaching agenda needs **naming apart**: show each thing on its own or in varied company at
   least sometimes, or its look can never be separated from its usual companions.
2. Reading would benefit from objecthood like sight's: a reader that hands in per-word descriptions.
3. Sight needs a placed description (what is where) to be tested properly; this is also the first
   step toward Mindspace's stored organisation.

### Design correction (made after the first hearing run, before its corrected re-run)
The first hearing run's diagnostic gave the true look 0.867 against reality, which must be 1.0.
Cause: the kernel scales every input description to unit length before projecting it. Text
descriptions are already unit length, so the first reality check never showed it. Two fixes:
1. `imagine(..., look=...)` now scales a described look exactly as real intake does (a bug).
2. For hearing and sight, the size of each description is lost on intake, and hearing's adding
   space (energy = exp of log energy) depends on it. The organism now refits each experience's
   lost size from its own record: alternately, the size that lets the pieces' shares explain the
   experience best, then the shares again (8 rounds). Reading needs no refit (whole-number counts
   fix the size exactly). The first run's numbers are kept in the git history of the report only.
