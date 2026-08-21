# Verdant Multisensory Substrate Prework

## Purpose

This package preserves the current design work for extending V5 from a bounded multimodal media-ingestion system into a genuinely multisensor embodied substrate.

The triggering use case was binocular depth from two robot-eye cameras, with a strict requirement:

> The depth layer must provide only a low-level spatial signal. It must not install object boxes, semantic categories, navigation rules, or designer-authored world meaning.

The review of V5 showed that this is possible, but the correct change is broader than adding a stereo function. Two eyes expose several assumptions in M10/M11 that should be corrected before embodiment work begins.

This document gives the whole idea in one place. `DESIGN_CONTRACT.md` turns it into explicit engineering rules, `ADVERSARIAL_TEST_MATRIX.md` lists the tests intended to break it, and `LLM_HANDOFF.md` is optimized for future resumption by another model.

---

# 1. Current V5 facts that were verified

The following are properties of V5 at base commit `ec37dfd90f5b4a3c889a7105d7e855692a372b77`.

## 1.1 Native sensory packets already preserve the right low-level evidence

`verdant_sensory/pipeline.py` defines `NativeSamplePacket` with:

- `stream_id`
- `sequence_number`
- `timestamp_ns`
- `modality`
- `media_type`
- exact `payload` bytes
- `clock_domain`
- optional `shape`
- optional sample rate and channel names
- metadata

This is a strong starting point because V5 already treats exact native evidence as distinct from later translation.

The `.vsa.zip` sensory archive preserves exact payload bytes and excludes derived features from the native manifest. This means future stereo or other derived sensory products can retain exact lineage back to the source observations.

## 1.2 The current native modalities are only vision and audio

`NativeModality` currently serves the M10/M11 world of `VISION` and `AUDIO`.

That is not itself a problem. The problem is that several later data structures currently treat *modality* as though it were also *sensor identity*.

## 1.3 Current synchronization assumes at most one sample per modality in a group

The current synchronizer greedily walks time-ordered records and stops when it encounters another sample whose modality is already present in the group.

With:

```text
left_eye   VISION
right_eye  VISION
left_ear   AUDIO
right_ear  AUDIO
```

all inside the time tolerance, current V5 can split them into malformed groups such as:

```text
GROUP 1: left_eye
GROUP 2: right_eye + left_ear
GROUP 3: right_ear
```

This is worse than merely lacking stereo support: it can associate the wrong physical organs because duplicate-modality samples terminate the greedy group.

## 1.4 Group summaries also collapse same-modality sensors

`_group_summary()` constructs a dictionary keyed by modality. If two visual samples were somehow present, only one visual sample can survive in the dictionary.

The summary is also hard-coded around one vision summary and one audio summary. Missing values are represented with zeros, which conflates a valid zero-valued signal with absence.

## 1.5 M11 currently treats every VISION sample as one temporal movie

`verdant_perception/pipeline.py` gathers all visual samples from selected temporal events and sorts them by timestamp / sequence / sample ID.

For two eyes, the resulting order can be:

```text
left t0
right t0
left t1
right t1
```

M11 then carries one `prior_regions` state across that sequence.

Therefore binocular parallax can be mistaken for temporal motion. A region seen from the left eye could be treated as the temporal predecessor of the same scene seen from the right eye.

Before two eyes are connected, M11 must become explicitly stream- or rig-scoped.

## 1.6 Current object observations are two-dimensional

The object pipeline currently receives `position: tuple[float, float]` and `motion: tuple[float, float]`.

This is fine for current M11 tests, but it must not be mistaken for a complete embodied spatial representation.

## 1.7 The media gateway currently destroys spatial audio

`verdant_media/gateway.py` averages multichannel audio into mono. Video audio extraction explicitly requests one output channel.

This is appropriate for the current milestone tests but cannot be reused as the physical binaural path because interaural timing and level differences are part of the sensory signal.

## 1.8 Event length currently depends on how many sensors are attached

`maximum_samples_per_event` counts individual samples.

