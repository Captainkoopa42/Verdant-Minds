# Multisensory Substrate Adversarial Test Matrix

## Purpose

This file is the `beat it bloody` checklist for the multisensory substrate.

The goal is not to prove that a demo works once. The goal is to force the design through the failure modes most likely to corrupt embodied learning while still producing superficially plausible output.

A future implementation should not be treated as trustworthy until the relevant test groups pass.

---

# 1. Baseline preservation tests

## T-001 — Existing V5 sensory fixtures still pass

**Setup:** Run all current V5 sensory tests unchanged after the multisensor changes.

**Pass:** Existing one-camera / one-audio behavior remains valid.

**Failure means:** New embodiment support broke historical V5 behavior.

## T-002 — Existing M11 single-camera perception fixtures still pass

**Setup:** Run current `tests/test_perception_phase.py` unchanged.

**Pass:** Moving-region, occlusion, reappearance, lookalike, still-image, semantic-boundary, stale-report, atomicity, and proto-object tests retain expected behavior.

## T-003 — Existing V5 checkpoints load

**Setup:** Load representative checkpoints created before multisensory changes.

**Pass:** No historical stable-ID or schema validation failure.

---

# 2. Same-modality multisensor tests

## T-010 — Two visual sensors coexist

**Input:** `left_eye` and `right_eye` frames at the same acquisition instant.

**Pass:** Both observations exist simultaneously. Neither overwrites or terminates the other because both are `VISION`.

## T-011 — Two audio sensors coexist

**Input:** left/right microphone blocks with the same acquisition identity.

**Pass:** Both remain distinct; no mono collapse in the native physical path.

## T-012 — Four same-modality sensors coexist

**Input:** four cameras in one broad experience window.

**Pass:** grouping behavior is determined by declared rig membership/contracts, not modality uniqueness.

---

# 3. Exact acquisition pairing tests

## T-020 — Correct stereo pair

**Input:**

```text
left capture 100
right capture 100
```

**Pass:** One complete stereo rig frame is produced.

## T-021 — Dropped left frame

**Input:**

```text
right capture 101
left capture 102
right capture 102
```

**Pass:** capture 101 records left missing; right 101 is never paired with left 102.

## T-022 — Dropped right frame

Symmetric to T-021.

## T-023 — Duplicate acquisition ID from one sensor

**Input:** two different payloads both claim `left capture 103`.

**Pass:** integrity error / explicit conflict. Never silently pick one.

## T-024 — Out-of-order arrival

**Input:** captures arrive in network order 105, 103, 104.

**Pass:** acquisition identity allows correct reconstruction within configured buffering rules. Arrival order is not physical time.

## T-025 — Late mate outside retention window

**Pass:** explicit incomplete record or documented late-reconciliation policy. Never fabricate a pair.

---

# 4. Clock-domain tests

## T-030 — Shared hardware clock

**Pass:** skew is computed normally.

## T-031 — Different clock domains with no mapping

**Input:** numerically similar timestamps from unrelated domains.

**Pass:** cross-domain skew comparison is refused or marked incomparable.

## T-032 — Valid clock mapping

**Pass:** mapped time and uncertainty are retained with mapping provenance.

## T-033 — Stale clock mapping

**Setup:** clock drift exceeds the calibration/mapping validity interval.

**Pass:** mapping is rejected or uncertainty expands enough to fail an exact-sync contract.

## T-034 — Clock reset mid-run

**Pass:** new stream epoch or explicit clock discontinuity; no false backward-time corruption of the physical sensor identity.

---

# 5. Sensor restart and stream integrity tests

## T-040 — Camera restart

**Before:** sensor `eye_left`, stream epoch A, sequence 4000.

**After restart:** same sensor, stream epoch B, sequence 0.

**Pass:** accepted as a new stream from the same physical sensor. Historical epoch A is preserved.

## T-041 — Sequence rollback within same epoch

**Pass:** rejected.

