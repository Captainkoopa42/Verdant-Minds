from __future__ import annotations

import hashlib
import io
import json
import mimetypes
import os
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from verdant_kernel.models import canonical_json_bytes, stable_id

MEDIA_IMPORT_FORMAT = "verdant-media-import-1"
RUN_PACKAGE_FORMAT = "verdant-run-package-1"
MEDIA_MANIFEST = "media_manifest.json"
RUN_MANIFEST = "run_manifest.json"
_FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


class MediaArchiveIntegrityError(ValueError):
    pass


class RunPackageIntegrityError(ValueError):
    pass


@dataclass(frozen=True)
class MediaArchiveRecord:
    import_id: str
    source_name: str
    source_sha256: str
    source_nbytes: int
    media_kind: str
    mime_type: str
    archive_sha256: str
    manifest_sha256: str
    member_path: str
    archive_path: Path


@dataclass(frozen=True)
class RunPackageRecord:
    package_id: str
    checkpoint_member: str
    checkpoint_sha256: str
    package_sha256: str
    manifest_sha256: str
    companion_members: tuple[str, ...]
    package_path: Path


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=name, date_time=_FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o600 << 16
    return info


def safe_member_name(name: str) -> str:
    base = Path(name).name
    cleaned = _SAFE.sub("_", base).strip("._")
    return cleaned or "source.bin"


def _validate_zip_member(name: str) -> None:
    path = Path(name)
    if path.is_absolute() or ".." in path.parts:
        raise MediaArchiveIntegrityError(f"Unsafe ZIP member path: {name!r}")
    # Backslashes are path separators on Windows and may be used for traversal.
    if "\\" in name:
        raise MediaArchiveIntegrityError(f"Unsafe ZIP member path: {name!r}")


