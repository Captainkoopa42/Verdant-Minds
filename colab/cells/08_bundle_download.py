# Cell 8 — Bundle all outputs and download
import zipfile
from pathlib import Path
from google.colab import files

repo = Path("/content/Verdant-Minds")
zip_path = repo / "verdant_intervention_bundle.zip"

if zip_path.exists():
    zip_path.unlink()

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for folder in ["intervention_comparison_full", "outputs_baseline",
                    "outputs_ablation", "outputs_scramble"]:
        p = repo / folder
        if p.exists():
            for file in p.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(repo))

print(f"Created: {zip_path}")
print(f"Size: {zip_path.stat().st_size / (1024*1024):.2f} MB")
files.download(str(zip_path))