## T-042 — Payload changed under reused observation identity

**Pass:** rejected as integrity violation.

## T-043 — Sensor replacement

**Setup:** physical left camera hardware is replaced.

**Pass:** new sensor/device identity or explicit replacement lineage. Calibration from old device is not silently reused.

---

# 6. Source observation versus translation tests

## T-050 — Same source, translator revision 1 and 2

**Pass:** one source observation; two translation products.

## T-051 — Translation configuration change

**Pass:** source identity remains stable; translation product identity changes.

## T-052 — Translation tampering

**Pass:** checksum/provenance validation fails without invalidating the exact source observation.

## T-053 — Recompute derived product

**Pass:** deterministic transform plus identical sources/config reproduces the same derived checksum where determinism is promised.

---

# 7. Stereo geometry truth tests

These should start with synthetic images where truth is known independently of the learner.

## T-060 — Constant known disparity plane

**Input:** synthetic rectified stereo pair with exact 8-pixel shift.

**Pass:** valid region returns expected disparity within declared numeric tolerance.

## T-061 — Double disparity

**Input:** same scene at 16-pixel disparity.

**Pass:** disparity doubles; no semantic label such as `closer` is created.

## T-062 — Metric conversion

**Input:** known `f`, `B`, and `d`.

**Pass:** optional metric depth product matches `Z = fB/d` within tolerance and remains a separate derivation from disparity.

## T-063 — Multiple depth planes

**Pass:** field preserves spatial variation rather than collapsing to one summary distance.

## T-064 — Slanted plane

**Pass:** continuous disparity gradient is preserved.

---

# 8. Ambiguity / unknown tests

## T-070 — Textureless wall

**Pass:** unsupported pixels become invalid/low-confidence, not plausible invented depth.

## T-071 — Repeating stripe pattern

**Pass:** ambiguity is reflected in validity/confidence or consistency checks.

## T-072 — Specular reflection

**Pass:** matcher failure does not become semantic certainty.

## T-073 — Transparent surface / glass

**Pass:** invalid/ambiguous measurements are preserved as such.

## T-074 — Occlusion boundary

**Pass:** pixels visible in only one eye are not forced into correspondence.

## T-075 — Complete darkness

**Pass:** no false dense depth field with high confidence.

## T-076 — Saturated image

Same principle as T-075.

---

# 9. Photometric mismatch tests

## T-080 — Left/right exposure mismatch

**Pass:** degradation is measurable and confidence/validity behaves consistently.

## T-081 — White-balance mismatch

**Pass:** geometry stage remains nonsemantic and records configuration; unsupported matches remain uncertain.

## T-082 — Sensor noise mismatch

**Pass:** no catastrophic false certainty.

---

# 10. Calibration tests

## T-090 — Correct calibration

**Pass:** baseline synthetic truth.

## T-091 — Wrong baseline

**Pass:** metric depth error is detectable by evaluator; calibration revision is part of derivation provenance.

## T-092 — Wrong focal calibration

Same principle as T-091.

## T-093 — Vertical misalignment

**Pass:** validation or consistency score degrades; system does not pretend quality is unchanged.

## T-094 — Calibration file changed without revision

**Pass:** checksum mismatch / integrity failure.

## T-095 — Physical camera moved after calibration

**Pass:** physical validation test can detect geometry drift before data is treated as trustworthy.

---

# 11. Timing and motion tests

## T-100 — Static scene, perfect sync

Baseline.

## T-101 — Moving target, controlled skew

Sweep relative velocity and exposure skew.

**Pass:** measured stereo error follows expected degradation; configured contract rejects pairs beyond acceptable skew.

## T-102 — Head motion with static world

**Pass:** source visual fields, IMU/head telemetry, and derived fields remain separately preserved.

## T-103 — Rolling-shutter distortion

**Pass:** quality loss is visible in confidence/validation; no silent assumption of global-shutter geometry.

## T-104 — Motion blur

