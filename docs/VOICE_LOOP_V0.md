# Voice loop v0: learning to use a voice by listening to itself (observer, seed 2301)

`run_observer_voice_loop.py`. Voice: synthetic sound-maker with 3 controls (pitch x5, brightness x3,
breath x2 = 30 combinations). The mind babbles 18 of the 30 combinations, 3 times each (54 ordinary
experiences, modality "audio", marked self_action): what it heard + the three control settings as
three concepts. Then a "parent" sound (other loudness, +-3% pitch, fresh noise) arrives as numbers
only; `inspect_resonance` picks a setting per control; the mind answers with its own voice.

| ear | sounds | pitch right (chance 20%) | breath right (50%) | brightness right (33%) | all three (3.3%) |
|---|---|---|---|---|---|
| media gateway (26 numbers), combinations it babbled | 54 | 39% | 52% | 46% | 13% |
| media gateway, combinations it never tried | 36 | 22% | 39% | 25% | 6% |
| finer ear (48 frequency bands), babbled | 54 | 74% | 85% | 33% | 22% |
| finer ear, never tried | 36 | 86% | 61% | 33% | 14% |
Ear-only baseline (nearest average babble, no mind) on pitch: gateway 54% / 19%; finer ear 78% / 83%.
By the ear's own distance, the echo is closer to the target than a random setting with the finer
ear (5.7 vs 9.4; 7.1 vs 11.9) and not with the gateway ear (6.9 vs 7.1; 8.6 vs 7.3).

The finer ear is NOT the media gateway: it is a 48-band log-frequency energy description written
for this test. With the wave sidecar's scoring, results were worse (pitch 30% / 28%): its 2 SD
rule is too strict with only 10 concepts in the mind.
Not learned: brightness. One seed, synthetic voice, no real microphone or speaker.
Demo audio: six parent sounds each followed by the mind's echo (combinations it never babbled).
