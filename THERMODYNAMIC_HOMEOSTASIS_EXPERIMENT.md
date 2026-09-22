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

## Prepared detector and Workbench infrastructure (not yet validated)

A new `run_v5x_thermodynamic_detector_study.py` runner accepts **one or more**
VDK checkpoints. The existing cycle-903 file is a development calibration
checkpoint; further checkpoints are held-out material only if they are selected
before inspecting the new detector results. Missing concepts are skipped.

Its case matrix contains the seven original probes plus additional single,
multi-member, and broad-structure negative controls. Each isolated probe is
run from the same checkpoint, with:
- ordinary observer baseline;
- unchanged soft homeostasis v4;
- score-only, support-only, and neither-gate resonance ablations for four
  declared probes;
- text-metadata sensitivity controls with **1 versus 60 neutral tokens**,
  holding explicit concept labels, feature vector, event identity and payload
  hash constant across fresh forked runs.

Both token conditions use the same V4-compatible text adapter. The intervention
changes command metadata and may change downstream evidence identities: inspect
actual effects rather than assuming field dynamics are identical.

A separate three-step stream for `actuator` and `foundation + frame` tests
actual previous-cycle lag using two V5X pipelines, with the Tg formula and
phase boundaries untouched. The report separates post-cycle Tg and post-cycle
access observations from the previous Tg actually available at decision time.

The runner records its checkpoint hashes, chosen cases, ablation configurations,
outcomes, skipped labels, raw phase/components and actual A/B fingerprints.
It does **not** compute semantic accuracy, estimate election-style probabilities,
infer truth labels from P count, or claim generalization from the seven probes.

### Launch from repository root (PowerShell)

Use the interpreter in the user's already-created original V5X virtual
environment with the isolated thermo worktree as the current directory.
Write results **outside** the Git worktree.

```powershell
$Repo = "$env:USERPROFILE\Verdant-Minds-V5X-Test"
$Lab = "$env:USERPROFILE\Verdant-Minds-Thermo-Test"
$Results = "$env:USERPROFILE\Verdant-Thermo-Results"
Set-Location $Lab
New-Item -ItemType Directory -Force -Path $Results | Out-Null
& "$Repo\.venv\Scripts\python.exe" -m pytest -q tests/test_thermodynamics_phase.py tests/test_ecwf_phase.py tests/test_development_phase.py tests/test_thermodynamic_detector_study.py
if ($LASTEXITCODE -ne 0) { throw "Focused tests failed" }
& "$Repo\.venv\Scripts\python.exe" .\run_v5x_thermodynamic_detector_study.py "$env:USERPROFILE\Desktop\Test Test Test.vdk" --output "$Results\thermodynamic_detector_study_v1.json"
```

To add held-out checkpoint(s), append each additional path BEFORE `--output`.
No checkpoints are rewritten by the study runner.

### Workbench groundwork

The fork also adds durable `THERMODYNAMIC_OBSERVED` and
`THERMODYNAMIC_CONTROL_APPLIED` Workbench events and a read-only
**Thermodynamics** page separating raw measurement from policy authority.
The Workbench worker retains observer-only behavior by default. This page
does not enable a governor or turn a VDK into a thermodynamic-state store.

Full Workbench governance controls and control-state continuity on save/reopen
remain blocked on detector validation, tests, and a durable policy state
contract. Do not present the page as a finished homeostasis switch.


## Detector study v1: observed result and consequence

Source: `thermodynamic_detector_study_v1.json`, checkpoint SHA-256
`06414a5b3d5c9783746d843889ea8780a57a33023eac3c9dd58447b707e55676`.

**18 distinct, intentionally selected cue sets**, each tested with one and
60 neutral text tokens, yielded 36 matched A/B case pairs. These are NOT
36 independent samples, because all cases reuse the same checkpoint and
the 60-token cases repeat the same cue labels and feature vectors.

For each text condition, baseline admitted 29 P structures whose current
input covered less than half their members, across 16 of 18 cue sets.
Forced homeostasis v4 admitted **zero** below-half-match Ps across these
cases. This is a structural access proxy, not independent semantic
correctness: the governor explicitly implements the same 0.50 overlap
floor, so removing below-half-match Ps is an expected sanity check,
not proof of a detector.

