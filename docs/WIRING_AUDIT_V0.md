# Wiring audit v0: what is idle in a running life, why, and how to distribute the work

Date: 2026-11-20. Status: AUDIT + PLAN, no code changed. Source: the live map
("Verdant, running": a static scan of 273 modules / 2,656 functions plus a recording of six
scenarios on a 140-lesson organism with the senses stack) and a reading of every idle package,
its users and its own reports.

## The finding that started it

In one recorded lesson the kernel and the acceleration sidecar make 98.9% of all calls
(acceleration 89.1%, kernel 9.8%); about 97% of all calls are checks, fingerprints and copies.
The developmental stages themselves barely work: workspace 56 calls, plasticity 36, structures 28,
the development pipeline 16. Inside the kernel, 14,660 of 17,881 calls are checks; the top two
are `_validated_evidence_refs` (6,652) and `canonical_json_bytes` (5,847), and concept addresses,
which never change, are re-derived and re-validated 984 times. 19 of 38 engine and sidecar
packages did not run at all.

## Correction to the first reading

"Never ran" means "not in the long-life runner used for the recent observers", not "unused in
Verdant". The official cultivation runner (`run_verdant_cultivation.py`, README "Hand-driven
cultivation runner"), the Workbench adapter and the Milestone 19 benchmark use compilation,
interaction, hierarchy and refolding. They are operated by a teacher's commands or a scripted
order, never by the organism.

## What each idle part is (from its code, users and reports)

| Part | What it does | Who drives it today | Kind |
|---|---|---|---|
| Council promotion of P (`verdant_structures.promote`, `verdant_governance` Data/Forefront/Ethics Kings) | Turns an eligible recurring pattern into an earned structure | A script every 20 lessons; the teacher's `promote` | Ready, hand-driven |
| Compilation, M15 (`verdant_compilation`) | An earned structure stands in for its parts; ablate/restore 1 -> 15 -> 1 | Recall (`sidecar_recall`), teacher's `compile` | Partly in the loop |
| Interaction, M16 (`verdant_interaction`) | Earned structures matched by relational shape, not label | Teacher's `interact`; M19 script | Ready, hand-driven |
| Hierarchy, M17 (`verdant_hierarchy`) | Structures of structures (Q); work 8 -> 3 on an unseen case | Teacher's `observe_hierarchy`, `promote_hierarchy`; M19 script | Ready, hand-driven |
| Refolding, M18 (`verdant_refolding`) | A structure revises or splits under recurring contradiction, history kept | Teacher's `challenge`, `refold`; M19 script | Ready, hand-driven |
| Thermodynamic governor (`verdant_thermodynamics`, `verdant_development/v5x.py`) | Tg, rigid/flexible/chaotic with hysteresis, next-cycle policy only | V5x runners (an experiment); detector study found the V4 Tg law tracks input wordiness | Built, needs real inputs (roadmap Stage C) |
| Shards (`verdant_shards`) | Specialised regions: formation and routing, each through Council proposals | Its demo only | Built, never used in a life |
| Sleep (`sidecar_rehearsal`) | Replays recent memory through the beat, bond clock paused | A count (every 8 experiences) | Running, clock-driven |
| Obligation substrate v0.67 (`verdant_obligations`, 36,757 lines; with the `verdant_math` teaching line) | Dependency gaps, contradictions, prediction failures; Stalled -> MayWake -> Recheck_Pending -> Reopened with hashed stall certificates and reopen predicates; an attention portfolio with an exploration reserve; a copy-on-write counterfactual runtime with a simulation budget; hypotheses with mandatory null/defer arms | Its own preregistered experiments | Deliberately firewalled: "hard absence of intervention authority" |
| Cognitive pockets (`verdant_pockets`) | Read-only pocket cultivation and corroboration | Its own experiments | Experiment |
| Language, claims, ECWF text pipeline | Grammar teaching front end, claim bridge, a stand-alone cue -> resonance path | Workbench, demos, the math line | Ways in, not parts of the beat |
| Motor | Removed on purpose; `FUTURE_MOTOR_IMPLEMENTATION_DESIGN.md` requires an independent safety controller | Nobody | Removed by decision; keep removed |

The obligation substrate already contains most of what roadmap Stage D (open propositions, cold
storage, retrieval, reward through the Council) planned to build, at a far higher standard of
rigour. Its latest result is negative and honest: retained partial evidence was reused, fresh
correct-answer transfer was falsified, and the line was paused.

## Where each belongs in the engine

* Fast loop (each experience): the beat as now; compilation's operand path (earned structures
  already enter the workspace).
* Quiet loop (nothing new arriving, or pressure building): sleep by state, not count; imagination
  and recall turning into open questions.
* Slow loop (evidence piling up): Council promotion of P when patterns are eligible; interaction
  among earned structures; hierarchy observation and Q promotion; refolding when recorded tension
  against a structure recurs (the tension record from `sidecar_ring` is the natural trigger for
  `record_structural_challenge`).
* Governor: the thermodynamic controller, fed by measured unknown share, tension and surprise.
* Distribution: shards, formed when the field grows crowded or families separate (the V4 basin
  budding idea), each region with its own routing.
* Research substrate (stays firewalled until William decides): obligations observing the live
  organism read-only, proposing, never committing.

## Ranked plan (each step opt-in, gated by: exact replay, full suite, 400-lesson life
145/148 kept, 43/46 promoted, 0 wrong, plus its own preregistered test)

1. **The Council convenes itself.** Replace "every 20 lessons" with a state trigger: eligible
   candidates waiting. Smallest change; the first lever the organism pulls.
2. **Tension calls for refolding.** Recurring tension against a promoted structure's members
   becomes a structural challenge; refolding inspects stable / revise / split / unresolved, and
   only the Council commits. Connects Stage A to Milestone 18.
3. **Structures meet structures.** After promotions, interaction runs among earned structures;
   hierarchy observes; the Council decides on Q. Milestones 16-17 in a life for the first time.
4. **Sleep by state.** Rehearse when consolidation pressure (recent unconsolidated bonds,
   workspace load) is high, not every 8.
5. **The governor.** Roadmap Stage C through the existing V5x pipeline, with the new inputs.
6. **Obligations, read-only** (needs William's decision): the substrate watches the live organism
   and proposes; replaces building Stage D anew. Granting it any authority is a separate decision.
7. **Shards for distribution.** Specialised regions so the work spreads.
8. **The kernel diet.** First, remember what is already checked (fixed addresses, evidence
   already validated) to cut redundant work without weakening the audit; then let each part own
   its state and checks, with the organism's fingerprint composed from the parts' fingerprints.

Expected risk: steps 2-3 change what a life learns (that is the point); the 400-lesson gate
measures whether old results hold, and new tests must show the stages fire for the right
reasons, never on noise.
