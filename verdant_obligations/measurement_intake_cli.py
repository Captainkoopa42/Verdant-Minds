"""Inspect a raw capture's local structure; never admit it as study evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .prediction_failure_measurement_intake import (
    PredictionFailureMeasurementIntakeIntegrityError,
    _MAX_RAW_BYTES, _bounded_read, _parse_capture, _sha,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path, help="Raw capture JSON file")
    args = parser.parse_args(argv)
    try:
        data = _bounded_read(args.capture, _MAX_RAW_BYTES)
        capture = _parse_capture(data)
        report = dict(
            status="quarantined", raw_capture_sha256=_sha(data), raw_capture_size=len(data),
            source=capture.source.model_dump(mode="json"), sample_count=len(capture.samples),
            capture_start_ns=capture.capture_start_ns, capture_end_ns=capture.capture_end_ns,
            decision_refs=sorted({s.decision_event_ref for s in capture.samples}),
            source_authenticated=False, decision_links_authenticated=False,
            physical_evidence_admissible=False, harm_scoring_implemented=False,
            calibration_observed=False,
        )
        print(json.dumps(report, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, PredictionFailureMeasurementIntakeIntegrityError) as exc:
        print(json.dumps(dict(status="invalid", error=str(exc)), sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
