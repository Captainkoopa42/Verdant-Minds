from __future__ import annotations
import json, sys
request = json.load(sys.stdin)
payload = request.get("payload", {})
metrics = payload.get("metrics", payload)
concepts = float(metrics.get("concept_count", 0) or 0)
relations = float(metrics.get("relation_count", 0) or 0)
ratio = 0.0 if concepts <= 0 else relations / concepts
json.dump({"metric_id": "relation_per_concept", "value": ratio, "inputs": {"concept_count": concepts, "relation_count": relations}}, sys.stdout, sort_keys=True)
