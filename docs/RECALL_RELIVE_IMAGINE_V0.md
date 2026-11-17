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