At a fixed frame rate, adding more simultaneous sensor streams makes a temporal event reach its sample cap sooner. That accidentally couples anatomy to experienced event duration.

A future embodied design should cap by rig frames, experience bundles, or duration—not by raw sensor count alone.

## 1.9 Sensory sample identity currently includes translator revision

The sensory sample stable ID includes `translator_revision`.

This means the exact same physical frame translated by revision 1 and revision 2 becomes two different `SensorySampleRecord` identities.

For long-term scientific replay, physical observation identity should be separated from translation-product identity.

## 1.10 Dense sensation does not currently have a direct path into P/Q development

This is the largest architectural discovery.

V5 plasticity is concept-scoped. Workspace items contribute to plasticity through bindings that are concept IDs. Plasticity associations join concept IDs. Later earned structures are built from those concept-level associations.

Therefore a perfect 1280x720 disparity field can be archived and translated without automatically becoming something the P/Q developmental machinery can organize.

Today, M11 provides the practical bridge:

```text
pixels
  -> region hypotheses
  -> object candidates
  -> proto-object concept
  -> concept-scoped plasticity / structures
```

If the research goal is to let Verdant earn perceptual organization rather than having M11 install region grouping, then a new **nonsemantic sensory developmental substrate** is required.

## 1.11 Current archives are excellent for bounded experiments but not continuous life

The native sensory archive uses deterministic `ZIP_STORED` exact-byte preservation.

That is ideal for reproducible bounded runs.

It becomes enormous for continuous embodied data. Two raw 1280x720 RGB8 cameras at 30 FPS are about 166 MB/s before derived fields. Adding one float16 1280x720 disparity field adds about 55 MB/s. The total is roughly 221 MB/s, or about 796 GB/hour in decimal units.

Continuous embodiment therefore needs rolling buffers, archive rotation, selective retention, and evidence pinning while preserving exact provenance.

## 1.12 Historical V5 records should not have their meaning silently changed

Synchronization group IDs and temporal event IDs are checksummed from their record contents.

Checkpoint loading validates stored state directly against current model definitions.

Changing the semantics or ID formula of existing record classes risks making historical V5 checkpoints unloadable.

The safer path is versioned new records or explicit migration rather than redefining old records in place.

---

# 2. Core idea

The embodied sensory stack should distinguish five things that are currently too close together:

```text
physical sensor
    ↓
source observation
    ↓
single-sensor translation
    ↓
relational sensory derivation
    ↓
synchronized experiential organization
```

Then higher perception and cognition operate downstream.

A binocular depth path should therefore look like:

```text
LEFT CAMERA SOURCE OBSERVATION ----┐
                                   ├─> stereo derivation -> disparity field
RIGHT CAMERA SOURCE OBSERVATION ---┘

LEFT source remains preserved
RIGHT source remains preserved
derived field has exact lineage to both
```

The stereo stage does **not** know:

- person
- hand
- chair
- wall
- obstacle
- safe
- reachable
- near
- far

It computes a geometric relationship between two sensor fields.

---

# 3. Why disparity is a good primitive

For fixed calibrated stereo cameras:

```text
Z = f B / d
```

where:

- `Z` is metric range,
- `f` is focal length in pixel units,
- `B` is camera baseline,
- `d` is binocular disparity.

The research system does not have to give Verdant `Z`.

It can preserve:

```text
left retinal field
right retinal field
disparity field
validity field
confidence field
```

and optionally metric depth as a separate derived representation.

This enables ablation studies:

```text
A: left/right only
B: left/right + confidence/correspondence
C: left/right + disparity
D: left/right + metric depth
E: left/right + disparity + metric depth
```

Ground-truth geometry can be used by the evaluator without being installed into Verdant's semantic state.

---

# 4. Stereo is nonsemantic, but it is not assumption-free

A conventional stereo matcher still contains physical / mathematical priors:

- camera calibration
- lens correction
- epipolar geometry / rectification
- correspondence constraints
- matcher configuration
- sometimes smoothness or neighborhood assumptions

