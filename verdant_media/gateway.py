from __future__ import annotations

import hashlib
import io
import json
import math
import mimetypes
import os
import shutil
import subprocess
import tempfile
import wave
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal, Sequence

import cv2
import numpy as np
import soundfile as sf
from PIL import Image, ImageOps

from verdant_kernel import KernelState, VerdantKernel, load_checkpoint, save_checkpoint
from verdant_kernel.models import KernelIdentity, NativeModality, stable_id
from verdant_sensory import NativeSamplePacket, SensoryBatchResult, VerdantSensoryPipeline

from .archive import (
    MediaArchiveIntegrityError,
    MediaArchiveRecord,
    RunPackageIntegrityError,
    RunPackageRecord,
    build_media_archive,
    build_run_package,
    extract_checkpoint_bytes_from_run_package,
    inspect_generic_zip,
    safe_member_name,
    verify_media_archive,
    verify_run_package,
)


_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
_AUDIO_EXTENSIONS = {".wav", ".flac", ".mp3", ".ogg", ".oga", ".m4a", ".aac", ".aiff", ".aif"}
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
_TEXT_EXTENSIONS = {".txt", ".md", ".json", ".jsonl", ".csv", ".tsv", ".yaml", ".yml", ".xml"}
_RUN_EXTENSIONS = {".vdk", ".vrun", ".zip"}


class MediaImportError(ValueError):
    pass


class UnsupportedTranslationError(MediaImportError):
    pass


class RunImportError(MediaImportError):
    pass


@dataclass(frozen=True)
class ImportOptions:
    start_seconds: float = 0.0
    end_seconds: float | None = None
    video_fps: float = 5.0
    audio_window_seconds: float = 0.20
    maximum_frames: int = 300
    maximum_source_bytes: int = 512 * 1024 * 1024
    include_video_audio: bool = True
    archive_only: bool = False

    def __post_init__(self) -> None:
        if self.start_seconds < 0:
            raise ValueError("start_seconds cannot be negative.")
        if self.end_seconds is not None and self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be later than start_seconds.")
        if self.video_fps <= 0 or self.audio_window_seconds <= 0:
            raise ValueError("Sampling rates must be positive.")
        if self.maximum_frames < 1 or self.maximum_source_bytes < 1:
            raise ValueError("Import limits must be positive.")


@dataclass(frozen=True)
class MediaImportResult:
    source_path: Path
    media_kind: str
    mime_type: str
    media_archive: MediaArchiveRecord
    translated: bool
    translation_status: str
    sensory_result: SensoryBatchResult | None = None
    notes: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def temporal_event_ids(self) -> tuple[str, ...]:
        if self.sensory_result is None:
            return ()
        return self.sensory_result.assembly_event.committed_event_ids

    @property
    def sensory_archive_path(self) -> Path | None:
        return None if self.sensory_result is None else self.sensory_result.archive_path


@dataclass(frozen=True)
class RunInspection:
    source_path: Path
    package_kind: str
    checkpoint_sha256: str
    state: KernelState
    metrics: dict[str, float | int]
    member_name: str | None = None
    package_record: RunPackageRecord | None = None
    generic_zip_inventory: dict[str, Any] | None = None


@dataclass(frozen=True)
class RunLoadResult:
    mode: Literal["inspect", "continue", "branch"]
    inspection: RunInspection
    kernel: VerdantKernel | None


