# Verdant V2 in Google Colab

Copy/paste the cells below into a fresh Colab notebook.

## 1) Clone repo and checkout `V2`
```bash
!git clone https://github.com/Captainkoopa42/Verdant-Minds.git
%cd Verdant-Minds
!git checkout V2
```

## 2) Install editable packages
```bash
!python -m pip install -U pip
!python -m pip install -e ./ethomorphic -e ./verdant_v2 -e ./cultivation
```

## 3) Quick sanity test
```bash
!pytest tests_v2 -q
```

## 4) One-command replication run (20 seeds baseline)
```bash
!python -m cultivation.cli run --cycles 120 --provider local --seeds 0-19 --basin-routing --outdir outputs
```

Expected run layout:
- `outputs/run_<timestamp>/seed_<n>/state.json`
- `outputs/run_<timestamp>/seed_<n>/cycles.jsonl`
- `outputs/run_<timestamp>/seed_<n>/summary.json`

## 5) One-command analysis run
Pick one produced `state.json` path (example uses seed 0):
```bash
!python analysis/run_all.py --state outputs/run_<timestamp>/seed_0/state.json --results-root results --n-nulls 1000 --k 6
```

## 6) Output locations and download targets
- Cultivation artifacts: under `outputs/run_<timestamp>/seed_<n>/`
- Analysis artifacts: under `results/<timestamp>/`
  - Includes `metrics.json`, `null_models.json`, `two_timescale_mixture.json`, `backbone_edges.csv`, and figure files.

In Colab, browse files from the left sidebar or zip outputs for download:
```bash
!zip -r verdant_outputs.zip outputs results
```
