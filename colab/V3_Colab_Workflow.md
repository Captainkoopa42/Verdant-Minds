# Branch V3 Colab Workflow (Quick + Long Runs)

> Ordered notebook cells for deterministic, non-mixing regime studies with analysis and bundle download.

---

## Cell 1 — Clone Branch V3 and enter repo
```python
%%bash
set -euo pipefail

cd /content
if [ -d Verdant-Minds ]; then
  rm -rf Verdant-Minds
fi

git clone <YOUR_V3_REPO_URL> Verdant-Minds
cd Verdant-Minds

git fetch --all --tags
# Replace with your actual V3 branch name if needed
git checkout V3

echo "HEAD=$(git rev-parse --short HEAD)"
```

## Cell 2 — Install dependencies
```python
%%bash
set -euo pipefail
cd /content/Verdant-Minds

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
pip install -e ./cultivation
```

## Cell 3 — Set deterministic study configuration (shared by all cells)
```python
from pathlib import Path
import os

ROOT = Path('/content/Verdant-Minds')
OUT_ROOT = ROOT / 'outputs_v3'
ANALYSIS_ROOT = ROOT / 'analysis_v3'
BUNDLE_ROOT = ROOT / 'bundle_v3'

for p in [OUT_ROOT, ANALYSIS_ROOT, BUNDLE_ROOT]:
    p.mkdir(parents=True, exist_ok=True)

QUICK_SEEDS = '0-4'      # deterministic quick sweep
LONG_SEEDS = '0-19'      # deterministic long sweep
QUICK_CYCLES = 80
LONG_CYCLES = 300

print('OUT_ROOT=', OUT_ROOT)
print('ANALYSIS_ROOT=', ANALYSIS_ROOT)
print('BUNDLE_ROOT=', BUNDLE_ROOT)
```

## Cell 4 — Run 80-cycle QUICK baseline regime (separate output dir)
```python
%%bash
set -euo pipefail
cd /content/Verdant-Minds

python -m cultivation.cli run \
  --cycles 80 \
  --seeds 0-4 \
  --provider local \
  --basin-routing \
  --outdir outputs_v3/quick_baseline

ls -1dt outputs_v3/quick_baseline/run_* | head -n 1
```

## Cell 5 — Run 80-cycle QUICK p6style regime (separate output dir)
```python
%%bash
set -euo pipefail
cd /content/Verdant-Minds

python -m cultivation.cli run \
  --cycles 80 \
  --seeds 0-4 \
  --provider local \
  --basin-routing \
  --enable-all-dynamics \
  --no-boundary-use-ecwf \
  --no-density-regulation \
  --bud-pressure-threshold 0.0001 \
  --outdir outputs_v3/quick_p6style

ls -1dt outputs_v3/quick_p6style/run_* | head -n 1
```

## Cell 6 — Run 80-cycle QUICK phase7 regime (separate output dir)
```python
%%bash
set -euo pipefail
cd /content/Verdant-Minds

python -m cultivation.cli run \
  --cycles 80 \
  --seeds 0-4 \
  --provider local \
  --basin-routing \
  --enable-all-dynamics \
  --boundary-use-ecwf \
  --density-regulation \
  --bud-pressure-threshold 0.001 \
  --outdir outputs_v3/quick_phase7

ls -1dt outputs_v3/quick_phase7/run_* | head -n 1
```

## Cell 7 — Run 300-cycle LONG baseline regime (separate output dir)
```python
%%bash
set -euo pipefail
cd /content/Verdant-Minds

python -m cultivation.cli run \
  --cycles 300 \
  --seeds 0-19 \
  --provider local \
  --basin-routing \
  --outdir outputs_v3/long_baseline

ls -1dt outputs_v3/long_baseline/run_* | head -n 1
```

## Cell 8 — Run 300-cycle LONG p6style regime (separate output dir)
```python
%%bash
set -euo pipefail
cd /content/Verdant-Minds

python -m cultivation.cli run \
  --cycles 300 \
  --seeds 0-19 \
  --provider local \
  --basin-routing \
  --enable-all-dynamics \
  --no-boundary-use-ecwf \
  --no-density-regulation \
  --bud-pressure-threshold 0.0001 \
  --outdir outputs_v3/long_p6style

ls -1dt outputs_v3/long_p6style/run_* | head -n 1
```

## Cell 9 — Run 300-cycle LONG phase7 regime (separate output dir)
```python
%%bash
set -euo pipefail
cd /content/Verdant-Minds

python -m cultivation.cli run \
  --cycles 300 \
  --seeds 0-19 \
  --provider local \
  --basin-routing \
  --enable-all-dynamics \
  --boundary-use-ecwf \
  --density-regulation \
  --bud-pressure-threshold 0.001 \
  --outdir outputs_v3/long_phase7

ls -1dt outputs_v3/long_phase7/run_* | head -n 1
```