class VerdantMediaGateway:
    """User-controlled media and run import boundary.

    The exact user file is preserved first. Decoding is a separate, explicit step.
    Unsupported files remain archived rather than being assigned fabricated meaning.
    """

    def __init__(self, sensory: VerdantSensoryPipeline | None = None) -> None:
        self.sensory = sensory or VerdantSensoryPipeline()

    @staticmethod
    def classify(path: Path) -> tuple[str, str]:
        path = Path(path)
        suffix = path.suffix.lower()
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if suffix in _IMAGE_EXTENSIONS:
            return "image", mime
        if suffix in _AUDIO_EXTENSIONS:
            return "audio", mime
        if suffix in _VIDEO_EXTENSIONS:
            return "video", mime
        if suffix == ".vdk":
            return "verdant_checkpoint", "application/vnd.verdant.checkpoint"
        if suffix in {".vrun"} or path.name.lower().endswith(".vrun.zip"):
            return "verdant_run_package", "application/vnd.verdant.run-package"
        if suffix == ".zip":
            try:
                inventory = inspect_generic_zip(path)
            except MediaArchiveIntegrityError:
                return "zip_archive", "application/zip"
            if inventory["contains_run_manifest"]:
                return "verdant_run_package", "application/vnd.verdant.run-package"
            if inventory["contains_vdk"]:
                return "zip_with_checkpoint", "application/zip"
            return "zip_archive", "application/zip"
        if suffix in _TEXT_EXTENSIONS:
            return "text_or_structured", mime
        return "unknown_binary", mime

    @staticmethod
    def _check_source(path: Path, maximum_source_bytes: int) -> None:
        if not path.is_file():
            raise MediaImportError(f"Input is not a regular file: {path}")
        size = path.stat().st_size
        if size <= 0:
            raise MediaImportError("Empty input files are not accepted.")
        if size > maximum_source_bytes:
            raise MediaImportError(
                f"Input file exceeds configured limit ({size} > {maximum_source_bytes} bytes)."
            )

    def import_path(
        self,
        kernel: VerdantKernel,
        source_path: Path,
        *,
        output_dir: Path,
        options: ImportOptions | None = None,
    ) -> MediaImportResult:
        options = options or ImportOptions()
        source_path = Path(source_path)
        output_dir = Path(output_dir)
        self._check_source(source_path, options.maximum_source_bytes)
        media_kind, mime = self.classify(source_path)
        if media_kind in {"verdant_checkpoint", "verdant_run_package", "zip_with_checkpoint"}:
            raise RunImportError(
                "This input is a run/checkpoint source. Use inspect_run or load_run instead of media ingestion."
            )
        stem = safe_member_name(source_path.stem)
        archive_path = output_dir / "media_imports" / f"{stem}_{hashlib.sha256(source_path.read_bytes()).hexdigest()[:12]}.vmi.zip"
        media_archive = build_media_archive(
            source_path,
            archive_path,
            media_kind=media_kind,
            mime_type=mime,
            metadata={
                "absolute_source_path_stored": False,
                "user_selected": True,
                "translation_requested": not options.archive_only,
            },
        )
        verified = verify_media_archive(archive_path)
        if verified != media_archive:
            raise MediaImportError("The exact-source media archive failed deterministic verification.")
        if options.archive_only:
            return MediaImportResult(
                source_path=source_path,
                media_kind=media_kind,
                mime_type=mime,
                media_archive=media_archive,
                translated=False,
                translation_status="archive_only",
                notes=("Exact source bytes preserved; no decoder was invoked.",),
            )

        if media_kind == "image":
            packets, metadata = self._decode_image(source_path, media_archive)
        elif media_kind == "audio":
            packets, metadata = self._decode_audio(source_path, media_archive, options)
        elif media_kind == "video":
            packets, metadata = self._decode_video(source_path, media_archive, options)
        else:
            return MediaImportResult(
                source_path=source_path,
                media_kind=media_kind,
                mime_type=mime,
                media_archive=media_archive,
                translated=False,
                translation_status="translation_unavailable",
                notes=(
                    "Exact source bytes preserved. No active translator supports this file type yet.",
                ),
                metadata={"semantic_interpretation_attempted": False},
            )

        if not packets:
            return MediaImportResult(
                source_path=source_path,
                media_kind=media_kind,
                mime_type=mime,
                media_archive=media_archive,
                translated=False,
                translation_status="decoded_no_samples",
                notes=("Decoder produced no bounded samples for the selected interval.",),
                metadata=metadata,
            )
        sensory_path = output_dir / "sensory_archives" / f"{media_archive.import_id}.vsa.zip"
        sensory_result = self.sensory.ingest_batch(
            kernel,
            packets,
            batch_key=f"user-media:{media_archive.import_id}",
            archive_path=sensory_path,
        )
        return MediaImportResult(
            source_path=source_path,
            media_kind=media_kind,
            mime_type=mime,
            media_archive=media_archive,
            translated=True,
            translation_status="ingested",
            sensory_result=sensory_result,
            notes=(
                "Original file preserved in .vmi.zip.",
                "Decoded samples preserved separately in .vsa.zip.",
                "No semantic categories were supplied by the importer.",
            ),
            metadata=metadata,
        )

    def import_many(
        self,
        kernel: VerdantKernel,
        inputs: Sequence[Path],
        *,
        output_dir: Path,
        options: ImportOptions | None = None,
    ) -> tuple[MediaImportResult, ...]:
        expanded: list[Path] = []
        for item in inputs:
            path = Path(item)
            if path.is_dir():
                expanded.extend(sorted(p for p in path.rglob("*") if p.is_file()))
            else:
                expanded.append(path)
        return tuple(
            self.import_path(kernel, item, output_dir=output_dir, options=options)
            for item in expanded
        )

    @staticmethod
    def _base_metadata(record: MediaArchiveRecord) -> dict[str, Any]:
        return {
            "media_import_id": record.import_id,
            "original_source_name": record.source_name,
            "original_source_sha256": record.source_sha256,
            "original_media_archive_sha256": record.archive_sha256,
            "original_media_archive_format": "verdant-media-import-1",
            "semantic_categories_supplied": False,
        }

    def _decode_image(
        self,
        path: Path,
        record: MediaArchiveRecord,
    ) -> tuple[tuple[NativeSamplePacket, ...], dict[str, Any]]:
        try:
            with Image.open(path) as image:
                image = ImageOps.exif_transpose(image).convert("RGB")
                array = np.asarray(image, dtype=np.uint8)
        except Exception as exc:  # Pillow has many codec-specific exceptions.
            raise MediaImportError(f"Image decoding failed: {exc}") from exc
        stream_id = stable_id("user_image_stream", record.import_id)
        packet = NativeSamplePacket(
            stream_id=stream_id,
            sequence_number=0,
            timestamp_ns=0,
            modality=NativeModality.VISION,
            media_type="application/x-raw-rgb8",
            payload=array.tobytes(order="C"),
            shape=tuple(int(item) for item in array.shape),
            metadata={
                **self._base_metadata(record),
                "decode_kind": "pillow_rgb8",
                "still_image": True,
                "invented_motion": False,
                "original_dimensions": [int(array.shape[1]), int(array.shape[0])],
            },
        )
        return (packet,), {
            "decoded_width": int(array.shape[1]),
            "decoded_height": int(array.shape[0]),
            "decoded_channels": int(array.shape[2]),
            "still_image": True,
        }

    @staticmethod
    def _read_audio(path: Path) -> tuple[np.ndarray, int]:
        try:
            data, rate = sf.read(path, dtype="float32", always_2d=True)
            return np.asarray(data, dtype=np.float32), int(rate)
        except Exception as first_exc:
            # Fallback through ffmpeg for codecs unsupported by libsndfile.
            with tempfile.TemporaryDirectory(prefix="verdant-audio-") as temp_dir:
                wav_path = Path(temp_dir) / "decoded.wav"
                command = [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    str(path),
                    "-acodec",
                    "pcm_s16le",
                    str(wav_path),
                ]
                try:
                    subprocess.run(command, check=True, capture_output=True)
                    data, rate = sf.read(wav_path, dtype="float32", always_2d=True)
                    return np.asarray(data, dtype=np.float32), int(rate)
                except Exception as second_exc:
                    raise MediaImportError(
                        f"Audio decoding failed with libsndfile and ffmpeg: {first_exc}; {second_exc}"
                    ) from second_exc

    def _audio_packets_from_array(
        self,
        data: np.ndarray,
        rate: int,
        *,
        record: MediaArchiveRecord,
        options: ImportOptions,
        stream_id: str,
        source_offset_seconds: float = 0.0,
        window_seconds: float | None = None,
    ) -> tuple[NativeSamplePacket, ...]:
        if data.ndim != 2 or not data.size:
            return ()
        mono = np.mean(data, axis=1)
        start_index = min(len(mono), max(0, int(round(options.start_seconds * rate))))
        end_index = len(mono)
        if options.end_seconds is not None:
            end_index = min(end_index, int(round(options.end_seconds * rate)))
        mono = mono[start_index:end_index]
        window = max(1, int(round((window_seconds or options.audio_window_seconds) * rate)))
        packets: list[NativeSamplePacket] = []
        for sequence, left in enumerate(range(0, len(mono), window)):
            segment = mono[left : left + window]
            if not segment.size:
                continue
            pcm = np.asarray(np.clip(segment, -1.0, 1.0) * 32767.0, dtype="<i2")
            timestamp_seconds = source_offset_seconds + options.start_seconds + left / rate
            packets.append(
                NativeSamplePacket(
                    stream_id=stream_id,
                    sequence_number=sequence,
                    timestamp_ns=int(round(timestamp_seconds * 1_000_000_000)),
                    modality=NativeModality.AUDIO,
                    media_type="audio/L16",
                    payload=pcm.tobytes(order="C"),
                    sample_rate_hz=rate,
                    channel_names=("mono",),
                    metadata={
                        **self._base_metadata(record),
                        "decode_kind": "pcm16_mono_window",
                        "source_channel_count": int(data.shape[1]),
                        "window_samples": int(segment.size),
                        "window_seconds": float(segment.size / rate),
                    },
                )
            )
        return tuple(packets)

    def _decode_audio(
        self,
        path: Path,
        record: MediaArchiveRecord,
        options: ImportOptions,
    ) -> tuple[tuple[NativeSamplePacket, ...], dict[str, Any]]:
        data, rate = self._read_audio(path)
        stream_id = stable_id("user_audio_stream", record.import_id)
        packets = self._audio_packets_from_array(
            data,
            rate,
            record=record,
            options=options,
            stream_id=stream_id,
        )
        return packets, {
            "sample_rate_hz": rate,
            "source_channels": int(data.shape[1]),
            "source_frames": int(data.shape[0]),
            "window_seconds": options.audio_window_seconds,
        }

    def _decode_video(
        self,
        path: Path,
        record: MediaArchiveRecord,
        options: ImportOptions,
    ) -> tuple[tuple[NativeSamplePacket, ...], dict[str, Any]]:
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            raise MediaImportError("Video decoding failed: OpenCV could not open the file.")
        source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if source_fps <= 0:
            source_fps = options.video_fps
        start_frame = max(0, int(math.floor(options.start_seconds * source_fps)))
        end_frame = frame_count if frame_count > 0 else math.inf
        if options.end_seconds is not None:
            end_frame = min(end_frame, int(math.ceil(options.end_seconds * source_fps)))
        stride = max(1, int(round(source_fps / options.video_fps)))
        capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        packets: list[NativeSamplePacket] = []
        sequence = 0
        frame_index = start_frame
        stream_id = stable_id("user_video_stream", record.import_id)
        while frame_index < end_frame and sequence < options.maximum_frames:
            ok, frame = capture.read()
            if not ok:
                break
            if (frame_index - start_frame) % stride == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                relative_seconds = frame_index / source_fps
                packets.append(
                    NativeSamplePacket(
                        stream_id=stream_id,
                        sequence_number=sequence,
                        timestamp_ns=int(round(relative_seconds * 1_000_000_000)),
                        modality=NativeModality.VISION,
                        media_type="application/x-raw-rgb8",
                        payload=np.ascontiguousarray(rgb, dtype=np.uint8).tobytes(order="C"),
                        shape=tuple(int(item) for item in rgb.shape),
                        metadata={
                            **self._base_metadata(record),
                            "decode_kind": "opencv_rgb8_frame",
                            "source_frame_index": frame_index,
                            "source_time_seconds": relative_seconds,
                            "source_fps": source_fps,
                            "sampled_fps": source_fps / stride,
                        },
                    )
                )
                sequence += 1
            frame_index += 1
        capture.release()
        notes: list[str] = []
        audio_packet_count = 0
        if options.include_video_audio:
            try:
                with tempfile.TemporaryDirectory(prefix="verdant-video-audio-") as temp_dir:
                    wav_path = Path(temp_dir) / "track.wav"
                    command = ["ffmpeg", "-v", "error", "-y"]
                    if options.start_seconds:
                        command += ["-ss", f"{options.start_seconds:.9f}"]
                    command += ["-i", str(path)]
                    if options.end_seconds is not None:
                        command += ["-t", f"{options.end_seconds - options.start_seconds:.9f}"]
                    command += ["-vn", "-ac", "1", "-acodec", "pcm_s16le", str(wav_path)]
                    subprocess.run(command, check=True, capture_output=True)
                    if wav_path.exists() and wav_path.stat().st_size > 44:
                        data, rate = sf.read(wav_path, dtype="float32", always_2d=True)
                        audio_options = ImportOptions(
                            start_seconds=0.0,
                            end_seconds=None,
                            video_fps=options.video_fps,
                            audio_window_seconds=max(0.04, 1.0 / max(1e-6, options.video_fps)),
                            maximum_frames=options.maximum_frames,
                            maximum_source_bytes=options.maximum_source_bytes,
                            include_video_audio=options.include_video_audio,
                            archive_only=False,
                        )
                        audio_packets = self._audio_packets_from_array(
                            np.asarray(data, dtype=np.float32),
                            int(rate),
                            record=record,
                            options=audio_options,
                            stream_id=stable_id("user_video_audio_stream", record.import_id),
                            source_offset_seconds=options.start_seconds,
                            window_seconds=audio_options.audio_window_seconds,
                        )
                        packets.extend(audio_packets)
                        audio_packet_count = len(audio_packets)
                    else:
                        notes.append("No decodable audio track was present.")
            except Exception as exc:
                notes.append(f"Video audio track was not imported: {type(exc).__name__}: {exc}")
        packets.sort(
            key=lambda item: (
                item.timestamp_ns,
                0 if item.modality == NativeModality.VISION else 1,
                item.stream_id,
                item.sequence_number,
            )
        )
        return tuple(packets), {
            "source_fps": source_fps,
            "source_frame_count": frame_count,
            "source_width": width,
            "source_height": height,
            "sampled_visual_frames": sequence,
            "sampled_audio_packets": audio_packet_count,
            "selected_start_seconds": options.start_seconds,
            "selected_end_seconds": options.end_seconds,
            "notes": notes,
        }

    def inspect_run(
        self,
        path: Path,
        *,
        checkpoint_member: str | None = None,
    ) -> RunInspection:
        path = Path(path)
        kind, _ = self.classify(path)
        if kind == "verdant_checkpoint":
            state = load_checkpoint(path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            kernel = VerdantKernel.from_state(state)
            return RunInspection(
                source_path=path,
                package_kind="checkpoint",
                checkpoint_sha256=digest,
                state=state,
                metrics=kernel.metrics(),
            )
        if kind == "verdant_run_package":
            record, checkpoint_bytes = extract_checkpoint_bytes_from_run_package(path)
            with tempfile.NamedTemporaryFile(suffix=".vdk", delete=False) as handle:
                temp_path = Path(handle.name)
                handle.write(checkpoint_bytes)
            try:
                state = load_checkpoint(temp_path)
            finally:
                temp_path.unlink(missing_ok=True)
            return RunInspection(
                source_path=path,
                package_kind="verdant_run_package",
                checkpoint_sha256=record.checkpoint_sha256,
                state=state,
                metrics=VerdantKernel.from_state(state).metrics(),
                member_name=record.checkpoint_member,
                package_record=record,
            )
        if kind in {"zip_with_checkpoint", "zip_archive"}:
            inventory = inspect_generic_zip(path)
            vdk_members = [
                item["name"] for item in inventory["members"] if item["name"].lower().endswith(".vdk")
            ]
            if not vdk_members:
                raise RunImportError(
                    "ZIP is preserved and inspectable, but it contains no current Verdant .vdk checkpoint. "
                    "A legacy adapter is required before it can continue a run."
                )
            if checkpoint_member is None:
                if len(vdk_members) != 1:
                    raise RunImportError(
                        "ZIP contains multiple checkpoints; provide checkpoint_member. Candidates: "
                        + ", ".join(vdk_members)
                    )
                checkpoint_member = vdk_members[0]
            if checkpoint_member not in vdk_members:
                raise RunImportError("Requested checkpoint member is not present in the ZIP.")
            with zipfile.ZipFile(path, "r") as archive:
                checkpoint_bytes = archive.read(checkpoint_member)
            digest = hashlib.sha256(checkpoint_bytes).hexdigest()
            with tempfile.NamedTemporaryFile(suffix=".vdk", delete=False) as handle:
                temp_path = Path(handle.name)
                handle.write(checkpoint_bytes)
            try:
                state = load_checkpoint(temp_path)
            finally:
                temp_path.unlink(missing_ok=True)
            return RunInspection(
                source_path=path,
                package_kind="zip_with_checkpoint",
                checkpoint_sha256=digest,
                state=state,
                metrics=VerdantKernel.from_state(state).metrics(),
                member_name=checkpoint_member,
                generic_zip_inventory=inventory,
            )
        raise RunImportError("Input is not a supported Verdant run source.")

    def load_run(
        self,
        path: Path,
        *,
        mode: Literal["inspect", "continue", "branch"] = "inspect",
        branch_label: str | None = None,
        checkpoint_member: str | None = None,
    ) -> RunLoadResult:
        inspection = self.inspect_run(path, checkpoint_member=checkpoint_member)
        if mode == "inspect":
            return RunLoadResult(mode=mode, inspection=inspection, kernel=None)
        if mode == "continue":
            return RunLoadResult(
                mode=mode,
                inspection=inspection,
                kernel=VerdantKernel.from_state(inspection.state),
            )
        if mode != "branch":
            raise RunImportError(f"Unknown run load mode: {mode!r}")
        label = (branch_label or f"branch-from-{inspection.state.identity.run_label}").strip()
        if not label:
            raise RunImportError("Branch label cannot be empty.")
        parent_state = inspection.state.model_copy(deep=True)
        parent_kernel_id = parent_state.identity.kernel_id
        branch_id = stable_id(
            "lineage_branch",
            parent_kernel_id,
            inspection.checkpoint_sha256,
            label,
            parent_state.lineage.generation + 1,
        )
        # A branch is a new lineage path, not a rewritten historical identity.
        # Historical Council, workspace, sensory, and perceptual records are signed
        # against the continuing kernel_id, so changing it would invalidate the
        # very history the branch is supposed to preserve.
        parent_state.identity = KernelIdentity(
            kernel_id=parent_kernel_id,
            schema_version=parent_state.identity.schema_version,
            run_label=label,
        )
        parent_state.lineage.generation += 1
        parent_state.lineage.branch_id = branch_id
        parent_state.lineage.branch_label = label
        parent_state.lineage.parent_checkpoint_hashes.append(inspection.checkpoint_sha256)
        parent_state.lineage.parent_checkpoint_hashes = sorted(
            set(parent_state.lineage.parent_checkpoint_hashes)
        )
        parent_state.lineage.ancestor_kernel_ids.append(parent_kernel_id)
        parent_state.lineage.ancestor_kernel_ids = sorted(
            set(parent_state.lineage.ancestor_kernel_ids)
        )
        return RunLoadResult(
            mode=mode,
            inspection=inspection,
            kernel=VerdantKernel.from_state(parent_state),
        )

    @staticmethod
    def write_run_package(
        kernel: VerdantKernel,
        output_path: Path,
        *,
        companion_paths: Iterable[Path] = (),
        metadata: dict[str, Any] | None = None,
    ) -> RunPackageRecord:
        output_path = Path(output_path)
        with tempfile.NamedTemporaryFile(suffix=".vdk", delete=False) as handle:
            checkpoint_path = Path(handle.name)
        try:
            checkpoint_hash = save_checkpoint(checkpoint_path, kernel.state)
            record = build_run_package(
                output_path,
                checkpoint_path=checkpoint_path,
                companion_paths=tuple(Path(item) for item in companion_paths),
                metadata={
                    "kernel_id": kernel.state.identity.kernel_id,
                    "run_label": kernel.state.identity.run_label,
                    "generation": kernel.state.lineage.generation,
                    "checkpoint_file_sha256": checkpoint_hash,
                    **(metadata or {}),
                },
            )
            verify_run_package(output_path)
            return record
        finally:
            checkpoint_path.unlink(missing_ok=True)
