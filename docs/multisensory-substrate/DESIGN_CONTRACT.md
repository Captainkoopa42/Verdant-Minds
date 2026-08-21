# Multisensory Substrate Design Contract

## Status

Pre-implementation specification for branch `V5-Multisensory-Substrate-Prework`, based on V5 commit `ec37dfd90f5b4a3c889a7105d7e855692a372b77`.

This document deliberately separates **what must be true** from exact class names or final code layout. Names below are illustrative unless marked as current V5 types.

---

# 1. Design objective

Extend Verdant from bounded one-vision/one-audio ingestion into a reproducible multisensor substrate capable of supporting future embodied development without installing semantic world structure in the sensor layer.

The first target use case is a rigid two-camera stereo rig that can produce a pure binocular disparity/depth signal while preserving exact native source evidence.

The design must generalize cleanly to:

- two eyes;
- two ears;
- IMU channels;
- joint encoders;
- distributed touch;
- motor telemetry;
- later movable eye cameras.

---

# 2. Non-negotiable invariants

## I-01 — Physical observation identity is independent of translation

The exact same captured frame remains the same source observation regardless of how many translators later inspect it.

A translator revision may create a new translation product. It must not retroactively create a new physical observation.

## I-02 — Sensor identity is not modality

Two sensors may share one modality.

Examples:

```text
eye_left   -> vision
eye_right  -> vision
ear_left   -> audio
ear_right  -> audio
```

No grouping rule may reject or overwrite a sample simply because another sensor of the same modality is present.

## I-03 — Sensor identity is not stream/session identity

A physical sensor may restart.

A restart may begin a new stream epoch with sequence zero while retaining the same physical sensor identity.

## I-04 — Rig membership is explicit

Sensors that participate in a physical acquisition relationship must belong to a declared rig or synchronization contract.

Examples:

```text
stereo_head_rig
binaural_head_rig
head_proprioception_rig
```

## I-05 — Exact-pairing relationships use acquisition identity when available

Stereo pairs and binaural sample blocks should use shared hardware capture/sample identity when possible.

Nearest timestamp must not silently replace a missing exact mate.

## I-06 — Clock domains may not be compared blindly

Numeric timestamps from different clock domains are not physically comparable unless an explicit clock mapping exists.

## I-07 — Missing, invalid, unknown, and zero are different states

A valid zero measurement is data.

No measurement is absence.

An invalid derived value is uncertainty.

These may never be silently conflated.

## I-08 — Derived fields preserve exact lineage

A stereo disparity field must identify the exact source observation IDs, calibration/configuration revision, transform revision, output checksum, and validity/confidence representation used to create it.

## I-09 — Derived geometry creates no semantic truth

The stereo stage may not emit or install categories such as:

- object
- face
- person
- obstacle
- floor
- near
- far
- reachable
- safe

## I-10 — Multiple visual streams may never be treated as one temporal movie by default

Left/right eye alternation cannot be interpreted as temporal motion.

Any temporal tracker must declare its source stream or rig geometry explicitly.

## I-11 — Adding sensors must not silently redefine event duration

Temporal event limits must not shrink simply because more sensors are sampled at each instant.

## I-12 — Dense fields do not live inside `.vdk`

Checkpoint state may retain identifiers, hashes, summaries, and provenance, but bulk dense fields remain in external sensory/derived archives.

## I-13 — Historical V5 record IDs retain historical meaning

Existing V5 record types whose IDs checksum their contents must not be silently redefined in a way that invalidates old checkpoints.

## I-14 — The sensor layer may explicitly say `unknown`

A stereo matcher is not required to fabricate depth where correspondence is unsupported.

## I-15 — Evaluation ground truth is not learner input unless the experimental arm says so

Synthetic depth truth, camera poses, or target distances may be used to score a run without being supplied to Verdant.

---

# 3. Proposed record separation

The following record categories are recommended conceptually.

## 3.1 SourceObservation

Represents one native physical acquisition.

Suggested fields:

