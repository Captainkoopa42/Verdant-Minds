# Recall that chooses how to remember; reliving; imagining (opt-in, IMPLEMENTED-EXPERIMENTAL)

Owner's design (2026-11-17): Verdant can reconstruct a memory and the thought that made it, so
recall should decide between just pulling, reliving, or searching wider before spending effort;
and reliving should allow new variables (other memories, a different context) to make novel
combinations while the original copy stays intact, so nothing is invented and passed off as memory.

`sidecar_recall` (read-only; every call checks the organism's fingerprint is unchanged):
* `recall(kernel, cue)` -> mode pull / relive / search / unknown, each partner labelled
  EARNED, REMEMBERED (>=3 real meetings), WEAK, FADED (met, bond below recall), SEARCHED (resembles,
  record confirms never met). Meetings are counted from observation evidence, not reinforcement counts.
* `relive(kernel, event_key)` -> the experience's exact field effect and the mind just before it,
  recovered from the field history (every experience leaves a frame).
* `imagine(kernel, event_key, swap_out, swap_in, context="then"|"now")` -> the relived experience
  with one concept's address and profile swapped for another's, played against the mind then or now;
  everything held is labelled RELIVED, CONTEXT, ECHO (the unchanged memory calls it up too) or IMAGINED.

## OBSERVED on the grown 406-lesson organism (seed 9001, full system)
* Reliving: 40/40 sampled experiences recovered exactly (replay difference <= 6e-17).
* Recall labels against the true history: every SEARCHED partner was truly never met (117/117);
  things met twice are WEAK or FADED with their 2 meetings relived, never REMEMBERED; one-offs
  read "met 1 time, only once"; never-met words answer "unknown" 10/10. Earned families pull.
* A far-apart family whose bond had faded below recall was found by wider search and relived
  from all 5 meetings in 3 settings.
* Imagining (6 trials, earned family with one member swapped for a member of another family):
  rest of the memory kept 6/6; swapped-out dropped 5/6; swapped-in held 5/6; original memory
  intact 12/12 (then and now contexts); then vs now held different things 6/6; organism unchanged.
* NOT happening: the swapped-in piece does not bring its own family along (0/6). The imagined
  moment recombines; it does not yet spread to the new piece's associations.

First version label errors found by this test and fixed: meeting counts had used bond
reinforcement counts (one experience reinforces several times), and wider search had called the
cue's own faded family "never met".

## Update (2026-11-17, later): the second step, five provenance kinds, and the reality check

### What changed in `sidecar_recall` (still read-only, fingerprint-checked)
* Reliving now also splits an experience back into what was **sensed** and which concepts were
  present: effect = unit(fc*F + cc*C) with C known from the concepts and |F| = 1, so F has one
  positive solution. On the grown organism the recovered sensing matches the lesson's own
  projected features to <= 1e-9 (11 sampled lessons); in tests to < 1e-8 for every lesson.
* `imagine` step one now rebuilds the moment from those parts: the original sensing with the
  swapped piece's average look replaced by the newcomer's (one share in k, declared before testing),
  the concepts present changed exactly, and the moment read with **the organism's own resonance
  readout** (profile 0.5, live field 0.3, recent history 0.2, scene profiles taking the exposure).
* Step two (`second_step=True`): the newcomer brings what the organism's association recall
  would bring from it (earned partners; bonds at or above the workspace's recall threshold 0.24),
  labelled `IMAGINED (brought by X ...)`; the rest of the scene calls things back too,
  `IMAGINED (called back by Y ...)`. This mirrors the development pipeline's own rules.
* `look=(features, modality)`: imagine with a described look instead of the guessed one.
* `simulate(kernel, pipeline, command)`: run one concrete experience through the real pipeline on
  a throwaway copy; results are `SIMULATED_RESULT`. Test: simulation equals the real beat exactly.
* `kind_of(label)` maps every fine label to the five kinds from the Mindspace design:
  OBSERVED, REMEMBERED (EARNED/REMEMBERED/WEAK/FADED/RELIVED/ECHO/CONTEXT), INFERRED (SEARCHED),
  IMAGINED, SIMULATED_RESULT.

### Reality check (`run_observer_imagination_reality.py`; report `imagination_reality_seed9001.json`)
Design, fixed before the run: on the 406-lesson organism, 12 trials. Each takes an earned
family's experience, imagines it with one member swapped for a member of another earned family
(context "now"), then teaches that exact sentence for real on fresh copies: straight away, and
after 20 unrelated new lessons (a different-seed pack; no shared words, asserted). Controls: the
unchanged memory, the wrong newcomer (a third family), and full simulation now vs reality later.

| measure | now | later (after 20 lessons) |
|---|---|---|
| the experience itself, imagined vs real (alignment) | 0.978 (unchanged 0.842, wrong 0.836) | same by construction* |
| imagined beats both controls on the experience | 12/12 | 12/12 |
| sensing alone, imagined vs unchanged | 0.962 vs 0.953 | same* |
| field after the experience, imagined vs real | 0.991 (unchanged 0.934) | 0.927 (unchanged 0.871) |
| what came to mind, top-6 overlap | **0.81** (unchanged 0.61, wrong 0.63) | **0.69** (unchanged 0.57, wrong 0.54) |
| top-1 of what came to mind matches | 10/12 | 9/12 |
| newcomer itself in the real top-6, predicted correctly | 12/12 | 12/12 |
| full simulation now vs reality later, top-6 overlap | — | 0.75 |
| diagnostic: imagination given the true look | 1.00, exact order and scores (<= 3e-11) 12/12 | 0.75 |
| second step: newcomer's partners predicted / really offered | 24/24 (all 24 won attention) | 24/24 |
| the swapped-out piece called back by the rest of its family | predicted 12/12, happened 12/12 | 12/12 |

\* An experience's own effect does not depend on the mind it lands in, so "now" and "later" are
identical for those rows; the field after and what comes to mind do depend on it.

### What this means, plainly
* Imagination's model of the organism is exact: given how the new combination really looks, it
  reproduces the organism's real readout to rounding error. **All of the remaining error is in
  guessing the look of something never seen.** The declared guess (newcomer's average look) is
  only slightly better than keeping the old look (0.962 vs 0.953), which is why "what came to mind"
  is 81%, not 100%. This is the gap a real imagination of appearance (Mindspace's job) would fill.
* "Later" is harder for everything, including exact simulation (0.75): the world moved on for 20
  lessons. Cheap imagination made beforehand (0.69) is close to full simulation made beforehand.
* The second step's agreement (24/24, 25/25) is **by construction**: it uses the organism's own
  recall rules. Not by construction: every predicted partner then won attention (24/24), and in a
  well-learned family the swapped-out piece comes straight back, called by the rest of its family
  (12/12). Imagining a family member away does not make the organism forget it; it returns.

Re-run of `run_observer_recall_and_imagine.py` with the new readout (report overwritten): rest of
the memory kept 6/6, swapped-in held 6/6 (was 5/6), swapped-out dropped 4/6 (was 5/6; with the
organism's own readout the old piece lingers through its look and recent history, as it does in
the real beats above), original intact 12/12, then vs now differ 6/6. The newcomer's family still
does not appear in the top-6 readout (0/6); it arrives through the second step instead (`brought`).