**Tg is not currently an effective automatic trigger for that proxy.**
Every one-token baseline case was Flexible, including all 16 cases with
below-half-match P recruitment. All six cycles in the two existing short
lag streams remained fingerprint-identical across observer and controlled
forks: Tg never engaged a non-identity policy. The previous-cycle Tg
provenance was recorded, but no actual threshold-crossing intervention
was exercised.

The matched verbosity control is especially important: switching from
1 to 60 neutral tokens raised **every** baseline Tg value by exactly
0.0885 while leaving P admission and the measured access outcomes
unchanged for all 18 cues. Three 60-token baseline cases entered raw
Chaotic (actuator; actuator+sensor; actuator+controller+sensor), while
the same cues with one token remained Flexible. This is a controlled
demonstration of sensitivity to input-token complexity, not proof that
verbosity alone will always force a phase transition across different
checkpoint states or longer histories.

### Resonance gate ablation

In the `controller` development probe, the two weakly supported
resonant intrusions (`target_point`, `forward_axis`) both have resonance
scores above the 0.32 score floor but have zero learned local support
from `controller`. Both entered under *score-only* and *neither-gate*
ablation; neither entered under *support-only* or *both-gate* control.
Thus the local-support floor, **not the 0.32 score floor**, accounts for
removing this specific leak on this checkpoint. Both-gate policy is kept
frozen pending tests of whether the score floor independently helps or
blocks contextually useful recall elsewhere.

### Next falsification: real lag with a high-token pulse

`run_v5x_thermodynamic_lag_stress.py` is a new, separate
**development-only** study. It uses the same checkpoint-forking pattern
to exercise real automatic previous-cycle control on the existing
V4-compatible Tg and the frozen homeostasis v4 policy. The four
preselected short streams test:

- high-token actuator followed by short actuator and then supported
  foundation/frame;
- high-token actuator/controller/sensor followed by a supported
  foundation/frame and actuator/sensor;
- a high-token but context-supported foundation/frame negative control;
- a short-token actuator negative control.

The report checks that the controller's source Tg is exactly the
**previous controlled fork's** Tg, not the observer fork's or the current
cycle's Tg. It shows whether the high-token pulse causes a non-identity
Chaotic intervention **one cycle later**, what happens to contextual P
recall, and whether control switches back after Tg returns to Flexible.
The result may reveal overreaction to irrelevant verbosity; it has
not been run yet and no outcome is presumed.

The Workbench observer remains the default. Do not expose automatic
behavioral authority as a user-facing toggle merely because this study
causes a phase transition: detector specificity and saved controller
state are separate gates.

### Run lag stress without rerunning the 36-case calibration

```powershell
$Repo = "$env:USERPROFILE\Verdant-Minds-V5X-Test"
$Lab = "$env:USERPROFILE\Verdant-Minds-Thermo-Test"
$Results = "$env:USERPROFILE\Verdant-Thermo-Results"
Set-Location $Lab
New-Item -ItemType Directory -Force -Path $Results | Out-Null
& "$Repo\.venv\Scripts\python.exe" -m pytest -q tests/test_thermodynamic_lag_stress.py
if ($LASTEXITCODE -ne 0) { throw "Lag tests failed" }
& "$Repo\.venv\Scripts\python.exe" .\run_v5x_thermodynamic_lag_stress.py "$env:USERPROFILE\Desktop\Test Test Test.vdk" --output "$Results\thermodynamic_lag_stress_v1.json"
```


## Lag stress v1: observed N-to-N+1 results

Source: `thermodynamic_lag_stress_v1.json`, cycle-903 checkpoint SHA-256
`06414a5b3d5c9783746d843889ea8780a57a33023eac3c9dd58447b707e55676`.
These are four deliberately selected three-cycle developmental sequences, not
held-out validation.

