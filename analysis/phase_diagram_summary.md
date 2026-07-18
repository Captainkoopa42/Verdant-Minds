# Phase Diagram Summary

## Scope

This summary reflects the Verdant-side configurable ethomorphic wrapper introduced in this branch. No files in `ethomorphic/` were modified. The implementation makes the following axes sweepable from `verdant/` and the cultivation/analysis tooling:

- `cognitive_dims`
- `ethical_dims`
- `entropy_window_min`
- `entropy_window_max`
- `magnitude_threshold`
- `adaptive_rate`
- `seed_count`
- `pressure_threshold`

Validation sweeps executed for this branch:

1. `cognitive_dims ∈ {2, 5, 8}`
2. `entropy_window_min ∈ {0.3, 0.8, 1.5}`

Each configuration used **40 cycles × 3 local-provider seeds**.

## 1. Which parameters affect onset_cycle and by how much

### Measured in this branch

- **`cognitive_dims`**: no measured onset-cycle shift across the tested range.
  - onset_cycle mean: `9.0` at 2, 5, and 8 dimensions
  - total shift: `0.0`
- **`entropy_window_min`**: no measured onset-cycle shift across the tested range.
  - onset_cycle mean: `9.0` at 0.3, 0.8, and 1.5
  - total shift: `0.0`

### Not yet executed, but now sweepable

- `ethical_dims`
- `entropy_window_max`
- `magnitude_threshold`
- `adaptive_rate`

These axes are implemented in the tooling and ready to run, but this summary does not claim empirical effects for them yet.

## 2. Which parameters affect onset_T_g

For both executed axes, onset temperature was invariant within the sampled runs:

- **`cognitive_dims`**: onset_T_g mean = `0.5725`
- **`entropy_window_min`**: onset_T_g mean = `0.5725`
- observed sample std across seeds: `0.00648`
- measured shift across tested values: `0.0`

### Interpretation

This is consistent with the hypothesis that onset is phase-conditioned: the system keeps crossing the same critical region even when the dimensionality and the lower entropy guard are changed within the tested range.

## 3. Which parameters are not sweepable and why

Within the new Verdant-side wrapper, **none of the requested axes are locked**:

- Constructor-pass-through: `num_cognitive_dims`, `num_ethical_dims`, `num_facets`, `adaptive_rate`, `feedback_factor`
- Post-init override: `initial_amplitude`
- Verdant runtime wrapper: `emergence_entropy_min`, `emergence_entropy_max`, `emergence_magnitude_threshold`, `co_activation_threshold`, `connection_weight_threshold`, `max_connections_per_concept`

The implementation choice for each axis was:

- **Option A / constructor arg** when upstream `ECWFCore` already accepted the parameter
- **Option B / post-init override** for `initial_amplitude`
- **Verdant wrapper/hook** for bridge and emergence thresholds that are hard-coded upstream

## 4. Shape of the F_c = 0 surface from available data

Based on the currently executed sweeps, the observable projection of the `F_c = 0` surface is locally flat along:

- `cognitive_dims`
- `entropy_window_min`

A first-order approximation from the sampled region is:

- `T_g,critical ≈ 0.5725`
- `onset_cycle ≈ 9`

for all tested values on those two axes.

## 5. Prediction: how to target onset at cycle 5 instead of 9

### Evidence-backed answer

From the currently executed sweeps, **neither tested axis moves onset toward cycle 5**.

### Best next experiments

The next parameters to test are:

1. `magnitude_threshold` — most directly tied to emergence admission
2. `adaptive_rate` — changes ECWF adaptation dynamics
3. `ethical_dims` / `entropy_window_max` — likely secondary structural effects

Operationally: lower `magnitude_threshold` and/or increase `adaptive_rate` are the most plausible next levers, but this remains a prediction until those sweeps are run.

## 6. Prediction: how to target 5 forges instead of 3

Using onset emergent-count as the closest available proxy, the tested axes do **not** show a strong qualitative basin-count change at onset.

What *does* change modestly is onset emergent-count under `cognitive_dims`:

- `cognitive_dims=2` → onset emergents ≈ `10.33`
- `cognitive_dims=5` → onset emergents ≈ `13.0`
- `cognitive_dims=8` → onset emergents ≈ `12.67`

So if “forges” tracks local combinatorial richness, **increasing cognitive dimensions appears mildly helpful**, but we do not yet have direct evidence that it yields 5 stable forges/basins.

## 7. Developmental specification language sketch

A preliminary DSL can now be expressed in terms of sweepable Verdant-side parameters:

```yaml
developmental_spec:
  desired_onset_cycle: 9
  desired_onset_t_g: 0.572
  ecwf:
    cognitive_dims: 5
    ethical_dims: 5
    adaptive_rate: 0.1
    feedback_factor: 0.05
    initial_amplitude: 1.0
  emergence:
    entropy_window: [0.3, 3.0]
    magnitude_threshold: 0.15
    co_activation_threshold: 0.2
  connectivity:
    connection_weight_threshold: 0.0
    max_connections_per_concept: null
```

### Current rule fragments

- If the goal is **preserve canonical onset**, both tested axes can vary while keeping:
  - `onset_cycle ≈ 9`
  - `onset_T_g ≈ 0.5725`
- If the goal is **increase onset combinatorics without shifting the phase point**, a larger `cognitive_dims` value is a reasonable candidate.
- If the goal is **shift onset earlier/later**, the next DSL clauses should target `magnitude_threshold` and `adaptive_rate`, which are now sweepable.

## Executed sweep results

### cognitive_dims

| value | onset_cycle_mean | onset_T_g_mean | onset_memory_mean | onset_emergent_mean |
|---|---:|---:|---:|---:|
| 2 | 9.0 | 0.5725 | 132.00 | 10.33 |
| 5 | 9.0 | 0.5725 | 134.67 | 13.00 |
| 8 | 9.0 | 0.5725 | 134.33 | 12.67 |

### entropy_window_min

| value | onset_cycle_mean | onset_T_g_mean | onset_memory_mean | onset_emergent_mean |
|---|---:|---:|---:|---:|
| 0.3 | 9.0 | 0.5725 | 134.00 | 12.33 |
| 0.8 | 9.0 | 0.5725 | 134.00 | 12.33 |
| 1.5 | 9.0 | 0.5725 | 134.00 | 12.33 |
