# LLM Handoff — Verdant Multisensory Substrate

## Read this first if you are resuming the work

You are working on the repository:

```text
Captainkoopa42/Verdant-Minds
```

The preserved prework branch is:

```text
V5-Multisensory-Substrate-Prework
```

It was created directly from V5 at:

```text
ec37dfd90f5b4a3c889a7105d7e855692a372b77
```

This branch is intentionally a **research/design branch**, not a claim that the runtime implementation already exists.

Before proposing code, read in this order:

1. `MULTISENSORY_SUBSTRATE_BRANCH_NOTE.md`
2. `docs/multisensory-substrate/README.md`
3. `docs/multisensory-substrate/DESIGN_CONTRACT.md`
4. `docs/multisensory-substrate/ADVERSARIAL_TEST_MATRIX.md`
5. the current V5 files listed below

---

# 1. Original problem

The motivating question was how a future robot running Verdant could have two camera eyes and receive **pure depth perception** without object detection, boxes, semantic labels, navigation logic, or other pre-authored world interpretation.

The desired analogy is biological in architecture:

```text
low-level sensory physiology computes binocular relationship
    ↓
rest of the learning system receives the sensory result
```

The stereo layer is not the cognitive system and is not supposed to know what anything is.

---

# 2. Core design conclusion

Do **not** bolt a `depth detector` onto M11.

Instead separate:

```text
source observation
translation product
relational sensory derivation
rig synchronization
temporal experience
```

Stereo disparity belongs in the low-level relational sensory derivation layer.

However, the review found that this alone is insufficient because current higher Verdant plasticity is concept-scoped. A dense disparity field can be perfectly preserved yet still have no direct developmental path into the existing P/Q machinery.

Therefore the larger research problem is:

> Build the missing nonsemantic sensory developmental substrate between dense sensation and concept-level Verdant cognition.

---

# 3. Current code files that matter

Inspect these on V5 or on the prework branch before modifying anything.

## `verdant_sensory/pipeline.py`

Important current behavior:

- `NativeSamplePacket` already carries stream ID, sequence, timestamp, modality, media type, exact bytes, clock domain, shape/rate/channels, metadata.
- exact native payloads are archived before semantic interpretation.
- the translator creates compact low-level feature vectors/signatures.
- `_synchronize()` currently stops when a second sample of the same modality appears in the candidate group.
- `_group_summary()` is keyed by modality and therefore cannot represent multiple same-modality sensors cleanly.
- event assembly currently counts individual samples toward `maximum_samples_per_event`.

## `verdant_sensory/archive.py`

Important current behavior:

- deterministic exact native archive;
- `ZIP_STORED`;
- derived features are intentionally excluded from the native manifest;
- excellent bounded-run provenance, but continuous raw embodiment would produce huge storage volume.

## `verdant_kernel/models.py`

Important current behavior:

- current `SensoryPolicy.minimum_modalities_per_group` assumes the two-modality M10 world;
- `SensorySampleRecord` stable ID includes translator revision;
- `SynchronizationGroupRecord` and `TemporalEventRecord` stable IDs checksum their current record contents;
- `ObjectObservationInput.position` and `.motion` are 2D;
- state schema contains current sensory/perception records directly.

## `verdant_kernel/checkpoint.py`

Important current behavior:

- checkpoint state is serialized and later directly validated as `KernelState`;
- do not casually change historical record checksum semantics or required fields without versioning/migration.

## `verdant_perception/pipeline.py`

Critical current issue for two eyes:

- it gathers all `VISION` samples in selected events;
- sorts them into one sequence;
- carries one prior-region state across them.

With two eyes:

```text
L0 R0 L1 R1
```

can be treated like four temporal frames.

This can turn binocular parallax into fake motion/persistence/transformation evidence.

Any implementation must make M11 explicitly stream/rig scoped before multiple visual sensors are allowed through it.

## `verdant_objects/pipeline.py`

Important current behavior:

