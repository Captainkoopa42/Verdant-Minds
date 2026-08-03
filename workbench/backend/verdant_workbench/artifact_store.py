from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path


class ArtifactIntegrityError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredArtifact:
    sha256: str
    size_bytes: int
    path: str
    media_type: str
    original_name: str | None = None


class ContentAddressedArtifactStore:
    """Immutable filesystem artifact store keyed by SHA-256.

    The Workbench may index these artifacts, but the artifact bytes themselves are
    addressed only by content. Cognitive checkpoint contents are never rewritten
    in place by this store.
    """

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.blobs = self.root / "blobs"
        self.tmp = self.root / "tmp"
        self.blobs.mkdir(parents=True, exist_ok=True)
        self.tmp.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sha256_file(path: Path | str) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _blob_path(self, sha256: str) -> Path:
        if len(sha256) != 64 or any(ch not in "0123456789abcdef" for ch in sha256):
            raise ValueError("Invalid SHA-256 digest.")
        return self.blobs / sha256[:2] / sha256[2:4] / sha256

    def ingest_file(
        self,
        source: Path | str,
        *,
        media_type: str = "application/octet-stream",
        expected_sha256: str | None = None,
    ) -> StoredArtifact:
        source = Path(source)
        if not source.is_file():
            raise FileNotFoundError(source)
        digest = self.sha256_file(source)
        if expected_sha256 is not None and digest != expected_sha256:
            raise ArtifactIntegrityError(
                f"Artifact digest mismatch while ingesting {source}: expected {expected_sha256}, got {digest}."
            )
        target = self._blob_path(digest)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            fd, temp_name = tempfile.mkstemp(prefix="artifact-", dir=self.tmp)
            os.close(fd)
            temp_path = Path(temp_name)
            try:
                shutil.copyfile(source, temp_path)
                if self.sha256_file(temp_path) != digest:
                    raise ArtifactIntegrityError("Temporary artifact copy failed integrity verification.")
                os.replace(temp_path, target)
            finally:
                temp_path.unlink(missing_ok=True)
        elif self.sha256_file(target) != digest:
            raise ArtifactIntegrityError(f"Stored artifact {digest} is corrupted.")
        return StoredArtifact(
            sha256=digest,
            size_bytes=target.stat().st_size,
            path=str(target),
            media_type=media_type,
            original_name=source.name,
        )

    def resolve(self, sha256: str, *, verify: bool = True) -> Path:
        path = self._blob_path(sha256)
        if not path.is_file():
            raise FileNotFoundError(f"Artifact {sha256} is not present in the store.")
        if verify:
            actual = self.sha256_file(path)
            if actual != sha256:
                raise ArtifactIntegrityError(
                    f"Stored artifact integrity failure: expected {sha256}, got {actual}."
                )
        return path

    def verify(self, sha256: str) -> bool:
        try:
            self.resolve(sha256, verify=True)
            return True
        except (FileNotFoundError, ArtifactIntegrityError):
            return False