def build_media_archive(
    source_path: Path,
    output_path: Path,
    *,
    media_kind: str,
    mime_type: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> MediaArchiveRecord:
    source_path = Path(source_path)
    output_path = Path(output_path)
    data = source_path.read_bytes()
    source_sha256 = hashlib.sha256(data).hexdigest()
    mime = mime_type or mimetypes.guess_type(source_path.name)[0] or "application/octet-stream"
    member_path = f"source/{safe_member_name(source_path.name)}"
    body = {
        "format": MEDIA_IMPORT_FORMAT,
        "format_revision": 1,
        "source_name": source_path.name,
        "source_sha256": source_sha256,
        "source_nbytes": len(data),
        "media_kind": media_kind,
        "mime_type": mime,
        "member_path": member_path,
        "metadata": metadata or {},
    }
    manifest_sha256 = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    import_id = stable_id(
        "media_import",
        source_path.name,
        source_sha256,
        len(data),
        media_kind,
        mime,
        manifest_sha256,
    )
    manifest = {**body, "import_id": import_id, "manifest_sha256": manifest_sha256}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(_zip_info(member_path), data)
        archive.writestr(_zip_info(MEDIA_MANIFEST), canonical_json_bytes(manifest))
    archive_bytes = buffer.getvalue()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(archive_bytes)
    return MediaArchiveRecord(
        import_id=import_id,
        source_name=source_path.name,
        source_sha256=source_sha256,
        source_nbytes=len(data),
        media_kind=media_kind,
        mime_type=mime,
        archive_sha256=hashlib.sha256(archive_bytes).hexdigest(),
        manifest_sha256=manifest_sha256,
        member_path=member_path,
        archive_path=output_path,
    )


def verify_media_archive(path: Path) -> MediaArchiveRecord:
    path = Path(path)
    archive_bytes = path.read_bytes()
    archive_sha256 = hashlib.sha256(archive_bytes).hexdigest()
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as archive:
            names = archive.namelist()
            for name in names:
                _validate_zip_member(name)
            manifest = json.loads(archive.read(MEDIA_MANIFEST).decode("utf-8"))
            body = {
                key: manifest.get(key)
                for key in (
                    "format",
                    "format_revision",
                    "source_name",
                    "source_sha256",
                    "source_nbytes",
                    "media_kind",
                    "mime_type",
                    "member_path",
                    "metadata",
                )
            }
            if body["format"] != MEDIA_IMPORT_FORMAT or body["format_revision"] != 1:
                raise MediaArchiveIntegrityError("Unsupported media import archive format.")
            manifest_sha256 = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
            if manifest_sha256 != manifest.get("manifest_sha256"):
                raise MediaArchiveIntegrityError("Media import manifest checksum mismatch.")
            member_path = str(body["member_path"])
            _validate_zip_member(member_path)
            payload = archive.read(member_path)
            if len(payload) != body["source_nbytes"]:
                raise MediaArchiveIntegrityError("Media source length mismatch.")
            source_sha256 = hashlib.sha256(payload).hexdigest()
            if source_sha256 != body["source_sha256"]:
                raise MediaArchiveIntegrityError("Media source checksum mismatch.")
            expected_id = stable_id(
                "media_import",
                body["source_name"],
                source_sha256,
                len(payload),
                body["media_kind"],
                body["mime_type"],
                manifest_sha256,
            )
            if expected_id != manifest.get("import_id"):
                raise MediaArchiveIntegrityError("Media import identity mismatch.")
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        raise MediaArchiveIntegrityError("Media import archive is unreadable.") from exc
    return MediaArchiveRecord(
        import_id=expected_id,
        source_name=str(body["source_name"]),
        source_sha256=source_sha256,
        source_nbytes=len(payload),
        media_kind=str(body["media_kind"]),
        mime_type=str(body["mime_type"]),
        archive_sha256=archive_sha256,
        manifest_sha256=manifest_sha256,
        member_path=member_path,
        archive_path=path,
    )


def read_media_source(path: Path) -> tuple[MediaArchiveRecord, bytes]:
    record = verify_media_archive(path)
    with zipfile.ZipFile(path, "r") as archive:
        return record, archive.read(record.member_path)


def build_run_package(
    output_path: Path,
    *,
    checkpoint_path: Path,
    companion_paths: tuple[Path, ...] = (),
    metadata: dict[str, Any] | None = None,
) -> RunPackageRecord:
    output_path = Path(output_path)
    checkpoint_path = Path(checkpoint_path)
    checkpoint_bytes = checkpoint_path.read_bytes()
    checkpoint_sha256 = hashlib.sha256(checkpoint_bytes).hexdigest()
    checkpoint_member = f"checkpoint/{safe_member_name(checkpoint_path.name)}"
    companions: list[dict[str, Any]] = []
    companion_payloads: list[tuple[str, bytes]] = []
    for index, companion in enumerate(sorted(map(Path, companion_paths), key=lambda p: p.name)):
        data = companion.read_bytes()
        member = f"companions/{index:03d}_{safe_member_name(companion.name)}"
        companions.append(
            {
                "member_path": member,
                "source_name": companion.name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "nbytes": len(data),
            }
        )
        companion_payloads.append((member, data))
    body = {
        "format": RUN_PACKAGE_FORMAT,
        "format_revision": 1,
        "checkpoint_member": checkpoint_member,
        "checkpoint_sha256": checkpoint_sha256,
        "checkpoint_nbytes": len(checkpoint_bytes),
        "companions": companions,
        "metadata": metadata or {},
    }
    manifest_sha256 = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    package_id = stable_id(
        "run_package",
        checkpoint_sha256,
        tuple((item["member_path"], item["sha256"]) for item in companions),
        manifest_sha256,
    )
    manifest = {**body, "package_id": package_id, "manifest_sha256": manifest_sha256}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(_zip_info(checkpoint_member), checkpoint_bytes)
        for member, data in companion_payloads:
            archive.writestr(_zip_info(member), data)
        archive.writestr(_zip_info(RUN_MANIFEST), canonical_json_bytes(manifest))
    package_bytes = buffer.getvalue()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(package_bytes)
    return RunPackageRecord(
        package_id=package_id,
        checkpoint_member=checkpoint_member,
        checkpoint_sha256=checkpoint_sha256,
        package_sha256=hashlib.sha256(package_bytes).hexdigest(),
        manifest_sha256=manifest_sha256,
        companion_members=tuple(item["member_path"] for item in companions),
        package_path=output_path,
    )


def verify_run_package(path: Path) -> RunPackageRecord:
    path = Path(path)
    package_bytes = path.read_bytes()
    package_sha256 = hashlib.sha256(package_bytes).hexdigest()
    try:
        with zipfile.ZipFile(io.BytesIO(package_bytes), "r") as archive:
            for name in archive.namelist():
                _validate_zip_member(name)
            manifest = json.loads(archive.read(RUN_MANIFEST).decode("utf-8"))
            body = {
                key: manifest.get(key)
                for key in (
                    "format",
                    "format_revision",
                    "checkpoint_member",
                    "checkpoint_sha256",
                    "checkpoint_nbytes",
                    "companions",
                    "metadata",
                )
            }
            if body["format"] != RUN_PACKAGE_FORMAT or body["format_revision"] != 1:
                raise RunPackageIntegrityError("Unsupported Verdant run package format.")
            manifest_sha256 = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
            if manifest_sha256 != manifest.get("manifest_sha256"):
                raise RunPackageIntegrityError("Run package manifest checksum mismatch.")
            checkpoint_member = str(body["checkpoint_member"])
            _validate_zip_member(checkpoint_member)
            checkpoint = archive.read(checkpoint_member)
            checkpoint_sha256 = hashlib.sha256(checkpoint).hexdigest()
            if checkpoint_sha256 != body["checkpoint_sha256"]:
                raise RunPackageIntegrityError("Run package checkpoint checksum mismatch.")
            if len(checkpoint) != body["checkpoint_nbytes"]:
                raise RunPackageIntegrityError("Run package checkpoint length mismatch.")
            companions = body["companions"]
            if not isinstance(companions, list):
                raise RunPackageIntegrityError("Run package companion list is malformed.")
            companion_members: list[str] = []
            companion_signature: list[tuple[str, str]] = []
            for item in companions:
                if not isinstance(item, dict):
                    raise RunPackageIntegrityError("Run package companion entry is malformed.")
                member = str(item["member_path"])
                _validate_zip_member(member)
                payload = archive.read(member)
                digest = hashlib.sha256(payload).hexdigest()
                if digest != item.get("sha256") or len(payload) != item.get("nbytes"):
                    raise RunPackageIntegrityError("Run package companion checksum mismatch.")
                companion_members.append(member)
                companion_signature.append((member, digest))
            expected_id = stable_id(
                "run_package",
                checkpoint_sha256,
                tuple(companion_signature),
                manifest_sha256,
            )
            if expected_id != manifest.get("package_id"):
                raise RunPackageIntegrityError("Run package identity mismatch.")
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        raise RunPackageIntegrityError("Run package is unreadable.") from exc
    return RunPackageRecord(
        package_id=expected_id,
        checkpoint_member=checkpoint_member,
        checkpoint_sha256=checkpoint_sha256,
        package_sha256=package_sha256,
        manifest_sha256=manifest_sha256,
        companion_members=tuple(companion_members),
        package_path=path,
    )


def extract_checkpoint_bytes_from_run_package(path: Path) -> tuple[RunPackageRecord, bytes]:
    record = verify_run_package(path)
    with zipfile.ZipFile(path, "r") as archive:
        return record, archive.read(record.checkpoint_member)


def inspect_generic_zip(path: Path, *, maximum_members: int = 10000) -> dict[str, Any]:
    """Safely inventory an arbitrary ZIP without extracting or executing anything."""

    path = Path(path)
    data = path.read_bytes()
    try:
        with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
            infos = archive.infolist()
            if len(infos) > maximum_members:
                raise MediaArchiveIntegrityError("ZIP contains too many members.")
            members: list[dict[str, Any]] = []
            for info in infos:
                _validate_zip_member(info.filename)
                mode = (info.external_attr >> 16) & 0o170000
                if mode == 0o120000:
                    raise MediaArchiveIntegrityError("ZIP symbolic links are not accepted.")
                members.append(
                    {
                        "name": info.filename,
                        "compressed_bytes": info.compress_size,
                        "uncompressed_bytes": info.file_size,
                        "is_directory": info.is_dir(),
                    }
                )
    except zipfile.BadZipFile as exc:
        raise MediaArchiveIntegrityError("ZIP file is unreadable.") from exc
    return {
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "nbytes": len(data),
        "member_count": len(members),
        "members": members,
        "contains_vdk": any(item["name"].lower().endswith(".vdk") for item in members),
        "contains_run_manifest": any(item["name"] == RUN_MANIFEST for item in members),
    }