## Cell 10 — Unified analysis pass over latest run in each regime/scale
```python
%%bash
set -euo pipefail
cd /content/Verdant-Minds

mkdir -p analysis_v3

run_analysis_for_regime () {
  local scale="$1"      # quick | long
  local regime="$2"     # baseline | p6style | phase7
  local run_dir
  run_dir=$(ls -1dt "outputs_v3/${scale}_${regime}"/run_* | head -n 1)

  mkdir -p "analysis_v3/${scale}_${regime}"

  for seed_dir in "$run_dir"/seed_*; do
    seed_name=$(basename "$seed_dir")
    state_path="$seed_dir/state.json"
    out_root="analysis_v3/${scale}_${regime}/${seed_name}"

    python analysis/run_all.py \
      --state "$state_path" \
      --results-root "$out_root" \
      --n-nulls 200 \
      --k 6 \
      --orientation older_to_newer
  done
}

run_analysis_for_regime quick baseline
run_analysis_for_regime quick p6style
run_analysis_for_regime quick phase7
run_analysis_for_regime long baseline
run_analysis_for_regime long p6style
run_analysis_for_regime long phase7

echo "Unified analysis complete under analysis_v3/"
```

## Cell 11 — Build compact regime summary tables from cycles/summary outputs
```python
import json
from pathlib import Path
import pandas as pd

root = Path('/content/Verdant-Minds')
out_csv_dir = root / 'analysis_v3' / 'tables'
out_csv_dir.mkdir(parents=True, exist_ok=True)

rows = []
for scale in ['quick', 'long']:
    for regime in ['baseline', 'p6style', 'phase7']:
        run_base = root / 'outputs_v3' / f'{scale}_{regime}'
        latest = sorted(run_base.glob('run_*'))[-1]
        for seed_dir in sorted(latest.glob('seed_*')):
            summary = json.loads((seed_dir / 'summary.json').read_text())
            cycles = [json.loads(x) for x in (seed_dir / 'cycles.jsonl').read_text().splitlines() if x.strip()]
            onset_cycle = next((r['cycle_index'] for r in cycles if int(r.get('emergent_count', 0)) > 0), None)
            rows.append({
                'scale': scale,
                'regime': regime,
                'seed': summary['seed'],
                'cycles': summary['cycles'],
                'final_phase': summary['final_phase'],
                'final_t_g': summary['final_t_g'],
                'emergent_count': summary['emergent_count'],
                'memory_size': summary['memory_size'],
                'avg_entropy': summary['avg_entropy'],
                'avg_hci': summary['avg_hci'],
                'onset_cycle_first_emergent': onset_cycle,
            })

df = pd.DataFrame(rows).sort_values(['scale', 'regime', 'seed'])
df.to_csv(out_csv_dir / 'regime_seed_summary.csv', index=False)

grp = (df.groupby(['scale', 'regime'])
         .agg(n_seeds=('seed', 'count'),
              emergent_mean=('emergent_count', 'mean'),
              memory_mean=('memory_size', 'mean'),
              onset_mean=('onset_cycle_first_emergent', 'mean'),
              entropy_mean=('avg_entropy', 'mean'),
              hci_mean=('avg_hci', 'mean'))
         .reset_index())
grp.to_csv(out_csv_dir / 'regime_aggregate_summary.csv', index=False)

print('Wrote:', out_csv_dir / 'regime_seed_summary.csv')
print('Wrote:', out_csv_dir / 'regime_aggregate_summary.csv')
grp
```

## Cell 12 — Bundle all outputs and download
```python
import zipfile
from pathlib import Path
from google.colab import files

repo = Path('/content/Verdant-Minds')
zip_path = repo / 'verdant_v3_regime_bundle.zip'

if zip_path.exists():
    zip_path.unlink()

include_roots = [
    'outputs_v3/quick_baseline',
    'outputs_v3/quick_p6style',
    'outputs_v3/quick_phase7',
    'outputs_v3/long_baseline',
    'outputs_v3/long_p6style',
    'outputs_v3/long_phase7',
    'analysis_v3',
]

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for rel in include_roots:
        p = repo / rel
        if p.exists():
            for f in p.rglob('*'):
                if f.is_file():
                    zf.write(f, f.relative_to(repo))

print(f'Created: {zip_path}')
print(f'Size: {zip_path.stat().st_size / (1024*1024):.2f} MB')
files.download(str(zip_path))
```