```text
observation_id
sensor_id
stream_id
stream_epoch
sequence_number
source_timestamp
source_clock_domain
normalized_timestamp?         # only if mapped
clock_mapping_ref?
timing_uncertainty_ns?
rig_id?
acquisition_id?
modality
media_type
shape / rate / channel schema
payload_sha256
payload_nbytes
archive_id
archive_member_path
native_metadata
```

Identity should depend on the native acquisition facts and exact payload digest, not translator revision.

## 3.2 TranslationProduct

Represents a single-sensor low-level transform.

Examples:

- luminance statistics;
- local image signature;
- audio spectrum signature;
- IMU normalization;
- encoder conversion.

Suggested fields:

```text
translation_id
source_observation_id
translator_kind
translator_revision
configuration_hash
feature_vector / compact signature
payload_or_field_ref?
output_sha256
validity metadata
created_cycle
```

## 3.3 DerivedSensoryField

Represents a relational transform that depends on multiple source observations or translations.

Stereo disparity is the first intended use.

Suggested fields:

```text
field_id
kind = binocular_disparity
source_observation_ids
source_translation_ids?       # only if derivation actually uses them
rig_id
acquisition_id
calibration_ref
transform_revision
configuration_hash
shape
dtype
field_archive_ref
field_sha256
validity_archive_ref
validity_sha256
confidence_archive_ref?
confidence_sha256?
timing_skew_ns
timing_uncertainty_ns
metadata
```

A derived field is not a native observation and must never masquerade as one.

## 3.4 RigFrame

Represents one exact local acquisition state for a rig.

Suggested fields:

```text
rig_frame_id
rig_id
acquisition_id
anchor_time
member_observation_ids
expected_sensor_ids
present_sensor_ids
missing_sensor_ids
maximum_skew_ns
clock_mapping_refs
complete_for_contract
```

Completeness is defined by the rig contract, not by the number of distinct modalities.

## 3.5 ExperienceBundle

Represents a looser cross-rig experiential association.

Example members may include:

```text
stereo rig frame
binaural rig frame
IMU state
neck encoders
eye encoders
touch state
motor telemetry
```

Cross-rig timing may tolerate greater uncertainty than stereo pairing.

## 3.6 TemporalEvent v2

A future temporal event should be organized around rig frames / experience bundles or duration, not raw sample count.

Historical `TemporalEventRecord` v1 should remain readable under its original semantics.

---

# 4. Rig contract

A rig declares how members relate physically and temporally.

Illustrative fixed stereo contract:

```text
rig_id: eyes_fixed_v1
kind: stereo_camera_pair
required_sensors:
  - eye_left
  - eye_right
pairing_key: acquisition_id
shared_clock_required: true
maximum_validated_skew_ns: <hardware-specific>
geometry_ref: stereo_calibration_v1
allow_partial_frame: true
partial_frame_derivation_allowed: false
```

Meaning:

- a right-eye frame without the matching left-eye acquisition is still preserved as a source observation;
- the rig frame records the missing left member;
- no stereo disparity field is fabricated from mismatched captures.

---

# 5. Clock model

## 5.1 Same-domain case

If both sensors share a hardware clock or trigger source, retain that common domain and acquisition identity.

## 5.2 Cross-domain case

If a source clock must be related to a host clock, create a separate mapping record.

Conceptually:

```text
mapped_time = a * source_time + b
uncertainty = epsilon
```

The exact model may later be more sophisticated, but the mapping itself must be versioned and referenced.

## 5.3 Forbidden behavior

Never do this unless the clock domains are known comparable:

```text
skew = timestamp_A - timestamp_B
```

The fact that both values are integers is not evidence they share an epoch or rate.

---

# 6. Stereo derivation contract

For a fixed calibrated stereo pair, the low-level relationship is:

```text
Z = f B / d
```

The derivation may preserve disparity even when metric depth is not supplied to the learner.

## 6.1 Minimum output

A stereo derivation should preserve at least:

```text
disparity field D(x,y)
validity field V(x,y)
confidence / consistency field C(x,y) if available
```