- object tracking remains evidence-preserving and nonsemantic until governed promotion;
- object associations currently work with 2D image position/motion;
- M11 is the current engineered bridge from raw image regions into proto-object concepts.

## `verdant_plasticity/pipeline.py`

Critical architectural fact:

- plasticity is concept-scoped;
- workspace binding refs are filtered to existing concept IDs;
- learned plasticity associations join concept IDs.

Dense sensory fields do not automatically become members of this substrate.

## `verdant_structures/pipeline.py`

Critical architectural fact:

- later earned structures are built from concept-level plasticity associations;
- this confirms the need for a separate sensory-developmental layer if perceptual organization is meant to be earned below concepts.

## `verdant_media/gateway.py`

Important embodiment warning:

- multichannel audio is currently averaged to mono;
- video audio extraction requests one channel;
- this is fine for current media milestones but must not define a future binaural physical-sensor path.

## `FUTURE_MOTOR_IMPLEMENTATION_DESIGN.md`

Important design alignment:

- future motor design already separates intention, issued command, native telemetry, and observed physical consequence;
- reuse that same epistemic discipline for proprioception and moving-eye telemetry.

---

# 4. Bugs / architectural traps already identified

Do not rediscover these and then accidentally ship a partial fix.

## Trap A — one-sample-per-modality synchronization

Current same-modality sensors can split groups incorrectly.

A simple change from `modality` to `stream_id` is still not enough because not all sensors require the same synchronization semantics.

Use explicit rig/acquisition relationships.

## Trap B — nearest-time stereo pairing

Do not pair `left frame n+1` with `right frame n` because the timestamps are close.

Prefer shared hardware capture ID / trigger identity.

Missing must remain missing.

## Trap C — comparing unrelated clock domains

`clock_domain` currently exists as metadata, but numeric timestamps are compared directly during synchronization.

Future exact sync must require common clock domain or explicit mapping.

## Trap D — sample identity includes translator revision

Physical observation identity and translation-product identity need separation for scientific replay.

## Trap E — all VISION becomes one movie

M11 must not alternate left/right cameras as temporal frames.

## Trap F — missing encoded as zero

Current summary logic uses zero placeholders. Future multisensor records need explicit presence/validity masks.

## Trap G — event duration shrinks when sensors are added

Raw sample-count caps must not become the primary definition of temporal duration in embodied runs.

## Trap H — dense field archived but developmentally inert

The current higher learning substrate is concept-based. Do not claim that adding a depth array automatically gives P/Q access to spatial structure.

## Trap I — raw archive explosion

Continuous dual-camera raw recording can approach hundreds of GB per hour. Do not put dense history in `.vdk` or assume bounded test archive behavior scales to embodied life.

## Trap J — breaking historical V5 checkpoints

Do not mutate old ID formulas or required schema fields without explicit versioning/migration.

---

# 5. Stereo-specific principles

For a fixed calibrated pair:

```text
Z = f B / d
```

where `d` is disparity.

The preferred research representation is not just a forced depth matrix. Preserve:

```text
disparity
validity
confidence/consistency
```

and optionally preserve metric depth as a separate derived product.

Invalid correspondence must remain unknown.

Stereo is nonsemantic but not assumption-free. Calibration, rectification, matcher choice, and matcher parameters are part of the sensory physiology and must be versioned/provenanced.

---

# 6. Why timing is stricter than current M10 tolerance

Current V5 default synchronization tolerance is 20 ms.

For simplified lateral relative motion:

```text
d_true = fB/Z

d_timing ~= fv DeltaT / Z

ratio ~= v DeltaT / B
```

With a 6 cm baseline and 20 ms skew:

```text
0.1 m/s -> ~3.3% disparity contamination
0.5 m/s -> ~16.7%
1.0 m/s -> ~33.3%
```

Therefore stereo should use hardware pairing / capture identity when possible. Broad multimodal temporal grouping belongs at a higher layer.

---

# 7. Proposed conceptual data model

Do not treat these names as final APIs. They are the separation to preserve.

