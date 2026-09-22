# Thermodynamic Homeostasis Experiment

Branch: `test/thermodynamic-homeostasis-v1`

Parent: `test/dependency-evidence-v1` at `b95f13f52f29564fae3974370755d7159a914d5b`

## Question

Can V5-X thermodynamic telemetry regulate **access** to learned material without deleting memory or changing semantic truth?

The experiment deliberately separates two questions:

1. **Controller mechanism:** if a conservative access policy is deliberately applied, does unsupported historical recruitment decrease while context-supported recall survives?
2. **Detector validity:** when Tg operates normally, does its phase state invoke that controller at moments where the controller is actually useful?

These questions must not be conflated.

## Safety boundary

Soft homeostasis does **not** change:

- canonical evidence;
- concepts, relations, claims, contradictions, or revisions;
- stored P/Q structures;
- ECWF policy stored in the kernel;
- compilation policy stored in the kernel;
- plasticity policy or plastic association strength;
- checkpoint lineage.

It changes only a temporary `DevelopmentalCycleConfig` used for the next cycle.

The previous committed thermodynamic state controls the next cycle. Tg never changes the same cycle that produced Tg.

Plasticity learning/decay multipliers remain explicitly deferred.

## Hysteretic control phase

Raw V4-compatible Tg telemetry remains unchanged and still reports:

- Rigid below 0.4;
- Flexible from 0.4 through 0.6;
- Chaotic above 0.6.

Behavioral control uses wider stateful boundaries so tiny threshold crossings do not flap policy every cycle:

- enter Rigid below 0.38;
- leave Rigid at or above 0.42;
- enter Chaotic above 0.62;
- leave Chaotic at or below 0.58.

The raw measured phase and the hysteretic control phase are both recorded.

## Current access policy: homeostasis v4

### Flexible

Identity policy. No developmental configuration changes.

### Rigid

The current Rigid policy is intentionally conservative and nonsemantic:

- current evidence resource: x1.15;
- historical resonance/local-association/earned-structure resource: x0.70;
- association recall threshold: +0.08;
- earned-structure trigger requirement: +1 member;
- earned-structure trigger fraction floor: 0.50;
- resonance score floor: 0.32;
- resonance local-support floor: 0.32;
- resonance top-k: unchanged;
- resonance commit limit: unchanged;
- persistence request: -1, bounded to the existing minimum.

The **trigger fraction** asks how much of a learned P structure is actually represented by the present cue. A two-member match therefore has different contextual support for a 3-member P (2/3) versus a 5-member P (2/5).

The **resonance local-support floor** requires a resonant candidate, during Rigid control, to have a sufficiently strong learned direct plastic association to at least one concept in the present experience. This is an access gate, not a semantic truth rule.

### Chaotic

Chaotic remains narrower:

- current evidence resource: x1.10;
- historical resources: x0.65;
- association recall threshold: +0.12;
- structure trigger requirement: +1 member;
- structure trigger fraction floor: 0.60;
- resonance score floor: 0.35;
- resonance local-support floor: 0.35;
- resonance top-k: -2;
- resonance commit limit: -1;
- persistence request: -1.

## Why the policy changed

Early forced-Rigid probes showed that a one-member structure trigger allowed an ambiguous cue such as `load` to recruit multiple unrelated learned P structures.

Requiring two members solved the single-cue intrusion but treated a 2/3 match and a 2/5 match as equivalent. The v3 checkpoint probe demonstrated that a 0.50 proportional trigger cleanly preserved the 3-member pressure and actuator structures while suppressing the broader 5-member cross-domain structures.

The same v3 probe showed a remaining failure mode: after P structures were suppressed for the single `controller` cue, `target_point` and `forward_axis` could enter through resonance. The v4 local-support gate addresses that specific *class* of failure by requiring current learned corroboration rather than merely raising a global resonance score threshold.

## Paired checkpoint probe

`run_v5x_thermodynamic_homeostasis.py` accepts a native VDK checkpoint.

It produces two experiments.

### Forced-Rigid A/B

Each probe reloads the same checkpoint twice. One copy uses the ordinary developmental configuration. One uses the current Rigid soft-homeostasis configuration.

This isolates the **controller mechanism** from Tg itself.

Default probes:

- `load`;
- `switch + load`;
- `controller`;
- `pressure_sensor + controller`;
- `actuator`;
- `actuator + sensor`;
- `foundation + frame`.

The report now records:

- admitted earned structures, local recalls, and resonant recalls;
- P trigger members and trigger fractions;
- resonance score and learned local-support strength;
- isolated Tg/components for each paired probe;
- simple access metrics such as admitted P count and low-context P count.

### Automatic A/B sequence

Two copies begin from the same checkpoint:

- control: thermodynamic observation only;
- experimental: observation + soft homeostasis.

The first cycle is necessarily identical because no previous Tg exists. Each later experimental cycle records the previous Tg/raw phase, hysteretic control phase, and effective temporary configuration.

## Current evidence from the cycle-903 checkpoint

The access mechanism has already shown the desired structural distinction in forced tests:

- `load` alone can suppress both ambiguous Ps;
- `switch + load` preserves the 3-member electrical P while suppressing the foundation P;
- `pressure_sensor + controller` preserves the 3-member pressure P while the 5-member cross-domain P is suppressed under the proportional gate;
- `actuator + sensor` preserves the 3-member actuator/controller/sensor P while the 5-member cross-domain P is suppressed;
- `foundation + frame` preserves the old foundation P.

This supports **context-sensitive access regulation**, not merely global memory muting.

The remaining v3 resonance leak on `controller` is the target of homeostasis v4.

## Detector status