## 6.2 Optional output

Metric depth or inverse depth may be a separately named derived product.

Do not overwrite disparity with metric depth.

## 6.3 Invalid pixels

Invalid correspondence must remain invalid.

Do not encode invalid as a physically meaningful zero or infinity unless the representation has a separate validity mask that makes the distinction unambiguous.

## 6.4 Calibration

Calibration is a property of the sensor apparatus, not a semantic world model.

A calibration record should include enough information to reproduce the transform, including revision and checksums for intrinsics/extrinsics/rectification data.

## 6.5 Matcher assumptions

The transform metadata should identify the matcher algorithm and parameters because stereo is not mathematically assumption-free.

This supports later ablations and prevents silently changing the learner's sensory physiology.

---

# 7. Timing error reasoning for stereo

For simplified lateral relative motion:

```text
d_true = f B / Z

d_time ~= f v DeltaT / Z
```

Therefore:

```text
d_time / d_true ~= v DeltaT / B
```

The distance and focal length cancel in the ratio.

This is why a broad multimodal tolerance cannot be reused as the stereo pairing criterion.

For example, with baseline `B = 0.06 m` and `DeltaT = 0.020 s`:

```text
v = 0.1 m/s -> about 3.3% disparity contamination
v = 0.5 m/s -> about 16.7%
v = 1.0 m/s -> about 33.3%
```

This is a design warning, not a universal hardware requirement. Actual accepted skew must be selected for the physical rig and experiment.

---

# 8. M11 compatibility contract

Before multiple visual sensors enter one runtime, M11 must stop implicitly using `all VISION samples` as one movie.

Every perception pass must declare one of:

```text
single stream temporal tracking
single sensor temporal tracking
stereo-rig geometric tracking
another explicit source policy
```

The existing single-camera M11 behavior should remain available as a control condition.

No left-to-right eye transition may increment temporal persistence, common-motion evidence, transformation count, or occlusion/reappearance evidence merely because the two views were adjacent in sorted order.

---

# 9. Ego-motion contract

Retinal motion does not equal world motion in an embodied platform.

Preserve:

```text
visual motion evidence
head IMU
neck encoder state
eye encoder state
motor command lineage
```

as distinct records.

Do not force the sensor layer to decide whether motion came from the observer or world unless that specific experimental stage intentionally tests such a transform.

Downstream learning should retain the information necessary to discover those covariations.

---

# 10. Binaural implications

The same architecture must support two ears without collapsing them into mono.

Physical binaural ingestion should preserve sample-aligned channels or separate sensor streams with sufficiently accurate common timing.

The current media gateway's mono conversion remains valid for existing bounded media tests but must not define the future physical-ear path.

A relational auditory derivation may later expose low-level differences such as interaural timing or level differences without installing semantic source-location labels.

---

# 11. Nonsemantic sensory developmental substrate

## 11.1 Problem

Existing Verdant plasticity and later P/Q structures operate on concept IDs.

A dense image or depth field is not directly a member of that developmental graph.

Without a new layer, an exact depth field may remain rich evidence that the higher developmental machinery cannot organize except through engineered M11 region/object promotion.

## 11.2 Required property

Create a bounded local learning substrate below concept semantics.

The substrate should be based on sensor topology, not human object categories.

Potential primitive state at one sensory locus may include:

```text
sensor/rig coordinate
multiscale local intensity/chroma response
local disparity response
local validity/confidence
local temporal change
possibly local motion response
```

Exact primitive choice remains open and should be experimentally justified.

## 11.3 What it may learn

It may learn persistent nonsemantic covariation such as:

```text
locus A and B recur together
this disparity pattern survives a viewpoint change
this retinal pattern predicts a proprioceptive transition
this configuration predicts touch
```

## 11.4 What it may not install

The sensory developmental layer may not name those patterns `chair`, `edge`, `hand`, `face`, `object`, `near`, etc.

## 11.5 Promotion boundary

Repeated stable sensory structure may eventually be promoted into an opaque perceptual operand.

