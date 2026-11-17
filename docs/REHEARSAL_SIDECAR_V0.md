# Rehearsal sidecar v0 (opt-in, IMPLEMENTED-EXPERIMENTAL)

Port of the V0-V4 `dream_cycle` idea onto the V5 heartbeat, as a sidecar. No file under
`verdant_*` is changed; the frozen math manifests and the Workbench engine identity are
untouched. Nothing runs unless `sidecar_rehearsal` is imported and constructed.

## What it does
Every Nth committed experience, `RehearsingDevelopmentPipeline` runs one staged beat:
workspace cycle with `RECALLED_EVIDENCE` items -> plasticity cycle -> commit.
Each item re-presents one remembered experience (its observation evidence id and the
concepts of its fading bonds). `apply_experience`, resonance commit and structure
observation are not run.

## Boundaries (enforced, tested in `tests/test_rehearsal_sidecar.py`)
* deterministic: selection and trigger are pure functions of canonical state;
* creates no evidence, concept, relation, claim or processed experience;
* changes no structure candidate (occurrences, contexts, quality stay experience-only);
* creates no plastic association (item score sits between the policy's reinforcement
  and creation thresholds; a staged beat that creates one is discarded);
* bonds are chosen by OBSERVATION evidence count, never by rehearsal count;
* bonds that have died are not resurrected; a horizon stops rehearsal of what has not
  really recurred.

## OBSERVED (seed 2301, this environment)
* A family taught every 10th lesson: baseline counts 3 candidate occurrences from 5
  exposures (bond is 0.264 after the 2nd exposure, under the 0.28 member threshold);
  with `min_real_exposures=1` the 2nd exposure lands at 0.318 and 4 occurrences are counted.
  The candidate still tracks: cohesion stays under 0.38.
* Controls pack (183 lessons), baseline vs `min_real_exposures` 2 and 1:
  no group changed outcome. gate_pass 0/6 and spaced 0/4 eligible in all three arms;
  under_exposed, single_context, pairs_only and distractor controls still correctly
  refused. 18-21 beats committed, 89-100 experiences rehearsed.

## What that shows
The sidecar is safe and does not help yet. Two causes, both measured:
1. A candidate occurrence is only counted when member bonds are already >= 0.28 at
   that exposure, so widely spaced lessons lose their first one or two occurrences.
2. Every plasticity cycle decays every bond, so each sleep beat costs all non-rehearsed
   bonds one decay step, and a rehearsal lift is about +0.06. With ~30 families and
   5 items per beat, rehearsal cannot hold bonds above the gates.

## MISSING / decisions for the owner (engine-level, not done here)
* a rehearsal beat that does not tick global decay;
* or decay on a clock other than "every plasticity cycle";
* or counting recurrence from experience rather than from bond strength at that moment.

## Follow-up: `sidecar_recurrence` (opt-in, IMPLEMENTED-EXPERIMENTAL, no dedicated tests yet)
`ExperienceRecurrenceStructurePipeline`, injected through
`VerdantDevelopmentPipeline(structures=...)`, admits a living bond to candidate membership
when both of its concepts are present in the current experience, whatever its strength.
All promotion gates are unchanged.

OBSERVED (controls pack, seed 2301): candidates 14 -> 29. Every gate_pass and spaced
family now has an exact candidate with 5 of 5 occurrences counted, evidence diversity
1.0 and context stability 1.0. None is eligible: internal cohesion is 0.17-0.31 against
0.38 and reconstructability 0.41-0.56 against 0.50. Negative controls are refused by the
gate that should refuse them (under_exposed: 2 occurrences, evidence 0.5; single_context:
context 0.5). The remaining block for spaced learning is bond strength under decay alone.

## Follow-up: `sidecar_bond_clock` (opt-in, IMPLEMENTED-EXPERIMENTAL, 3 tests)
`BondClockPlasticityPipeline`, injected through `VerdantDevelopmentPipeline(plasticity=...)`.
Its `inspect` is the stock method with the one decay line changed; a test fails if stock drifts.
Rule: decay rate / real exposures (OBSERVATION evidence, capped at 5); bonds with >= 3 real
exposures do not decay below 0.10; rehearsal beats apply no time decay.
Tested: a single-exposure bond fades exactly as stock; runs are deterministic; evidence and
concepts are identical to stock.

## OBSERVED: the three sidecars stacked (controls pack, seed 2301, default settings, no tuning)
| arm | gate_pass eligible | spaced eligible | spaced cohesion (bar 0.38) | refused controls | policy checks |
|---|---|---|---|---|---|
| stock | 0/6 | 0/4 | no candidate | 12/12 | 14/20 |
| + recurrence | 0/6 | 0/4 | 0.20 | 12/12 | 14/20 |
| + bond clock | 0/6 | 0/4 | 0.33 | 12/12 | 14/20 |
| + rehearsal (min 1) | 2/6 | 1/4 | 0.35-0.38 | 12/12 | 16/20 |
No distractor-only candidate became eligible in any arm. In the last arm two "bridged"
families also became eligible and two more sit inside one larger eligible five-member
candidate (exploratory group; whether that merge is wanted is undecided).
One seed. Engine test suites were not rerun because no engine file changed.
