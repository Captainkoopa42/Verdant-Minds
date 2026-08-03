# Verdant User Media and Run Import Guide

This guide explains how to give Verdant your own images, audio clips, video clips, folders, unknown files, checkpoints, and portable run ZIPs.

## Core rule

Verdant preserves the exact source file before decoding it.

```text
your selected file
→ exact source archive (.vmi.zip)
→ format-specific decoding when supported
→ native sample archive (.vsa.zip)
→ temporal/perceptual processing
→ canonical checkpoint and run package
```

A file being accepted does not mean it was understood. Unsupported files are retained exactly and reported as untranslated.

## Quick start

Open a terminal in the rebuild directory:

```bash
cd /path/to/verdant_rebuild
```

### Image

```bash
python run_verdant_media.py \
  --input "C:/Users/You/Pictures/test.png" \
  --output-dir "image_test"
```

### Audio clip

```bash
python run_verdant_media.py \
  --input "C:/Users/You/Recordings/test.wav" \
  --output-dir "audio_test"
```

### Short video section

```bash
python run_verdant_media.py \
  --input "C:/Users/You/Videos/test.mp4" \
  --start 5 \
  --end 12 \
  --video-fps 5 \
  --max-frames 80 \
  --output-dir "video_test"
```

The example processes seconds 5 through 12, samples roughly five frames per second, and refuses to exceed 80 visual frames.

### Several files in one run

```bash
python run_verdant_media.py \
  --input "view_one.png" \
  --input "view_two.png" \
  --input "recording.wav" \
  --output-dir "combined_test"
```

### Entire folder

```bash
python run_verdant_media.py \
  --input "C:/Users/You/VerdantMaterial" \
  --output-dir "folder_test"
```

Folders are expanded recursively in deterministic path order.

### Graphical chooser

Run without `--input`:

```bash
python run_verdant_media.py --output-dir "chosen_files_run"
```

A file-selection window is attempted. On systems without a graphical environment, pass `--input` explicitly.

## Supported decoding

### Images

Common PNG, JPEG, WebP, BMP, and TIFF files are decoded into exact RGB or grayscale native samples.

A still image is one observation. Verdant does not invent prior frames, movement, persistence, disappearance, or reappearance from it.

### Audio

Common WAV, FLAC, MP3, OGG, M4A, AAC, and AIFF files are decoded when the installed audio libraries support the particular encoding.

Control packet duration with:

```bash
--audio-window 0.20
```

### Video

Common MP4, MOV, MKV, WebM, AVI, and M4V files are decoded through the installed video stack.

Useful limits:

```text
--start SECONDS
--end SECONDS
--video-fps FRAMES_PER_SECOND
--max-frames COUNT
--no-video-audio
```

`--no-video-audio` prevents extraction of an audio track from the selected video.

### Other and unknown files

Any regular file within the configured size limit can be preserved. When no active translator supports it, the report records:

```text
translation_status = translation_unavailable
semantic_interpretation_attempted = false
```

The exact source can be reinterpreted later after a legitimate translator is added.

## Archive-only mode

To preserve material without decoding or developmental ingestion:

```bash
python run_verdant_media.py \
  --input "material.dat" \
  --archive-only \
  --output-dir "preserved_material"
```

## Inspect before committing

```bash
python run_verdant_media.py \
  --input "material.mp4" \
  --inspect-only \
  --output-dir "inspection"
```

This reports file classification and size without creating sensory records.

## Continue an existing run

A `.vdk` checkpoint can be continued directly:

```bash
python run_verdant_media.py \
  --checkpoint "current_run.vdk" \
  --input "new_image.png" \
  --output-dir "continued_checkpoint"
```

A portable `.vrun.zip` can be continued with its package metadata and companions:

```bash
python run_verdant_media.py \
  --run-source "current_run.vrun.zip" \
  --run-mode continue \
  --input "new_clip.mp4" \
  --output-dir "continued_package"
```

## Inspect a previous run read-only

```bash
python run_verdant_media.py \
  --run-source "current_run.vrun.zip" \
  --run-mode inspect \
  --output-dir "run_inspection"
```

This writes `run_inspection.json` and does not return a mutable kernel.

## Branch from a previous run

```bash
python run_verdant_media.py \
  --run-source "current_run.vrun.zip" \
  --run-mode branch \
  --branch-label "different-order-test" \
  --input "new_material.wav" \
  --output-dir "branch_test"
```

Branching preserves the historical `kernel_id` so existing signed records remain valid. It adds:

- a new `branch_id`;
- branch label;
- incremented generation;
- parent checkpoint hash;
- ancestor identity record.

The branch is therefore distinguishable without falsifying the identity under which its earlier history occurred.

## Generic ZIPs containing checkpoints

A ZIP containing exactly one `.vdk` can be inspected or continued. When several checkpoints exist, select one with:

```bash
--checkpoint-member "path/inside/archive/run.vdk"
```

ZIP member paths are validated. Traversal paths and unsafe link-style members are rejected.

## Output files

A typical output directory contains:

```text
current_run.vdk
current_run.vrun.zip
media_import_summary.json
media_imports/*.vmi.zip
sensory_archives/*.vsa.zip
```

### `.vmi.zip`

Contains the exact original source bytes plus import identity, MIME/type classification, size, and SHA-256 manifest.

### `.vsa.zip`

Contains decoded native samples and a deterministic sensory manifest. It exists only when decoding succeeds.

### `.vdk`

Contains canonical Verdant state.

### `.vrun.zip`

Contains the checkpoint and supplied companion archives in a portable, verified run package.

## Perceptual processing

Visual imports are processed by default. Disable that layer while still preserving and translating media with:

```bash
--no-perception
```

Perceptual processing performs low-level region proposal and temporal continuity tracking. It does not provide object names or categories.

## Safety limits

The defaults include:

- maximum source size: 512 MB;
- maximum sampled visual frames: 300;
- video sampling rate: 5 FPS;
- audio packet duration: 0.20 seconds.

Override source size deliberately:

```bash
--max-source-mb 100
```

Large files should normally be clipped with `--start`, `--end`, and `--max-frames` before developmental ingestion.

## Recommended first tests

1. Import one still image and confirm no motion or object continuity is claimed.
2. Import two views of the same simple item and compare candidate evidence.
3. Import a short clip with one high-contrast shape moving steadily.
4. Import a clip where the shape disappears briefly and returns.
5. Import a lookalike moving on a conflicting path and check candidate separation.
6. Save the run package, reload it in `inspect`, `continue`, and `branch` modes.

## Honest interpretation

A generated proto-object label such as `proto-object-0d8ab3ac5b93` is an internal identity, not recognition of a human category. It means the candidate earned enough persistence and continuity support under the current experimental policy to be promoted by Council.
