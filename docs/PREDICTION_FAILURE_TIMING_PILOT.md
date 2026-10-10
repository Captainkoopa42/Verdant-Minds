# PredictionFailure timing pilot v0.55

This explicitly invoked performance pilot measures an existing read-only
operation. It does not measure physical harm, execute the prospective `.vfs`
study, calibrate a forecast or satisfy N. Every reading stays quarantined.

`PredictionFailureGovernanceRiskOperator.evaluate` computes the complete
unchanged three-arm risk bundle on each call. The timing roles are two identical
invocations of that whole bundle: baseline and valid-null repetition. They are
not timings of separately ablated inputs. The older `.vfp`/`.vft` ablation,
thresholds, negative results and Attention accounting remain unchanged.

## Fixed acquisition protocol

- Two independent canonical copies, constructed from the exact source snapshot.
- One untimed warmup per copy, followed by six pairs / twelve timed calls.
- Baseline then null in even-numbered pairs; null then baseline in odd pairs.
- `time.perf_counter_ns()` brackets the invocation wrapper and native evaluator,
  including that evaluator's file reads, validation and fingerprints.
- Clone construction, warmup, result comparison, capture intake, provenance
  checks outside the evaluator and publication are outside the timing window.
- Elapsed milliseconds are derived from integer nanosecond subtraction. Every
  sample must be positive, ordered and non-overlapping. No caller supplies
  durations, forecasts, scores, measurement callbacks or adaptive sample counts.
- Each returned full evaluation must exactly equal the previously validated
  native risk receipt. Each private copy and the caller must retain the exact
  canonical fingerprint. No simulation runtime, reservation or settlement is
  used by timing acquisition; read-only CPU work creates no simulation grant.

The clock's implementation, monotonic/adjustable flags and nominal resolution
are recorded, along with Python/platform metadata, the Git base revision at
acquisition, twelve declared source-file hashes, six exact input-file hashes,
canonical identity/fingerprint and source decision/proposal/report/output refs.
The base revision identifies the parent checkout; the new acquisition code was
in its working tree, and its exact bytes are pinned separately. The manifest is
bounded to the declared paths, not the complete transitive environment.

Each sample's decision reference identifies the historical decision supplying
the workload. It does not claim that the decision ran again or that its physical
consequence was measured. All sampled refs remain excluded from the future
study. The single-clock quantity is `read_only_risk_bundle_elapsed`, unit `ms`,
with origin reported as `unknown`; this does not invent a harm definition.

The generated raw bytes are imported through the existing v0.54 intake in a
temporary workspace. A single immutable `.vtp` contains the actual samples,
clock/provenance/protocol metadata and complete `.vmi` envelope with embedded
raw bytes. Temporary capture/intake files are removed. Final publication reuses
the existing POSIX locked, synced, atomic immutable writer. This provides one
whole-file publication, not a cross-file transaction, source authentication,
trusted timestamp, signature or rollback of an external writer. An occupied
valid `.vtp` replays; a different or invalid occupied file is never overwritten.

## Recorded local pilot

The reviewable dataset is in `artifacts/prediction_failure_timing_v055/`.
`source.vdk`, `prior.vfp`, `prior.vpp`, `prior.vfr`, `completed.vft`, `anchor.vfe`
and `study.vfs` preserve the full input chain. `pilot.vtp`, `capture.json`,
`intake.vmi` and `run.json` preserve readings and the collection/replay report.
The standalone capture/intake copies are exact exports from the final envelope.

The workload is the existing synthetic `_inputs` fixture in
`tests/test_prediction_failure_forecast_preregistration.py`, seed `79055`, mode
`unchanged`. Preparing that fixture makes the already implemented three-arm
trial with its existing valid grant; those setup operations are not timing
acquisition and do not constitute physical data. The old risk scores are
`(0.64, 0.64, 0.64)` from supplied fixture outcomes. The twelve elapsed readings
are actual local clock calls, not synthetic numbers. Other tests were active
in the shared container during acquisition; CPU load, frequency, scheduling,
cache state and thermal conditions were not independently controlled.

| Role | Calls | Mean ms | Median ms | Minimum ms | Maximum ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline repetition | 6 | 48.97608233333333 | 46.1910955 | 28.762745 | 79.885488 |
| Valid-null repetition | 6 | 48.01703783333333 | 45.8368975 | 31.172089 | 64.632821 |

All twelve complete outputs match exactly. All readings, including the slowest,
are retained. These summaries describe this sample; there is no significance,
speed-improvement, ablation-performance, causal repair, prediction calibration
or learning-makes-learning-cheaper claim. Identical logical output does not
require equal clock durations. The old canonical/ledger fingerprints and input
bytes stayed unchanged; checkpoint/mapping-order reload replayed exact stored
readings with no new timing call or simulation charge.

## Inspect, replay or acquire

Install the repository's locked requirements and run from its root. Local
inspection checks bytes and structure; only replay checks external provenance:

```bash
python -m verdant_obligations.timing_pilot_cli inspect artifacts/prediction_failure_timing_v055/pilot.vtp
```

```bash
python -m verdant_obligations.timing_pilot_cli replay artifacts/prediction_failure_timing_v055/pilot.vtp \
  --checkpoint artifacts/prediction_failure_timing_v055/source.vdk \
  --forecast-study artifacts/prediction_failure_timing_v055/study.vfs \
  --resolution-evidence artifacts/prediction_failure_timing_v055/anchor.vfe \
  --completed-result artifacts/prediction_failure_timing_v055/completed.vft \
  --risk-receipt artifacts/prediction_failure_timing_v055/prior.vfr \
  --plan artifacts/prediction_failure_timing_v055/prior.vpp \
  --preregistration artifacts/prediction_failure_timing_v055/prior.vfp
```

For another explicit acquisition, use `acquire`, choose a fresh output path and
pass those same source flags. Changing the output path does not authorize a new
physical study. The API equivalents are `PredictionFailureTimingPilot.acquire`,
`load_prediction_failure_timing_pilot`, `read_prediction_failure_timing_pilot`
and `prediction_failure_timing_pilot_bytes`. Exit 0 means a valid quarantined
pilot, not physical admission; exit 2 means invalid input.

Replay validates the unchanged complete source chain and rechecks the native
read-only risk evaluation through existing provenance loaders. It takes no new
clock samples, warmups, timed invocations, reservations or settlements. It does
not reproduce the elapsed durations by running the workload again.

## Evidence limits and next dependency

Tests use explicitly synthetic clocks for adversarial arithmetic/control cases;
the committed pilot uses real `perf_counter_ns` readings. Rehashed wrong units,
arithmetic, ordering, incomplete pairs, protocol changes, isolation flags,
external input/code/decision/output substitutions and authority attempts fail.
Privately mutated copies, output/source/code drift and pre-replace failure do not
publish a completed pilot. There is also an explicit negative test: replacing
all readings consistently and updating every hash can remain structurally valid
and quarantined. Consistency is not clock-source authentication.

The source is self-recorded, not independently authenticated or replicated.
Platform and clock metadata are not verified attestations. No hostile path,
power-loss, process-termination or multi-writer acquisition proof is added;
external source mutation after publication is detected on reload, not rolled
back. The supplied `.vfs` is unchanged and still requires an operational
trace-derived physical harm protocol, a prospective adapter, complete enrollment
and forecast sealing, and fresh per-case Attention funding before execution.
Calibrated physical prediction, causal repair, source independence and held-out
replication remain mandatory missing Resolution requirements. N stays unresolved.
