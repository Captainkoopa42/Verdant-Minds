# Verdant V3 Verification Bundle

## Key Results (500-cycle clean run, v4)

- Earlier-share: 1.000000 (z = 113.06, p < 10^-114)
- Emergent concepts: 252 with clean parents
- EE edges: 12,833 (32.9% of total graph)
- T_g: 0.5762 ± 0.0263 (stable through all density states)
- H1 coherence: 500/500 (perfect)
- Bud events: 17 across 4 generations
- Density oscillation: 14 peaks, 14 troughs
- Regulation events: 184
- Noise parents: 0

## Contents

### verification_runs/
- thermo_verify_v3/ — Pre-fix runs (budding gate fix applied)
- thermo_verify_v4/ — Post-fix runs (noise filter + EE edges restored)

Each seed directory contains:
- cycles.jsonl — Per-cycle telemetry
- basin_snapshots.jsonl — Periodic basin state snapshots
- state.json — Final system state
- *.png — Visualization outputs
- analysis/ — Basin persistence analysis results

### thaw_paper/
- thaw_paper.pdf — The Crystallization Scaling Law paper
- thaw_paper.docx — Editable source
- THAW_README.md — Zenodo upload guide

### codex_prompts/
- All Codex prompts used during this session

### colab_cells/
- All Colab cell scripts used for verification

## Reproducing Results

1. Clone V3: git clone -b V3 https://github.com/Captainkoopa42/Verdant-Minds.git
2. Run: python -m cultivation.cli run --cycles 500 --seeds 0 --provider local \
   --enable-all-dynamics --density-regulation --bud-pressure-threshold 0.001 \
   --basin-snapshot-interval 10 --self-reflect-interval 25
3. Results should match within stochastic variation
