"""Formatting helpers for query interface outputs."""

from __future__ import annotations

import json
from typing import Any


def format_query_result(result: dict[str, Any], *, pretty: bool = True) -> str:
    """Serialize a query result dictionary as JSON text."""
    if pretty:
        return json.dumps(result, indent=2, sort_keys=False)
    return json.dumps(result, separators=(",", ":"), sort_keys=False)