| Sequence | First-cycle Tg | Second-cycle action | Second-cycle outcome | Third-cycle behavior |
| --- | ---: | --- | --- | --- |
| Long actuator -> short actuator -> foundation/frame | 0.632193, Chaotic | Chaotic from previous Tg | 4 low-overlap Ps in observer; 0 Ps in controlled | Flexible identity policy; supported foundation P survives in both |
| Long actuator/controller/sensor -> foundation/frame -> actuator/sensor | 0.633384, Chaotic | Chaotic from previous Tg | Supported foundation P survives in both, with resource 0.06 observer vs 0.039 controlled | Flexible identity policy; broad low-context P intrusion returns on actuator/sensor |
| Long supported foundation/frame -> actuator -> foundation/frame | 0.539024, Flexible | Identity policy | Four low-overlap Ps in both arms | Arms remain fingerprint-identical |
| Short actuator -> short actuator -> foundation/frame | 0.543693, Flexible | Identity policy | Four low-overlap Ps in both arms | Arms remain fingerprint-identical |

No previous-cycle controller action occurs on first-cycle exposure; the second
cycle records the **previous controlled fork's** Tg exactly. The Chaotic
pulse returns to Flexible on the following short cycle; effective config
returns to identity but fork fingerprints **remain different** once a previous
controlled developmental cycle has changed canonical state. Thus policy reset
is not rollback and must not be described as restoring organism equality.

**Causal lesson:** a 60-token neutral sentence with actuator-related
content can induce a Chaotic Tg and therefore apply reduced historical
access to a **different next cue**. That control can suppress four weakly
supported Ps if the next cue is actuator, but it also attenuates the
legitimate foundation/frame P's allocated resource from 0.06 to 0.039
when the next cue is foundation/frame. In this tested case the supported P
remains admitted, so the data do **not** establish catastrophic forgetting or
loss of supported recall. They establish an unnecessary intervention whose
trigger is confounded by preceding input verbosity.

Meanwhile a repeated short actuator cue retains four low-context Ps and
never triggers the governor: the existing Tg detector **misses** the same
structural pressure without the 60-token pulse.

**Decision:** keep V4 access policy frozen and Workbench behavioral authority
OFF. Tg can remain useful as an observation of the V4-compatible
complexity/entropy formula, but the evidence does not justify treating its
Rigid/Chaotic phase as a validated detector for contextual memory intrusion.

### Next architectural experiment: independent contextual-access-pressure telemetry

Do not silently reinterpret, subtract terms from, or rename Tg to make it
agree with handpicked examples. Add a separate, explicitly named,
observer-only access-pressure measurement with:
- cue coverage of eligible learned P structures before workspace admission;
- weak-overlap and strong-overlap candidates separately;
- admitted-structure fractions, budget pressure and resource allocation;
- learned-local and resonance support traces;
- original Tg/components, raw phase, and previous-cycle provenance beside it;
- no authority to change canonical memory, plasticity or runtime config.

Pre-admission pressure must be measured **before the access gate acts**, or
successful suppression would erase the measurement that justified control.
This measurement must also be stress-tested against legitimate broad recall,
larger/new checkpoints, missing concepts and within-stream changes. The
original V4 Tg remains a distinct signal for complexity/metabolic
state, not a surrogate semantic correctness label.

Full experimental control in the Workbench remains gated on a detector with
demonstrated specificity and on durable save/reopen of its phase history.


### Prepared pre-admission shadow measurement (not yet run)

The fork now also implements
`verdant_thermodynamics.inspect_access_pressure(kernel, cue_concept_ids)`.
This is a deterministic, observer-only snapshot of available learned P
structures with overlap to the incoming cue **before** the current
experience is admitted. It distinguishes zero-overlap structures, weak
positive-overlap structures below 0.50 member coverage, and strong
member-overlap structures at or above 0.50. These are membership
descriptors, not truth judgements, nor predictions of which workspace
candidates will be admitted.

`run_v5x_thermodynamic_lag_stress.py` now includes these pre-policy
measurements on **both** checkpoint forks, as well as the original
post-policy Tg and access observations. The report schema advances to
`verdant.v5x.homeostasis_lag_stress.v2`. This lets us distinguish:
candidate P pressure at cue arrival, downstream observed P admission,
previous-cycle Tg and intervention effects. It does not yet activate an
access-pressure controller.

When a cue contains concepts absent from the pre-cycle checkpoint
(for example a newly taught concept), the pre-pressure measurement is
`null` rather than silently treating partial cue membership as a
complete measurement. This distinction matters for new curriculum data.
The shadow measurement's behavior and test suite still require local
execution before use as a validated signal.
