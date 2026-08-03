from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import zipfile
from pathlib import Path

from .models import KernelState, canonical_json_bytes


class CheckpointIntegrityError(ValueError):
    pass


STATE_PATH = "state.json"
MANIFEST_PATH = "manifest.json"
FORMAT_VERSION = "verdant-kernel-checkpoint-1"
_FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=name, date_time=_FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o600 << 16
    return info


def state_bytes(state: KernelState) -> bytes:
    return canonical_json_bytes(state.model_dump(mode="json"))


def checkpoint_bytes(state: KernelState) -> bytes:
    payload = state_bytes(state)
    digest = hashlib.sha256(payload).hexdigest()
    manifest = canonical_json_bytes(
        {
            "format": FORMAT_VERSION,
            "state_path": STATE_PATH,
            "state_sha256": digest,
            "state_bytes": len(payload),
        }
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(_zip_info(STATE_PATH), payload)
        archive.writestr(_zip_info(MANIFEST_PATH), manifest)
    return buffer.getvalue()


def save_checkpoint(path: Path, state: KernelState) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = checkpoint_bytes(state)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return hashlib.sha256(data).hexdigest()


def load_checkpoint(path: Path) -> KernelState:
    with zipfile.ZipFile(path, "r") as archive:
        state_payload = archive.read(STATE_PATH)
        manifest = json.loads(archive.read(MANIFEST_PATH).decode("utf-8"))
    if manifest.get("format") != FORMAT_VERSION:
        raise CheckpointIntegrityError("Unsupported checkpoint format.")
    actual_hash = hashlib.sha256(state_payload).hexdigest()
    if actual_hash != manifest.get("state_sha256"):
        raise CheckpointIntegrityError("Checkpoint state checksum mismatch.")
    if len(state_payload) != manifest.get("state_bytes"):
        raise CheckpointIntegrityError("Checkpoint state length mismatch.")
    return KernelState.model_validate_json(state_payload)
