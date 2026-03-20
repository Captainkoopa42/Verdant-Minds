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
echo "Repo commit:"
git rev-parse HEAD

# Cell 2 — Upload or restore a checkpoint bundle
from google.colab import files
uploaded = files.upload()
print('Uploaded files:', list(uploaded))

# Cell 3 — Resume from checkpoint
%%bash
set -e
cd /content/Verdant-Minds
python -m cultivation.cli resume \
  --checkpoint /content/checkpoint_500.json \
  --additional-cycles 500 \
  --provider local \
  --checkpoint-interval 100 \
  --fast-bridge \
  --outdir outputs_v3_resumed

echo
echo 'Latest resumed run:'
ls -1dt outputs_v3_resumed/run_* | head -n 1

# Cell 4 — Run validation on resumed output
%%bash
set -e
cd /content/Verdant-Minds
python analysis/run_full_validation.py \
  --run-dir outputs_v3_resumed/run_* \
  --seeds 1 \
  --outdir validation_v3_resumed \
  --n-nulls 200

# Cell 5 — Bundle and download resumed outputs
import zipfile
from pathlib import Path
from google.colab import files

repo = Path('/content/Verdant-Minds')
zip_path = repo / 'verdant_v3_resumed_bundle.zip'
if zip_path.exists():
    zip_path.unlink()

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for folder in ['outputs_v3_resumed', 'validation_v3_resumed']:
        root = repo / folder
        if root.exists():
            for file in root.rglob('*'):
                if file.is_file():
                    zf.write(file, file.relative_to(repo))

print(f'Created: {zip_path}')
print(f'Size: {zip_path.stat().st_size / (1024 * 1024):.2f} MB')
files.download(str(zip_path))
