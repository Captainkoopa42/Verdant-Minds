# Cell 1 — Clone repo, install, and use the current branch
%%bash
set -e
cd /content
rm -rf Verdant-Minds
git clone https://github.com/Captainkoopa42/Verdant-Minds.git
cd Verdant-Minds
git use the current branch
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
pip install -e .
echo "Repo commit:"
git rev-parse HEAD

# Cell 2 — Quick smoke test (5 cycles) and verify V4 registry/checkpoints
%%bash
set -e
cd /content/Verdant-Minds
python -m cultivation.cli run \
  --cycles 5 --seeds 0 --provider local \
  --basin-routing --enable-all-dynamics \
  --boundary-use-ecwf --density-regulation \
  --bud-pressure-threshold 0.001 \
  --checkpoint-interval 5 \
  --fast-bridge \
  --outdir outputs_v4_smoke
python - <<'PY2'
import glob, json
state_path = sorted(glob.glob('outputs_v4_smoke/run_*/seed_0/state.json'))[-1]
state = json.load(open(state_path))
extra = state.get('extra', {})
registry = extra.get('basin_registry', {})
config = extra.get('config', {})
print('Smoke state:', state_path)
print('Registry enabled:', bool(config.get('basin_use_registry', registry.get('basins'))))
print('Fast bridge enabled:', bool(config.get('fast_bridge', False)))
print('Checkpoint created:', bool(sorted(glob.glob('outputs_v4_smoke/run_*/seed_0/checkpoint_*.json'))))
print('Registry basin entries:', len((registry.get('basins') or {})))
PY2

# Cell 3 — 1000-cycle run with checkpointing
%%bash
set -e
cd /content/Verdant-Minds
python -m cultivation.cli run \
  --cycles 1000 --seeds 0-4 --provider local \
  --basin-routing --enable-all-dynamics \
  --boundary-use-ecwf --density-regulation \
  --bud-pressure-threshold 0.001 \
  --checkpoint-interval 100 \
  --fast-bridge \
  --outdir outputs_v4_1000

echo
echo 'Latest 1000-cycle run:'
ls -1dt outputs_v4_1000/run_* | head -n 1

# Cell 4 — Run full validation on the 1000-cycle output
%%bash
set -e
cd /content/Verdant-Minds
python analysis/run_full_validation.py \
  --run-dir outputs_v4_1000/run_* \
  --seeds 5 \
  --outdir validation_v4_1000 \
  --n-nulls 200

# Cell 5 — Print validation report
import json
from pathlib import Path

report_path = Path('/content/Verdant-Minds/validation_v4_1000/validation_report.json')
report = json.loads(report_path.read_text())
print(json.dumps(report, indent=2))

# Cell 6 — Bundle and download outputs
import zipfile
from pathlib import Path
from google.colab import files

repo = Path('/content/Verdant-Minds')
zip_path = repo / 'verdant_v4_1000_bundle.zip'
if zip_path.exists():
    zip_path.unlink()

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for folder in ['outputs_v4_1000', 'validation_v4_1000']:
        root = repo / folder
        if root.exists():
            for file in root.rglob('*'):
                if file.is_file():
                    zf.write(file, file.relative_to(repo))

print(f'Created: {zip_path}')
print(f'Size: {zip_path.stat().st_size / (1024 * 1024):.2f} MB')
files.download(str(zip_path))
