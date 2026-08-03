from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Iterable, Mapping

from verdant_kernel.models import (
    SensoryArchiveRecord,
    canonical_json_bytes,
    stable_id,
)


ARCHIVE_FORMAT = "verdant-native-sensory-archive-1"
MANIFEST_PATH = "manifest.json"
_FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)


class SensoryArchiveIntegrityError(ValueError):
    pass


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=name, date_time=_FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o600 << 16
    return info


def build_archive(
    path: Path,
    *,
    batch_key: str,
    entries: Iterable[Mapping[str, object]],
    payloads: Mapping[str, bytes],
) -> SensoryArchiveRecord:
    """Write a deterministic archive containing the exact native payload bytes.

    Entry dictionaries must contain sample_id, member_path, payload_sha256,
    payload_nbytes, and stable native metadata. The archive manifest deliberately
    excludes derived features so the source record remains native and replayable.
    """

    path = Path(path)
    normalized = sorted((dict(item) for item in entries), key=lambda item: str(item["sample_id"]))
    if not normalized:
        raise ValueError("A sensory archive requires at least one sample.")
    sample_ids = tuple(str(item["sample_id"]) for item in normalized)
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("Sensory archive sample IDs must be unique.")
    member_paths = [str(item["member_path"]) for item in normalized]
    if len(member_paths) != len(set(member_paths)):
        raise ValueError("Sensory archive member paths must be unique.")
    for entry in normalized:
        sample_id = str(entry["sample_id"])
        payload = payloads.get(sample_id)
        if payload is None:
            raise ValueError(f"Missing payload for sample {sample_id!r}.")
        digest = hashlib.sha256(payload).hexdigest()
        if digest != entry["payload_sha256"]:
            raise ValueError("Sensory archive entry payload digest mismatch.")
        if len(payload) != entry["payload_nbytes"]:
            raise ValueError("Sensory archive entry payload length mismatch.")

    body = {
        "format": ARCHIVE_FORMAT,
        "batch_key": batch_key,
        "format_revision": 1,
        "entries": normalized,
    }
    manifest_sha256 = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    archive_id = stable_id(
        "sensory_archive",
        batch_key,
        manifest_sha256,
        sample_ids,
        1,
    )
    manifest = {
        **body,
        "archive_id": archive_id,
        "manifest_sha256": manifest_sha256,
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for entry in normalized:
            archive.writestr(
                _zip_info(str(entry["member_path"])),
                payloads[str(entry["sample_id"])],
            )
        archive.writestr(_zip_info(MANIFEST_PATH), canonical_json_bytes(manifest))
    data = buffer.getvalue()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    archive_sha256 = hashlib.sha256(data).hexdigest()
    return SensoryArchiveRecord(
        archive_id=archive_id,
        batch_key=batch_key,
        archive_sha256=archive_sha256,
        sample_ids=sample_ids,
        manifest_sha256=manifest_sha256,
        format_revision=1,
        created_cycle=0,
        metadata={
            "native_payloads_preserved": True,
            "derived_features_in_manifest": False,
        },
    )


def verify_archive(path: Path) -> SensoryArchiveRecord:
    path = Path(path)
    data = path.read_bytes()
    archive_sha256 = hashlib.sha256(data).hexdigest()
    with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
        try:
            manifest = json.loads(archive.read(MANIFEST_PATH).decode("utf-8"))
        except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SensoryArchiveIntegrityError("Sensory archive manifest is unreadable.") from exc
        body = {
            "format": manifest.get("format"),
            "batch_key": manifest.get("batch_key"),
            "format_revision": manifest.get("format_revision"),
            "entries": manifest.get("entries"),
        }
        if body["format"] != ARCHIVE_FORMAT:
            raise SensoryArchiveIntegrityError("Unsupported sensory archive format.")
        manifest_sha256 = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
        if manifest_sha256 != manifest.get("manifest_sha256"):
            raise SensoryArchiveIntegrityError("Sensory archive manifest checksum mismatch.")
        entries = body["entries"]
        if not isinstance(entries, list) or not entries:
            raise SensoryArchiveIntegrityError("Sensory archive has no sample entries.")
        sample_ids: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise SensoryArchiveIntegrityError("Malformed sensory archive entry.")
            try:
                payload = archive.read(str(entry["member_path"]))
            except KeyError as exc:
                raise SensoryArchiveIntegrityError("Sensory archive payload is missing.") from exc
            if hashlib.sha256(payload).hexdigest() != entry.get("payload_sha256"):
                raise SensoryArchiveIntegrityError("Sensory archive payload checksum mismatch.")
            if len(payload) != entry.get("payload_nbytes"):
                raise SensoryArchiveIntegrityError("Sensory archive payload length mismatch.")
            sample_ids.append(str(entry["sample_id"]))
        sample_tuple = tuple(sorted(sample_ids))
        expected_id = stable_id(
            "sensory_archive",
            str(body["batch_key"]),
            manifest_sha256,
            sample_tuple,
            int(body["format_revision"]),
        )
        if expected_id != manifest.get("archive_id"):
            raise SensoryArchiveIntegrityError("Sensory archive identity checksum mismatch.")
    return SensoryArchiveRecord(
        archive_id=expected_id,
        batch_key=str(body["batch_key"]),
        archive_sha256=archive_sha256,
        sample_ids=sample_tuple,
        manifest_sha256=manifest_sha256,
        format_revision=int(body["format_revision"]),
        created_cycle=0,
        metadata={
            "native_payloads_preserved": True,
            "derived_features_in_manifest": False,
        },
    )
