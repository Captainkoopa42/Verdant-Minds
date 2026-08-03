from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import cv2
import numpy as np
import pytest
import soundfile as sf
from PIL import Image

from verdant_kernel import VerdantKernel, load_checkpoint, save_checkpoint
from verdant_media import (
    ImportOptions,
    MediaArchiveIntegrityError,
    RunImportError,
    VerdantMediaGateway,
    inspect_generic_zip,
    read_media_source,
    verify_media_archive,
    verify_run_package,
)


def write_image(path: Path, *, offset: int = 8, value: int = 220) -> bytes:
    image = np.zeros((48, 64, 3), dtype=np.uint8)
    image[14:32, offset : offset + 18] = value
    Image.fromarray(image).save(path)
    return path.read_bytes()


def write_audio(path: Path, *, duration: float = 0.5, rate: int = 8000) -> bytes:
    time = np.arange(int(duration * rate), dtype=np.float64) / rate
    data = 0.35 * np.sin(2.0 * np.pi * 330.0 * time)
    sf.write(path, data.astype(np.float32), rate, subtype="PCM_16")
    return path.read_bytes()


def write_video(path: Path, *, frames: int = 8, fps: float = 5.0) -> bytes:
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (64, 48)
    )
    assert writer.isOpened()
    for index in range(frames):
        frame = np.zeros((48, 64, 3), dtype=np.uint8)
        x = 4 + index * 5
        frame[14:30, x : x + 14] = 210
        writer.write(frame)
    writer.release()
    return path.read_bytes()


def test_media_gateway_classifies_supported_and_unknown_files(tmp_path: Path) -> None:
    image = tmp_path / "photo.png"
    audio = tmp_path / "sound.wav"
    video = tmp_path / "clip.mp4"
    unknown = tmp_path / "payload.xyz123"
    write_image(image)
    write_audio(audio)
    write_video(video)
    unknown.write_bytes(b"opaque payload")
    gateway = VerdantMediaGateway()
    assert gateway.classify(image)[0] == "image"
    assert gateway.classify(audio)[0] == "audio"
    assert gateway.classify(video)[0] == "video"
    assert gateway.classify(unknown)[0] == "unknown_binary"


def test_user_image_is_preserved_exactly_before_translation(tmp_path: Path) -> None:
    source = tmp_path / "chosen.png"
    original = write_image(source)
    kernel = VerdantKernel(seed=1101, state_dim=64, run_label="user-image")
    result = VerdantMediaGateway().import_path(kernel, source, output_dir=tmp_path / "out")
    verified, recovered = read_media_source(result.media_archive.archive_path)
    assert recovered == original
    assert verified.source_sha256 == hashlib.sha256(original).hexdigest()
    assert result.translated is True
    assert len(result.sensory_result.samples) == 1
    assert len(result.temporal_event_ids) == 1
    assert kernel.state.concepts == {}
    assert kernel.state.relations == {}
    assert kernel.state.claims == {}


def test_user_audio_clip_can_be_bounded_and_chunked(tmp_path: Path) -> None:
    source = tmp_path / "chosen.wav"
    write_audio(source, duration=1.0)
    kernel = VerdantKernel(seed=1102, state_dim=64, run_label="user-audio")
    result = VerdantMediaGateway().import_path(
        kernel,
        source,
        output_dir=tmp_path / "out",
        options=ImportOptions(start_seconds=0.20, end_seconds=0.70, audio_window_seconds=0.10),
    )
    assert result.translated is True
    assert 4 <= len(result.sensory_result.samples) <= 6
    assert all(item.modality.value == "audio" for item in result.sensory_result.samples)
    assert min(item.timestamp_ns for item in result.sensory_result.samples) >= 200_000_000
    assert max(item.timestamp_ns for item in result.sensory_result.samples) < 700_000_000


def test_user_video_decodes_to_bounded_visual_samples(tmp_path: Path) -> None:
    source = tmp_path / "chosen.mp4"
    original = write_video(source, frames=10, fps=5.0)
    kernel = VerdantKernel(seed=1103, state_dim=64, run_label="user-video")
    kernel.update_sensory_policy(
        feature_change_threshold=1.0,
        maximum_event_gap_ns=300_000_000,
        minimum_modalities_per_group=1,
    )
    result = VerdantMediaGateway().import_path(
        kernel,
        source,
        output_dir=tmp_path / "out",
        options=ImportOptions(video_fps=5.0, maximum_frames=4, include_video_audio=False),
    )
    assert result.translated is True
    assert len(result.sensory_result.samples) == 4
    assert all(item.modality.value == "vision" for item in result.sensory_result.samples)
    assert result.media_archive.source_sha256 == hashlib.sha256(original).hexdigest()


