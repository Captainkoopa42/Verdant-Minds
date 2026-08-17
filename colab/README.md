# V2 Colab assets

This directory contains two notebooks and a set of notebook-cell fragments.

| Asset | Intended role | Current status |
| --- | --- | --- |
| `Verdant_V2_Replication.ipynb` | Multi-seed cultivation and intervention workflow | Valid notebook JSON; installation cell references absent `./verdant_v2` and package metadata that does not install correctly |
| `verdant_v2_quickstart.ipynb` | Short demonstration | Valid notebook JSON; root editable install fails and it calls absent `analysis.depth_age_analysis` |
| `cells/01_...py` through `cells/10_...py` | Source fragments for notebook assembly | Contain IPython and shell magics; they are not standalone Python modules |

## Why the install cells fail

The tracked source directory is named `verdant`, while imports throughout the active implementation require `verdant_v2`. Its `pyproject.toml` also searches for a child package named `verdant_v2`, which is not present. The root package metadata instead points to an absent `usm` package.

The local workaround is documented in [../INSTALL.md](../INSTALL.md), but the notebooks themselves have been preserved unchanged as V2 research artifacts. Until their installation cells and absent analysis call are corrected, they should not be described as one-click reproduction notebooks.

## Expected runnable surface

Once `verdant_v2` is importable, the active experiment command is:

```bash
python -m cultivation.cli run \
  --cycles 80 \
  --seeds 0-19 \
  --provider local \
  --basin-routing \
  --outdir outputs_baseline
```

See [../cultivation/README.md](../cultivation/README.md) for outputs and intervention options.