**Pass:** uncertainty rises or valid coverage falls rather than producing confidently wrong geometry.

---

# 12. M11 cross-eye contamination tests

## T-110 — Alternating left/right identical instant

**Input sequence:**

```text
L0 R0 L1 R1 L2 R2
```

**Pass:** a single-camera temporal tracker never treats `L0 -> R0` as frame-to-frame motion.

## T-111 — Binocular parallax cannot increase common-motion count

**Pass:** object-development evidence does not increase merely because the two cameras view the same scene from different positions.

## T-112 — Binocular parallax cannot count as transformation novelty

Same principle.

## T-113 — One eye occluded

**Pass:** missing right-eye data does not cause a left-eye tracked object to receive a fake temporal occlusion/reappearance event through cross-stream ordering.

---

# 13. Event-duration scaling tests

## T-120 — Two streams versus sixteen streams

**Setup:** same physical one-second experience, different number of sensors.

**Pass:** temporal duration semantics remain comparable. Sensor count alone cannot shrink the event from one second to a fraction of a second.

## T-121 — High-rate IMU plus low-rate camera

**Pass:** IMU sample count does not dominate event-length limits or eject the camera experience merely because it samples faster.

---

# 14. Missing versus zero tests

## T-130 — Silent audio block

**Input:** real all-zero PCM samples.

**Pass:** represented as a valid silent observation.

## T-131 — Missing audio block

**Pass:** presence mask / missing member state differs from T-130.

## T-132 — Valid zero disparity where representation permits it

**Pass:** distinguish from invalid/missing correspondence.

---

# 15. Archive integrity tests

## T-140 — Source payload tamper

**Pass:** exact source archive verification fails.

## T-141 — Derived disparity field tamper

**Pass:** derived-field checksum fails while original left/right source evidence remains valid.

## T-142 — Validity mask tamper

**Pass:** detected separately.

## T-143 — Calibration record tamper

**Pass:** derived product can no longer verify against its claimed transform lineage.

## T-144 — Missing companion archive

**Pass:** checkpoint still loads if state format permits, but evidence is explicitly unavailable; no fabricated field appears.

## T-145 — Wrong archive substituted under same path

**Pass:** hash verification detects substitution.

---

# 16. Storage pressure tests

## T-150 — Rolling buffer overflow

**Pass:** oldest unpinned data expires according to explicit policy; pinned evidence survives.

## T-151 — Event pinning under pressure

**Pass:** evidence referenced by a committed learning event is not silently deleted.

## T-152 — Derived product eviction

**Pass:** if product is declared reproducible, exact transform/source lineage remains sufficient to regenerate it; otherwise it cannot be evicted under a policy that promises later replay.

## T-153 — Archive rotation boundary

**Pass:** a stereo pair or rig frame crossing chunk boundaries retains correct lineage and pairing.

---

# 17. Checkpoint / compatibility tests

## T-160 — New checkpoint roundtrip

**Pass:** all multisensor metadata survives exact save/load.

## T-161 — Old V5 checkpoint roundtrip after new code

**Pass:** load succeeds; historical IDs validate under historical semantics.

## T-162 — New checkpoint opened by migration-aware later runtime

**Pass:** version fields make record interpretation explicit.

## T-163 — Migration idempotence

**Pass:** migrating an already migrated state does not produce different identity/history.

---

# 18. Semantic boundary tests

## T-170 — Stereo ingest creates no concepts

**Pass:** `concepts == {}` in an otherwise empty kernel after stereo ingestion/derivation.

## T-171 — Stereo ingest creates no relations

## T-172 — Stereo ingest creates no claims

## T-173 — Stereo ingest creates no contradictions

## T-174 — Derived field contains no semantic categories

Reject metadata/output that directly encodes human categories.

## T-175 — Depth change creates no `near`/`far` label

Change disparity from 8 to 16 pixels.

**Pass:** sensory geometry changes; no semantic direction label is installed.

---

# 19. Sensory-developmental substrate tests

