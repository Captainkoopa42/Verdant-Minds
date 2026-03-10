# Cell 7 — Print intervention comparison summary
import json
from pathlib import Path

summary_path = Path("/content/Verdant-Minds/intervention_comparison_full/comparison_summary.json")
summary = json.loads(summary_path.read_text())
print(json.dumps(summary, indent=2))
