# Verdant Minds Independent Rebuild — Milestone 11

## User Media Import and Native Perceptual Binding

Milestone 11 adds two connected capabilities:

1. a user-facing gateway for chosen files and prior Verdant runs;
2. nonsemantic visual-region continuity feeding the existing earned objecthood pathway.

```text
chosen file or run package
→ exact preservation and verification
→ bounded decoding when supported
→ native visual/audio events
→ low-level visual regions
→ temporal continuity and competing identity candidates
→ earned proto-object support
→ Three Kings and Council
→ canonical promotion
```

No LLM, foundation model, pretrained object detector, speech recognizer, semantic embedding model, or cloud cognition is present.

No hardware-output implementation was added.

## User file gateway

The runner accepts repeated files, recursively expanded folders, graphical file selection, direct checkpoints, portable Verdant run packages, and generic ZIPs containing checkpoints.

Every regular source file within the configured size limit is first written to a deterministic `.vmi.zip` archive containing its exact bytes and verified import manifest.

### Actively decoded media

- images: PNG, JPEG, WebP, BMP, TIFF;
- audio: WAV, FLAC, MP3, OGG, M4A, AAC, AIFF;
- video: MP4, MOV, MKV, WebM, AVI, M4V.

Actual decoder support also depends on the encoding libraries installed on the running machine.

### Unsupported material

An unsupported file is still preserved. Verdant records that translation is unavailable and that semantic interpretation was not attempted.

### Bounded processing

The caller can set:

- start and end time;
- sampled video frame rate;
- maximum frame count;
- audio packet duration;
- maximum source size;
- whether a video audio track is included;
- archive-only mode;
- perception-disabled mode;
- inspection-only mode.

## Run package behavior

### Inspect

Returns checkpoint metadata and metrics without providing a mutable kernel.

### Continue

Loads the exact verified state and continues its existing lineage.

### Branch

Creates a distinct lineage branch while preserving the historical `kernel_id` used by existing Council, workspace, sensory, and perceptual records.

The branch receives:

- a content-derived `branch_id`;
- branch label;
- incremented generation;
- parent checkpoint hash;
- ancestor identity entry.

This fixed an important integrity problem. Replacing the kernel identity during branching invalidated historical records that were correctly notarized under the parent identity. The final branch design marks divergence without rewriting history.

## Native perceptual binding

The perception pipeline reads exact verified visual payloads from `.vsa.zip` archives.

### Region proposal

Frames are converted into temporary low-level regions using measured luminance deviation, morphology, and connected components. Each region preserves:

- exact source sample and event;
- normalized bounds and centroid;
- area;
- luminance statistics and quantiles;
- compact histogram;
- edge fraction;
- low-resolution appearance signature.

A region is a temporary hypothesis, not an object.

### Temporal continuity

Across frames, the pipeline compares:

- appearance distance;
- position and trajectory;
- size and shape change;
- continuity with the previous match;
- temporary absence;
- possible reappearance.

Similarity can propose a match but cannot by itself establish identity.

### Objecthood integration

Region observations enter the existing Milestone 7 candidate pathway. Tracking remains nonsemantic. Only accumulated evidence can make a candidate eligible for promotion, and promotion still requires Council authorization.

## Controlled demonstration

The demonstration selected five user-style files:

- one PNG image;
- one WAV audio clip;
- two short MP4 clips;
- one unsupported binary file.

### Gateway result

| Measurement | Result |
|---|---:|
| Selected files | 5 |
| Exact source archives | 5 |
| Files translated | 4 |
| Preserved without translator | 1 |
| Native sensory archives | 4 |
| Visual samples | 17 |
| Audio samples | 5 |
| Total native samples | 22 |
| Temporal events | 4 |

The unsupported binary remained preserved without fabricated interpretation.

### Perceptual result

The still image and two clips produced:

| Measurement | Result |
|---|---:|
| Perceptual binding events | 3 |
| Visual frames processed | 17 |
| Region observations | 15 |
| Object candidates | 1 |
| Visible observations in developed candidate | 15 |
| Independent episodes | 3 |
| Persistence count | 12 |
| Transformation count | 7 |
| Common-motion count | 11 |
| Occlusions | 1 |
| Reappearances | 1 |
| Objecthood support | **0.80** |

Before promotion:

```text
concepts:       0
relations:      0
claims:         0
contradictions: 0
```

After Council-authorized promotion:

```text
concepts:       1
relations:      0
claims:         0
contradictions: 0
```

The concept received the generated identity:

```text
proto-object-0d8ab3ac5b93
```

No human category was preinstalled.

## Persistence and run lineage

The final demonstration produced:

- `milestone_11_media_perception_demo.vdk`;
- exact checkpoint reload;
- `milestone_11_demo_run.vrun.zip`;
- successful package inspection;
- successful branch creation;
- preserved historical kernel identity;
- distinct `branch_id` and generation 1.

## Safeguards

Milestone 11 tests and enforces:

- source preservation before decoding;
- exact archive and payload checksums;
- bounded media decoding;
- unknown-file archive-only behavior;
- safe ZIP member validation;
- deterministic run packages;
- read-only run inspection;
- explicit continuation and branching;
- pure perceptual inspection;
- stale-report rejection;
- altered-report rejection;
- atomic failure without partial state mutation;
- still images cannot invent motion;
- visually similar but conflicting tracks can remain separate;
- occlusion and reappearance are explicit evidence;
- perceptual binding cannot create semantic records;
- exact checkpoint persistence;
- deterministic replay.

## Test result

```text
124 passed
```

## Current boundary

This phase is an earned-perception research pathway, not general visual understanding.

It does not yet provide:

- learned segmentation;
- learned visual feature extraction;
- depth reconstruction;
- dense optical flow;
- category recognition;
- face recognition;
- speech recognition;
- causal attribution from audio coincidence;
- long-duration archive rotation;
- learned attention allocation;
- autonomous grammar induction;
- cross-modal word grounding.

The strongest current claim is:

> Verdant can preserve user-selected native media, derive low-level visual-region hypotheses, maintain and challenge candidate continuity across frames and episodes, and promote one unnamed proto-object only after accumulated evidence and Council authorization.
