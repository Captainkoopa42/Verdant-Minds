# Thermodynamic Homeostasis Experiment v1

Branch: `test/thermodynamic-homeostasis-v1`

Parent: `test/dependency-evidence-v1` at `b95f13f52f29564fae3974370755d7159a914d5b`

## Question

Can the existing V5-X thermodynamic telemetry regulate access to learned material without deleting memory or changing semantic truth?

The first experiment separates two questions:

1. **Controller mechanism:** if a Rigid policy is deliberately applied, does historical recruitment become less dominant while current evidence remains strong?
2. **Detector validity:** when Tg is allowed to operate normally, does it enter Rigid/Chaotic at moments where the bounded controller is useful?

These must not be conflated.

## Safety boundary

Soft-homeostasis v1 does **not** change:

- canonical evidence;
- concepts, relations, claims, contradictions, or revisions;
- stored P/Q structures;
- ECWF policy stored in the kernel;
- compilation policy stored in the kernel;
- plasticity policy or plastic association strength;
- checkpoint lineage.

It changes only a temporary `DevelopmentalCycleConfig` used for the next cycle.

The previous committed thermodynamic state controls the next cycle. Tg never changes the cycle that produced Tg.

## Phase behavior

### Flexible

Identity policy. No developmental configuration changes.

### Rigid

- current evidence resource: x1.15;
- historical resonance/local-association/earned-structure resource: x0.70;
- association recall threshold: +0.08;
- earned-structure trigger requirement: +1 member;
- resonance top-k inspected: +1;
- resonance commit limit: unchanged;
- persistence request: -1, bounded to the existing minimum.

The intent is to reduce entrenched historical recruitment while permitting the system to inspect an extra alternative without committing more historical material.

### Chaotic

- current evidence resource: x1.10;
- historical resources: x0.65;
- association recall threshold: +0.12;
- earned-structure trigger requirement: +1 member;
- resonance top-k: -2;
- resonance commit limit: -1;
- persistence request: -1.

The intent is to narrow recurrent activation while anchoring the foreground in present evidence.

## Deliberately deferred

`plasticity_learning_multiplier` and `plasticity_decay_multiplier` remain in the policy schema but are not applied in v1.

No profile vectors, graph edges, plastic associations, or P structures are decayed or deleted by thermodynamics in this experiment.

That is a separate causal experiment and should only be attempted after the access-control test is characterized.

## Paired checkpoint probe

`run_v5x_thermodynamic_homeostasis.py` accepts a native VDK checkpoint.

It produces two experiments.

### Forced-Rigid A/B

Each probe reloads the same checkpoint twice. One copy uses the ordinary developmental configuration. One uses the Rigid soft-homeostasis configuration.

This isolates the **mechanism** from Tg itself.

The default probes are selected to exercise the overlaps visible in the cycle-903 "Test Test Test" checkpoint:

- `load`;
- `switch + load`;
- `controller`;
- `pressure_sensor + controller`;
- `actuator`;
- `actuator + sensor`;
- `foundation + frame`.

Missing labels are skipped rather than invented.

### Automatic A/B sequence

Two copies begin from the same checkpoint.

- control: thermodynamic observation only;
- experimental: observation + soft homeostasis.

The first cycle is necessarily identical because no previous Tg exists. Each later experimental cycle records the previous Tg/phase and the effective temporary config used for that cycle.

## Interpretation

A useful result is not simply "fewer P activations."

The controller should reduce unsupported historical intrusion while preserving supported partial recall. For example:

- `load` alone may become more conservative;
- `switch + load` should still be able to recruit an electrical structure when enough members match;
- `foundation + frame` should preserve the old foundation structure;
- automatic Tg control should only be credited if its phase transitions correlate with useful changes rather than arbitrary suppression.

If forced-Rigid improves recruitment but automatic Tg never invokes it at useful moments, the controller mechanism may be sound while Tg is not yet a useful detector.

If automatic Tg invokes control at the wrong moments, the phase model—not the access-control mechanism—is the next target.
