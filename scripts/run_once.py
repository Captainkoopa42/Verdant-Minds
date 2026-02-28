#!/usr/bin/env python3
import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from usm import UnifiedSyntheticMind


def to_jsonable(obj):
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(v) for v in obj]
    if hasattr(obj, "tolist"):
        try:
            return to_jsonable(obj.tolist())
        except Exception:
            pass
    return str(obj)


def main():
    try:
        mind = UnifiedSyntheticMind(config={"initialize_knowledge": False})
    except TypeError:
        mind = UnifiedSyntheticMind()

    chunk = mind.process_input("Hello Verdant.")

    print("section_keys:", sorted(chunk.sections.keys()))
    print("processing_metrics_section:", chunk.get_section_content("processing_metrics_section"))
    print("coherence_invariants_section:", chunk.get_section_content("coherence_invariants_section"))

    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    out_path = artifacts_dir / "chunk_trace.json"
    out_path.write_text(json.dumps(to_jsonable(chunk.sections), indent=2))
    print(f"wrote: {out_path}")


if __name__ == "__main__":
    main()
