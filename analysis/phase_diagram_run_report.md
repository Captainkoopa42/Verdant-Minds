# Phase Diagram Sweep Run Report

## Sanity check

Command:

`python -m cultivation.cli run --cycles 40 --seeds 0 --provider local --basin-routing --outdir /tmp/phase_diagram_sanity`

Detected onset (`/tmp/onset_sanity.json`):

```json
{
  "onset_cycle": 9,
  "onset_t_g": 0.5665,
  "onset_memory_size": 135,
  "onset_emergent_count": 12,
  "onset_entropy": -1.4426951601859516e-10,
  "onset_hci": 0.0,
  "pre_onset_cycles": 9,
  "total_cycles": 40
}
```

## Sweep results

### seed_count

```json
{
  "parameter": "seed_count",
  "values": [20, 30, 40, 50, 60, 70, 82, 100, 120],
  "results": [
    {"value": 20, "onset_cycle_mean": 9.0, "onset_cycle_std": 0.0, "onset_t_g_mean": 0.5725, "onset_t_g_std": 0.006480740698407866, "onset_memory_mean": 75.0, "onset_emergent_mean": 10.666666666666666, "onsets_found": 3, "seeds_run": 3},
    {"value": 30, "onset_cycle_mean": 9.0, "onset_cycle_std": 0.0, "onset_t_g_mean": 0.5725, "onset_t_g_std": 0.006480740698407866, "onset_memory_mean": 84.66666666666667, "onset_emergent_mean": 11.333333333333334, "onsets_found": 3, "seeds_run": 3},
    {"value": 40, "onset_cycle_mean": 9.0, "onset_cycle_std": 0.0, "onset_t_g_mean": 0.5725, "onset_t_g_std": 0.006480740698407866, "onset_memory_mean": 93.33333333333333, "onset_emergent_mean": 11.666666666666666, "onsets_found": 3, "seeds_run": 3},
    {"value": 50, "onset_cycle_mean": 9.0, "onset_cycle_std": 0.0, "onset_t_g_mean": 0.5725, "onset_t_g_std": 0.006480740698407866, "onset_memory_mean": 101.66666666666667, "onset_emergent_mean": 12.333333333333334, "onsets_found": 3, "seeds_run": 3},
    {"value": 60, "onset_cycle_mean": 9.0, "onset_cycle_std": 0.0, "onset_t_g_mean": 0.5725, "onset_t_g_std": 0.006480740698407866, "onset_memory_mean": 109.66666666666667, "onset_emergent_mean": 11.666666666666666, "onsets_found": 3, "seeds_run": 3},
    {"value": 70, "onset_cycle_mean": 9.0, "onset_cycle_std": 0.0, "onset_t_g_mean": 0.5725, "onset_t_g_std": 0.006480740698407866, "onset_memory_mean": 118.66666666666667, "onset_emergent_mean": 11.666666666666666, "onsets_found": 3, "seeds_run": 3},
    {"value": 82, "onset_cycle_mean": 9.0, "onset_cycle_std": 0.0, "onset_t_g_mean": 0.5725, "onset_t_g_std": 0.006480740698407866, "onset_memory_mean": 131.0, "onset_emergent_mean": 12.0, "onsets_found": 3, "seeds_run": 3},
    {"value": 100, "onset_cycle_mean": 9.0, "onset_cycle_std": 0.0, "onset_t_g_mean": 0.5725, "onset_t_g_std": 0.006480740698407866, "onset_memory_mean": 146.33333333333334, "onset_emergent_mean": 10.333333333333334, "onsets_found": 3, "seeds_run": 3},
    {"value": 120, "onset_cycle_mean": 9.0, "onset_cycle_std": 0.0, "onset_t_g_mean": 0.5725, "onset_t_g_std": 0.006480740698407866, "onset_memory_mean": 167.33333333333334, "onset_emergent_mean": 11.333333333333334, "onsets_found": 3, "seeds_run": 3}
  ]
}
```

### pressure_threshold

```json
{
  "parameter": "pressure_threshold",
  "values": [0.0001, 0.001, 0.01, 0.1, 0.5],
  "results": [
    {"value": 0.0001, "onset_cycle_mean": 9.0, "onset_cycle_std": 0.0, "onset_t_g_mean": 0.5725, "onset_t_g_std": 0.006480740698407866, "onset_memory_mean": 134.33333333333334, "onset_emergent_mean": 12.666666666666666, "onsets_found": 3, "seeds_run": 3},
    {"value": 0.001, "onset_cycle_mean": 9.0, "onset_cycle_std": 0.0, "onset_t_g_mean": 0.5725, "onset_t_g_std": 0.006480740698407866, "onset_memory_mean": 134.33333333333334, "onset_emergent_mean": 12.666666666666666, "onsets_found": 3, "seeds_run": 3},
    {"value": 0.01, "onset_cycle_mean": 9.0, "onset_cycle_std": 0.0, "onset_t_g_mean": 0.5725, "onset_t_g_std": 0.006480740698407866, "onset_memory_mean": 134.33333333333334, "onset_emergent_mean": 12.666666666666666, "onsets_found": 3, "seeds_run": 3},
    {"value": 0.1, "onset_cycle_mean": 9.0, "onset_cycle_std": 0.0, "onset_t_g_mean": 0.5725, "onset_t_g_std": 0.006480740698407866, "onset_memory_mean": 134.33333333333334, "onset_emergent_mean": 12.666666666666666, "onsets_found": 3, "seeds_run": 3},
    {"value": 0.5, "onset_cycle_mean": 9.0, "onset_cycle_std": 0.0, "onset_t_g_mean": 0.5725, "onset_t_g_std": 0.006480740698407866, "onset_memory_mean": 134.33333333333334, "onset_emergent_mean": 12.666666666666666, "onsets_found": 3, "seeds_run": 3}
  ]
}
```

## Figure paths

- `/tmp/outputs_phase_diagram/figures/phase_onset_cycle.png`
- `/tmp/outputs_phase_diagram/figures/phase_onset_tg.png`
- `/tmp/outputs_phase_diagram/figures/phase_onset_state_scatter.png`
