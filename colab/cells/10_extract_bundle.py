# Cell 10 — Extract a downloaded data bundle
import zipfile
from pathlib import Path

zip_path = Path("/content/verdant_v2_colab_bundle.zip")
extract_dir = Path("/content/verdant_data")
extract_dir.mkdir(exist_ok=True)

with zipfile.ZipFile(zip_path, "r") as z:
    z.extractall(extract_dir)

print("Extracted to:", extract_dir)
for p in sorted(extract_dir.rglob("*"))[:30]:
    print(f"  {p.relative_to(extract_dir)}")
