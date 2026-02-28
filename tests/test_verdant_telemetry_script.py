import json
import subprocess
import sys
from pathlib import Path


def test_verdant_telemetry_json_mode_outputs_expected_sections():
    script = Path("scripts/verdant_telemetry.py")
    proc = subprocess.run(
        [sys.executable, str(script), "--json"],
        input="hello\nexit\n",
        text=True,
        capture_output=True,
        check=True,
    )

    # Find first JSON object in stdout
    lines = proc.stdout.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("{"):
            start = i
            break
    assert start is not None, proc.stdout

    payload = "\n".join(lines[start:])
    # trim trailing prompt text if any
    end = payload.rfind("}")
    assert end != -1
    telemetry = json.loads(payload[: end + 1])

    assert "thermodynamic_state" in telemetry
    assert "wave_state" in telemetry
    assert "coherence_invariants" in telemetry
    assert "memory_topology" in telemetry
    assert "kings_status" in telemetry
    assert "action_taken" in telemetry
