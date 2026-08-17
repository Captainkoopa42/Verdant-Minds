# Verdant-V0 Visualization Suite

`plot_processing.py` generates high-resolution PNG figures for architecture explanation, papers, and presentations.

## Data provenance warning

The command-line defaults generate **sample/synthetic plotting data**. The figures verify the plotting code and illustrate expected shapes; they are not automatically measurements from a live Verdant run. Python callers can construct the script's data classes and call the plot methods with recorded data. A figure should only be labeled as experimental evidence when that input source is documented.

## Commands

```bash
python visualization/plot_processing.py --all
python visualization/plot_processing.py --chunk-flow
python visualization/plot_processing.py --wave-evolution
python visualization/plot_processing.py --memory-activation
python visualization/plot_processing.py --ethical-scores
```

Options:

```bash
python visualization/plot_processing.py --all --output outputs/figures
python visualization/plot_processing.py --all --show
python visualization/plot_processing.py --all --show --no-save
```

The output option is `--output`, not `--output-dir`. The default destination is `outputs/figures`.

## Figure types

| Flag | Contents |
|---|---|
| `--chunk-flow` | block timings, activations, cumulative timing, flow view |
| `--wave-evolution` | cognitive/ethical dimensions, entropy, state trajectory |
| `--memory-activation` | concept activation, relationships, top concepts |
| `--ethical-scores` | principle heatmap, radar, distribution, thresholds |
| `--all` | all four figure types |

Figures are saved as 300-DPI PNG files.

## Dependencies

```bash
python -m pip install matplotlib numpy seaborn
```

On a headless machine, omit `--show`. If Matplotlib cannot write its default cache directory, point `MPLCONFIGDIR` to a writable temporary directory.

## Reporting checklist

For any figure used as evidence, state:

- the source artifact or state file;
- branch and runtime configuration;
- whether the data is measured, transformed, or simulated;
- metric definitions and units;
- plotting command and any preprocessing;
- whether smoothing, normalization, or selection was applied.