```text
SourceObservation
    physical acquisition identity
    sensor identity
    stream epoch
    exact bytes / native telemetry

TranslationProduct
    one source observation
    translator kind/revision/config
    compact low-level output

DerivedSensoryField
    multiple source refs
    transform/calibration refs
    disparity/depth/validity/confidence
    external dense archive

RigFrame
    rig + acquisition identity
    expected/present/missing members
    exact sync/skew state

ExperienceBundle
    looser cross-rig temporal association

SensoryDevelopmentalState
    bounded nonsemantic local plasticity
    no object labels
```

---

# 8. The missing sensory developmental layer

Do not solve this by creating a canonical concept for every pixel.

The suggested direction is local, retinotopic/multiscale, bounded sensory loci whose state may include:

```text
sensor topology coordinate
local luminance/chroma response
local disparity response
local temporal change
validity/confidence
```

The layer may learn recurrence/covariation but not semantic categories.

Examples of permissible learned regularity:

```text
these loci recur together
this pattern survives viewpoint change
this retinal change predicts this joint change
this configuration predicts touch
```

Stable sensory structures may later be promoted into **opaque perceptual operands**, which can then bridge into the existing concept-scoped P/Q substrate.

Exactly how that promotion works remains intentionally unresolved.

---

# 9. Keep M11 as a control arm

Do not delete the engineered region pipeline.

It is scientifically useful to compare:

```text
engineered region/object path
vs
sensory-developmental path
```

This can reveal whether learned perceptual organization is slower, more robust, more compact, stranger, or more general than the engineered route.

---

# 10. First implementation sequence if work resumes

Do not begin with moving robot eyes.

Recommended order:

1. Preserve old V5 behavior with compatibility tests.
2. Separate physical source observation identity from translation identity.
3. Add explicit sensor identity / stream epoch / rig / acquisition identity.
4. Implement rig-frame synchronization with missing members and clock-domain validation.
5. Make M11 explicitly single-stream by default.
6. Build synthetic fixed-stereo derived fields with exact known truth.
7. Add disparity validity/confidence and corruption tests.
8. Add external derived-field archives and checkpoint references.
9. Test fixed synchronized physical cameras.
10. Only then prototype the sensory developmental substrate.
11. Only after fixed stereo is trustworthy add eye actuation/proprioception.

---

# 11. Things you must not assume

Do not assume:

- `stream_id` alone is a permanent physical sensor identity;
- all sensors use the same clock;
- timestamps that look close are comparable;
- invalid depth is zero;
- current M11 is stereo-safe;
- current media audio path is binaural-safe;
- a depth field is automatically learnable by P/Q;
- dense arrays belong in kernel checkpoint state;
- changing a Pydantic record definition is harmless to old checkpoints;
- the user wants object detection, boxes, SLAM, or semantic spatial rules in this layer.

---

# 12. Definition of success

A first successful multisensory substrate should be able to ingest a synthetic or real fixed stereo pair and truthfully say, in data terms only:

```text
these are the two exact source observations
this is the exact acquisition relationship
this is the calibration/transform used
this is the disparity field we derived
these pixels are valid
these pixels are uncertain/unknown
this is the exact evidence lineage
```

while also guaranteeing:

```text
no semantic concepts were installed
no left/right frame was treated as temporal motion
no missing mate was replaced with a nearby frame
no unrelated clocks were compared
no historical V5 checkpoint semantics were rewritten
```

Anything beyond that belongs to later developmental learning, not the stereo transducer.

---

# 13. Final handoff statement

The work is not `add depth perception`.

The work is to create an evidence-preserving **sensory nervous system layer** that lets Verdant receive multiple physical organs and low-level relational senses without a human-authored ontology being smuggled in between the world and the learner.

Stereo depth is the first pressure test because two eyes expose almost every hidden single-sensor assumption at once.

If you are the next model picking this up, start by trying to break `DESIGN_CONTRACT.md` and `ADVERSARIAL_TEST_MATRIX.md` before writing implementation code.
