# Motor Subsystem Removal Record

## Decision

All motor-oriented implementation was removed from the active Verdant rebuild. Nothing was renamed to disguise or preserve it under a different label.

The active codebase now stops at:

```text
user-selected files
→ exact native preservation
→ vision/audio temporal events
→ nonsemantic perceptual continuity
→ governed proto-object promotion
```

There is no active hardware-command path anywhere in the runtime.

## Deleted from the active codebase

The following were deleted rather than renamed:

- the complete `verdant_skills/` package;
- `tests/test_skills_phase.py`;
- Milestone 8 report, manifest, checkpoint, summaries, reports, and stdout artifact;
- all skill policy, attempt, candidate, operator, compilation, execution, reopening, and cost models from `KernelState`;
- all skill validation, commit, fingerprint, metrics, and invariant code from `VerdantKernel`;
- the workspace `SKILL` source kind and compiled-skill admission path;
- the native `TELEMETRY` modality;
- the telemetry JSON translator;
- wheel, yaw-rate, current, and body-telemetry test/demo packets;
- the differential-drive/Milestone 11 implementation plan from the active milestone report;
- robot-specific curriculum fixtures used only by the removed path;
- probe-extension and actuator fixtures used as physical-action demonstrations;
- the proto-object causal-interaction observation kind, policy gate, support component, tests, and demo fixture;
- all cached Python bytecode and stale test caches that could preserve deleted imports.

## Rebuilt after deletion

Milestone 9 was regenerated from the Milestone 7 object checkpoint. It no longer loads, references, admits, or reports any compiled skill. The old sensorimotor shard fixture was deleted; Milestone 9 now reads the existing root shard context, not the old fixture under a new name.

Milestone 10 was regenerated with only:

- raw grayscale vision bytes;
- raw PCM audio bytes.

Its active demonstration now contains 16 samples: 8 vision and 8 audio. No control or body telemetry stream exists.

## What remains, and why it is not motor code

The following general cognitive records remain:

- `EvidenceKind.ACTION` and `EvidenceKind.OUTCOME`;
- Council proposals of kind `ACT`;
- workspace records of an `AUTHORIZED_ACTION`;
- claim records based on physical outcomes.

These are abstract epistemic and governance records. They cannot contact hardware, emit a device command, access a driver, or alter a physical device. Removing them would delete Verdant's ability to represent that an event occurred or that Council authorized a non-hardware operation such as an inspection.

No aliases such as `device movement`, `physical transition`, `output channel`, or similar replacements were introduced for deleted motor code.

## Verification

The active Python tree was scanned for motor and removed-subsystem identifiers, including:

```text
motor, actuator, servo, wheel, encoder, IMU, PWM, driver,
differential drive, chassis, sensorimotor, Skill*, skill_, TELEMETRY
```

The scan found zero matches in active Python source.

The active test suite still passes after deletion and the later media/perception work:

```text
124 passed
```

## Reintroduction rule

Motor support may return only as a new, separately reviewed implementation after real hardware and a physical test method are available. The design is documented in `FUTURE_MOTOR_IMPLEMENTATION_DESIGN.md`; that document is not imported by the runtime and contains no active implementation.