The automatic sequence through the same seven probes has so far remained Flexible, with baseline and controlled fingerprints identical.

That is a useful null result: when Tg does not request intervention, the controller leaves the organism unchanged.

It also means Tg has **not yet been validated as the detector** for the historical-overrecruitment failure mode.

The v3 telemetry suggests why this must be tested rather than assumed: in this short probe set, increased active-workspace concept count raises `c_memory`, which raises Tg. Several of the strongest over-recruitment cases therefore move Tg upward within the Flexible region rather than downward into Rigid.

The next report measures Tg on each isolated forced probe from the same starting checkpoint so the relationship between access pressure and Tg can be examined without sequential carry-over.

## Interpretation standard

A useful result is not simply "fewer P activations."

The controller should reduce **unsupported** historical intrusion while preserving context-supported partial recall.

The access governor and the Tg detector are judged separately:

- if forced conservative access works but Tg never invokes it at useful moments, preserve the access mechanism and revisit the detector;
- if Tg invokes control at the wrong moments, revise the phase/detector model rather than weakening memory;
- only after access regulation and detector validity are characterized should plasticity-coupled thermodynamic control be tested.

Thermodynamics should regulate how hard memory must compete for access to the present before it is ever allowed to regulate storage.

## Cycle-903 homeostasis v4 observed results (2026-09-22)

The v4 paired report was produced from checkpoint SHA-256
`06414a5b3d5c9783746d843889ea8780a57a33023eac3c9dd58447b707e55676`.
Seven forced-Rigid paired probes completed without failure.

| Probe | Baseline admitted Ps | Forced-Rigid admitted Ps | Observed contextual distinction |
| --- | ---: | ---: | --- |
| load | 2 | 0 | Single ambiguous concept does not recruit either 3-member P. |
| switch + load | 2 | 1 | Electrical 3-member P remains; unrelated foundation P drops. |
| controller | 3 | 0 | Local actuator/sensor associations survive; no resonant target_point/forward_axis admission. |
| pressure_sensor + controller | 3 | 1 | 3-member pressure P remains; 5-member cross-domain P drops. |
| actuator | 4 | 0 | Local controller/sensor associations survive without P over-recruitment. |
| actuator + sensor | 4 | 1 | 3-member actuator/controller/sensor P remains; broad 5-member P drops. |
| foundation + frame | 1 | 1 | Foundation P remains. |

All seven forced-Rigid probes have zero admitted P structures with trigger
fraction below 0.50; the automatic observer-only sequence still has 15 such
admissions across the seven probes. This is an **access-support proxy**, not a
semantic correctness label or a large-sample generalization claim.

The automatic observer-only and experimental-control sequences ended with
identical fingerprints
(`cf1831a52812cfac7663586804464385350a4432b5e7172e8b1ad0e7246a2f94`).
All seven measured Tg values remained Flexible, approximately 0.4526 to 0.5456.
Thus enabling the controller did not itself change the organism when no phase
requested intervention, but the Tg detector has not yet demonstrated a useful
invocation of the governor.

In the isolated `actuator` probe, baseline Tg was approximately 0.5437 with
four admitted Ps and `c_memory=0.9`; forced-Rigid Tg was approximately 0.4481
with zero admitted Ps and `c_memory=0.3`. The high-overlap baseline therefore
moves Tg **upward**, not toward the Rigid entry boundary. The same directional
pattern appears in the `actuator + sensor` probe.

The v4 report supports treating the access governor as **provisionally useful
for this checkpoint and this probe set**, not treating its detector as validated.
The v4 probe cannot attribute the `controller` resonance result independently
to the resonance score floor or the new learned-local-support floor because
both were active. A small ablation is needed before assigning that mechanism.

## Next validation gate: detector, not more access tuning

Freeze homeostasis v4 as the first candidate access-governor policy. Preserve
observer-only as the default; do not revise the V4-compatible Tg formula,
change phase thresholds to force a desired answer, or enable plasticity control.

The detector study should predeclare the hypothesized failure metric: number
and resource allocation of admitted Ps whose current-input overlap is below
0.50, reported alongside support of contextually matched 3-member Ps and the
raw workspace competition. This metric is a proxy for contextual pressure and
must not be used as an independent ground-truth semantic label.

1. Separate **pre-control state** and **post-control response**. Record raw Tg,
   Tg components, phase, admitted P counts/fractions, resource use, current
   evidence, and local/resonant recalls for both arms. Do not use post-control
   improvements as evidence that the pre-control detector was correct.
2. Test whether the previous cycle's Tg calls for control at the next cycle
   when the same failure pattern persists. One-cycle lag must be evaluated,
   not silently treated as same-cycle detection.
3. Include matched negative controls: legitimate broad structure activation,
   supported partial recall, small or empty memory, and extra input-text tokens
   that do not change the declared concept labels/feature vector. Text-token
   complexity currently scales as tokens/100, so phase sensitivity to verbosity
   must be distinguished from contextual access pressure.
4. Compare raw Tg and its components against the predeclared pressure proxy
   across more than seven deliberately selected cases, including held-out
   curriculum checkpoints. Do not infer classifier accuracy from the handpicked
   cycle-903 probes alone.
5. Independently ablate the resonance score floor and the local-support floor
   under otherwise identical forced-Rigid policy to identify which suppresses
   unsupported resonant recall and whether either rejects useful recall.
6. Only after the detector/lag study and preservation tests should the governor
   be integrated into the Workbench. Workbench requirements include explicit
   observer-only vs experimental-control authority, both raw/control phase,
   prior-cycle policy provenance, side-by-side checkpoint forks, lineage, and
   control-state continuity across save/reopen without modifying the original
   organism.
