# Cell 6 — Compare baseline vs ablation vs scramble
%%bash
set -e
cd /content/Verdant-Minds

BASE=$(ls -1dt outputs_baseline/run_* | head -n 1)
ABL=$(ls -1dt outputs_ablation/run_* | head -n 1)
SCR=$(ls -1dt outputs_scramble/run_* | head -n 1)

python analysis/compare_intervention_runs.py \n  --baseline "$BASE" --ablation "$ABL" --scramble "$SCR" \n  --outdir intervention_comparison_full

echo
echo "Created comparison files:"
find intervention_comparison_full -maxdepth 1 -type f | sort
