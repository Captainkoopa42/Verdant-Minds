"""Explicit acquisition/replay CLI; inspection alone proves local consistency."""
from __future__ import annotations

import argparse
import json
import statistics

from verdant_kernel import VerdantKernel, load_checkpoint

from .prediction_failure_timing_pilot import (
    PredictionFailureTimingPilot, load_prediction_failure_timing_pilot,
    read_prediction_failure_timing_pilot,
)


def timing_pilot_summary(envelope):
    r = envelope.receipt
    roles = {}
    for role in ("baseline", "valid_null"):
        values = [s.elapsed_ms for s in r.samples if s.role == role]
        roles[role] = dict(count=len(values), elapsed_ms=values, mean_ms=statistics.mean(values),
                           median_ms=statistics.median(values), min_ms=min(values), max_ms=max(values))
    return dict(status="quarantined_performance_pilot", pilot_ref=r.pilot_id, roles=roles,
        clock=r.clock.model_dump(mode="json"), output_match="exact_complete_risk_evaluation",
        decision_event_ref=r.source_decision_ref, raw_capture_sha256=r.intake.receipt.raw_capture_sha256,
        source_authenticated=False, physical_evidence_admissible=False, harm_scoring_implemented=False,
        calibration_observed=False, resolution_contract_satisfied=False,
        performance_improvement_claim_permitted=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "acquire", "replay"):
        command = commands.add_parser(name)
        command.add_argument("path")
        if name != "inspect":
            command.add_argument("--checkpoint", required=True)
            for source in ("forecast_study", "resolution_evidence", "completed_result",
                           "risk_receipt", "plan", "preregistration"):
                command.add_argument("--" + source.replace("_", "-"), required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            envelope = read_prediction_failure_timing_pilot(args.path)
        else:
            sources = {name + "_path": getattr(args, name) for name in (
                "forecast_study", "resolution_evidence", "completed_result", "risk_receipt", "plan", "preregistration")}
            sources["kernel"] = VerdantKernel.from_state(load_checkpoint(args.checkpoint))
            envelope = (PredictionFailureTimingPilot().acquire(args.path, **sources)
                        if args.command == "acquire" else load_prediction_failure_timing_pilot(args.path, **sources))
        print(json.dumps(timing_pilot_summary(envelope), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(json.dumps(dict(status="invalid", error=str(exc)), sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
