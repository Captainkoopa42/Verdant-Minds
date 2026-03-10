# Cell 5 — Run baseline + ablation + scramble (80 cycles x 20 seeds x 3 conditions)
%%bash
set -e
cd /content/Verdant-Minds

# BASELINE
python -m cultivation.cli run \n  --cycles 80 --seeds 0-19 --provider local \n  --basin-routing --outdir outputs_baseline

# ABLATION
python -m cultivation.cli run \n  --cycles 80 --seeds 0-19 --provider local \n  --basin-routing --outdir outputs_ablation \n  --intervention-mode ablate_oldest_nodes \n  --intervention-cycle 40 --ablation-fraction 0.1 \n  --intervention-target global

# SCRAMBLE
python -m cultivation.cli run \n  --cycles 80 --seeds 0-19 --provider local \n  --basin-routing --outdir outputs_scramble \n  --intervention-mode scramble_ee_edges \n  --intervention-cycle 40 --intervention-target global

echo
echo "Latest baseline run:"
ls -1dt outputs_baseline/run_* | head -n 1
echo "Latest ablation run:"
ls -1dt outputs_ablation/run_* | head -n 1
echo "Latest scramble run:"
ls -1dt outputs_scramble/run_* | head -n 1