These are not object categories, but they are assumptions.

Therefore two different experiments should remain possible:

1. Give Verdant a biologically analogous low-level disparity primitive and study what spatial cognition develops.
2. Give Verdant only the two retinal fields and study whether useful correspondence / depth structure can be learned.

The architecture should preserve both options rather than collapsing them into one philosophical answer.

---

# 5. Unknown is a real sensory state

A stereo field must never force every pixel to have a believable number.

Stereo can fail on:

- textureless surfaces
- repeated patterns
- reflections
- glass
- occlusions
- darkness
- motion blur
- exposure mismatch
- calibration drift
- rolling shutter

The primitive should therefore carry at least:

```text
D(x,y) = disparity or range value
V(x,y) = validity / knownness
C(x,y) = confidence / consistency
```

Invalid is not zero and is not infinity unless the measurement actually establishes that value.

The sensory apparatus must be allowed to say `unknown`.

---

# 6. Sensor identity, stream identity, modality, and rig membership are different

A future observation should not rely on one field to mean all of these things.

Conceptually:

```text
sensor_id       = physical organ/device identity
stream_id       = one acquisition session / epoch
modality        = vision, audio, proprioception, etc.
rig_id          = synchronized physical assembly
acquisition_id  = shared capture/sample identity within the rig
```

This solves several real problems:

- two eyes share one modality but are different sensors;
- a camera can reboot and restart sequence numbering without becoming a new physical eye;
- stereo pairing can use a shared acquisition ID instead of nearest timestamp;
- a binaural pair can share a sample clock;
- exact lineage survives device restarts.

---

# 7. Synchronization must become hierarchical

There should not be one universal rule saying that everything within N milliseconds is one experience.

Different relationships need different contracts.

Example:

```text
STEREO RIG
    left eye
    right eye
    exact capture pairing
    tight skew validation

BINAURAL RIG
    left ear
    right ear
    sample-aligned shared clock

HEAD STATE RIG
    IMU
    neck encoders
    eye encoders

LOCAL RIG FRAMES
    ↓
CROSS-RIG EXPERIENCE BUNDLE
    ↓
TEMPORAL EVENT
```

For stereo, timestamp tolerance should validate a pair, not create the pair when a stronger acquisition identity is available.

If frame 81724 is missing from the left eye, the correct representation is:

```text
capture 81724
left  = missing
right = present
```

not pairing the right frame with left frame 81725.

---

# 8. Clock domains must become operational, not merely archival metadata

V5 already stores `clock_domain`, but current synchronization compares numeric timestamps directly.

Future rules should be:

- exact synchronization is allowed inside a known shared clock domain;
- cross-domain synchronization requires an explicit clock mapping;
- mapped timestamps carry uncertainty;
- no code may subtract timestamps from unrelated clock domains and treat the result as physical skew.

A mapped observation may preserve:

```text
source_timestamp
source_clock_domain
normalized_timestamp
clock_mapping_ref
timing_uncertainty_ns
```

---

# 9. Moving eyes should add proprioception, not semantic interpretation

For fixed cameras, geometry is static.

For movable eyes, the same retinal disparity depends on eye pose.

A future sensory state may include:

```text
left retinal field
right retinal field
left eye pan/tilt telemetry
right eye pan/tilt telemetry
head pose / IMU
```

Eye angle should enter as native proprioceptive telemetry, not as commands such as `LOOKING_LEFT`.

The first physical experiment should still use a rigid fixed stereo rig. Add eye motion only after fixed geometry is trustworthy.

---

# 10. M11 should remain, but it should become a control arm

Do not delete the existing region / object path.

It is valuable because it provides an engineered reference condition:

```text
M11 engineered region route
vs
sensory-developmental route
```

This makes future experiments much stronger.

M11 does, however, need stream/rig scoping before multiple cameras can be present safely.

---

# 11. The missing layer: nonsemantic sensory plasticity

This is the central architectural addition suggested by the review.

