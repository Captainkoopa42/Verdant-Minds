# Recognition in the wave: one readout for every sense (opt-in, read-only, EXPERIMENTAL)

Status: design and expectations written **before** the first run (2026-11-17, night). Results
are appended below the line.

## The idea (William's design, read out)
The wave was made as a medium where diverse data can interact. Already in the engine:
* every sense writes into the same field through its own fixed doorway (a projection per sense);
* each concept keeps one resonance profile, and every exposure, of any sense, is averaged into it:
  the senses sit on top of each other like notes in a chord;
* a concept's address does not depend on the sense, so seeing and hearing the same thing write the
  same address: that is where binding across senses comes from;
* the sensory pipeline already groups sight and sound that happen together into one event;
* resonance includes the live field and recent history, so hearing a thing should prime seeing it.

So step 1 is not a new recogniser. `sidecar_recognize.read_wave` reads any input the same way: the
input through its sense's doorway, explained by known things by least squares in the field, the
rest left as unknown. Views of the known: the engine's own **chord** (one profile per concept), or
**per sense** (a concept's experiences of that sense, recovered exactly from the field history).
Adaptation in the wave: subtract the sense's average wave first.

## What is measured (run_observer_one_wave.py)
World: 8 things (look via the real media gateway and perception; sound via an ear; name via text).
Groups of 2: mostly heard (6 sounds, 1 sight), mostly seen (1 sound, 6 sights), balanced (3/3),
together (3/3, each sight followed at once by its sound in the same context). 2 name lessons each.
2 never-shown shapes, 2 never-heard voices. 4 new test sights and sounds per thing.
1. **Dilution**: naming from sight and sound, per group, by the organism's own resonance and by the
   readout (chord / per sense / per sense + adaptation). Baseline: the sense alone.
2. **Priming**: an unlabelled sound arrives, then a hard (dim, noisy) sight. Rank of the thing.
3. **The unknown**: leftover of known vs never-met inputs per sense and group.
4. **Conflict**: a sight of X with a sound of X, of another known Y, or of a never-heard voice.

Expectations stated in advance (to be checked, not tuned toward):
* The chord view will be diluted: the mostly-heard things will be poorly recognised by sight and
  the mostly-seen by sound; and a rarely-met sense of a known thing may look "unknown".
* The per-sense view should remove most of the dilution, since it reads each sense on its own.
* Priming: a sound of X should improve X's rank for a hard sight; a sound of another thing should not.
* Conflict: with fixed random doorways, two different things are nearly at right angles in the
  field, so I expect disagreement to show up as **silence** (no in-phase part), not as cancellation
  (a negative in-phase part). If so, the wave as built cannot yet tell "conflicts with" from
  "unrelated to"; that would need the half-turn coding the stance sidecar uses.
Ears compared: the fine 48-band ear and the built-in pipeline's 10 audio numbers (readiness item 4).
Minds compared: full stack, and full stack with the wave sidecar (phase direction).

---
## Results
(Interim notes in order of discovery; the full table follows at the end.)

**Run 1 findings that changed the plan.** (a) Dilution is real in the organism's own resonance;
the per-sense reading removes it. (b) Priming is absent: nothing in the system writes what the
organism recognises back into the field, so an unnamed sound leaves only "a sound" in the field.
Built `sidecar_ring` (per-sense views kept in the organism; recognition rings the wave; inferred is
never told). Thresholds fixed before its first run: share >= 0.25, unknown <= 0.5, at most 2.
(c) After ringing, the organism's own sight naming was still poor (0-50%) while the per-sense
reading with the sense's usual wave removed was 88-100%; so adaptation in the wave was added as an
option (`install_ring(adapt=True)`) and is tested on a fresh seed (33) as well as 31 and 32.

### Results (full stack "reunion", 48-band ear unless noted; 8 things, chance 12.5%)
Naming = mean over the four groups of naming new sights / new sounds (4 tests per thing).

| run | the organism names from **sight** | from **sound** | sense alone (sight) | per-sense reading (sight) |
|---|---|---|---|---|
| seed 31, stock | 25% | 75% (mostly-seen: 0%) | 100% | 97% |
| seed 32, stock | 16% | 62% | 100% | 100% |
| seed 33 (fresh), stock | 25% | 75% | 91% | 91% |
| seed 31, ring | 25% | 100% | | |
| seed 32, ring | 47% | 100% | | |
| **seed 31, ring + adaptation** | **91%** | **100%** | 100% | 97% |
| **seed 32, ring + adaptation** | **84%** | **100%** | 100% | 100% |
| **seed 33 (fresh), ring + adaptation** | **78%** | **100%** | 91% | 91% |
| seed 31, stock, wave sidecar ("whole") | 12% | 75% | | |
| seed 31, built-in 10-number ear (stock) | 28% (sight) | 12% | | |

Priming (a dim, noisy sight of X after an unnamed sound; X named first, of 8):

| run | no sound | sound of X | sound of another thing |
|---|---|---|---|
| stock (seeds 31, 32, 33) | 2, 1, 1 | 2, 2, 2 | 2, 1, 1 |
| ring (seeds 31, 32; built-in ear 31) | 1, 3, 1 | **8, 8, 8** | 1, 0, 1 (the other thing named first in most) |
| ring + adaptation (seeds 31, 32, 33) | 5, 5, 4 | **8, 7, 7** | 2, 4, 3 |

The unknown (share of (known, never-met) pairs where the never-met input has more leftover):

| | sight, chord | sight, per sense | sound, chord | sound, per sense |
|---|---|---|---|---|
| seed 31 | 0.45 (mostly-heard things: 0.19) | 0.83 | 0.88 (mostly-seen: 0.50) | **1.00** |
| seed 32 | 0.50 | 0.93 | 0.88 | **1.00** |
| seed 33 | 0.65 | 0.97 | 0.95 | **1.00** |
| seed 31, built-in ear | | | 0.52 | 1.00 relative, but 7/8 never-heard voices still under the 0.5 "unknown" line |

Conflict (a sight of X with a sound; verdict from the readout; in-phase = Re<expected sound of X, heard>):

| sound heard | verdicts (seeds 31, 32, 33) | in-phase part |
|---|---|---|
| of X | agree 8, 7, 8 | 0.98 |
| of another known thing | "two different things" 8, 8, 8 | 0.07-0.11 |
| never heard | "unknown" 8, 8, 8 | 0.17-0.23 |
| (built-in ear: other / never heard) | 8 / 7 read as "two known things" | 0.93 / 0.96 |

### What it means, plainly
* **The wave is a working common medium.** One calculation, the same for every sense, says what an
  input is, and how much of it is unknown; sound reaches 100% naming and perfect unknown-detection.
* **Dilution was real and is fixed inside the organism.** The engine averages every sense into one
  profile, so a thing mostly heard was barely recognisable by sight (organism: 16-25% from sight).
  Keeping each sense's own view of each concept (in the organism, saved with it) plus adaptation in
  the wave brings the organism's own sight naming to 78-91%, close to the eye alone (91-100%).
  Ringing alone did not fix sight: sight descriptions are ~96% alike, so it needed adaptation.
* **Priming needed one missing loop, and now works.** Nothing wrote what the organism recognises
  back into the field. With ringing, hearing a thing unnamed makes a hard sight of it named first
  7-8 of 8. Risk seen: without adaptation, hearing another thing overruled a weak sight; with
  adaptation the sight holds its own more often (2-4 of 8 still named correctly).
* **Conflict shows as silence, not cancellation, exactly as expected beforehand.** The readout tells
  agree / two different things / unknown perfectly (24/24 each), but in the wave a disagreeing sound
  is simply unrelated (in-phase ~0.1), never opposed. "Conflicts with" and "unrelated to" are not yet
  different in the field; that needs the half-turn coding the stance sidecar already uses for claims.
* **The built-in 10-number ear is too coarse** (readiness item 4): it can name trained voices when
  read per sense, but cannot call a new voice new, and conflict collapses (in-phase 0.93 for a
  different voice). The 48-band ear should go into the pipeline.
* Limits: small synthetic worlds, 8 things, 3 seeds, synthetic shapes and voices; the "together"
  group did not show a separate binding benefit; the wave sidecar arm did not help naming.

### Connections to the remaining readiness items
2 placed sight: sight is still the weakest sense because its description is pooled; 4 ear: the
48-band ear is needed; 5 adaptation: done in the wave, opt-in; 6 naming: rings are inferred and kept
apart from told names, with disagreements logged; 7 cross-sense binding: the conflict test is a first
version (expected sound from a sight lines up 0.98 with the right sound); 8 tension: logged
disagreements and the silence-not-cancellation finding are the starting point.
