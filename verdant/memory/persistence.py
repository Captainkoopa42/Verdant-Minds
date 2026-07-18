from __future__ import annotations
import json
from pathlib import Path
from typing import Any

def save_state(path: str | Path, state: dict[str, Any]) -> None:
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2), encoding='utf-8')

def load_state(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding='utf-8'))
