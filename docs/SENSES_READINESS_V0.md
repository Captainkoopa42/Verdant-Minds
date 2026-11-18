# Senses readiness: items 2-8 before developmental teaching (opt-in sidecars, EXPERIMENTAL)

Date: 2026-11-18. Item 1 (recognition in the wave) is in docs/RECOGNITION_IN_THE_WAVE_V0.md;
looks and imagination across senses in docs/LOOKS_ACROSS_SENSES_V0.md. No file under `verdant_*`
was edited. Every result below names its observer and report; small synthetic worlds unless noted.

## Item 4: the fine ear inside the real sensory pipeline (`sidecar_ear`)
The built-in audio translator hands the field 10 numbers. `install_fine_ear(48)` makes the real
pipeline hand it 48 log-energy bands spaced by pitch, level removed; the pipeline's own change
signature is kept exactly. Tested end to end through `VerdantSensoryPipeline.ingest_samples`
(archive written and verified) with ringing on (`run_observer_pipeline_ear.py`; reports
`pipeline_ear_seed{41,42}_{builtin,fine}.json`). 8 known voices, 4 lessons each; then unnamed new
recordings of known voices and of 2 never-heard voices.

| | built-in 10 numbers (seeds 41, 42) | fine 48 bands (seeds 41, 42) |
|---|---|---|
| a known voice rings itself, exactly | 24/32, 20/32 | **32/32, 32/32** |
| a never-heard voice rings nothing | **0/16, 0/16** (every one felt familiar) | **16/16, 16/16** |
| a never-heard voice is called unknown (> 0.5 left over) | 0/16, 0/16 | **16/16, 16/16** |

The built-in ear makes the organism mistake every new voice for one it knows. Note: an organism
should not mix sounds heard with both ears (different description widths enter by different doorways).