def test_unknown_file_is_archived_without_invented_translation(tmp_path: Path) -> None:
    source = tmp_path / "unknown.bin"
    source.write_bytes(b"\x00\x01not a known media codec\xff")
    kernel = VerdantKernel(seed=1104, state_dim=64, run_label="unknown-file")
    before = kernel.snapshot()
    result = VerdantMediaGateway().import_path(kernel, source, output_dir=tmp_path / "out")
    assert result.translated is False
    assert result.translation_status == "translation_unavailable"
    assert kernel.snapshot() == before
    _, recovered = read_media_source(result.media_archive.archive_path)
    assert recovered == source.read_bytes()


def test_media_archive_tampering_is_detected(tmp_path: Path) -> None:
    source = tmp_path / "chosen.png"
    write_image(source)
    kernel = VerdantKernel(seed=1105, state_dim=64, run_label="tamper-media")
    result = VerdantMediaGateway().import_path(
        kernel,
        source,
        output_dir=tmp_path / "out",
        options=ImportOptions(archive_only=True),
    )
    damaged = tmp_path / "damaged.vmi.zip"
    with zipfile.ZipFile(result.media_archive.archive_path, "r") as source_zip:
        members = {name: source_zip.read(name) for name in source_zip.namelist()}
    payload_name = next(name for name in members if name.startswith("source/"))
    payload = bytearray(members[payload_name])
    payload[0] ^= 0x01
    members[payload_name] = bytes(payload)
    with zipfile.ZipFile(damaged, "w", compression=zipfile.ZIP_STORED) as target:
        for name, data in members.items():
            target.writestr(name, data)
    with pytest.raises(MediaArchiveIntegrityError):
        verify_media_archive(damaged)


def test_run_package_roundtrip_supports_inspect_and_continue(tmp_path: Path) -> None:
    kernel = VerdantKernel(seed=1106, state_dim=64, run_label="run-package")
    checkpoint = tmp_path / "source.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    package = tmp_path / "source.vrun.zip"
    gateway = VerdantMediaGateway()
    record = gateway.write_run_package(kernel, package)
    assert verify_run_package(package).package_id == record.package_id
    inspected = gateway.load_run(package, mode="inspect")
    assert inspected.kernel is None
    assert inspected.inspection.state == kernel.snapshot()
    continued = gateway.load_run(package, mode="continue")
    assert continued.kernel.snapshot() == kernel.snapshot()


def test_run_branch_has_explicit_lineage_without_rewriting_historical_identity(tmp_path: Path) -> None:
    kernel = VerdantKernel(seed=1107, state_dim=64, run_label="parent")
    checkpoint = tmp_path / "parent.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    result = VerdantMediaGateway().load_run(
        checkpoint,
        mode="branch",
        branch_label="child-branch",
    )
    assert result.kernel is not None
    child = result.kernel
    assert child.state.identity.kernel_id == kernel.state.identity.kernel_id
    assert child.state.identity.run_label == "child-branch"
    assert child.state.lineage.generation == 1
    assert child.state.lineage.branch_id is not None
    assert child.state.lineage.branch_label == "child-branch"
    assert kernel.state.identity.kernel_id in child.state.lineage.ancestor_kernel_ids
    assert result.inspection.checkpoint_sha256 in child.state.lineage.parent_checkpoint_hashes


def test_generic_zip_with_one_checkpoint_can_be_loaded(tmp_path: Path) -> None:
    kernel = VerdantKernel(seed=1108, state_dim=64, run_label="generic-zip")
    checkpoint = tmp_path / "inside.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    bundle = tmp_path / "legacy_bundle.zip"
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("run/inside.vdk", checkpoint.read_bytes())
        archive.writestr("run/notes.json", json.dumps({"legacy": True}))
    loaded = VerdantMediaGateway().load_run(bundle, mode="continue")
    assert loaded.kernel.snapshot() == kernel.snapshot()
    assert loaded.inspection.member_name == "run/inside.vdk"


def test_zip_path_traversal_is_rejected_without_extraction(tmp_path: Path) -> None:
    malicious = tmp_path / "malicious.zip"
    with zipfile.ZipFile(malicious, "w") as archive:
        archive.writestr("../outside.txt", b"bad")
    with pytest.raises(MediaArchiveIntegrityError):
        inspect_generic_zip(malicious)
    assert not (tmp_path.parent / "outside.txt").exists()
