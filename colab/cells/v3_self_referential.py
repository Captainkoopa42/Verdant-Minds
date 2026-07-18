# Cell 1 — Clone repo, install, and checkout V3
%%bash
set -e
cd /content
rm -rf Verdant-Minds
git clone https://github.com/Captainkoopa42/Verdant-Minds.git
cd Verdant-Minds
git checkout V3
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
pip install -e .
git rev-parse HEAD

# Cell 2 — Smoke test (20 cycles, self-reflect every 5)
%%bash
set -e
cd /content/Verdant-Minds
python -m cultivation.cli run \
  --cycles 20 --seeds 0 --provider local \
  --basin-routing --enable-all-dynamics \
  --boundary-use-ecwf --density-regulation \
  --self-reflect-interval 5 \
  --outdir outputs_self_reflection_smoke

# Cell 3 — Full experiment (300 cycles, 5 seeds, self-reflect every 50)
%%bash
set -e
cd /content/Verdant-Minds
python -m cultivation.cli run \
  --cycles 300 --seeds 0-4 --provider local \
  --basin-routing --enable-all-dynamics \
  --boundary-use-ecwf --density-regulation \
  --self-reflect-interval 50 \
  --outdir outputs_self_referential

# Cell 4 — Baseline comparison (300 cycles, 5 seeds, no self-reflection)
%%bash
set -e
cd /content/Verdant-Minds
python -m cultivation.cli run \
  --cycles 300 --seeds 0-4 --provider local \
  --basin-routing --enable-all-dynamics \
  --boundary-use-ecwf --density-regulation \
  --outdir outputs_self_baseline

# Cell 5 — Self-referential concept detection
%%bash
set -e
cd /content/Verdant-Minds
python analysis/detect_self_referential_concepts.py \
  --state outputs_self_referential/run_*/seed_0/state.json \
  --cycles-jsonl outputs_self_referential/run_*/seed_0/cycles.jsonl \
  --outfile self_referential_analysis.json

# Cell 6 — Comparison analysis
%%bash
set -e
cd /content/Verdant-Minds
python analysis/compare_self_reflection.py \
  --self-run outputs_self_referential/run_* \
  --baseline-run outputs_self_baseline/run_* \
  --seeds 5 \
  --outfile self_reflection_comparison.json

# Cell 7 — Print all results
import json
from pathlib import Path
repo = Path('/content/Verdant-Minds')
for name in ['self_referential_analysis.json', 'self_reflection_comparison.json']:
    path = repo / name
    print(f'===== {name} =====')
    print(json.dumps(json.loads(path.read_text()), indent=2))

# Cell 8 — Download bundle
import zipfile
from pathlib import Path
from google.colab import files

repo = Path('/content/Verdant-Minds')
zip_path = repo / 'verdant_self_reflection_bundle.zip'
if zip_path.exists():
    zip_path.unlink()

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for folder in ['outputs_self_reflection_smoke', 'outputs_self_referential', 'outputs_self_baseline']:
        root = repo / folder
        if root.exists():
            for file in root.rglob('*'):
                if file.is_file():
                    zf.write(file, file.relative_to(repo))
    for file in ['self_referential_analysis.json', 'self_reflection_comparison.json']:
        path = repo / file
        if path.exists():
            zf.write(path, path.relative_to(repo))

print(zip_path)
files.download(str(zip_path))
