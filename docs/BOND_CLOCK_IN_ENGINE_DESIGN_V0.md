# Changes-only plasticity records and the bond clock (IMPLEMENTED-EXPERIMENTAL as a layer)

## What was built (2026-11-17), and why not as an engine edit
An engine edit was built first (Option A below, in verdant_kernel/ and verdant_plasticity/).
It was behaviour-identical by default, but the frozen math line pins every top-level file in
verdant_kernel/ by hash, and its protocols are preregistered: re-freezing them would rewrite
preregistered protocols after their outcomes are known. So the engine edit was reverted and the
same design was built as `sidecar_bond_clock`, outside every pinned directory:
* the kernel's plasticity check and commit, and the plasticity stage's inspect, are derived from
  their stock source with one passage replaced and refuse to install if stock changes;
* a changes-only report names itself and its fade rule in its `operation` string, lists bonds that
  only faded in `decayed_association_ids`, and stores only real changes in `proposed_associations`;
* stock reports go through stock code unchanged; the Explorer replays changes-only history.
Checks: full suite 2,185 passed (math line included, preregistration checks intact); Workbench 71
passed; uniform changes-only gives exactly the stock bonds; a saved-and-resumed organism ends on the
same fingerprint as an uninterrupted one, and replayed history equals the live table.

Bug found and fixed at the same time: sleep (`sidecar_rehearsal`) ran its own fresh STOCK plasticity
stage, so every rehearsal beat faded every bond at the stock rate and "free sleep" never happened in
any earlier run. Sleep now uses the waking plasticity stage (test added).

## Result, same 406-lesson life (seed 9001), full stack (`--arm reunion`)
| | 2026-11-16 | 2026-11-17 |
|---|---|---|
| long-gap families promoted | 6/15 | 12/15 |
| all gate-meeting families promoted | 37/46 | 43/46 |
| cues recalled exactly | 129/148 | 145/148 |
| wrong / distractor promotions | 0 / 0 | 0 / 0 |
| saved organism | 135.5 MB | 37.8 MB |
| peak memory (resume + 2 beats) | 1.45 GB | 0.46 GB |
| ms per lesson at checkpoints 100..400 | 411, 1358, 2848, 7902 | 371, 879, 1408, 1910 |
| wall time | 21.8 min | 7.8 min |
The learning gains come from the sleep fix (changes-only records are proven not to change bonds).
Cost now grows roughly linearly (~0.5 s per lesson per 100 lessons). Rough projection, untested:
1,000 lessons ~45 min and ~1.2 GB; 2,500 lessons ~4-5 h and ~3 GB.

# Original design note (kept for the record)

## The problem, measured (saved 406-lesson organism, full experimental stack)
* State 135.5 MB; 108 MB (80%) is `plasticity_events`.
* Every plasticity event stores the whole bond table (`report.proposed_associations`), because
  every bond fades every beat and so counts as changed.
* Across 456 events: 74,588 bond records written; 72,795 (97.6%) differ from the previous beat
  only in `strength`, `updated_cycle`, `last_workspace_event_id`. Real changes: 394 new,
  1,399 reinforced, 158 removed = 1,951. A record of only real change is ~38x smaller.
* Consequence: history grows with lessons x bonds. Projected full stack at 1,000 lessons:
  ~6-7 h, ~8-9 GB RAM. 2,500 lessons: not feasible.

## Option A (recommended first): same meaning, smaller record
Strengths keep fading every beat exactly as now; only what is RECORDED changes.
* `PlasticityPolicy` gains the decay rule as data: `decay_mode = "uniform" | "bond_clock"`,
  with the bond-clock parameters (durability cap 5, floor after 3 exposures, floor 0.10,
  rehearsal beats free). The bond clock stops being a sidecar and becomes engine policy, so
  the kernel can recompute fading itself.
* `PlasticityReport` replaces `proposed_associations` (full table) with
  `changed_associations` (new, reinforced, normalised, or otherwise not explained by the rule)
  and `removed_association_ids`. `decayed_association_ids` is derivable and can go.
* `validate_plasticity_report` / `commit_plasticity_report` rebuild the next table as
  rule(previous table) overridden by `changed_associations`, minus removed, using the identical
  float expression the pipeline used, then run every existing check (degree cap, edge ratio,
  counts, evidence) on the rebuilt table.
* `_validate_state` history loops (missing-evidence check, structure lineage) read
  `changed_associations` plus the live table; every bond ever created still appears in some
  event's `changed_associations`, so lineage checks keep working.
* Readers of the live table (`state.plasticity_associations`) are unchanged: structures,
  compilation recall, workspace, sidecars.
* Readers of event history to update: `verdant_thermodynamics/telemetry.py`,
  `workbench/backend/verdant_workbench/living.py` (Explorer replay must rebuild frames by
  replaying deltas; one O(bonds) pass per frame).
Files: `verdant_kernel/models.py`, `verdant_kernel/kernel.py`, `verdant_plasticity/pipeline.py`,
the two readers above, `sidecar_bond_clock` (retired into policy).

## Option B (later, larger): lazy fading
Bonds store strength-as-of-a-cycle and every reader computes the fade when it reads. Removes the
per-beat O(bonds) rewrite as well, but every reader of `.strength` changes. Only worth it if A is
not enough.

## Consequences the owner must decide on
* Canonical state format changes, so fingerprints change. The frozen math artifacts
  (v0.56-v0.67) pin `verdant_kernel/*.py` by code identity: they must be re-frozen, or their
  manifests taught to accept the new identity explicitly. Proposal: re-freeze on the new branch
  only; the frozen artifacts on existing branches are untouched.
* Saved states from before the change need a one-way migration (full table -> deltas), or a
  format-version flag that keeps reading old events.
* Pass mark: the whole existing suite on the new branch; replay determinism (same lessons, same
  fingerprint twice); and this week's results reproduced on the 406-lesson life (promotions,
  wrong promotions 0, cues recalled) with stock decay and with `decay_mode = "bond_clock"`.

## Second life (life seed 4242, kernel seed 7), same settings
| | engine as it was | full system |
|---|---|---|
| all gate-meeting families promoted | 8/46 | 45/46 |
| short gaps / long gaps / returning | 0/15 / 0/15 / 0/5 | 15/15 / 15/15 / 5/5 |
| cues recalled exactly | 33/148 | 148/148 |
| wrong / noise-only promotions | 0 / 0 | 0 / 0 |
| ms per lesson at lesson 406 | 3,399 (full records) | 1,924 (changes-only) |

## Does it now remember too much? (`run_observer_should_fade.py`, life seed 9001, final organisms)
| | engine as it was | full system |
|---|---|---|
| bonds among random noise pairs | 8 | 8 |
| met once: families with a living bond / cues recalling a partner | 4/28, 0/84 | 7/28, 3/84 |
| met twice: | 3/14, 0/42 | 9/14, 15/42 |
| met 5 times in one setting: | 2/6, 0/18 | 6/6, 12/18 |
Noise is not held more; one-offs still fade. Things met twice, or often in one setting, stay
recallable from the living web (never promoted). Whether a mind should keep those weak,
unearned memories is a design decision, not settled by this measurement.