Only then does it need a bridge into the existing concept-scoped developmental substrate.

The promotion mechanism and evidence threshold are intentionally **not yet finalized**. They are a major open design problem.

---

# 12. Storage contract

## 12.1 Preserve exact evidence

Exact source bytes remain immutable and checksummed.

## 12.2 Do not retain every dense field forever by default

Continuous embodiment needs bounded retention.

Recommended direction:

```text
short exact rolling buffer
chunked immutable archives
archive manifest checksums
selective event pinning
explicit eviction records or retention policy
checkpoint references to pinned evidence
```

## 12.3 Checkpoints remain compact

`.vdk` should store state/provenance metadata and references, not hours of raw image/depth arrays.

## 12.4 Derived archives are reproducible

If a derived field is evicted because it can be reproduced exactly from pinned sources plus a known transform, its record should retain enough information to reproduce and verify it.

If exact reproduction is not guaranteed, the field must be retained when scientifically required.

---

# 13. Backward compatibility contract

Do not change an existing v1 checksum formula and then expect old records to validate.

Preferred options:

1. Add new v2 record types and leave v1 untouched.
2. Add an explicit migration layer that validates a historical v1 record under the historical formula, then creates a new v2 representation with lineage back to it.

Migration must never silently rewrite the meaning of historical evidence.

---

# 14. Suggested implementation stages

## Stage 0 — Documentation only

Current branch state.

Exit criterion: design and adversarial tests are internally coherent.

## Stage 1 — Generic multisensor identity model

Implement source observation separation, sensor identity, stream epoch, rig membership, and acquisition identity without stereo math.

Exit criterion: multiple same-modality streams can coexist without grouping corruption and old V5 fixtures still pass.

## Stage 2 — Rig-frame synchronization

Implement exact rig pairing, missing members, clock-domain validation, and presence masks.

Exit criterion: dropped frames and clock mismatches cannot create false pairs.

## Stage 3 — Fixed synthetic stereo derivation

Implement disparity as a derived sensory field using synthetic data with known truth.

Exit criterion: transform reproduces deterministically, no semantic state changes, invalid regions remain invalid, lineage is exact.

## Stage 4 — M11 stream scoping

Make existing perception explicitly single-stream unless a future stereo-aware path is selected.

Exit criterion: alternating left/right inputs cannot accumulate temporal-object evidence.

## Stage 5 — Archive / checkpoint integration

Add compact field records and companion archive handling without embedding dense arrays in `.vdk`.

Exit criterion: checkpoint roundtrip retains lineage; archive corruption is detected; old checkpoints load.

## Stage 6 — Physical fixed stereo rig

Use rigid, synchronized cameras. No eye motion.

Exit criterion: calibration, dropped-frame, motion, low-texture, and restart tests pass in real hardware.

## Stage 7 — Sensory developmental substrate prototype

Add nonsemantic local sensory plasticity as a separate research path.

Exit criterion: it can form persistent opaque sensory structures from recurrence without semantic labels or M11 region proposals.

## Stage 8 — Movable eyes / proprioception

Only after fixed stereo is stable.

Exit criterion: eye pose lineage and geometry remain reproducible under motion and backlash measurement.

---

# 15. Explicitly unresolved questions

The following should remain visible rather than being guessed away:

1. Exact schema and naming of new v2 records.
2. Whether source observation should replace `SensorySampleRecord` or coexist beside a historical v1 adapter.
3. Exact physical hardware synchronization requirement for first rig.
4. Exact stereo matcher to use for the first control implementation.
5. Whether confidence is algorithm-specific, consistency-derived, or both.
6. Exact archive chunk duration and retention policy.
7. Exact local primitive representation for sensory plasticity.
8. Promotion rule from learned sensory structure to opaque perceptual operand.
9. How those operands bind into the existing concept-scoped P/Q substrate without becoming semantic claims.
10. Whether metric depth should ever be learner input by default or only an ablation arm.

These are research decisions, not blanks to be filled by convenience.
