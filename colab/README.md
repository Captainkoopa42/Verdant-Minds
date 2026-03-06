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

## 4) Scaffold-ablation experiment commands

Baseline:
```bash
!python -m cultivation.cli run \
  --cycles 80 \
  --seeds 0-19 \
  --provider local \
  --basin-routing \
  --outdir outputs_baseline
```

Ablation:
```bash
!python -m cultivation.cli run \
  --cycles 80 \
  --seeds 0-19 \
  --provider local \
  --basin-routing \
  --outdir outputs_ablation \
  --intervention-mode ablate_oldest_nodes \
  --intervention-cycle 40 \
  --ablation-fraction 0.1 \
  --intervention-target global
```

Scramble:
```bash
!python -m cultivation.cli run \
  --cycles 80 \
  --seeds 0-19 \
  --provider local \
  --basin-routing \
  --outdir outputs_scramble \
  --intervention-mode scramble_ee_edges \
  --intervention-cycle 40 \
  --intervention-target global
```

Comparison:
```bash
!python analysis/compare_intervention_runs.py \
  --baseline outputs_baseline/<run_stamp> \
  --ablation outputs_ablation/<run_stamp> \
  --scramble outputs_scramble/<run_stamp> \
  --outdir intervention_comparison
```

Expected run layout:
- `outputs_*/run_<timestamp>/seed_<n>/state.json`
- `outputs_*/run_<timestamp>/seed_<n>/cycles.jsonl`
- `outputs_*/run_<timestamp>/seed_<n>/summary.json`

## 5) Output locations and download targets
- Cultivation artifacts: under `outputs_*/run_<timestamp>/seed_<n>/`
- Comparison artifacts: under `intervention_comparison/`
  - Includes `comparison_summary.json` and intervention comparison figures.

In Colab, browse files from the left sidebar or zip outputs for download:
```bash
!zip -r verdant_outputs.zip outputs_baseline outputs_ablation outputs_scramble intervention_comparison
```