## Item 3: a reader that sees words separately (`sidecar_reader`)
The reading organ hands the field one description of a whole sentence (letter-pattern counts), so
words always taught together can never be separated (last night's finding). Objecthood for reading
has to happen at the organ, as perception does for sight. The reader hands in, alongside the
unchanged sentence description, each word's own look and the words in order; the organism keeps
each told concept's word look as OBSERVED. **Development is exactly stock**: on the 400-lesson
life (seed 4242) field history (406 frames), bonds, structures and profiles are identical with and
without the reader; 338/338 concepts gained a word look.

Imagination reality check on that organism, same 12 trials as before (`imagination_reality_seed4242_reader.json`):

| predictor | look (sensing) | came to mind now / later | top-1 now |
|---|---|---|---|
| average look (old) | 0.959 | 0.83 / 0.72 | 11/12 |
| shares by regression | 0.957 | 0.85 / 0.74 | 11/12 |
| word looks alone | 0.961 | 0.79 / 0.72 | 10/12 |
| **re-read with the words in order** | **1.000** | **1.00 / 0.74** | **12/12** |
| true look (ceiling) | 1 | 1.00 / 0.74 | |

Word looks alone do not help: the letter patterns that span word boundaries ("e al", "ba b")
belong to neither word (in a test sentence, 12 of 102 patterns). Keeping the words in order lets
a swap be re-read through the reading organ itself, which is exact by construction for the look
(stated, not a discovery); what it shows is that for reading, keeping what is where is what
imagination needs, the same lesson as sight.

## Item 2: sight that knows what is where (`sidecar_looks.placed_sight`, observer `--sight-description placed`)
Perception records each object's position. The placed description hands the field each object's
look in its place, left to right, plus where it is (2 places x (35 + 2) numbers). Pieces occupy
places; a swap replaces what is in the swapped piece's place (old place - out share + in share)
and leaves the other place untouched. Reports `imagination_sight_placed_seed{11,12}.json` vs the
pooled `imagination_sight_seed{11,12}.json`:

| | pooled (seeds 11, 12) | placed (seeds 11, 12) |
|---|---|---|
| same pair with places swapped looks alike | 1.0 (identical by construction) | **0.84, 0.84** |
| scenes alike before any swap (unchanged memory vs real) | 0.96, 0.96 | **0.92, 0.92** (a harder, fairer test) |
| shares beat the old guess on the look | 8/8, 8/8 (0.999 vs 0.987) | **8/8, 8/8** after the fix below |

A first version pasted a piece's share as if it were the whole object's look (shares are learned
relative to what every scene has), and chose the place by plain resemblance, which fails when
looks are ~96% alike: shares lost (0.75-0.80 vs 0.94). Fixed: swap within the place, choose the
place after removing the common part. Test: the untouched place stays exact; the imagined scene is
closer to the never-seen pair than the memory is.

## Item 6: naming as its own kind of evidence (`sidecar_ring.how_known`)
For each concept, kept apart by kind: how many times it was named (reading), sensed while told per
sense (OBSERVED), recognised without being told per sense (INFERRED, from the ring log), and which
senses it has its own view through. Binding world (`binding_seed51*.json`): a thing named, seen and
heard; seen only; heard only; and only named ("knows_look_of": [], so the organism can say "I know
the word, not what it looks like"), all reported correctly.

## Item 7: binding across senses, with its negative control (`run_observer_binding.py`)
Pairs: P seen and Q heard in the same moment (same context), 6 times; R seen and S heard, never
within 5 experiences of each other, 6 times each. Seeds 51 and 52.

| | P-Q bond (together) | R-S bond (never together) | named Q brings P | unnamed Q brings P | a sound brings back its own look |
|---|---|---|---|---|---|
| stock + ringing | 0, 0 / 0, 0 | 0 | 0/4 | 0/4 | 12/12 |
| + carry everything one experience | 0.38, 0.37 / 0.41, 0.36 | 0 | 4/4 | 0/4 | 12/12 |
| + carry + recognition can remind | same | 0 | 4/4 | **4/4** | 12/12 |
| **+ binding by moment + recognition can remind** | **0.43, 0.42 / 0.40, 0.36** | **0** | **4/4** | **4/4** | **12/12** |

Why nothing bound (found by reading the workspace's own reasons): what is sensed stays present for
1 kernel cycle and the workspace caps carrying at 4, but one experience takes 4-5 cycles inside the
organism, so nothing sensed is ever still present when the next experience arrives; and the faint
echo of a moment ago scored 0.21 against an admission line of 0.28. Carrying every sensed item
through the next experience (the engine's own settings) made binding work but **harmed the text
life** (below), so the kept version binds by moment: the previous experience's told concepts are
offered again ("same moment: <event>") only when the new experience shares its context. And
association recall started only from told concepts, so an unnamed sound could not remind;
`install_inferred_association` lets rung concepts start it, every such candidate marked
`triggered_by_inferred`. (Recall and structures never create bonds; stock rule, kept.)

## Item 8: tension and the unknown steer attention (`sidecar_ring.install_attention`, `run_observer_attention.py`)
Stock gives every experience novelty 0.35 and contradiction 0, although the workspace weights both.
Now both are measured from the wave before the experience changes memory: novelty = the unknown
share in its sense; contradiction = how much a concept it was not told explains beyond the told
ones (when those already have a view in that sense). Each told concept keeps a phase-aware agreement
record like the stance sidecar (+1 agree, a half turn for conflict); `read_tension` gives net and tension.

| seeds 61, 62 | stock | measured |
|---|---|---|
| a sound told X but sounding like Y: flagged (contradiction > 0.2) | 0/3, 0/3 | **3/3, 3/3** (0.96, 1.0) |
| correctly told familiar sounds flagged (false alarms) | 0/8, 0/8 | **0/8, 0/8** |
| attention score of the conflicting moment | 0.53, 0.53 | **0.645, 0.65** |
| tension on the conflicted concept / on others | none recorded | **0.36, 0.38 / 0.0** |
| novelty of new things / familiar things | 0.35 / 0.35 | 0.14, 0.22 / 0.02 |
| bonds of new pairs vs familiar pairs (4 shared moments) | 0.46, 0.36 / 0.52, 0.58 | 0.41, 0.39 / 0.54, 0.59 |

Conflict steers attention cleanly. Novelty is measured but barely moves attention: the workspace
gives novelty 6% of its weight, and stock's flat 0.35 is already higher than what most new things
measure after their first meeting; new pairs were not learned faster. Raising novelty's weight is a
policy decision, not made here. Conflict in the field itself still shows as silence, not opposition
(item 1 finding); the half-turn lives in the per-concept record, which resonance (absolute values)
does not read.

## Does the new senses stack keep the old text results? (400-lesson life, seed 9001, kernel 2301)
`run_observer_long_life.py --senses` installs ringing + adaptation, binding by moment, recognition
can remind, and measured attention.

| | cues kept | promoted | wrong promotions |
|---|---|---|---|
| full stack as before ("reunion") | 145/148 | 43/46 | 0 |
| **+ senses stack (binding by moment)** | **145/148** | **43/46** | **0** |
| + ringing and carry-everything (rejected) | 139/148 | 43/46 | 5 |
| full senses stack with carry-everything (rejected) | 139/148 | 43/46 | 5 |

Carry-everything bound unrelated neighbouring lessons into wrong structures (e.g. a family plus two
members of other families). In the text life no two neighbouring lessons share a context, so binding
by moment never fires there and text development is unchanged.

## What is left
* Novelty barely steers attention at stock weights (a policy choice).
* Conflict is opposition only in the per-concept record, not in the field resonance reads.
* Sight is described for 2 places; more places, depth and the Mindspace geometry worker come later.
* All of this is on small synthetic worlds plus the 400-lesson text lives; the teaching agenda is next.
