# PredictionFailure measurement intake v0.54

This tool inspects and preserves candidate measurement captures. Every capture
remains quarantined. `physical_reported` is an acquisition claim supplied in the
file, not authentication of a physical source. The tool provides no harm score,
forecast, calibration result, funding or canonical authority.

From the repository root, with the locked Python environment installed:

```sh
python -m verdant_obligations.measurement_intake_cli candidate.json
```

Exit code 0 means the candidate has valid local structure and is **quarantined**.
Exit code 2 means it is invalid. The JSON report includes source claims, sample
count, unit label, capture window, claimed decision references and the exact file
SHA-256. It writes no file, changes no kernel and executes no simulation.
This inspection command does not validate canonical decision or study lineage.

## Capture format

The following is a **synthetic format example**, not physical evidence. Keep
`reported_origin` as `simulated` for generated captures. Replace metadata and
readings only with the actual acquisition record when a real source is available;
setting `physical_reported` still does not authenticate it.

```json
{
  "capture_format": "verdant-prediction-failure-raw-capture-v1",
  "source": {
    "source_ref": "fixture://synthetic-position",
    "acquisition_id": "fixture-acquisition-1",
    "acquisition_method": "explicitly synthetic example",
    "clock_ref": "fixture-clock-1",
    "reported_origin": "simulated",
    "action_class": "replace-with-study-action-class",
    "quantity": "fixture_position",
    "unit": "mm"
  },
  "capture_start_ns": 100,
  "capture_end_ns": 300,
  "expected_sample_count": 2,
  "samples": [
    {"sample_id": "s1", "decision_event_ref": "claimed-decision-1", "captured_at_ns": 100, "unit": "mm", "value": 1.25},
    {"sample_id": "s2", "decision_event_ref": "claimed-decision-1", "captured_at_ns": 300, "unit": "mm", "value": 2.5}
  ]
}
```

Files use UTF-8 JSON without a byte-order mark. One file contains one quantity
and one reported clock. Sample IDs must be unique,
times must strictly increase within the declared capture window, and the complete
sample count must match. All sample unit labels must equal the source unit label.
Supported labels are `m`, `mm`, `cm`, `s`, `ms`, `g`, `kg`, `N`, `Pa`, `V`, `A`,
`count` and `1`. There is no unit conversion, dimensional inference, quantity/unit
semantic validation or clock authentication. Timestamps are claimed integer
nanoseconds in the named clock, not trusted wall-clock or canonical-cycle times.

Raw files are bounded to 1 MiB and 4096 samples. Duplicate JSON keys, unknown
fields, nonfinite values, booleans/numeric strings masquerading as measurements,
incomplete captures and supplied `harm_score` fields are rejected. Whitespace and
JSON mapping order are accepted but retained in the exact raw bytes; changing
either creates a distinct source identity rather than silently replacing a file.

## Study-bound immutable intake

The Python API can persist a pilot receipt paired to the exact original v0.53
study and its full checkpoint/trial provenance chain:

```python
from verdant_obligations import PredictionFailureMeasurementIntake

receipt = PredictionFailureMeasurementIntake().ingest(
    "pilot.vmi",
    kernel=original_kernel,
    forecast_study_path="study.vfs",
    raw_capture_path="candidate.json",
    resolution_evidence_path="trial.vfe",
    completed_result_path="trial.vft",
    risk_receipt_path="trial.vfr",
    plan_path="trial.vpp",
    preregistration_path="trial.vfp",
)
assert receipt.receipt.quarantined
assert not receipt.receipt.physical_evidence_admissible
```

`original_kernel` must be the actual original checkpoint loaded through the native
VDK API, not a regenerated fixture. Capture action class must match the study.
The `.vmi` embeds the original raw bytes, the parsed capture and source hashes.
`load_prediction_failure_measurement_intake(path, **sources)` revalidates that
entire pairing. The raw file and all upstream files must remain byte-identical.
`read_prediction_failure_measurement_intake(path)` checks local integrity only.

Historical decision references are explicitly classified as excluded from the
future study. Other references remain unverified and are never enrolled by this
tool. A reported decision ID does not prove that the source measured that action.
The receipt is a measurement-protocol pilot only; it cannot become a study
outcome by changing flags, origin labels or recomputing checksums.

The `.vmi` is bounded to 8 MiB and uses the existing local POSIX immutable writer.
Identical replay costs no simulation budget; occupied paths with different bytes
are rejected. The writer has no Windows/network filesystem, hostile path,
process-death/power-loss, signature or trusted-timestamp guarantee, and creates no
transaction with canonical checkpoints or other sidecars. CLI inspection is
read-only and does not use that writer.

## Next dependency

Identify an actual acquisition source and one operational quantity, then define
and freeze a defensible physical measurement/scoring protocol before forecasts.
Verify source and decision linkage rather than trusting this file's declarations.
Keep matched controls and raw provenance. If no sourceable physical quantity
exists, physical calibration remains blocked.

Prospective forecast recording, cohort enrollment/sealing, new Attention funding
and durable evaluation follow that protocol. All four v0.52 mandatory missing
Resolution requirements remain missing. No source independence, independent
replication, causal repair or successful Resolution is established here.
