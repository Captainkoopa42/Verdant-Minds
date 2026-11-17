# Moving the bond clock into the engine: design v0 (PROPOSED, not implemented)

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