These apply only once that layer is implemented.

## T-180 — No pixel-to-concept explosion

**Pass:** raw image resolution does not create one canonical concept per pixel/locus.

## T-181 — Local recurrence can create a nonsemantic trace

**Pass:** repeated local configurations alter only the sensory developmental substrate.

## T-182 — Random uncorrelated noise does not saturate the substrate

**Pass:** association count/strength remains bounded and decays under noise.

## T-183 — Repeated rigid sensory configuration can become an opaque perceptual operand

**Pass:** promotion requires recurrence/stability evidence and creates no human semantic label.

## T-184 — M11 disabled

**Pass:** sensory-developmental route can still operate without engineered region proposals.

## T-185 — M11 control arm

**Setup:** identical sensory history with M11 enabled versus developmental-only route.

**Pass:** both conditions are separately reproducible and measurable.

## T-186 — Disparity ablation

Compare left/right-only versus disparity-assisted development without changing semantic curriculum.

## T-187 — Metric-depth ablation

Compare disparity versus metric depth as learner-accessible primitives.

---

# 20. Proprioception / moving-eye tests

Only after fixed stereo passes.

## T-190 — Eye encoder replay

**Pass:** exact eye-pose telemetry is synchronized/provenanced with visual acquisition.

## T-191 — Same scene, different vergence

**Pass:** geometry derivation uses correct eye-pose/calibration state or intentionally refuses unsupported geometry.

## T-192 — Servo command versus measured pose disagreement

**Pass:** measured telemetry remains distinct from requested motor command. The system never substitutes command target for observed eye angle.

## T-193 — Backlash

**Pass:** repeated command angle with different measured pose produces different physical provenance as appropriate.

## T-194 — Eye motion during exposure

**Pass:** invalid or degraded geometry can be represented instead of fabricating a clean field.

---

# 21. Binaural tests

## T-200 — Shared-clock stereo audio preserved

**Pass:** channel timing remains sample aligned.

## T-201 — Mono importer control remains unchanged

Existing media test behavior may still intentionally be mono.

## T-202 — Physical binaural path never uses the mono averaging importer

**Pass:** architecture keeps research-media convenience separate from embodied sensor physiology.

## T-203 — Missing ear sample

**Pass:** no pairing with a later sample to fake interaural timing.

---

# 22. Long-run degradation tests

## T-210 — 24-hour synthetic stream

**Pass:** no unbounded in-memory accumulation of dense fields; archive rotation and references remain valid.

## T-211 — Repeated sensor restart

**Pass:** stream epochs remain distinct without losing physical sensor lineage.

## T-212 — Slow clock drift

**Pass:** timing uncertainty / remapping behavior is visible and bounded.

## T-213 — Calibration drift simulation

**Pass:** evaluator detects accuracy degradation; provenance identifies which calibration generated each field.

## T-214 — One degraded eye

Add blur/noise to one eye over time.

**Pass:** confidence/validity and later learning evidence can distinguish degraded input rather than silently treating both eyes as equally reliable.

---

# 23. Red-team questions to ask after every implementation revision

1. Can two sensors of the same modality be silently collapsed?
2. Can the wrong left/right capture ever be paired because timestamps are close?
3. Can unrelated clocks be subtracted?
4. Can missing become zero?
5. Can invalid depth look numerically valid?
6. Can a translator change rewrite physical observation identity?
7. Can left/right parallax masquerade as temporal motion?
8. Can attaching more sensors shorten the experienced world?
9. Can a dense field be stored but remain developmentally inaccessible?
10. Can a sensor algorithm accidentally install a semantic category?
11. Can old checkpoints become unloadable because a checksum formula changed?
12. Can a hardware restart look like corruption or, worse, silently overwrite history?
13. Can calibration change without lineage changing?
14. Can a command target be mistaken for measured proprioception?
15. Can archive pressure silently delete evidence that later learning depends on?

If any answer is `yes`, the design is not finished.
