# What the wave field does when it is the only way in (observer, seed 2301)

`run_observer_field_function.py`: 30 three-member families, 150 ordinary lessons, 90 concepts.
Probes are FEATURES ONLY (hashed text of an unseen sentence, no concept list), read through
the kernel's own read-only `inspect_resonance`. Report: `curriculum_packs/reports/field_function_seed2301.json`.

OBSERVED
| test | stock weights (0.5/0.3/0.2) | profile only | live field only | history only |
|---|---|---|---|---|
| A. unseen sentence naming all 3 members -> top 3 are exactly the family | 0% | 87% | 0% | 0% |
| A. sentence naming 1 member -> its 2 unnamed partners in top 3 | 3% | 33% | 3% | 5% |
| B. ambiguous cue (1 member each of 2 families): recently revisited family wins | 100% | 50% | 100% | 85% |
Chance for a given member in the top 3 is 3.3%.
C. A family's alignment with the live field: 0.28 right after it is taught, 0.125 one lesson
   later, 0.09 two lessons later, then 0.077, which is the random level (0.078).
D. Same write/read rule in numpy, separation at lag 0 in noise SDs: complex phasors x128: 9.5;
   real signs x128: 7.0; real signs x256 (same stored numbers as complex x128): 12.0.
E. Putting the three terms on a common scale before weighting did not restore recognition (7%).
F. Numpy only: writing source at phase 0 and target a quarter turn later, direction is read
   back correctly 100% / 100% / 96% at 0 / 1 / 2 lessons of lag. The stock field adds addresses
   with no offset and reads only |overlap|, so it holds no direction today.

READING
The profile recognises without names. The live field carries context about 2-3 lessons wide.
At stock weights, on a features-only probe, context outranks recognition. Phase is not yet a
working variable: per stored number, phasors store no more than real signs under this readout.
One seed; text n-gram features; F is a simulation, not the kernel.

## Follow-up: `sidecar_wave` (opt-in, IMPLEMENTED-EXPERIMENTAL, 5 tests) - a behaviour change, fingerprints differ
Write side: source in step, target a quarter turn later, middle of a chain an eighth turn.
Read side: recognition (profile standing out from the crowd) leads; context multiplies it and
alone cannot exceed 0.1. `field_direction` reads direction back from canonical field history.

OBSERVED (same experiment, same seed, relations supplied in both arms)
| | stock | wave |
|---|---|---|
| A. unseen sentence naming all members -> top 3 exactly the family (combined score) | 0% | 87% |
| A. one member named -> unnamed partners in top 3 | 3% | 15% |
| B. recently revisited family wins an ambiguous cue | 100% | 95% |
| G. direction of 60 taught relations read from the kernel's field history | 52% | 100% (mean 0.13 turn) |

Controls pack, seed 2301: stock + wave gives the same outcomes as stock (0/6, 0/4, 4/4; 14/20).
Three earlier sidecars + wave: gate_pass 3/6 (was 2/6), spaced 1/4, policy checks 17/20 (was 16),
and the merged five-member candidate no longer forms. No refused control became eligible.
Not run: the engine test suites with the wave installed (fingerprint-pinned tests would differ by design).
Nothing in the system consumes field direction yet; G shows it is recorded and recoverable.