Do **not** turn pixels into concepts.

Instead introduce a bounded local sensory substrate whose primitives are things such as:

```text
retinotopic / sensor-topology locus
local luminance / chromatic activity
local disparity activity
local temporal change
validity / confidence
sensor or rig coordinates
```

These remain nonsemantic.

Local recurrence and coactivation can then produce persistent developmental traces:

```text
these local activities recur together
these disparity patterns covary
this configuration survives observer motion
this visual state predicts touch
this proprioceptive change predicts retinal change
```

Stable recurring sensory configurations can eventually earn promotion into **opaque perceptual operands**.

Only after that promotion do they need to enter the existing concept-scoped plasticity / P / Q world.

This preserves the research distinction:

```text
raw sensation
  !=
engineered segmentation
  !=
earned perceptual organization
  !=
semantic concept
```

---

# 12. Recommended future architecture

```text
PHYSICAL WORLD

    ↓

SOURCE OBSERVATIONS
exact bytes / native telemetry

    ↓

SINGLE-SENSOR TRANSLATIONS
nonsemantic low-level measurements

    ↓

RELATIONAL SENSOR DERIVATIONS
stereo disparity, binaural differences, etc.

    ↓

RIG FRAMES
exact acquisition relationships

    ↓

EXPERIENCE BUNDLES / TEMPORAL EVENTS

    ├───────────────> M11 ENGINEERED CONTROL ROUTE
    │                     region hypotheses
    │                     object candidates
    │                     proto-object promotion
    │
    └───────────────> SENSORY DEVELOPMENTAL ROUTE
                          local sensory plasticity
                          recurring perceptual structure
                          opaque perceptual operand

                                  ↓

                         EXISTING VERDANT COGNITION
                         concept plasticity
                         earned structures P
                         higher structures Q
                         compilation / refolding
```

---

# 13. Storage strategy for actual embodiment

Do not put dense sensory fields directly into `.vdk` state.

A future continuous design should use:

```text
short exact rolling buffer
+ chunked append-only sensory archives
+ per-record checksums
+ selective event pinning
+ evidence references from checkpoint state
+ archive rotation
```

A checkpoint should know *what evidence exists and how to verify it*, not contain hours of raw camera data itself.

Native hardware compression may be acceptable when it is itself the preserved source representation. Derived scientific products should record the exact transform configuration that produced them.

---

# 14. Compatibility rule

Do not silently redefine historical V5 record classes whose stable IDs are already part of saved checkpoints.

Prefer:

```text
SynchronizationGroupRecord v1   # historical V5 semantics
RigFrameRecord v2               # new multisensor semantics
```

or an explicit migration layer that can verify old IDs under their original formula.

History should remain replayable under the rules that created it.

---

# 15. Research questions this architecture makes possible

Once the substrate exists, Verdant can be tested on questions that are difficult to ask cleanly in conventional pretrained systems:

- Does binocular disparity accelerate stable objecthood?
- Can metric depth be learned from disparity plus proprioception and touch?
- Can a sensory substrate discover egocentric spatial regularity without object labels?
- Does M11 engineered segmentation help early learning but constrain later representations?
- Can a developmental sensory route outperform or reorganize beyond the engineered region route?
- Can Verdant learn to compensate for moving eyes through proprioceptive covariation?
- Can it distinguish retinal motion caused by self-motion from world motion without having that distinction hard-coded?
- What happens if one sensory channel becomes unreliable or biased?
- What spatial abstractions emerge when distance labels are never supplied?

---

# 16. Current conclusion

The original question was `how do we add pure depth perception?`

The code review changed the question to:

> **What is Verdant's equivalent of a nervous system between raw sensors and concept-level developmental cognition?**

V5 already has two strong ends of that system:

1. evidence-preserving sensory ingestion;
2. higher developmental / cognitive machinery.

The missing work is the multisensor temporal substrate and the nonsemantic developmental tissue between dense sensation and concept-scoped learning.

That is what this branch is for.
